import { currentMonitor, getCurrentWindow } from "@tauri-apps/api/window";

function occupiesWorkAreaAxis(size, monitor, isLinux) {
    if (!size || !monitor) return false;
    const workArea = monitor.workArea.size;
    const occupies = (length, available) => available > 0
        && length >= available - Math.max(16 * monitor.scaleFactor, isLinux ? available * 0.05 : 0);
    return occupies(size.width, workArea.width) || occupies(size.height, workArea.height);
}

export function setupWindowControls(translate) {
    if (!("__TAURI_INTERNALS__" in window)) {
        document.querySelector(".window-controls").hidden = true;
        document.querySelectorAll(".window-resize-handle").forEach((handle) => {
            handle.hidden = true;
        });
        return;
    }

    const appWindow = getCurrentWindow();
    const maximizeButton = document.querySelector("#window-maximize");
    const maximizeIcon = document.querySelector("#window-maximize-icon");
    const restoreIcon = document.querySelector("#window-restore-icon");
    const isLinux = navigator.platform.toLowerCase().startsWith("linux");
    let windowStateTimer;
    let windowStateQuery = 0;

    const hideWindow = () => {
        void appWindow.hide().catch((error) => console.error("Não foi possível ocultar a janela:", error));
    };

    const syncWindowState = async () => {
        const query = ++windowStateQuery;
        try {
            const [maximized, size, monitor] = await Promise.all([
                appWindow.isMaximized(),
                appWindow.outerSize().catch(() => null),
                currentMonitor().catch(() => null),
            ]);
            if (query !== windowStateQuery) return;
            document.documentElement.toggleAttribute("data-square-corners",
                maximized || occupiesWorkAreaAxis(size, monitor, isLinux));
            maximizeIcon.hidden = maximized;
            restoreIcon.hidden = !maximized;
            maximizeButton.dataset.windowControl = maximized ? "restore_window" : "maximize_window";
            maximizeButton.setAttribute("aria-label", translate(maximizeButton.dataset.windowControl));
        } catch (error) {
            console.error("Não foi possível consultar o estado da janela:", error);
        }
    };

    document.querySelector("#window-minimize").addEventListener("click", hideWindow);
    maximizeButton.addEventListener("click", () => {
        void appWindow.toggleMaximize()
            .then(syncWindowState)
            .catch((error) => console.error("Não foi possível maximizar/restaurar a janela:", error));
    });
    document.querySelector("#window-close").addEventListener("click", () => {
        void appWindow.close().catch((error) => console.error("Não foi possível fechar a janela:", error));
    });

    document.querySelectorAll("[data-window-resize]").forEach((handle) => {
        handle.addEventListener("pointerdown", (event) => {
            if (event.button !== 0) return;
            event.preventDefault();
            void appWindow.startResizeDragging(handle.dataset.windowResize)
                .catch((error) => console.error("Não foi possível redimensionar a janela:", error));
        });
    });

    const scheduleWindowStateSync = () => {
        window.clearTimeout(windowStateTimer);
        windowStateTimer = window.setTimeout(() => void syncWindowState(), 120);
    };
    void syncWindowState();
    void appWindow.onResized(scheduleWindowStateSync)
        .catch((error) => console.error("Não foi possível acompanhar o redimensionamento da janela:", error));
    void appWindow.onMoved(scheduleWindowStateSync)
        .catch((error) => console.error("Não foi possível acompanhar a posição da janela:", error));
}
