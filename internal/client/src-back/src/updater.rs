fn public_key() -> Option<&'static str> {
    option_env!("UPDATER_PUBLIC_KEY").filter(|key| !key.trim().is_empty())
}

pub(super) fn configure(builder: tauri::Builder<tauri::Wry>) -> tauri::Builder<tauri::Wry> {
    match public_key() {
        Some(key) => builder.plugin(tauri_plugin_updater::Builder::new().pubkey(key).build()),
        None => builder,
    }
}

#[tauri::command]
pub(super) fn updater_is_configured() -> bool {
    public_key().is_some()
}

#[tauri::command]
pub(super) fn updater_target() -> Option<String> {
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
pub(super) fn restart_app(app: tauri::AppHandle) {
    app.restart();
}
