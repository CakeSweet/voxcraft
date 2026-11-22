import { invoke } from "@tauri-apps/api/core";
import { check } from "@tauri-apps/plugin-updater";

const isTauriRuntime = () => "__TAURI_INTERNALS__" in window;

export function setupUpdater() {
    const status = document.querySelector("#update-status");
    const button = document.querySelector("#check-updates");
    let update = null;
    let isDownloaded = false;
    let busy = false;

    const setAction = (label, action) => {
        button.textContent = label;
        button.dataset.action = action;
    };

    async function checkForUpdates() {
        if (busy) return;

        if (!isTauriRuntime()) {
            status.textContent = "As atualizações ficam disponíveis na versão desktop.";
            setAction("Verificar agora", "check");
            return;
        }

        busy = true;
        button.disabled = true;
        status.textContent = "Verificando atualizações…";
        setAction("Verificando…", "check");

        try {
            if (!(await invoke("updater_is_configured"))) {
                update = null;
                status.textContent =
                    "O atualizador será habilitado nos builds assinados de produção.";
                setAction("Verificar novamente", "check");
                return;
            }

            const target = await invoke("updater_target");
            if (!target) {
                update = null;
                status.textContent =
                    "Atualizações automáticas estão disponíveis para instalações .deb e .rpm.";
                setAction("Verificar novamente", "check");
                return;
            }

            update = await check({ target });
            isDownloaded = false;

            if (!update) {
                status.textContent = "O VoxCraft Studio já está atualizado.";
                setAction("Verificar novamente", "check");
                return;
            }

            status.textContent = `A versão ${update.version} está disponível.`;
            setAction(`Baixar atualização ${update.version}`, "download");
        } catch (error) {
            status.textContent = `Não foi possível verificar atualizações: ${String(error)}`;
            setAction("Tentar novamente", "check");
        } finally {
            busy = false;
            button.disabled = false;
        }
    }

    async function downloadUpdate() {
        if (busy || !update) return;

        busy = true;
        button.disabled = true;

        try {
            let downloaded = 0;
            let contentLength = 0;
            status.textContent = `Baixando a versão ${update.version}…`;
            setAction("Baixando…", "download");

            await update.download((event) => {
                if (event.event === "Started") {
                    contentLength = event.data.contentLength ?? 0;
                } else if (event.event === "Progress") {
                    downloaded += event.data.chunkLength;
                    const percent = contentLength
                        ? ` (${Math.floor((downloaded / contentLength) * 100)}%)`
                        : "";
                    status.textContent = `Baixando a atualização${percent}…`;
                }
            });
            isDownloaded = true;
            status.textContent = `A versão ${update.version} foi baixada. Você pode instalar e reiniciar agora ou fechar para instalar depois.`;
            setAction("Instalar e reiniciar", "install");
        } catch (error) {
            status.textContent = `Não foi possível baixar a atualização: ${String(error)}`;
            setAction("Tentar baixar novamente", "download");
        } finally {
            busy = false;
            button.disabled = false;
        }
    }

    async function installUpdate() {
        if (busy || !update || !isDownloaded) return;

        busy = true;
        button.disabled = true;
        try {
            status.textContent = "Instalando a atualização…";
            setAction("Instalando…", "install");
            await update.install();
            status.textContent = "Atualização instalada. Reiniciando…";
            await invoke("restart_app");
        } catch (error) {
            status.textContent = `Não foi possível instalar a atualização: ${String(error)}`;
            setAction("Tentar instalar novamente", "install");
        } finally {
            busy = false;
            button.disabled = false;
        }
    }

    button.addEventListener("click", () => {
        if (button.dataset.action === "install") {
            void installUpdate();
        } else if (button.dataset.action === "download") {
            void downloadUpdate();
        } else {
            void checkForUpdates();
        }
    });

    status.textContent = "As atualizações são verificadas automaticamente ao iniciar.";
    setAction("Verificar agora", "check");

    if (import.meta.env.PROD) {
        const idleWindow = window;
        if (typeof idleWindow.requestIdleCallback === "function") {
            idleWindow.requestIdleCallback(() => void checkForUpdates(), {
                timeout: 4000,
            });
        } else {
            window.setTimeout(() => void checkForUpdates(), 1200);
        }
    }
}
