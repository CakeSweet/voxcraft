(() => {
  const REPO = "CakeSweet/voxcraft";
  const DEFAULT_VERSION = "2.1.0";

  const PRESET_GROUPS = [
    {
      title: { pt: "Limpeza, Estúdio & Modulação", en: "Clean, Studio & Modulation", es: "Estudio y Modulación" },
      items: [
        { name: "Normal", tag: "EQ · HPF · Comp" },
        { name: "Locutor / Podcast (Estúdio)", tag: "Broadcast EQ" },
        { name: "Voz Anônima (Entrevista)", tag: "-4 st · Freq Shift" },
        { name: "Coro Épico (Chorus + Reverb)", tag: "Chorus · Reverb" },
        { name: "Auto-Wah / Funk (Wahwah)", tag: "Auto-Wah · Chorus" },
        { name: "Flanger Metálico (Jato)", tag: "Flanger · 68% Fdbk" },
        { name: "Catedral / Deus Épico", tag: "-2 st · 95% Room" },
        { name: "Caverna / Eco Épico", tag: "330 ms Echo · Hall" },
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
        { name: "Alienígena (Freq Shifter)", tag: "-2 st · +145 Hz" },
        { name: "Tremolo Assombrado (Terror)", tag: "-2.5 st · 8.5 Hz" },
        { name: "Sussurro Fantasma (Vocoder)", tag: "Noise · 6-Stg Phaser" },
      ],
    },
    {
      title: { pt: "Sci-Fi, Rádio & Synth", en: "Sci-Fi, Radio & Synth", es: "Sci-Fi, Radio y Synth" },
      items: [
        { name: "Robô / Ciborgue", tag: "Ring Mod · 16 ms" },
        { name: "Vocoder Synth (Daft)", tag: "Chord Vocoder" },
        { name: "Phaser Espacial (Sci-Fi)", tag: "8-Stage Phaser" },
        { name: "Voz Subaquática (Tremolo + Wah)", tag: "LPF · Tremolo · Wah" },
        { name: "Megafone / Estádio", tag: "550–3200 Hz · Echo" },
        { name: "Rádio Militar / Walkie-Talkie", tag: "Bandpass · 10-bit" },
        { name: "Rádio AM Retrô (8-Bit Lo-Fi)", tag: "7-bit · Downsample" },
        { name: "Astronauta (Rádio Espacial)", tag: "Chorus · 12-bit" },
      ],
    },
  ];

  const COPY = {
    pt: {
      skip_content: "Pular para o conteúdo",
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
      hero_secondary_cta: "Explorar Cadeia DSP",
      spec_latency_label: "Bloco mínimo",
      spec_presets_label: "Presets nativos",
      spec_presets_val: "24 vozes + custom",
      spec_privacy_label: "Execução",
      spec_privacy_val: "100% local / offline",
      hero_caption: "WASAPI, DirectSound & PipeWire / ALSA",
      pipe_kicker: "01. Arquitetura de Áudio",
      pipe_title: "Projetado para voz limpa, baixa latência e controle total no desktop.",
      feat_1_title: "Cadeia DSP em tempo real sem dependências na nuvem",
      feat_1_desc:
        "Processamento em bloco contínuo com NumPy e SciPy: Noise Gate opcional, Compressor RMS, Pitch Shifter sem perda de cadência, Frequency Shifter, Vocoder com portadoras sintetizadas, Equalizador de 5 bandas com filtros HPF/LPF, Chorus/Flanger, Phaser multi-estágio, Auto-Wah, Ring Modulator, Distortion/Bitcrusher, Echo e Reverb Schroeder.",
      feat_1_meta: "Resampling automático entre dispositivos",
      feat_2_title: "Atalho Global Instantâneo",
      feat_2_desc:
        "Alterne entre voz modificada e voz natural com uma tecla ou botão lateral do mouse (como F9) no modo Alternar ou Segurar.",
      feat_3_title: "Roteamento para Discord, OBS e Jogos",
      feat_3_desc:
        "Envie sua voz processada para o VB-Cable no Windows ou sink virtual no Linux com monitoramento local separado nos seus fones via WASAPI, DirectSound e MME.",
      presets_kicker: "02. Biblioteca Nativa",
      presets_title: "24 presets prontos de fábrica e vozes personalizadas ilimitadas.",
      dl_kicker: "03. Instalação e Releases",
      dl_title: "Baixe a versão mais recente para o seu sistema.",
      dl_lead:
        "Cada release no GitHub publica instaladores versionados para Windows e pacotes nativos .deb e .rpm para distribuições Linux.",
      tab_source: "Código-Fonte",
      dl_all_releases: "Histórico de Releases",
      copy_cmd: "Copiar",
      copied_cmd: "Copiado",
      footer_note: "Modulador de voz desktop nativo em Python",
    },
    en: {
      skip_content: "Skip to content",
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
      hero_secondary_cta: "Explore DSP Chain",
      spec_latency_label: "Minimum buffer",
      spec_presets_label: "Factory presets",
      spec_presets_val: "24 voices + custom",
      spec_privacy_label: "Processing",
      spec_privacy_val: "100% local / offline",
      hero_caption: "WASAPI, DirectSound & PipeWire / ALSA",
      pipe_kicker: "01. Audio Architecture",
      pipe_title: "Engineered for clean voice routing, low latency, and desktop reliability.",
      feat_1_title: "Real-time DSP chain with zero cloud dependencies",
      feat_1_desc:
        "Continuous block processing via NumPy and SciPy: optional Noise Gate, RMS Compressor, Pitch Shifter, Frequency Shifter, synthesized-carrier Vocoder, 5-Band EQ with HPF/LPF, Chorus/Flanger, multi-stage Phaser, Auto-Wah, Ring Modulator, Distortion/Bitcrusher, Echo, and Schroeder Reverb.",
      feat_1_meta: "Automatic sample-rate resampling",
      feat_2_title: "Instant Global Hotkey",
      feat_2_desc:
        "Switch between modulated and natural voice with a key or side mouse button (such as F9) in Toggle or Hold mode.",
      feat_3_title: "Routing for Discord, OBS & Games",
      feat_3_desc:
        "Route processed voice into VB-Cable on Windows or virtual sinks on Linux with separate headphone monitoring over WASAPI, DirectSound, and MME.",
      presets_kicker: "02. Built-in Library",
      presets_title: "24 factory voice presets plus unlimited custom profiles.",
      dl_kicker: "03. Releases & Installation",
      dl_title: "Get the latest build for your operating system.",
      dl_lead:
        "Every GitHub release ships versioned Windows installers alongside native .deb and .rpm packages for Linux.",
      tab_source: "Source Code",
      dl_all_releases: "Release History",
      copy_cmd: "Copy",
      copied_cmd: "Copied",
      footer_note: "Native Python desktop voice modulator",
    },
    es: {
      skip_content: "Saltar al contenido",
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
      hero_secondary_cta: "Explorar Cadena DSP",
      spec_latency_label: "Bloque mínimo",
      spec_presets_label: "Presets incluidos",
      spec_presets_val: "24 voces + custom",
      spec_privacy_label: "Ejecución",
      spec_privacy_val: "100% local / offline",
      hero_caption: "WASAPI, DirectSound y PipeWire / ALSA",
      pipe_kicker: "01. Arquitectura de Audio",
      pipe_title: "Diseñado para voz limpia, baja latencia y estabilidad de escritorio.",
      feat_1_title: "Cadena DSP en tiempo real sin nube",
      feat_1_desc:
        "Procesamiento por bloques con NumPy y SciPy: Noise Gate opcional, Compresor RMS, Pitch Shifter, Frequency Shifter, Vocoder sintetizado, Ecualizador de 5 bandas con HPF/LPF, Chorus/Flanger, Phaser, Auto-Wah, Ring Modulator, Distortion/Bitcrusher, Echo y Reverb Schroeder.",
      feat_1_meta: "Resampling automático entre dispositivos",
      feat_2_title: "Atajo Global Instantáneo",
      feat_2_desc:
        "Alterna entre voz con efecto y voz natural con una tecla o botón lateral del ratón (como F9) en modo Alternar o Mantener.",
      feat_3_title: "Listo para Discord, OBS y Juegos",
      feat_3_desc:
        "Envía la voz procesada a VB-Cable en Windows o sinks virtuales en Linux con monitoreo independiente en tus auriculares vía WASAPI, DirectSound y MME.",
      presets_kicker: "02. Biblioteca Nativa",
      presets_title: "24 presets integrados y voces personalizadas ilimitadas.",
      dl_kicker: "03. Instalación y Releases",
      dl_title: "Descarga la versión más reciente para tu sistema.",
      dl_lead:
        "Cada release publica instaladores versionados para Windows y paquetes nativos .deb y .rpm para Linux.",
      tab_source: "Código Fuente",
      dl_all_releases: "Historial de Releases",
      copy_cmd: "Copiar",
      copied_cmd: "Copiado",
      footer_note: "Modulador de voz de escritorio nativo en Python",
    },
  };

  const state = {
    lang: "pt",
    theme: "dark",
    platform: "windows",
    version: DEFAULT_VERSION,
    tag: `v${DEFAULT_VERSION}`,
    assets: {},
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

  let copyTimer = null;

  function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    $$("[data-theme-choice]").forEach((btn) => {
      const active = btn.dataset.themeChoice === theme;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
    try {
      localStorage.setItem("voxcraft_pages_theme", theme);
    } catch {}
  }

  function applyLanguage(lang) {
    state.lang = lang;
    document.documentElement.lang = lang === "pt" ? "pt-BR" : lang;
    $$("[data-lang-choice]").forEach((btn) => {
      const active = btn.dataset.langChoice === lang;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
    $$("[data-i18n]").forEach((el) => {
      const k = el.getAttribute("data-i18n");
      if (k) el.textContent = t(k);
    });
    renderPresetShowcase();
    renderDownloadCard();
    try {
      localStorage.setItem("voxcraft_pages_lang", lang);
    } catch {}
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

    if (copyTimer) {
      clearTimeout(copyTimer);
      copyTimer = null;
    }
    copyBtn.textContent = t("copy_cmd");
    actionsEl.innerHTML = "";

    const debAsset = resolveAssetUrl("deb", `voxcraft-studio_${v}_amd64.deb`);
    const rpmAsset = resolveAssetUrl("rpm", `voxcraft-studio-${v}-1.x86_64.rpm`);

    const specs = {
      windows: {
        title: {
          pt: "Instalador Windows",
          en: "Windows Installer",
          es: "Instalador Windows",
        },
        meta: {
          pt: `${tag} · Windows 10 / 11 (x64)`,
          en: `${tag} · Windows 10 / 11 (x64)`,
          es: `${tag} · Windows 10 / 11 (x64)`,
        },
        desc: {
          pt: "Inclui o core de áudio. Para roteamento virtual no Discord ou OBS, instale o VB-Audio Virtual Cable separadamente.",
          en: "Includes the audio core. For virtual audio routing to Discord or OBS, install VB-Audio Virtual Cable separately.",
          es: "Incluye el motor de audio. Para el enrutamiento virtual en Discord u OBS, instala VB-Audio Virtual Cable por separado.",
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
          pt: "Empacotado com atalho no menu de aplicativos e ícone nativo para GNOME, KDE e XFCE.",
          en: "Packaged with desktop launcher entry and native icon for GNOME, KDE, and XFCE.",
          es: "Empaquetado con acceso directo en el menú de aplicaciones e icono nativo para GNOME, KDE y XFCE.",
        },
        buttons: [
          {
            primary: true,
            label: {
              pt: `Baixar ${debAsset.name}`,
              en: `Download ${debAsset.name}`,
              es: `Descargar ${debAsset.name}`,
            },
            asset: debAsset,
          },
        ],
        cmd: `sudo apt install ./${debAsset.name}`,
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
          pt: "Pacote desktop com core de áudio incluso, pronto para instalar via DNF com suporte a PipeWire/PulseAudio.",
          en: "Desktop package with the audio core included, ready to install with DNF on PipeWire or PulseAudio setups.",
          es: "Compilado de forma nativa para instalar con DNF sobre PipeWire o PulseAudio.",
        },
        buttons: [
          {
            primary: true,
            label: {
              pt: `Baixar ${rpmAsset.name}`,
              en: `Download ${rpmAsset.name}`,
              es: `Descargar ${rpmAsset.name}`,
            },
            asset: rpmAsset,
          },
        ],
        cmd: `sudo dnf install ./${rpmAsset.name}`,
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
        cmd: `git clone https://github.com/${REPO}.git && cd voxcraft && pip install -r internal/core/requirements.txt && python internal/core/app.py`,
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
        if (copyTimer) clearTimeout(copyTimer);
        $("#dlCopyBtn").textContent = t("copied_cmd");
        copyTimer = setTimeout(() => {
          $("#dlCopyBtn").textContent = t("copy_cmd");
          copyTimer = null;
        }, 1600);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initEvents();
    applyTheme(state.theme);
    applyLanguage(state.lang);
    syncLatestRelease();
  });
})();
