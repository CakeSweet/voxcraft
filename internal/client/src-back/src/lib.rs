#[cfg(target_os = "linux")]
use futures_util::StreamExt;
use serde::Serialize;
use serde_json::{json, Value};
use std::{
    io::{BufRead, BufReader, Write},
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};
use tauri::{Emitter, Manager, State};
#[cfg(any(target_os = "macos", windows, target_os = "linux"))]
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};

mod tray;
mod updater;

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

    fn spawn() -> Result<(Self, Value), String> {
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
        let status = process.request("ping", json!({}))?;
        Ok((process, status))
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

enum CoreConnection {
    NotStarted,
    Running(CoreProcess),
    Failed(String),
    Stopped,
}

struct CoreState(Mutex<CoreConnection>);

impl CoreState {
    fn new() -> Self {
        Self(Mutex::new(CoreConnection::NotStarted))
    }

    fn connect(&self) -> Result<Value, String> {
        let mut connection = self
            .0
            .lock()
            .map_err(|_| "estado do core Python indisponível".to_string())?;
        if matches!(*connection, CoreConnection::NotStarted) {
            return match CoreProcess::spawn() {
                Ok((process, status)) => {
                    *connection = CoreConnection::Running(process);
                    Ok(status)
                }
                Err(error) => {
                    eprintln!("VoxCraft Python core: {error}");
                    *connection = CoreConnection::Failed(error.clone());
                    Err(error)
                }
            };
        }
        Self::request_connected(&mut connection, "ping", json!({}))
    }

    fn request(&self, method: &str, params: Value) -> Result<Value, String> {
        let mut connection = self
            .0
            .lock()
            .map_err(|_| "estado do core Python indisponível".to_string())?;
        Self::request_connected(&mut connection, method, params)
    }

    fn request_connected(
        connection: &mut CoreConnection,
        method: &str,
        params: Value,
    ) -> Result<Value, String> {
        match connection {
            CoreConnection::Running(process) => process.request(method, params),
            CoreConnection::Failed(error) => Err(error.clone()),
            CoreConnection::NotStarted | CoreConnection::Stopped => {
                Err("core Python não iniciado".into())
            }
        }
    }

    fn shutdown(&self) {
        if let Ok(mut connection) = self.0.lock() {
            let previous = std::mem::replace(&mut *connection, CoreConnection::Stopped);
            drop(connection);
            drop(previous);
        }
    }
}

#[cfg(test)]
mod core_startup_tests {
    use super::{CoreConnection, CoreState};
    use serde_json::json;

    #[test]
    fn creating_core_state_does_not_start_python() {
        let core = CoreState::new();
        assert!(matches!(
            *core.0.lock().unwrap(),
            CoreConnection::NotStarted
        ));
        assert!(core.request("ping", json!({})).is_err());
        core.shutdown();
        assert!(core.connect().is_err());
        assert!(matches!(*core.0.lock().unwrap(), CoreConnection::Stopped));
    }
}

#[cfg(target_os = "linux")]
#[derive(Default)]
struct PortalShortcutState {
    task: Mutex<Option<PortalShortcutTask>>,
}

#[cfg(target_os = "linux")]
struct PortalShortcutTask {
    cancel: tokio::sync::oneshot::Sender<()>,
    join: tauri::async_runtime::JoinHandle<()>,
    portal: Arc<ashpd::desktop::global_shortcuts::GlobalShortcuts>,
    session: Arc<ashpd::desktop::Session<ashpd::desktop::global_shortcuts::GlobalShortcuts>>,
}

#[cfg(target_os = "linux")]
impl PortalShortcutState {
    fn shutdown(&self) {
        if let Ok(mut task) = self.task.lock() {
            if let Some(task) = task.take() {
                let _ = task.cancel.send(());
            }
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
async fn get_runtime_status(core: State<'_, Arc<CoreState>>) -> Result<RuntimeStatus, String> {
    let core = Arc::clone(core.inner());
    let status = tauri::async_runtime::spawn_blocking(move || core.connect())
        .await
        .map_err(|error| error.to_string())?;
    Ok(match status {
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
    })
}

#[tauri::command]
async fn core_request(
    core: State<'_, Arc<CoreState>>,
    method: String,
    params: Option<Value>,
) -> Result<Value, String> {
    const ALLOWED_METHODS: &[&str] = &[
        "list_devices",
        "refresh_devices",
        "ensure_virtual_output",
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
    let core = Arc::clone(core.inner());
    tauri::async_runtime::spawn_blocking(move || {
        core.request(&method, params.unwrap_or_else(|| json!({})))
    })
    .await
    .map_err(|error| error.to_string())?
}

#[tauri::command]
fn is_wayland_session() -> bool {
    #[cfg(target_os = "linux")]
    {
        // XWayland grabs cannot reach native Wayland apps, even if GTK uses X11.
        return std::env::var("XDG_SESSION_TYPE")
            .is_ok_and(|session| session.eq_ignore_ascii_case("wayland"))
            || std::env::var_os("WAYLAND_DISPLAY").is_some_and(|display| !display.is_empty());
    }

    #[cfg(not(target_os = "linux"))]
    {
        false
    }
}

#[cfg(any(target_os = "macos", windows, target_os = "linux"))]
fn emit_hotkey(app: &tauri::AppHandle, state: &str) {
    let _ = app.emit_to("main", "voxcraft-global-hotkey", state);
}

#[tauri::command]
#[cfg(any(target_os = "macos", windows, target_os = "linux"))]
async fn configure_native_hotkey(
    app: tauri::AppHandle,
    shortcut: String,
    enabled: bool,
) -> Result<(), String> {
    if is_wayland_session() {
        return Err("atalhos nativos indisponíveis nesta sessão Wayland".into());
    }
    let manager = app.global_shortcut();
    let result = if enabled {
        manager.on_shortcut(shortcut.as_str(), |app, _, event| {
            emit_hotkey(
                app,
                match event.state {
                    ShortcutState::Pressed => "Pressed",
                    ShortcutState::Released => "Released",
                },
            );
        })
    } else {
        manager.unregister(shortcut.as_str())
    };
    result.map_err(|error| error.to_string())
}

#[cfg(not(any(target_os = "macos", windows, target_os = "linux")))]
#[tauri::command]
fn configure_native_hotkey() -> Result<(), String> {
    Err("atalhos nativos indisponíveis nesta plataforma".into())
}

#[cfg(target_os = "linux")]
fn portal_preferred_trigger(shortcut: &str) -> Option<String> {
    let tokens: Vec<_> = shortcut.split('+').collect();
    let (key_token, modifier_tokens) = tokens.split_last()?;
    let mut modifiers = Vec::with_capacity(modifier_tokens.len());
    for modifier in modifier_tokens {
        modifiers.push(match modifier.to_ascii_uppercase().as_str() {
            "CTRL" | "CONTROL" => "CTRL",
            "ALT" | "OPTION" => "ALT",
            "SHIFT" => "SHIFT",
            "SUPER" | "META" | "CMD" | "COMMAND" => "LOGO",
            _ => return None,
        });
    }

    let key = match *key_token {
        " " | "Space" | "space" => "space".to_string(),
        "Enter" | "Return" => "Return".to_string(),
        "Escape" | "Esc" => "Escape".to_string(),
        "Backspace" | "BackSpace" => "BackSpace".to_string(),
        "Tab" => "Tab".to_string(),
        "ArrowUp" | "Up" => "Up".to_string(),
        "ArrowDown" | "Down" => "Down".to_string(),
        "ArrowLeft" | "Left" => "Left".to_string(),
        "ArrowRight" | "Right" => "Right".to_string(),
        "PageUp" | "Page_Up" => "Page_Up".to_string(),
        "PageDown" | "Page_Down" => "Page_Down".to_string(),
        "Home" | "End" | "Insert" | "Delete" => key_token.to_string(),
        "CapsLock" | "Caps_Lock" => "Caps_Lock".to_string(),
        "NumLock" | "Num_Lock" => "Num_Lock".to_string(),
        "ScrollLock" | "Scroll_Lock" => "Scroll_Lock".to_string(),
        "Backquote" | "grave" => "grave".to_string(),
        "Backslash" | "backslash" => "backslash".to_string(),
        "BracketLeft" | "bracketleft" => "bracketleft".to_string(),
        "BracketRight" | "bracketright" => "bracketright".to_string(),
        "Comma" | "comma" => "comma".to_string(),
        "Equal" | "equal" => "equal".to_string(),
        "Minus" | "minus" => "minus".to_string(),
        "Period" | "period" => "period".to_string(),
        "Quote" | "apostrophe" => "apostrophe".to_string(),
        "Semicolon" | "semicolon" => "semicolon".to_string(),
        "Slash" | "slash" => "slash".to_string(),
        "NumpadAdd" => "KP_Add".to_string(),
        "NumpadSubtract" => "KP_Subtract".to_string(),
        "NumpadMultiply" => "KP_Multiply".to_string(),
        "NumpadDivide" => "KP_Divide".to_string(),
        "NumpadDecimal" => "KP_Decimal".to_string(),
        "NumpadEnter" => "KP_Enter".to_string(),
        "NumpadEqual" => "KP_Equal".to_string(),
        _ if key_token.strip_prefix("Key").is_some_and(|letter| {
            letter.len() == 1 && letter.as_bytes()[0].is_ascii_alphabetic()
        }) =>
        {
            key_token[3..].to_ascii_lowercase()
        }
        _ if key_token
            .strip_prefix("Digit")
            .is_some_and(|digit| digit.len() == 1 && digit.as_bytes()[0].is_ascii_digit()) =>
        {
            key_token[5..].to_string()
        }
        _ if key_token
            .strip_prefix("Numpad")
            .and_then(|digit| digit.parse::<u8>().ok())
            .is_some_and(|digit| digit <= 9) =>
        {
            format!("KP_{}", &key_token[6..])
        }
        _ if key_token
            .strip_prefix('F')
            .and_then(|number| number.parse::<u8>().ok())
            .is_some_and(|number| (1..=35).contains(&number)) =>
        {
            key_token.to_string()
        }
        _ if key_token.len() == 1 && key_token.as_bytes()[0].is_ascii_alphanumeric() => {
            key_token.to_ascii_lowercase()
        }
        _ => return None,
    };
    let mut trigger = modifiers.join("+");
    if !trigger.is_empty() {
        trigger.push('+');
    }
    trigger.push_str(&key);
    Some(trigger)
}

#[cfg(all(test, target_os = "linux"))]
mod portal_shortcut_tests {
    use super::portal_preferred_trigger;

    #[test]
    fn maps_modifier_chords_to_portal_trigger_syntax() {
        assert_eq!(
            portal_preferred_trigger("CTRL+SHIFT+KeyA").as_deref(),
            Some("CTRL+SHIFT+a")
        );
        assert_eq!(
            portal_preferred_trigger("SUPER+ALT+F9").as_deref(),
            Some("LOGO+ALT+F9")
        );
        assert_eq!(
            portal_preferred_trigger("CTRL+Digit1").as_deref(),
            Some("CTRL+1")
        );
    }
}

#[cfg(target_os = "linux")]
#[tauri::command]
async fn set_wayland_global_shortcut(
    app: tauri::AppHandle,
    state: State<'_, PortalShortcutState>,
    shortcut: Option<String>,
) -> Result<Option<String>, String> {
    let previous = state
        .task
        .lock()
        .map_err(|_| "estado do atalho global indisponível".to_string())?
        .take();
    if let Some(previous) = previous {
        let _ = previous.cancel.send(());
        let _ = previous.join.await;
    }

    let Some(shortcut) = shortcut else {
        return Ok(None);
    };
    if !is_wayland_session() {
        return Err("o portal de atalhos só é usado em sessões Wayland".into());
    }

    use ashpd::desktop::global_shortcuts::{GlobalShortcuts, NewShortcut};

    const SHORTCUT_ID: &str = "com.cakesweet.voxcraft.toggle_bypass";
    let trigger = portal_preferred_trigger(&shortcut)
        .ok_or_else(|| "combinação não suportada pelo portal de atalhos".to_string())?;
    let portal = GlobalShortcuts::new()
        .await
        .map_err(|error| format!("não foi possível conectar ao portal de atalhos: {error}"))?;
    let session = portal
        .create_session(Default::default())
        .await
        .map_err(|error| format!("não foi possível criar a sessão do portal: {error}"))?;
    let mut activated = portal
        .receive_activated()
        .await
        .map_err(|error| format!("não foi possível ouvir ativações do portal: {error}"))?;
    let mut deactivated = portal
        .receive_deactivated()
        .await
        .map_err(|error| format!("não foi possível ouvir liberações do portal: {error}"))?;
    let mut shortcuts_changed = portal
        .receive_shortcuts_changed()
        .await
        .map_err(|error| format!("não foi possível ouvir mudanças de atalho do portal: {error}"))?;

    let definition = NewShortcut::new(
        SHORTCUT_ID,
        "Atalho do VoxCraft Studio para alternar a voz original",
    )
    .preferred_trigger(trigger.as_str());
    let binding = async {
        let request = portal
            .bind_shortcuts(&session, &[definition], None, Default::default())
            .await
            .map_err(|error| format!("não foi possível solicitar o atalho ao portal: {error}"))?;
        let response = request
            .response()
            .map_err(|error| format!("o portal não confirmou o atalho: {error}"))?;
        response
            .shortcuts()
            .iter()
            .find(|bound| bound.id() == SHORTCUT_ID)
            .map(|bound| bound.trigger_description().to_string())
            .ok_or_else(|| "o compositor não vinculou o atalho global solicitado".to_string())
    };
    let description = match binding.await {
        Ok(description) => description,
        Err(error) => {
            let _ = session.close().await;
            return Err(error);
        }
    };

    let (cancel, mut cancel_rx) = tokio::sync::oneshot::channel();
    let event_app = app.clone();
    let portal = Arc::new(portal);
    let session = Arc::new(session);
    let event_session = Arc::clone(&session);
    let join = tauri::async_runtime::spawn(async move {
        let session = event_session;
        let Ok(mut closed) = session.receive_closed().await else {
            emit_hotkey(&event_app, "Unavailable");
            let _ = session.close().await;
            return;
        };
        let cancelled = loop {
            tokio::select! {
                biased;
                _ = &mut cancel_rx => break true,
                _ = closed.next() => break false,
                event = activated.next() => match event {
                    Some(event) if event.shortcut_id() == SHORTCUT_ID => {
                        emit_hotkey(&event_app, "Pressed");
                    }
                    Some(_) => {}
                    None => break false,
                },
                event = deactivated.next() => match event {
                    Some(event) if event.shortcut_id() == SHORTCUT_ID => {
                        emit_hotkey(&event_app, "Released");
                    }
                    Some(_) => {}
                    None => break false,
                },
                event = shortcuts_changed.next() => match event {
                    Some(event) => {
                        if let Some(bound) = event.shortcuts().iter().find(|bound| bound.id() == SHORTCUT_ID) {
                            let _ = event_app.emit(
                                "voxcraft-global-hotkey",
                                json!({ "description": bound.trigger_description() }),
                            );
                        }
                    }
                    None => break false,
                },
            }
        };
        if !cancelled {
            emit_hotkey(&event_app, "Unavailable");
        }
        let _ = session.close().await;
    });

    *state
        .task
        .lock()
        .map_err(|_| "estado do atalho global indisponível".to_string())? =
        Some(PortalShortcutTask {
            cancel,
            join,
            portal,
            session,
        });
    Ok(Some(description))
}

#[cfg(not(target_os = "linux"))]
#[tauri::command]
fn set_wayland_global_shortcut(_shortcut: Option<String>) -> Result<Option<String>, String> {
    Err("o portal de atalhos Wayland só está disponível no Linux".into())
}

#[cfg(target_os = "linux")]
#[tauri::command]
async fn configure_wayland_global_shortcut(
    state: State<'_, PortalShortcutState>,
) -> Result<(), String> {
    let (portal, session) = state
        .task
        .lock()
        .map_err(|_| "estado do atalho global indisponível".to_string())?
        .as_ref()
        .map(|task| (Arc::clone(&task.portal), Arc::clone(&task.session)))
        .ok_or_else(|| "não há atalho global vinculado ao portal".to_string())?;
    portal
        .configure_shortcuts(&session, None, Default::default())
        .await
        .map_err(|error| format!("não foi possível abrir a configuração de atalhos: {error}"))
}

#[cfg(not(target_os = "linux"))]
#[tauri::command]
fn configure_wayland_global_shortcut() -> Result<(), String> {
    Err("o portal de atalhos Wayland só está disponível no Linux".into())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default();
    #[cfg(any(target_os = "macos", windows, target_os = "linux"))]
    let builder = if is_wayland_session() {
        builder
    } else {
        builder.plugin(tauri_plugin_global_shortcut::Builder::new().build())
    };
    let builder = builder
        .invoke_handler(tauri::generate_handler![
            get_runtime_status,
            core_request,
            updater::updater_is_configured,
            is_wayland_session,
            configure_native_hotkey,
            set_wayland_global_shortcut,
            configure_wayland_global_shortcut,
            updater::updater_target,
            updater::restart_app
        ])
        .setup(|app| {
            let core = Arc::new(CoreState::new());
            // The Windows updater clears Tauri resources before exiting to run NSIS.
            app.resources_table().add(CoreShutdown(Arc::clone(&core)));
            app.manage(core);
            #[cfg(target_os = "linux")]
            app.manage(PortalShortcutState::default());
            tray::setup(app)?;
            Ok(())
        });

    let app = updater::configure(builder)
        .build(tauri::generate_context!())
        .expect("erro ao iniciar VoxCraft Studio");
    app.run(|app_handle, event| {
        if matches!(event, tauri::RunEvent::Exit) {
            app_handle.state::<Arc<CoreState>>().shutdown();
            #[cfg(target_os = "linux")]
            app_handle.state::<PortalShortcutState>().shutdown();
        }
    });
}
