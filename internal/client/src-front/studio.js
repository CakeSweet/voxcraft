import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { setupHotkeyFeedback } from "./hotkey-feedback.js";
import { setupUpdater } from "./updates.js";
import { setupWindowControls } from "./window-controls.js";

const TEXT = {
    pt: {
        cancel: "Cancelar", notice: "Aviso",
        preset: "Preset", current_config: "Configuração atual", save: "Salvar", delete: "Excluir",
        settings: "Configurações", update: "Atualizar", original_voice: "Voz Original",
        start_audio: "Iniciar Áudio", stop_audio: "Parar Áudio", audio_section: "Áudio", microphone: "Microfone",
        output: "Destino da voz filtrada", status_label: "Status", monitor_voice: "Escutar minha voz",
        latency: "Latência", lat_ultra: "Ultra (256)", lat_low: "Baixa (512)", lat_stable: "Estável (1024)",
        refresh_devices: "Atualizar Dispositivos",
        loading_devices: "Listando dispositivos…", stopped: "Parado", hotkey_section: "Atalho", enable_hotkey: "Ativar atalho",
        define_key: "Definir atalho",
        hotkey_local_only: "Atalho global indisponível. Funciona apenas com a janela focada.",
        hold_key: "Segurar tecla", levels_section: "Níveis", input_lbl: "Entrada", output_lbl: "Saída",
        gate_open: "● Noise Gate: Aberto", gate_closed: "● Noise Gate: Silenciado",
        dynamics_section: "Dinâmica & Ganho", input_gain: "Ganho de Entrada", noise_gate: "Noise Gate",
        gate_thresh: "Limite do Gate", compressor: "Compressor", comp_thresh: "Limite Compressor", output_vol: "Volume de Saída",
        tab_pitch: "Tom & Vocoder", tab_eq: "Equalizador", tab_mod: "Modulação", tab_fx: "Robô & Distorção",
        tab_space: "Eco & Reverb", tab_mixer: "Mixer", pitch_shift: "Alterar Tom (Pitch)", semitones: "Semitons",
        fine_tune: "Ajuste Fino", mix: "Mistura", freq_shift: "Frequency Shifter", shift_hz: "Deslocamento",
        vocoder: "Vocoder", carrier: "Portadora", base_freq: "Frequência Base", smoothness: "Suavidade",
        equalizer: "Equalizador", reset_eq: "Zerar EQ", eq_flat: "EQ Desativado (Flat)", hpf: "Passa-Altas (HPF)",
        lpf: "Passa-Baixas (LPF)", frequency: "Frequência", eq_b1: "Grave\n120 Hz", eq_b2: "Méd-Grave\n400 Hz",
        eq_b3: "Presença\n1.2 kHz", eq_b4: "Brilho\n3.5 kHz", eq_b5: "Agudo\n7.5 kHz",
        phaser: "Phaser", wah: "Wah-Wah", stages: "Estágios", lfo_speed: "Velocidade LFO", depth: "Profundidade",
        feedback: "Feedback", lfo_freq: "Frequência LFO", resonance: "Ressonância (Q)",
        chorus_flanger: "Chorus & Flanger", base_delay: "Atraso Base", modulation: "Modulação",
        waveform: "Forma de Onda", intensity: "Intensidade", tremolo: "Tremolo",
        ring_mod: "Ring Modulator (Robô)", ring_mod_short: "Ring Modulator", carrier_freq: "Frequência Portadora",
        dist_bit: "Distorção & Bitcrusher", drive_sat: "Drive / Saturação", resolution: "Resolução",
        downsample: "Downsample", echo_delay: "Eco / Delay", delay: "Atraso", echo_vol: "Volume do Eco",
        reverb: "Reverb", room_size: "Tamanho da Sala", damping: "Abafamento", effects_chain: "Cadeia de Efeitos",
        reset_effects: "Resetar Efeitos", wave_sine: "Senoide", wave_tri: "Triangular", wave_sq: "Quadrada",
        wave_saw: "Dente de Serra", wave_chord: "Acorde", wave_whisper: "Sussurro (Ruído)",
        settings_title: "Configurações", appearance_section: "Aparência", theme_label: "Tema", theme_dark: "Escuro (Dark)",
        theme_oled: "Dark Puro (OLED)", theme_light: "Claro (Light)", language_label: "Idioma", close: "Fechar",
        minimize_window: "Minimizar", maximize_window: "Maximizar", restore_window: "Restaurar",
        close_window: "Fechar janela",
        upd_header: "Atualização do VoxCraft Studio", upd_check_btn: "Verificar",
        no_devices: "Nenhum dispositivo encontrado", audio_starting: "Iniciando áudio…", audio_started: "Áudio ativo",
        devices_refreshed: "Dispositivos atualizados.", core_unavailable: "Core Python indisponível",
        core_starting: "Preparando o motor de áudio…",
        browser_mode: "Abra pelo Tauri para controlar o core Python.", save_preset_prompt: "Nome para este preset:",
        delete_preset_confirm: "Excluir o preset personalizado “{name}”?", preset_saved: "Preset salvo.",
        preset_deleted: "Preset excluído.", only_custom_delete: "Somente presets personalizados podem ser excluídos.",
        audio_error: "Erro ao iniciar o áudio", key_capture: "Pressione a combinação… (Esc cancela)",
        reset_confirm: "Restaurar todos os efeitos para o preset Normal?", current_audio: "Configuração atual",
        start_required_devices: "Selecione uma entrada de áudio.",
        no_virtual_output: "Nenhum destino virtual detectado",
        virtual_output_required: "O destino virtual da voz filtrada não está disponível. O áudio não pode ser iniciado.",
        configure_virtual_output: "Configurar microfone virtual",
        virtual_output_setup_failed: "Não foi possível configurar a rota de áudio virtual automaticamente.",
        virtual_microphone_setup_failed: "O microfone virtual CABLE Output não está disponível. O áudio não pode ser iniciado.",
    },
    en: {
        cancel: "Cancel", notice: "Notice",
        preset: "Preset", current_config: "Current configuration", save: "Save", delete: "Delete",
        settings: "Settings", update: "Update", original_voice: "Original Voice",
        start_audio: "Start Audio", stop_audio: "Stop Audio", audio_section: "Audio", microphone: "Microphone",
        output: "Filtered voice destination", status_label: "Status", monitor_voice: "Hear my voice",
        latency: "Latency", lat_ultra: "Ultra (256)", lat_low: "Low (512)", lat_stable: "Stable (1024)",
        refresh_devices: "Refresh Devices",
        loading_devices: "Listing devices…", stopped: "Stopped", hotkey_section: "Hotkey", enable_hotkey: "Enable hotkey",
        define_key: "Set shortcut",
        hotkey_local_only: "Global shortcut unavailable. It only works while the window is focused.",
        hold_key: "Hold key", levels_section: "Levels", input_lbl: "Input", output_lbl: "Output",
        gate_open: "● Noise Gate: Open", gate_closed: "● Noise Gate: Muted",
        dynamics_section: "Dynamics & Gain", input_gain: "Input Gain", noise_gate: "Noise Gate",
        gate_thresh: "Gate Threshold", compressor: "Compressor", comp_thresh: "Compressor Threshold", output_vol: "Output Volume",
        tab_pitch: "Pitch & Vocoder", tab_eq: "Equalizer", tab_mod: "Modulation", tab_fx: "Robot & Distortion",
        tab_space: "Echo & Reverb", tab_mixer: "Mixer", pitch_shift: "Pitch Shifter", semitones: "Semitones",
        fine_tune: "Fine Tune", mix: "Mix", freq_shift: "Frequency Shifter", shift_hz: "Shift",
        vocoder: "Vocoder", carrier: "Carrier", base_freq: "Base Frequency", smoothness: "Smoothness",
        equalizer: "Equalizer", reset_eq: "Reset EQ", eq_flat: "EQ Disabled (Flat)", hpf: "High-Pass (HPF)",
        lpf: "Low-Pass (LPF)", frequency: "Frequency", eq_b1: "Bass\n120 Hz", eq_b2: "Low-Mid\n400 Hz",
        eq_b3: "Presence\n1.2 kHz", eq_b4: "Brilliance\n3.5 kHz", eq_b5: "Treble\n7.5 kHz",
        phaser: "Phaser", wah: "Wah-Wah", stages: "Stages", lfo_speed: "LFO Speed", depth: "Depth",
        feedback: "Feedback", lfo_freq: "LFO Frequency", resonance: "Resonance (Q)",
        chorus_flanger: "Chorus & Flanger", base_delay: "Base Delay", modulation: "Modulation",
        waveform: "Waveform", intensity: "Intensity", tremolo: "Tremolo",
        ring_mod: "Ring Modulator (Robot)", ring_mod_short: "Ring Modulator", carrier_freq: "Carrier Frequency",
        dist_bit: "Distortion & Bitcrusher", drive_sat: "Drive / Saturation", resolution: "Resolution",
        downsample: "Downsample", echo_delay: "Echo / Delay", delay: "Delay", echo_vol: "Echo Level",
        reverb: "Reverb", room_size: "Room Size", damping: "Damping", effects_chain: "Effects Chain",
        reset_effects: "Reset Effects", wave_sine: "Sine", wave_tri: "Triangle", wave_sq: "Square",
        wave_saw: "Sawtooth", wave_chord: "Chord", wave_whisper: "Whisper (Noise)",
        settings_title: "Settings", appearance_section: "Appearance", theme_label: "Theme", theme_dark: "Dark",
        theme_oled: "Pure Dark (OLED)", theme_light: "Light", language_label: "Language", close: "Close",
        minimize_window: "Minimize", maximize_window: "Maximize", restore_window: "Restore",
        close_window: "Close window",
        upd_header: "VoxCraft Studio Update", upd_check_btn: "Check",
        no_devices: "No devices found", audio_starting: "Starting audio…", audio_started: "Audio active",
        devices_refreshed: "Devices updated.", core_unavailable: "Python core unavailable",
        core_starting: "Preparing the audio engine…",
        browser_mode: "Open the Tauri app to control the Python core.", save_preset_prompt: "Name this preset:",
        delete_preset_confirm: "Delete custom preset “{name}”?", preset_saved: "Preset saved.",
        preset_deleted: "Preset deleted.", only_custom_delete: "Only custom presets can be deleted.",
        audio_error: "Audio start error", key_capture: "Press a shortcut… (Esc cancels)",
        reset_confirm: "Reset all effects to the Normal preset?", current_audio: "Current configuration",
        start_required_devices: "Select an input device.",
        no_virtual_output: "No virtual output detected",
        virtual_output_required: "The virtual destination for processed voice is unavailable. Audio cannot start.",
        configure_virtual_output: "Configure virtual microphone",
        virtual_output_setup_failed: "Could not configure the virtual audio route automatically.",
        virtual_microphone_setup_failed: "The CABLE Output virtual microphone is unavailable. Audio cannot start.",
    },
    es: {
        cancel: "Cancelar", notice: "Aviso",
        preset: "Preset", current_config: "Configuración actual", save: "Guardar", delete: "Eliminar",
        settings: "Configuración", update: "Actualizar", original_voice: "Voz Original",
        start_audio: "Iniciar Audio", stop_audio: "Detener Audio", audio_section: "Audio", microphone: "Micrófono",
        output: "Destino de la voz filtrada", status_label: "Estado", monitor_voice: "Escuchar mi voz",
        latency: "Latencia", lat_ultra: "Ultra (256)", lat_low: "Baja (512)", lat_stable: "Estable (1024)",
        refresh_devices: "Actualizar Dispositivos",
        loading_devices: "Listando dispositivos…", stopped: "Detenido", hotkey_section: "Atajo", enable_hotkey: "Activar atajo",
        define_key: "Asignar atajo",
        hotkey_local_only: "Atajo global no disponible. Solo funciona con la ventana enfocada.",
        hold_key: "Mantener tecla", levels_section: "Niveles", input_lbl: "Entrada", output_lbl: "Salida",
        gate_open: "● Noise Gate: Abierto", gate_closed: "● Noise Gate: Silenciado",
        dynamics_section: "Dinámica y Ganancia", input_gain: "Ganancia de Entrada", noise_gate: "Noise Gate",
        gate_thresh: "Umbral del Gate", compressor: "Compresor", comp_thresh: "Umbral del Compresor", output_vol: "Volumen de Salida",
        tab_pitch: "Tono y Vocoder", tab_eq: "Ecualizador", tab_mod: "Modulación", tab_fx: "Robot y Distorsión",
        tab_space: "Eco y Reverb", tab_mixer: "Mezclador", pitch_shift: "Cambiar Tono (Pitch)", semitones: "Semitonos",
        fine_tune: "Ajuste Fino", mix: "Mezcla", freq_shift: "Frequency Shifter", shift_hz: "Desplazamiento",
        vocoder: "Vocoder", carrier: "Portadora", base_freq: "Frecuencia Base", smoothness: "Suavidad",
        equalizer: "Ecualizador", reset_eq: "Reiniciar EQ", eq_flat: "EQ Desactivado (Plano)", hpf: "Pasa-Altos (HPF)",
        lpf: "Pasa-Bajos (LPF)", frequency: "Frecuencia", eq_b1: "Graves\n120 Hz", eq_b2: "Med-Graves\n400 Hz",
        eq_b3: "Presencia\n1.2 kHz", eq_b4: "Brillo\n3.5 kHz", eq_b5: "Agudos\n7.5 kHz",
        phaser: "Phaser", wah: "Wah-Wah", stages: "Etapas", lfo_speed: "Velocidad LFO", depth: "Profundidad",
        feedback: "Feedback", lfo_freq: "Frecuencia LFO", resonance: "Resonancia (Q)",
        chorus_flanger: "Chorus y Flanger", base_delay: "Retardo Base", modulation: "Modulación",
        waveform: "Forma de Onda", intensity: "Intensidad", tremolo: "Tremolo",
        ring_mod: "Ring Modulator (Robot)", ring_mod_short: "Ring Modulator", carrier_freq: "Frecuencia Portadora",
        dist_bit: "Distorsión y Bitcrusher", drive_sat: "Drive / Saturación", resolution: "Resolución",
        downsample: "Downsample", echo_delay: "Eco / Delay", delay: "Retardo", echo_vol: "Volumen del Eco",
        reverb: "Reverb", room_size: "Tamaño de Sala", damping: "Amortiguación", effects_chain: "Cadena de Efectos",
        reset_effects: "Reiniciar Efectos", wave_sine: "Senoidal", wave_tri: "Triangular", wave_sq: "Cuadrada",
        wave_saw: "Diente de Sierra", wave_chord: "Acorde", wave_whisper: "Susurro (Ruido)",
        settings_title: "Configuración", appearance_section: "Apariencia", theme_label: "Tema", theme_dark: "Oscuro (Dark)",
        theme_oled: "Dark Puro (OLED)", theme_light: "Claro (Light)", language_label: "Idioma", close: "Cerrar",
        minimize_window: "Minimizar", maximize_window: "Maximizar", restore_window: "Restaurar",
        close_window: "Cerrar ventana",
        upd_header: "Actualización de VoxCraft Studio", upd_check_btn: "Verificar",
        no_devices: "No se encontraron dispositivos", audio_starting: "Iniciando audio…", audio_started: "Audio activo",
        devices_refreshed: "Dispositivos actualizados.", core_unavailable: "Core Python no disponible",
        core_starting: "Preparando el motor de audio…",
        browser_mode: "Abre la aplicación Tauri para controlar el core Python.", save_preset_prompt: "Nombre para este preset:",
        delete_preset_confirm: "¿Eliminar el preset personalizado “{name}”?", preset_saved: "Preset guardado.",
        preset_deleted: "Preset eliminado.", only_custom_delete: "Solo se pueden eliminar presets personalizados.",
        audio_error: "Error al iniciar el audio", key_capture: "Pulsa la combinación… (Esc cancela)",
        reset_confirm: "¿Restablecer todos los efectos al preset Normal?", current_audio: "Configuración actual",
        start_required_devices: "Selecciona una entrada de audio.",
        no_virtual_output: "No se detectó una salida virtual",
        virtual_output_required: "El destino virtual de la voz procesada no está disponible. No se puede iniciar el audio.",
        configure_virtual_output: "Configurar micrófono virtual",
        virtual_output_setup_failed: "No se pudo configurar automáticamente la ruta de audio virtual.",
        virtual_microphone_setup_failed: "El micrófono virtual CABLE Output no está disponible. No se puede iniciar el audio.",
    },
};

