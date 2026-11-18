import type { DSPParams } from "../dsp/params";

export interface AudioDeviceItem {
  deviceId: string;
  label: string;
  kind: "audioinput" | "audiooutput";
}

export interface TelemetryData {
  inputPeakDb: number;
  outputPeakDb: number;
  gateIsOpen: boolean;
  waveform: number[];
}

export type AudioDriverMode = "interactive" | "balanced" | "playback";
export type SampleRateOption = 48000 | 44100 | "auto";

interface MediaDevicesWithSelectOutput extends MediaDevices {
  selectAudioOutput?: (options?: { deviceId?: string }) => Promise<MediaDeviceInfo>;
}

export class WebAudioRouter {
  public running = false;
  public activeSampleRate = 48000;
  public activeBlocksize = 512;
  public activeDriverMode: AudioDriverMode = "interactive";

  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private worklet: AudioWorkletNode | null = null;
  private outAudioEl: HTMLAudioElement | null = null;
  private monAudioEl: HTMLAudioElement | null = null;
  private onTelemetryCb: ((data: TelemetryData) => void) | null = null;

  public setTelemetryListener(cb: ((data: TelemetryData) => void) | null): void {
    this.onTelemetryCb = cb;
  }

  public static supportsSetSinkId(): boolean {
    return (
      typeof HTMLAudioElement !== "undefined" &&
      typeof (HTMLAudioElement.prototype as { setSinkId?: (id: string) => Promise<void> }).setSinkId ===
        "function"
    );
  }

  public static supportsSelectAudioOutput(): boolean {
    return (
      typeof navigator !== "undefined" &&
      !!navigator.mediaDevices &&
      typeof (navigator.mediaDevices as MediaDevicesWithSelectOutput).selectAudioOutput === "function"
    );
  }

  public static async selectSystemOutput(): Promise<AudioDeviceItem | null> {
    if (!WebAudioRouter.supportsSelectAudioOutput()) {
      return null;
    }
    const md = navigator.mediaDevices as MediaDevicesWithSelectOutput;
    const selected = await md.selectAudioOutput!();
    return {
      deviceId: selected.deviceId,
      label: `[Sistema] ${selected.label || "Dispositivo de Saída"}`,
      kind: "audiooutput",
    };
  }

  public static async listDevices(requestPermission = false): Promise<{
    inputs: AudioDeviceItem[];
    outputs: AudioDeviceItem[];
  }> {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
      return { inputs: [], outputs: [] };
    }

    if (requestPermission && navigator.mediaDevices.getUserMedia) {
      try {
        const temp = await navigator.mediaDevices.getUserMedia({ audio: true });
        temp.getTracks().forEach((t) => t.stop());
      } catch {
        // Proceed with available device metadata if denied or unavailable
      }
    }

    const devices = await navigator.mediaDevices.enumerateDevices();
    const inputs: AudioDeviceItem[] = [];
    const outputs: AudioDeviceItem[] = [];

    let inIdx = 1;
    let outIdx = 1;
    for (const d of devices) {
      if (d.kind === "audioinput") {
        const name = d.label || `Microfone ${inIdx++}`;
        inputs.push({
          deviceId: d.deviceId,
          label: `[WebAudio] ${name}`,
          kind: "audioinput",
        });
      } else if (d.kind === "audiooutput") {
        const name = d.label || `Saída de Áudio ${outIdx++}`;
        outputs.push({
          deviceId: d.deviceId,
          label: `[WebAudio] ${name}`,
          kind: "audiooutput",
        });
      }
    }

    if (outputs.length === 0) {
      outputs.push({
        deviceId: "default",
        label: "[WebAudio] Saída Padrão do Navegador",
        kind: "audiooutput",
      });
    }

