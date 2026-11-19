<div align="center">


<img src="https://i.ibb.co/4RSQm9Wp/voxcraft.png" alt="Voxcraft Icon" width="112" />

# VoxCraft Studio

**Real-time desktop voice modulator and DSP studio**
**Modulador de voz em tempo real e estúdio DSP para desktop**

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)

[🇺🇸 English](#-english) · [🇧🇷 Português](#-português)

</div>

---

# 🇺🇸 English

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Routing to Discord & Games](#routing-to-discord--games)
- [Running from Source](#running-from-source)
- [Building Installers](#building-installers)

## Overview

**VoxCraft Studio** is a real-time voice modulator and audio effects processor built with Python, `customtkinter`, `sounddevice`, `numpy`, and `scipy`.

It routes your physical microphone through a studio-grade DSP chain and sends the result straight into virtual audio cables (such as **VB-Audio Virtual Cable**), ready for Discord, games, streaming, and voice calls.

## Features

### Real-Time DSP Chain

| Module | What it includes |
| --- | --- |
| **Dynamics** | Input Gain, Noise Gate (with live status indicator), Compressor, Output Volume |
| **Pitch & Vocoder** | Pitch Shifter (semitones + fine tune), Frequency Shifter, multi-waveform Vocoder (Sine, Triangle, Square, Sawtooth, Chord, Whisper) |
| **Equalizer** | 5-Band EQ (`120 Hz`, `400 Hz`, `1.2 kHz`, `3.5 kHz`, `7.5 kHz`) + High-Pass (HPF) and Low-Pass (LPF) filters, with live frequency-response graph |
| **Modulation & FX** | Phaser, Wah-Wah, Chorus & Flanger, Tremolo, Ring Modulator (Robot), Distortion & Bitcrusher, Echo/Delay, Reverb |

### Presets

Built-in voice presets plus custom user presets saved locally.

### Global Hotkeys

Switch between the processed voice and a clean bypass from anywhere, even in full-screen games or while minimized to the system tray.

- Keyboard combinations
- **Mouse 4 / Mouse 5**
- **Toggle** or **Hold** mode

## Installation

### Windows

1. Download one of the following from the [Releases](../../releases) page (full version history is preserved there):
   - `VoxCraftStudio_Setup_v<version>.exe` — installer
   - `VoxCraftStudio_Portable_v<version>.exe` — portable
2. Run the installer and choose your language (**English** by default, **Português**, or **Español**).
3. Optionally check **Download and install VB-Audio Virtual Cable**.
4. Launch **VoxCraft Studio**.

### Linux (`.deb` / `.rpm`)

1. Download the package matching your distro from the [Releases](../../releases) page, then install it:

   | Distro | Command |
   | --- | --- |
   | Debian / Ubuntu / Mint / Pop!_OS | `sudo apt install ./voxcraft-studio_<version>_amd64.deb` |
   | Fedora / RHEL / openSUSE | `sudo dnf install ./voxcraft-studio-<version>-1.x86_64.rpm` |

2. Launch **VoxCraft Studio** from your application menu or run:

   ```bash
   voxcraft-studio
   ```

## Routing to Discord & Games

This setup uses [VB-Audio Virtual Cable](https://vb-audio.com/Cable) (`vb-audio.com/Cable`).

**1. Install** VB-Audio Virtual Cable.

**2. In VoxCraft Studio:**

| Setting | Value |
| --- | --- |
| **Microphone** | Your physical microphone |
| **Output** | `CABLE Input (VB-Audio Virtual Cable)` |
| **Hear my voice** | *Optional* — enable to test with your headphones |

Then click **Start Audio**.

**3. In Discord / your game:**

- Set **Input Device** to `CABLE Output (VB-Audio Virtual Cable)`.

> 💡 **Tip:** disable Krisp / aggressive noise suppression in Discord if it clips your voice effects.

## Running from Source

```bash
pip install -r requirements.txt
python app.py
```

## Building Installers

### Windows

Requirements: Python 3.11+, PyInstaller, and **Inno Setup 6**.

```bat
build_installer.bat
```

Output: `Output\VoxCraftStudio_Setup.exe`

### Linux (`.deb` & `.rpm`)

Requirements: Python 3.11+, PyInstaller, `portaudio19-dev`, `python3-tk`, `dpkg`, `rpm`.

```bash
chmod +x packaging/linux/build_linux_packages.sh
./packaging/linux/build_linux_packages.sh
```

Output:
- `Output/voxcraft-studio_<version>_amd64.deb`
- `Output/voxcraft-studio-<version>-1.x86_64.rpm`

---

# 🇧🇷 Português

## Sumário

- [Sobre o Programa](#sobre-o-programa)
- [Principais Recursos](#principais-recursos)
- [Instalação](#instalação)
- [Configuração no Discord e Jogos](#configuração-no-discord-e-jogos)
- [Executar pelo Código-Fonte](#executar-pelo-código-fonte)
- [Gerar Instaladores](#gerar-instaladores)

## Sobre o Programa

O **VoxCraft Studio** é um modulador de voz e processador de efeitos DSP em tempo real, feito com Python, `customtkinter`, `sounddevice`, `numpy` e `scipy`.

Ele roteia o seu microfone físico por uma cadeia de efeitos e envia o resultado diretamente para cabos de áudio virtuais (como o **VB-Audio Virtual Cable**), pronto para uso no Discord, jogos, lives e chamadas.

## Principais Recursos

### Cadeia DSP em Tempo Real

| Módulo | O que inclui |
| --- | --- |
| **Dinâmica** | Ganho de Entrada, Noise Gate (com indicador ao vivo), Compressor, Volume de Saída |
| **Tom & Vocoder** | Alterador de Tom / Pitch (semitons + ajuste fino), Frequency Shifter, Vocoder com múltiplas formas de onda (Senoide, Triangular, Quadrada, Dente de Serra, Acorde, Sussurro) |
| **Equalizador** | Equalizador de 5 bandas (`120 Hz`, `400 Hz`, `1.2 kHz`, `3.5 kHz`, `7.5 kHz`) + filtros Passa-Altas (HPF) e Passa-Baixas (LPF), com gráfico da curva de resposta ao vivo |
| **Modulação & Efeitos** | Phaser, Wah-Wah, Chorus & Flanger, Tremolo, Ring Modulator (Robô), Distorção & Bitcrusher, Eco/Delay, Reverb |

### Presets

Presets prontos e suporte para salvar e excluir vozes personalizadas.

### Atalhos Globais (Hotkeys)

Alterne entre a voz com efeito e a voz original limpa de qualquer lugar, inclusive em jogos em tela cheia ou com o programa minimizado na bandeja do sistema.

- Combinações de teclado
- **Mouse 4 / Mouse 5**
- Modo **Alternar** ou **Segurar**

## Instalação

### Windows

1. Baixe um dos arquivos abaixo na página de [Releases](../../releases) (com histórico completo de versões):
   - `VoxCraftStudio_Setup_v<versão>.exe` — instalador
   - `VoxCraftStudio_Portable_v<versão>.exe` — portátil
2. Execute o instalador e escolha o idioma (**English** por padrão, **Português** ou **Español**).
3. Se desejar, marque a opção **Baixar e instalar VB-Audio Virtual Cable**.
4. Abra o **VoxCraft Studio**.

### Linux (`.deb` / `.rpm`)

1. Baixe o pacote compatível com a sua distribuição na página de [Releases](../../releases) e instale:

   | Distribuição | Comando |
   | --- | --- |
   | Debian / Ubuntu / Mint / Pop!_OS | `sudo apt install ./voxcraft-studio_<versão>_amd64.deb` |
   | Fedora / RHEL / openSUSE | `sudo dnf install ./voxcraft-studio-<versão>-1.x86_64.rpm` |

2. Abra o **VoxCraft Studio** pelo menu de aplicativos ou execute:

   ```bash
   voxcraft-studio
   ```

## Configuração no Discord e Jogos

Esta configuração usa o [VB-Audio Virtual Cable](https://vb-audio.com/Cable) (`vb-audio.com/Cable`).

**1. Instale** o VB-Audio Virtual Cable.

**2. No VoxCraft Studio:**

| Opção | Valor |
| --- | --- |
| **Microfone** | Seu microfone físico |
| **Saída** | `CABLE Input (VB-Audio Virtual Cable)` |
| **Ouvir minha voz** | *Opcional* — ative apenas para testar nos fones |

Depois, clique em **Iniciar Áudio**.

**3. No Discord / Jogo:**

- Defina o **Dispositivo de Entrada** como `CABLE Output (VB-Audio Virtual Cable)`.

> 💡 **Dica:** desative o Krisp no Discord caso ele esteja cortando os efeitos.

## Executar pelo Código-Fonte

```bash
pip install -r requirements.txt
python app.py
```

## Gerar Instaladores

### Windows

Requisitos: Python 3.11+, PyInstaller e **Inno Setup 6**.

```bat
build_installer.bat
```

Saída: `Output\VoxCraftStudio_Setup.exe`

### Linux (`.deb` e `.rpm`)

Requisitos: Python 3.11+, PyInstaller, `portaudio19-dev`, `python3-tk`, `dpkg`, `rpm`.

```bash
chmod +x packaging/linux/build_linux_packages.sh
./packaging/linux/build_linux_packages.sh
```

Saída:
- `Output/voxcraft-studio_<versão>_amd64.deb`
- `Output/voxcraft-studio-<versão>-1.x86_64.rpm`
