use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct AutostartState {
    pub(crate) supported: bool,
    pub(crate) enabled: bool,
    pub(crate) platform: &'static str,
}

#[tauri::command]
pub(crate) fn get_autostart_state() -> Result<AutostartState, String> {
    platform::get_state()
}

#[tauri::command]
pub(crate) fn set_autostart_enabled(enabled: bool) -> Result<AutostartState, String> {
    platform::set_enabled(enabled)
}

#[cfg(target_os = "windows")]
mod platform {
    use super::AutostartState;
    use std::ffi::{c_void, OsStr};
    use std::os::windows::ffi::OsStrExt;
    use std::ptr::{null, null_mut};

    type Hkey = isize;
    type Lstatus = i32;
    type Dword = u32;

    const HKEY_CURRENT_USER: Hkey = 0x8000_0001_u32 as i32 as isize;
    const KEY_READ: Dword = 0x0002_0019;
    const KEY_SET_VALUE: Dword = 0x0002;
    const REG_SZ: Dword = 1;
    const REG_EXPAND_SZ: Dword = 2;
    const REG_BINARY: Dword = 3;
    const REG_OPTION_NON_VOLATILE: Dword = 0;
    const ERROR_SUCCESS: Lstatus = 0;
    const ERROR_FILE_NOT_FOUND: Lstatus = 2;
    const ERROR_MORE_DATA: Lstatus = 234;

    const RUN_SUBKEY: &str = "Software\\Microsoft\\Windows\\CurrentVersion\\Run";
    const STARTUP_APPROVED_SUBKEY: &str =
        "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\StartupApproved\\Run";
    const VALUE_NAME: &str = "VoxCraftStudio";

    #[link(name = "advapi32")]
    extern "system" {
        fn RegOpenKeyExW(
            h_key: Hkey,
            lp_sub_key: *const u16,
            ul_options: Dword,
            sam_desired: Dword,
            phk_result: *mut Hkey,
        ) -> Lstatus;
        fn RegCreateKeyExW(
            h_key: Hkey,
            lp_sub_key: *const u16,
            reserved: Dword,
            lp_class: *const u16,
            dw_options: Dword,
            sam_desired: Dword,
            lp_security_attributes: *const c_void,
            phk_result: *mut Hkey,
            lpdw_disposition: *mut Dword,
        ) -> Lstatus;
        fn RegQueryValueExW(
            h_key: Hkey,
            lp_value_name: *const u16,
            lp_reserved: *mut Dword,
            lp_type: *mut Dword,
            lp_data: *mut u8,
            lpcb_data: *mut Dword,
        ) -> Lstatus;
        fn RegSetValueExW(
            h_key: Hkey,
            lp_value_name: *const u16,
            reserved: Dword,
            dw_type: Dword,
            lp_data: *const u8,
            cb_data: Dword,
        ) -> Lstatus;
        fn RegDeleteValueW(h_key: Hkey, lp_value_name: *const u16) -> Lstatus;
        fn RegCloseKey(h_key: Hkey) -> Lstatus;
    }

    struct RegistryKey(Hkey);

    impl Drop for RegistryKey {
        fn drop(&mut self) {
            unsafe {
                RegCloseKey(self.0);
            }
        }
    }

    fn to_wide_null(value: &OsStr) -> Vec<u16> {
        value.encode_wide().chain(std::iter::once(0)).collect()
    }

    fn open_key(subkey: &str, access: Dword) -> Result<Option<RegistryKey>, String> {
        let wide_subkey = to_wide_null(OsStr::new(subkey));
        let mut handle: Hkey = 0;
        let status = unsafe {
            RegOpenKeyExW(
                HKEY_CURRENT_USER,
                wide_subkey.as_ptr(),
                0,
                access,
                &mut handle,
            )
        };
        match status {
            ERROR_SUCCESS => Ok(Some(RegistryKey(handle))),
            ERROR_FILE_NOT_FOUND => Ok(None),
            _ => Err(format!(
                "não foi possível abrir a chave de inicialização do Windows (código {status})"
            )),
        }
    }

    fn create_key(subkey: &str, access: Dword) -> Result<RegistryKey, String> {
        let wide_subkey = to_wide_null(OsStr::new(subkey));
        let mut handle: Hkey = 0;
        let status = unsafe {
            RegCreateKeyExW(
                HKEY_CURRENT_USER,
                wide_subkey.as_ptr(),
                0,
                null(),
                REG_OPTION_NON_VOLATILE,
                access,
                null(),
                &mut handle,
                null_mut(),
            )
        };
        if status == ERROR_SUCCESS {
            Ok(RegistryKey(handle))
        } else {
            Err(format!(
                "não foi possível preparar a chave de inicialização do Windows (código {status})"
            ))
        }
    }

