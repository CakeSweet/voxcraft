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
- **Themes & Languages**: Switch live in **Settings** between **Dark**, **Pure Dark (OLED)**, and **Light** themes, and between **English**, **Português**, and **Español**.
- **Built-in Updater**: Check and install new GitHub Releases (or local `.exe` / `.zip` packages) while keeping all audio devices, presets, and settings intact.

### Installation (Windows)

1. Download **`VoxCraftStudio_Setup.exe`** (installer) or **`VoxCraftStudio.exe`** (portable) from the **Releases** page.
2. Run the installer, choose your preferred installer language (**English**, **Português**, or **Español**), and launch **VoxCraft Studio**.

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

### Building the Windows Installer

Requires Python 3.11+, PyInstaller, and **Inno Setup 6**:

```bat
build_installer.bat
```

The compiled installer is output to `Output\VoxCraftStudio_Setup.exe`.

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
- **Temas e Idiomas**: Altere em **Configurações** entre os temas **Escuro (Dark)**, **Dark Puro (OLED)** e **Claro (Light)**, e entre os idiomas **Português**, **English** e **Español**.
- **Atualizador Integrado**: Baixe e instale atualizações do GitHub Releases (ou pacotes `.exe` / `.zip` locais) preservando automaticamente seus dispositivos, presets e preferências.

### Instalação (Windows)

1. Baixe **`VoxCraftStudio_Setup.exe`** (instalador) ou **`VoxCraftStudio.exe`** (portátil) na página de **Releases**.
2. Execute o instalador, escolha o idioma desejado na instalação (**English**, **Português** ou **Español**) e abra o **VoxCraft Studio**.

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

### Gerar o Instalador Windows

Requer Python 3.11+, PyInstaller e **Inno Setup 6**:

```bat
build_installer.bat
```

O instalador final será gerado em `Output\VoxCraftStudio_Setup.exe`.
