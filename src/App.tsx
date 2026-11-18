import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  WebAudioRouter,
  type AudioDeviceItem,
  type AudioDriverMode,
  type SampleRateOption,
} from "./audio/audioRouter";
import { EqCurveCanvas } from "./components/EqCurveCanvas";
import { PWAInstallButton } from "./components/PWAInstallButton";
import { WaveformCanvas } from "./components/WaveformCanvas";
import { createDefaultParams, type DSPParams, type RingWaveform } from "./dsp/params";
import { getBuiltinPresets, loadUserPresets, saveUserPresets } from "./dsp/presets";

type TabId = "pitch" | "eq" | "fx" | "space" | "mixer";
type CloseBehavior = "confirm_active" | "stop_immediately";

const CLOSE_BEHAVIOR_KEY = "voxcraft_close_behavior_v1";

interface DocumentPictureInPictureApi {
  requestWindow: (opts?: { width?: number; height?: number }) => Promise<Window>;
}

interface SliderRowProps {
  label: string;
  min: number;
  max: number;
  step?: number;
  value: number;
  unit: string;
  onChange: (val: number) => void;
}

function SliderRow({ label, min, max, step = 0.5, value, unit, onChange }: SliderRowProps) {
  const intUnits = new Set(["Hz", "ms", "%", "bits", "x", "ct"]);
  const formatted =
    intUnits.has(unit) && step >= 1.0 ? `${Math.round(value)} ${unit}` : `${value.toFixed(1)} ${unit}`;

  return (
    <div className="slider-block">
      <div className="slider-top">
        <span>{label}</span>
        <span className="slider-val">{formatted}</span>
      </div>
      <input
        type="range"
        className="h-slider"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </div>
  );
}

interface VerticalEqBandProps {
  title: string;
  value: number;
  onChange: (val: number) => void;
}

function VerticalEqBand({ title, value, onChange }: VerticalEqBandProps) {
  const signed = `${value >= 0 ? "+" : ""}${value.toFixed(1)} dB`;
  return (
    <div className="eq-band-col">
      <span className="eq-band-val">{signed}</span>
      <div className="v-slider-wrap">
        <input
          type="range"
          className="v-slider"
          min={-18.0}
          max={18.0}
          step={0.5}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
        />
      </div>
      <span className="eq-band-title">{title}</span>
    </div>
  );
}

interface SwitchProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  variant?: "default" | "amber";
  size?: "sm" | "md" | "bold";
}

function ToggleSwitch({ label, checked, onChange, variant = "default", size = "sm" }: SwitchProps) {
  const labelClass =
    size === "bold" ? "switch-label-bold" : size === "md" ? "switch-label-md" : "switch-label-sm";
  return (
    <label className="switch-row">
      <input
        type="checkbox"
        className={`switch-input ${variant === "amber" ? "switch-amber" : ""}`}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className={labelClass}>{label}</span>
    </label>
  );
}

