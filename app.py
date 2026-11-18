import ctypes
from dataclasses import asdict
import io
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog
import urllib.request
import zipfile
import customtkinter as ctk
import numpy as np
from scipy import signal

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    Image = None
    ImageDraw = None
    ImageTk = None

try:
    import pystray
except ImportError:
    pystray = None

from dsp_engine import DSPParams, RealTimeDSPEngine, build_eq_sos
from presets import (
    get_builtin_presets,
    load_app_config,
    load_user_presets,
    save_app_config,
    save_user_presets,
)
from audio_router import AudioDeviceItem, AudioRouter

GITHUB_REPO = "CakeSweet/voxcraft_studio"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_ICO_PATH = os.path.join(BASE_DIR, "assets", "voxcraft.ico")
ICON_PNG_PATH = os.path.join(BASE_DIR, "assets", "voxcraft.png")


def _enable_windows_taskbar_icon_id():
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CakeSweet.VoxCraftStudio.1")
        except Exception:
            pass


def _load_or_create_pil_icon():
    if Image is None:
        return None
    if os.path.exists(ICON_PNG_PATH):
        try:
            return Image.open(ICON_PNG_PATH).convert("RGBA")
        except Exception:
            pass
    # Fallback programático caso assets/voxcraft.png não exista
    img = Image.new("RGBA", (128, 128), (15, 23, 42, 255))
    if ImageDraw is not None:
        draw = ImageDraw.Draw(img)
        draw.ellipse((10, 10, 118, 118), outline=(76, 201, 240, 255), width=6)
        draw.rounded_rectangle((50, 30, 78, 74), radius=14, outline=(76, 201, 240, 255), width=5)
        draw.arc((40, 48, 88, 90), start=0, end=180, fill=(37, 99, 235, 255), width=5)
        draw.line((64, 90, 64, 106), fill=(76, 201, 240, 255), width=5)
    return img


