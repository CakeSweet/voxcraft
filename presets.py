import json
import os
from dataclasses import asdict
from dsp_engine import DSPParams

USER_PRESETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_presets.json")


def get_builtin_presets() -> dict[str, DSPParams]:
    return {
        "Normal (Limpo + Gate)": DSPParams(
            gate_enabled=True,
            gate_threshold_db=-44.0,
            comp_enabled=True,
            eq_enabled=True,
            eq_hpf_enabled=True,
            eq_hpf_hz=80.0,
            eq_band3_db=1.5,
            eq_band5_db=2.0,
        ),
        "Voz Grossa / Demônio": DSPParams(
            pitch_enabled=True,
            pitch_semitones=-5.5,
            pitch_mix=1.0,
            freq_shift_enabled=True,
            freq_shift_hz=-18.0,
            freq_shift_mix=0.65,
            eq_enabled=True,
            eq_hpf_enabled=True,
            eq_hpf_hz=45.0,
            eq_band1_db=6.5,
            eq_band2_db=3.0,
            eq_band4_db=-2.0,
            dist_enabled=True,
            dist_drive=2.4,
            dist_bits=16,
            dist_downsample=1,
            dist_mix=0.35,
            reverb_enabled=True,
            reverb_room=0.72,
            reverb_damp=0.55,
            reverb_mix=0.32,
        ),
        "Voz Fina / Esquilo": DSPParams(
            pitch_enabled=True,
            pitch_semitones=6.5,
            pitch_mix=1.0,
            eq_enabled=True,
            eq_hpf_enabled=True,
            eq_hpf_hz=120.0,
            eq_band1_db=-3.0,
            eq_band4_db=3.5,
            eq_band5_db=3.0,
        ),
        "Robô / Ciborgue": DSPParams(
            ring_enabled=True,
            ring_freq_hz=62.0,
            ring_waveform="Senoide",
            ring_mix=0.82,
            echo_enabled=True,
            echo_delay_ms=16.0,
            echo_feedback=0.62,
            echo_mix=0.55,
            eq_enabled=True,
            eq_hpf_enabled=True,
            eq_hpf_hz=180.0,
            eq_band3_db=5.0,
        ),
        "Alienígena (Freq Shifter)": DSPParams(
            pitch_enabled=True,
            pitch_semitones=-2.0,
            pitch_mix=0.85,
            freq_shift_enabled=True,
            freq_shift_hz=145.0,
            freq_shift_mix=0.85,
            reverb_enabled=True,
            reverb_room=0.65,
            reverb_damp=0.25,
            reverb_mix=0.35,
        ),
        "Rádio Militar / Walkie-Talkie": DSPParams(
            eq_enabled=True,
            eq_hpf_enabled=True,
            eq_hpf_hz=480.0,
            eq_lpf_enabled=True,
            eq_lpf_hz=2600.0,
            eq_band3_db=10.0,
            eq_band4_db=4.0,
            dist_enabled=True,
            dist_drive=6.5,
            dist_bits=10,
            dist_downsample=2,
            dist_mix=0.72,
        ),
        "Capacete / Darth Vader": DSPParams(
            pitch_enabled=True,
            pitch_semitones=-3.5,
            pitch_mix=1.0,
            eq_enabled=True,
            eq_hpf_enabled=True,
            eq_hpf_hz=60.0,
            eq_lpf_enabled=True,
            eq_lpf_hz=4500.0,
            eq_band1_db=7.0,
            eq_band2_db=4.5,
            echo_enabled=True,
            echo_delay_ms=14.0,
            echo_feedback=0.52,
            echo_mix=0.45,
        ),
        "Caverna / Eco Épico": DSPParams(
            eq_enabled=True,
            eq_hpf_enabled=True,
            eq_hpf_hz=70.0,
            eq_band1_db=3.5,
            echo_enabled=True,
            echo_delay_ms=330.0,
            echo_feedback=0.45,
            echo_mix=0.42,
            reverb_enabled=True,
            reverb_room=0.92,
            reverb_damp=0.38,
            reverb_mix=0.52,
        ),
        "Voz Anônima (Entrevista)": DSPParams(
            pitch_enabled=True,
            pitch_semitones=-4.0,
            pitch_mix=1.0,
            freq_shift_enabled=True,
            freq_shift_hz=-32.0,
            freq_shift_mix=0.7,
            eq_enabled=True,
            eq_hpf_enabled=True,
            eq_hpf_hz=65.0,
            eq_lpf_enabled=True,
            eq_lpf_hz=5500.0,
            eq_band2_db=4.0,
        ),
    }


def load_user_presets() -> dict[str, DSPParams]:
    if not os.path.exists(USER_PRESETS_FILE):
        return {}
    try:
        with open(USER_PRESETS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        out = {}
        valid_fields = set(asdict(DSPParams()).keys())
        for name, data in raw.items():
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            out[name] = DSPParams(**filtered)
        return out
    except Exception:
        return {}


def save_user_presets(user_presets: dict[str, DSPParams]):
    serializable = {name: asdict(params) for name, params in user_presets.items()}
    with open(USER_PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
