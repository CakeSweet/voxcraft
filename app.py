import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk
import numpy as np
from scipy import signal

from dsp_engine import DSPParams, RealTimeDSPEngine, build_eq_sos
from presets import get_builtin_presets, load_user_presets, save_user_presets
from audio_router import AudioDeviceItem, AudioRouter

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class VoxCraftApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VoxCraft Studio — Modulador de Voz em Tempo Real (Estilo Audacity)")
        self.geometry("1220x780")
        self.minsize(1060, 680)

        self.dsp = RealTimeDSPEngine(48000.0)
        self.router = AudioRouter(self.dsp)
        self.params = DSPParams()

        self.builtin_presets = get_builtin_presets()
        self.user_presets = load_user_presets()

        self.in_devices: list[AudioDeviceItem] = []
        self.out_devices: list[AudioDeviceItem] = []
        self._syncing_ui = False

        self._build_layout()
        self._refresh_devices()
        self._apply_preset("Normal (Limpo + Gate)")
        self._schedule_ui_loop()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    # Construção da Interface
    # ------------------------------------------------------------------ #
    def _build_layout(self):
        # Barra Superior
        topbar = ctk.CTkFrame(self, height=64, corner_radius=10, fg_color="#161b24")
        topbar.pack(fill="x", padx=12, pady=(10, 6))
        topbar.pack_propagate(False)

        title_box = ctk.CTkFrame(topbar, fg_color="transparent")
        title_box.pack(side="left", padx=14)
        ctk.CTkLabel(
            title_box, text="VoxCraft Studio", font=ctk.CTkFont(size=20, weight="bold"), text_color="#4cc9f0"
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_box,
            text="Efeitos estilo Audacity em tempo real para Discord & Jogos",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w")

        # Controles de Preset no Topo
        preset_box = ctk.CTkFrame(topbar, fg_color="transparent")
        preset_box.pack(side="left", padx=20)
        ctk.CTkLabel(preset_box, text="Voz / Preset:", font=ctk.CTkFont(size=12, weight="bold")).pack(
            side="left", padx=(0, 6)
        )
        self.preset_var = ctk.StringVar(value="Normal (Limpo + Gate)")
        self.preset_menu = ctk.CTkOptionMenu(
            preset_box,
            variable=self.preset_var,
            values=self._all_preset_names(),
            width=230,
            command=self._on_preset_selected,
        )
        self.preset_menu.pack(side="left", padx=4)

        ctk.CTkButton(
            preset_box, text="Salvar Voz", width=95, fg_color="#2563eb", command=self._save_custom_preset
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            preset_box, text="Excluir", width=70, fg_color="#475569", hover_color="#dc2626",
            command=self._delete_custom_preset
        ).pack(side="left", padx=4)

        # Botões da Direita (Guia, Bypass, Ligar)
        right_top = ctk.CTkFrame(topbar, fg_color="transparent")
        right_top.pack(side="right", padx=12)

        ctk.CTkButton(
            right_top, text="Guia Discord / Jogos", width=145, fg_color="#334155",
            hover_color="#475569", command=self._open_discord_guide
        ).pack(side="left", padx=6)

        self.bypass_var = ctk.BooleanVar(value=False)
        self.bypass_btn = ctk.CTkSwitch(
            right_top,
            text="Voz Original (Bypass)",
            variable=self.bypass_var,
            progress_color="#f59e0b",
            command=self._on_param_change,
        )
        self.bypass_btn.pack(side="left", padx=10)

        self.power_btn = ctk.CTkButton(
            right_top,
            text="INICIAR ÁUDIO",
            width=145,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self._toggle_audio,
        )
        self.power_btn.pack(side="left", padx=4)

        # Corpo Principal: Sidebar (Esquerda) + Workbench (Direita)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(2, 10))

        self._build_sidebar(body)
        self._build_workbench(body)

    def _build_sidebar(self, parent):
        side = ctk.CTkScrollableFrame(parent, width=320, corner_radius=10, fg_color="#161b24")
        side.pack(side="left", fill="y", padx=(0, 8))

        ctk.CTkLabel(
            side, text="Roteamento de Áudio", font=ctk.CTkFont(size=15, weight="bold"), text_color="#e2e8f0"
        ).pack(anchor="w", padx=10, pady=(6, 4))

        # Entrada
        ctk.CTkLabel(side, text="Microfone (Entrada):", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10)
        self.in_dev_var = ctk.StringVar()
        self.in_dev_menu = ctk.CTkOptionMenu(side, variable=self.in_dev_var, values=[""], width=285)
        self.in_dev_menu.pack(padx=10, pady=(2, 8))

        # Saída
        ctk.CTkLabel(side, text="Saída (VB-Cable p/ Discord ou Fone):", font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=10
        )
        self.out_dev_var = ctk.StringVar()
        self.out_dev_menu = ctk.CTkOptionMenu(side, variable=self.out_dev_var, values=[""], width=285)
        self.out_dev_menu.pack(padx=10, pady=(2, 8))

        # Monitoramento (Ouvir a própria voz)
        self.monitor_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            side, text="Ouvir minha voz (Monitor no Fone)", variable=self.monitor_var, command=self._restart_if_running
        ).pack(anchor="w", padx=10, pady=(4, 4))
        self.mon_dev_var = ctk.StringVar()
        self.mon_dev_menu = ctk.CTkOptionMenu(side, variable=self.mon_dev_var, values=[""], width=285)
        self.mon_dev_menu.pack(padx=10, pady=(2, 8))

        # Latência e Atualizar
        lat_row = ctk.CTkFrame(side, fg_color="transparent")
        lat_row.pack(fill="x", padx=10, pady=(2, 6))
        ctk.CTkLabel(lat_row, text="Buffer / Latência:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.latency_var = ctk.StringVar(value="Baixa (512)")
        ctk.CTkOptionMenu(
            lat_row,
            variable=self.latency_var,
            values=["Ultra (256)", "Baixa (512)", "Estável (1024)"],
            width=145,
            command=lambda _: self._restart_if_running(),
        ).pack(side="right")

        ctk.CTkButton(
            side, text="Atualizar Dispositivos", height=28, fg_color="#334155", command=self._refresh_devices
        ).pack(fill="x", padx=10, pady=(2, 6))

        self.status_lbl = ctk.CTkLabel(
            side, text="Status: Parado", font=ctk.CTkFont(size=11), text_color="#94a3b8", wraplength=280
        )
        self.status_lbl.pack(anchor="w", padx=10, pady=(0, 8))

        # Medidores ao vivo + Osciloscópio
        meter_card = ctk.CTkFrame(side, fg_color="#0f172a", corner_radius=8)
        meter_card.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(meter_card, text="Níveis & Forma de Onda", font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="w", padx=10, pady=(6, 4)
        )

        # Entrada VU
        row_in = ctk.CTkFrame(meter_card, fg_color="transparent")
        row_in.pack(fill="x", padx=10)
        ctk.CTkLabel(row_in, text="Entrada", width=55, anchor="w", font=ctk.CTkFont(size=11)).pack(side="left")
        self.in_bar = ctk.CTkProgressBar(row_in, height=10, progress_color="#38bdf8")
        self.in_bar.set(0)
        self.in_bar.pack(side="left", fill="x", expand=True, padx=6)

        # Saída VU
        row_out = ctk.CTkFrame(meter_card, fg_color="transparent")
        row_out.pack(fill="x", padx=10, pady=(4, 4))
        ctk.CTkLabel(row_out, text="Saída", width=55, anchor="w", font=ctk.CTkFont(size=11)).pack(side="left")
        self.out_bar = ctk.CTkProgressBar(row_out, height=10, progress_color="#10b981")
        self.out_bar.set(0)
        self.out_bar.pack(side="left", fill="x", expand=True, padx=6)

        self.gate_led = ctk.CTkLabel(
            meter_card, text="● Noise Gate: Aberto", font=ctk.CTkFont(size=11), text_color="#10b981"
        )
        self.gate_led.pack(anchor="w", padx=10, pady=(0, 4))

        self.wave_canvas = tk.Canvas(meter_card, height=68, bg="#090d16", highlightthickness=0)
        self.wave_canvas.pack(fill="x", padx=10, pady=(2, 10))

        # Pré-processamento & Ganho Final
        dyn_card = ctk.CTkFrame(side, fg_color="#0f172a", corner_radius=8)
        dyn_card.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(dyn_card, text="Limpeza & Ganho", font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="w", padx=10, pady=(6, 4)
        )

        self.input_gain_var = self._add_slider(
            dyn_card, "Ganho Entrada (Mic)", -18.0, 24.0, 0.0, "dB"
        )
        self.gate_en_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            dyn_card, text="Noise Gate (Corta ruído)", variable=self.gate_en_var, command=self._on_param_change
        ).pack(anchor="w", padx=10, pady=(4, 0))
        self.gate_thresh_var = self._add_slider(
            dyn_card, "Limite do Gate", -65.0, -15.0, -42.0, "dB"
        )

        self.comp_en_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            dyn_card, text="Compressor (Nivelar voz)", variable=self.comp_en_var, command=self._on_param_change
        ).pack(anchor="w", padx=10, pady=(4, 0))
        self.comp_thresh_var = self._add_slider(
            dyn_card, "Limite Compressor", -36.0, -4.0, -18.0, "dB"
        )
        self.output_gain_var = self._add_slider(
            dyn_card, "Volume Final (Saída)", -24.0, 24.0, 0.0, "dB"
        )

    def _build_workbench(self, parent):
        self.tabs = ctk.CTkTabview(parent, corner_radius=10, fg_color="#161b24")
        self.tabs.pack(side="left", fill="both", expand=True)

        t_pitch = self.tabs.add("1. Tom & Frequency Shifter")
        t_eq = self.tabs.add("2. Equalizador (Audacity)")
        t_fx = self.tabs.add("3. Robô, Rádio & Distorção")
        t_space = self.tabs.add("4. Eco & Reverb")
        t_mixer = self.tabs.add("5. Mixer Rápido")

        self._build_pitch_tab(t_pitch)
        self._build_eq_tab(t_eq)
        self._build_fx_tab(t_fx)
        self._build_space_tab(t_space)
        self._build_mixer_tab(t_mixer)

    def _build_pitch_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Card: Alterar Tom (Pitch Shifter)
        card1 = ctk.CTkFrame(scroll, fg_color="#0f172a", corner_radius=10)
        card1.pack(fill="x", padx=10, pady=8)

        hdr1 = ctk.CTkFrame(card1, fg_color="transparent")
        hdr1.pack(fill="x", padx=14, pady=(10, 4))
        self.pitch_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            hdr1,
            text="Alterar Tom (Pitch Shifter — estilo 'Alterar Tom' do Audacity)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.pitch_en_var,
            command=self._on_param_change,
        ).pack(side="left")

        ctk.CTkLabel(
            card1,
            text="Valores negativos deixam a voz mais grave/monstro; positivos deixam mais fina/aguda, mantendo a velocidade da fala.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        self.pitch_st_var = self._add_slider(card1, "Semitons", -12.0, 12.0, 0.0, "st", step=0.1)
        self.pitch_cents_var = self._add_slider(card1, "Ajuste Fino (Cents)", -100.0, 100.0, 0.0, "ct", step=1.0)
        self.pitch_mix_var = self._add_slider(card1, "Mistura (Dry / Wet)", 0.0, 100.0, 100.0, "%", step=1.0)

        # Atalhos rápidos de Pitch
        qrow = ctk.CTkFrame(card1, fg_color="transparent")
        qrow.pack(fill="x", padx=14, pady=(4, 12))
        ctk.CTkLabel(qrow, text="Atalhos rápidos:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(
            side="left", padx=(0, 8)
        )
        for label, st_val in [
            ("-1 Oitava (-12)", -12.0),
            ("Grave (-5)", -5.0),
            ("Leve Grave (-2)", -2.0),
            ("Original (0)", 0.0),
            ("Fina (+4)", 4.0),
            ("Esquilo (+7)", 7.0),
            ("+1 Oitava (+12)", 12.0),
        ]:
            ctk.CTkButton(
                qrow,
                text=label,
                width=90,
                height=26,
                fg_color="#1e293b",
                hover_color="#334155",
                command=lambda v=st_val: self._quick_pitch(v),
            ).pack(side="left", padx=3)

        # Card: Frequency Shifter (Hilbert)
        card2 = ctk.CTkFrame(scroll, fg_color="#0f172a", corner_radius=10)
        card2.pack(fill="x", padx=10, pady=8)

        hdr2 = ctk.CTkFrame(card2, fg_color="transparent")
        hdr2.pack(fill="x", padx=14, pady=(10, 4))
        self.fshift_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            hdr2,
            text="Frequency Shifter (Deslocamento Linear em Hz)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.fshift_en_var,
            command=self._on_param_change,
        ).pack(side="left")

        ctk.CTkLabel(
            card2,
            text="Diferente do Pitch, desloca todas as frequências por um valor fixo em Hz (+ ou -). Cria vozes alienígenas, metálicas e sintéticas!",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        self.fshift_hz_var = self._add_slider(card2, "Deslocamento (Hz)", -500.0, 500.0, 0.0, "Hz", step=1.0)
        self.fshift_mix_var = self._add_slider(card2, "Mistura (Dry / Wet)", 0.0, 100.0, 100.0, "%", step=1.0)

        qrow2 = ctk.CTkFrame(card2, fg_color="transparent")
        qrow2.pack(fill="x", padx=14, pady=(4, 12))
        for label, hz_val in [("-120 Hz", -120.0), ("-30 Hz", -30.0), ("0 Hz", 0.0), ("+50 Hz", 50.0), ("+180 Hz", 180.0)]:
            ctk.CTkButton(
                qrow2,
                text=label,
                width=85,
                height=26,
                fg_color="#1e293b",
                hover_color="#334155",
                command=lambda v=hz_val: self._quick_fshift(v),
            ).pack(side="left", padx=4)

    def _build_eq_tab(self, tab):
        top = ctk.CTkFrame(tab, fg_color="#0f172a", corner_radius=10)
        top.pack(fill="x", padx=10, pady=8)

        hdr = ctk.CTkFrame(top, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(8, 4))
        self.eq_en_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            hdr,
            text="Ativar Equalizador (Curva de Filtro estilo Audacity)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.eq_en_var,
            command=self._on_param_change,
        ).pack(side="left")

        ctk.CTkButton(
            hdr, text="Zerar EQ (Flat)", width=110, height=28, fg_color="#334155", command=self._reset_eq
        ).pack(side="right")

        # Gráfico da curva de resposta de frequência
        self.eq_canvas = tk.Canvas(top, height=195, bg="#090d16", highlightthickness=1, highlightbackground="#1e293b")
        self.eq_canvas.pack(fill="x", padx=14, pady=(4, 12))
        self.eq_canvas.bind("<Configure>", lambda _e: self._draw_eq_curve())

        # Controles de Corte (HPF / LPF) e 5 Bandas
        bot = ctk.CTkFrame(tab, fg_color="#0f172a", corner_radius=10)
        bot.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        cuts = ctk.CTkFrame(bot, fg_color="transparent")
        cuts.pack(fill="x", padx=14, pady=(10, 4))

        # HPF
        hpf_box = ctk.CTkFrame(cuts, fg_color="#161f33", corner_radius=8)
        hpf_box.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.hpf_en_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            hpf_box, text="Corte Graves (Passa-Altas)", variable=self.hpf_en_var, command=self._on_param_change
        ).pack(anchor="w", padx=10, pady=(6, 0))
        self.hpf_hz_var = self._add_slider(hpf_box, "Frequência", 20.0, 1000.0, 80.0, "Hz", step=5.0)

        # LPF
        lpf_box = ctk.CTkFrame(cuts, fg_color="#161f33", corner_radius=8)
        lpf_box.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.lpf_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            lpf_box, text="Corte Agudos (Passa-Baixas)", variable=self.lpf_en_var, command=self._on_param_change
        ).pack(anchor="w", padx=10, pady=(6, 0))
        self.lpf_hz_var = self._add_slider(lpf_box, "Frequência", 1200.0, 18000.0, 12000.0, "Hz", step=100.0)

        # 5 Bandas verticais estilo mesa / Audacity
        bands_frame = ctk.CTkFrame(bot, fg_color="transparent")
        bands_frame.pack(fill="both", expand=True, padx=14, pady=8)

        self.eq_b1_var = self._add_vertical_eq_band(bands_frame, "Grave\n120 Hz")
        self.eq_b2_var = self._add_vertical_eq_band(bands_frame, "Méd-Grave\n400 Hz")
        self.eq_b3_var = self._add_vertical_eq_band(bands_frame, "Presença\n1.2 kHz")
        self.eq_b4_var = self._add_vertical_eq_band(bands_frame, "Brilho\n3.5 kHz")
        self.eq_b5_var = self._add_vertical_eq_band(bands_frame, "Agudo\n7.5 kHz")

    def _build_fx_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Modulador em Anel
        c1 = ctk.CTkFrame(scroll, fg_color="#0f172a", corner_radius=10)
        c1.pack(fill="x", padx=10, pady=8)
        self.ring_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            c1,
            text="Modulador em Anel / Robô (Ring Modulator)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.ring_en_var,
            command=self._on_param_change,
        ).pack(anchor="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(
            c1,
            text="Multiplica a voz por uma onda osciladora. Frequências entre 30–90 Hz criam efeito Robô/Dalek clássico.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        wave_row = ctk.CTkFrame(c1, fg_color="transparent")
        wave_row.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(wave_row, text="Forma de Onda:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        self.ring_wave_var = ctk.StringVar(value="Senoide")
        ctk.CTkOptionMenu(
            wave_row,
            variable=self.ring_wave_var,
            values=["Senoide", "Quadrada", "Triangular"],
            command=lambda _: self._on_param_change(),
        ).pack(side="left")

        self.ring_freq_var = self._add_slider(c1, "Frequência Portadora", 5.0, 400.0, 60.0, "Hz", step=1.0)
        self.ring_mix_var = self._add_slider(c1, "Mistura (Mix)", 0.0, 100.0, 70.0, "%", step=1.0)

        # Distorção & Bitcrusher
        c2 = ctk.CTkFrame(scroll, fg_color="#0f172a", corner_radius=10)
        c2.pack(fill="x", padx=10, pady=8)
        self.dist_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            c2,
            text="Distorção & Bitcrusher (Rádio / Mega-fone / Lo-Fi)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.dist_en_var,
            command=self._on_param_change,
        ).pack(anchor="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(
            c2,
            text="Adiciona saturação analógica, redução de bits (8-bit/rádio) e redução de taxa de amostragem.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        self.dist_drive_var = self._add_slider(c2, "Drive / Saturação", 1.0, 25.0, 3.0, "x", step=0.2)
        self.dist_bits_var = self._add_slider(c2, "Resolução (Bits)", 4.0, 16.0, 16.0, "bits", step=1.0)
        self.dist_down_var = self._add_slider(c2, "Downsample (Lo-Fi)", 1.0, 16.0, 1.0, "x", step=1.0)
        self.dist_mix_var = self._add_slider(c2, "Mistura (Mix)", 0.0, 100.0, 70.0, "%", step=1.0)

    def _build_space_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Eco / Delay
        c1 = ctk.CTkFrame(scroll, fg_color="#0f172a", corner_radius=10)
        c1.pack(fill="x", padx=10, pady=8)
        self.echo_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            c1,
            text="Eco / Delay (estilo 'Eco' do Audacity)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.echo_en_var,
            command=self._on_param_change,
        ).pack(anchor="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(
            c1,
            text="Dica: Use atrasos curtos (10–25 ms) com feedback alto para som de Capacete/Tubo metálico, ou 250–500 ms para Eco de Caverna.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        self.echo_delay_var = self._add_slider(c1, "Tempo de Atraso", 10.0, 700.0, 220.0, "ms", step=2.0)
        self.echo_fb_var = self._add_slider(c1, "Repetições (Feedback)", 0.0, 85.0, 35.0, "%", step=1.0)
        self.echo_mix_var = self._add_slider(c1, "Volume do Eco", 0.0, 100.0, 35.0, "%", step=1.0)

        # Reverb
        c2 = ctk.CTkFrame(scroll, fg_color="#0f172a", corner_radius=10)
        c2.pack(fill="x", padx=10, pady=8)
        self.rev_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            c2,
            text="Reverberação (Reverb de Sala / Catedral)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.rev_en_var,
            command=self._on_param_change,
        ).pack(anchor="w", padx=14, pady=(10, 2))
        self.rev_room_var = self._add_slider(c2, "Tamanho da Sala", 0.0, 100.0, 60.0, "%", step=1.0)
        self.rev_damp_var = self._add_slider(c2, "Abafamento (Damping)", 5.0, 92.0, 45.0, "%", step=1.0)
        self.rev_mix_var = self._add_slider(c2, "Mistura do Reverb", 0.0, 100.0, 30.0, "%", step=1.0)

    def _build_mixer_tab(self, tab):
        box = ctk.CTkFrame(tab, fg_color="#0f172a", corner_radius=10)
        box.pack(fill="both", expand=True, padx=10, pady=8)

        ctk.CTkLabel(
            box,
            text="Visão Rápida da Cadeia de Efeitos (Ligue/Desligue módulos instantaneamente)",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 10))

        modules = [
            ("Noise Gate (Corte de ruído)", self.gate_en_var),
            ("Compressor de Voz", self.comp_en_var),
            ("Alterar Tom (Pitch Shifter)", self.pitch_en_var),
            ("Frequency Shifter (Hz)", self.fshift_en_var),
            ("Equalizador (EQ 5 Bandas + Cortes)", self.eq_en_var),
            ("Modulador em Anel (Robô)", self.ring_en_var),
            ("Distorção & Bitcrusher (Rádio/Lo-Fi)", self.dist_en_var),
            ("Eco / Delay", self.echo_en_var),
            ("Reverberação (Reverb)", self.rev_en_var),
        ]

        grid = ctk.CTkFrame(box, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=6)
        for idx, (label, var) in enumerate(modules):
            card = ctk.CTkFrame(grid, fg_color="#161f33", corner_radius=8)
            card.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=6, pady=6)
            grid.columnconfigure(0, weight=1)
            grid.columnconfigure(1, weight=1)
            ctk.CTkSwitch(
                card, text=label, variable=var, font=ctk.CTkFont(size=13), command=self._on_param_change
            ).pack(anchor="w", padx=14, pady=12)

        ctk.CTkButton(
            box,
            text="Resetar Todos os Efeitos (Voz Limpa)",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=36,
            command=lambda: self._apply_preset("Normal (Limpo + Gate)"),
        ).pack(pady=18)

    # ------------------------------------------------------------------ #
    # Helpers de Widgets
    # ------------------------------------------------------------------ #
    def _add_slider(self, parent, label: str, vmin: float, vmax: float, default: float, unit: str, step: float = 0.5):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=12, pady=3)

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=label, font=ctk.CTkFont(size=12)).pack(side="left")
        val_lbl = ctk.CTkLabel(top, text=f"{default:.1f} {unit}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8")
        val_lbl.pack(side="right")

        var = ctk.DoubleVar(value=default)
        steps = max(1, int(round((vmax - vmin) / step)))

        def on_slide(v):
            if unit in ("Hz", "ms", "%", "bits", "x", "ct") and step >= 1.0:
                val_lbl.configure(text=f"{int(round(float(v)))} {unit}")
            else:
                val_lbl.configure(text=f"{float(v):.1f} {unit}")
            self._on_param_change()

        slider = ctk.CTkSlider(frame, from_=vmin, to=vmax, number_of_steps=steps, variable=var, command=on_slide)
        slider.pack(fill="x", pady=(1, 3))
        # Armazena callback para atualizar o label quando carregar um preset
        var._val_lbl = val_lbl
        var._unit = unit
        var._step = step
        return var

    def _add_vertical_eq_band(self, parent, title: str):
        col = ctk.CTkFrame(parent, fg_color="#161f33", corner_radius=8)
        col.pack(side="left", fill="both", expand=True, padx=4)

        val_lbl = ctk.CTkLabel(col, text="0.0 dB", font=ctk.CTkFont(size=11, weight="bold"), text_color="#38bdf8")
        val_lbl.pack(pady=(8, 2))

        var = ctk.DoubleVar(value=0.0)

        def on_slide(v):
            val_lbl.configure(text=f"{float(v):+.1f} dB")
            self._on_param_change()

        slider = ctk.CTkSlider(
            col,
            from_=-18.0,
            to=18.0,
            number_of_steps=72,
            orientation="vertical",
            height=150,
            variable=var,
            command=on_slide,
        )
        slider.pack(pady=4)

        ctk.CTkLabel(col, text=title, font=ctk.CTkFont(size=11), justify="center").pack(pady=(2, 8))
        var._val_lbl = val_lbl
        var._unit = "dB"
        var._step = 0.5
        return var

    def _refresh_slider_label(self, var: ctk.DoubleVar):
        lbl = getattr(var, "_val_lbl", None)
        if lbl is None:
            return
        v = float(var.get())
        unit = var._unit
        step = var._step
        if unit == "dB" and lbl.cget("text").startswith(("+", "-")):
            lbl.configure(text=f"{v:+.1f} dB")
        elif unit in ("Hz", "ms", "%", "bits", "x", "ct") and step >= 1.0:
            lbl.configure(text=f"{int(round(v))} {unit}")
        else:
            lbl.configure(text=f"{v:.1f} {unit}")

    # ------------------------------------------------------------------ #
    # Sincronização UI <-> DSP
    # ------------------------------------------------------------------ #
    def _on_param_change(self, *_):
        if self._syncing_ui:
            return
        p = DSPParams(
            bypass=bool(self.bypass_var.get()),
            input_gain_db=float(self.input_gain_var.get()),
            output_gain_db=float(self.output_gain_var.get()),
            gate_enabled=bool(self.gate_en_var.get()),
            gate_threshold_db=float(self.gate_thresh_var.get()),
            comp_enabled=bool(self.comp_en_var.get()),
            comp_threshold_db=float(self.comp_thresh_var.get()),
            pitch_enabled=bool(self.pitch_en_var.get()),
            pitch_semitones=float(self.pitch_st_var.get()),
            pitch_cents=float(self.pitch_cents_var.get()),
            pitch_mix=float(self.pitch_mix_var.get()) / 100.0,
            freq_shift_enabled=bool(self.fshift_en_var.get()),
            freq_shift_hz=float(self.fshift_hz_var.get()),
            freq_shift_mix=float(self.fshift_mix_var.get()) / 100.0,
            eq_enabled=bool(self.eq_en_var.get()),
            eq_hpf_enabled=bool(self.hpf_en_var.get()),
            eq_hpf_hz=float(self.hpf_hz_var.get()),
            eq_lpf_enabled=bool(self.lpf_en_var.get()),
            eq_lpf_hz=float(self.lpf_hz_var.get()),
            eq_band1_db=float(self.eq_b1_var.get()),
            eq_band2_db=float(self.eq_b2_var.get()),
            eq_band3_db=float(self.eq_b3_var.get()),
            eq_band4_db=float(self.eq_b4_var.get()),
            eq_band5_db=float(self.eq_b5_var.get()),
            ring_enabled=bool(self.ring_en_var.get()),
            ring_freq_hz=float(self.ring_freq_var.get()),
            ring_waveform=str(self.ring_wave_var.get()),
            ring_mix=float(self.ring_mix_var.get()) / 100.0,
            dist_enabled=bool(self.dist_en_var.get()),
            dist_drive=float(self.dist_drive_var.get()),
            dist_bits=int(round(self.dist_bits_var.get())),
            dist_downsample=int(round(self.dist_down_var.get())),
            dist_mix=float(self.dist_mix_var.get()) / 100.0,
            echo_enabled=bool(self.echo_en_var.get()),
            echo_delay_ms=float(self.echo_delay_var.get()),
            echo_feedback=float(self.echo_fb_var.get()) / 100.0,
            echo_mix=float(self.echo_mix_var.get()) / 100.0,
            reverb_enabled=bool(self.rev_en_var.get()),
            reverb_room=float(self.rev_room_var.get()) / 100.0,
            reverb_damp=float(self.rev_damp_var.get()) / 100.0,
            reverb_mix=float(self.rev_mix_var.get()) / 100.0,
        )
        self.params = p
        self.dsp.update_params(p)
        self._draw_eq_curve()

    def _load_params_to_ui(self, p: DSPParams):
        self._syncing_ui = True
        try:
            self.bypass_var.set(p.bypass)
            self.input_gain_var.set(p.input_gain_db)
            self.output_gain_var.set(p.output_gain_db)
            self.gate_en_var.set(p.gate_enabled)
            self.gate_thresh_var.set(p.gate_threshold_db)
            self.comp_en_var.set(p.comp_enabled)
            self.comp_thresh_var.set(p.comp_threshold_db)

            self.pitch_en_var.set(p.pitch_enabled)
            self.pitch_st_var.set(p.pitch_semitones)
            self.pitch_cents_var.set(p.pitch_cents)
            self.pitch_mix_var.set(p.pitch_mix * 100.0)

            self.fshift_en_var.set(p.freq_shift_enabled)
            self.fshift_hz_var.set(p.freq_shift_hz)
            self.fshift_mix_var.set(p.freq_shift_mix * 100.0)

            self.eq_en_var.set(p.eq_enabled)
            self.hpf_en_var.set(p.eq_hpf_enabled)
            self.hpf_hz_var.set(p.eq_hpf_hz)
            self.lpf_en_var.set(p.eq_lpf_enabled)
            self.lpf_hz_var.set(p.eq_lpf_hz)
            self.eq_b1_var.set(p.eq_band1_db)
            self.eq_b2_var.set(p.eq_band2_db)
            self.eq_b3_var.set(p.eq_band3_db)
            self.eq_b4_var.set(p.eq_band4_db)
            self.eq_b5_var.set(p.eq_band5_db)

            self.ring_en_var.set(p.ring_enabled)
            self.ring_freq_var.set(p.ring_freq_hz)
            self.ring_wave_var.set(p.ring_waveform)
            self.ring_mix_var.set(p.ring_mix * 100.0)

            self.dist_en_var.set(p.dist_enabled)
            self.dist_drive_var.set(p.dist_drive)
            self.dist_bits_var.set(p.dist_bits)
            self.dist_down_var.set(p.dist_downsample)
            self.dist_mix_var.set(p.dist_mix * 100.0)

            self.echo_en_var.set(p.echo_enabled)
            self.echo_delay_var.set(p.echo_delay_ms)
            self.echo_fb_var.set(p.echo_feedback * 100.0)
            self.echo_mix_var.set(p.echo_mix * 100.0)

            self.rev_en_var.set(p.reverb_enabled)
            self.rev_room_var.set(p.reverb_room * 100.0)
            self.rev_damp_var.set(p.reverb_damp * 100.0)
            self.rev_mix_var.set(p.reverb_mix * 100.0)

            for v in (
                self.input_gain_var, self.output_gain_var, self.gate_thresh_var, self.comp_thresh_var,
                self.pitch_st_var, self.pitch_cents_var, self.pitch_mix_var,
                self.fshift_hz_var, self.fshift_mix_var,
                self.hpf_hz_var, self.lpf_hz_var,
                self.eq_b1_var, self.eq_b2_var, self.eq_b3_var, self.eq_b4_var, self.eq_b5_var,
                self.ring_freq_var, self.ring_mix_var,
                self.dist_drive_var, self.dist_bits_var, self.dist_down_var, self.dist_mix_var,
                self.echo_delay_var, self.echo_fb_var, self.echo_mix_var,
                self.rev_room_var, self.rev_damp_var, self.rev_mix_var,
            ):
                self._refresh_slider_label(v)
        finally:
            self._syncing_ui = False

        self._on_param_change()

    # ------------------------------------------------------------------ #
    # Atalhos & Presets
    # ------------------------------------------------------------------ #
    def _quick_pitch(self, semitones: float):
        self.pitch_en_var.set(abs(semitones) > 0.01)
        self.pitch_st_var.set(semitones)
        self.pitch_cents_var.set(0.0)
        self._refresh_slider_label(self.pitch_st_var)
        self._refresh_slider_label(self.pitch_cents_var)
        self._on_param_change()

    def _quick_fshift(self, hz: float):
        self.fshift_en_var.set(abs(hz) > 0.5)
        self.fshift_hz_var.set(hz)
        self._refresh_slider_label(self.fshift_hz_var)
        self._on_param_change()

    def _reset_eq(self):
        for v in (self.eq_b1_var, self.eq_b2_var, self.eq_b3_var, self.eq_b4_var, self.eq_b5_var):
            v.set(0.0)
            self._refresh_slider_label(v)
        self.hpf_en_var.set(True)
        self.hpf_hz_var.set(80.0)
        self.lpf_en_var.set(False)
        self.lpf_hz_var.set(12000.0)
        self._refresh_slider_label(self.hpf_hz_var)
        self._refresh_slider_label(self.lpf_hz_var)
        self._on_param_change()

    def _all_preset_names(self) -> list[str]:
        names = list(self.builtin_presets.keys())
        for u in self.user_presets.keys():
            names.append(f"★ {u}")
        return names

    def _on_preset_selected(self, choice: str):
        clean = choice[2:] if choice.startswith("★ ") else choice
        self._apply_preset(clean)

    def _apply_preset(self, name: str):
        if name in self.builtin_presets:
            self._load_params_to_ui(self.builtin_presets[name].copy())
        elif name in self.user_presets:
            self._load_params_to_ui(self.user_presets[name].copy())

    def _save_custom_preset(self):
        name = simpledialog.askstring("Salvar Voz Personalizada", "Digite um nome para esta voz:", parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        self.user_presets[name] = self.params.copy()
        save_user_presets(self.user_presets)
        self.preset_menu.configure(values=self._all_preset_names())
        self.preset_var.set(f"★ {name}")

    def _delete_custom_preset(self):
        sel = self.preset_var.get()
        if not sel.startswith("★ "):
            messagebox.showinfo("Aviso", "Apenas vozes personalizadas (marcadas com ★) podem ser excluídas.")
            return
        name = sel[2:]
        if name in self.user_presets:
            del self.user_presets[name]
            save_user_presets(self.user_presets)
            self.preset_menu.configure(values=self._all_preset_names())
            self.preset_var.set("Normal (Limpo + Gate)")
            self._apply_preset("Normal (Limpo + Gate)")

    # ------------------------------------------------------------------ #
    # Dispositivos e Motor de Áudio
    # ------------------------------------------------------------------ #
    def _refresh_devices(self):
        self.in_devices, self.out_devices = AudioRouter.list_devices()
        in_labels = [d.label for d in self.in_devices] or ["Nenhum microfone encontrado"]
        out_labels = [d.label for d in self.out_devices] or ["Nenhuma saída encontrada"]

        self.in_dev_menu.configure(values=in_labels)
        self.out_dev_menu.configure(values=out_labels)
        self.mon_dev_menu.configure(values=out_labels)

        if in_labels and self.in_dev_var.get() not in in_labels:
            self.in_dev_var.set(in_labels[0])

        # Tenta selecionar VB-Cable automaticamente como Saída se existir
        if out_labels and self.out_dev_var.get() not in out_labels:
            vb = next((lbl for lbl in out_labels if "CABLE Input" in lbl or "VB-Audio" in lbl), out_labels[0])
            self.out_dev_var.set(vb)

        if out_labels and self.mon_dev_var.get() not in out_labels:
            non_vb = next((lbl for lbl in out_labels if "CABLE" not in lbl), out_labels[0])
            self.mon_dev_var.set(non_vb)

    def _selected_device_index(self, label: str, items: list[AudioDeviceItem]) -> int | None:
        for d in items:
            if d.label == label:
                return d.index
        return None

    def _get_blocksize(self) -> int:
        txt = self.latency_var.get()
        if "256" in txt:
            return 256
        if "1024" in txt:
            return 1024
        return 512

    def _toggle_audio(self):
        if self.router.running:
            self.router.stop()
            self.power_btn.configure(text="INICIAR ÁUDIO", fg_color="#10b981", hover_color="#059669")
            self.status_lbl.configure(text="Status: Parado", text_color="#94a3b8")
        else:
            self._start_audio()

    def _start_audio(self):
        in_idx = self._selected_device_index(self.in_dev_var.get(), self.in_devices)
        out_idx = self._selected_device_index(self.out_dev_var.get(), self.out_devices)
        mon_idx = self._selected_device_index(self.mon_dev_var.get(), self.out_devices)

        if in_idx is None or out_idx is None:
            messagebox.showerror("Erro", "Selecione dispositivos válidos de Entrada e Saída.")
            return

        ok, msg = self.router.start(
            in_idx=in_idx,
            out_idx=out_idx,
            blocksize=self._get_blocksize(),
            monitor_enabled=bool(self.monitor_var.get()),
            monitor_idx=mon_idx,
        )
        if ok:
            self.power_btn.configure(text="PARAR ÁUDIO", fg_color="#ef4444", hover_color="#dc2626")
            self.status_lbl.configure(text=msg, text_color="#10b981")
            self._draw_eq_curve()
        else:
            messagebox.showerror("Erro de Áudio", msg)
            self.status_lbl.configure(text=msg, text_color="#ef4444")

    def _restart_if_running(self):
        if self.router.running:
            self._start_audio()

    # ------------------------------------------------------------------ #
    # Gráficos em Tempo Real (Curva EQ & Osciloscópio)
    # ------------------------------------------------------------------ #
    def _draw_eq_curve(self):
        c = self.eq_canvas
        w = max(400, c.winfo_width())
        h = max(160, c.winfo_height())
        c.delete("all")

        pad_x, pad_y = 36, 16
        gw = w - 2 * pad_x
        gh = h - 2 * pad_y

        # Grade de dB (+18, +9, 0, -9, -18)
        for db in (-18, -9, 0, 9, 18):
            y = pad_y + (18.0 - db) / 36.0 * gh
            color = "#334155" if db == 0 else "#162032"
            c.create_line(pad_x, y, w - pad_x, y, fill=color, dash=(3, 3) if db != 0 else ())
            c.create_text(pad_x - 6, y, text=f"{db:+d}", fill="#64748b", font=("Segoe UI", 8), anchor="e")

        # Grade logarítmica de frequências (20 Hz -> 20 kHz)
        f_min, f_max = 20.0, 20000.0
        for f in (30, 60, 120, 250, 500, 1000, 2000, 4000, 8000, 16000):
            x = pad_x + (np.log10(f / f_min) / np.log10(f_max / f_min)) * gw
            c.create_line(x, pad_y, x, h - pad_y, fill="#162032")
            lbl = f"{f // 1000}k" if f >= 1000 else str(f)
            c.create_text(x, h - 5, text=lbl, fill="#64748b", font=("Segoe UI", 8))

        if not self.params.eq_enabled:
            y0 = pad_y + 0.5 * gh
            c.create_line(pad_x, y0, w - pad_x, y0, fill="#475569", width=2)
            c.create_text(w / 2, y0 - 14, text="EQ Desativado (Flat)", fill="#64748b", font=("Segoe UI", 10))
            return

        sr = self.dsp.sr
        sos = build_eq_sos(self.params, sr)
        freqs = np.logspace(np.log10(f_min), np.log10(min(f_max, sr * 0.48)), 220)
        _, resp = signal.sosfreqz(sos, worN=freqs, fs=sr)
        db_resp = 20.0 * np.log10(np.maximum(np.abs(resp), 1e-5))
        db_resp = np.clip(db_resp, -20.0, 20.0)

        pts = []
        for f, db in zip(freqs, db_resp):
            x = pad_x + (np.log10(f / f_min) / np.log10(f_max / f_min)) * gw
            y = pad_y + (18.0 - db) / 36.0 * gh
            y = np.clip(y, pad_y, h - pad_y)
            pts.extend([float(x), float(y)])

        if len(pts) >= 4:
            c.create_line(*pts, fill="#38bdf8", width=2.5, smooth=True)

    def _schedule_ui_loop(self):
        # Atualiza VU meters e forma de onda ~30 FPS
        in_norm = max(0.0, min(1.0, (self.dsp.input_peak_db + 60.0) / 60.0))
        out_norm = max(0.0, min(1.0, (self.dsp.output_peak_db + 60.0) / 60.0))
        self.in_bar.set(in_norm)
        self.out_bar.set(out_norm)

        if self.dsp.gate_is_open:
            self.gate_led.configure(text="● Noise Gate: Aberto", text_color="#10b981")
        else:
            self.gate_led.configure(text="● Noise Gate: Silenciado", text_color="#f59e0b")

        # Desenha Osciloscópio
        wc = self.wave_canvas
        ww = max(200, wc.winfo_width())
        wh = max(50, wc.winfo_height())
        wc.delete("all")
        mid = wh / 2.0
        wc.create_line(0, mid, ww, mid, fill="#1e293b")

        wave = self.dsp.last_waveform
        if self.router.running and len(wave) > 1:
            xs = np.linspace(0, ww, len(wave))
            ys = mid - np.clip(wave, -1.0, 1.0) * (mid - 4)
            pts = []
            for xv, yv in zip(xs, ys):
                pts.extend([float(xv), float(yv)])
            color = "#f59e0b" if self.params.bypass else "#4cc9f0"
            wc.create_line(*pts, fill=color, width=1.6)

        self.after(33, self._schedule_ui_loop)

    # ------------------------------------------------------------------ #
    # Guia Discord & Fechamento
    # ------------------------------------------------------------------ #
    def _open_discord_guide(self):
        win = ctk.CTkToplevel(self)
        win.title("Como usar no Discord, Valorant, CS2, OBS e Jogos")
        win.geometry("560x420")
        win.grab_set()

        txt = (
            "Para enviar a sua voz modificada para o Discord e qualquer jogo, você precisa de um "
            "cabo de áudio virtual (gratuito):\n\n"
            "1. Instale o VB-Audio Virtual Cable (VB-Cable):\n"
            "   • Baixe em: vb-audio.com/Cable (Windows/macOS) e reinicie se solicitado.\n"
            "   • No Linux, use PipeWire/PulseAudio virtual sink.\n\n"
            "2. Configure aqui no VoxCraft Studio:\n"
            "   • Microfone (Entrada): Escolha o seu microfone físico.\n"
            "   • Saída: Escolha 'CABLE Input (VB-Audio Virtual Cable)'.\n"
            "   • Marque 'Ouvir minha voz' apenas enquanto estiver testando nos seus fones!\n"
            "   • Clique em INICIAR ÁUDIO.\n\n"
            "3. Configure no Discord / Jogos:\n"
            "   • No Discord: Configurações > Voz e Vídeo > Dispositivo de Entrada:\n"
            "     Selecione 'CABLE Output (VB-Audio Virtual Cable)'.\n"
            "   • Dica Discord: Desative o 'Supressão de Ruído Krisp' do Discord se ele\n"
            "     estiver cortando efeitos como Robô, Eco ou Voz Grave."
        )
        ctk.CTkLabel(
            win, text="Roteamento para Discord e Jogos", font=ctk.CTkFont(size=17, weight="bold"), text_color="#4cc9f0"
        ).pack(anchor="w", padx=20, pady=(16, 8))
        ctk.CTkLabel(win, text=txt, justify="left", font=ctk.CTkFont(size=12.5), wraplength=520).pack(
            anchor="w", padx=20, pady=4
        )
        ctk.CTkButton(win, text="Entendi!", width=120, command=win.destroy).pack(pady=14)

    def _on_close(self):
        self.router.stop()
        self.destroy()


if __name__ == "__main__":
    app = VoxCraftApp()
    app.mainloop()