export default function App() {
  const builtinPresets = useMemo(() => getBuiltinPresets(), []);
  const [userPresets, setUserPresets] = useState<Record<string, DSPParams>>(() => loadUserPresets());
  const [selectedPreset, setSelectedPreset] = useState<string>("Normal (Limpo + Gate)");
  const [params, setParams] = useState<DSPParams>(() => ({
    ...builtinPresets["Normal (Limpo + Gate)"],
  }));

  const [activeTab, setActiveTab] = useState<TabId>("pitch");
  const [isOnline, setIsOnline] = useState<boolean>(() =>
    typeof navigator !== "undefined" ? navigator.onLine : true
  );

  // Audio devices & driver/routing state
  const routerRef = useRef<WebAudioRouter | null>(null);
  if (!routerRef.current) {
    routerRef.current = new WebAudioRouter();
  }

  const [inDevices, setInDevices] = useState<AudioDeviceItem[]>([]);
  const [outDevices, setOutDevices] = useState<AudioDeviceItem[]>([]);
  const [inDeviceId, setInDeviceId] = useState<string>("default");
  const [outDeviceId, setOutDeviceId] = useState<string>("default");
  const [monitorEnabled, setMonitorEnabled] = useState<boolean>(false);
  const [monDeviceId, setMonDeviceId] = useState<string>("default");
  const [latencyLabel, setLatencyLabel] = useState<string>("Baixa (512)");
  const [driverMode, setDriverMode] = useState<AudioDriverMode>("interactive");
  const [sampleRateOption, setSampleRateOption] = useState<SampleRateOption>(48000);

  // Close & Background / Mini-window state
  const [closeBehavior, setCloseBehavior] = useState<CloseBehavior>(() => {
    try {
      const saved = localStorage.getItem(CLOSE_BEHAVIOR_KEY);
      return saved === "stop_immediately" ? "stop_immediately" : "confirm_active";
    } catch {
      return "confirm_active";
    }
  });
  const [showFloatingMini, setShowFloatingMini] = useState<boolean>(false);
  const pipWindowRef = useRef<Window | null>(null);

  const [running, setRunning] = useState<boolean>(false);
  const [statusText, setStatusText] = useState<string>("Status: Parado");
  const [statusState, setStatusState] = useState<"idle" | "active" | "error">("idle");
  const [sampleRate, setSampleRate] = useState<number>(48000);

  // Live levels & waveform
  const [inPeakDb, setInPeakDb] = useState<number>(-60);
  const [outPeakDb, setOutPeakDb] = useState<number>(-60);
  const [gateIsOpen, setGateIsOpen] = useState<boolean>(true);
  const [waveform, setWaveform] = useState<number[]>(() => new Array(256).fill(0));

  // Modals
  const [showGuideModal, setShowGuideModal] = useState<boolean>(false);
  const [showSaveModal, setShowSaveModal] = useState<boolean>(false);
  const [saveNameInput, setSaveNameInput] = useState<string>("");
  const [alertModal, setAlertModal] = useState<{ title: string; message: string } | null>(null);
  const importInputRef = useRef<HTMLInputElement | null>(null);

  const supportsSinkId = useMemo(() => WebAudioRouter.supportsSetSinkId(), []);
  const supportsSelectOutput = useMemo(() => WebAudioRouter.supportsSelectAudioOutput(), []);

  const allPresetNames = useMemo(() => {
    const names = Object.keys(builtinPresets);
    for (const u of Object.keys(userPresets)) {
      names.push(`★ ${u}`);
    }
    return names;
  }, [builtinPresets, userPresets]);

  const getBlocksize = useCallback((lbl: string) => {
    if (lbl.includes("256")) return 256;
    if (lbl.includes("1024")) return 1024;
    return 512;
  }, []);

  const refreshDevices = useCallback(async (requestPermission = false) => {
    const { inputs, outputs } = await WebAudioRouter.listDevices(requestPermission);
    setInDevices(inputs);
    setOutDevices(outputs);

    if (inputs.length > 0) {
      setInDeviceId((prev) => (inputs.some((d) => d.deviceId === prev) ? prev : inputs[0].deviceId));
    }
    if (outputs.length > 0) {
      setOutDeviceId((prev) => {
        if (outputs.some((d) => d.deviceId === prev)) return prev;
        const vb = outputs.find((d) => d.label.includes("CABLE Input") || d.label.includes("VB-Audio"));
        return vb ? vb.deviceId : outputs[0].deviceId;
      });
      setMonDeviceId((prev) => {
        if (outputs.some((d) => d.deviceId === prev)) return prev;
        const nonVb = outputs.find((d) => !d.label.includes("CABLE"));
        return nonVb ? nonVb.deviceId : outputs[0].deviceId;
      });
    }
  }, []);

  useEffect(() => {
    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  useEffect(() => {
    const router = routerRef.current!;
    router.setTelemetryListener((data) => {
      setInPeakDb(data.inputPeakDb);
      setOutPeakDb(data.outputPeakDb);
      setGateIsOpen(data.gateIsOpen);
      setWaveform(data.waveform);
    });
    void refreshDevices(false);
    return () => {
      router.setTelemetryListener(null);
      void router.stop();
      if (pipWindowRef.current && !pipWindowRef.current.closed) {
        pipWindowRef.current.close();
      }
    };
  }, [refreshDevices]);

  // Sync params to DSP worklet whenever params change
  useEffect(() => {
    routerRef.current?.updateParams(params);
  }, [params]);

  // Close guard & clean shutdown ("quando fechar ele")
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (running && closeBehavior === "confirm_active") {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    const handlePageHide = () => {
      void routerRef.current?.stop();
      if (pipWindowRef.current && !pipWindowRef.current.closed) {
        pipWindowRef.current.close();
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    window.addEventListener("pagehide", handlePageHide);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      window.removeEventListener("pagehide", handlePageHide);
    };
  }, [running, closeBehavior]);

  const updateParam = useCallback(<K extends keyof DSPParams>(key: K, value: DSPParams[K]) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  }, []);

  const applyPreset = useCallback(
    (name: string) => {
      if (name in builtinPresets) {
        setParams({ ...builtinPresets[name] });
      } else if (name in userPresets) {
        setParams({ ...userPresets[name] });
      }
    },
    [builtinPresets, userPresets]
  );

  const handlePresetSelected = (choice: string) => {
    setSelectedPreset(choice);
    const clean = choice.startsWith("★ ") ? choice.slice(2) : choice;
    applyPreset(clean);
  };

  const handleConfirmSavePreset = () => {
    const trimmed = saveNameInput.trim();
    if (!trimmed) return;
    const updated = { ...userPresets, [trimmed]: { ...params } };
    setUserPresets(updated);
    saveUserPresets(updated);
    setSelectedPreset(`★ ${trimmed}`);
    setSaveNameInput("");
    setShowSaveModal(false);
  };

  const handleDeletePreset = () => {
    if (!selectedPreset.startsWith("★ ")) {
      setAlertModal({
        title: "Aviso",
        message: "Apenas vozes personalizadas (marcadas com ★) podem ser excluídas.",
      });
      return;
    }
    const name = selectedPreset.slice(2);
    if (name in userPresets) {
      const updated = { ...userPresets };
      delete updated[name];
      setUserPresets(updated);
      saveUserPresets(updated);
      setSelectedPreset("Normal (Limpo + Gate)");
      applyPreset("Normal (Limpo + Gate)");
    }
  };

  const handleExportPresets = () => {
    const json = JSON.stringify(userPresets, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "user_presets.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportPresets = async (file: File | undefined) => {
    if (!file) return;
    try {
      const text = await file.text();
      const raw = JSON.parse(text) as Record<string, Partial<DSPParams>>;
      const imported: Record<string, DSPParams> = { ...userPresets };
      let count = 0;
      for (const [name, data] of Object.entries(raw)) {
        if (data && typeof data === "object") {
          imported[name] = createDefaultParams(data);
          count++;
        }
      }
      setUserPresets(imported);
      saveUserPresets(imported);
      setAlertModal({
        title: "Presets Importados",
        message: `${count} voz(es) personalizada(s) importada(s) com sucesso.`,
      });
    } catch {
      setAlertModal({
        title: "Erro ao Importar",
        message: "Arquivo JSON inválido. Selecione um arquivo user_presets.json válido.",
      });
    }
  };

  const startAudio = useCallback(
    async (overrides?: {
      inId?: string;
      outId?: string;
      monEnabled?: boolean;
      monId?: string;
      latLabel?: string;
      drvMode?: AudioDriverMode;
      srOption?: SampleRateOption;
    }) => {
      const router = routerRef.current!;
      const result = await router.start({
        inDeviceId: overrides?.inId ?? inDeviceId,
        outDeviceId: overrides?.outId ?? outDeviceId,
        blocksize: getBlocksize(overrides?.latLabel ?? latencyLabel),
        driverMode: overrides?.drvMode ?? driverMode,
        sampleRateOption: overrides?.srOption ?? sampleRateOption,
        monitorEnabled: overrides?.monEnabled ?? monitorEnabled,
        monitorDeviceId: overrides?.monId ?? monDeviceId,
        params,
      });

      if (result.ok) {
        setRunning(true);
        setSampleRate(router.activeSampleRate);
        setStatusText(result.message);
        setStatusState("active");
        void refreshDevices(false);
      } else {
        setRunning(false);
        setStatusText(result.message);
        setStatusState("error");
        setAlertModal({ title: "Erro de Áudio", message: result.message });
      }
    },
    [
      driverMode,
      getBlocksize,
      inDeviceId,
      latencyLabel,
      monDeviceId,
      monitorEnabled,
      outDeviceId,
      params,
      refreshDevices,
      sampleRateOption,
    ]
  );

  const stopAudio = useCallback(async () => {
    const router = routerRef.current!;
    await router.stop();
    setRunning(false);
    setStatusText("Status: Parado");
    setStatusState("idle");
    setWaveform(new Array(256).fill(0));
    setInPeakDb(-60);
    setOutPeakDb(-60);
  }, []);

  const toggleAudio = useCallback(async () => {
    if (routerRef.current!.running) {
      await stopAudio();
    } else {
      await startAudio();
    }
  }, [startAudio, stopAudio]);

  // OS Taskbar / Media Session controls
  useEffect(() => {
    if (!("mediaSession" in navigator)) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: `VoxCraft Studio — ${selectedPreset}`,
      artist: params.bypass ? "Modo Bypass (Voz Original)" : "Modulador de Voz Ativo",
      album: "VoxCraft DSP",
      artwork: [
        { src: "/pwa-192x192.png", sizes: "192x192", type: "image/png" },
        { src: "/pwa-512x512.png", sizes: "512x512", type: "image/png" },
      ],
    });
    navigator.mediaSession.playbackState = running ? "playing" : "paused";

    navigator.mediaSession.setActionHandler("play", () => {
      if (!routerRef.current?.running) void startAudio();
    });
    navigator.mediaSession.setActionHandler("pause", () => {
      if (routerRef.current?.running) void stopAudio();
    });
    navigator.mediaSession.setActionHandler("stop", () => {
      void stopAudio();
    });
  }, [params.bypass, running, selectedPreset, startAudio, stopAudio]);

  // Mini-Janela Flutuante / 2º Plano (Document Picture-in-Picture + fallback)
  const openMiniBackgroundWindow = async () => {
    const docPip = (window as unknown as { documentPictureInPicture?: DocumentPictureInPictureApi })
      .documentPictureInPicture;
    if (docPip && typeof docPip.requestWindow === "function") {
      try {
        if (pipWindowRef.current && !pipWindowRef.current.closed) {
          pipWindowRef.current.focus();
          return;
        }
        const pipWin = await docPip.requestWindow({ width: 320, height: 190 });
        pipWindowRef.current = pipWin;
        pipWin.document.title = "VoxCraft Studio — Mini";
        pipWin.document.body.style.cssText =
          "margin:0;padding:12px;background:#0f172a;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;display:flex;flex-direction:column;gap:10px;";

        const header = pipWin.document.createElement("div");
        header.style.cssText = "display:flex;align-items:center;gap:8px;font-weight:700;color:#4cc9f0;";
        const img = pipWin.document.createElement("img");
        img.src = "/pwa-192x192.png";
        img.style.cssText = "width:24px;height:24px;border-radius:6px;";
        const title = pipWin.document.createElement("span");
        title.textContent = "VoxCraft Studio (2º Plano)";
        header.append(img, title);

        const presetLbl = pipWin.document.createElement("div");
        presetLbl.style.cssText = "font-size:12px;color:#94a3b8;";
        presetLbl.textContent = `Preset: ${selectedPreset}`;

        const btnRow = pipWin.document.createElement("div");
        btnRow.style.cssText = "display:flex;gap:8px;";

        const powerBtn = pipWin.document.createElement("button");
        powerBtn.textContent = routerRef.current?.running ? "PARAR ÁUDIO" : "INICIAR ÁUDIO";
        powerBtn.style.cssText = `flex:1;border:none;border-radius:6px;padding:8px;color:#fff;font-weight:700;cursor:pointer;background:${
          routerRef.current?.running ? "#ef4444" : "#10b981"
        };`;
        powerBtn.onclick = async () => {
          await toggleAudio();
          const isNowRunning = Boolean(routerRef.current?.running);
          powerBtn.textContent = isNowRunning ? "PARAR ÁUDIO" : "INICIAR ÁUDIO";
          powerBtn.style.background = isNowRunning ? "#ef4444" : "#10b981";
        };

        const bypassBtn = pipWin.document.createElement("button");
        bypassBtn.textContent = params.bypass ? "Bypass: ON" : "Bypass: OFF";
        bypassBtn.style.cssText =
          "border:none;border-radius:6px;padding:8px 10px;color:#fff;font-weight:600;cursor:pointer;background:#334155;";
        bypassBtn.onclick = () => {
          setParams((prev) => {
            const next = !prev.bypass;
            bypassBtn.textContent = next ? "Bypass: ON" : "Bypass: OFF";
            return { ...prev, bypass: next };
          });
        };

        btnRow.append(powerBtn, bypassBtn);
        pipWin.document.body.append(header, presetLbl, btnRow);
        return;
      } catch {
        // Fallback to in-app floating mini widget if Document PiP is blocked (e.g. iframe)
      }
    }
    setShowFloatingMini((prev) => !prev);
  };

  const handleSelectSystemOutput = async () => {
    try {
      const picked = await WebAudioRouter.selectSystemOutput();
      if (!picked) {
        setAlertModal({
          title: "Seleção de Saída",
          message:
            "Seu navegador usa o menu padrão de áudio. Use a lista 'Saída' ao lado ou configure a saída padrão no sistema.",
        });
        return;
      }
      await refreshDevices(false);
      setOutDeviceId(picked.deviceId);
      if (running) {
        await startAudio({ outId: picked.deviceId });
      }
    } catch {
      // User cancelled picker
    }
  };

  const quickPitch = (semitones: number) => {
    setParams((prev) => ({
      ...prev,
      pitch_enabled: Math.abs(semitones) > 0.01,
      pitch_semitones: semitones,
      pitch_cents: 0.0,
    }));
  };

  const quickFshift = (hz: number) => {
    setParams((prev) => ({
      ...prev,
      freq_shift_enabled: Math.abs(hz) > 0.5,
      freq_shift_hz: hz,
    }));
  };

  const resetEq = () => {
    setParams((prev) => ({
      ...prev,
      eq_band1_db: 0.0,
      eq_band2_db: 0.0,
      eq_band3_db: 0.0,
      eq_band4_db: 0.0,
      eq_band5_db: 0.0,
      eq_hpf_enabled: true,
      eq_hpf_hz: 80.0,
      eq_lpf_enabled: false,
      eq_lpf_hz: 12000.0,
    }));
  };

  const resetAllEffects = () => {
    setSelectedPreset("Normal (Limpo + Gate)");
    setParams({ ...createDefaultParams(), ...builtinPresets["Normal (Limpo + Gate)"] });
  };

  const inNorm = Math.max(0, Math.min(1, (inPeakDb + 60.0) / 60.0));
  const outNorm = Math.max(0, Math.min(1, (outPeakDb + 60.0) / 60.0));

  return (
    <div className="app-shell">
      {/* Barra Superior */}
      <header className="topbar">
        <div className="title-box">
          <img src="/icon.svg" alt="VoxCraft Studio" className="brand-icon" />
          <div className="title-text-col">
            <span className="app-title">VoxCraft Studio</span>
            <span className="app-subtitle">Efeitos estilo Audacity em tempo real para Discord & Jogos</span>
          </div>
        </div>

        <div className="preset-box">
          <span className="preset-label">Voz / Preset:</span>
          <select
            className="select-input select-preset"
            value={selectedPreset}
            onChange={(e) => handlePresetSelected(e.target.value)}
          >
            {allPresetNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn-blue"
            onClick={() => {
              setSaveNameInput("");
              setShowSaveModal(true);
            }}
          >
            Salvar Voz
          </button>
          <button type="button" className="btn btn-slate btn-delete" onClick={handleDeletePreset}>
            Excluir
          </button>
          <button
            type="button"
            className="btn btn-dark"
            onClick={handleExportPresets}
            title="Exportar user_presets.json"
          >
            Exportar
          </button>
          <button
            type="button"
            className="btn btn-dark"
            onClick={() => importInputRef.current?.click()}
            title="Importar user_presets.json"
          >
            Importar
          </button>
          <input
            ref={importInputRef}
            type="file"
            accept="application/json,.json"
            style={{ display: "none" }}
            onChange={(e) => {
              void handleImportPresets(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </div>

        <div className="right-top">
          <PWAInstallButton />
          <button
            type="button"
            className="btn btn-slate"
            onClick={() => void openMiniBackgroundWindow()}
            title="Abrir mini-janela compacta para manter em 2º plano"
          >
            Mini-Janela
          </button>
          <button type="button" className="btn btn-slate" onClick={() => setShowGuideModal(true)}>
            Guia Discord / Jogos
          </button>
          <ToggleSwitch
            label="Voz Original (Bypass)"
            checked={params.bypass}
            onChange={(v) => updateParam("bypass", v)}
            variant="amber"
            size="sm"
          />
          <button
            type="button"
            className={`btn ${running ? "btn-power-stop" : "btn-power-start"}`}
            onClick={() => void toggleAudio()}
          >
            {running ? "PARAR ÁUDIO" : "INICIAR ÁUDIO"}
          </button>
        </div>
      </header>

      {/* Corpo Principal */}
      <div className="main-body">
        {/* Sidebar */}
        <aside className="sidebar">
          <h2 className="sidebar-heading">Roteamento de Áudio</h2>

          <div className="field-group">
            <label className="field-label">Microfone (Entrada):</label>
            <select
              className="select-input select-full"
              value={inDeviceId}
              onChange={(e) => {
                const nextId = e.target.value;
                setInDeviceId(nextId);
                if (running) void startAudio({ inId: nextId });
              }}
            >
              {inDevices.length === 0 ? (
                <option value="default">Microfone Padrão do Navegador</option>
              ) : (
                inDevices.map((d) => (
                  <option key={d.deviceId} value={d.deviceId}>
                    {d.label}
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="field-group">
            <label className="field-label">Saída (VB-Cable p/ Discord ou Fone):</label>
            <select
              className="select-input select-full"
              value={outDeviceId}
              onChange={(e) => {
                const nextId = e.target.value;
                setOutDeviceId(nextId);
                if (running) void startAudio({ outId: nextId });
              }}
            >
              {outDevices.map((d) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.label}
                </option>
              ))}
            </select>
            {supportsSelectOutput && (
              <button
                type="button"
                className="btn btn-dark"
                onClick={() => void handleSelectSystemOutput()}
              >
                Escolher Saída do Sistema (VB-Cable)
              </button>
            )}
            {!supportsSinkId && (
              <div className="capability-note">
                Este navegador usa a saída padrão do sistema. Para selecionar VB-Cable direto na lista, use Chrome ou
                Edge.
              </div>
            )}
          </div>

          <ToggleSwitch
            label="Ouvir minha voz (Monitor no Fone)"
            checked={monitorEnabled}
            onChange={(v) => {
              setMonitorEnabled(v);
              if (running) void startAudio({ monEnabled: v });
            }}
          />

          <select
            className="select-input select-full"
            value={monDeviceId}
            onChange={(e) => {
              const nextId = e.target.value;
              setMonDeviceId(nextId);
              if (running) void startAudio({ monId: nextId });
            }}
          >
            {outDevices.map((d) => (
              <option key={d.deviceId} value={d.deviceId}>
                {d.label}
              </option>
            ))}
          </select>

          <div className="latency-row">
            <span className="field-label">Driver / Modo:</span>
            <select
              className="select-input"
              value={driverMode}
              onChange={(e) => {
                const nextMode = e.target.value as AudioDriverMode;
                setDriverMode(nextMode);
                if (running) void startAudio({ drvMode: nextMode });
              }}
            >
              <option value="interactive">Baixa Latência</option>
              <option value="balanced">Equilibrado</option>
              <option value="playback">Estável (Playback)</option>
            </select>
          </div>

          <div className="latency-row">
            <span className="field-label">Taxa (Sample Rate):</span>
            <select
              className="select-input"
              value={String(sampleRateOption)}
              onChange={(e) => {
                const raw = e.target.value;
                const nextSr: SampleRateOption =
                  raw === "auto" ? "auto" : (Number(raw) as 48000 | 44100);
                setSampleRateOption(nextSr);
                if (running) void startAudio({ srOption: nextSr });
              }}
            >
              <option value="48000">48000 Hz</option>
              <option value="44100">44100 Hz</option>
              <option value="auto">Automático</option>
            </select>
          </div>

          <div className="latency-row">
            <span className="field-label">Buffer / Latência:</span>
            <select
              className="select-input"
              value={latencyLabel}
              onChange={(e) => {
                const nextLat = e.target.value;
                setLatencyLabel(nextLat);
                if (running) void startAudio({ latLabel: nextLat });
              }}
            >
              <option value="Ultra (256)">Ultra (256)</option>
              <option value="Baixa (512)">Baixa (512)</option>
              <option value="Estável (1024)">Estável (1024)</option>
            </select>
          </div>

          <div className="latency-row">
            <span className="field-label">Ao fechar janela:</span>
            <select
              className="select-input"
              value={closeBehavior}
              onChange={(e) => {
                const val = e.target.value as CloseBehavior;
                setCloseBehavior(val);
                try {
                  localStorage.setItem(CLOSE_BEHAVIOR_KEY, val);
                } catch {
                  // ignore
                }
              }}
            >
              <option value="confirm_active">Confirmar se ativo</option>
              <option value="stop_immediately">Parar áudio e sair</option>
            </select>
          </div>

          <div className="btn-row">
            <button
              type="button"
              className="btn btn-slate"
              onClick={() => void refreshDevices(true)}
            >
              Atualizar Dispositivos
            </button>
          </div>

          <div
            className={`status-text ${
              statusState === "active"
                ? "status-active"
                : statusState === "error"
                ? "status-error"
                : ""
            }`}
          >
            {statusText}
          </div>

          {/* Medidores & Osciloscópio */}
          <div className="card">
            <div className="card-title">Níveis & Forma de Onda</div>
            <div className="meter-row">
              <span className="meter-label">Entrada</span>
              <div className="meter-track">
                <div className="meter-fill-in" style={{ width: `${(inNorm * 100).toFixed(1)}%` }} />
              </div>
            </div>
            <div className="meter-row">
              <span className="meter-label">Saída</span>
              <div className="meter-track">
                <div className="meter-fill-out" style={{ width: `${(outNorm * 100).toFixed(1)}%` }} />
              </div>
            </div>
            <div className={`gate-led ${gateIsOpen ? "gate-open" : "gate-closed"}`}>
              {gateIsOpen ? "● Noise Gate: Aberto" : "● Noise Gate: Silenciado"}
            </div>
            <WaveformCanvas waveform={waveform} running={running} bypass={params.bypass} />
          </div>

          {/* Limpeza & Ganho */}
          <div className="card">
            <div className="card-title">Limpeza & Ganho</div>
            <SliderRow
              label="Ganho Entrada (Mic)"
              min={-18.0}
              max={24.0}
              value={params.input_gain_db}
              unit="dB"
              onChange={(v) => updateParam("input_gain_db", v)}
            />
            <ToggleSwitch
              label="Noise Gate (Corta ruído)"
              checked={params.gate_enabled}
              onChange={(v) => updateParam("gate_enabled", v)}
            />
            <SliderRow
              label="Limite do Gate"
              min={-65.0}
              max={-15.0}
              value={params.gate_threshold_db}
              unit="dB"
              onChange={(v) => updateParam("gate_threshold_db", v)}
            />
            <ToggleSwitch
              label="Compressor (Nivelar voz)"
              checked={params.comp_enabled}
              onChange={(v) => updateParam("comp_enabled", v)}
            />
            <SliderRow
              label="Limite Compressor"
              min={-36.0}
              max={-4.0}
              value={params.comp_threshold_db}
              unit="dB"
              onChange={(v) => updateParam("comp_threshold_db", v)}
            />
            <SliderRow
              label="Volume Final (Saída)"
              min={-24.0}
              max={24.0}
              value={params.output_gain_db}
              unit="dB"
              onChange={(v) => updateParam("output_gain_db", v)}
            />
          </div>
        </aside>

        {/* Workbench (Abas) */}
        <main className="workbench">
          <div className="tab-bar">
            <button
              type="button"
              className={`tab-btn ${activeTab === "pitch" ? "active" : ""}`}
              onClick={() => setActiveTab("pitch")}
            >
              1. Tom & Frequency Shifter
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === "eq" ? "active" : ""}`}
              onClick={() => setActiveTab("eq")}
            >
              2. Equalizador (Audacity)
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === "fx" ? "active" : ""}`}
              onClick={() => setActiveTab("fx")}
            >
              3. Robô, Rádio & Distorção
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === "space" ? "active" : ""}`}
              onClick={() => setActiveTab("space")}
            >
              4. Eco & Reverb
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === "mixer" ? "active" : ""}`}
              onClick={() => setActiveTab("mixer")}
            >
              5. Mixer Rápido
            </button>
          </div>

          <div className="tab-content">
            {activeTab === "pitch" && (
              <>
                <div className="workbench-card">
                  <ToggleSwitch
                    label="Alterar Tom (Pitch Shifter — estilo 'Alterar Tom' do Audacity)"
                    checked={params.pitch_enabled}
                    onChange={(v) => updateParam("pitch_enabled", v)}
                    size="bold"
                  />
                  <p className="card-desc">
                    Valores negativos deixam a voz mais grave/monstro; positivos deixam mais fina/aguda, mantendo a
                    velocidade da fala.
                  </p>
                  <SliderRow
                    label="Semitons"
                    min={-12.0}
                    max={12.0}
                    step={0.1}
                    value={params.pitch_semitones}
                    unit="st"
                    onChange={(v) => updateParam("pitch_semitones", v)}
                  />
                  <SliderRow
                    label="Ajuste Fino (Cents)"
                    min={-100.0}
                    max={100.0}
                    step={1.0}
                    value={params.pitch_cents}
                    unit="ct"
                    onChange={(v) => updateParam("pitch_cents", v)}
                  />
                  <SliderRow
                    label="Mistura (Dry / Wet)"
                    min={0.0}
                    max={100.0}
                    step={1.0}
                    value={params.pitch_mix * 100.0}
                    unit="%"
                    onChange={(v) => updateParam("pitch_mix", v / 100.0)}
                  />
                  <div className="quick-row">
                    <span className="quick-label">Atalhos rápidos:</span>
                    {[
                      ["-1 Oitava (-12)", -12.0],
                      ["Grave (-5)", -5.0],
                      ["Leve Grave (-2)", -2.0],
                      ["Original (0)", 0.0],
                      ["Fina (+4)", 4.0],
                      ["Esquilo (+7)", 7.0],
                      ["+1 Oitava (+12)", 12.0],
                    ].map(([lbl, val]) => (
                      <button
                        key={String(lbl)}
                        type="button"
                        className="btn btn-dark"
                        onClick={() => quickPitch(Number(val))}
                      >
                        {lbl}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="workbench-card">
                  <ToggleSwitch
                    label="Frequency Shifter (Deslocamento Linear em Hz)"
                    checked={params.freq_shift_enabled}
                    onChange={(v) => updateParam("freq_shift_enabled", v)}
                    size="bold"
                  />
                  <p className="card-desc">
                    Diferente do Pitch, desloca todas as frequências por um valor fixo em Hz (+ ou -). Cria vozes
                    alienígenas, metálicas e sintéticas!
                  </p>
                  <SliderRow
                    label="Deslocamento (Hz)"
                    min={-500.0}
                    max={500.0}
                    step={1.0}
                    value={params.freq_shift_hz}
                    unit="Hz"
                    onChange={(v) => updateParam("freq_shift_hz", v)}
                  />
                  <SliderRow
                    label="Mistura (Dry / Wet)"
                    min={0.0}
                    max={100.0}
                    step={1.0}
                    value={params.freq_shift_mix * 100.0}
                    unit="%"
                    onChange={(v) => updateParam("freq_shift_mix", v / 100.0)}
                  />
                  <div className="quick-row">
                    {[
                      ["-120 Hz", -120.0],
                      ["-30 Hz", -30.0],
                      ["0 Hz", 0.0],
                      ["+50 Hz", 50.0],
                      ["+180 Hz", 180.0],
                    ].map(([lbl, val]) => (
                      <button
                        key={String(lbl)}
                        type="button"
                        className="btn btn-dark"
                        onClick={() => quickFshift(Number(val))}
                      >
                        {lbl}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {activeTab === "eq" && (
              <>
                <div className="workbench-card">
                  <div className="card-header-row">
                    <ToggleSwitch
                      label="Ativar Equalizador (Curva de Filtro estilo Audacity)"
                      checked={params.eq_enabled}
                      onChange={(v) => updateParam("eq_enabled", v)}
                      size="bold"
                    />
                    <button type="button" className="btn btn-slate" onClick={resetEq}>
                      Zerar EQ (Flat)
                    </button>
                  </div>
                  <EqCurveCanvas params={params} sampleRate={sampleRate} />
                </div>

                <div className="workbench-card" style={{ flex: 1 }}>
                  <div className="eq-cuts-row">
                    <div className="subcard">
                      <ToggleSwitch
                        label="Corte Graves (Passa-Altas)"
                        checked={params.eq_hpf_enabled}
                        onChange={(v) => updateParam("eq_hpf_enabled", v)}
                      />
                      <SliderRow
                        label="Frequência"
                        min={20.0}
                        max={1000.0}
                        step={5.0}
                        value={params.eq_hpf_hz}
                        unit="Hz"
                        onChange={(v) => updateParam("eq_hpf_hz", v)}
                      />
                    </div>
                    <div className="subcard">
                      <ToggleSwitch
                        label="Corte Agudos (Passa-Baixas)"
                        checked={params.eq_lpf_enabled}
                        onChange={(v) => updateParam("eq_lpf_enabled", v)}
                      />
                      <SliderRow
                        label="Frequência"
                        min={1200.0}
                        max={18000.0}
                        step={100.0}
                        value={params.eq_lpf_hz}
                        unit="Hz"
                        onChange={(v) => updateParam("eq_lpf_hz", v)}
                      />
                    </div>
                  </div>

                  <div className="eq-bands-row">
                    <VerticalEqBand
                      title={"Grave\n120 Hz"}
                      value={params.eq_band1_db}
                      onChange={(v) => updateParam("eq_band1_db", v)}
                    />
                    <VerticalEqBand
                      title={"Méd-Grave\n400 Hz"}
                      value={params.eq_band2_db}
                      onChange={(v) => updateParam("eq_band2_db", v)}
                    />
                    <VerticalEqBand
                      title={"Presença\n1.2 kHz"}
                      value={params.eq_band3_db}
                      onChange={(v) => updateParam("eq_band3_db", v)}
                    />
                    <VerticalEqBand
                      title={"Brilho\n3.5 kHz"}
                      value={params.eq_band4_db}
                      onChange={(v) => updateParam("eq_band4_db", v)}
                    />
                    <VerticalEqBand
                      title={"Agudo\n7.5 kHz"}
                      value={params.eq_band5_db}
                      onChange={(v) => updateParam("eq_band5_db", v)}
                    />
                  </div>
                </div>
              </>
            )}

            {activeTab === "fx" && (
              <>
                <div className="workbench-card">
                  <ToggleSwitch
                    label="Modulador em Anel / Robô (Ring Modulator)"
                    checked={params.ring_enabled}
                    onChange={(v) => updateParam("ring_enabled", v)}
                    size="bold"
                  />
                  <p className="card-desc">
                    Multiplica a voz por uma onda osciladora. Frequências entre 30–90 Hz criam efeito Robô/Dalek
                    clássico.
                  </p>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span className="field-label">Forma de Onda:</span>
                    <select
                      className="select-input"
                      value={params.ring_waveform}
                      onChange={(e) => updateParam("ring_waveform", e.target.value as RingWaveform)}
                    >
                      <option value="Senoide">Senoide</option>
                      <option value="Quadrada">Quadrada</option>
                      <option value="Triangular">Triangular</option>
                    </select>
                  </div>
                  <SliderRow
                    label="Frequência Portadora"
                    min={5.0}
                    max={400.0}
                    step={1.0}
                    value={params.ring_freq_hz}
                    unit="Hz"
                    onChange={(v) => updateParam("ring_freq_hz", v)}
                  />
                  <SliderRow
                    label="Mistura (Mix)"
                    min={0.0}
                    max={100.0}
                    step={1.0}
                    value={params.ring_mix * 100.0}
                    unit="%"
                    onChange={(v) => updateParam("ring_mix", v / 100.0)}
                  />
                </div>

                <div className="workbench-card">
                  <ToggleSwitch
                    label="Distorção & Bitcrusher (Rádio / Mega-fone / Lo-Fi)"
                    checked={params.dist_enabled}
                    onChange={(v) => updateParam("dist_enabled", v)}
                    size="bold"
                  />
                  <p className="card-desc">
                    Adiciona saturação analógica, redução de bits (8-bit/rádio) e redução de taxa de amostragem.
                  </p>
                  <SliderRow
                    label="Drive / Saturação"
                    min={1.0}
                    max={25.0}
                    step={0.2}
                    value={params.dist_drive}
                    unit="x"
                    onChange={(v) => updateParam("dist_drive", v)}
                  />
                  <SliderRow
                    label="Resolução (Bits)"
                    min={4.0}
                    max={16.0}
                    step={1.0}
                    value={params.dist_bits}
                    unit="bits"
                    onChange={(v) => updateParam("dist_bits", Math.round(v))}
                  />
                  <SliderRow
                    label="Downsample (Lo-Fi)"
                    min={1.0}
                    max={16.0}
                    step={1.0}
                    value={params.dist_downsample}
                    unit="x"
                    onChange={(v) => updateParam("dist_downsample", Math.round(v))}
                  />
                  <SliderRow
                    label="Mistura (Mix)"
                    min={0.0}
                    max={100.0}
                    step={1.0}
                    value={params.dist_mix * 100.0}
                    unit="%"
                    onChange={(v) => updateParam("dist_mix", v / 100.0)}
                  />
                </div>
              </>
            )}

            {activeTab === "space" && (
              <>
                <div className="workbench-card">
                  <ToggleSwitch
                    label="Eco / Delay (estilo 'Eco' do Audacity)"
                    checked={params.echo_enabled}
                    onChange={(v) => updateParam("echo_enabled", v)}
                    size="bold"
                  />
                  <p className="card-desc">
                    Dica: Use atrasos curtos (10–25 ms) com feedback alto para som de Capacete/Tubo metálico, ou 250–500
                    ms para Eco de Caverna.
                  </p>
                  <SliderRow
                    label="Tempo de Atraso"
                    min={10.0}
                    max={700.0}
                    step={2.0}
                    value={params.echo_delay_ms}
                    unit="ms"
                    onChange={(v) => updateParam("echo_delay_ms", v)}
                  />
                  <SliderRow
                    label="Repetições (Feedback)"
                    min={0.0}
                    max={85.0}
                    step={1.0}
                    value={params.echo_feedback * 100.0}
                    unit="%"
                    onChange={(v) => updateParam("echo_feedback", v / 100.0)}
                  />
                  <SliderRow
                    label="Volume do Eco"
                    min={0.0}
                    max={100.0}
                    step={1.0}
                    value={params.echo_mix * 100.0}
                    unit="%"
                    onChange={(v) => updateParam("echo_mix", v / 100.0)}
                  />
                </div>

                <div className="workbench-card">
                  <ToggleSwitch
                    label="Reverberação (Reverb de Sala / Catedral)"
                    checked={params.reverb_enabled}
                    onChange={(v) => updateParam("reverb_enabled", v)}
                    size="bold"
                  />
                  <SliderRow
                    label="Tamanho da Sala"
                    min={0.0}
                    max={100.0}
                    step={1.0}
                    value={params.reverb_room * 100.0}
                    unit="%"
                    onChange={(v) => updateParam("reverb_room", v / 100.0)}
                  />
                  <SliderRow
                    label="Abafamento (Damping)"
                    min={5.0}
                    max={92.0}
                    step={1.0}
                    value={params.reverb_damp * 100.0}
                    unit="%"
                    onChange={(v) => updateParam("reverb_damp", v / 100.0)}
                  />
                  <SliderRow
                    label="Mistura do Reverb"
                    min={0.0}
                    max={100.0}
                    step={1.0}
                    value={params.reverb_mix * 100.0}
                    unit="%"
                    onChange={(v) => updateParam("reverb_mix", v / 100.0)}
                  />
                </div>
              </>
            )}

            {activeTab === "mixer" && (
              <div className="workbench-card" style={{ flex: 1 }}>
                <div style={{ fontSize: 15, fontWeight: 700, paddingBottom: 4 }}>
                  Visão Rápida da Cadeia de Efeitos (Ligue/Desligue módulos instantaneamente)
                </div>

                <div className="mixer-grid">
                  <div className="mixer-card">
                    <ToggleSwitch
                      label="Noise Gate (Corte de ruído)"
                      checked={params.gate_enabled}
                      onChange={(v) => updateParam("gate_enabled", v)}
                      size="md"
                    />
                  </div>
                  <div className="mixer-card">
                    <ToggleSwitch
                      label="Compressor de Voz"
                      checked={params.comp_enabled}
                      onChange={(v) => updateParam("comp_enabled", v)}
                      size="md"
                    />
                  </div>
                  <div className="mixer-card">
                    <ToggleSwitch
                      label="Alterar Tom (Pitch Shifter)"
                      checked={params.pitch_enabled}
                      onChange={(v) => updateParam("pitch_enabled", v)}
                      size="md"
                    />
                  </div>
                  <div className="mixer-card">
                    <ToggleSwitch
                      label="Frequency Shifter (Hz)"
                      checked={params.freq_shift_enabled}
                      onChange={(v) => updateParam("freq_shift_enabled", v)}
                      size="md"
                    />
                  </div>
                  <div className="mixer-card">
                    <ToggleSwitch
                      label="Equalizador (EQ 5 Bandas + Cortes)"
                      checked={params.eq_enabled}
                      onChange={(v) => updateParam("eq_enabled", v)}
                      size="md"
                    />
                  </div>
                  <div className="mixer-card">
                    <ToggleSwitch
                      label="Modulador em Anel (Robô)"
                      checked={params.ring_enabled}
                      onChange={(v) => updateParam("ring_enabled", v)}
                      size="md"
                    />
                  </div>
                  <div className="mixer-card">
                    <ToggleSwitch
                      label="Distorção & Bitcrusher (Rádio/Lo-Fi)"
                      checked={params.dist_enabled}
                      onChange={(v) => updateParam("dist_enabled", v)}
                      size="md"
                    />
                  </div>
                  <div className="mixer-card">
                    <ToggleSwitch
                      label="Eco / Delay"
                      checked={params.echo_enabled}
                      onChange={(v) => updateParam("echo_enabled", v)}
                      size="md"
                    />
                  </div>
                  <div className="mixer-card">
                    <ToggleSwitch
                      label="Reverberação (Reverb)"
                      checked={params.reverb_enabled}
                      onChange={(v) => updateParam("reverb_enabled", v)}
                      size="md"
                    />
                  </div>
                </div>

                <div className="mixer-footer">
                  <button type="button" className="btn btn-danger" onClick={resetAllEffects}>
                    Resetar Todos os Efeitos (Voz Limpa)
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Mini-Janela Flutuante (Fallback caso Document PiP não esteja disponível) */}
      {showFloatingMini && (
        <div className="mini-tray-widget">
          <div className="mini-tray-header">
            <div className="mini-tray-brand">
              <img src="/icon.svg" alt="VoxCraft" style={{ width: 20, height: 20, borderRadius: 4 }} />
              <span>VoxCraft — Mini</span>
            </div>
            <button
              type="button"
              className="btn btn-dark"
              onClick={() => setShowFloatingMini(false)}
            >
              Fechar
            </button>
          </div>
          <div className="status-text">Preset: {selectedPreset}</div>
          <div className="meter-row">
            <span className="meter-label">Saída</span>
            <div className="meter-track">
              <div className="meter-fill-out" style={{ width: `${(outNorm * 100).toFixed(1)}%` }} />
            </div>
          </div>
          <div className="btn-row">
            <button
              type="button"
              className={`btn ${running ? "btn-power-stop" : "btn-power-start"}`}
              style={{ height: 32, minWidth: 0 }}
              onClick={() => void toggleAudio()}
            >
              {running ? "PARAR ÁUDIO" : "INICIAR ÁUDIO"}
            </button>
            <button
              type="button"
              className="btn btn-slate"
              onClick={() => updateParam("bypass", !params.bypass)}
            >
              {params.bypass ? "Bypass: ON" : "Bypass: OFF"}
            </button>
          </div>
        </div>
      )}

      {!isOnline && (
        <div className="offline-banner">Modo Offline — DSP local ativo</div>
      )}

      {/* Modal Guia Discord / Jogos */}
      {showGuideModal && (
        <div className="modal-backdrop" onClick={() => setShowGuideModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Roteamento para Discord e Jogos</h3>
            <p className="modal-body">
              {
                "Para enviar a sua voz modificada para o Discord e qualquer jogo, você precisa de um cabo de áudio virtual (gratuito):\n\n1. Instale o VB-Audio Virtual Cable (VB-Cable):\n   • Baixe em: vb-audio.com/Cable (Windows/macOS) e reinicie se solicitado.\n   • No Linux, use PipeWire/PulseAudio virtual sink.\n\n2. Configure aqui no VoxCraft Studio:\n   • Microfone (Entrada): Escolha o seu microfone físico.\n   • Saída: Escolha 'CABLE Input (VB-Audio Virtual Cable)' (use Chrome ou Edge para roteamento direto via setSinkId).\n   • Marque 'Ouvir minha voz' apenas enquanto estiver testando nos seus fones!\n   • Clique em INICIAR ÁUDIO.\n\n3. Configure no Discord / Jogos:\n   • No Discord: Configurações > Voz e Vídeo > Dispositivo de Entrada:\n     Selecione 'CABLE Output (VB-Audio Virtual Cable)'.\n   • Dica Discord: Desative o 'Supressão de Ruído Krisp' do Discord se ele estiver cortando efeitos como Robô, Eco ou Voz Grave."
              }
            </p>
            <div className="modal-actions">
              <button type="button" className="btn btn-blue" onClick={() => setShowGuideModal(false)}>
                Entendi!
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Salvar Voz Personalizada */}
      {showSaveModal && (
        <div className="modal-backdrop" onClick={() => setShowSaveModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Salvar Voz Personalizada</h3>
            <p className="modal-body">Digite um nome para esta voz:</p>
            <input
              type="text"
              className="modal-input"
              value={saveNameInput}
              autoFocus
              placeholder="Ex: Minha Voz Grave"
              onChange={(e) => setSaveNameInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleConfirmSavePreset();
              }}
            />
            <div className="modal-actions">
              <button type="button" className="btn btn-slate" onClick={() => setShowSaveModal(false)}>
                Cancelar
              </button>
              <button type="button" className="btn btn-blue" onClick={handleConfirmSavePreset}>
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Alerta / Erro */}
      {alertModal && (
        <div className="modal-backdrop" onClick={() => setAlertModal(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">{alertModal.title}</h3>
            <p className="modal-body">{alertModal.message}</p>
            <div className="modal-actions">
              <button type="button" className="btn btn-blue" onClick={() => setAlertModal(null)}>
                OK
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