    fn query_value(key: &RegistryKey, name: &str) -> Result<Option<(Dword, Vec<u8>)>, String> {
        let wide_name = to_wide_null(OsStr::new(name));
        let mut value_type: Dword = 0;
        let mut byte_len: Dword = 0;
        let status = unsafe {
            RegQueryValueExW(
                key.0,
                wide_name.as_ptr(),
                null_mut(),
                &mut value_type,
                null_mut(),
                &mut byte_len,
            )
        };
        match status {
            ERROR_FILE_NOT_FOUND => return Ok(None),
            ERROR_SUCCESS | ERROR_MORE_DATA => {}
            _ => {
                return Err(format!(
                    "não foi possível ler a inicialização do Windows (código {status})"
                ));
            }
        }
        if byte_len == 0 {
            return Ok(Some((value_type, Vec::new())));
        }

        let mut buffer = vec![0u8; byte_len as usize];
        let mut read_len = byte_len;
        let status = unsafe {
            RegQueryValueExW(
                key.0,
                wide_name.as_ptr(),
                null_mut(),
                &mut value_type,
                buffer.as_mut_ptr(),
                &mut read_len,
            )
        };
        match status {
            ERROR_FILE_NOT_FOUND => Ok(None),
            ERROR_SUCCESS => {
                buffer.truncate(read_len as usize);
                Ok(Some((value_type, buffer)))
            }
            _ => Err(format!(
                "não foi possível ler a inicialização do Windows (código {status})"
            )),
        }
    }

    fn delete_value_if_present(subkey: &str, name: &str) -> Result<(), String> {
        let Some(key) = open_key(subkey, KEY_SET_VALUE)? else {
            return Ok(());
        };
        let wide_name = to_wide_null(OsStr::new(name));
        let status = unsafe { RegDeleteValueW(key.0, wide_name.as_ptr()) };
        if status == ERROR_SUCCESS || status == ERROR_FILE_NOT_FOUND {
            Ok(())
        } else {
            Err(format!(
                "não foi possível remover a inicialização do Windows (código {status})"
            ))
        }
    }

    fn is_disabled_in_task_manager() -> Result<bool, String> {
        let Some(key) = open_key(STARTUP_APPROVED_SUBKEY, KEY_READ)? else {
            return Ok(false);
        };
        let Some((value_type, data)) = query_value(&key, VALUE_NAME)? else {
            return Ok(false);
        };
        Ok(value_type == REG_BINARY && data.first().is_some_and(|byte| (byte & 0x01) != 0))
    }

    fn is_enabled() -> Result<bool, String> {
        let Some(key) = open_key(RUN_SUBKEY, KEY_READ)? else {
            return Ok(false);
        };
        let Some((value_type, data)) = query_value(&key, VALUE_NAME)? else {
            return Ok(false);
        };
        if value_type != REG_SZ && value_type != REG_EXPAND_SZ {
            return Ok(false);
        }
        let mut units: Vec<u16> = data
            .chunks_exact(2)
            .map(|pair| u16::from_le_bytes([pair[0], pair[1]]))
            .collect();
        while units.last() == Some(&0) {
            units.pop();
        }
        let command = String::from_utf16_lossy(&units);
        if command.trim().is_empty() {
            return Ok(false);
        }
        Ok(!is_disabled_in_task_manager()?)
    }

    pub(super) fn get_state() -> Result<AutostartState, String> {
        Ok(AutostartState {
            supported: true,
            enabled: is_enabled()?,
            platform: "windows",
        })
    }

    pub(super) fn set_enabled(enabled: bool) -> Result<AutostartState, String> {
        if enabled {
            let exe = std::env::current_exe()
                .map_err(|error| format!("não foi possível localizar o executável: {error}"))?;
            let command = format!("\"{}\"", exe.display());
            let wide_name = to_wide_null(OsStr::new(VALUE_NAME));
            let wide_command = to_wide_null(OsStr::new(&command));
            let byte_len = u32::try_from(wide_command.len() * std::mem::size_of::<u16>())
                .map_err(|_| "caminho do executável excede o tamanho suportado".to_string())?;
            let key = create_key(RUN_SUBKEY, KEY_SET_VALUE)?;
            let status = unsafe {
                RegSetValueExW(
                    key.0,
                    wide_name.as_ptr(),
                    0,
                    REG_SZ,
                    wide_command.as_ptr().cast::<u8>(),
                    byte_len,
                )
            };
            if status != ERROR_SUCCESS {
                return Err(format!(
                    "não foi possível salvar a inicialização no Windows (código {status})"
                ));
            }
            let _ = delete_value_if_present(STARTUP_APPROVED_SUBKEY, VALUE_NAME);
        } else {
            delete_value_if_present(RUN_SUBKEY, VALUE_NAME)?;
            let _ = delete_value_if_present(STARTUP_APPROVED_SUBKEY, VALUE_NAME);
        }

        get_state()
    }
}

