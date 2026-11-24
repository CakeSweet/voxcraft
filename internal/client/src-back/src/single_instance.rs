use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};

pub(crate) enum AcquireOutcome {
    Primary(InstanceGuard),
    AlreadyRunning,
}

pub(crate) struct InstanceGuard {
    stopping: Arc<AtomicBool>,
    #[cfg(any(target_os = "windows", target_os = "linux"))]
    platform: platform::PlatformGuard,
}

impl InstanceGuard {
    pub(crate) fn start_listener<F>(&mut self, on_activate: F)
    where
        F: Fn() + Send + Sync + 'static,
    {
        #[cfg(any(target_os = "windows", target_os = "linux"))]
        self.platform
            .start_listener(Arc::clone(&self.stopping), Arc::new(on_activate));

        #[cfg(not(any(target_os = "windows", target_os = "linux")))]
        let _ = on_activate;
    }

    pub(crate) fn shutdown(&mut self) {
        self.stopping.store(true, Ordering::Release);
        #[cfg(any(target_os = "windows", target_os = "linux"))]
        self.platform.shutdown();
    }
}

impl Drop for InstanceGuard {
    fn drop(&mut self) {
        self.shutdown();
    }
}

pub(crate) fn acquire() -> AcquireOutcome {
    #[cfg(any(target_os = "windows", target_os = "linux"))]
    {
        platform::acquire()
    }

    #[cfg(not(any(target_os = "windows", target_os = "linux")))]
    {
        AcquireOutcome::Primary(InstanceGuard {
            stopping: Arc::new(AtomicBool::new(false)),
        })
    }
}

#[cfg(any(target_os = "windows", target_os = "linux", test))]
fn sanitize_scope_suffix(raw: &str) -> String {
    let cleaned: String = raw
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || ch == '_' || ch == '-' {
                ch
            } else {
                '_'
            }
        })
        .take(48)
        .collect();
    if cleaned.is_empty() {
        "default".to_string()
    } else {
        cleaned
    }
}

