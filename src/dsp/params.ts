export type RingWaveform = "Senoide" | "Quadrada" | "Triangular";

export interface DSPParams {
  // Controle geral
  bypass: boolean;
  input_gain_db: number;
  output_gain_db: number;

  // Noise Gate & Compressor (Limpeza para Discord)
  gate_enabled: boolean;
  gate_threshold_db: number;
  comp_enabled: boolean;
  comp_threshold_db: number;
  comp_ratio: number;

  // Alterar Tom (Pitch Shifter estilo Audacity)
  pitch_enabled: boolean;
  pitch_semitones: number; // -12.0 a +12.0
  pitch_cents: number; // -100.0 a +100.0
  pitch_mix: number; // 0.0 a 1.0

  // Frequency Shifter (Deslocamento linear em Hz - Hilbert SSB)
  freq_shift_enabled: boolean;
  freq_shift_hz: number; // -500.0 a +500.0 Hz
  freq_shift_mix: number;

  // Equalizador (Filtro + 5 Bandas estilo Audacity)
  eq_enabled: boolean;
  eq_hpf_enabled: boolean;
  eq_hpf_hz: number; // Corte de graves (Low-Cut)
  eq_lpf_enabled: boolean;
  eq_lpf_hz: number; // Corte de agudos (High-Cut)
  eq_band1_db: number; // Grave (120 Hz)
  eq_band2_db: number; // Médio-Grave (400 Hz)
  eq_band3_db: number; // Médio / Presença (1200 Hz)
  eq_band4_db: number; // Médio-Agudo (3500 Hz)
  eq_band5_db: number; // Agudo / Brilho (7500 Hz)

  // Modulador (Robô / Alien / Tremolo)
  ring_enabled: boolean;
  ring_freq_hz: number; // 5 a 400 Hz
  ring_waveform: RingWaveform;
  ring_mix: number;

  // Distorção & Lo-Fi / Rádio (Overdrive + Bitcrusher)
  dist_enabled: boolean;
  dist_drive: number; // 1.0 a 25.0
  dist_bits: number; // 4 a 16 bits
  dist_downsample: number; // 1 a 16x
  dist_mix: number;

  // Eco / Delay
  echo_enabled: boolean;
  echo_delay_ms: number; // 10 a 700 ms
  echo_feedback: number; // 0.0 a 0.85
  echo_mix: number;

  // Reverb (Espaço / Sala)
  reverb_enabled: boolean;
  reverb_room: number; // 0.0 a 1.0
  reverb_damp: number; // 0.0 a 1.0
  reverb_mix: number;
}

export function createDefaultParams(overrides: Partial<DSPParams> = {}): DSPParams {
  return {
    bypass: false,
    input_gain_db: 0.0,
    output_gain_db: 0.0,

    gate_enabled: true,
    gate_threshold_db: -42.0,
    comp_enabled: true,
    comp_threshold_db: -18.0,
    comp_ratio: 4.0,

    pitch_enabled: false,
    pitch_semitones: 0.0,
    pitch_cents: 0.0,
    pitch_mix: 1.0,

    freq_shift_enabled: false,
    freq_shift_hz: 0.0,
    freq_shift_mix: 1.0,

    eq_enabled: true,
    eq_hpf_enabled: true,
    eq_hpf_hz: 80.0,
    eq_lpf_enabled: false,
    eq_lpf_hz: 12000.0,
    eq_band1_db: 0.0,
    eq_band2_db: 0.0,
    eq_band3_db: 0.0,
    eq_band4_db: 0.0,
    eq_band5_db: 0.0,

    ring_enabled: false,
    ring_freq_hz: 60.0,
    ring_waveform: "Senoide",
    ring_mix: 0.7,

    dist_enabled: false,
    dist_drive: 3.0,
    dist_bits: 16,
    dist_downsample: 1,
    dist_mix: 0.7,

    echo_enabled: false,
    echo_delay_ms: 220.0,
    echo_feedback: 0.35,
    echo_mix: 0.35,

    reverb_enabled: false,
    reverb_room: 0.6,
    reverb_damp: 0.45,
    reverb_mix: 0.3,

    ...overrides,
  };
}
