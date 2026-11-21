use serde::Serialize;
use serde_json::{json, Value};
use std::{
    io::{BufRead, BufReader, Write},
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, State,
};

struct CoreProcess {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
    request_id: u64,
}

impl CoreProcess {
    #[cfg(debug_assertions)]
    fn command() -> Result<Command, String> {
        let core_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../core");
        let core_entrypoint = core_dir.join("app.py");
        if !core_entrypoint.is_file() {
            return Err(format!(
                "entrypoint do core Python não encontrado: {}",
                core_entrypoint.display()
            ));
        }

        let python = std::env::var_os("VOXCRAFT_PYTHON").unwrap_or_else(|| {
            if cfg!(target_os = "windows") {
                "python".into()
            } else {
                "python3".into()
            }
        });
        let mut command = Command::new(python);
        command.args(["-u", "app.py"]).current_dir(core_dir);
        Ok(command)
    }

    #[cfg(not(debug_assertions))]
    fn command() -> Result<Command, String> {
        let exe = std::env::current_exe()
            .map_err(|error| format!("não foi possível localizar o VoxCraft: {error}"))?;
        let core = exe.with_file_name(format!("voxcraft-core{}", std::env::consts::EXE_SUFFIX));
        if !core.is_file() {
            return Err(format!(
                "core Python do pacote não encontrado: {}",
                core.display()
            ));
        }
        Ok(Command::new(core))
    }

    fn spawn() -> Result<Self, String> {
        let mut command = Self::command()?;
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x0800_0000); // CREATE_NO_WINDOW (stdio remains piped)
        }
        let mut child = command
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .map_err(|error| format!("não foi possível iniciar o core Python: {error}"))?;

        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| "não foi possível abrir stdin do core Python".to_string())?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "não foi possível abrir stdout do core Python".to_string())?;
        let mut process = Self {
            child,
            stdin,
            stdout: BufReader::new(stdout),
            request_id: 0,
        };
        process.request("ping", json!({}))?;
        Ok(process)
    }

    fn request(&mut self, method: &str, params: Value) -> Result<Value, String> {
        self.request_id += 1;
        let request_id = self.request_id;
        let request = json!({
            "id": request_id,
            "method": method,
            "params": params
        });

        serde_json::to_writer(&mut self.stdin, &request)
            .map_err(|error| format!("falha ao enviar comando ao core Python: {error}"))?;
        self.stdin
            .write_all(b"\n")
            .and_then(|()| self.stdin.flush())
            .map_err(|error| format!("falha ao enviar comando ao core Python: {error}"))?;

        let mut line = String::new();
        let bytes = self
            .stdout
            .read_line(&mut line)
            .map_err(|error| format!("falha ao ler resposta do core Python: {error}"))?;
        if bytes == 0 {
            let exit = self
                .child
                .try_wait()
                .ok()
                .flatten()
                .map(|status| format!(" (processo encerrado com {status})"))
                .unwrap_or_default();
            return Err(format!("core Python encerrou sem responder{exit}"));
        }

        let response: Value = serde_json::from_str(&line)
            .map_err(|error| format!("resposta inválida do core Python: {error}"))?;
        if response.get("id").and_then(Value::as_u64) != Some(request_id) {
            return Err("resposta do core Python com identificador inesperado".into());
        }
        if response.get("ok").and_then(Value::as_bool) != Some(true) {
            return Err(response
                .get("error")
                .and_then(Value::as_str)
                .unwrap_or("erro desconhecido no core Python")
                .to_string());
        }
        Ok(response.get("result").cloned().unwrap_or(Value::Null))
    }

    fn shutdown(&mut self) {
        if self.child.try_wait().ok().flatten().is_none() {
            if self.request("shutdown", json!({})).is_ok() {
                // Let the one-file bootloader reap Python and remove its temporary files.
                let deadline = Instant::now() + Duration::from_secs(1);
                while Instant::now() < deadline {
                    if let Ok(Some(_)) = self.child.try_wait() {
                        return;
                    }
                    std::thread::sleep(Duration::from_millis(20));
                }
            }
            let _ = self.child.kill();
            let _ = self.child.wait();
        }
    }
}

impl Drop for CoreProcess {
    fn drop(&mut self) {
        self.shutdown();
    }
}

struct CoreState {
    process: Mutex<Option<CoreProcess>>,
    startup_error: Option<String>,
}

impl CoreState {
    fn launch() -> Self {
        match CoreProcess::spawn() {
            Ok(process) => Self {
                process: Mutex::new(Some(process)),
                startup_error: None,
            },
            Err(error) => {
                eprintln!("VoxCraft Python core: {error}");
                Self {
                    process: Mutex::new(None),
                    startup_error: Some(error),
                }
            }
        }
    }

