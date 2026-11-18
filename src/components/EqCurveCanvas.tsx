import { useEffect, useRef } from "react";
import { buildEqSos, computeSosFreqResponseDb } from "../dsp/eqMath";
import type { DSPParams } from "../dsp/params";

interface EqCurveCanvasProps {
  params: DSPParams;
  sampleRate: number;
}

export function EqCurveCanvas({ params, sampleRate }: EqCurveCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const draw = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const w = Math.max(400, Math.floor(rect.width));
      const h = Math.max(160, Math.floor(rect.height));

      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr;
        canvas.height = h * dpr;
      }

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, w, h);

      ctx.fillStyle = "#090d16";
      ctx.fillRect(0, 0, w, h);

      const padX = 36;
      const padY = 16;
      const gw = w - 2 * padX;
      const gh = h - 2 * padY;

      // dB grid (+18, +9, 0, -9, -18)
      ctx.font = '10px "Segoe UI", sans-serif';
      ctx.textBaseline = "middle";
      for (const db of [-18, -9, 0, 9, 18]) {
        const y = padY + ((18.0 - db) / 36.0) * gh;
        ctx.beginPath();
        ctx.strokeStyle = db === 0 ? "#334155" : "#162032";
        ctx.lineWidth = 1;
        ctx.setLineDash(db !== 0 ? [3, 3] : []);
        ctx.moveTo(padX, y);
        ctx.lineTo(w - padX, y);
        ctx.stroke();

        ctx.setLineDash([]);
        ctx.fillStyle = "#64748b";
        ctx.textAlign = "right";
        ctx.fillText(db > 0 ? `+${db}` : `${db}`, padX - 6, y);
      }

      // Logarithmic frequency grid (20 Hz -> 20 kHz)
      const fMin = 20.0;
      const fMax = 20000.0;
      const logSpan = Math.log10(fMax / fMin);
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      for (const f of [30, 60, 120, 250, 500, 1000, 2000, 4000, 8000, 16000]) {
        const x = padX + (Math.log10(f / fMin) / logSpan) * gw;
        ctx.beginPath();
        ctx.strokeStyle = "#162032";
        ctx.lineWidth = 1;
        ctx.moveTo(x, padY);
        ctx.lineTo(x, h - padY);
        ctx.stroke();

        const lbl = f >= 1000 ? `${Math.floor(f / 1000)}k` : String(f);
        ctx.fillStyle = "#64748b";
        ctx.fillText(lbl, x, h - 2);
      }

      if (!params.eq_enabled) {
        const y0 = padY + 0.5 * gh;
        ctx.beginPath();
        ctx.strokeStyle = "#475569";
        ctx.lineWidth = 2;
        ctx.moveTo(padX, y0);
        ctx.lineTo(w - padX, y0);
        ctx.stroke();

        ctx.fillStyle = "#64748b";
        ctx.font = '12px "Segoe UI", sans-serif';
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillText("EQ Desativado (Flat)", w / 2, y0 - 8);
        ctx.restore();
        return;
      }

      const sr = sampleRate || 48000;
      const sos = buildEqSos(params, sr);
      const maxFreq = Math.min(fMax, sr * 0.48);
      const numPts = 220;
      const freqs: number[] = [];
      const logMin = Math.log10(fMin);
      const logMax = Math.log10(maxFreq);
      for (let i = 0; i < numPts; i++) {
        const t = i / (numPts - 1);
        freqs.push(Math.pow(10, logMin + t * (logMax - logMin)));
      }

      const dbResp = computeSosFreqResponseDb(sos, freqs, sr);

      ctx.beginPath();
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 2.5;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";

      for (let i = 0; i < numPts; i++) {
        const f = freqs[i];
        const db = dbResp[i];
        const x = padX + (Math.log10(f / fMin) / logSpan) * gw;
        const yRaw = padY + ((18.0 - db) / 36.0) * gh;
        const y = Math.max(padY, Math.min(h - padY, yRaw));
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.restore();
    };

    draw();
    window.addEventListener("resize", draw);
    return () => window.removeEventListener("resize", draw);
  }, [params, sampleRate]);

  return <canvas ref={canvasRef} className="eq-canvas" />;
}
