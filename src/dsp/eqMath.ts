import type { DSPParams } from "./params";

export type BiquadRow = [number, number, number, number, number, number];

function clip(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

export function biquadLowpass(fc: number, q: number, fs: number): BiquadRow {
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
  return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0];
}

export function biquadHighpass(fc: number, q: number, fs: number): BiquadRow {
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
  return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0];
}

export function biquadPeaking(fc: number, gainDb: number, q: number, fs: number): BiquadRow {
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
  return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0];
}

export function biquadLowShelf(fc: number, gainDb: number, fs: number, slope = 0.85): BiquadRow {
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
  return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0];
}

export function biquadHighShelf(fc: number, gainDb: number, fs: number, slope = 0.85): BiquadRow {
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
  return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0];
}

export function buildEqSos(p: DSPParams, fs: number): BiquadRow[] {
  const rows: BiquadRow[] = [];
  if (p.eq_hpf_enabled) {
    rows.push(biquadHighpass(p.eq_hpf_hz, 0.707, fs));
  } else {
    rows.push([1.0, 0.0, 0.0, 1.0, 0.0, 0.0]);
  }

  rows.push(biquadLowShelf(120.0, p.eq_band1_db, fs));
  rows.push(biquadPeaking(400.0, p.eq_band2_db, 1.0, fs));
  rows.push(biquadPeaking(1200.0, p.eq_band3_db, 1.0, fs));
  rows.push(biquadPeaking(3500.0, p.eq_band4_db, 1.0, fs));
  rows.push(biquadHighShelf(7500.0, p.eq_band5_db, fs));

  if (p.eq_lpf_enabled) {
    rows.push(biquadLowpass(p.eq_lpf_hz, 0.707, fs));
  } else {
    rows.push([1.0, 0.0, 0.0, 1.0, 0.0, 0.0]);
  }

  return rows;
}

/**
 * Evaluates magnitude response (in dB) of the 7-stage SOS filter at given frequencies,
 * matching scipy.signal.sosfreqz.
 */
export function computeSosFreqResponseDb(sos: BiquadRow[], freqs: number[], fs: number): number[] {
  return freqs.map((f) => {
    const w = (2.0 * Math.PI * f) / fs;
    const cosW = Math.cos(w);
    const sinW = Math.sin(w);
    const cos2W = Math.cos(2.0 * w);
    const sin2W = Math.sin(2.0 * w);

    let magSq = 1.0;
    for (const [b0, b1, b2, , a1, a2] of sos) {
      const numRe = b0 + b1 * cosW + b2 * cos2W;
      const numIm = -(b1 * sinW + b2 * sin2W);
      const denRe = 1.0 + a1 * cosW + a2 * cos2W;
      const denIm = -(a1 * sinW + a2 * sin2W);

      const numMagSq = numRe * numRe + numIm * numIm;
      const denMagSq = Math.max(1e-20, denRe * denRe + denIm * denIm);
      magSq *= numMagSq / denMagSq;
    }

    const db = 10.0 * Math.log10(Math.max(magSq, 1e-10));
    return clip(db, -20.0, 20.0);
  });
}
