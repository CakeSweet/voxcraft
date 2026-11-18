import { useState } from "react";
import { usePWAInstall } from "../hooks/usePWAInstall";

export function PWAInstallButton() {
  const { isInstallable, isInstalled, isIOS, install } = usePWAInstall();
  const [showGuide, setShowGuide] = useState(false);

  if (isInstalled) {
    return null;
  }

  const handleClick = async () => {
    if (isInstallable) {
      await install();
      return;
    }
    setShowGuide(true);
  };

  return (
    <>
      <button
        type="button"
        className="btn btn-slate"
        onClick={() => void handleClick()}
        title="Instalar como aplicativo com ícone na barra de tarefas"
      >
        {isIOS ? "Instalar no iOS" : "Fixar na Barra / App"}
      </button>

      {showGuide && (
        <div className="modal-backdrop" onClick={() => setShowGuide(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Instalar na Barra de Tarefas (App)</h3>
            {isIOS ? (
              <p className="modal-body">
                {
                  "1. Toque no botão Compartilhar na barra do Safari.\n2. Role para baixo e toque em Adicionar à Tela de Início."
                }
              </p>
            ) : (
              <p className="modal-body">
                {
                  "Para ter o VoxCraft Studio com ícone próprio na Barra de Tarefas (Windows/macOS/Linux):\n\n1. Abra o app em uma aba própria no Chrome ou Edge (se estiver em modo preview/iframe, clique em abrir em nova aba).\n2. Clique no ícone de Instalação (+) na barra de endereços ou em Menu (⋮) > Salvar e compartilhar > Instalar VoxCraft Studio.\n3. Depois de instalado, clique com o botão direito no ícone na barra de tarefas e selecione 'Fixar na barra de tarefas'."
                }
              </p>
            )}
            <div className="modal-actions">
              <button type="button" className="btn btn-blue" onClick={() => setShowGuide(false)}>
                Entendi!
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