const PARAMS_DEFAULT = {
    bypass: false, input_gain_db: 0, output_gain_db: 0, gate_enabled: true, gate_threshold_db: -44,
    comp_enabled: true, comp_threshold_db: -18, pitch_enabled: false, pitch_semitones: 0, pitch_cents: 0,
    pitch_mix: 1, freq_shift_enabled: false, freq_shift_hz: 0, freq_shift_mix: 1, vocoder_enabled: false,
    vocoder_carrier: "Dente de Serra", vocoder_freq_hz: 110, vocoder_smooth: 0.45, vocoder_mix: 0.85,
    eq_enabled: true, eq_hpf_enabled: true, eq_hpf_hz: 80, eq_lpf_enabled: false, eq_lpf_hz: 12000,
    eq_band1_db: 0, eq_band2_db: 0, eq_band3_db: 0, eq_band4_db: 0, eq_band5_db: 0,
    chorus_enabled: false, chorus_rate_hz: 1.2, chorus_delay_ms: 14, chorus_depth_ms: 4.5,
    chorus_feedback: 0.25, chorus_mix: 0.5, phaser_enabled: false, phaser_stages: 6,
    phaser_freq_hz: 0.8, phaser_depth: 0.7, phaser_feedback: 0.45, phaser_mix: 0.6,
    wah_enabled: false, wah_freq_hz: 1.5, wah_depth: 0.75, wah_resonance: 2.8, wah_mix: 0.75,
    tremolo_enabled: false, tremolo_freq_hz: 6, tremolo_waveform: "Senoide", tremolo_depth: 0.65,
    ring_enabled: false, ring_freq_hz: 60, ring_waveform: "Senoide", ring_mix: 0.7,
    dist_enabled: false, dist_drive: 3, dist_bits: 16, dist_downsample: 1, dist_mix: 0.7,
    echo_enabled: false, echo_delay_ms: 220, echo_feedback: 0.35, echo_mix: 0.35,
    reverb_enabled: false, reverb_room: 0.6, reverb_damp: 0.45, reverb_mix: 0.3,
};

const slider = (param, label, min, max, step, unit, factor = 1, integer = false) => ({
    kind: "slider", param, label, min, max, step, unit, factor, integer,
});
const selector = (param, label, options) => ({ kind: "select", param, label, options });
const waveOptions = [
    { value: "Senoide", label: "wave_sine" },
    { value: "Triangular", label: "wave_tri" },
    { value: "Quadrada", label: "wave_sq" },
    { value: "Dente de Serra", label: "wave_saw" },
];