#[cfg(target_os = "windows")]
mod platform {
    use super::{sanitize_scope_suffix, AcquireOutcome, InstanceGuard};
    use std::ffi::{c_void, OsStr};
    use std::os::windows::ffi::OsStrExt;
    use std::ptr::{null, null_mut};
    use std::sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    };
    use std::time::{Duration, Instant};

    type Handle = isize;
    type Dword = u32;

    const INVALID_HANDLE_VALUE: Handle = -1;
    const ERROR_FILE_NOT_FOUND: Dword = 2;
    const ERROR_ALREADY_EXISTS: Dword = 183;
    const ERROR_PIPE_BUSY: Dword = 231;
    const ERROR_PIPE_CONNECTED: Dword = 535;

    const PIPE_ACCESS_INBOUND: Dword = 0x0000_0001;
    const PIPE_TYPE_BYTE: Dword = 0x0000_0000;
    const PIPE_READMODE_BYTE: Dword = 0x0000_0000;
    const PIPE_WAIT: Dword = 0x0000_0000;

    const GENERIC_WRITE: Dword = 0x4000_0000;
    const OPEN_EXISTING: Dword = 3;

    const MUTEX_NAME: &str = "Local\\VoxCraftStudio_SingleInstance";

    #[link(name = "kernel32")]
    extern "system" {
        fn CreateMutexW(
            lp_mutex_attributes: *const c_void,
            b_initial_owner: i32,
            lp_name: *const u16,
        ) -> Handle;
        fn GetLastError() -> Dword;
        fn CloseHandle(h_object: Handle) -> i32;
        fn CreateNamedPipeW(
            lp_name: *const u16,
            dw_open_mode: Dword,
            dw_pipe_mode: Dword,
            n_max_instances: Dword,
            n_out_buffer_size: Dword,
            n_in_buffer_size: Dword,
            n_default_time_out: Dword,
            lp_security_attributes: *const c_void,
        ) -> Handle;
        fn ConnectNamedPipe(h_named_pipe: Handle, lp_overlapped: *mut c_void) -> i32;
        fn DisconnectNamedPipe(h_named_pipe: Handle) -> i32;
        fn WaitNamedPipeW(lp_named_pipe_name: *const u16, n_time_out: Dword) -> i32;
        fn CreateFileW(
            lp_file_name: *const u16,
            dw_desired_access: Dword,
            dw_share_mode: Dword,
            lp_security_attributes: *const c_void,
            dw_creation_disposition: Dword,
            dw_flags_and_attributes: Dword,
            h_template_file: Handle,
        ) -> Handle;
        fn ReadFile(
            h_file: Handle,
            lp_buffer: *mut u8,
            n_number_of_bytes_to_read: Dword,
            lp_number_of_bytes_read: *mut Dword,
            lp_overlapped: *mut c_void,
        ) -> i32;
        fn WriteFile(
            h_file: Handle,
            lp_buffer: *const u8,
            n_number_of_bytes_to_write: Dword,
            lp_number_of_bytes_written: *mut Dword,
            lp_overlapped: *mut c_void,
        ) -> i32;
    }

    pub(super) struct PlatformGuard {
        mutex_handle: Handle,
        pipe_name: String,
        listener_started: bool,
    }

    impl PlatformGuard {
        pub(super) fn start_listener(
            &mut self,
            stopping: Arc<AtomicBool>,
            on_activate: Arc<dyn Fn() + Send + Sync>,
        ) {
            if self.listener_started {
                return;
            }
            self.listener_started = true;
            let pipe_name = self.pipe_name.clone();
            std::thread::spawn(move || {
                let wide_pipe = to_wide_null(&pipe_name);
                let pipe = unsafe {
                    CreateNamedPipeW(
                        wide_pipe.as_ptr(),
                        PIPE_ACCESS_INBOUND,
                        PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                        1,
                        64,
                        64,
                        0,
                        null(),
                    )
                };
                if pipe == INVALID_HANDLE_VALUE || pipe == 0 {
                    eprintln!("VoxCraft single-instance pipe unavailable");
                    return;
                }

                while !stopping.load(Ordering::Acquire) {
                    let connected = unsafe { ConnectNamedPipe(pipe, null_mut()) } != 0
                        || unsafe { GetLastError() } == ERROR_PIPE_CONNECTED;
                    if !connected {
                        std::thread::sleep(Duration::from_millis(25));
                        continue;
                    }

                    let mut buffer = [0u8; 64];
                    let mut read_bytes: Dword = 0;
                    let ok = unsafe {
                        ReadFile(
                            pipe,
                            buffer.as_mut_ptr(),
                            buffer.len() as Dword,
                            &mut read_bytes,
                            null_mut(),
                        )
                    };
                    unsafe {
                        let _ = DisconnectNamedPipe(pipe);
                    }

                    if stopping.load(Ordering::Acquire) {
                        break;
                    }
                    if ok != 0 && buffer[..read_bytes as usize].starts_with(b"SHOW") {
                        on_activate();
                    }
                }

                unsafe {
                    let _ = CloseHandle(pipe);
                }
            });
        }

        pub(super) fn shutdown(&mut self) {
            if self.listener_started {
                self.listener_started = false;
                let _ = send_pipe_message(&self.pipe_name, b"STOP\n", Duration::from_millis(100));
            }
            if self.mutex_handle != 0 && self.mutex_handle != INVALID_HANDLE_VALUE {
                unsafe {
                    let _ = CloseHandle(self.mutex_handle);
                }
                self.mutex_handle = 0;
            }
        }
    }

    fn to_wide_null(value: &str) -> Vec<u16> {
        OsStr::new(value)
            .encode_wide()
            .chain(std::iter::once(0))
            .collect()
    }

    fn pipe_name() -> String {
        let user = std::env::var("USERNAME").unwrap_or_default();
        format!(
            r"\\.\pipe\VoxCraftStudio_IPC_{}",
            sanitize_scope_suffix(&user)
        )
    }

    fn send_pipe_message(pipe_name: &str, payload: &[u8], timeout: Duration) -> bool {
        let wide_pipe = to_wide_null(pipe_name);
        let deadline = Instant::now() + timeout;
        loop {
            let handle = unsafe {
                CreateFileW(
                    wide_pipe.as_ptr(),
                    GENERIC_WRITE,
                    0,
                    null(),
                    OPEN_EXISTING,
                    0,
                    0,
                )
            };
            if handle != INVALID_HANDLE_VALUE && handle != 0 {
                let mut written: Dword = 0;
                let ok = unsafe {
                    WriteFile(
                        handle,
                        payload.as_ptr(),
                        payload.len() as Dword,
                        &mut written,
                        null_mut(),
                    )
                };
                unsafe {
                    let _ = CloseHandle(handle);
                }
                return ok != 0;
            }

            if Instant::now() >= deadline {
                return false;
            }

            let err = unsafe { GetLastError() };
            if err == ERROR_PIPE_BUSY {
                let _ = unsafe { WaitNamedPipeW(wide_pipe.as_ptr(), 250) };
            } else if err == ERROR_FILE_NOT_FOUND {
                std::thread::sleep(Duration::from_millis(50));
            } else {
                return false;
            }
        }
    }

    pub(super) fn acquire() -> AcquireOutcome {
        let wide_mutex = to_wide_null(MUTEX_NAME);
        let handle = unsafe { CreateMutexW(null(), 0, wide_mutex.as_ptr()) };
        let last_err = unsafe { GetLastError() };
        let pipe = pipe_name();

        if handle != 0 && last_err == ERROR_ALREADY_EXISTS {
            unsafe {
                let _ = CloseHandle(handle);
            }
            let _ = send_pipe_message(&pipe, b"SHOW\n", Duration::from_secs(2));
            return AcquireOutcome::AlreadyRunning;
        }

        AcquireOutcome::Primary(InstanceGuard {
            stopping: Arc::new(AtomicBool::new(false)),
            platform: PlatformGuard {
                mutex_handle: handle,
                pipe_name: pipe,
                listener_started: false,
            },
        })
    }
}