    fn request(&self, method: &str, params: Value) -> Result<Value, String> {
        let mut process = self
            .process
            .lock()
            .map_err(|_| "estado do core Python indisponível".to_string())?;
        let process = process.as_mut().ok_or_else(|| {
            self.startup_error
                .clone()
                .unwrap_or_else(|| "core Python não iniciado".to_string())
        })?;
        process.request(method, params)
    }

    fn shutdown(&self) {
        if let Ok(mut process) = self.process.lock() {
            process.take();
        }
    }
}

struct CoreShutdown(Arc<CoreState>);

impl tauri::Resource for CoreShutdown {}

impl Drop for CoreShutdown {
    fn drop(&mut self) {
        self.0.shutdown();
    }
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeStatus {
    shell: &'static str,
    core_connected: bool,
    message: String,
}

#[tauri::command]
fn get_runtime_status(core: State<'_, Arc<CoreState>>) -> RuntimeStatus {
    match core.request("ping", json!({})) {
        Ok(status) => RuntimeStatus {
            shell: "tauri",
            core_connected: true,
            message: status
                .get("message")
                .and_then(Value::as_str)
                .unwrap_or("Core Python conectado.")
                .to_string(),
        },
        Err(error) => RuntimeStatus {
            shell: "tauri",
            core_connected: false,
            message: format!("Core Python indisponível: {error}"),
        },
    }
}

#[tauri::command]
fn core_request(
    core: State<'_, Arc<CoreState>>,
    method: String,
    params: Option<Value>,
) -> Result<Value, String> {
    const ALLOWED_METHODS: &[&str] = &[
        "list_devices",
        "refresh_devices",
        "get_params",
        "set_params",
        "list_presets",
        "apply_preset",
        "save_preset",
        "delete_preset",
        "start_audio",
        "set_monitor",
        "stop_audio",
        "meters",
    ];
    if !ALLOWED_METHODS.contains(&method.as_str()) {
        return Err(format!("comando do core não permitido: {method}"));
    }
    core.request(&method, params.unwrap_or_else(|| json!({})))
}

#[tauri::command]
fn updater_is_configured() -> bool {
    option_env!("UPDATER_PUBLIC_KEY").is_some_and(|key| !key.trim().is_empty())
}

#[tauri::command]
fn updater_target() -> Option<String> {
    let platform = format!("{}-{}", std::env::consts::OS, std::env::consts::ARCH);

    #[cfg(target_os = "linux")]
    {
        use tauri::utils::{config::BundleType, platform::bundle_type};
        let format = match bundle_type()? {
            BundleType::Deb => "deb",
            BundleType::Rpm => "rpm",
            _ => return None,
        };
        Some(format!("{platform}-{format}"))
    }

    #[cfg(not(target_os = "linux"))]
    {
        Some(platform)
    }
}

#[tauri::command]
fn restart_app(app: tauri::AppHandle) {
    app.restart();
}

fn show_main_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn setup_tray(app: &tauri::App) -> tauri::Result<()> {
    let show = MenuItem::with_id(app, "show", "Abrir", true, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let quit = MenuItem::with_id(app, "quit", "Sair", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&show, &separator, &quit])?;
    let icon = app.default_window_icon().cloned().ok_or_else(|| {
        tauri::Error::InvalidIcon(std::io::Error::other(
            "ícone padrão do VoxCraft não configurado",
        ))
    })?;

    TrayIconBuilder::with_id("voxcraft-tray")
        .icon(icon)
        .tooltip("VoxCraft Studio")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id().as_ref() {
            "show" => show_main_window(app),
            "quit" => app.exit(0),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if matches!(
                event,
                TrayIconEvent::Click {
                    button: MouseButton::Left,
                    button_state: MouseButtonState::Up,
                    ..
                }
            ) {
                show_main_window(tray.app_handle());
            }
        })
        .build(app)?;

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_runtime_status,
            core_request,
            updater_is_configured,
            updater_target,
            restart_app
        ])
        .setup(|app| {
            let core = Arc::new(CoreState::launch());
            // The Windows updater clears Tauri resources before exiting to run NSIS.
            app.resources_table().add(CoreShutdown(Arc::clone(&core)));
            app.manage(core);
            setup_tray(app)?;
            Ok(())
        });

    let builder = match option_env!("UPDATER_PUBLIC_KEY") {
        Some(public_key) if !public_key.trim().is_empty() => builder.plugin(
            tauri_plugin_updater::Builder::new()
                .pubkey(public_key)
                .build(),
        ),
        _ => builder,
    };

    let app = builder
        .build(tauri::generate_context!())
        .expect("erro ao iniciar VoxCraft Studio");
    app.run(|app_handle, event| {
        if matches!(event, tauri::RunEvent::Exit) {
            app_handle.state::<Arc<CoreState>>().shutdown();
        }
    });
}