const GROUPS = {
    pitch: [
        {
            title: "pitch_shift", toggle: "pitch_enabled",
            controls: [
                slider("pitch_semitones", "semitones", -12, 12, 0.1, "st"),
                slider("pitch_cents", "fine_tune", -100, 100, 1, "ct"),
                slider("pitch_mix", "mix", 0, 100, 1, "%", 0.01),
            ],
            quick: [-12, -5, -2, 0, 4, 7, 12].map((value) => ({
                label: `${value > 0 ? "+" : ""}${value} st`,
                patch: { pitch_enabled: value !== 0, pitch_semitones: value, pitch_cents: 0 },
            })),
        },
        {
            title: "freq_shift", toggle: "freq_shift_enabled",
            controls: [
                slider("freq_shift_hz", "shift_hz", -500, 500, 1, "Hz"),
                slider("freq_shift_mix", "mix", 0, 100, 1, "%", 0.01),
            ],
            quick: [-120, -30, 0, 50, 180].map((value) => ({
                label: `${value > 0 ? "+" : ""}${value} Hz`,
                patch: { freq_shift_enabled: value !== 0, freq_shift_hz: value },
            })),
        },
        {
            title: "vocoder", toggle: "vocoder_enabled",
            controls: [
                selector("vocoder_carrier", "carrier", [
                    { value: "Dente de Serra", label: "wave_saw" },
                    { value: "Acorde", label: "wave_chord" },
                    { value: "Quadrada", label: "wave_sq" },
                    { value: "Sussurro (Ruído)", label: "wave_whisper" },
                ]),
                slider("vocoder_freq_hz", "base_freq", 55, 300, 1, "Hz"),
                slider("vocoder_smooth", "smoothness", 10, 95, 1, "%", 0.01),
                slider("vocoder_mix", "mix", 0, 100, 1, "%", 0.01),
            ],
        },
    ],
    modulation: [
        {
            title: "phaser", toggle: "phaser_enabled",
            controls: [
                slider("phaser_stages", "stages", 2, 12, 2, "x", 1, true),
                slider("phaser_freq_hz", "lfo_speed", 0.1, 6, 0.1, "Hz"),
                slider("phaser_depth", "depth", 0, 100, 1, "%", 0.01),
                slider("phaser_feedback", "feedback", -90, 90, 1, "%", 0.01),
                slider("phaser_mix", "mix", 0, 100, 1, "%", 0.01),
            ],
        },
        {
            title: "wah", titleText: "Wah-Wah", toggle: "wah_enabled",
            controls: [
                slider("wah_freq_hz", "lfo_freq", 0.2, 8, 0.1, "Hz"),
                slider("wah_depth", "depth", 0, 100, 1, "%", 0.01),
                slider("wah_resonance", "resonance", 0.5, 8, 0.1, "x"),
                slider("wah_mix", "mix", 0, 100, 1, "%", 0.01),
            ],
        },
        {
            title: "chorus_flanger", toggle: "chorus_enabled",
            controls: [
                slider("chorus_rate_hz", "lfo_speed", 0.1, 8, 0.1, "Hz"),
                slider("chorus_delay_ms", "base_delay", 1.5, 35, 0.5, "ms"),
                slider("chorus_depth_ms", "modulation", 0.5, 15, 0.5, "ms"),
                slider("chorus_feedback", "feedback", 0, 85, 1, "%", 0.01),
                slider("chorus_mix", "mix", 0, 100, 1, "%", 0.01),
            ],
        },
        {
            title: "tremolo", toggle: "tremolo_enabled",
            controls: [
                selector("tremolo_waveform", "waveform", waveOptions),
                slider("tremolo_freq_hz", "frequency", 0.5, 25, 0.5, "Hz"),
                slider("tremolo_depth", "intensity", 0, 100, 1, "%", 0.01),
            ],
        },
    ],
    fx: [
        {
            title: "ring_mod", toggle: "ring_enabled",
            controls: [
                selector("ring_waveform", "waveform", [
                    { value: "Senoide", label: "wave_sine" },
                    { value: "Quadrada", label: "wave_sq" },
                    { value: "Triangular", label: "wave_tri" },
                ]),
                slider("ring_freq_hz", "carrier_freq", 5, 400, 1, "Hz"),
                slider("ring_mix", "mix", 0, 100, 1, "%", 0.01),
            ],
        },
        {
            title: "dist_bit", toggle: "dist_enabled",
            controls: [
                slider("dist_drive", "drive_sat", 1, 25, 0.2, "x"),
                slider("dist_bits", "resolution", 4, 16, 1, "bits", 1, true),
                slider("dist_downsample", "downsample", 1, 16, 1, "x", 1, true),
                slider("dist_mix", "mix", 0, 100, 1, "%", 0.01),
            ],
        },
    ],
    space: [
        {
            title: "echo_delay", toggle: "echo_enabled",
            controls: [
                slider("echo_delay_ms", "delay", 10, 700, 2, "ms"),
                slider("echo_feedback", "feedback", 0, 85, 1, "%", 0.01),
                slider("echo_mix", "echo_vol", 0, 100, 1, "%", 0.01),
            ],
        },
        {
            title: "reverb", toggle: "reverb_enabled",
            controls: [
                slider("reverb_room", "room_size", 0, 100, 1, "%", 0.01),
                slider("reverb_damp", "damping", 5, 92, 1, "%", 0.01),
                slider("reverb_mix", "mix", 0, 100, 1, "%", 0.01),
            ],
        },
    ],
};

const TAB_DEFS = [
    { id: "tab_pitch", groups: "pitch" },
    { id: "tab_eq", special: "eq" },
    { id: "tab_mod", groups: "modulation" },
    { id: "tab_fx", groups: "fx" },
    { id: "tab_space", groups: "space" },
    { id: "tab_mixer", special: "mixer" },
];

const MIXER_MODULES = [
    ["pitch_enabled", "pitch_shift"], ["freq_shift_enabled", "freq_shift"],
    ["vocoder_enabled", "vocoder"], ["eq_enabled", "equalizer"],
    ["phaser_enabled", "phaser"], ["wah_enabled", "wah"],
    ["chorus_enabled", "chorus_flanger"], ["tremolo_enabled", "tremolo"],
    ["ring_enabled", "ring_mod_short"], ["dist_enabled", "dist_bit"],
    ["echo_enabled", "echo_delay"], ["reverb_enabled", "reverb"],
];

let language = localStorage.getItem("voxcraft-language") || "pt";
let theme = localStorage.getItem("voxcraft-theme") || "dark";
let params = { ...PARAMS_DEFAULT };
let coreConnected = false;
let audioRunning = false;
let currentTab = "tab_pitch";
let presetNames = { builtIn: [], custom: [] };
let selectedPreset = "";
let devices = { inputs: [], outputs: [] };
let routing = readStoredRouting();
let virtualOutputSetupSupported = false;
let virtualOutputSetupCanRetry = false;
let virtualMicrophoneAvailable = true;
let pendingParams = {};
let paramTimer = null;
let parameterUpdateQueue = Promise.resolve();
let meterBusy = false;
let captureHotkey = false;
let hotkey = localStorage.getItem("voxcraft-hotkey") || "F9";
const HOTKEY_MODIFIER_ORDER = ["CTRL", "ALT", "SHIFT", "SUPER"];
let hotkeyDown = false;
let holdBaseBypass = null;
let registeredHotkey = null;
let listenForGlobalHotkey = null;
let waylandHotkeys = null;
let hotkeyGlobalError = "";
let portalHotkeyDescription = "";
let hotkeyRegistrationQueue = Promise.resolve();
let playHotkeyFeedback = () => {};
let showMessage;

function normalizeHotkeyKey(key) {
    const value = String(key).trim();
    if (/^[a-z]$/i.test(value)) return `Key${value.toUpperCase()}`;
    if (/^\d$/.test(value)) return `Digit${value}`;

    const aliases = {
        " ": "Space",
        "`": "Backquote",
        "\\": "Backslash",
        "[": "BracketLeft",
        "]": "BracketRight",
        ",": "Comma",
        "=": "Equal",
        "-": "Minus",
        ".": "Period",
        "'": "Quote",
        ";": "Semicolon",
        "/": "Slash",
        Esc: "Escape",
        Return: "Enter",
        Left: "ArrowLeft",
        Right: "ArrowRight",
        Up: "ArrowUp",
        Down: "ArrowDown",
        Page_Up: "PageUp",
        Page_Down: "PageDown",
        Caps_Lock: "CapsLock",
        Num_Lock: "NumLock",
        Scroll_Lock: "ScrollLock",
        Bracketleft: "BracketLeft",
        Bracketright: "BracketRight",
        comma: "Comma",
        equal: "Equal",
        minus: "Minus",
        period: "Period",
        apostrophe: "Quote",
        semicolon: "Semicolon",
        slash: "Slash",
    };
    return aliases[value] || value;
}

function normalizeHotkey(shortcut) {
    const raw = String(shortcut ?? "F9");
    const original = raw === " " ? "Space" : raw.trim() || "F9";
    const tokens = original === "+"
        ? ["SHIFT", "Equal"]
        : original.split("+").map((token) => token.trim()).filter(Boolean);
    const modifiers = new Set();
    let key = null;
    const modifierAliases = {
        CTRL: "CTRL", CONTROL: "CTRL",
        ALT: "ALT", OPTION: "ALT",
        SHIFT: "SHIFT",
        SUPER: "SUPER", META: "SUPER", CMD: "SUPER", COMMAND: "SUPER",
    };

    for (const token of tokens) {
        const modifier = modifierAliases[token.toUpperCase()];
        if (modifier) {
            modifiers.add(modifier);
        } else if (key === null) {
            key = normalizeHotkeyKey(token);
        } else {
            return "F9";
        }
    }
    if (!key) return "F9";
    return [...HOTKEY_MODIFIER_ORDER.filter((modifier) => modifiers.has(modifier)), key].join("+");
}

function hotkeyParts(shortcut) {
    const tokens = normalizeHotkey(shortcut).split("+");
    return {
        key: tokens.at(-1),
        modifiers: new Set(tokens.slice(0, -1)),
    };
}