#[cfg(target_os = "linux")]
mod platform {
    use super::AutostartState;
    use std::ffi::OsString;
    use std::fs;
    use std::io::ErrorKind;
    use std::path::{Path, PathBuf};

    const DESKTOP_FILENAME: &str = "voxcraft-studio.desktop";

    fn autostart_file_path_from(
        xdg_config_home: Option<OsString>,
        home: Option<OsString>,
    ) -> Result<PathBuf, String> {
        let config_dir = match xdg_config_home {
            Some(path) if !path.is_empty() => PathBuf::from(path),
            _ => match home {
                Some(path) if !path.is_empty() => PathBuf::from(path).join(".config"),
                _ => {
                    return Err(
                        "não foi possível determinar o diretório de configuração do usuário".into(),
                    );
                }
            },
        };
        Ok(config_dir.join("autostart").join(DESKTOP_FILENAME))
    }

    fn autostart_file_path() -> Result<PathBuf, String> {
        autostart_file_path_from(
            std::env::var_os("XDG_CONFIG_HOME"),
            std::env::var_os("HOME"),
        )
    }

    fn executable_path() -> Result<PathBuf, String> {
        if let Some(appimage) = std::env::var_os("APPIMAGE").filter(|path| !path.is_empty()) {
            return Ok(PathBuf::from(appimage));
        }
        std::env::current_exe()
            .map_err(|error| format!("não foi possível localizar o executável: {error}"))
    }

    fn format_desktop_exec(executable: &Path) -> String {
        let raw = executable.to_string_lossy();
        let mut escaped = String::with_capacity(raw.len() + 4);
        escaped.push('"');
        for ch in raw.chars() {
            match ch {
                '\\' | '"' | '`' | '$' => {
                    escaped.push('\\');
                    escaped.push(ch);
                }
                '%' => escaped.push_str("%%"),
                _ => escaped.push(ch),
            }
        }
        escaped.push('"');
        escaped
    }

    fn desktop_entry_contents(executable: &Path) -> String {
        format!(
            "[Desktop Entry]\n\
Type=Application\n\
Version=1.0\n\
Name=VoxCraft Studio\n\
Comment=VoxCraft Studio\n\
Exec={}\n\
Icon=voxcraft-app\n\
Terminal=false\n\
Categories=AudioVideo;Audio;\n\
X-GNOME-Autostart-enabled=true\n",
            format_desktop_exec(executable)
        )
    }

    fn is_desktop_entry_enabled(contents: &str) -> bool {
        let mut in_desktop_entry = false;
        let mut has_exec = false;
        let mut hidden = false;
        let mut gnome_enabled = true;

        for raw_line in contents.lines() {
            let line = raw_line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            if line.starts_with('[') && line.ends_with(']') {
                if in_desktop_entry {
                    break;
                }
                in_desktop_entry = line == "[Desktop Entry]";
                continue;
            }
            if !in_desktop_entry {
                continue;
            }
            let Some((key, value)) = line.split_once('=') else {
                continue;
            };
            let key = key.trim();
            let value = value.trim();
            match key {
                "Exec" => has_exec = !value.is_empty(),
                "Hidden" => hidden = value.eq_ignore_ascii_case("true"),
                "X-GNOME-Autostart-enabled" => {
                    gnome_enabled = !value.eq_ignore_ascii_case("false");
                }
                _ => {}
            }
        }

        has_exec && !hidden && gnome_enabled
    }

    fn read_enabled(path: &Path) -> Result<bool, String> {
        match fs::read_to_string(path) {
            Ok(contents) => Ok(is_desktop_entry_enabled(&contents)),
            Err(error) if error.kind() == ErrorKind::NotFound => Ok(false),
            Err(error) => Err(format!(
                "não foi possível ler a entrada de inicialização automática: {error}"
            )),
        }
    }