class VoxCraftApp(ctk.CTk):
    def __init__(self):
        _enable_windows_taskbar_icon_id()
        super().__init__()
        self.title("VoxCraft Studio — Modulador de Voz em Tempo Real (Estilo Audacity)")
        self.geometry("1220x780")
        self.minsize(1060, 680)

        self._window_icon_photo = None
        self._tray_icon = None
        self._tray_thread = None
        self._is_quitting = False

        self._apply_window_icon()

        self.dsp = RealTimeDSPEngine(48000.0)
        self.router = AudioRouter(self.dsp)
        self.params = DSPParams()

        self.builtin_presets = get_builtin_presets()
        self.user_presets = load_user_presets()
        self.app_config = load_app_config()

        self.in_devices: list[AudioDeviceItem] = []
        self.out_devices: list[AudioDeviceItem] = []
        self._syncing_ui = False

        self._build_layout()
        self._restore_saved_ui_prefs()
        self._refresh_devices(reinit_backend=False, initial_load=True)

        saved_preset = self.app_config.get("last_preset", "Normal (Limpo + Gate)")
        if saved_preset in self.builtin_presets:
            self.preset_var.set(saved_preset)
            self._apply_preset(saved_preset, save_cfg=False)
        elif saved_preset in self.user_presets:
            self.preset_var.set(f"★ {saved_preset}")
            self._apply_preset(saved_preset, save_cfg=False)
        else:
            self.preset_var.set("Normal (Limpo + Gate)")
            self._apply_preset("Normal (Limpo + Gate)", save_cfg=False)

        if self.app_config.pop("pending_update_restore", False):
            raw_params = self.app_config.pop("current_params", None)
            was_running_upd = bool(self.app_config.pop("was_running_before_update", False))
            if isinstance(raw_params, dict):
                valid_fields = set(asdict(DSPParams()).keys())
                filtered = {k: v for k, v in raw_params.items() if k in valid_fields}
                try:
                    self._load_params_to_ui(DSPParams(**filtered))
                except Exception:
                    pass
            self._save_config()
            self.status_lbl.configure(
                text="Aplicação atualizada! Entradas, saídas e ajustes restaurados.",
                text_color="#10b981",
            )
            if was_running_upd:
                self.after(450, self._start_audio)

        self._start_tray_icon()
        self._schedule_ui_loop()
        self.after(250, self._apply_window_icon)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_window_icon(self):
        if sys.platform == "win32" and os.path.exists(ICON_ICO_PATH):
            try:
                self.iconbitmap(default=ICON_ICO_PATH)
            except Exception:
                pass
        pil_img = _load_or_create_pil_icon()
        if pil_img is not None and ImageTk is not None:
            try:
                self._window_icon_photo = ImageTk.PhotoImage(pil_img)
                self.iconphoto(True, self._window_icon_photo)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Bandeja do Sistema (System Tray) e Barra de Tarefas
    # ------------------------------------------------------------------ #
    def _start_tray_icon(self):
        if pystray is None:
            return
        pil_img = _load_or_create_pil_icon()
        if pil_img is None:
            return

        def on_show(icon, item):
            self.after(0, self._restore_from_tray)

        def on_toggle_audio(icon, item):
            self.after(0, self._toggle_audio)

        def on_toggle_bypass(icon, item):
            def _flip():
                self.bypass_var.set(not self.bypass_var.get())
                self._on_param_change()
            self.after(0, _flip)

        def on_quit(icon, item):
            self.after(0, self._quit_app)

        menu = pystray.Menu(
            pystray.MenuItem("Abrir VoxCraft Studio", on_show, default=True),
            pystray.MenuItem(
                lambda item: "Parar Áudio" if self.router.running else "Iniciar Áudio",
                on_toggle_audio,
            ),
            pystray.MenuItem(
                "Voz Original (Bypass)",
                on_toggle_bypass,
                checked=lambda item: bool(self.bypass_var.get()),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", on_quit),
        )

        self._tray_icon = pystray.Icon("voxcraft_studio", pil_img, "VoxCraft Studio", menu)
        self._tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
        self._tray_thread.start()

    def _restore_from_tray(self):
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def _minimize_to_tray(self):
        self.withdraw()
        if self._tray_icon is not None:
            try:
                self._tray_icon.notify(
                    "VoxCraft Studio continua rodando em segundo plano.",
                    "VoxCraft Studio",
                )
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Construção da Interface
    # ------------------------------------------------------------------ #
    def _build_layout(self):
        # Barra Superior
        topbar = ctk.CTkFrame(self, height=64, corner_radius=10, fg_color="#161b24")
        topbar.pack(fill="x", padx=12, pady=(10, 6))
        topbar.pack_propagate(False)

        title_box = ctk.CTkFrame(topbar, fg_color="transparent")
        title_box.pack(side="left", padx=(12, 8))
        ctk.CTkLabel(
            title_box, text="VoxCraft Studio", font=ctk.CTkFont(size=20, weight="bold"), text_color="#4cc9f0"
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_box,
            text="Modulador estilo Audacity em tempo real",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w")

        # Controles de Preset no Topo
        preset_box = ctk.CTkFrame(topbar, fg_color="transparent")
        preset_box.pack(side="left", padx=8)
        ctk.CTkLabel(preset_box, text="Voz / Preset:", font=ctk.CTkFont(size=12, weight="bold")).pack(
            side="left", padx=(0, 6)
        )
        self.preset_var = ctk.StringVar(value="Normal (Limpo + Gate)")
        self.preset_menu = ctk.CTkOptionMenu(
            preset_box,
            variable=self.preset_var,
            values=self._all_preset_names(),
            width=195,
            command=self._on_preset_selected,
        )
        self.preset_menu.pack(side="left", padx=3)

        ctk.CTkButton(
            preset_box, text="Salvar Voz", width=82, fg_color="#2563eb", command=self._save_custom_preset
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            preset_box, text="Excluir", width=58, fg_color="#475569", hover_color="#dc2626",
            command=self._delete_custom_preset
        ).pack(side="left", padx=3)

        # Botões da Direita (Atualizar App, Guia, Bypass, Ligar)
        right_top = ctk.CTkFrame(topbar, fg_color="transparent")
        right_top.pack(side="right", padx=8)

        self.update_btn = ctk.CTkButton(
            right_top,
            text="Atualizar App",
            width=106,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._start_app_update,
        )
        self.update_btn.pack(side="left", padx=4)

        ctk.CTkButton(
            right_top, text="Guia Discord", width=102, fg_color="#334155",
            hover_color="#475569", command=self._open_discord_guide
        ).pack(side="left", padx=4)

        self.bypass_var = ctk.BooleanVar(value=False)
        self.bypass_btn = ctk.CTkSwitch(
            right_top,
            text="Voz Original",
            variable=self.bypass_var,
            progress_color="#f59e0b",
            command=self._on_param_change,
        )
        self.bypass_btn.pack(side="left", padx=6)

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
        self.in_dev_menu = ctk.CTkOptionMenu(
            side, variable=self.in_dev_var, values=[""], width=285, command=self._on_device_changed
        )
        self.in_dev_menu.pack(padx=10, pady=(2, 8))

        # Saída
        ctk.CTkLabel(side, text="Saída (VB-Cable p/ Discord ou Fone):", font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=10
        )
        self.out_dev_var = ctk.StringVar()
        self.out_dev_menu = ctk.CTkOptionMenu(
            side, variable=self.out_dev_var, values=[""], width=285, command=self._on_device_changed
        )
        self.out_dev_menu.pack(padx=10, pady=(2, 8))

        # Monitoramento (Ouvir a própria voz)
        self.monitor_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            side, text="Ouvir minha voz (Monitor no Fone)", variable=self.monitor_var, command=self._on_routing_pref_changed
        ).pack(anchor="w", padx=10, pady=(4, 4))
        self.mon_dev_var = ctk.StringVar()
        self.mon_dev_menu = ctk.CTkOptionMenu(
            side, variable=self.mon_dev_var, values=[""], width=285, command=self._on_device_changed
        )
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
            command=lambda _: self._on_routing_pref_changed(),
        ).pack(side="right")

        # Comportamento ao Fechar (Bandeja / Tray)
        self.minimize_to_tray_var = ctk.BooleanVar(value=pystray is not None)
        ctk.CTkSwitch(
            side,
            text="Ao fechar (X): Minimizar na Bandeja",
            variable=self.minimize_to_tray_var,
            command=self._save_config,
        ).pack(anchor="w", padx=10, pady=(2, 6))

        ctk.CTkButton(
            side,
            text="Atualizar Dispositivos",
            height=28,
            fg_color="#334155",
            command=lambda: self._refresh_devices(reinit_backend=True),
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

        t_pitch = self.tabs.add("1. Tom & Vocoder")
        t_eq = self.tabs.add("2. Equalizador")
        t_mod = self.tabs.add("3. Modulação (Audacity)")
        t_fx = self.tabs.add("4. Robô & Distorção")
        t_space = self.tabs.add("5. Eco & Reverb")
        t_mixer = self.tabs.add("6. Mixer Rápido")

        self._build_pitch_tab(t_pitch)
        self._build_eq_tab(t_eq)
        self._build_mod_tab(t_mod)
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

        # Card: Vocoder (estilo Audacity)
        card3 = ctk.CTkFrame(scroll, fg_color="#0f172a", corner_radius=10)
        card3.pack(fill="x", padx=10, pady=8)

        hdr3 = ctk.CTkFrame(card3, fg_color="transparent")
        hdr3.pack(fill="x", padx=14, pady=(10, 4))
        self.voc_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            hdr3,
            text="Vocoder (estilo 'Vocoder' do Audacity — 12 Bandas)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.voc_en_var,
            command=self._on_param_change,
        ).pack(side="left")

        ctk.CTkLabel(
            card3,
            text="Transforma a sua fala modulando uma onda sintetizada ou ruído de sussurro em 12 faixas de frequência (Daft Punk / Fantasma).",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        voc_row = ctk.CTkFrame(card3, fg_color="transparent")
        voc_row.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(voc_row, text="Portadora (Carrier):", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        self.voc_carrier_var = ctk.StringVar(value="Dente de Serra")
        ctk.CTkOptionMenu(
            voc_row,
            variable=self.voc_carrier_var,
            values=["Dente de Serra", "Acorde", "Quadrada", "Sussurro (Ruído)"],
            command=lambda _: self._on_param_change(),
        ).pack(side="left")

        self.voc_freq_var = self._add_slider(card3, "Nota / Frequência Base", 55.0, 300.0, 110.0, "Hz", step=1.0)
        self.voc_smooth_var = self._add_slider(card3, "Suavidade do Envelope", 10.0, 95.0, 45.0, "%", step=1.0)
        self.voc_mix_var = self._add_slider(card3, "Mistura (Dry / Wet)", 0.0, 100.0, 85.0, "%", step=1.0)

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

    def _build_mod_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Phaser (estilo Audacity)
        c1 = ctk.CTkFrame(scroll, fg_color="#0f172a", corner_radius=10)
        c1.pack(fill="x", padx=10, pady=8)
        self.phaser_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            c1,
            text="Phaser (estilo 'Phaser' do Audacity)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.phaser_en_var,
            command=self._on_param_change,
        ).pack(anchor="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(
            c1,
            text="Cria varreduras espaciais e futuristas de fase (efeito nave espacial / sci-fi).",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=14, pady=(0, 8))
        self.phaser_stages_var = self._add_slider(c1, "Estágios (Stages)", 2.0, 12.0, 6.0, "x", step=2.0)
        self.phaser_freq_var = self._add_slider(c1, "Velocidade LFO", 0.1, 6.0, 0.8, "Hz", step=0.1)
        self.phaser_depth_var = self._add_slider(c1, "Profundidade (Depth)", 0.0, 100.0, 70.0, "%", step=1.0)
        self.phaser_fb_var = self._add_slider(c1, "Feedback", -90.0, 90.0, 45.0, "%", step=1.0)
        self.phaser_mix_var = self._add_slider(c1, "Mistura (Mix)", 0.0, 100.0, 60.0, "%", step=1.0)

        # Wahwah (estilo Audacity)
        c2 = ctk.CTkFrame(scroll, fg_color="#0f172a", corner_radius=10)
        c2.pack(fill="x", padx=10, pady=8)
        self.wah_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            c2,
            text="Wahwah (estilo 'Wahwah' do Audacity)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.wah_en_var,
            command=self._on_param_change,
        ).pack(anchor="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(
            c2,
            text="Filtro ressonante dinâmico que abre e fecha as frequências médias automaticamente.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=14, pady=(0, 8))
        self.wah_freq_var = self._add_slider(c2, "Frequência LFO", 0.2, 8.0, 1.5, "Hz", step=0.1)
        self.wah_depth_var = self._add_slider(c2, "Profundidade (Depth)", 0.0, 100.0, 75.0, "%", step=1.0)
        self.wah_res_var = self._add_slider(c2, "Ressonância (Q)", 0.5, 8.0, 2.8, "x", step=0.1)
        self.wah_mix_var = self._add_slider(c2, "Mistura (Mix)", 0.0, 100.0, 75.0, "%", step=1.0)

        # Chorus / Flanger
        c3 = ctk.CTkFrame(scroll, fg_color="#0f172a", corner_radius=10)
        c3.pack(fill="x", padx=10, pady=8)
        self.chorus_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            c3,
            text="Chorus & Flanger (Coro / Voz Dupla / Jato)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.chorus_en_var,
            command=self._on_param_change,
        ).pack(anchor="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(
            c3,
            text="Atrasos curtos (1.5–7 ms) geram Flanger metálico; atrasos maiores (12–30 ms) criam efeito Coro / Voz Dupla.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=14, pady=(0, 8))
        self.chorus_rate_var = self._add_slider(c3, "Velocidade LFO", 0.1, 8.0, 1.2, "Hz", step=0.1)
        self.chorus_delay_var = self._add_slider(c3, "Atraso Base (Flanger ↔ Chorus)", 1.5, 35.0, 14.0, "ms", step=0.5)
        self.chorus_depth_var = self._add_slider(c3, "Modulação (Depth)", 0.5, 15.0, 4.5, "ms", step=0.5)
        self.chorus_fb_var = self._add_slider(c3, "Feedback", 0.0, 85.0, 25.0, "%", step=1.0)
        self.chorus_mix_var = self._add_slider(c3, "Mistura (Mix)", 0.0, 100.0, 50.0, "%", step=1.0)

        # Tremolo (estilo Audacity)
        c4 = ctk.CTkFrame(scroll, fg_color="#0f172a", corner_radius=10)
        c4.pack(fill="x", padx=10, pady=8)
        self.trem_en_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            c4,
            text="Tremolo (estilo 'Tremolo' do Audacity)",
            font=ctk.CTkFont(size=15, weight="bold"),
            variable=self.trem_en_var,
            command=self._on_param_change,
        ).pack(anchor="w", padx=14, pady=(10, 2))
        trem_row = ctk.CTkFrame(c4, fg_color="transparent")
        trem_row.pack(fill="x", padx=14, pady=(4, 6))
        ctk.CTkLabel(trem_row, text="Forma de Onda:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        self.trem_wave_var = ctk.StringVar(value="Senoide")
        ctk.CTkOptionMenu(
            trem_row,
            variable=self.trem_wave_var,
            values=["Senoide", "Triangular", "Quadrada", "Dente de Serra"],
            command=lambda _: self._on_param_change(),
        ).pack(side="left")
        self.trem_freq_var = self._add_slider(c4, "Frequência", 0.5, 25.0, 6.0, "Hz", step=0.5)
        self.trem_depth_var = self._add_slider(c4, "Intensidade (Wetness)", 0.0, 100.0, 65.0, "%", step=1.0)

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
        box = ctk.CTkScrollableFrame(tab, fg_color="#0f172a", corner_radius=10)
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
            ("Vocoder (12 Bandas Synth)", self.voc_en_var),
            ("Equalizador (EQ 5 Bandas + Cortes)", self.eq_en_var),
            ("Phaser (Audacity)", self.phaser_en_var),
            ("Wahwah (Audacity)", self.wah_en_var),
            ("Chorus & Flanger", self.chorus_en_var),
            ("Tremolo (Audacity)", self.trem_en_var),
            ("Modulador em Anel (Robô)", self.ring_en_var),
            ("Distorção & Bitcrusher (Rádio/Lo-Fi)", self.dist_en_var),
            ("Eco / Delay", self.echo_en_var),
            ("Reverberação (Reverb)", self.rev_en_var),
        ]

        grid = ctk.CTkFrame(box, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=6)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        for idx, (label, var) in enumerate(modules):
            card = ctk.CTkFrame(grid, fg_color="#161f33", corner_radius=8)
            card.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=6, pady=6)
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
            vocoder_enabled=bool(self.voc_en_var.get()),
            vocoder_carrier=str(self.voc_carrier_var.get()),
            vocoder_freq_hz=float(self.voc_freq_var.get()),
            vocoder_smooth=float(self.voc_smooth_var.get()) / 100.0,
            vocoder_mix=float(self.voc_mix_var.get()) / 100.0,
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
            chorus_enabled=bool(self.chorus_en_var.get()),
            chorus_rate_hz=float(self.chorus_rate_var.get()),
            chorus_delay_ms=float(self.chorus_delay_var.get()),
            chorus_depth_ms=float(self.chorus_depth_var.get()),
            chorus_feedback=float(self.chorus_fb_var.get()) / 100.0,
            chorus_mix=float(self.chorus_mix_var.get()) / 100.0,
            phaser_enabled=bool(self.phaser_en_var.get()),
            phaser_stages=int(round(self.phaser_stages_var.get())),
            phaser_freq_hz=float(self.phaser_freq_var.get()),
            phaser_depth=float(self.phaser_depth_var.get()) / 100.0,
            phaser_feedback=float(self.phaser_fb_var.get()) / 100.0,
            phaser_mix=float(self.phaser_mix_var.get()) / 100.0,
            wah_enabled=bool(self.wah_en_var.get()),
            wah_freq_hz=float(self.wah_freq_var.get()),
            wah_depth=float(self.wah_depth_var.get()) / 100.0,
            wah_resonance=float(self.wah_res_var.get()),
            wah_mix=float(self.wah_mix_var.get()) / 100.0,
            tremolo_enabled=bool(self.trem_en_var.get()),
            tremolo_freq_hz=float(self.trem_freq_var.get()),
            tremolo_waveform=str(self.trem_wave_var.get()),
            tremolo_depth=float(self.trem_depth_var.get()) / 100.0,
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

            self.voc_en_var.set(p.vocoder_enabled)
            self.voc_carrier_var.set(p.vocoder_carrier)
            self.voc_freq_var.set(p.vocoder_freq_hz)
            self.voc_smooth_var.set(p.vocoder_smooth * 100.0)
            self.voc_mix_var.set(p.vocoder_mix * 100.0)

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

            self.chorus_en_var.set(p.chorus_enabled)
            self.chorus_rate_var.set(p.chorus_rate_hz)
            self.chorus_delay_var.set(p.chorus_delay_ms)
            self.chorus_depth_var.set(p.chorus_depth_ms)
            self.chorus_fb_var.set(p.chorus_feedback * 100.0)
            self.chorus_mix_var.set(p.chorus_mix * 100.0)

            self.phaser_en_var.set(p.phaser_enabled)
            self.phaser_stages_var.set(p.phaser_stages)
            self.phaser_freq_var.set(p.phaser_freq_hz)
            self.phaser_depth_var.set(p.phaser_depth * 100.0)
            self.phaser_fb_var.set(p.phaser_feedback * 100.0)
            self.phaser_mix_var.set(p.phaser_mix * 100.0)

            self.wah_en_var.set(p.wah_enabled)
            self.wah_freq_var.set(p.wah_freq_hz)
            self.wah_depth_var.set(p.wah_depth * 100.0)
            self.wah_res_var.set(p.wah_resonance)
            self.wah_mix_var.set(p.wah_mix * 100.0)

            self.trem_en_var.set(p.tremolo_enabled)
            self.trem_freq_var.set(p.tremolo_freq_hz)
            self.trem_wave_var.set(p.tremolo_waveform)
            self.trem_depth_var.set(p.tremolo_depth * 100.0)

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
                self.voc_freq_var, self.voc_smooth_var, self.voc_mix_var,
                self.hpf_hz_var, self.lpf_hz_var,
                self.eq_b1_var, self.eq_b2_var, self.eq_b3_var, self.eq_b4_var, self.eq_b5_var,
                self.chorus_rate_var, self.chorus_delay_var, self.chorus_depth_var, self.chorus_fb_var, self.chorus_mix_var,
                self.phaser_stages_var, self.phaser_freq_var, self.phaser_depth_var, self.phaser_fb_var, self.phaser_mix_var,
                self.wah_freq_var, self.wah_depth_var, self.wah_res_var, self.wah_mix_var,
                self.trem_freq_var, self.trem_depth_var,
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

    def _apply_preset(self, name: str, save_cfg: bool = True):
        if name in self.builtin_presets:
            self._load_params_to_ui(self.builtin_presets[name].copy())
            if save_cfg:
                self._save_config()
        elif name in self.user_presets:
            self._load_params_to_ui(self.user_presets[name].copy())
            if save_cfg:
                self._save_config()

    def _save_custom_preset(self):
        name = simpledialog.askstring("Salvar Voz Personalizada", "Digite um nome para esta voz:", parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        self.user_presets[name] = self.params.copy()
        save_user_presets(self.user_presets)
        self.preset_menu.configure(values=self._all_preset_names())
        self.preset_var.set(f"★ {name}")
        self._save_config()

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
    # Persistência de Entradas, Saídas e Preferências
    # ------------------------------------------------------------------ #
    def _restore_saved_ui_prefs(self):
        cfg = self.app_config or {}
        if "monitor_enabled" in cfg:
            self.monitor_var.set(bool(cfg["monitor_enabled"]))
        saved_lat = cfg.get("latency")
        if saved_lat in ("Ultra (256)", "Baixa (512)", "Estável (1024)"):
            self.latency_var.set(saved_lat)
        if "minimize_to_tray" in cfg and pystray is not None:
            self.minimize_to_tray_var.set(bool(cfg["minimize_to_tray"]))

    @staticmethod
    def _device_to_dict(item: AudioDeviceItem | None) -> dict | None:
        if item is None:
            return None
        return {"label": item.label, "name": item.name, "hostapi": item.hostapi}

    def _save_config(self, include_params: bool = False):
        in_item = self._selected_device_item(self.in_dev_var.get(), self.in_devices)
        out_item = self._selected_device_item(self.out_dev_var.get(), self.out_devices)
        mon_item = self._selected_device_item(self.mon_dev_var.get(), self.out_devices)

        # Mantém o dispositivo salvo anteriormente se estiver temporariamente desconectado
        if in_item is not None:
            self.app_config["input_device"] = self._device_to_dict(in_item)
        if out_item is not None:
            self.app_config["output_device"] = self._device_to_dict(out_item)
        if mon_item is not None:
            self.app_config["monitor_device"] = self._device_to_dict(mon_item)

        preset_choice = self.preset_var.get()
        clean_preset = preset_choice[2:] if preset_choice.startswith("★ ") else preset_choice
        self.app_config["last_preset"] = clean_preset
        self.app_config["monitor_enabled"] = bool(self.monitor_var.get())
        self.app_config["latency"] = str(self.latency_var.get())
        self.app_config["minimize_to_tray"] = bool(self.minimize_to_tray_var.get())
        if include_params:
            self.app_config["current_params"] = asdict(self.params)
        save_app_config(self.app_config)

    def _on_device_changed(self, *_):
        self._save_config()
        self._restart_if_running()

    def _on_routing_pref_changed(self):
        self._save_config()
        self._restart_if_running()

    # ------------------------------------------------------------------ #
    # Dispositivos e Motor de Áudio
    # ------------------------------------------------------------------ #
    @staticmethod
    def _match_device_label(
        items: list[AudioDeviceItem],
        labels: list[str],
        prev_item: AudioDeviceItem | None,
        saved_dict: dict | None,
        fallback_fn,
    ) -> str:
        if not items or not labels:
            return labels[0] if labels else ""

        candidates: list[dict] = []
        if prev_item is not None:
            candidates.append({"label": prev_item.label, "name": prev_item.name, "hostapi": prev_item.hostapi})
        if isinstance(saved_dict, dict):
            candidates.append(saved_dict)

        for cand in candidates:
            c_label = cand.get("label")
            if c_label and c_label in labels:
                return c_label
            c_name = cand.get("name")
            c_api = cand.get("hostapi")
            if c_name and c_api:
                for d in items:
                    if d.name == c_name and d.hostapi == c_api:
                        return d.label
            if c_name:
                for d in items:
                    if d.name == c_name:
                        return d.label

        return fallback_fn(labels)

    def _refresh_devices(self, reinit_backend: bool = True, initial_load: bool = False):
        was_running = self.router.running
        prev_in = self._selected_device_item(self.in_dev_var.get(), self.in_devices)
        prev_out = self._selected_device_item(self.out_dev_var.get(), self.out_devices)
        prev_mon = self._selected_device_item(self.mon_dev_var.get(), self.out_devices)

        if reinit_backend:
            if was_running:
                self.router.stop()
            self.in_devices, self.out_devices = AudioRouter.refresh_backend()
        else:
            self.in_devices, self.out_devices = AudioRouter.list_devices()

        in_labels = [d.label for d in self.in_devices] or ["Nenhum microfone encontrado"]
        out_labels = [d.label for d in self.out_devices] or ["Nenhuma saída encontrada"]

        self.in_dev_menu.configure(values=in_labels)
        self.out_dev_menu.configure(values=out_labels)
        self.mon_dev_menu.configure(values=out_labels)

        sel_in = self._match_device_label(
            self.in_devices,
            in_labels,
            prev_in,
            self.app_config.get("input_device"),
            lambda lbls: lbls[0],
        )
        sel_out = self._match_device_label(
            self.out_devices,
            out_labels,
            prev_out,
            self.app_config.get("output_device"),
            lambda lbls: next((lbl for lbl in lbls if "CABLE Input" in lbl or "VB-Audio" in lbl), lbls[0]),
        )
        sel_mon = self._match_device_label(
            self.out_devices,
            out_labels,
            prev_mon,
            self.app_config.get("monitor_device"),
            lambda lbls: next((lbl for lbl in lbls if "CABLE" not in lbl), lbls[0]),
        )

        self.in_dev_var.set(sel_in)
        self.out_dev_var.set(sel_out)
        self.mon_dev_var.set(sel_mon)
        self._save_config()

        if was_running:
            self._start_audio()
        elif not initial_load:
            self.status_lbl.configure(
                text=f"Dispositivos atualizados ({len(self.in_devices)} entradas, {len(self.out_devices)} saídas) — seleções salvas.",
                text_color="#38bdf8",
            )

    def _selected_device_item(self, label: str, items: list[AudioDeviceItem]) -> AudioDeviceItem | None:
        for d in items:
            if d.label == label:
                return d
        return None

    def _selected_device_index(self, label: str, items: list[AudioDeviceItem]) -> int | None:
        item = self._selected_device_item(label, items)
        return item.index if item is not None else None

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
        if self._is_quitting:
            return
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
    # Atualização do Aplicativo (Git / GitHub) + Preservar Configurações
    # ------------------------------------------------------------------ #
    @staticmethod
    def _run_cmd(args: list[str], cwd: str) -> tuple[int, str]:
        kwargs = {"cwd": cwd, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True}
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            res = subprocess.run(args, timeout=45, **kwargs)
            return res.returncode, (res.stdout or "").strip()
        except Exception as e:
            return 1, str(e)

    def _start_app_update(self):
        # Salva imediatamente entradas, saídas, preset e parâmetros atuais antes de checar/atualizar
        self._save_config(include_params=True)

        win = ctk.CTkToplevel(self)
        win.title("Atualizar VoxCraft Studio")
        win.geometry("490x260")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(
            win, text="Atualização do VoxCraft Studio", font=ctk.CTkFont(size=17, weight="bold"), text_color="#4cc9f0"
        ).pack(anchor="w", padx=20, pady=(16, 6))

        msg_lbl = ctk.CTkLabel(
            win,
            text="Verificando atualizações e garantindo que suas entradas e saídas estejam salvas...",
            justify="left",
            wraplength=450,
            font=ctk.CTkFont(size=12.5),
        )
        msg_lbl.pack(anchor="w", padx=20, pady=8)

        progress = ctk.CTkProgressBar(win, mode="indeterminate", width=440)
        progress.pack(padx=20, pady=(6, 12))
        progress.start()

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(6, 14))

        action_btn = ctk.CTkButton(btn_row, text="Aplicar Atualização", width=165, fg_color="#10b981", state="disabled")
        action_btn.pack(side="left")
        close_btn = ctk.CTkButton(btn_row, text="Fechar", width=100, fg_color="#334155", command=win.destroy)
        close_btn.pack(side="right")

        def safe_ui(fn):
            if win.winfo_exists():
                self.after(0, fn)

        def finish_with_message(text: str, color: str = "#e2e8f0"):
            def _ui():
                progress.stop()
                progress.set(1.0)
                msg_lbl.configure(text=text, text_color=color)
                action_btn.configure(state="disabled")
            safe_ui(_ui)

        def apply_git_update(target_ref: str):
            def _worker():
                safe_ui(lambda: (
                    action_btn.configure(state="disabled"),
                    close_btn.configure(state="disabled"),
                    progress.start(),
                    msg_lbl.configure(text="Baixando novos arquivos via Git...", text_color="#38bdf8"),
                ))
                rc, out = self._run_cmd(["git", "pull", "--ff-only"], BASE_DIR)
                if rc != 0:
                    remote_branch = target_ref.split("/", 1)[-1] if "/" in target_ref else "main"
                    rc, out = self._run_cmd(["git", "pull", "--autostash", "origin", remote_branch], BASE_DIR)
                if rc != 0:
                    safe_ui(lambda: (
                        progress.stop(),
                        close_btn.configure(state="normal"),
                        msg_lbl.configure(text=f"Falha ao atualizar via Git:\n{out[:280]}", text_color="#ef4444"),
                    ))
                    return

                safe_ui(lambda: msg_lbl.configure(text="Atualizando dependências Python (requirements.txt)..."))
                self._run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"], BASE_DIR)
                safe_ui(self._relaunch_after_update)

            threading.Thread(target=_worker, daemon=True).start()

        def apply_zip_update():
            def _worker():
                safe_ui(lambda: (
                    action_btn.configure(state="disabled"),
                    close_btn.configure(state="disabled"),
                    progress.start(),
                    msg_lbl.configure(text="Baixando pacote mais recente do GitHub...", text_color="#38bdf8"),
                ))
                raw_zip = None
                last_err = ""
                for branch in ("main", "master"):
                    url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/{branch}.zip"
                    try:
                        with urllib.request.urlopen(url, timeout=25) as resp:
                            raw_zip = resp.read()
                        break
                    except Exception as e:
                        last_err = str(e)
                if not raw_zip:
                    safe_ui(lambda: (
                        progress.stop(),
                        close_btn.configure(state="normal"),
                        msg_lbl.configure(text=f"Não foi possível baixar atualização:\n{last_err}", text_color="#ef4444"),
                    ))
                    return

                try:
                    preserved = {"voxcraft_config.json", "user_presets.json"}
                    with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
                        for member in zf.infolist():
                            if member.is_dir():
                                continue
                            parts = member.filename.split("/", 1)
                            rel = parts[1] if len(parts) > 1 else parts[0]
                            if not rel or rel in preserved or rel.startswith("."):
                                if rel != ".gitignore":
                                    continue
                            dest = os.path.normpath(os.path.join(BASE_DIR, rel))
                            if not dest.startswith(os.path.normpath(BASE_DIR)):
                                continue
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            with zf.open(member) as src, open(dest, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                except Exception as e:
                    safe_ui(lambda: (
                        progress.stop(),
                        close_btn.configure(state="normal"),
                        msg_lbl.configure(text=f"Erro ao extrair arquivos:\n{e}", text_color="#ef4444"),
                    ))
                    return

                safe_ui(lambda: msg_lbl.configure(text="Atualizando dependências Python (requirements.txt)..."))
                self._run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"], BASE_DIR)
                safe_ui(self._relaunch_after_update)

            threading.Thread(target=_worker, daemon=True).start()

        def check_worker():
            git_dir = os.path.join(BASE_DIR, ".git")
            if os.path.isdir(git_dir):
                rc, out = self._run_cmd(["git", "fetch", "origin"], BASE_DIR)
                if rc != 0:
                    finish_with_message(f"Não foi possível verificar o GitHub:\n{out[:260]}", "#f59e0b")
                    return
                rc_u, upstream = self._run_cmd(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], BASE_DIR)
                target = upstream if rc_u == 0 and upstream else "origin/main"
                rc_r, remote_sha = self._run_cmd(["git", "rev-parse", target], BASE_DIR)
                if rc_r != 0:
                    target = "origin/master"
                    rc_r, remote_sha = self._run_cmd(["git", "rev-parse", target], BASE_DIR)
                rc_h, local_sha = self._run_cmd(["git", "rev-parse", "HEAD"], BASE_DIR)
                if rc_h == 0 and rc_r == 0 and local_sha == remote_sha:
                    finish_with_message(
                        "Você já está na versão mais recente do VoxCraft Studio!\n"
                        "Suas entradas e saídas de áudio continuam salvas.",
                        "#10b981",
                    )
                    return

                _, log_out = self._run_cmd(["git", "log", f"HEAD..{target}", "--oneline", "-n", "4"], BASE_DIR)
                summary = f"Nova atualização disponível!\n\n{log_out}" if log_out else "Nova atualização disponível no repositório."
                safe_ui(lambda: (
                    progress.stop(),
                    msg_lbl.configure(
                        text=f"{summary}\n\nSuas entradas, saídas e presets serão mantidos.",
                        text_color="#e2e8f0",
                    ),
                    action_btn.configure(state="normal", command=lambda: apply_git_update(target)),
                ))
            else:
                safe_ui(lambda: (
                    progress.stop(),
                    msg_lbl.configure(
                        text="Pasta sem repositório Git detectada.\n"
                             "Você pode baixar e aplicar a versão mais recente do GitHub agora.\n"
                             "Suas entradas, saídas e presets salvos não serão apagados.",
                        text_color="#e2e8f0",
                    ),
                    action_btn.configure(state="normal", text="Baixar e Atualizar", command=apply_zip_update),
                ))

        threading.Thread(target=check_worker, daemon=True).start()

    def _relaunch_after_update(self):
        self.app_config["pending_update_restore"] = True
        self.app_config["was_running_before_update"] = bool(self.router.running)
        self._save_config(include_params=True)
        try:
            subprocess.Popen([sys.executable, os.path.abspath(__file__)], cwd=BASE_DIR)
        except Exception as e:
            messagebox.showerror("Atualização Concluída", f"Arquivos atualizados! Reabra o aplicativo manualmente.\n({e})")
        self._quit_app()

    # ------------------------------------------------------------------ #
    # Guia Discord & Fechamento / Bandeja
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
        if not self._is_quitting and self.minimize_to_tray_var.get() and self._tray_icon is not None:
            self._minimize_to_tray()
            return
        self._quit_app()

    def _quit_app(self):
        self._is_quitting = True
        self._save_config()
        self.router.stop()
        if self._tray_icon is not None:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None
        self.destroy()


if __name__ == "__main__":
    app = VoxCraftApp()
    app.mainloop()