function formatHotkey(shortcut) {
    const { key, modifiers } = hotkeyParts(shortcut);
    const labels = { CTRL: "Ctrl", ALT: "Alt", SHIFT: "Shift", SUPER: "Super" };
    const keyLabels = {
        ArrowDown: "Down",
        ArrowLeft: "Left",
        ArrowRight: "Right",
        ArrowUp: "Up",
        Backspace: "Backspace",
        Backquote: "`",
        Backslash: "\\",
        BracketLeft: "[",
        BracketRight: "]",
        Comma: ",",
        Equal: "=",
        Minus: "-",
        PageDown: "Page Down",
        PageUp: "Page Up",
        Period: ".",
        Quote: "'",
        Semicolon: ";",
        Slash: "/",
        Space: "Space",
    };
    const displayKey = keyLabels[key]
        || key.replace(/^Key([A-Z])$/, "$1").replace(/^Digit([0-9])$/, "$1");
    return [
        ...HOTKEY_MODIFIER_ORDER.filter((modifier) => modifiers.has(modifier)).map((modifier) => labels[modifier]),
        displayKey,
    ].join("+");
}

function hotkeyModifiersFromEvent(event) {
    return [
        event.ctrlKey && "CTRL",
        event.altKey && "ALT",
        event.shiftKey && "SHIFT",
        event.metaKey && "SUPER",
    ].filter(Boolean);
}

function modifierKeyFromEvent(event) {
    if (["Control", "ControlLeft", "ControlRight"].includes(event.key)
        || /^Control(Left|Right)$/.test(event.code)) return "CTRL";
    if (["Alt", "AltLeft", "AltRight", "AltGraph"].includes(event.key)
        || /^Alt(Left|Right)$/.test(event.code)) return "ALT";
    if (["Shift", "ShiftLeft", "ShiftRight"].includes(event.key)
        || /^Shift(Left|Right)$/.test(event.code)) return "SHIFT";
    if (["Meta", "MetaLeft", "MetaRight", "OS"].includes(event.key)
        || /^(Meta|OS)(Left|Right)?$/.test(event.code)) return "SUPER";
    return null;
}

function formatHotkeyCapture(modifiers) {
    const labels = { CTRL: "Ctrl", ALT: "Alt", SHIFT: "Shift", SUPER: "Super" };
    const prefix = HOTKEY_MODIFIER_ORDER
        .filter((modifier) => modifiers.includes(modifier))
        .map((modifier) => labels[modifier]);
    return prefix.length ? `${prefix.join("+")}+…` : t("key_capture");
}

function matchesHotkeyEvent(event, shortcut) {
    const { key, modifiers } = hotkeyParts(shortcut);
    const eventKey = event.code || normalizeHotkeyKey(event.key);
    const eventModifiers = hotkeyModifiersFromEvent(event);
    return eventKey === key
        && eventModifiers.length === modifiers.size
        && eventModifiers.every((modifier) => modifiers.has(modifier));
}

function t(key) {
    return TEXT[language]?.[key] ?? TEXT.pt[key] ?? key;
}

function readStoredRouting() {
    try {
        return JSON.parse(localStorage.getItem("voxcraft-routing") || "{}");
    } catch {
        return {};
    }
}

function saveRouting() {
    localStorage.setItem("voxcraft-routing", JSON.stringify(routing));
}

function readStoredVoiceSettings() {
    try {
        const saved = JSON.parse(localStorage.getItem("voxcraft-voice-settings") || "null");
        return saved && typeof saved === "object" ? saved : {};
    } catch {
        return {};
    }
}

function saveVoiceSettings() {
    if (!coreConnected) return;
    try {
        localStorage.setItem("voxcraft-voice-settings", JSON.stringify({ params, selectedPreset }));
    } catch (error) {
        console.error("Não foi possível salvar os ajustes de voz:", error);
    }
}

function coreRequest(method, requestParams = {}) {
    return invoke("core_request", { method, params: requestParams });
}

function applyLanguage(nextLanguage) {
    language = TEXT[nextLanguage] ? nextLanguage : "pt";
    localStorage.setItem("voxcraft-language", language);
    document.documentElement.lang = language === "pt" ? "pt-BR" : language;
    document.querySelectorAll("[data-i18n]").forEach((element) => {
        element.textContent = t(element.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-label]").forEach((element) => {
        element.setAttribute("aria-label", t(element.dataset.i18nLabel));
    });
    document.querySelectorAll("[data-label-key]").forEach((element) => {
        element.textContent = t(element.dataset.labelKey);
    });
    document.querySelectorAll("[data-option-label]").forEach((option) => {
        option.textContent = t(option.dataset.optionLabel);
    });
    document.querySelectorAll("[data-tab-label]").forEach((button) => {
        button.textContent = t(button.dataset.tabLabel);
    });
    document.querySelectorAll("[data-mixer-label]").forEach((element) => {
        element.textContent = t(element.dataset.mixerLabel);
    });
    document.querySelectorAll("[data-window-control]").forEach((button) => {
        const label = t(button.dataset.windowControl);
        button.setAttribute("aria-label", label);
    });
    document.querySelector("#language-select").value = language;
    document.querySelector("#hotkey-key").setAttribute("aria-description", t("define_key"));
    renderGlobalHotkeyStatus();
    updateAudioButton();
    updateGateIndicator(true);
}

function applyTheme(nextTheme) {
    theme = ["dark", "oled", "light"].includes(nextTheme) ? nextTheme : "dark";
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("voxcraft-theme", theme);
    document.querySelector("#theme-select").value = theme;
    drawEqCurve();
    drawWaveform([]);
}

function setAudioStatus(message, running = audioRunning, error = false) {
    const dot = document.querySelector("#audio-status-dot");
    dot.classList.toggle("is-connected", running);
    dot.classList.toggle("is-error", error);
    document.querySelector("#audio-status-text").textContent = message;
}

function updateAudioButton() {
    const button = document.querySelector("#power-button");
    button.textContent = audioRunning ? t("stop_audio") : t("start_audio");
    button.classList.toggle("is-running", audioRunning);
    button.setAttribute("aria-pressed", String(audioRunning));
}

function updateBypassButton() {
    const button = document.querySelector("#bypass-button");
    const enabled = Boolean(params.bypass);
    button.classList.toggle("is-bypass", enabled);
    button.setAttribute("aria-pressed", String(enabled));
}

function renderControlValues() {
    document.querySelectorAll("[data-param]").forEach((control) => {
        const key = control.dataset.param;
        const value = params[key] ?? control.dataset.default;
        if (control.type === "checkbox") {
            control.checked = value === true || value === "true";
            return;
        }
        if (control.tagName === "SELECT") {
            control.value = String(value);
            return;
        }
        const factor = Number(control.dataset.factor || 1);
        const uiValue = Number(value) / factor;
        control.value = String(Math.min(Number(control.max), Math.max(Number(control.min), uiValue)));
        updateSliderValue(control);
    });
    updateBypassButton();
    drawEqCurve();
}

function formatSliderValue(value, step, unit) {
    const text = step < 1 ? Number(value).toFixed(1) : String(Math.round(Number(value)));
    return `${text} ${unit}`;
}

function updateSliderValue(input) {
    const output = input.closest(".slider-card, .vertical-band")?.querySelector("output");
    if (!output) return;
    const value = Number(input.value);
    output.textContent =
        input.closest(".vertical-band") && input.dataset.unit === "dB"
            ? `${value >= 0 ? "+" : ""}${value.toFixed(1)} dB`
            : formatSliderValue(value, Number(input.step), input.dataset.unit || "");
}

function scheduleParameterUpdate(key, value, immediate = false) {
    params[key] = value;
    if (!coreConnected) return;
    saveVoiceSettings();
    pendingParams[key] = value;
    window.clearTimeout(paramTimer);
    if (immediate) {
        void flushParameterUpdates();
    } else {
        paramTimer = window.setTimeout(flushParameterUpdates, 90);
    }
}

function flushParameterUpdates() {
    if (!coreConnected || Object.keys(pendingParams).length === 0) return parameterUpdateQueue;
    const patch = pendingParams;
    pendingParams = {};
    // Keep press/release patches distinct and in order, even when sent back-to-back.
    parameterUpdateQueue = parameterUpdateQueue
        .then(() => coreRequest("set_params", { params: patch }))
        .catch((error) => setAudioStatus(String(error), audioRunning, true));
    return parameterUpdateQueue;
}

function createSwitch(param, labelKey, options = {}) {
    const label = document.createElement("label");
    label.className = `switch-row${options.className ? ` ${options.className}` : ""}`;

    const input = document.createElement("input");
    input.type = "checkbox";
    input.dataset.param = param;
    input.dataset.default = String(PARAMS_DEFAULT[param] ?? false);
    input.setAttribute("aria-label", t(labelKey));
    input.addEventListener("change", () => {
        scheduleParameterUpdate(param, input.checked);
        if (param.startsWith("eq_")) drawEqCurve();
    });

    const track = document.createElement("span");
    track.className = "switch-track";
    track.setAttribute("aria-hidden", "true");
    const text = document.createElement("span");
    text.dataset.labelKey = labelKey;
    text.textContent = t(labelKey);
    label.append(input, track, text);
    return label;
}

function createSlider(control, options = {}) {
    const wrapper = document.createElement("label");
    wrapper.className = options.vertical ? "vertical-band" : "slider-card";

    const head = document.createElement("span");
    head.className = "slider-head";
    const title = document.createElement("span");
    title.className = "slider-title";
    title.dataset.labelKey = control.label;
    title.textContent = t(control.label);
    const value = document.createElement("output");
    value.className = "slider-value";
    head.append(title, value);

    const input = document.createElement("input");
    input.type = "range";
    input.min = String(control.min);
    input.max = String(control.max);
    input.step = String(control.step);
    input.value = String(PARAMS_DEFAULT[control.param] / control.factor);
    input.dataset.param = control.param;
    input.dataset.default = String(PARAMS_DEFAULT[control.param]);
    input.dataset.factor = String(control.factor);
    input.dataset.unit = control.unit;
    input.dataset.integer = String(control.integer);
    input.setAttribute("aria-label", t(control.label));
    input.addEventListener("input", () => {
        updateSliderValue(input);
        let raw = Number(input.value);
        if (control.integer) raw = Math.round(raw);
        scheduleParameterUpdate(control.param, raw * control.factor);
        if (control.param.startsWith("eq_")) drawEqCurve();
    });
    wrapper.append(head, input);
    updateSliderValue(input);
    return wrapper;
}

