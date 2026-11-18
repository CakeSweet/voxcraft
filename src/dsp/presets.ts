import { createDefaultParams, type DSPParams } from "./params";

const USER_PRESETS_KEY = "voxcraft_user_presets_v1";

export function getBuiltinPresets(): Record<string, DSPParams> {
  return {
    "Normal (Limpo + Gate)": createDefaultParams({
      gate_enabled: true,
      gate_threshold_db: -44.0,
      comp_enabled: true,
      eq_enabled: true,
      eq_hpf_enabled: true,
      eq_hpf_hz: 80.0,
      eq_band3_db: 1.5,
      eq_band5_db: 2.0,
    }),
    "Voz Grossa / Demônio": createDefaultParams({
      pitch_enabled: true,
      pitch_semitones: -5.5,
      pitch_mix: 1.0,
      freq_shift_enabled: true,
      freq_shift_hz: -18.0,
      freq_shift_mix: 0.65,
      eq_enabled: true,
      eq_hpf_enabled: true,
      eq_hpf_hz: 45.0,
      eq_band1_db: 6.5,
      eq_band2_db: 3.0,
      eq_band4_db: -2.0,
      dist_enabled: true,
      dist_drive: 2.4,
      dist_bits: 16,
      dist_downsample: 1,
      dist_mix: 0.35,
      reverb_enabled: true,
      reverb_room: 0.72,
      reverb_damp: 0.55,
      reverb_mix: 0.32,
    }),
    "Voz Fina / Esquilo": createDefaultParams({
      pitch_enabled: true,
      pitch_semitones: 6.5,
      pitch_mix: 1.0,
      eq_enabled: true,
      eq_hpf_enabled: true,
      eq_hpf_hz: 120.0,
      eq_band1_db: -3.0,
      eq_band4_db: 3.5,
      eq_band5_db: 3.0,
    }),
    "Robô / Ciborgue": createDefaultParams({
      ring_enabled: true,
      ring_freq_hz: 62.0,
      ring_waveform: "Senoide",
      ring_mix: 0.82,
      echo_enabled: true,
      echo_delay_ms: 16.0,
      echo_feedback: 0.62,
      echo_mix: 0.55,
      eq_enabled: true,
      eq_hpf_enabled: true,
      eq_hpf_hz: 180.0,
      eq_band3_db: 5.0,
    }),
    "Alienígena (Freq Shifter)": createDefaultParams({
      pitch_enabled: true,
      pitch_semitones: -2.0,
      pitch_mix: 0.85,
      freq_shift_enabled: true,
      freq_shift_hz: 145.0,
      freq_shift_mix: 0.85,
      reverb_enabled: true,
      reverb_room: 0.65,
      reverb_damp: 0.25,
      reverb_mix: 0.35,
    }),
    "Rádio Militar / Walkie-Talkie": createDefaultParams({
      eq_enabled: true,
      eq_hpf_enabled: true,
      eq_hpf_hz: 480.0,
      eq_lpf_enabled: true,
      eq_lpf_hz: 2600.0,
      eq_band3_db: 10.0,
      eq_band4_db: 4.0,
      dist_enabled: true,
      dist_drive: 6.5,
      dist_bits: 10,
      dist_downsample: 2,
      dist_mix: 0.72,
    }),
    "Capacete / Darth Vader": createDefaultParams({
      pitch_enabled: true,
      pitch_semitones: -3.5,
      pitch_mix: 1.0,
      eq_enabled: true,
      eq_hpf_enabled: true,
      eq_hpf_hz: 60.0,
      eq_lpf_enabled: true,
      eq_lpf_hz: 4500.0,
      eq_band1_db: 7.0,
      eq_band2_db: 4.5,
      echo_enabled: true,
      echo_delay_ms: 14.0,
      echo_feedback: 0.52,
      echo_mix: 0.45,
    }),
    "Caverna / Eco Épico": createDefaultParams({
      eq_enabled: true,
      eq_hpf_enabled: true,
      eq_hpf_hz: 70.0,
      eq_band1_db: 3.5,
      echo_enabled: true,
      echo_delay_ms: 330.0,
      echo_feedback: 0.45,
      echo_mix: 0.42,
      reverb_enabled: true,
      reverb_room: 0.92,
      reverb_damp: 0.38,
      reverb_mix: 0.52,
    }),
    "Voz Anônima (Entrevista)": createDefaultParams({
      pitch_enabled: true,
      pitch_semitones: -4.0,
      pitch_mix: 1.0,
      freq_shift_enabled: true,
      freq_shift_hz: -32.0,
      freq_shift_mix: 0.7,
      eq_enabled: true,
      eq_hpf_enabled: true,
      eq_hpf_hz: 65.0,
      eq_lpf_enabled: true,
      eq_lpf_hz: 5500.0,
      eq_band2_db: 4.0,
    }),
  };
}

export function loadUserPresets(): Record<string, DSPParams> {
  try {
    const raw = localStorage.getItem(USER_PRESETS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, Partial<DSPParams>>;
    const out: Record<string, DSPParams> = {};
    for (const [name, data] of Object.entries(parsed)) {
      if (data && typeof data === "object") {
        out[name] = createDefaultParams(data);
      }
    }
    return out;
  } catch {
    return {};
  }
}

export function saveUserPresets(userPresets: Record<string, DSPParams>): void {
  try {
    localStorage.setItem(USER_PRESETS_KEY, JSON.stringify(userPresets));
  } catch {
    // Ignore storage quota errors
  }
}