    fn write_enabled(path: &Path, executable: &Path, enabled: bool) -> Result<(), String> {
        if enabled {
            let parent = path.parent().ok_or_else(|| {
                "diretório de inicialização automática inválido".to_string()
            })?;
            fs::create_dir_all(parent).map_err(|error| {
                format!("não foi possível criar o diretório de autostart: {error}")
            })?;
            let contents = desktop_entry_contents(executable);
            fs::write(path, contents).map_err(|error| {
                format!("não foi possível salvar o arquivo de autostart: {error}")
            })?;
        } else if let Err(error) = fs::remove_file(path) {
            if error.kind() != ErrorKind::NotFound {
                return Err(format!(
                    "não foi possível remover o arquivo de autostart: {error}"
                ));
            }
        }
        Ok(())
    }

    pub(super) fn get_state() -> Result<AutostartState, String> {
        let path = autostart_file_path()?;
        Ok(AutostartState {
            supported: true,
            enabled: read_enabled(&path)?,
            platform: "linux",
        })
    }

    pub(super) fn set_enabled(enabled: bool) -> Result<AutostartState, String> {
        let path = autostart_file_path()?;
        let executable = if enabled {
            executable_path()?
        } else {
            PathBuf::new()
        };
        write_enabled(&path, &executable, enabled)?;
        Ok(AutostartState {
            supported: true,
            enabled: read_enabled(&path)?,
            platform: "linux",
        })
    }

    #[cfg(test)]
    mod tests {
        use super::{
            autostart_file_path_from, desktop_entry_contents, format_desktop_exec,
            is_desktop_entry_enabled, read_enabled, write_enabled, DESKTOP_FILENAME,
        };
        use std::ffi::OsString;
        use std::fs;
        use std::path::Path;
        use std::time::{SystemTime, UNIX_EPOCH};

        #[test]
        fn resolves_xdg_autostart_path_with_home_fallback() {
            let from_xdg = autostart_file_path_from(
                Some(OsString::from("/tmp/xdg-config")),
                Some(OsString::from("/home/tester")),
            )
            .unwrap();
            assert_eq!(
                from_xdg,
                Path::new("/tmp/xdg-config/autostart").join(DESKTOP_FILENAME)
            );

            let from_home = autostart_file_path_from(
                Some(OsString::new()),
                Some(OsString::from("/home/tester")),
            )
            .unwrap();
            assert_eq!(
                from_home,
                Path::new("/home/tester/.config/autostart").join(DESKTOP_FILENAME)
            );

            assert!(autostart_file_path_from(None, None).is_err());
        }

        #[test]
        fn escapes_desktop_exec_spec_characters() {
            let formatted = format_desktop_exec(Path::new("/opt/Vox Craft/bin/vox\"$100%"));
            assert_eq!(formatted, "\"/opt/Vox Craft/bin/vox\\\"\\$100%%\"");
        }

        #[test]
        fn parses_desktop_entry_autostart_flags() {
            let generated = desktop_entry_contents(Path::new("/usr/bin/voxcraft-app"));
            assert!(is_desktop_entry_enabled(&generated));

            assert!(!is_desktop_entry_enabled(
                "[Desktop Entry]\nExec=/usr/bin/voxcraft-app\nHidden=true\n"
            ));
            assert!(!is_desktop_entry_enabled(
                "[Desktop Entry]\nExec=/usr/bin/voxcraft-app\nX-GNOME-Autostart-enabled=false\n"
            ));
            assert!(!is_desktop_entry_enabled(
                "[Desktop Entry]\nName=VoxCraft Studio\n"
            ));
        }

        #[test]
        fn writes_reads_and_removes_desktop_file() {
            let unique = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos();
            let temp_root = std::env::temp_dir().join(format!("voxcraft-autostart-{unique}"));
            let desktop_path = temp_root.join("autostart").join(DESKTOP_FILENAME);

            assert!(!read_enabled(&desktop_path).unwrap());

            write_enabled(
                &desktop_path,
                Path::new("/usr/local/bin/voxcraft-app"),
                true,
            )
            .unwrap();
            assert!(desktop_path.is_file());
            assert!(read_enabled(&desktop_path).unwrap());

            write_enabled(&desktop_path, Path::new(""), false).unwrap();
            assert!(!desktop_path.exists());
            assert!(!read_enabled(&desktop_path).unwrap());

            let _ = fs::remove_dir_all(&temp_root);
        }
    }
}

#[cfg(not(any(target_os = "windows", target_os = "linux")))]
mod platform {
    use super::AutostartState;

    pub(super) fn get_state() -> Result<AutostartState, String> {
        Ok(AutostartState {
            supported: false,
            enabled: false,
            platform: std::env::consts::OS,
        })
    }

    pub(super) fn set_enabled(_enabled: bool) -> Result<AutostartState, String> {
        Err("iniciar com o sistema está disponível apenas no Windows e no Linux".into())
    }
}
