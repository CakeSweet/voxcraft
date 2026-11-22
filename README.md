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

**VoxCraft Studio** is a real-time voice modulator with a Tauri desktop interface and a Python audio/DSP core using `sounddevice`, `numpy`, and `scipy`.

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

Built-in voice presets plus custom presets saved locally. Input gain, output
volume, Noise Gate, and Compressor are global and stay unchanged when switching presets.

### Voice Shortcut

Switch between processed and original voice with a configurable key while the
VoxCraft window is focused. Choose **Toggle** or **Hold** in Settings.
Original Voice bypasses effects but keeps the configured gains.

## Installation

### Windows

1. Download `VoxCraftStudio_Setup_v<version>.exe` from [Releases](../../releases).
2. Run the installer and approve the Windows administrator prompt to install
   the required VB-Audio Virtual Cable. If approval is denied or installation
   fails, VoxCraft setup is canceled.
3. Launch **VoxCraft Studio**.

### Linux (`.deb` / `.rpm`)

1. Download the package matching your distro from the [Releases](../../releases) page, then install it:

   | Distro | Command |
   | --- | --- |
   | Debian / Ubuntu / Mint / Pop!_OS | `sudo apt install ./voxcraft-studio_<version>_amd64.deb` |
   | Fedora / RHEL / openSUSE | `sudo dnf install ./voxcraft-studio-<version>-1.x86_64.rpm` |

2. Launch **VoxCraft Studio** from your application menu or run:

   ```bash
    voxcraft-app
   ```

   With PipeWire/PulseAudio and `pactl` available, VoxCraft creates a temporary
   virtual sink for the current session if it cannot find one. This does not
   change the system's default output or volume.

## Routing to Discord & Games

On Windows, use [VB-Audio Virtual Cable](https://vb-audio.com/Cable).
On Linux, VoxCraft creates a virtual sink automatically when needed and when
PipeWire/PulseAudio is available through `pactl`. Select the sink's monitor
source as the input in Discord or the receiving app.

**Windows example:**

1. The VoxCraft installer installs VB-Audio Virtual Cable as a required
   component (and skips it if it is already installed).
2. In VoxCraft Studio:

| Setting | Value |
| --- | --- |
| **Microphone** | Your physical microphone |
| **Output** | `CABLE Input (VB-Audio Virtual Cable)` |
| **Hear my voice** | *Optional* — listen on the system's default output |

Then click **Start Audio**.

3. In Discord or your game:

- Set **Input Device** to `CABLE Output (VB-Audio Virtual Cable)`.

> 💡 **Tip:** disable Krisp / aggressive noise suppression in Discord if it clips your voice effects.

## Running from Source

```bash
python scripts/install.py
python scripts/dev.py
```

## Building Installers

### Windows

Requirements: Node.js, Rust/Tauri prerequisites, updater signing keys, and
Python dependencies installed with `python scripts/install.py`.

```bash
python scripts/build.py --target windows
```

The package includes the Python core.

### Linux (`.deb` & `.rpm`)

Requirements: Node.js, Rust/Tauri Linux prerequisites, `dpkg`, `rpm`, updater
signing keys, and Python dependencies installed with
`python scripts/install.py`.

```bash
python scripts/build.py --target linux
```


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

O **VoxCraft Studio** é um modulador de voz em tempo real com interface desktop Tauri e core de áudio/DSP em Python, usando `sounddevice`, `numpy` e `scipy`.

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
Ganho de Entrada, Volume de Saída, Noise Gate e Compressor são globais e não
mudam ao trocar de preset.

### Atalho de Voz

Alterne entre a voz com efeitos e a voz original usando uma tecla configurável
enquanto a janela do VoxCraft estiver focada. Escolha **Alternar** ou **Segurar**
em Configurações. Voz Original ignora os efeitos, mas mantém os ganhos configurados.

## Instalação

### Windows

1. Baixe `VoxCraftStudio_Setup_v<versão>.exe` na página de [Releases](../../releases).
2. Execute o instalador e autorize a solicitação de administrador do Windows
   para instalar o VB-Audio Virtual Cable obrigatório. Se a aprovação for
   negada ou a instalação falhar, a instalação do VoxCraft será cancelada.
3. Abra o **VoxCraft Studio**.

### Linux (`.deb` / `.rpm`)

1. Baixe o pacote compatível com a sua distribuição na página de [Releases](../../releases) e instale:

   | Distribuição | Comando |
   | --- | --- |
   | Debian / Ubuntu / Mint / Pop!_OS | `sudo apt install ./voxcraft-studio_<versão>_amd64.deb` |
   | Fedora / RHEL / openSUSE | `sudo dnf install ./voxcraft-studio-<versão>-1.x86_64.rpm` |

2. Abra o **VoxCraft Studio** pelo menu de aplicativos ou execute:

   ```bash
    voxcraft-app
   ```

   Com PipeWire/PulseAudio e `pactl` disponíveis, o VoxCraft cria um sink
   virtual temporário para a sessão se não encontrar um. Isso não altera a
   saída padrão nem o volume do sistema.

## Configuração no Discord e Jogos

No Windows, use o [VB-Audio Virtual Cable](https://vb-audio.com/Cable).
No Linux, o VoxCraft cria um sink virtual automaticamente quando necessário e
quando PipeWire/PulseAudio está disponível via `pactl`. No Discord ou no
aplicativo que recebe o áudio, selecione a fonte de monitoramento desse sink
como entrada.

**Exemplo no Windows:**

1. O instalador do VoxCraft instala o VB-Audio Virtual Cable como componente
   obrigatório (e não o reinstala se já estiver instalado).
2. No VoxCraft Studio:

| Opção | Valor |
| --- | --- |
| **Microfone** | Seu microfone físico |
| **Saída** | `CABLE Input (VB-Audio Virtual Cable)` |
| **Escutar minha voz** | *Opcional* — escute pela saída padrão do sistema |

Depois, clique em **Iniciar Áudio**.

3. No Discord ou no jogo:

- Defina o **Dispositivo de Entrada** como `CABLE Output (VB-Audio Virtual Cable)`.

> 💡 **Dica:** desative o Krisp no Discord caso ele esteja cortando os efeitos.

## Executar pelo Código-Fonte

```bash
python scripts/install.py
python scripts/dev.py
```

## Gerar Instaladores

### Windows

Requisitos: Node.js, Rust/pré-requisitos Tauri, chaves de assinatura do updater
e dependências Python instaladas com `python scripts/install.py`.

```bash
python scripts/build.py --target windows
```

O pacote inclui o core Python.

### Linux (`.deb` e `.rpm`)

Requisitos: Node.js, pré-requisitos Tauri para Linux, `dpkg`, `rpm`, chaves de
assinatura do updater e dependências Python instaladas com
`python scripts/install.py`.

```bash
python scripts/build.py --target linux
```