function createSelect(control) {
    const wrapper = document.createElement("label");
    wrapper.className = "wide-control";
    const label = document.createElement("span");
    label.className = "field-label";
    label.dataset.labelKey = control.label;
    label.textContent = t(control.label);
    const select = document.createElement("select");
    select.className = "select-input";
    select.dataset.param = control.param;
    select.dataset.default = PARAMS_DEFAULT[control.param];
    select.setAttribute("aria-label", t(control.label));
    control.options.forEach((entry) => {
        const option = document.createElement("option");
        option.value = entry.value;
        option.dataset.optionLabel = entry.label;
        option.textContent = t(entry.label);
        select.append(option);
    });
    select.addEventListener("change", () => {
        scheduleParameterUpdate(control.param, select.value);
    });
    wrapper.append(label, select);
    return wrapper;
}

function renderEffectCard(definition) {
    const card = document.createElement("section");
    card.className = "card effect-card";

    const header = document.createElement("div");
    header.className = "effect-header";
    if (definition.toggle) {
        header.append(createSwitch(definition.toggle, definition.title));
    } else {
        const title = document.createElement("h2");
        title.className = "effect-title";
        title.textContent = definition.titleText || t(definition.title);
        title.dataset.labelKey = definition.titleText ? "wah" : definition.title;
        header.append(title);
    }

    const controls = document.createElement("div");
    controls.className = "control-grid";
    definition.controls.forEach((control) => {
        controls.append(control.kind === "select" ? createSelect(control) : createSlider(control));
    });
    card.append(header, controls);

    if (definition.quick) {
        const quickRow = document.createElement("div");
        quickRow.className = "quick-row";
        definition.quick.forEach((item) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "button quick-button";
            button.textContent = item.label;
            button.addEventListener("click", () => applyLocalPatch(item.patch));
            quickRow.append(button);
        });
        card.append(quickRow);
    }
    return card;
}

function renderEqTab(panel) {
    const top = document.createElement("section");
    top.className = "card eq-card";
    const header = document.createElement("div");
    header.className = "effect-header";
    header.append(createSwitch("eq_enabled", "equalizer"));
    const right = document.createElement("div");
    right.className = "eq-header-actions";
    const badge = document.createElement("span");
    badge.id = "eq-hpf-badge";
    badge.className = "eq-badge";
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "button button-small";
    reset.dataset.i18n = "reset_eq";
    reset.textContent = t("reset_eq");
    reset.addEventListener("click", resetEqualizer);
    right.append(badge, reset);
    header.append(right);

    const canvas = document.createElement("canvas");
    canvas.id = "eq-canvas";
    canvas.className = "eq-canvas";
    canvas.setAttribute("aria-label", t("equalizer"));
    top.append(header, canvas);
    panel.append(top);

    const cuts = document.createElement("div");
    cuts.className = "eq-cut-grid";
    const hpf = document.createElement("section");
    hpf.className = "card cut-card";
    hpf.append(createSwitch("eq_hpf_enabled", "hpf"));
    hpf.append(createSlider(slider("eq_hpf_hz", "frequency", 20, 1000, 5, "Hz")));
    const lpf = document.createElement("section");
    lpf.className = "card cut-card";
    lpf.append(createSwitch("eq_lpf_enabled", "lpf"));
    lpf.append(createSlider(slider("eq_lpf_hz", "frequency", 1200, 18000, 100, "Hz")));
    cuts.append(hpf, lpf);
    panel.append(cuts);

    const bands = document.createElement("section");
    bands.className = "card eq-bands custom-scrollbar";
    [
        ["eq_band1_db", "eq_b1"], ["eq_band2_db", "eq_b2"], ["eq_band3_db", "eq_b3"],
        ["eq_band4_db", "eq_b4"], ["eq_band5_db", "eq_b5"],
    ].forEach(([param, label]) => {
        bands.append(createSlider(slider(param, label, -18, 18, 0.5, "dB"), { vertical: true }));
    });
    panel.append(bands);
}

function renderMixerTab(panel) {
    const title = document.createElement("h2");
    title.className = "mixer-title";
    title.dataset.i18n = "effects_chain";
    title.textContent = t("effects_chain");
    const grid = document.createElement("div");
    grid.className = "mixer-grid";
    MIXER_MODULES.forEach(([param, label], index) => {
        const card = document.createElement("section");
        card.className = "card mixer-module";
        const number = document.createElement("span");
        number.className = "mixer-number";
        number.textContent = String(index + 1).padStart(2, "0");
        const control = createSwitch(param, label);
        control.classList.add("mixer-switch");
        grid.append(card);
        card.append(number, control);
    });
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "button button-danger reset-effects";
    reset.dataset.i18n = "reset_effects";
    reset.textContent = t("reset_effects");
    reset.addEventListener("click", async () => {
        if (!(await showMessage({
            type: "confirm", title: t("reset_effects"), message: t("reset_confirm"),
            acceptLabel: t("reset_effects"), danger: true,
        }))) return;
        await applyPreset("Normal");
    });
    panel.append(title, grid, reset);
}

function renderTabs() {
    const tabList = document.querySelector("#tab-list");
    const content = document.querySelector("#tab-content");
    tabList.replaceChildren();
    content.replaceChildren();

    TAB_DEFS.forEach((definition) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "tab-button";
        button.id = `${definition.id}-button`;
        button.role = "tab";
        button.dataset.tab = definition.id;
        button.dataset.tabLabel = definition.id;
        button.textContent = t(definition.id);
        button.setAttribute("aria-controls", definition.id);
        button.addEventListener("click", () => selectTab(definition.id));
        tabList.append(button);

        const panel = document.createElement("div");
        panel.id = definition.id;
        panel.className = "tab-panel";
        panel.role = "tabpanel";
        panel.setAttribute("aria-labelledby", button.id);
        if (definition.special === "eq") {
            renderEqTab(panel);
        } else if (definition.special === "mixer") {
            renderMixerTab(panel);
        } else {
            GROUPS[definition.groups].forEach((group) => panel.append(renderEffectCard(group)));
        }
        content.append(panel);
    });
    selectTab(currentTab);
    applyLanguage(language);
    renderControlValues();
}

function selectTab(id) {
    currentTab = id;
    document.querySelectorAll(".tab-button").forEach((button) => {
        const selected = button.dataset.tab === id;
        button.classList.toggle("is-selected", selected);
        button.setAttribute("aria-selected", String(selected));
        button.tabIndex = selected ? 0 : -1;
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
        panel.hidden = panel.id !== id;
    });
    if (id === "tab_eq") drawEqCurve();
}

function applyLocalPatch(patch) {
    Object.assign(params, patch);
    renderControlValues();
    Object.entries(patch).forEach(([key, value]) => scheduleParameterUpdate(key, value));
}

function resetEqualizer() {
    applyLocalPatch({
        eq_hpf_enabled: true, eq_hpf_hz: 80, eq_lpf_enabled: false, eq_lpf_hz: 12000,
        eq_band1_db: 0, eq_band2_db: 0, eq_band3_db: 0, eq_band4_db: 0, eq_band5_db: 0,
    });
}

