(() => {
  const REPO = "CakeSweet/voxcraft";
  const DEFAULT_VERSION = "2.1.0";

  const PRESETS = [
    {
      id: "Normal",
      label: { pt: "Normal", en: "Normal", es: "Normal" },
      pitch: 0.0,
      hpf: 80,
      presence: 1.5,
      reverb: 0,
      comp: true,
      vocoder: false,
      dist: false,
      mod: false,
    },
    {
      id: "Locutor / Podcast (Estúdio)",
      label: {
        pt: "Locutor / Podcast (Estúdio)",
        en: "Broadcaster / Podcast (Studio)",
        es: "Locutor / Podcast (Estudio)",
      },
      pitch: 0.0,
      hpf: 75,
      presence: 3.0,
      reverb: 0,
      comp: true,
      vocoder: false,
      dist: false,
      mod: false,
    },
    {
      id: "Voz Grossa / Demônio",
      label: {
        pt: "Voz Grossa / Demônio",
        en: "Deep Voice / Demon",
        es: "Voz Grave / Demonio",
      },
      pitch: -5.5,
      hpf: 45,
      presence: -2.0,
      reverb: 32,
      comp: true,
      vocoder: false,
      dist: true,
      mod: false,
    },
    {
      id: "Monstro Abissal / Gigante",
      label: {
        pt: "Monstro Abissal / Gigante",
        en: "Abyssal Monster / Giant",
        es: "Monstruo Abisal / Gigante",
      },
      pitch: -8.0,
      hpf: 35,
      presence: -3.5,
      reverb: 45,
      comp: true,
      vocoder: false,
      dist: false,
      mod: true,
    },
    {
      id: "Robô / Ciborgue",
      label: {
        pt: "Robô / Ciborgue",
        en: "Robot / Cyborg",
        es: "Robot / Cíborg",
      },
      pitch: 0.0,
      hpf: 180,
      presence: 5.0,
      reverb: 18,
      comp: true,
      vocoder: false,
      dist: false,
      mod: true,
    },
    {
      id: "Vocoder Synth (Daft)",
      label: {
        pt: "Vocoder Synth (Daft)",
        en: "Vocoder Synth (Daft)",
        es: "Vocoder Synth (Daft)",
      },
      pitch: 0.0,
      hpf: 90,
      presence: 2.0,
      reverb: 22,
      comp: true,
      vocoder: true,
      dist: false,
      mod: true,
    },
    {
      id: "Rádio Militar / Walkie-Talkie",
      label: {
        pt: "Rádio Militar / Walkie-Talkie",
        en: "Military Radio / Walkie-Talkie",
        es: "Radio Militar / Walkie-Talkie",
      },
      pitch: 0.0,
      hpf: 390,
      presence: 8.5,
      reverb: 0,
      comp: true,
      vocoder: false,
      dist: true,
      mod: false,
    },
    {
      id: "Capacete / Darth Vader",
      label: {
        pt: "Capacete / Darth Vader",
        en: "Helmet / Darth Vader",
        es: "Casco / Darth Vader",
      },
      pitch: -3.5,
      hpf: 60,
      presence: 3.0,
      reverb: 28,
      comp: true,
      vocoder: false,
      dist: false,
      mod: false,
    },
  ];

  const PRESET_GROUPS = [
    {
      title: { pt: "Limpeza & Estúdio", en: "Clean & Broadcast", es: "Limpio y Estudio" },
      items: [
        { name: "Normal", tag: "EQ · HPF · Comp" },
        { name: "Locutor / Podcast (Estúdio)", tag: "Broadcast EQ" },
        { name: "Voz Anônima (Entrevista)", tag: "-4 st · Freq Shift" },
        { name: "Coro Épico (Chorus + Reverb)", tag: "Chorus · Reverb" },
      ],
    },
    {
      title: { pt: "Personagens & Criaturas", en: "Characters & Creatures", es: "Personajes y Criaturas" },
      items: [
        { name: "Voz Grossa / Demônio", tag: "-5.5 st · Drive" },
        { name: "Monstro Abissal / Gigante", tag: "-8.0 st · Hall" },
        { name: "Voz Fina / Esquilo", tag: "+6.5 st" },
        { name: "Duende / Goblin Travesso", tag: "+5.0 st · Tremolo" },
        { name: "Capacete / Darth Vader", tag: "-3.5 st · Echo" },
        { name: "Catedral / Deus Épico", tag: "Chorus · 95% Room" },
      ],
    },
    {
      title: { pt: "Sci-Fi, Rádio & Synth", en: "Sci-Fi, Radio & Synth", es: "Sci-Fi, Radio y Synth" },
      items: [
        { name: "Robô / Ciborgue", tag: "Ring Mod · 16 ms" },
        { name: "Vocoder Synth (Daft)", tag: "Chord Vocoder" },
        { name: "Sussurro Fantasma (Vocoder)", tag: "Noise · Phaser" },
        { name: "Phaser Espacial (Sci-Fi)", tag: "8-Stage Phaser" },
        { name: "Rádio Militar / Walkie-Talkie", tag: "Bandpass · 10-bit" },
        { name: "Astronauta (Rádio Espacial)", tag: "Chorus · 12-bit" },
      ],
    },
  ];

  const COPY = {
    pt: {
      skip_content: "Pular para o conteúdo",
      nav_studio: "Estúdio",
      nav_pipeline: "Cadeia DSP",
      nav_presets: "Presets",
      nav_download: "Download",
      nav_cta: "Baixar Agora",
      hero_os: "Windows & Linux (.deb / .rpm)",
      hero_license: "Open Source",
      hero_title: "Modulação de voz em tempo real com processamento DSP nativo.",
      hero_subtitle:
        "Transforme seu microfone no Discord, OBS ou jogos sem mensalidades, sem nuvem e com controle completo sobre Pitch, Vocoder, Equalizador de 5 bandas e dinâmica de estúdio.",
      hero_primary_cta: "Baixar VoxCraft Studio",
      hero_secondary_cta: "Explorar Painel DSP",
      spec_latency_label: "Bloco mínimo",
      spec_presets_label: "Presets nativos",
      spec_presets_val: "24 vozes + custom",
      spec_privacy_label: "Execução",
      spec_privacy_val: "100% local / offline",
      hero_caption: "WASAPI, DirectSound & PipeWire / ALSA",
      studio_kicker: "01. Prévia Interativa do Estúdio",
      studio_title: "Mesma paleta, mesmos efeitos, antes mesmo de instalar.",
      wb_preset_label: "Preset:",
      wb_bypass: "Voz Original",
      wb_audio_active: "Áudio Ativo",
      wb_audio_stopped: "Iniciar Áudio",
      wb_routing_title: "Roteamento de Áudio",
      wb_mic_label: "Microfone (Entrada)",
      wb_out_label: "Saída Processada",
      wb_active_chain: "Módulos Ativos",
      ctl_pitch: "Pitch (Semitons)",
      ctl_hpf: "Corte de Graves (HPF)",
      ctl_presence: "Presença Vocal (3 kHz)",
      ctl_reverb: "Espaço / Reverb Mix",
      canvas_eq_title: "Curva de Equalização (20 Hz – 20 kHz)",
      canvas_wave_title: "Osciloscópio de Saída",
      pipe_kicker: "02. Arquitetura de Áudio",
      pipe_title: "Projetado para voz limpa, baixa latência e controle total no desktop.",
      feat_1_title: "Cadeia DSP em tempo real sem dependências na nuvem",
      feat_1_desc:
        "Processamento em bloco contínuo com NumPy e SciPy: Noise Gate opcional, Compressor RMS, Pitch Shifter sem perda de cadência, Frequency Shifter, Vocoder com portadoras sintetizadas, Equalizador de 5 bandas com filtros HPF/LPF, Chorus/Flanger, Phaser multi-estágio, Auto-Wah, Ring Modulator, Distortion/Bitcrusher, Echo e Reverb Schroeder.",
      feat_1_meta: "Resampling automático entre dispositivos",
      feat_2_title: "Atalho Global Instantâneo",
      feat_2_desc:
        "Alterne entre voz modificada e voz natural com uma tecla (ex: F9 ou botões laterais do mouse) no modo Alternar ou Segurar para falar com efeito, sem cortes ou áudio preso ao soltar.",
      feat_3_title: "Roteamento para Discord, OBS e Jogos",
      feat_3_desc:
        "Envie sua voz processada para o VB-Cable no Windows ou sink virtual no Linux com monitoramento local separado nos seus fones e fallback automático de APIs (WASAPI, DirectSound e MME).",
      feat_4_title: "Experiência nativa no Windows e no Linux",
      feat_4_desc:
        "Suporte a instância única, inicialização automática com o sistema, bandeja do sistema, barra de janela personalizada no Linux (com Minimizar, Maximizar/Restaurar e Fechar) e atualizador integrado por releases versionadas no GitHub.",
      presets_kicker: "03. Biblioteca Nativa",
      presets_title: "24 presets prontos de fábrica e vozes personalizadas ilimitadas.",
      dl_kicker: "04. Instalação e Releases",
      dl_title: "Baixe a versão mais recente para o seu sistema.",
      dl_lead:
        "Cada release no GitHub publica instaladores versionados para Windows e pacotes nativos .deb e .rpm para distribuições Linux.",
      tab_source: "Código-Fonte",
      dl_all_releases: "Histórico de Releases",
      copy_cmd: "Copiar",
      copied_cmd: "Copiado",
      footer_note: "Modulador de voz desktop nativo em Python",
      chain_comp: "Compressor RMS",
      chain_pitch: "Pitch / Freq Shifter",
      chain_vocoder: "Vocoder Synth",
      chain_eq: "Equalizador 5 Bandas",
      chain_mod: "Chorus / Phaser / Ring",
      chain_dist: "Drive / Bitcrusher",
      chain_reverb: "Echo & Reverb",
      state_on: "Ativo",
      state_off: "Desligado",
      status_running: "Ativo: 48000 Hz | Bloco 512 (~10.7 ms)",
      status_bypass: "Ativo (Bypass): Voz Original sem efeitos",
      status_stopped: "Motor de áudio parado",
    },
    en: {
      skip_content: "Skip to content",
      nav_studio: "Studio",
      nav_pipeline: "DSP Chain",
      nav_presets: "Presets",
      nav_download: "Download",
      nav_cta: "Download Now",
      hero_os: "Windows & Linux (.deb / .rpm)",
      hero_license: "Open Source",
      hero_title: "Real-time voice modulation powered by a native DSP engine.",
      hero_subtitle:
        "Shape your microphone for Discord, OBS, and games without subscriptions or cloud delays. Full control over Pitch, Vocoder, 5-Band EQ, dynamics, and studio spaces.",
      hero_primary_cta: "Download VoxCraft Studio",
      hero_secondary_cta: "Explore DSP Workbench",
      spec_latency_label: "Minimum buffer",
      spec_presets_label: "Factory presets",
      spec_presets_val: "24 voices + custom",
      spec_privacy_label: "Processing",
      spec_privacy_val: "100% local / offline",
      hero_caption: "WASAPI, DirectSound & PipeWire / ALSA",
      studio_kicker: "01. Interactive Studio Preview",
      studio_title: "Same palette, same effects, right in your browser before installing.",
      wb_preset_label: "Preset:",
      wb_bypass: "Original Voice",
      wb_audio_active: "Audio Active",
      wb_audio_stopped: "Start Audio",
      wb_routing_title: "Audio Routing",
      wb_mic_label: "Microphone (Input)",
      wb_out_label: "Processed Output",
      wb_active_chain: "Active Modules",
      ctl_pitch: "Pitch (Semitones)",
      ctl_hpf: "Low-Cut Filter (HPF)",
      ctl_presence: "Vocal Presence (3 kHz)",
      ctl_reverb: "Space / Reverb Mix",
      canvas_eq_title: "EQ Frequency Response (20 Hz – 20 kHz)",
      canvas_wave_title: "Output Oscilloscope",
      pipe_kicker: "02. Audio Architecture",
      pipe_title: "Engineered for clean voice routing, low latency, and desktop reliability.",
      feat_1_title: "Real-time DSP chain with zero cloud dependencies",
      feat_1_desc:
        "Continuous block processing via NumPy and SciPy: optional Noise Gate, RMS Compressor, Pitch Shifter, Frequency Shifter, synthesized-carrier Vocoder, 5-Band EQ with HPF/LPF, Chorus/Flanger, multi-stage Phaser, Auto-Wah, Ring Modulator, Distortion/Bitcrusher, Echo, and Schroeder Reverb.",
      feat_1_meta: "Automatic sample-rate resampling",
      feat_2_title: "Instant Global Hotkey",
      feat_2_desc:
        "Switch between modulated and natural voice with a single key (such as F9 or side mouse buttons) in Toggle or Hold-to-Effect mode with clean buffer resets.",
      feat_3_title: "Routing for Discord, OBS & Games",
      feat_3_desc:
        "Route processed voice into VB-Cable on Windows or virtual sinks on Linux with separate headphone monitoring and automatic Host API fallback (WASAPI, DirectSound, MME).",
      feat_4_title: "Native experience on Windows and Linux",
      feat_4_desc:
        "Single-instance lock, OS autostart toggle, system tray support, custom Windows-style Linux title bar (Minimize, Maximize/Restore, Close), and built-in GitHub release updater.",
      presets_kicker: "03. Built-in Library",
      presets_title: "24 factory voice presets plus unlimited custom profiles.",
      dl_kicker: "04. Releases & Installation",
      dl_title: "Get the latest build for your operating system.",
      dl_lead:
        "Every GitHub release ships versioned Windows installers alongside native .deb and .rpm packages for Linux.",
      tab_source: "Source Code",
      dl_all_releases: "Release History",
      copy_cmd: "Copy",
      copied_cmd: "Copied",
      footer_note: "Native Python desktop voice modulator",
      chain_comp: "RMS Compressor",
      chain_pitch: "Pitch / Freq Shifter",
      chain_vocoder: "Synth Vocoder",
      chain_eq: "5-Band Equalizer",
      chain_mod: "Chorus / Phaser / Ring",
      chain_dist: "Drive / Bitcrusher",
      chain_reverb: "Echo & Reverb",
      state_on: "Active",
      state_off: "Off",
      status_running: "Active: 48000 Hz | Block 512 (~10.7 ms)",
      status_bypass: "Active (Bypass): Clean mic pass-through",
      status_stopped: "Audio engine stopped",
    },
    es: {
      skip_content: "Saltar al contenido",
      nav_studio: "Estudio",
      nav_pipeline: "Cadena DSP",
      nav_presets: "Presets",
      nav_download: "Descargar",
      nav_cta: "Descargar",
      hero_os: "Windows y Linux (.deb / .rpm)",
      hero_license: "Código Abierto",
      hero_title: "Modulación de voz en tiempo real con motor DSP nativo.",
      hero_subtitle:
        "Transforma tu micrófono en Discord, OBS o juegos sin suscripciones ni nube, con control total sobre Pitch, Vocoder, Ecualizador de 5 bandas y dinámica de estudio.",
      hero_primary_cta: "Descargar VoxCraft Studio",
      hero_secondary_cta: "Explorar Panel DSP",
      spec_latency_label: "Bloque mínimo",
      spec_presets_label: "Presets incluidos",
      spec_presets_val: "24 voces + custom",
      spec_privacy_label: "Ejecución",
      spec_privacy_val: "100% local / offline",
      hero_caption: "WASAPI, DirectSound y PipeWire / ALSA",
      studio_kicker: "01. Vista Previa del Estudio",
      studio_title: "Misma paleta y efectos directamente en el navegador antes de instalar.",
      wb_preset_label: "Preset:",
      wb_bypass: "Voz Original",
      wb_audio_active: "Audio Activo",
      wb_audio_stopped: "Iniciar Audio",
      wb_routing_title: "Enrutamiento de Audio",
      wb_mic_label: "Micrófono (Entrada)",
      wb_out_label: "Salida Procesada",
      wb_active_chain: "Módulos Activos",
      ctl_pitch: "Pitch (Semitonos)",
      ctl_hpf: "Filtro Paso Alto (HPF)",
      ctl_presence: "Presencia Vocal (3 kHz)",
      ctl_reverb: "Espacio / Reverb Mix",
      canvas_eq_title: "Curva de Ecualización (20 Hz – 20 kHz)",
      canvas_wave_title: "Osciloscopio de Salida",
      pipe_kicker: "02. Arquitectura de Audio",
      pipe_title: "Diseñado para voz limpia, baja latencia y estabilidad de escritorio.",
      feat_1_title: "Cadena DSP en tiempo real sin nube",
      feat_1_desc:
        "Procesamiento por bloques con NumPy y SciPy: Noise Gate opcional, Compresor RMS, Pitch Shifter, Frequency Shifter, Vocoder sintetizado, Ecualizador de 5 bandas con HPF/LPF, Chorus/Flanger, Phaser, Auto-Wah, Ring Modulator, Distortion/Bitcrusher, Echo y Reverb Schroeder.",
      feat_1_meta: "Resampling automático entre dispositivos",
      feat_2_title: "Atajo Global Instantáneo",
      feat_2_desc:
        "Alterna entre voz con efecto y voz natural con una tecla (como F9 o botones laterales del ratón) en modo Alternar o Mantener pulsado.",
      feat_3_title: "Listo para Discord, OBS y Juegos",
      feat_3_desc:
        "Envía la voz procesada a VB-Cable en Windows o sinks virtuales en Linux con monitoreo independiente y respaldo automático de APIs (WASAPI, DirectSound y MME).",
      feat_4_title: "Experiencia nativa en Windows y Linux",
      feat_4_desc:
        "Instancia única, inicio con el sistema, bandeja del sistema, barra de ventana propia para Linux (Minimizar, Maximizar/Restaurar y Cerrar) y actualizador por releases de GitHub.",
      presets_kicker: "03. Biblioteca Nativa",
      presets_title: "24 presets integrados y voces personalizadas ilimitadas.",
      dl_kicker: "04. Instalación y Releases",
      dl_title: "Descarga la versión más reciente para tu sistema.",
      dl_lead:
        "Cada release publica instaladores versionados para Windows y paquetes nativos .deb y .rpm para Linux.",
      tab_source: "Código Fuente",
      dl_all_releases: "Historial de Releases",
      copy_cmd: "Copiar",
      copied_cmd: "Copiado",
      footer_note: "Modulador de voz de escritorio nativo en Python",
      chain_comp: "Compresor RMS",
      chain_pitch: "Pitch / Freq Shifter",
      chain_vocoder: "Vocoder Synth",
      chain_eq: "Ecualizador 5 Bandas",
      chain_mod: "Chorus / Phaser / Ring",
      chain_dist: "Drive / Bitcrusher",
      chain_reverb: "Echo y Reverb",
      state_on: "Activo",
      state_off: "Apagado",
      status_running: "Activo: 48000 Hz | Bloque 512 (~10.7 ms)",
      status_bypass: "Activo (Bypass): Voz Original sin efectos",
      status_stopped: "Motor de audio detenido",
    },
  };

  const state = {
    lang: "pt",
    theme: "dark",
    platform: "windows",
    version: DEFAULT_VERSION,
    tag: `v${DEFAULT_VERSION}`,
    assets: {},
    presetIndex: 0,
    audioRunning: true,
    bypass: false,
    pitch: 0.0,
    hpf: 80,
    presence: 1.5,
    reverb: 0,
    phase: 0,
  };

  try {
    const savedTheme = localStorage.getItem("voxcraft_pages_theme");
    const savedLang = localStorage.getItem("voxcraft_pages_lang");
    if (savedTheme && ["dark", "oled", "light"].includes(savedTheme)) state.theme = savedTheme;
    if (savedLang && ["pt", "en", "es"].includes(savedLang)) state.lang = savedLang;
  } catch {
    // Ignora caso storage esteja restrito
  }

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  function t(key) {
    return (COPY[state.lang] && COPY[state.lang][key]) || COPY.pt[key] || key;
  }

  function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    $$("[data-theme-choice]").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.themeChoice === theme);
    });
    try {
      localStorage.setItem("voxcraft_pages_theme", theme);
    } catch {}
    drawEqCanvas();
    drawWaveFrame();
  }

  function applyLanguage(lang) {
    state.lang = lang;
    document.documentElement.lang = lang === "pt" ? "pt-BR" : lang;
    $$("[data-lang-choice]").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.langChoice === lang);
    });
    $$("[data-i18n]").forEach((el) => {
      const k = el.getAttribute("data-i18n");
      if (k) el.textContent = t(k);
    });
    populatePresetSelect();
    renderPresetShowcase();
    renderWorkbenchState();
    renderDownloadCard();
    try {
      localStorage.setItem("voxcraft_pages_lang", lang);
    } catch {}
  }

  function populatePresetSelect() {
    const sel = $("#wbPresetSelect");
    if (!sel) return;
    sel.innerHTML = "";
    PRESETS.forEach((p, idx) => {
      const opt = document.createElement("option");
      opt.value = String(idx);
      opt.textContent = p.label[state.lang] || p.label.pt;
      if (idx === state.presetIndex) opt.selected = true;
      sel.appendChild(opt);
    });
  }

  function selectPreset(index) {
    state.presetIndex = index;
    const p = PRESETS[index] || PRESETS[0];
    state.pitch = p.pitch;
    state.hpf = p.hpf;
    state.presence = p.presence;
    state.reverb = p.reverb;
    $("#sliderPitch").value = String(p.pitch);
    $("#sliderHpf").value = String(p.hpf);
    $("#sliderPresence").value = String(p.presence);
    $("#sliderReverb").value = String(p.reverb);
    renderWorkbenchState();
  }

  function renderWorkbenchState() {
    const p = PRESETS[state.presetIndex] || PRESETS[0];
    $("#valPitch").textContent = `${state.pitch > 0 ? "+" : ""}${state.pitch.toFixed(1)} st`;
    $("#valHpf").textContent = `${Math.round(state.hpf)} Hz`;
    $("#valPresence").textContent = `${state.presence > 0 ? "+" : ""}${state.presence.toFixed(1)} dB`;
    $("#valReverb").textContent = `${Math.round(state.reverb)}%`;
    $("#eqPeakBadge").textContent = `HPF ${Math.round(state.hpf)} Hz`;

    const bypassBtn = $("#wbBypassBtn");
    bypassBtn.setAttribute("aria-pressed", state.bypass ? "true" : "false");

    const powerBtn = $("#wbPowerBtn");
    powerBtn.setAttribute("aria-pressed", state.audioRunning ? "true" : "false");
    powerBtn.textContent = state.audioRunning ? t("wb_audio_active") : t("wb_audio_stopped");

    const statusEl = $("#wbStatusText");
    statusEl.classList.toggle("is-paused", !state.audioRunning);
    if (!state.audioRunning) {
      statusEl.textContent = t("status_stopped");
    } else if (state.bypass) {
      statusEl.textContent = t("status_bypass");
    } else {
      statusEl.textContent = t("status_running");
    }

    $("#waveModeBadge").textContent = !state.audioRunning ? "IDLE" : state.bypass ? "BYPASS" : "DSP";

    const chain = [
      { label: t("chain_comp"), on: !state.bypass && p.comp },
      { label: t("chain_pitch"), on: !state.bypass && Math.abs(state.pitch) >= 0.1 },
      { label: t("chain_vocoder"), on: !state.bypass && p.vocoder },
      { label: t("chain_eq"), on: !state.bypass },
      { label: t("chain_mod"), on: !state.bypass && p.mod },
      { label: t("chain_dist"), on: !state.bypass && p.dist },
      { label: t("chain_reverb"), on: !state.bypass && state.reverb > 0 },
    ];
    const listEl = $("#wbChainList");
    listEl.innerHTML = "";
    chain.forEach((item) => {
      const li = document.createElement("li");
      const nameSpan = document.createElement("span");
      nameSpan.textContent = item.label;
      const stSpan = document.createElement("span");
      stSpan.className = `chain-state ${item.on ? "on" : ""}`;
      stSpan.textContent = item.on ? t("state_on") : t("state_off");
      li.append(nameSpan, stSpan);
      listEl.appendChild(li);
    });

    drawEqCanvas();
    drawWaveFrame();
  }

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function drawEqCanvas() {
    const canvas = $("#eqCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    const padX = 36;
    const padY = 18;
    const gw = w - padX * 2;
    const gh = h - padY * 2;

    const bg = cssVar("--canvas");
    const gridLine = cssVar("--grid-line");
    const gridZero = cssVar("--grid-zero");
    const gridText = cssVar("--text-subtle");
    const accent = state.bypass ? cssVar("--warn") : cssVar("--accent");

    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    ctx.font = "10px 'JetBrains Mono', monospace";
    ctx.textBaseline = "middle";

    [-12, -6, 0, 6, 12].forEach((db) => {
      const y = padY + ((12 - db) / 24) * gh;
      ctx.strokeStyle = db === 0 ? gridZero : gridLine;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(padX, y);
      ctx.lineTo(w - padX, y);
      ctx.stroke();

      ctx.fillStyle = gridText;
      ctx.textAlign = "right";
      ctx.fillText(`${db > 0 ? "+" : ""}${db}`, padX - 6, y);
    });

    const fMin = 20;
    const fMax = 20000;
    const logSpan = Math.log10(fMax / fMin);

    [50, 120, 250, 500, 1000, 2000, 4000, 8000, 16000].forEach((freq) => {
      const x = padX + (Math.log10(freq / fMin) / logSpan) * gw;
      ctx.strokeStyle = gridLine;
      ctx.beginPath();
      ctx.moveTo(x, padY);
      ctx.lineTo(x, h - padY);
      ctx.stroke();

      ctx.fillStyle = gridText;
      ctx.textAlign = "center";
      ctx.fillText(freq >= 1000 ? `${freq / 1000}k` : String(freq), x, h - 6);
    });

    ctx.strokeStyle = accent;
    ctx.lineWidth = 2.4;
    ctx.beginPath();

    const samples = 140;
    for (let i = 0; i <= samples; i++) {
      const tNorm = i / samples;
      const freq = fMin * Math.pow(fMax / fMin, tNorm);
      let dbVal = 0;
      if (!state.bypass) {
        if (freq < state.hpf) {
          const ratio = Math.max(freq / state.hpf, 0.08);
          dbVal += 12 * Math.log2(ratio);
        }
        const octDiff = Math.log2(freq / 3000);
        dbVal += state.presence * Math.exp(-(octDiff * octDiff) / 0.72);
        const airShift = state.pitch < -2 ? -1.8 : state.pitch > 2 ? 1.6 : 0.8;
        const airOct = Math.log2(freq / 9000);
        dbVal += airShift * Math.exp(-(airOct * airOct) / 1.1);
      }
      dbVal = Math.max(-13, Math.min(13, dbVal));
      const x = padX + tNorm * gw;
      const y = padY + ((12 - dbVal) / 24) * gh;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  function drawWaveFrame() {
    const canvas = $("#waveCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    const mid = h / 2;

    const bg = cssVar("--canvas");
    const gridZero = cssVar("--grid-zero");
    const accent = state.bypass ? cssVar("--warn") : cssVar("--accent");

    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = gridZero;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, mid);
    ctx.lineTo(w, mid);
    ctx.stroke();

    if (!state.audioRunning) return;

    const p = PRESETS[state.presetIndex] || PRESETS[0];
    const freqScale = state.bypass ? 1.0 : Math.pow(2, state.pitch / 12);
    const amp = state.bypass ? 0.34 : 0.42;

    ctx.strokeStyle = accent;
    ctx.lineWidth = 2;
    ctx.beginPath();

    for (let x = 0; x <= w; x += 2) {
      const u = (x / w) * Math.PI * 6 * freqScale + state.phase;
      let sample = Math.sin(u) * 0.65 + Math.sin(u * 2.02) * 0.25 + Math.sin(u * 3.1) * 0.1;
      if (!state.bypass && p.dist) {
        sample = Math.tanh(sample * 2.3);
      }
      if (!state.bypass && p.vocoder) {
        sample = Math.sign(sample) * Math.pow(Math.abs(sample), 0.7) * 0.85;
      }
      const env = 0.55 + 0.45 * Math.sin((x / w) * Math.PI);
      const y = mid - sample * env * (mid - 14) * amp * 1.45;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  function renderPresetShowcase() {
    const grid = $("#presetShowcaseGrid");
    if (!grid) return;
    grid.innerHTML = "";
    PRESET_GROUPS.forEach((group) => {
      const card = document.createElement("article");
      card.className = "preset-cat-card";
      const h3 = document.createElement("h3");
      h3.textContent = group.title[state.lang] || group.title.pt;
      const ul = document.createElement("ul");
      ul.className = "preset-items";
      group.items.forEach((it) => {
        const li = document.createElement("li");
        const n = document.createElement("span");
        n.textContent = it.name;
        const tag = document.createElement("span");
        tag.className = "preset-tag mono";
        tag.textContent = it.tag;
        li.append(n, tag);
        ul.appendChild(li);
      });
      card.append(h3, ul);
      grid.appendChild(card);
    });
  }

  function resolveAssetUrl(prefix, fallbackName) {
    const found = state.assets[prefix];
    if (found && found.url) return found;
    return {
      name: fallbackName,
      url: `https://github.com/${REPO}/releases/latest/download/${fallbackName}`,
    };
  }

  function renderDownloadCard() {
    const v = state.version;
    const tag = state.tag;
    const plat = state.platform;

    const headingEl = $("#dlHeading");
    const metaEl = $("#dlMetaLine");
    const descEl = $("#dlDescription");
    const actionsEl = $("#dlActionButtons");
    const cmdCodeEl = $("#dlCmdCode");
    const copyBtn = $("#dlCopyBtn");

    copyBtn.textContent = t("copy_cmd");
    actionsEl.innerHTML = "";

    const specs = {
      windows: {
        title: {
          pt: "Instalador Windows + Executável Portátil",
          en: "Windows Installer + Portable Executable",
          es: "Instalador Windows + Ejecutable Portátil",
        },
        meta: {
          pt: `${tag} · Windows 10 / 11 (x64)`,
          en: `${tag} · Windows 10 / 11 (x64)`,
          es: `${tag} · Windows 10 / 11 (x64)`,
        },
        desc: {
          pt: "O instalador oficial inclui opção integrada para instalar o VB-Audio Virtual Cable caso ainda não o possua para usar no Discord ou OBS.",
          en: "The official installer includes an optional step to install VB-Audio Virtual Cable for Discord, OBS, or games.",
          es: "El instalador oficial incluye opción para instalar VB-Audio Virtual Cable automáticamente para Discord u OBS.",
        },
        buttons: [
          {
            primary: true,
            label: {
              pt: `Baixar Setup v${v} (.exe)`,
              en: `Download Setup v${v} (.exe)`,
              es: `Descargar Setup v${v} (.exe)`,
            },
            asset: resolveAssetUrl("VoxCraftStudio_Setup", `VoxCraftStudio_Setup_v${v}.exe`),
          },
          {
            primary: false,
            label: {
              pt: `Baixar Portátil v${v} (.exe)`,
              en: `Download Portable v${v} (.exe)`,
              es: `Descargar Portátil v${v} (.exe)`,
            },
            asset: resolveAssetUrl("VoxCraftStudio_Portable", `VoxCraftStudio_Portable_v${v}.exe`),
          },
        ],
        cmd: "winget install VB-Audio.VBCABLE  # opcional para roteamento virtual",
      },
      deb: {
        title: {
          pt: "Pacote Linux Debian / Ubuntu (.deb)",
          en: "Debian / Ubuntu Linux Package (.deb)",
          es: "Paquete Linux Debian / Ubuntu (.deb)",
        },
        meta: {
          pt: `${tag} · amd64 · libportaudio2`,
          en: `${tag} · amd64 · libportaudio2`,
          es: `${tag} · amd64 · libportaudio2`,
        },
        desc: {
          pt: "Empacotado com atalho no menu de aplicativos, ícone e barra de janela própria para GNOME, KDE e XFCE.",
          en: "Includes desktop launcher entry, icon, and custom Windows-style window controls for GNOME, KDE, and XFCE.",
          es: "Incluye entrada de menú, icono y barra de ventana propia para GNOME, KDE y XFCE.",
        },
        buttons: [
          {
            primary: true,
            label: {
              pt: `Baixar voxcraft-studio_${v}_amd64.deb`,
              en: `Download voxcraft-studio_${v}_amd64.deb`,
              es: `Descargar voxcraft-studio_${v}_amd64.deb`,
            },
            asset: resolveAssetUrl("deb", `voxcraft-studio_${v}_amd64.deb`),
          },
        ],
        cmd: `sudo apt install ./voxcraft-studio_${v}_amd64.deb`,
      },
      rpm: {
        title: {
          pt: "Pacote Linux Fedora / RHEL / openSUSE (.rpm)",
          en: "Fedora / RHEL / openSUSE Package (.rpm)",
          es: "Paquete Linux Fedora / RHEL / openSUSE (.rpm)",
        },
        meta: {
          pt: `${tag} · x86_64 · portaudio`,
          en: `${tag} · x86_64 · portaudio`,
          es: `${tag} · x86_64 · portaudio`,
        },
        desc: {
          pt: "Compilado nativamente com PyInstaller e pronto para instalar via DNF com suporte a PipeWire/PulseAudio.",
          en: "Built natively with PyInstaller and ready to install with DNF on PipeWire or PulseAudio setups.",
          es: "Compilado de forma nativa para instalar con DNF sobre PipeWire o PulseAudio.",
        },
        buttons: [
          {
            primary: true,
            label: {
              pt: `Baixar voxcraft-studio-${v}-1.x86_64.rpm`,
              en: `Download voxcraft-studio-${v}-1.x86_64.rpm`,
              es: `Descargar voxcraft-studio-${v}-1.x86_64.rpm`,
            },
            asset: resolveAssetUrl("rpm", `voxcraft-studio-${v}-1.x86_64.rpm`),
          },
        ],
        cmd: `sudo dnf install ./voxcraft-studio-${v}-1.x86_64.rpm`,
      },
      source: {
        title: {
          pt: "Execução Direta via Python 3.10+",
          en: "Run Directly from Python 3.10+ Source",
          es: "Ejecución Directa desde Python 3.10+",
        },
        meta: {
          pt: `${tag} · Python · NumPy / SciPy / CustomTkinter`,
          en: `${tag} · Python · NumPy / SciPy / CustomTkinter`,
          es: `${tag} · Python · NumPy / SciPy / CustomTkinter`,
        },
        desc: {
          pt: "Clone o repositório oficial, instale as dependências de requirements.txt e execute o aplicativo diretamente.",
          en: "Clone the official repository, install requirements.txt dependencies, and launch the studio directly.",
          es: "Clona el repositorio oficial, instala las dependencias y ejecuta la aplicación directamente.",
        },
        buttons: [
          {
            primary: true,
            label: {
              pt: "Abrir Repositório no GitHub",
              en: "Open GitHub Repository",
              es: "Abrir Repositorio en GitHub",
            },
            asset: { url: `https://github.com/${REPO}` },
          },
        ],
        cmd: `git clone https://github.com/${REPO}.git && cd voxcraft && pip install -r requirements.txt && python app.py`,
      },
    };

    const cfg = specs[plat] || specs.windows;
    headingEl.textContent = cfg.title[state.lang] || cfg.title.pt;
    metaEl.textContent = cfg.meta[state.lang] || cfg.meta.pt;
    descEl.textContent = cfg.desc[state.lang] || cfg.desc.pt;
    cmdCodeEl.textContent = cfg.cmd;

    cfg.buttons.forEach((b) => {
      const a = document.createElement("a");
      a.href = b.asset.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.className = b.primary ? "btn btn-primary" : "btn btn-secondary";
      a.textContent = b.label[state.lang] || b.label.pt;
      actionsEl.appendChild(a);
    });
  }

  async function syncLatestRelease() {
    try {
      const res = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`, {
        headers: { Accept: "application/vnd.github+json" },
      });
      if (!res.ok) return;
      const data = await res.json();
      if (!data || !data.tag_name) return;
      const tag = String(data.tag_name).trim();
      const ver = tag.replace(/^v/i, "");
      const mapped = {};
      (data.assets || []).forEach((asset) => {
        const name = String(asset.name || "");
        const url = String(asset.browser_download_url || "");
        if (!url) return;
        if (name.includes("Setup") && name.endsWith(".exe")) mapped.VoxCraftStudio_Setup = { name, url };
        else if (name.includes("Portable") && name.endsWith(".exe")) mapped.VoxCraftStudio_Portable = { name, url };
        else if (name.endsWith(".deb")) mapped.deb = { name, url };
        else if (name.endsWith(".rpm")) mapped.rpm = { name, url };
      });
      state.tag = tag;
      state.version = ver;
      state.assets = mapped;
      const verEl = $("#releaseVersionText");
      if (verEl) verEl.textContent = tag;
      const relLink = $("#dlReleaseTagLink");
      if (relLink && data.html_url) relLink.href = data.html_url;
      renderDownloadCard();
    } catch {
      // Mantém versão padrão v2.1.0 caso a API esteja indisponível offline
    }
  }

  function initEvents() {
    const mobileBtn = $("#mobileMenuBtn");
    const mobileDrawer = $("#mobileDrawer");
    if (mobileBtn && mobileDrawer) {
      mobileBtn.addEventListener("click", () => {
        const open = mobileDrawer.hidden;
        mobileDrawer.hidden = !open;
        mobileBtn.setAttribute("aria-expanded", open ? "true" : "false");
      });
      mobileDrawer.querySelectorAll("a").forEach((a) => {
        a.addEventListener("click", () => {
          mobileDrawer.hidden = true;
          mobileBtn.setAttribute("aria-expanded", "false");
        });
      });
    }

    $$("[data-theme-choice]").forEach((btn) => {
      btn.addEventListener("click", () => applyTheme(btn.dataset.themeChoice));
    });

    $$("[data-lang-choice]").forEach((btn) => {
      btn.addEventListener("click", () => applyLanguage(btn.dataset.langChoice));
    });

    $("#wbPresetSelect").addEventListener("change", (e) => {
      selectPreset(Number(e.target.value) || 0);
    });

    $("#wbBypassBtn").addEventListener("click", () => {
      state.bypass = !state.bypass;
      renderWorkbenchState();
    });

    $("#wbPowerBtn").addEventListener("click", () => {
      state.audioRunning = !state.audioRunning;
      renderWorkbenchState();
    });

    $("#sliderPitch").addEventListener("input", (e) => {
      state.pitch = Number(e.target.value);
      renderWorkbenchState();
    });
    $("#sliderHpf").addEventListener("input", (e) => {
      state.hpf = Number(e.target.value);
      renderWorkbenchState();
    });
    $("#sliderPresence").addEventListener("input", (e) => {
      state.presence = Number(e.target.value);
      renderWorkbenchState();
    });
    $("#sliderReverb").addEventListener("input", (e) => {
      state.reverb = Number(e.target.value);
      renderWorkbenchState();
    });

    $$(".plat-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        state.platform = tab.dataset.platform;
        $$(".plat-tab").forEach((tEl) => {
          const active = tEl === tab;
          tEl.classList.toggle("active", active);
          tEl.setAttribute("aria-selected", active ? "true" : "false");
        });
        renderDownloadCard();
      });
    });

    $("#dlCopyBtn").addEventListener("click", async () => {
      const text = $("#dlCmdCode").textContent || "";
      let copied = false;
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text);
          copied = true;
        }
      } catch {
        copied = false;
      }
      if (!copied) {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        try {
          copied = document.execCommand("copy");
        } catch {
          copied = false;
        }
        document.body.removeChild(ta);
      }
      if (copied) {
        $("#dlCopyBtn").textContent = t("copied_cmd");
        setTimeout(() => {
          $("#dlCopyBtn").textContent = t("copy_cmd");
        }, 1600);
      }
    });

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!reduceMotion.matches) {
      let lastTick = 0;
      const tick = (ts) => {
        if (ts - lastTick >= 45) {
          lastTick = ts;
          if (state.audioRunning) {
            state.phase = (state.phase + 0.16) % (Math.PI * 200);
            drawWaveFrame();
          }
        }
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    populatePresetSelect();
    initEvents();
    applyTheme(state.theme);
    applyLanguage(state.lang);
    selectPreset(0);
    syncLatestRelease();
  });
})();
