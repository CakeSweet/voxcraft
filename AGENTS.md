# Contexto do projeto — VoxCraft Studio

## Visão geral

Aplicativo desktop de modulação de voz em tempo real para Windows e Linux. O
motor DSP Python captura e processa o áudio localmente, roteando-o para um
dispositivo de saída — por exemplo, um cabo virtual usado por Discord, jogos ou
streaming. O shell desktop é Tauri 2; o frontend é Vite/JavaScript.

## Estrutura atual

- `internal/core/`: serviço headless Python.
  - `app.py`: entry point do serviço; inicia `src.backend.main`.
  - `src/backend.py`: estado do motor de áudio e API JSON Lines via stdin/stdout.
  - `src/audio_router.py`: enumeração de dispositivos e streams PortAudio, com
    fallback de configuração, resampling e monitoramento.
  - `src/dsp_engine.py`: `DSPParams` e cadeia DSP em tempo real com NumPy/SciPy.
  - `src/presets.py`: presets nativos e persistência de presets personalizados.
  - `requirements.txt`: dependências do core (`numpy`, `scipy`, `sounddevice`).
- `internal/client/`: aplicativo Tauri.
  - `index.html` e `index.css`: interface e estilos da bancada.
  - `src-front/`: controles DSP, roteamento, preferências e updater.
  - `src-back/src/lib.rs`: inicia/gerencia o processo Python, faz RPC JSON Lines
    e expõe comandos Tauri.
  - `src-back/tauri.conf.json`: configuração do bundle e endpoint do updater.
  - `src-back/capabilities/`: permissões da janela.
  - `public/`: arquivos copiados pelo Vite; os ícones do Tauri também ficam em
    `src-back/icons/`.
- `internal/client/public/assets/`: fontes e recursos estáticos do frontend
  Tauri; os ícones do bundle também ficam em `src-back/icons/`.
- `docs/`: site estático do projeto; `docs/assets/` contém as
  imagens e fontes usadas pelo site.
- `.github/workflows/release.yml`: automação de releases.
- `scripts/`: scripts Python de instalação, execução, checagem e build; os
  utilitários compartilhados ficam em `common.py`.

## Arquitetura e estado atual

- Em desenvolvimento, o Tauri inicia `internal/core/app.py` como processo
  filho. Em builds de release, usa o sidecar `voxcraft-core` incluído no
  pacote pelo PyInstaller. `VOXCRAFT_PYTHON` em desenvolvimento
  pode indicar o interpretador; sem essa variável, o Rust procura `python` no
  Windows ou `python3` nos demais sistemas.
- A comunicação usa uma requisição JSON por linha em stdin e uma resposta JSON
  correspondente em stdout, identificada por `id`. O stderr do processo é
  herdado para diagnóstico.
- `src/backend.py` mantém o `RealTimeDSPEngine`, o `AudioRouter`, os parâmetros
  e presets. A API interna inclui descoberta de dispositivos, parâmetros,
  presets, início/parada de áudio e medidores.
- `src-back/src/lib.rs` expõe `core_request` com allowlist. Ao adicionar ou
  renomear uma operação, atualize tanto o dispatch Python quanto essa allowlist.
- A bancada controla o core via RPC. A **Saída virtual** define o destino
  principal do áudio processado; não altere a saída padrão nem o volume do
  sistema. No Linux, se necessário, o core cria um sink temporário via `pactl`
  e o remove ao encerrar. **Escutar minha voz** monitora pela saída padrão sem
  duplicar o sinal quando os destinos coincidem. O atalho de voz original é
  global; em Wayland, o compositor pode solicitar autorização para vinculá-lo.
- Mantenha stdout do core reservado às respostas JSON Lines; logs e erros devem
  ir para stderr para não corromper o protocolo.
- O updater consulta `latest.json` no GitHub e instala pacotes assinados após
  confirmação. A pipeline publica NSIS, `.deb` e `.rpm` para x86-64.

## Desenvolvimento e verificações

Execute os comandos na raiz:

- `python scripts/install.py`: instala dependências Node com `npm ci`,
  cria `.venv` e instala `internal/core/requirements.txt`.
- `python scripts/dev.py`: inicia o aplicativo Tauri e passa o Python
  do ambiente `.venv` pelo `VOXCRAFT_PYTHON`.
- `python scripts/check.py`: compila os fontes Python, verifica a
  sintaxe JavaScript e executa `cargo check`/`cargo fmt --check`.
- `python -m unittest discover -s internal/core/tests -v`: executa os testes
  unitários/regressivos do roteamento de áudio.
- `python scripts/build.py`: compila para o sistema atual.
- `python scripts/build.py --target linux`: gera bundles `.deb` e `.rpm`.
- `python scripts/build.py --target windows`: gera bundle NSIS no Windows.
- `python scripts/build.py --target frontend`: compila somente o Vite.

Os alvos de build do Tauri que assinam/publicam updater exigem as variáveis
`UPDATER_PUBLIC_KEY` e `SIGNING_PRIVATE_KEY`; não grave chaves ou tokens no
repositório.

Os testes do core usam `unittest` e não precisam de uma dependência adicional.
`check` continua sendo uma verificação estática/compilação, não uma suíte de
testes funcionais; áudio e dispositivos exigem validação manual em um sistema
com os dispositivos apropriados. `python internal/core/app.py` inicia o
servidor JSON Lines e aguarda comandos em stdin; para abrir o aplicativo, use
`python scripts/dev.py`.

## Cuidados ao alterar

- Preserve o processamento em tempo real: evite operações bloqueantes, I/O de
  disco ou trabalho pesado no callback de áudio.
- Ao adicionar ou renomear parâmetros DSP, confira `DSPParams`, a cadeia em
  `RealTimeDSPEngine`, validação/serialização em `src/backend.py` e os presets.
- O frontend restaura do `localStorage` os ajustes de voz e o preset ativo, além
  de tema, idioma, dispositivos e atalho. O core não lê nem grava
  `voxcraft_config.json`. Apenas presets personalizados ficam em
  `user_presets.json`: na raiz gravável em dev e no diretório de configuração
  `VoxCraftStudio` em instalações. Não apague dados locais durante limpeza.
- Dinâmica & Ganho (ganhos, Noise Gate e Compressor) é global: não permita que
  presets salvem ou substituam esses campos. Voz Original ignora os efeitos,
  mas mantém os ganhos.
- A versão aparece em mais de um lugar: `internal/core/src/__init__.py`,
  `internal/client/package.json` e `package-lock.json`,
  `internal/client/src-back/Cargo.toml` e `Cargo.lock`,
  `internal/client/src-back/tauri.conf.json`, `docs/app.js` e os valores
  iniciais em `docs/index.html`. Confira a consistência ao preparar uma release.
- `node_modules/`, `dist/`, `target/`, caches Python e
  `internal/client/src-back/gen/` são dependências/artefatos gerados; não os
  trate como fonte de verdade.
- Não confunda `internal/client/public/assets/`,
  `docs/assets/` e os ícones de `internal/client/src-back/icons/`;
  são diretórios distintos.
- Faça mudanças localizadas e preserve modificações preexistentes no checkout.

## Releases

`.github/workflows/release.yml` publica por tags de versão e permite um build
manual sem publicar. `scripts/release.py`
valida a versão e só gera o `latest.json` se todos os pacotes e assinaturas
estiverem presentes.

O GitHub Pages publica o site estático de `main:/docs`. Preserve `docs/` e
`docs/.nojekyll` enquanto essa for a origem configurada no Pages.