function drawEqCurve() {
    const canvas = document.querySelector("#eq-canvas");
    if (!canvas || canvas.clientWidth < 2) return;
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    const context = canvas.getContext("2d");
    context.scale(ratio, ratio);

    const styles = getComputedStyle(document.documentElement);
    const lineColor = styles.getPropertyValue("--accent").trim();
    const gridColor = styles.getPropertyValue("--grid-line").trim();
    const zeroColor = styles.getPropertyValue("--grid-zero").trim();
    const textColor = styles.getPropertyValue("--text-subtle").trim();
    const pad = { left: 36, right: 12, top: 14, bottom: 22 };
    const plotW = width - pad.left - pad.right;
    const plotH = height - pad.top - pad.bottom;
    const minDb = -18;
    const maxDb = 12;
    const yFor = (db) => pad.top + ((maxDb - db) / (maxDb - minDb)) * plotH;

    context.clearRect(0, 0, width, height);
    context.font = '10px "JetBrains Mono", monospace';
    context.textBaseline = "middle";
    [-12, -6, 0, 6, 12].forEach((db) => {
        const y = yFor(db);
        context.strokeStyle = db === 0 ? zeroColor : gridColor;
        context.lineWidth = 1;
        context.beginPath();
        context.moveTo(pad.left, y);
        context.lineTo(width - pad.right, y);
        context.stroke();
        context.fillStyle = textColor;
        context.fillText(`${db}`, 5, y);
    });
    const frequencies = [20, 100, 500, 1000, 5000, 10000, 20000];
    frequencies.forEach((frequency) => {
        const x = pad.left + (Math.log10(frequency / 20) / 3) * plotW;
        context.strokeStyle = gridColor;
        context.beginPath();
        context.moveTo(x, pad.top);
        context.lineTo(x, pad.top + plotH);
        context.stroke();
        context.fillStyle = textColor;
        context.textAlign = "center";
        context.fillText(frequency >= 1000 ? `${frequency / 1000}k` : String(frequency), x, height - 9);
    });

    const centers = [120, 400, 1200, 3500, 7500];
    const gains = [1, 2, 3, 4, 5].map((index) => Number(params[`eq_band${index}_db`] || 0));
    context.strokeStyle = lineColor;
    context.lineWidth = 2;
    context.beginPath();
    for (let i = 0; i <= 180; i += 1) {
        const frequency = 20 * (1000 ** (i / 180));
        const x = pad.left + (i / 180) * plotW;
        let db = 0;
        centers.forEach((center, band) => {
            const distance = Math.log(frequency / center);
            db += gains[band] * Math.exp(-0.5 * (distance / 0.55) ** 2);
        });
        if (params.eq_hpf_enabled && frequency < Number(params.eq_hpf_hz || 80)) {
            db -= Math.min(24, (Math.log(Number(params.eq_hpf_hz || 80) / frequency) / Math.LN2) * 12);
        }
        if (params.eq_lpf_enabled && frequency > Number(params.eq_lpf_hz || 12000)) {
            db -= Math.min(24, (Math.log(frequency / Number(params.eq_lpf_hz || 12000)) / Math.LN2) * 12);
        }
        const y = yFor(Math.max(minDb, Math.min(maxDb, db)));
        if (i === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
    }
    context.stroke();

    const badge = document.querySelector("#eq-hpf-badge");
    if (badge) badge.textContent = params.eq_hpf_enabled ? `HPF ${Math.round(params.eq_hpf_hz || 80)} Hz` : t("eq_flat");
}

function drawWaveform(samples) {
    const canvas = document.querySelector("#waveform");
    if (!canvas || canvas.clientWidth < 2) return;
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    const context = canvas.getContext("2d");
    context.scale(ratio, ratio);
    const styles = getComputedStyle(document.documentElement);
    context.clearRect(0, 0, width, height);
    context.strokeStyle = styles.getPropertyValue("--grid-line").trim();
    context.beginPath();
    context.moveTo(0, height / 2);
    context.lineTo(width, height / 2);
    context.stroke();
    context.strokeStyle = styles.getPropertyValue("--accent").trim();
    context.lineWidth = 1.5;
    context.beginPath();
    const data = samples?.length ? samples : Array(128).fill(0);
    data.forEach((sample, index) => {
        const x = (index / Math.max(1, data.length - 1)) * width;
        const y = height / 2 - Math.max(-1, Math.min(1, Number(sample))) * (height * 0.42);
        if (index === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
    });
    context.stroke();
}

function updateGateIndicator(isOpen) {
    const gate = document.querySelector("#gate-indicator");
    if (!gate) return;
    gate.textContent = t(isOpen ? "gate_open" : "gate_closed");
    gate.classList.toggle("is-open", isOpen);
    gate.classList.toggle("is-closed", !isOpen);
}

function updateMeters(meter) {
    const inputDb = Number(meter.inputPeakDb ?? -60);
    const outputDb = Number(meter.outputPeakDb ?? -60);
    document.querySelector("#input-meter").style.width = `${Math.max(0, Math.min(100, ((inputDb + 60) / 60) * 100))}%`;
    document.querySelector("#output-meter").style.width = `${Math.max(0, Math.min(100, ((outputDb + 60) / 60) * 100))}%`;
    document.querySelector("#input-db").textContent = `${inputDb.toFixed(0)} dB`;
    document.querySelector("#output-db").textContent = `${outputDb.toFixed(0)} dB`;
    updateGateIndicator(Boolean(meter.gateOpen));
    drawWaveform(meter.waveform);
    if (Boolean(meter.running) !== audioRunning) {
        audioRunning = Boolean(meter.running);
        updateAudioButton();
        setAudioStatus(audioRunning ? t("audio_started") : t("stopped"), audioRunning);
    }
}

async function pollMeters() {
    if (!coreConnected || meterBusy) return;
    meterBusy = true;
    try {
        updateMeters(await coreRequest("meters"));
    } catch {
        // A telemetry hiccup should not interrupt audio controls.
    } finally {
        meterBusy = false;
    }
}

function fillDeviceSelect(select, items, savedIndex, emptyLabel = "no_devices") {
    select.replaceChildren();
    if (items.length === 0) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = t(emptyLabel);
        select.append(option);
        return;
    }
    items.forEach((device) => {
        const option = document.createElement("option");
        option.value = String(device.index);
        option.textContent = device.name;
        select.append(option);
    });
    const saved = items.find((device) => String(device.index) === String(savedIndex));
    select.value = String(saved?.index ?? items[0].index);
}

function isCableInput(device) {
    const normalized = String(device?.name || "").toLowerCase().replace(/[^a-z0-9]/g, "");
    return normalized === "cableinput";
}

function renderDevices() {
    fillDeviceSelect(document.querySelector("#input-device"), devices.inputs, routing.inputIndex);
    const virtualOutputs = devices.outputs.filter((device) => device.isVirtualOutput
        && (!virtualOutputSetupSupported || isCableInput(device)));
    document.querySelector("#configure-virtual-output").hidden =
        !virtualOutputSetupSupported || !virtualOutputSetupCanRetry
        || (virtualOutputs.length > 0 && virtualMicrophoneAvailable);
    const preferredOutput = virtualOutputs.find((device) => /cable\s*input/i.test(device.name))
        || virtualOutputs.find((device) => /vb[\s-]*audio/i.test(device.name))
        || virtualOutputs[0];
    routing.outputIndex = String(preferredOutput?.index ?? "");
    updateRoutingFromControls();
}

function updateRoutingFromControls() {
    routing = {
        inputIndex: document.querySelector("#input-device").value,
        outputIndex: String(routing.outputIndex ?? ""),
        blocksize: document.querySelector("#latency-select").value || "512",
        monitorEnabled: document.querySelector("#monitor-enabled").checked,
    };
    saveRouting();
}

async function updateMonitor(control) {
    const enabled = control.checked;
    updateRoutingFromControls();
    if (!audioRunning) return;

    control.disabled = true;
    try {
        await coreRequest("set_monitor", { enabled });
    } catch (error) {
        control.checked = false;
        updateRoutingFromControls();
        setAudioStatus(String(error), audioRunning, true);
    } finally {
        control.disabled = false;
    }
}

async function refreshDevices() {
    const button = document.querySelector("#refresh-devices");
    button.disabled = true;
    const wasRunning = audioRunning;
    try {
        if (wasRunning) {
            await coreRequest("stop_audio");
            audioRunning = false;
            updateAudioButton();
        }
        devices = await coreRequest("refresh_devices");
        renderDevices();
        setAudioStatus(t("devices_refreshed"), audioRunning);
        if (wasRunning) await toggleAudio();
    } catch (error) {
        setAudioStatus(String(error), audioRunning, true);
    } finally {
        button.disabled = false;
    }
}

async function configureVirtualOutput() {
    const button = document.querySelector("#configure-virtual-output");
    button.disabled = true;
    try {
        const setup = await coreRequest("ensure_virtual_output");
        virtualOutputSetupSupported = setup.supported === true;
        virtualOutputSetupCanRetry = setup.canRetry === true;
        virtualMicrophoneAvailable = setup.microphoneAvailable !== false;
        devices = await coreRequest("list_devices");
        renderDevices();
        if (setup.available && virtualMicrophoneAvailable
      && devices.outputs.some((device) => device.isVirtualOutput
        && (!virtualOutputSetupSupported || isCableInput(device)))) {
            setAudioStatus(t("stopped"), false);
        } else {
            setAudioStatus(
                setup.message || (!virtualMicrophoneAvailable
                    ? t("virtual_microphone_setup_failed")
                    : t("virtual_output_setup_failed")),
                false,
                true,
            );
        }
    } catch (error) {
        setAudioStatus(String(error), false, true);
    } finally {
        button.disabled = false;
    }
}

function renderPresets() {
    const select = document.querySelector("#preset-select");
    const value = selectedPreset;
    select.replaceChildren();
    const current = document.createElement("option");
    current.value = "";
    current.textContent = t("current_config");
    select.append(current);
    presetNames.builtIn.forEach((name) => {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        select.append(option);
    });
    presetNames.custom.forEach((name) => {
        const option = document.createElement("option");
        option.value = `★ ${name}`;
        option.textContent = `★ ${name}`;
        select.append(option);
    });
    select.value = [...select.options].some((option) => option.value === value) ? value : "";
    document.querySelector("#delete-preset").disabled = !select.value.startsWith("★ ");
}

async function refreshPresets() {
    presetNames = await coreRequest("list_presets");
    renderPresets();
}

async function applyPreset(value) {
    const custom = value.startsWith("★ ");
    const name = custom ? value.slice(2) : value;
    if (!name) return;
    window.clearTimeout(paramTimer);
    try {
        await flushParameterUpdates();
        params = await coreRequest("apply_preset", { name, custom });
        selectedPreset = value;
        saveVoiceSettings();
        renderPresets();
        renderControlValues();
        setAudioStatus(`${t("preset")}: ${name}`, audioRunning);
    } catch (error) {
        renderPresets();
        setAudioStatus(String(error), audioRunning, true);
    }
}

async function savePreset() {
    const name = await showMessage({
        type: "input", title: t("save"), message: t("save_preset_prompt"), acceptLabel: t("save"),
    });
    if (name === null) return;
    try {
        await flushParameterUpdates();
        await coreRequest("save_preset", { name });
        selectedPreset = `★ ${name}`;
        saveVoiceSettings();
        await refreshPresets();
        setAudioStatus(t("preset_saved"), audioRunning);
    } catch (error) {
        await showMessage({ title: t("notice"), message: String(error) });
    }
}

async function deletePreset() {
    const selected = document.querySelector("#preset-select").value;
    if (!selected.startsWith("★ ")) {
        await showMessage({ title: t("notice"), message: t("only_custom_delete") });
        return;
    }
    const name = selected.slice(2);
    if (!(await showMessage({
        type: "confirm", title: t("delete"),
        message: t("delete_preset_confirm").replace("{name}", () => name),
        acceptLabel: t("delete"), danger: true,
    }))) return;
    try {
        window.clearTimeout(paramTimer);
        await flushParameterUpdates();
        await coreRequest("delete_preset", { name });
        selectedPreset = "";
        params = await coreRequest("apply_preset", { name: "Normal", custom: false });
        saveVoiceSettings();
        await refreshPresets();
        renderControlValues();
        setAudioStatus(t("preset_deleted"), audioRunning);
    } catch (error) {
        await showMessage({ title: t("notice"), message: String(error) });
    }
}

async function toggleAudio() {
    const button = document.querySelector("#power-button");
    const monitorControl = document.querySelector("#monitor-enabled");
    button.disabled = true;
    monitorControl.disabled = true;
    try {
        if (audioRunning) {
            await coreRequest("stop_audio");
            audioRunning = false;
            updateAudioButton();
            setAudioStatus(t("stopped"), false);
            return;
        }

        updateRoutingFromControls();
        const inputIndex = Number(routing.inputIndex);
        const outputIndex = Number(routing.outputIndex);
        if (virtualOutputSetupSupported && !virtualMicrophoneAvailable) {
            setAudioStatus(t("virtual_microphone_setup_failed"), false, true);
            return;
        }
        if (routing.inputIndex === "" || !Number.isInteger(inputIndex)) {
            setAudioStatus(t("start_required_devices"), false, true);
            return;
        }
        const virtualOutput = devices.outputs.some((device) => device.isVirtualOutput
            && device.index === outputIndex
            && (!virtualOutputSetupSupported || isCableInput(device)));
        if (!virtualOutput) {
            setAudioStatus(t("virtual_output_required"), false, true);
            return;
        }
        setAudioStatus(t("audio_starting"), false);
        const result = await coreRequest("start_audio", {
            input_index: inputIndex,
            output_index: outputIndex,
            blocksize: Number(routing.blocksize) || 512,
            monitor_enabled: routing.monitorEnabled,
        });
        audioRunning = Boolean(result.started);
        updateAudioButton();
        setAudioStatus(result.monitorError || result.message || (audioRunning ? t("audio_started") : t("stopped")),
            audioRunning, !audioRunning || Boolean(result.monitorError));
    } catch (error) {
        audioRunning = false;
        updateAudioButton();
        setAudioStatus(`${t("audio_error")}: ${String(error)}`, false, true);
    } finally {
        button.disabled = false;
        monitorControl.disabled = false;
    }
}

function setBypass(enabled) {
    params.bypass = Boolean(enabled);
    updateBypassButton();
    scheduleParameterUpdate("bypass", params.bypass, true);
}

function releaseHeldHotkey() {
    if (hotkeyDown && holdBaseBypass !== null) setBypass(holdBaseBypass);
    hotkeyDown = false;
    holdBaseBypass = null;
}

function pressHotkey() {
    if (captureHotkey || !document.querySelector("#hotkey-enabled").checked) return;
    if (hotkeyDown) return;
    hotkeyDown = true;
    if (document.querySelector("#hotkey-hold").checked) {
        holdBaseBypass = Boolean(params.bypass);
        setBypass(!holdBaseBypass);
    } else {
        setBypass(!params.bypass);
    }
    playHotkeyFeedback();
}

function renderGlobalHotkeyStatus() {
    const status = document.querySelector("#hotkey-status");
    if (!captureHotkey) {
        document.querySelector("#hotkey-key").textContent =
            portalHotkeyDescription || formatHotkey(hotkey);
    }
    status.textContent = hotkeyGlobalError ? t("hotkey_local_only") : "";
    status.title = hotkeyGlobalError;
    status.hidden = !status.textContent;
}

function handleGlobalHotkey(state) {
    if (waylandHotkeys && typeof state?.description === "string") {
        portalHotkeyDescription = state.description;
        renderGlobalHotkeyStatus();
        return;
    }
    if (state === "Pressed" && registeredHotkey === hotkey) pressHotkey();
    if (state === "Released") releaseHeldHotkey();
    if (state === "Unavailable") {
        releaseHeldHotkey();
        registeredHotkey = null;
        portalHotkeyDescription = "";
        hotkeyGlobalError = "XDG GlobalShortcuts session closed";
        renderGlobalHotkeyStatus();
    }
}

function configureGlobalHotkey() {
    if (!("__TAURI_INTERNALS__" in window)) return Promise.resolve();

    hotkeyRegistrationQueue = hotkeyRegistrationQueue.then(async () => {
        const desiredHotkey = !captureHotkey
            && document.querySelector("#hotkey-enabled").checked
            ? hotkey
            : null;
        if (registeredHotkey === desiredHotkey && (!hotkeyGlobalError || desiredHotkey)) return;
        try {
            if (desiredHotkey) {
                listenForGlobalHotkey ??= await listen("voxcraft-global-hotkey", ({ payload }) => {
                    handleGlobalHotkey(payload);
                });
            }
            const previous = registeredHotkey;
            portalHotkeyDescription = "";
            if (previous || desiredHotkey) {
                waylandHotkeys ??= await invoke("is_wayland_session");
                if (waylandHotkeys) {
                    registeredHotkey = null;
                    portalHotkeyDescription =
                        await invoke("set_wayland_global_shortcut", { shortcut: desiredHotkey }) ?? "";
                } else {
                    if (previous) {
                        await invoke("configure_native_hotkey", { shortcut: previous, enabled: false });
                        registeredHotkey = null;
                    }
                    if (desiredHotkey) {
                        await invoke("configure_native_hotkey", { shortcut: desiredHotkey, enabled: true });
                    }
                }
            }
            releaseHeldHotkey();
            registeredHotkey = desiredHotkey;
            hotkeyGlobalError = "";
        } catch (error) {
            hotkeyGlobalError = String(error);
            console.error("Não foi possível configurar o atalho global:", error);
        }
        renderGlobalHotkeyStatus();
    });

    return hotkeyRegistrationQueue;
}

function setupHotkey() {
    playHotkeyFeedback = setupHotkeyFeedback();
    const keyButton = document.querySelector("#hotkey-key");
    hotkey = normalizeHotkey(hotkey);
    localStorage.setItem("voxcraft-hotkey", hotkey);
    const finishCapture = () => {
        const wasCapturing = captureHotkey;
        captureHotkey = false;
        keyButton.classList.remove("is-capturing");
        renderGlobalHotkeyStatus();
        if (wasCapturing) void configureGlobalHotkey();
    };
    keyButton.textContent = formatHotkey(hotkey);
    keyButton.addEventListener("click", async () => {
        await hotkeyRegistrationQueue;
        if (waylandHotkeys && registeredHotkey) {
            keyButton.disabled = true;
            try {
                await invoke("configure_wayland_global_shortcut");
            } catch (error) {
                await showMessage({ title: t("notice"), message: String(error) });
            } finally {
                keyButton.disabled = false;
            }
            return;
        }
        captureHotkey = true;
        releaseHeldHotkey();
        keyButton.textContent = t("key_capture");
        keyButton.classList.add("is-capturing");
        void configureGlobalHotkey();
    });
    document.querySelector("#settings-dialog").addEventListener("close", finishCapture);

    document.querySelector("#hotkey-enabled").checked =
        localStorage.getItem("voxcraft-hotkey-enabled") !== "false";
    document.querySelector("#hotkey-hold").checked =
        localStorage.getItem("voxcraft-hotkey-hold") === "true";
    const hotkeyEnabledControl = document.querySelector("#hotkey-enabled");
    const hotkeyHoldControl = document.querySelector("#hotkey-hold");
    const syncHotkeyHoldControl = () => {
        hotkeyHoldControl.disabled = !hotkeyEnabledControl.checked;
        if (hotkeyHoldControl.disabled && hotkeyHoldControl.checked) {
            hotkeyHoldControl.checked = false;
            localStorage.setItem("voxcraft-hotkey-hold", "false");
        }
    };
    syncHotkeyHoldControl();
    document.querySelector("#hotkey-enabled").addEventListener("change", (event) => {
        localStorage.setItem("voxcraft-hotkey-enabled", String(event.target.checked));
        if (!event.target.checked) releaseHeldHotkey();
        syncHotkeyHoldControl();
        void configureGlobalHotkey();
    });
    document.querySelector("#hotkey-hold").addEventListener("change", (event) => {
        if (!hotkeyEnabledControl.checked) return;
        localStorage.setItem("voxcraft-hotkey-hold", String(event.target.checked));
        releaseHeldHotkey();
    });

    window.addEventListener("keydown", (event) => {
        if (captureHotkey) {
            event.preventDefault();
            event.stopImmediatePropagation();
            const modifiers = hotkeyModifiersFromEvent(event);
            if (event.code === "Escape" && modifiers.length === 0) {
                finishCapture();
                return;
            }

            if (modifierKeyFromEvent(event)) {
                keyButton.textContent = formatHotkeyCapture(modifiers);
                return;
            }

            const key = normalizeHotkeyKey(event.code || event.key);
            hotkey = normalizeHotkey([...modifiers, key].join("+"));
            localStorage.setItem("voxcraft-hotkey", hotkey);
            finishCapture();
            return;
        }
        if (registeredHotkey === hotkey || event.repeat
            || !document.querySelector("#hotkey-enabled").checked
            || !matchesHotkeyEvent(event, hotkey)) return;
        const target = event.target;
        if (target instanceof HTMLElement && ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)) return;
        event.preventDefault();
        pressHotkey();
    });
    window.addEventListener("keyup", (event) => {
        if (captureHotkey && modifierKeyFromEvent(event)) {
            keyButton.textContent = formatHotkeyCapture(hotkeyModifiersFromEvent(event));
            return;
        }
        const modifier = modifierKeyFromEvent(event);
        const { key, modifiers } = hotkeyParts(hotkey);
        if (registeredHotkey !== hotkey && hotkeyDown
            && (event.code === key || (modifier && modifiers.has(modifier)))) {
            releaseHeldHotkey();
        }
    });
    window.addEventListener("blur", () => {
        if (registeredHotkey !== hotkey) releaseHeldHotkey();
    });

    void configureGlobalHotkey();
}

