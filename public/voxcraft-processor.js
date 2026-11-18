// Real-Time DSP AudioWorkletProcessor faithfully ported from dsp_engine.py

function clip(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

function biquadLowpass(fc, q, fs) {
  const f = clip(fc, 20.0, fs * 0.48);
  const w0 = (2.0 * Math.PI * f) / fs;
  const alpha = Math.sin(w0) / (2.0 * q);
  const cosW0 = Math.cos(w0);
  const b0 = (1.0 - cosW0) / 2.0;
  const b1 = 1.0 - cosW0;
  const b2 = (1.0 - cosW0) / 2.0;
  const a0 = 1.0 + alpha;
  const a1 = -2.0 * cosW0;
  const a2 = 1.0 - alpha;
  return [b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0];
}

function biquadHighpass(fc, q, fs) {
  const f = clip(fc, 20.0, fs * 0.48);
  const w0 = (2.0 * Math.PI * f) / fs;
  const alpha = Math.sin(w0) / (2.0 * q);
  const cosW0 = Math.cos(w0);
  const b0 = (1.0 + cosW0) / 2.0;
  const b1 = -(1.0 + cosW0);
  const b2 = (1.0 + cosW0) / 2.0;
  const a0 = 1.0 + alpha;
  const a1 = -2.0 * cosW0;
  const a2 = 1.0 - alpha;
  return [b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0];
}

function biquadPeaking(fc, gainDb, q, fs) {
  const f = clip(fc, 20.0, fs * 0.48);
  const A = Math.pow(10.0, gainDb / 40.0);
  const w0 = (2.0 * Math.PI * f) / fs;
  const alpha = Math.sin(w0) / (2.0 * q);
  const cosW0 = Math.cos(w0);
  const b0 = 1.0 + alpha * A;
  const b1 = -2.0 * cosW0;
  const b2 = 1.0 - alpha * A;
  const a0 = 1.0 + alpha / A;
  const a1 = -2.0 * cosW0;
  const a2 = 1.0 - alpha / A;
  return [b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0];
}

function biquadLowShelf(fc, gainDb, fs, slope = 0.85) {
  const f = clip(fc, 20.0, fs * 0.48);
  const A = Math.pow(10.0, gainDb / 40.0);
  const w0 = (2.0 * Math.PI * f) / fs;
  const cosW0 = Math.cos(w0);
  const sinW0 = Math.sin(w0);
  const alpha = (sinW0 / 2.0) * Math.sqrt((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0);
  const sqrtA2 = 2.0 * Math.sqrt(A) * alpha;
  const b0 = A * (A + 1.0 - (A - 1.0) * cosW0 + sqrtA2);
  const b1 = 2.0 * A * (A - 1.0 - (A + 1.0) * cosW0);
  const b2 = A * (A + 1.0 - (A - 1.0) * cosW0 - sqrtA2);
  const a0 = A + 1.0 + (A - 1.0) * cosW0 + sqrtA2;
  const a1 = -2.0 * (A - 1.0 + (A + 1.0) * cosW0);
  const a2 = A + 1.0 + (A - 1.0) * cosW0 - sqrtA2;
  return [b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0];
}

function biquadHighShelf(fc, gainDb, fs, slope = 0.85) {
  const f = clip(fc, 20.0, fs * 0.48);
  const A = Math.pow(10.0, gainDb / 40.0);
  const w0 = (2.0 * Math.PI * f) / fs;
  const cosW0 = Math.cos(w0);
  const sinW0 = Math.sin(w0);
  const alpha = (sinW0 / 2.0) * Math.sqrt((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0);
  const sqrtA2 = 2.0 * Math.sqrt(A) * alpha;
  const b0 = A * (A + 1.0 + (A - 1.0) * cosW0 + sqrtA2);
  const b1 = -2.0 * A * (A - 1.0 + (A + 1.0) * cosW0);
  const b2 = A * (A + 1.0 + (A - 1.0) * cosW0 - sqrtA2);
  const a0 = A + 1.0 - (A - 1.0) * cosW0 + sqrtA2;
  const a1 = 2.0 * (A - 1.0 - (A + 1.0) * cosW0);
  const a2 = A + 1.0 - (A - 1.0) * cosW0 - sqrtA2;
  return [b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0];
}

function buildEqSos(p, fs) {
  const rows = [];
  if (p.eq_hpf_enabled) {
    rows.push(biquadHighpass(p.eq_hpf_hz, 0.707, fs));
  } else {
    rows.push([1.0, 0.0, 0.0, 0.0, 0.0]);
  }
  rows.push(biquadLowShelf(120.0, p.eq_band1_db, fs));
  rows.push(biquadPeaking(400.0, p.eq_band2_db, 1.0, fs));
  rows.push(biquadPeaking(1200.0, p.eq_band3_db, 1.0, fs));
  rows.push(biquadPeaking(3500.0, p.eq_band4_db, 1.0, fs));
  rows.push(biquadHighShelf(7500.0, p.eq_band5_db, fs));
  if (p.eq_lpf_enabled) {
    rows.push(biquadLowpass(p.eq_lpf_hz, 0.707, fs));
  } else {
    rows.push([1.0, 0.0, 0.0, 0.0, 0.0]);
  }
  return rows;
}

class RingDelay {
  constructor(maxSamples) {
    this.size = Math.max(128, Math.floor(maxSamples));
    this.buf = new Float32Array(this.size);
    this.writeIdx = 0;
  }

  readSample(delaySamples) {
    const delay = Math.max(1, Math.min(delaySamples, this.size - 1));
    let idx = this.writeIdx - delay;
    if (idx < 0) idx += this.size;
    return this.buf[idx];
  }

  writeSample(val) {
    this.buf[this.writeIdx] = val;
    this.writeIdx = (this.writeIdx + 1) % this.size;
  }
}

class VoxCraftProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.sr = sampleRate;
    this.params = {
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
    };

    this.inputPeakDb = -60.0;
    this.outputPeakDb = -60.0;
    this.gateIsOpen = true;
    this.lastWaveform = new Float32Array(256);
    this._waveWriteIdx = 0;
    this._telemetryCounter = 0;

    this._initStates();

    this.port.onmessage = (event) => {
      const msg = event.data;
      if (msg && msg.type === "params") {
        this.params = msg.params;
        this._eqDirty = true;
      }
    };
  }

  _initStates() {
    const sr = this.sr;

    // Noise Gate & Compressor
    this._gateGain = 1.0;
    this._gateHoldCounter = 0;
    this._compGain = 1.0;

    // Pitch Shifter (Dual-Tap Delay Line, window ~45ms)
    this._pitchW = Math.floor(0.045 * sr);
    this._pitchHistLen = this._pitchW + 16;
    this._pitchHist = new Float32Array(this._pitchHistLen);
    this._pitchPhase = 0.0;

    // Frequency Shifter (65-tap Hilbert FIR)
    const nTap = 65;
    const m = (nTap - 1) >> 1;
    this._hilbNTap = nTap;
    this._hilbB = new Float64Array(nTap);
    for (let i = 0; i < nTap; i++) {
      const k = i - m;
      let h = 0.0;
      if ((k & 1) !== 0) {
        h = 2.0 / (Math.PI * k);
      }
      const w =
        0.42 -
        0.5 * Math.cos((2.0 * Math.PI * i) / (nTap - 1)) +
        0.08 * Math.cos((4.0 * Math.PI * i) / (nTap - 1));
      this._hilbB[i] = h * w;
    }
    this._hilbBuf = new Float32Array(nTap);
    this._hilbIdx = 0;
    this._hilbDelayLen = m;
    this._hilbDelayBuf = new Float32Array(m);
    this._hilbDelayIdx = 0;
    this._fshiftPhase = 0.0;

    // Equalizer SOS (7 biquad stages)
    this._eqSos = buildEqSos(this.params, sr);
    this._eqZ1 = new Float64Array(7);
    this._eqZ2 = new Float64Array(7);
    this._eqDirty = false;

    // Ring Modulator
    this._ringPhase = 0.0;

    // Bitcrusher Downsample
    this._bcCounter = 0;
    this._bcHold = 0.0;

    // Echo
    this._echoRing = new RingDelay(Math.floor(1.2 * sr));
    this._echoLpX = Math.exp((-2.0 * Math.PI * 4800.0) / sr);
    this._echoLpState = 0.0;

    // Reverb (4 parallel Comb + 2 series All-pass)
    const combBase = [1116, 1188, 1277, 1356];
    const apBase = [556, 441];
    this._combDelays = combBase.map((d) => Math.max(64, Math.floor((d * sr) / 44100.0)));
    this._apDelays = apBase.map((d) => Math.max(64, Math.floor((d * sr) / 44100.0)));
    this._combRings = this._combDelays.map((d) => new RingDelay(d + 2048));
    this._combLpState = new Float64Array(this._combDelays.length);
    this._apRings = this._apDelays.map((d) => new RingDelay(d + 2048));
  }

  _peakDb(arr) {
    let pk = 0.0;
    for (let i = 0; i < arr.length; i++) {
      const a = Math.abs(arr[i]);
      if (a > pk) pk = a;
    }
    return Math.max(-60.0, 20.0 * Math.log10(pk + 1e-7));
  }

  _pushWaveform(arr) {
    // Downsample 128 samples -> push 64 points into 256-sample rolling oscilloscope buffer
    for (let i = 0; i < arr.length; i += 2) {
      this.lastWaveform[this._waveWriteIdx] = arr[i];
      this._waveWriteIdx = (this._waveWriteIdx + 1) % 256;
    }
  }

  _getOrderedWaveform() {
    const out = new Float32Array(256);
    for (let i = 0; i < 256; i++) {
      out[i] = this.lastWaveform[(this._waveWriteIdx + i) % 256];
    }
    return out;
  }

  process(inputs, outputs) {
    const input = inputs[0];
    const output = outputs[0];
    if (!input || input.length === 0 || !output || output.length === 0) {
      return true;
    }

    const inCh = input[0];
    const n = inCh.length;
    if (n === 0) return true;

    const p = this.params;
    if (this._eqDirty) {
      this._eqSos = buildEqSos(p, this.sr);
      this._eqDirty = false;
    }

    const x = new Float32Array(n);
    x.set(inCh);

    // Input peak meter (pre-effects)
    const inDb = this._peakDb(x);
    this.inputPeakDb = 0.65 * this.inputPeakDb + 0.35 * inDb;

    if (p.bypass) {
      this.outputPeakDb = this.inputPeakDb;
      this.gateIsOpen = true;
      this._pushWaveform(x);
      for (let ch = 0; ch < output.length; ch++) {
        output[ch].set(x);
      }
      this._maybeSendTelemetry();
      return true;
    }

    // 1. Input Gain
    if (Math.abs(p.input_gain_db) > 0.05) {
      const gIn = Math.pow(10.0, p.input_gain_db / 20.0);
      for (let i = 0; i < n; i++) x[i] *= gIn;
    }

    // 2. Noise Gate
    if (p.gate_enabled) {
      let sumSq = 0.0;
      for (let i = 0; i < n; i++) sumSq += x[i] * x[i];
      const rms = Math.sqrt(sumSq / n + 1e-12);
      const rmsDb = 20.0 * Math.log10(rms);
      const holdBlocks = Math.max(1, Math.floor((0.14 * this.sr) / n));
      let targetG;
      if (rmsDb >= p.gate_threshold_db) {
        this._gateHoldCounter = holdBlocks;
        targetG = 1.0;
        this.gateIsOpen = true;
      } else if (this._gateHoldCounter > 0) {
        this._gateHoldCounter--;
        targetG = 1.0;
        this.gateIsOpen = true;
      } else {
        targetG = 0.0005;
        this.gateIsOpen = false;
      }

      const coeff = targetG > this._gateGain ? 0.45 : 0.22;
      const nextG = this._gateGain + coeff * (targetG - this._gateGain);
      const stepG = (nextG - this._gateGain) / Math.max(1, n - 1);
      for (let i = 0; i < n; i++) {
        x[i] *= this._gateGain + stepG * i;
      }
      this._gateGain = nextG;
    } else {
      this.gateIsOpen = true;
    }

    // 3. Compressor
    if (p.comp_enabled) {
      let sumSq = 0.0;
      for (let i = 0; i < n; i++) sumSq += x[i] * x[i];
      const rms = Math.sqrt(sumSq / n + 1e-12);
      const lvlDb = 20.0 * Math.log10(rms);
      let targetCg = 1.0;
      if (lvlDb > p.comp_threshold_db) {
        const over = lvlDb - p.comp_threshold_db;
        const reducedDb = over * (1.0 - 1.0 / Math.max(1.1, p.comp_ratio));
        targetCg = Math.pow(10.0, -reducedDb / 20.0);
      }
      const makeup = Math.pow(10.0, Math.min(8.0, Math.max(0.0, (-p.comp_threshold_db - 10.0) * 0.22)) / 20.0);
      targetCg *= makeup;
      const cCoeff = targetCg < this._compGain ? 0.35 : 0.12;
      const nextCg = this._compGain + cCoeff * (targetCg - this._compGain);
      const stepCg = (nextCg - this._compGain) / Math.max(1, n - 1);
      for (let i = 0; i < n; i++) {
        x[i] *= this._compGain + stepCg * i;
      }
      this._compGain = nextCg;
    }

    // 4. Pitch Shifter (Dual-Tap Delay Line)
    const totalSt = p.pitch_semitones + p.pitch_cents / 100.0;
    if (p.pitch_enabled && Math.abs(totalSt) > 0.02 && p.pitch_mix > 0.01) {
      const wet = this._processPitchShift(x, totalSt);
      const dryMix = 1.0 - p.pitch_mix;
      for (let i = 0; i < n; i++) {
        x[i] = x[i] * dryMix + wet[i] * p.pitch_mix;
      }
    }

    // 5. Frequency Shifter (Hilbert SSB)
    if (p.freq_shift_enabled && Math.abs(p.freq_shift_hz) > 0.5 && p.freq_shift_mix > 0.01) {
      const wet = this._processFreqShift(x, p.freq_shift_hz);
      const dryMix = 1.0 - p.freq_shift_mix;
      for (let i = 0; i < n; i++) {
        x[i] = x[i] * dryMix + wet[i] * p.freq_shift_mix;
      }
    }

    // 6. Equalizer SOS (7 biquad stages)
    if (p.eq_enabled) {
      this._processEqInPlace(x);
    }

    // 7. Ring Modulator
    if (p.ring_enabled && p.ring_mix > 0.01) {
      const wet = this._processRingMod(x, p.ring_freq_hz, p.ring_waveform);
      const dryMix = 1.0 - p.ring_mix;
      for (let i = 0; i < n; i++) {
        x[i] = x[i] * dryMix + wet[i] * p.ring_mix;
      }
    }

    // 8. Distortion & Bitcrusher
    if (p.dist_enabled && p.dist_mix > 0.01) {
      const wet = this._processDistortion(x, p.dist_drive, p.dist_bits, p.dist_downsample);
      const dryMix = 1.0 - p.dist_mix;
      for (let i = 0; i < n; i++) {
        x[i] = x[i] * dryMix + wet[i] * p.dist_mix;
      }
    }

    // 9. Echo / Delay
    if (p.echo_enabled && p.echo_mix > 0.01) {
      this._processEchoInPlace(x, p.echo_delay_ms, p.echo_feedback, p.echo_mix);
    }

    // 10. Reverb
    if (p.reverb_enabled && p.reverb_mix > 0.01) {
      this._processReverbInPlace(x, p.reverb_room, p.reverb_damp, p.reverb_mix);
    }

    // 11. Output Gain + Soft Limiter
    const gOut = Math.abs(p.output_gain_db) > 0.05 ? Math.pow(10.0, p.output_gain_db / 20.0) : 1.0;
    for (let i = 0; i < n; i++) {
      x[i] = Math.tanh(x[i] * gOut * 0.92) * 0.98;
    }

    const outDb = this._peakDb(x);
    this.outputPeakDb = 0.65 * this.outputPeakDb + 0.35 * outDb;
    this._pushWaveform(x);

    for (let ch = 0; ch < output.length; ch++) {
      output[ch].set(x);
    }

    this._maybeSendTelemetry();
    return true;
  }

  _maybeSendTelemetry() {
    this._telemetryCounter++;
    // ~30 Hz telemetry at 48kHz / 128 samples = ~375 blocks/sec -> every 12 blocks
    if (this._telemetryCounter >= 12) {
      this._telemetryCounter = 0;
      this.port.postMessage({
        type: "telemetry",
        inputPeakDb: this.inputPeakDb,
        outputPeakDb: this.outputPeakDb,
        gateIsOpen: this.gateIsOpen,
        waveform: Array.from(this._getOrderedWaveform()),
      });
    }
  }

  _processPitchShift(x, semitones) {
    const n = x.length;
    const w = this._pitchW;
    const m = this._pitchHistLen;
    const buf = new Float32Array(m + n);
    buf.set(this._pitchHist, 0);
    buf.set(x, m);

    const alpha = Math.pow(2.0, semitones / 12.0);
    const dphi = (alpha - 1.0) / w;
    const out = new Float32Array(n);

    for (let i = 0; i < n; i++) {
      let phi1 = (this._pitchPhase + i * dphi) % 1.0;
      if (phi1 < 0) phi1 += 1.0;
      const phi2 = (phi1 + 0.5) % 1.0;

      const d1 = (1.0 - phi1) * w + 2.0;
      const d2 = (1.0 - phi2) * w + 2.0;

      const idx = i + m;
      const pos1 = idx - d1;
      const pos2 = idx - d2;

      const i1 = Math.floor(pos1);
      const f1 = pos1 - i1;
      const i2 = Math.floor(pos2);
      const f2 = pos2 - i2;

      const y1 = buf[i1] * (1.0 - f1) + buf[i1 + 1] * f1;
      const y2 = buf[i2] * (1.0 - f2) + buf[i2 + 1] * f2;

      const s1 = Math.sin(Math.PI * phi1);
      const w1 = s1 * s1;
      const w2 = 1.0 - w1;
      out[i] = y1 * w1 + y2 * w2;
    }

    let nextPhase = (this._pitchPhase + n * dphi) % 1.0;
    if (nextPhase < 0) nextPhase += 1.0;
    this._pitchPhase = nextPhase;

    this._pitchHist.set(buf.subarray(buf.length - m));
    return out;
  }

  _processFreqShift(x, shiftHz) {
    const n = x.length;
    const nTap = this._hilbNTap;
    const dphi = (2.0 * Math.PI * shiftHz) / this.sr;
    const out = new Float32Array(n);

    for (let i = 0; i < n; i++) {
      const sample = x[i];
      // Delayed real branch
      const xDel = this._hilbDelayBuf[this._hilbDelayIdx];
      this._hilbDelayBuf[this._hilbDelayIdx] = sample;
      this._hilbDelayIdx = (this._hilbDelayIdx + 1) % this._hilbDelayLen;

      // FIR Hilbert branch
      this._hilbBuf[this._hilbIdx] = sample;
      let xHilb = 0.0;
      let p = this._hilbIdx;
      for (let t = 0; t < nTap; t++) {
        xHilb += this._hilbB[t] * this._hilbBuf[p];
        p = p === 0 ? nTap - 1 : p - 1;
      }
      this._hilbIdx = (this._hilbIdx + 1) % nTap;

      const phase = this._fshiftPhase;
      this._fshiftPhase = (phase + dphi) % (2.0 * Math.PI);
      out[i] = xDel * Math.cos(phase) - xHilb * Math.sin(phase);
    }

    return out;
  }

  _processEqInPlace(x) {
    const n = x.length;
    const sos = this._eqSos;
    for (let s = 0; s < 7; s++) {
      const [b0, b1, b2, a1, a2] = sos[s];
      let z1 = this._eqZ1[s];
      let z2 = this._eqZ2[s];
      for (let i = 0; i < n; i++) {
        const xi = x[i];
        const yi = b0 * xi + z1;
        z1 = b1 * xi - a1 * yi + z2;
        z2 = b2 * xi - a2 * yi;
        x[i] = yi;
      }
      this._eqZ1[s] = z1;
      this._eqZ2[s] = z2;
    }
  }

  _processRingMod(x, freqHz, waveform) {
    const n = x.length;
    const dphi = freqHz / this.sr;
    const out = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const ph = this._ringPhase;
      let mod;
      if (waveform === "Quadrada") {
        mod = ph < 0.5 ? 1.0 : -1.0;
      } else if (waveform === "Triangular") {
        mod = 4.0 * Math.abs(ph - 0.5) - 1.0;
      } else {
        mod = Math.sin(2.0 * Math.PI * ph);
      }
      out[i] = x[i] * mod;
      this._ringPhase = (ph + dphi) % 1.0;
    }
    return out;
  }

  _processDistortion(x, drive, bits, downsample) {
    const n = x.length;
    const d = Math.max(1.0, drive);
    const comp = 1.0 / (1.0 + 0.16 * (d - 1.0));
    const levels = bits < 16 ? Math.pow(2.0, Math.max(2, bits) - 1) : 0;
    const k = Math.max(1, Math.round(downsample));
    const out = new Float32Array(n);

    for (let i = 0; i < n; i++) {
      let y = Math.tanh(x[i] * d) * comp;
      if (levels > 0) {
        y = Math.round(y * levels) / levels;
      }
      if (k > 1) {
        if (this._bcCounter === 0) {
          this._bcHold = y;
        }
        y = this._bcHold;
        this._bcCounter = (this._bcCounter + 1) % k;
      }
      out[i] = y;
    }
    return out;
  }

  _processEchoInPlace(x, delayMs, feedback, mix) {
    const delaySamples = Math.max(48, Math.floor(delayMs * 0.001 * this.sr));
    const fb = clip(feedback, 0.0, 0.88);
    const lpX = this._echoLpX;
    const oneMinusX = 1.0 - lpX;

    for (let i = 0; i < x.length; i++) {
      const xc = x[i];
      const delayed = this._echoRing.readSample(delaySamples);
      this._echoLpState = oneMinusX * delayed + lpX * this._echoLpState;
      this._echoRing.writeSample(xc + fb * this._echoLpState);
      x[i] = xc + mix * delayed;
    }
  }

  _processReverbInPlace(x, room, damp, mix) {
    const fb = 0.68 + 0.27 * clip(room, 0.0, 1.0);
    const d = clip(damp, 0.05, 0.92);
    const oneMinusD = 1.0 - d;
    const apG = 0.5;
    const dryMix = 1.0 - 0.5 * mix;

    for (let i = 0; i < x.length; i++) {
      const xc = x[i] * 0.25;
      let combSum = 0.0;
      for (let c = 0; c < this._combRings.length; c++) {
        const ring = this._combRings[c];
        const delSig = ring.readSample(this._combDelays[c]);
        this._combLpState[c] = oneMinusD * delSig + d * this._combLpState[c];
        ring.writeSample(xc + fb * this._combLpState[c]);
        combSum += delSig;
      }

      let yAp = combSum;
      for (let a = 0; a < this._apRings.length; a++) {
        const ring = this._apRings[a];
        const vDel = ring.readSample(this._apDelays[a]);
        const v = yAp + apG * vDel;
        ring.writeSample(v);
        yAp = -apG * v + vDel;
      }

      x[i] = x[i] * dryMix + yAp * mix;
    }
  }
}

registerProcessor("voxcraft-processor", VoxCraftProcessor);
