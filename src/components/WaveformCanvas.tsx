import { useEffect, useRef } from "react";

interface WaveformCanvasProps {
  waveform: number[];
  running: boolean;
  bypass: boolean;
}

export function WaveformCanvas({ waveform, running, bypass }: WaveformCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(200, Math.floor(rect.width));
    const h = Math.max(50, Math.floor(rect.height));

    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.fillStyle = "#090d16";
    ctx.fillRect(0, 0, w, h);

    const mid = h / 2.0;
    ctx.beginPath();
    ctx.strokeStyle = "#1e293b";
    ctx.lineWidth = 1;
    ctx.moveTo(0, mid);
    ctx.lineTo(w, mid);
    ctx.stroke();

    if (running && waveform.length > 1) {
      ctx.beginPath();
      ctx.strokeStyle = bypass ? "#f59e0b" : "#4cc9f0";
      ctx.lineWidth = 1.6;
      const len = waveform.length;
      for (let i = 0; i < len; i++) {
        const x = (i / (len - 1)) * w;
        const clamped = Math.max(-1.0, Math.min(1.0, waveform[i]));
        const y = mid - clamped * (mid - 4);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    ctx.restore();
  }, [waveform, running, bypass]);

  return <canvas ref={canvasRef} className="wave-canvas" />;
}
