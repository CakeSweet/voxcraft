use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager,
};

#[cfg(target_os = "windows")]
fn restore_windows_window(window: &tauri::WebviewWindow) {
    let Ok(hwnd) = window.hwnd() else {
        return;
    };

    #[link(name = "user32")]
    extern "system" {
        fn IsIconic(h_wnd: isize) -> i32;
        fn ShowWindow(h_wnd: isize, n_cmd_show: i32) -> i32;
        fn SetForegroundWindow(h_wnd: isize) -> i32;
        fn RedrawWindow(
            h_wnd: isize,
            lprc_update: *const std::ffi::c_void,
            hrgn_update: isize,
            flags: u32,
        ) -> i32;
    }

    const SW_SHOW: i32 = 5;
    const SW_RESTORE: i32 = 9;
    const RDW_INVALIDATE: u32 = 0x0001;
    const RDW_ALLCHILDREN: u32 = 0x0080;
    const RDW_UPDATENOW: u32 = 0x0100;

    let raw_hwnd = hwnd.0 as isize;
    unsafe {
        if IsIconic(raw_hwnd) != 0 {
            let _ = ShowWindow(raw_hwnd, SW_RESTORE);
        } else {
            let _ = ShowWindow(raw_hwnd, SW_SHOW);
        }
        let _ = SetForegroundWindow(raw_hwnd);
        let _ = RedrawWindow(
            raw_hwnd,
            std::ptr::null(),
            0,
            RDW_INVALIDATE | RDW_UPDATENOW | RDW_ALLCHILDREN,
        );
    }
}

pub(super) fn show_main_window(app: &tauri::AppHandle) {
    let handle = app.clone();
    let _ = app.run_on_main_thread(move || {
        if let Some(window) = handle.get_webview_window("main") {
            if window.is_minimized().unwrap_or(false) {
                let _ = window.unminimize();
            }
            let _ = window.show();
            #[cfg(target_os = "windows")]
            restore_windows_window(&window);
            let _ = window.set_focus();
            let _ = handle.emit_to("main", "voxcraft-window-shown", ());
        }
    });
}

pub(super) fn setup(app: &tauri::AppHandle) -> tauri::Result<()> {
    if app.tray_by_id("voxcraft-tray").is_some() {
        return Ok(());
    }

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
                } | TrayIconEvent::DoubleClick {
                    button: MouseButton::Left,
                    ..
                }
            ) {
                show_main_window(tray.app_handle());
            }
        })
        .build(app)?;

    Ok(())
}