function applyStoredThemeAndLanguage() {
    document.querySelector("#theme-select").value = theme;
    document.querySelector("#language-select").value = language;
    applyTheme(theme);
    applyLanguage(language);
}

function buildDynamicsControls() {
    const container = document.querySelector("#dynamics-controls");
    container.append(
        createSlider(slider("input_gain_db", "input_gain", -18, 24, 0.5, "dB")),
        createSlider(slider("gate_threshold_db", "gate_thresh", -65, -15, 0.5, "dB")),
        createSlider(slider("comp_threshold_db", "comp_thresh", -36, -4, 0.5, "dB")),
        createSlider(slider("output_gain_db", "output_vol", -24, 24, 0.5, "dB")),
    );
}

function setupDialogs() {
    const modalLayer = document.querySelector("#modal-layer");
    const appShell = document.querySelector(".app-shell");
    const titlebar = appShell.querySelector(".window-titlebar");
    const dialogs = [...document.querySelectorAll(".dialog")];
    let activeDialog = null;
    let restoreFocusTo = null;
    const messageDialog = document.querySelector("#message-dialog");
    const messageForm = document.querySelector("#message-form");
    const messageTitle = document.querySelector("#message-title");
    const messageText = document.querySelector("#message-text");
    const messageInput = document.querySelector("#message-input");
    const messageCancel = document.querySelector("#message-cancel");
    const messageAccept = document.querySelector("#message-accept");
    let pendingMessage = null;

    const setContentInert = (inert) => {
        for (const child of appShell.children) {
            if (child !== titlebar && child !== modalLayer) child.inert = inert;
        }
    };

    const closeDialog = (dialog) => {
        if (dialog.open) dialog.close();
    };

    const openDialog = (dialog, initialFocus) => {
        if (activeDialog === dialog) return;
        const trigger = activeDialog ? restoreFocusTo : document.activeElement;
        if (activeDialog) closeDialog(activeDialog);

        restoreFocusTo = trigger;
        activeDialog = dialog;
        modalLayer.hidden = false;
        setContentInert(true);
        dialog.setAttribute("aria-modal", "true");
        dialog.show();

        const firstFocusable = dialog.querySelector(
            '[autofocus], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
        );
        (initialFocus || firstFocusable || dialog).focus();
    };

    for (const dialog of dialogs) {
        dialog.addEventListener("close", () => {
            if (dialog === messageDialog && pendingMessage) {
                const { resolve, value } = pendingMessage;
                pendingMessage = null;
                resolve(value);
            }
            if (activeDialog !== dialog) return;
            activeDialog = null;
            dialog.removeAttribute("aria-modal");
            modalLayer.hidden = true;
            setContentInert(false);

            if (restoreFocusTo instanceof HTMLElement && restoreFocusTo.isConnected) {
                restoreFocusTo.focus({ preventScroll: true });
            }
            restoreFocusTo = null;
        });
    }

    showMessage = ({ type = "alert", title, message, acceptLabel = "OK", danger = false }) => {
        if (pendingMessage) return Promise.resolve(null);

        messageTitle.textContent = title;
        messageText.textContent = message;
        messageInput.value = "";
        messageInput.hidden = type !== "input";
        messageCancel.hidden = type === "alert";
        messageAccept.disabled = type === "input";
        messageAccept.textContent = acceptLabel;
        messageAccept.classList.toggle("button-danger", danger);
        messageAccept.classList.toggle("button-primary", !danger);

        return new Promise((resolve) => {
            pendingMessage = { resolve, value: null, type };
            openDialog(messageDialog, type === "input" ? messageInput
                : type === "confirm" ? messageCancel : messageAccept);
        });
    };

    messageInput.addEventListener("input", () => {
        messageAccept.disabled = !messageInput.value.trim();
    });
    messageForm.addEventListener("submit", (event) => {
        event.preventDefault();
        if (!pendingMessage || messageAccept.disabled) return;
        pendingMessage.value = pendingMessage.type === "input" ? messageInput.value.trim() : true;
        closeDialog(messageDialog);
    });

    window.addEventListener("keydown", (event) => {
        if (!activeDialog || captureHotkey) return;

        if (event.key === "Escape") {
            event.preventDefault();
            event.stopImmediatePropagation();
            closeDialog(activeDialog);
            return;
        }
        if (event.key !== "Tab") return;

        const focusable = [...activeDialog.querySelectorAll(
            'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
        )].filter((element) => element.getClientRects().length > 0);
        if (focusable.length === 0) {
            event.preventDefault();
            activeDialog.focus();
            return;
        }

        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!activeDialog.contains(document.activeElement)) {
            event.preventDefault();
            (event.shiftKey ? last : first).focus();
        } else if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }, true);

    document.querySelector("#open-settings").addEventListener("click", () => {
        if (pendingMessage) return;
        openDialog(document.querySelector("#settings-dialog"));
    });
    document.querySelector("#open-updates").addEventListener("click", () => {
        const dialog = document.querySelector("#updates-dialog");
        if (pendingMessage) return;
        openDialog(dialog);
        const button = document.querySelector("#check-updates");
        if (button.dataset.action === "check") button.click();
    });
    document.querySelectorAll("[data-close-dialog]").forEach((button) => {
        button.addEventListener("click", () =>
            closeDialog(document.querySelector(`#${button.dataset.closeDialog}`)));
    });
    document.querySelector("#theme-select").addEventListener("change", (event) => applyTheme(event.target.value));
    document.querySelector("#language-select").addEventListener("change", (event) => applyLanguage(event.target.value));
}