#[cfg(target_os = "linux")]
mod platform {
    use super::{sanitize_scope_suffix, AcquireOutcome, InstanceGuard};
    use std::fs;
    use std::io::{ErrorKind, Read, Write};
    use std::os::unix::net::{UnixListener, UnixStream};
    use std::path::{Path, PathBuf};
    use std::sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    };
    use std::time::Duration;

    pub(super) struct PlatformGuard {
        listener: Option<UnixListener>,
        socket_path: Option<PathBuf>,
    }

    impl PlatformGuard {
        pub(super) fn start_listener(
            &mut self,
            stopping: Arc<AtomicBool>,
            on_activate: Arc<dyn Fn() + Send + Sync>,
        ) {
            let Some(listener) = self.listener.take() else {
                return;
            };
            std::thread::spawn(move || {
                for stream in listener.incoming() {
                    if stopping.load(Ordering::Acquire) {
                        break;
                    }
                    let Ok(mut stream) = stream else {
                        continue;
                    };
                    let _ = stream.set_read_timeout(Some(Duration::from_millis(200)));
                    let mut buf = [0u8; 64];
                    if let Ok(read) = stream.read(&mut buf) {
                        if buf[..read].starts_with(b"SHOW") {
                            on_activate();
                        }
                    }
                }
            });
        }

        pub(super) fn shutdown(&mut self) {
            if let Some(path) = self.socket_path.take() {
                if let Ok(mut stream) = UnixStream::connect(&path) {
                    let _ = stream.write_all(b"STOP\n");
                }
                let _ = fs::remove_file(&path);
            }
        }
    }

    fn socket_path() -> PathBuf {
        if let Some(runtime_dir) = std::env::var_os("XDG_RUNTIME_DIR").filter(|p| !p.is_empty()) {
            return PathBuf::from(runtime_dir).join("voxcraft-studio.sock");
        }
        let user = std::env::var("USER").unwrap_or_default();
        std::env::temp_dir().join(format!(
            "voxcraft-studio-{}.sock",
            sanitize_scope_suffix(&user)
        ))
    }

    fn notify_running(path: &Path) -> bool {
        let Ok(mut stream) = UnixStream::connect(path) else {
            return false;
        };
        let _ = stream.set_write_timeout(Some(Duration::from_millis(500)));
        let _ = stream.write_all(b"SHOW\n");
        let _ = stream.flush();
        true
    }

    pub(super) fn acquire() -> AcquireOutcome {
        let path = socket_path();
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }

        if notify_running(&path) {
            return AcquireOutcome::AlreadyRunning;
        }

        match UnixListener::bind(&path) {
            Ok(listener) => AcquireOutcome::Primary(InstanceGuard {
                stopping: Arc::new(AtomicBool::new(false)),
                platform: PlatformGuard {
                    listener: Some(listener),
                    socket_path: Some(path),
                },
            }),
            Err(err) if err.kind() == ErrorKind::AddrInUse => {
                std::thread::sleep(Duration::from_millis(40));
                if notify_running(&path) {
                    return AcquireOutcome::AlreadyRunning;
                }
                let _ = fs::remove_file(&path);
                match UnixListener::bind(&path) {
                    Ok(listener) => AcquireOutcome::Primary(InstanceGuard {
                        stopping: Arc::new(AtomicBool::new(false)),
                        platform: PlatformGuard {
                            listener: Some(listener),
                            socket_path: Some(path),
                        },
                    }),
                    Err(_) => {
                        if notify_running(&path) {
                            AcquireOutcome::AlreadyRunning
                        } else {
                            AcquireOutcome::Primary(InstanceGuard {
                                stopping: Arc::new(AtomicBool::new(false)),
                                platform: PlatformGuard {
                                    listener: None,
                                    socket_path: None,
                                },
                            })
                        }
                    }
                }
            }
            Err(_) => AcquireOutcome::Primary(InstanceGuard {
                stopping: Arc::new(AtomicBool::new(false)),
                platform: PlatformGuard {
                    listener: None,
                    socket_path: None,
                },
            }),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::sanitize_scope_suffix;

    #[test]
    fn sanitizes_scope_suffix_for_ipc_names() {
        assert_eq!(sanitize_scope_suffix("Alice Smith"), "Alice_Smith");
        assert_eq!(sanitize_scope_suffix("..\\evil/name"), "___evil_name");
        assert_eq!(sanitize_scope_suffix(""), "default");
    }
}