    return { inputs, outputs };
  }

  public updateParams(params: DSPParams): void {
    if (this.worklet) {
      this.worklet.port.postMessage({ type: "params", params });
    }
  }

  public async start(opts: {
    inDeviceId: string;
    outDeviceId: string;
    blocksize: number;
    driverMode: AudioDriverMode;
    sampleRateOption: SampleRateOption;
    monitorEnabled: boolean;
    monitorDeviceId: string;
    params: DSPParams;
  }): Promise<{ ok: boolean; message: string }> {
    await this.stop();

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return {
        ok: false,
        message: "API de microfone (MediaDevices) indisponível neste navegador.",
      };
    }

    try {
      const audioConstraints: MediaTrackConstraints = {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
      };
      if (opts.inDeviceId && opts.inDeviceId !== "default") {
        audioConstraints.deviceId = { exact: opts.inDeviceId };
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: audioConstraints,
      });
      this.stream = stream;

      const ctxOptions: AudioContextOptions = {
        latencyHint: opts.driverMode,
      };
      if (opts.sampleRateOption !== "auto") {
        ctxOptions.sampleRate = opts.sampleRateOption;
      }

      const ctx = new AudioContext(ctxOptions);
      this.ctx = ctx;

      if (ctx.state === "suspended") {
        await ctx.resume();
      }

      await ctx.audioWorklet.addModule("/voxcraft-processor.js");

      const source = ctx.createMediaStreamSource(stream);
      const worklet = new AudioWorkletNode(ctx, "voxcraft-processor", {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [2],
      });

      worklet.port.onmessage = (event: MessageEvent) => {
        const d = event.data;
        if (d && d.type === "telemetry" && this.onTelemetryCb) {
          this.onTelemetryCb({
            inputPeakDb: d.inputPeakDb,
            outputPeakDb: d.outputPeakDb,
            gateIsOpen: d.gateIsOpen,
            waveform: d.waveform,
          });
        }
      };

      worklet.port.postMessage({ type: "params", params: opts.params });

      source.connect(worklet);

      // Output routing (VB-Cable or selected output device via setSinkId)
      const supportsSink = WebAudioRouter.supportsSetSinkId();
      if (supportsSink && opts.outDeviceId && opts.outDeviceId !== "default") {
        const dest = ctx.createMediaStreamDestination();
        worklet.connect(dest);
        const audioEl = new Audio();
        audioEl.srcObject = dest.stream;
        await audioEl.setSinkId(opts.outDeviceId);
        await audioEl.play();
        this.outAudioEl = audioEl;
      } else {
        worklet.connect(ctx.destination);
      }

      // Optional separate monitor routing
      const shouldMonitor =
        opts.monitorEnabled &&
        Boolean(opts.monitorDeviceId) &&
        opts.monitorDeviceId !== opts.outDeviceId;

      if (shouldMonitor && supportsSink) {
        try {
          const monDest = ctx.createMediaStreamDestination();
          worklet.connect(monDest);
          const monEl = new Audio();
          monEl.srcObject = monDest.stream;
          await monEl.setSinkId(opts.monitorDeviceId);
          await monEl.play();
          this.monAudioEl = monEl;
        } catch {
          this.monAudioEl = null;
        }
      }

      this.source = source;
      this.worklet = worklet;
      this.running = true;
      this.activeSampleRate = ctx.sampleRate;
      this.activeBlocksize = opts.blocksize;
      this.activeDriverMode = opts.driverMode;

      const baseLatencyMs =
        typeof ctx.baseLatency === "number" && ctx.baseLatency > 0
          ? ctx.baseLatency * 1000
          : (opts.blocksize * 1000) / ctx.sampleRate;
      return {
        ok: true,
        message: `Ativo: ${ctx.sampleRate} Hz | ${opts.driverMode} (~${baseLatencyMs.toFixed(1)} ms)`,
      };
    } catch (err) {
      await this.stop();
      const msg = err instanceof Error ? err.message : String(err);
      return {
        ok: false,
        message: `Falha ao iniciar áudio: ${msg}`,
      };
    }
  }

  public async stop(): Promise<void> {
    this.running = false;
    if (this.outAudioEl) {
      try {
        this.outAudioEl.pause();
        this.outAudioEl.srcObject = null;
      } catch {
        // ignore
      }
      this.outAudioEl = null;
    }
    if (this.monAudioEl) {
      try {
        this.monAudioEl.pause();
        this.monAudioEl.srcObject = null;
      } catch {
        // ignore
      }
      this.monAudioEl = null;
    }
    if (this.worklet) {
      try {
        this.worklet.disconnect();
      } catch {
        // ignore
      }
      this.worklet = null;
    }
    if (this.source) {
      try {
        this.source.disconnect();
      } catch {
        // ignore
      }
      this.source = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
    if (this.ctx) {
      try {
        await this.ctx.close();
      } catch {
        // ignore
      }
      this.ctx = null;
    }
  }
}