function setupEvents() {
    document.querySelector("#preset-select").addEventListener("change", (event) => {
        const value = event.target.value;
        if (value) {
            void applyPreset(value);
        } else {
            selectedPreset = "";
            saveVoiceSettings();
            renderPresets();
        }
    });
    document.querySelector("#save-preset").addEventListener("click", () => void savePreset());
    document.querySelector("#delete-preset").addEventListener("click", () => void deletePreset());
    document.querySelector("#power-button").addEventListener("click", () => void toggleAudio());
    document.querySelector("#bypass-button").addEventListener("click", () => setBypass(!params.bypass));
    document.querySelector("#refresh-devices").addEventListener("click", () => void refreshDevices());
    document.querySelector("#configure-virtual-output").addEventListener("click", () => void configureVirtualOutput());
    ["input-device", "latency-select"].forEach((id) => {
        document.querySelector(`#${id}`).addEventListener("change", updateRoutingFromControls);
    });
    const latencySelect = document.querySelector("#latency-select");
    const savedBlocksize = String(routing.blocksize);
    if ([...latencySelect.options].some((option) => option.value === savedBlocksize)) {
        latencySelect.value = savedBlocksize;
    }
    const monitorControl = document.querySelector("#monitor-enabled");
    monitorControl.checked = routing.monitorEnabled === true;
    monitorControl.addEventListener("change", () => void updateMonitor(monitorControl));
}

async function connectCore() {
    if (!("__TAURI_INTERNALS__" in window)) {
        setAudioStatus(t("browser_mode"), false, true);
        return;
    }

    const powerButton = document.querySelector("#power-button");
    powerButton.disabled = true;
    setAudioStatus(t("core_starting"), false);
    try {
        const status = await invoke("get_runtime_status");
        if (!status.coreConnected) {
            setAudioStatus(status.message || t("core_unavailable"), false, true);
            return;
        }
        const [loadedParams, presetList] = await Promise.all([
            coreRequest("get_params"),
            coreRequest("list_presets"),
        ]);
        let virtualOutputSetup = {
            supported: false,
            available: false,
            microphoneAvailable: true,
            created: false,
            canRetry: false,
            message: null,
        };
        try {
            virtualOutputSetup = await coreRequest("ensure_virtual_output");
        } catch (error) {
            virtualOutputSetup.message = String(error);
        }
        virtualOutputSetupSupported = virtualOutputSetup.supported === true;
        virtualOutputSetupCanRetry = virtualOutputSetup.canRetry === true;
        virtualMicrophoneAvailable = virtualOutputSetup.microphoneAvailable !== false;
        const deviceList = await coreRequest("list_devices");
        const saved = readStoredVoiceSettings();
        const savedParams = Object.fromEntries(Object.entries(loadedParams).flatMap(([key, fallback]) => {
            const value = saved.params?.[key];
            return typeof value === typeof fallback && (typeof value !== "number" || Number.isFinite(value))
                ? [[key, value]]
                : [];
        }));
        params = Object.keys(savedParams).length
            ? await coreRequest("set_params", { params: savedParams })
            : loadedParams;
        presetNames = presetList;
        if (typeof saved.selectedPreset === "string") {
            const custom = saved.selectedPreset.startsWith("★ ");
            const name = custom ? saved.selectedPreset.slice(2) : saved.selectedPreset;
            if ((custom ? presetNames.custom : presetNames.builtIn).includes(name)) {
                selectedPreset = saved.selectedPreset;
            }
        }
        devices = deviceList;
        coreConnected = true;
        renderPresets();
        renderDevices();
        renderControlValues();
        if (virtualOutputSetup.supported
            && (!virtualOutputSetup.available || !virtualMicrophoneAvailable)) {
            setAudioStatus(
                virtualOutputSetup.message || (!virtualMicrophoneAvailable
                    ? t("virtual_microphone_setup_failed")
                    : t("virtual_output_setup_failed")),
                false,
                true,
            );
        } else {
            setAudioStatus(t("stopped"), false);
        }
        window.setInterval(() => void pollMeters(), 180);
    } catch (error) {
        coreConnected = false;
        setAudioStatus(`${t("core_unavailable")}: ${String(error)}`, false, true);
    } finally {
        powerButton.disabled = !coreConnected;
    }
}

export function initializeStudio() {
    buildDynamicsControls();
    renderTabs();
    applyStoredThemeAndLanguage();
    setupEvents();
    setupDialogs();
    setupWindowControls(t);
    setupHotkey();
    updateAudioButton();
    updateBypassButton();
    setupUpdater();

    window.addEventListener("resize", () => {
        drawEqCurve();
        drawWaveform([]);
    });

    if ("__TAURI_INTERNALS__" in window) {
        // Reveal the themed shell first; startup of the audio engine must not gate it.
        void getCurrentWindow().show()
            .catch((error) => console.error("Não foi possível mostrar a janela:", error))
            .then(connectCore);
    } else {
        void connectCore();
    }
}
