# VoxCraft Studio

Real-time desktop voice modulator and DSP studio for Windows (with cross-platform Python source support).  
Modulador de voz em tempo real e estúdio DSP para desktop Windows (com suporte via código-fonte Python).

[English](#english) · [Português](#português)

---

## English

### Overview

**VoxCraft Studio** is a real-time voice modulator and audio effects processor built with Python, `customtkinter`, `sounddevice`, `numpy`, and `scipy`. It lets you route your physical microphone through a studio-grade DSP chain directly into virtual audio cables (such as **VB-Audio Virtual Cable**) for Discord, games, streaming, and voice calls.

### Key Features

- **Real-Time DSP Chain**:
  - **Dynamics**: Input Gain, Noise Gate with live status indicator, Compressor, and Output Volume.
  - **Pitch & Vocoder**: Pitch Shifter (semitones + fine tune), Frequency Shifter, and multi-waveform Vocoder (Sine, Triangle, Square, Sawtooth, Chord, Whisper).
  - **Equalizer**: 5-Band EQ (`120 Hz`, `400 Hz`, `1.2 kHz`, `3.5 kHz`, `7.5 kHz`) + High-Pass (HPF) & Low-Pass (LPF) filters with live frequency-response graph.
  - **Modulation & FX**: Phaser, Wah-Wah, Chorus & Flanger, Tremolo, Ring Modulator (Robot), Distortion & Bitcrusher, Echo/Delay, and Reverb.
- **Presets**: Built-in voice presets plus custom user presets (`★`) saved locally.
- **Global Hotkeys**: Switch between processed voice and clean bypass globally—even in full-screen games or when minimized to the system tray—supporting keyboard combinations and **Mouse 4 / Mouse 5** in Toggle or Hold mode.
- **Monitoring & Visualizers**: Optional headphone monitoring (`Hear my voice`), real-time Input/Output VU meters, and live waveform oscilloscope.
- **Themes, Languages & Startup**: Switch live in **Settings** between **Dark**, **Pure Dark (OLED)**, and **Light** themes, between **English**, **Português**, and **Español**, and toggle **Start with Windows** (or system autostart on Linux).
- **Single-Instance & System Tray**: Minimizes cleanly to the system tray; launching VoxCraft Studio again focuses the running window instead of spawning duplicate tray icons.
- **Built-in Updater**: Checks GitHub Releases by version (only downloading/restarting when a newer version exists) or installs from local `.exe` / `.zip` packages while keeping your audio devices, presets, and settings intact.

### Installation (Windows)

1. Download **`VoxCraftStudio_Setup_v<version>.exe`** (installer) or **`VoxCraftStudio_Portable_v<version>.exe`** (portable) from the **Releases** page (full version history is preserved on GitHub Releases).
2. Run the installer, select your preferred installer language (**English** by default, **Português**, or **Español**), optionally check **Download and install VB-Audio Virtual Cable**, and launch **VoxCraft Studio**.

### Installation (Linux `.deb` / `.rpm`)

1. Download the package matching your distro from the **Releases** page:
   - **Debian / Ubuntu / Mint / Pop!_OS**:
     ```bash
     sudo apt install ./voxcraft-studio_<version>_amd64.deb
     ```
   - **Fedora / RHEL / openSUSE**:
     ```bash
     sudo dnf install ./voxcraft-studio-<version>-1.x86_64.rpm
     ```
2. Launch **VoxCraft Studio** from your application menu or run `voxcraft-studio`.

### Discord & Games Routing (VB-Audio Virtual Cable)

1. Install **VB-Audio Virtual Cable** (`vb-audio.com/Cable`).
2. In **VoxCraft Studio**:
   - **Microphone**: select your physical microphone.
   - **Output**: select `CABLE Input (VB-Audio Virtual Cable)`.
   - Optionally enable **Hear my voice** to test using your headphones.
   - Click **Start Audio**.
3. In **Discord / Game**:
   - Set **Input Device** to `CABLE Output (VB-Audio Virtual Cable)`.
   - Tip: disable Krisp/aggressive noise suppression in Discord if it clips voice effects.

### Running from Source

```bash
pip install -r requirements.txt
python app.py
```

### Building Installers (Windows & Linux)

- **Windows** (Python 3.11+, PyInstaller, and **Inno Setup 6**):
  ```bat
  build_installer.bat
  ```
  Output: `Output\VoxCraftStudio_Setup.exe`.

- **Linux `.deb` & `.rpm`** (Python 3.11+, PyInstaller, `portaudio19-dev`, `python3-tk`, `dpkg`, `rpm`):
  ```bash
  chmod +x packaging/linux/build_linux_packages.sh
  ./packaging/linux/build_linux_packages.sh
  ```
  Output: `Output/voxcraft-studio_<version>_amd64.deb` and `Output/voxcraft-studio-<version>-1.x86_64.rpm`.

---

## Português

### Sobre o Programa

O **VoxCraft Studio** é um modulador de voz e processador de efeitos DSP em tempo real feito com Python, `customtkinter`, `sounddevice`, `numpy` e `scipy`. Ele permite rotear o seu microfone físico por uma cadeia de efeitos diretamente para cabos de áudio virtuais (como o **VB-Audio Virtual Cable**) para uso no Discord, jogos, lives e chamadas.

### Principais Recursos

- **Cadeia DSP em Tempo Real**:
  - **Dinâmica**: Ganho de Entrada, Noise Gate com indicador ao vivo, Compressor e Volume de Saída.
  - **Tom & Vocoder**: Alterador de Tom / Pitch (semitons + ajuste fino), Frequency Shifter e Vocoder com múltiplas formas de onda (Senoide, Triangular, Quadrada, Dente de Serra, Acorde e Sussurro).
  - **Equalizador**: Equalizador de 5 bandas (`120 Hz`, `400 Hz`, `1.2 kHz`, `3.5 kHz`, `7.5 kHz`) + filtros Passa-Altas (HPF) e Passa-Baixas (LPF) com gráfico da curva de resposta ao vivo.
  - **Modulação & Efeitos**: Phaser, Wah-Wah, Chorus & Flanger, Tremolo, Ring Modulator (Robô), Distorção & Bitcrusher, Eco/Delay e Reverb.
- **Presets**: Presets prontos e suporte para salvar/excluir vozes personalizadas (`★`).
- **Atalho Global (Hotkeys)**: Alterne entre a voz com efeito e a voz original limpa mesmo em jogos em tela cheia ou minimizado na bandeja do sistema, com suporte a combinações de teclado e **Mouse 4 / Mouse 5** no modo alternar ou segurar.
- **Monitoramento e Visualização**: Opção **Ouvir minha voz** nos fones, medidores VU de entrada/saída e osciloscópio em tempo real.
- **Temas, Idiomas e Inicialização**: Altere em **Configurações** entre os temas **Escuro (Dark)**, **Dark Puro (OLED)** e **Claro (Light)**, entre **Português**, **English** e **Español**, e ative ou desative **Iniciar com o Windows** (ou login automático no Linux).
- **Instância Única e Bandeja do Sistema**: Minimiza para a bandeja; abrir o VoxCraft Studio novamente restaura a janela já aberta em vez de duplicar o ícone na bandeja.
- **Atualizador Integrado**: Compara a versão instalada com a última Release no GitHub (só baixa e reinicia se houver uma versão mais recente) e preserva automaticamente seus dispositivos, presets e preferências.

### Instalação (Windows)

1. Baixe **`VoxCraftStudio_Setup_v<versão>.exe`** (instalador) ou **`VoxCraftStudio_Portable_v<versão>.exe`** (portátil) na página de **Releases** (com histórico completo de versões).
2. Execute o instalador, escolha o idioma desejado (**English** por padrão, **Português** ou **Español**), marque se desejar a opção **Baixar e instalar VB-Audio Virtual Cable** e abra o **VoxCraft Studio**.

### Instalação (Linux `.deb` / `.rpm`)

1. Baixe o pacote compatível com a sua distribuição na página de **Releases**:
   - **Debian / Ubuntu / Mint / Pop!_OS**:
     ```bash
     sudo apt install ./voxcraft-studio_<versão>_amd64.deb
     ```
   - **Fedora / RHEL / openSUSE**:
     ```bash
     sudo dnf install ./voxcraft-studio-<versão>-1.x86_64.rpm
     ```
2. Abra o **VoxCraft Studio** pelo menu de aplicativos ou execute `voxcraft-studio`.

### Configuração no Discord e Jogos (VB-Audio Virtual Cable)

1. Instale o **VB-Audio Virtual Cable** (`vb-audio.com/Cable`).
2. No **VoxCraft Studio**:
   - **Microfone**: selecione seu microfone físico.
   - **Saída**: selecione `CABLE Input (VB-Audio Virtual Cable)`.
   - Ative **Ouvir minha voz** apenas se quiser testar nos fones.
   - Clique em **Iniciar Áudio**.
3. No **Discord / Jogo**:
   - Defina o **Dispositivo de Entrada** como `CABLE Output (VB-Audio Virtual Cable)`.
   - Dica: desative o Krisp no Discord caso esteja cortando os efeitos.

### Executar pelo Código-Fonte

```bash
pip install -r requirements.txt
python app.py
```

### Gerar Instaladores (Windows e Linux)

- **Windows** (Python 3.11+, PyInstaller e **Inno Setup 6**):
  ```bat
  build_installer.bat
  ```
  Saída em `Output\VoxCraftStudio_Setup.exe`.

- **Linux `.deb` e `.rpm`** (Python 3.11+, PyInstaller, `portaudio19-dev`, `python3-tk`, `dpkg`, `rpm`):
  ```bash
  chmod +x packaging/linux/build_linux_packages.sh
  ./packaging/linux/build_linux_packages.sh
  ```
  Saída em `Output/voxcraft-studio_<versão>_amd64.deb` e `Output/voxcraft-studio-<versão>-1.x86_64.rpm`.
