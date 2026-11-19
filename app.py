from __future__ import annotations

import ctypes
from dataclasses import asdict
import io
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import urllib.error
import urllib.parse
import urllib.request
import zipfile

if sys.platform == "win32":
    import winreg
else:
    winreg = None
    try:
        import fcntl
    except ImportError:
        fcntl = None

import customtkinter as ctk

from i18n import (
    LANGUAGES,
    LANGUAGE_LABELS,
    get_theme,
    preset_to_display,
    preset_to_internal,
    tr,
)

GITHUB_REPO = "CakeSweet/voxcraft"
APP_VERSION = "2.1.0"

IS_FROZEN = bool(getattr(sys, "frozen", False))
BASE_DIR = os.path.dirname(os.path.abspath(sys.executable if IS_FROZEN else __file__))
ASSETS_DIR = os.path.join(getattr(sys, "_MEIPASS", BASE_DIR), "assets")
ICON_ICO_PATH = os.path.join(ASSETS_DIR, "voxcraft.ico")
ICON_PNG_PATH = os.path.join(ASSETS_DIR, "voxcraft.png")
BUILD_INFO_PATH = os.path.join(ASSETS_DIR, "build_info.json")


def _get_app_data_dir(create: bool = True) -> str:
    if not IS_FROZEN and os.access(BASE_DIR, os.W_OK):
        return BASE_DIR
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    data_dir = os.path.join(base, "VoxCraftStudio")
    if create:
        os.makedirs(data_dir, exist_ok=True)
    return data_dir


def _get_instance_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    inst_dir = os.path.join(base, "VoxCraftStudio")
    os.makedirs(inst_dir, exist_ok=True)
    return inst_dir


class _VoxCraftSingleInstance:
    """Garante instância única e restaura a janela já aberta quando iniciado novamente."""

    def __init__(self):
        self._inst_dir = _get_instance_dir()
        self._lock_path = os.path.join(self._inst_dir, "voxcraft.lock")
        self._ipc_path = os.path.join(self._inst_dir, "voxcraft.ipc")
        self._lock_fp = None
        self._win_mutex = None
        self._server_sock: socket.socket | None = None
        self._stop_event = threading.Event()
        self._on_show = None

    def acquire(self, wait_timeout: float = 0.0) -> bool:
        deadline = time.monotonic() + max(0.0, wait_timeout)
        while True:
            if sys.platform == "win32":
                try:
                    k32 = ctypes.windll.kernel32
                    handle = k32.CreateMutexW(None, True, "Local\\VoxCraftStudio_SingleInstance_V1")
                    last_err = k32.GetLastError()
                    if handle and last_err != 183:  # ERROR_ALREADY_EXISTS
                        self._win_mutex = handle
                        return True
                    if handle:
                        k32.CloseHandle(handle)
                except Exception:
                    pass
            else:
                try:
                    fp = open(self._lock_path, "w", encoding="utf-8")
                    if fcntl is not None:
                        fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fp.write(str(os.getpid()))
                    fp.flush()
                    self._lock_fp = fp
                    return True
                except Exception:
                    try:
                        fp.close()
                    except Exception:
                        pass

            if time.monotonic() >= deadline:
                return False
            time.sleep(0.1)

    def start_ipc_server(self, on_show_callback):
        self._on_show = on_show_callback
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", 0))
            srv.listen(4)
            srv.settimeout(0.4)
            port = srv.getsockname()[1]
            self._server_sock = srv
            with open(self._ipc_path, "w", encoding="utf-8") as f:
                f.write(str(port))
        except Exception:
            return

        def _serve():
            while not self._stop_event.is_set():
                try:
                    conn, _ = srv.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    data = conn.recv(64)
                    if b"SHOW" in data and self._on_show is not None:
                        self._on_show()
                except Exception:
                    pass
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

        threading.Thread(target=_serve, daemon=True).start()

    def notify_existing(self, retries: int = 8) -> bool:
        for _ in range(retries):
            try:
                if os.path.exists(self._ipc_path):
                    with open(self._ipc_path, "r", encoding="utf-8") as f:
                        port = int(f.read().strip())
                    with socket.create_connection(("127.0.0.1", port), timeout=1.0) as cli:
                        cli.sendall(b"SHOW\n")
                    return True
            except Exception:
                pass
            time.sleep(0.08)
        return False

    def release(self):
        self._stop_event.set()
        if self._server_sock is not None:
            try:
                self._server_sock.close()
            except Exception:
                pass
            self._server_sock = None
        try:
            if os.path.exists(self._ipc_path):
                os.remove(self._ipc_path)
        except Exception:
            pass
        if self._win_mutex is not None and sys.platform == "win32":
            try:
                k32 = ctypes.windll.kernel32
                k32.ReleaseMutex(self._win_mutex)
                k32.CloseHandle(self._win_mutex)
            except Exception:
                pass
            self._win_mutex = None
        if self._lock_fp is not None:
            try:
                if fcntl is not None:
                    fcntl.flock(self._lock_fp.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                self._lock_fp.close()
            except Exception:
                pass
            self._lock_fp = None


_SINGLE_INSTANCE: _VoxCraftSingleInstance | None = None


def _peek_startup_prefs() -> tuple[str, str]:
    candidates = []
    if not IS_FROZEN and os.access(BASE_DIR, os.W_OK):
        candidates.append(os.path.join(BASE_DIR, "voxcraft_config.json"))
    candidates.append(os.path.join(_get_instance_dir(), "voxcraft_config.json"))

    theme_key, lang_key = "dark", "pt"
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    t = str(data.get("theme", "")).strip().lower()
                    if t in ("dark", "oled", "light"):
                        theme_key = t
                    l = str(data.get("language", "")).strip().lower()
                    if l in LANGUAGES:
                        lang_key = l
                break
            except Exception:
                pass
    return theme_key, lang_key


_INIT_THEME, _INIT_LANG = _peek_startup_prefs()
ctk.set_appearance_mode(get_theme(_INIT_THEME)["ctk_mode"])
ctk.set_default_color_theme("blue")

# Módulos pesados carregados em segundo plano durante a tela de carregamento suave
np = None
signal = None
Image = None
ImageDraw = None
ImageTk = None
pystray = None
pynput_kb = None
DSPParams = None
RealTimeDSPEngine = None
build_eq_sos = None
get_builtin_presets = None
load_app_config = None
load_user_presets = None
save_app_config = None
save_user_presets = None
AudioDeviceItem = None
AudioRouter = None
_MODULES_LOADED = False


def _load_runtime_modules():
    global np, signal, Image, ImageDraw, ImageTk, pystray, pynput_kb
    global DSPParams, RealTimeDSPEngine, build_eq_sos
    global get_builtin_presets, load_app_config, load_user_presets, save_app_config, save_user_presets
    global AudioDeviceItem, AudioRouter, _MODULES_LOADED

    if _MODULES_LOADED:
        return

    import numpy as _np
    from scipy import signal as _signal

    np = _np
    signal = _signal

    try:
        from PIL import Image as _Image, ImageDraw as _ImageDraw, ImageTk as _ImageTk
        Image, ImageDraw, ImageTk = _Image, _ImageDraw, _ImageTk
    except ImportError:
        Image = ImageDraw = ImageTk = None

    try:
        import pystray as _pystray
        pystray = _pystray
    except ImportError:
        pystray = None

    try:
        from pynput import keyboard as _pynput_kb
        pynput_kb = _pynput_kb
    except ImportError:
        pynput_kb = None

    from dsp_engine import DSPParams as _DSPParams, RealTimeDSPEngine as _RealTimeDSPEngine, build_eq_sos as _build_eq_sos
    from presets import (
        get_builtin_presets as _get_builtin_presets,
        load_app_config as _load_app_config,
        load_user_presets as _load_user_presets,
        save_app_config as _save_app_config,
        save_user_presets as _save_user_presets,
    )
    from audio_router import AudioDeviceItem as _AudioDeviceItem, AudioRouter as _AudioRouter

    DSPParams = _DSPParams
    RealTimeDSPEngine = _RealTimeDSPEngine
    build_eq_sos = _build_eq_sos
    get_builtin_presets = _get_builtin_presets
    load_app_config = _load_app_config
    load_user_presets = _load_user_presets
    save_app_config = _save_app_config
    save_user_presets = _save_user_presets
    AudioDeviceItem = _AudioDeviceItem
    AudioRouter = _AudioRouter
    _MODULES_LOADED = True


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

        self._window_icon_photo = None
        self._splash_icon_photo = None
        self._tray_icon = None
        self._tray_thread = None
        self._is_quitting = False
        self._is_loaded = False
        self._rebuilding_ui = False
        self._ui_loop_job = None
        self.ui_theme: str = _INIT_THEME
        self.ui_lang: str = _INIT_LANG
        self._i18n_hooks: list = []
        self._theme_hooks: list = []
        self._transparent_containers: list = []
        self._tab_frames: dict[str, ctk.CTkFrame] = {}
        self._tab_buttons: dict[str, ctk.CTkButton] = {}
        self._active_tab_key: str = "tab_pitch"

        # Pool compartilhado de fontes (evita 120+ objetos Font no Tkinter e acelera redesenhos)
        self._fonts = {
            "xs": ctk.CTkFont(size=11),
            "xs_b": ctk.CTkFont(size=11, weight="bold"),
            "sm": ctk.CTkFont(size=12),
            "sm_b": ctk.CTkFont(size=12, weight="bold"),
            "md": ctk.CTkFont(size=13),
            "md_b": ctk.CTkFont(size=13, weight="bold"),
            "lg_b": ctk.CTkFont(size=14, weight="bold"),
            "h3_b": ctk.CTkFont(size=15, weight="bold"),
            "h2_b": ctk.CTkFont(size=17, weight="bold"),
            "h1_b": ctk.CTkFont(size=18, weight="bold"),
            "brand": ctk.CTkFont(size=19, weight="bold"),
            "splash": ctk.CTkFont(size=22, weight="bold"),
        }

        # Cache de estado da UI e controle assíncrono de áudio (evita congelamentos/tela branca)
        self._audio_op_seq = 0
        self._audio_worker_lock = threading.Lock()
        self._update_win = None
        self._discord_win = None
        self._wave_mid_id = None
        self._wave_line_id = None
        self._wave_cached_w = 0
        self._wave_cached_len = 0
        self._wave_xs = None
        self._last_in_norm = -1.0
        self._last_out_norm = -1.0
        self._last_gate_open: bool | None = None
        self._last_wave_idle = False
        self._last_ui_hidden = False
        self._eq_redraw_job = None
        self._last_eq_sig = None

        th = self._c()
        # Abre imediatamente em modo Tela de Carregamento (janela única, 60 FPS suave, sem travar)
        self.title(f"VoxCraft Studio — {self._t('loading')}")
        self.configure(fg_color=th["window_bg"])
        sw_w, sw_h = 480, 235
        scr_w = self.winfo_screenwidth()
        scr_h = self.winfo_screenheight()
        self.geometry(f"{sw_w}x{sw_h}+{(scr_w - sw_w) // 2}+{(scr_h - sw_h) // 2}")
        self.resizable(False, False)
        self._apply_window_icon()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._splash_disp = 0.05
        self._splash_target = 0.55
        self._splash_phase = 0.0
        self._splash_anim_job = None
        self._import_done = False
        self._import_error: str | None = None

        self._build_splash_ui()
        self._animate_splash()
        self.after(30, self._start_async_boot)

    def _t(self, key: str, **kwargs) -> str:
        return tr(self.ui_lang, key, **kwargs)

    def _c(self) -> dict[str, str]:
        return get_theme(self.ui_theme)

    def _preset_to_display(self, canonical_name: str) -> str:
        if canonical_name.startswith("★ "):
            return canonical_name
        return preset_to_display(self.ui_lang, canonical_name)

    def _preset_to_internal(self, display_name: str) -> str:
        if display_name.startswith("★ "):
            return display_name
        return preset_to_internal(display_name)

    def _reg_i18n(self, fn):
        self._i18n_hooks.append(fn)

    def _reg_theme(self, widget, fn):
        self._theme_hooks.append((widget, fn))
        return widget

    def _card(self, parent, role: str = "card", **kw) -> ctk.CTkFrame:
        th = self._c()
        if role == "panel":
            w = ctk.CTkFrame(parent, fg_color=th["panel_bg"], border_width=1, border_color=th["panel_border"], **kw)
            self._reg_theme(
                w,
                lambda t, wd=w: wd.configure(
                    fg_color=t["panel_bg"], border_color=t["panel_border"], bg_color="transparent"
                ),
            )
        elif role == "subcard":
            w = ctk.CTkFrame(parent, fg_color=th["subcard_bg"], **kw)
            self._reg_theme(w, lambda t, wd=w: wd.configure(fg_color=t["subcard_bg"], bg_color="transparent"))
        elif role == "tabbar":
            w = ctk.CTkFrame(parent, fg_color=th["tab_bg"], **kw)
            self._reg_theme(w, lambda t, wd=w: wd.configure(fg_color=t["tab_bg"], bg_color="transparent"))
        else:
            w = ctk.CTkFrame(parent, fg_color=th["card_bg"], border_width=1, border_color=th["card_border"], **kw)
            self._reg_theme(
                w,
                lambda t, wd=w: wd.configure(
                    fg_color=t["card_bg"], border_color=t["card_border"], bg_color="transparent"
                ),
            )
        return w

    def _scroll(self, parent, role: str = "transparent", **kw) -> ctk.CTkScrollableFrame:
        th = self._c()
        if role == "panel":
            w = ctk.CTkScrollableFrame(
                parent,
                fg_color=th["panel_bg"],
                border_width=1,
                border_color=th["panel_border"],
                scrollbar_fg_color=th["panel_bg"],
                scrollbar_button_color=th["control_btn"],
                scrollbar_button_hover_color=th["control_hover"],
                **kw,
            )

            def _apply_panel_scroll_theme(t, wd=w):
                wd.configure(
                    fg_color=t["panel_bg"],
                    border_color=t["panel_border"],
                    bg_color="transparent",
                    scrollbar_fg_color=t["panel_bg"],
                    scrollbar_button_color=t["control_btn"],
                    scrollbar_button_hover_color=t["control_hover"],
                )
                try:
                    if hasattr(wd, "_parent_frame"):
                        wd._parent_frame.configure(
                            fg_color=t["panel_bg"], border_color=t["panel_border"], bg_color="transparent"
                        )
                    if hasattr(wd, "_parent_canvas"):
                        wd._parent_canvas.configure(bg=t["panel_bg"])
                except Exception:
                    pass

            self._reg_theme(w, _apply_panel_scroll_theme)
        else:
            w = ctk.CTkScrollableFrame(
                parent,
                fg_color="transparent",
                scrollbar_fg_color=th["panel_bg"],
                scrollbar_button_color=th["control_btn"],
                scrollbar_button_hover_color=th["control_hover"],
                **kw,
            )

            def _apply_trans_scroll_theme(t, wd=w):
                wd.configure(
                    fg_color="transparent",
                    bg_color="transparent",
                    scrollbar_fg_color=t["panel_bg"],
                    scrollbar_button_color=t["control_btn"],
                    scrollbar_button_hover_color=t["control_hover"],
                )
                try:
                    if hasattr(wd, "_parent_frame"):
                        wd._parent_frame.configure(fg_color=t["panel_bg"], bg_color="transparent")
                    if hasattr(wd, "_parent_canvas"):
                        wd._parent_canvas.configure(bg=t["panel_bg"])
                except Exception:
                    pass

            self._reg_theme(w, _apply_trans_scroll_theme)
        return w

    def _lbl(self, parent, key_or_text: str, font_key: str = "sm", color_role: str = "text_muted", is_key: bool = True, **kw) -> ctk.CTkLabel:
        th = self._c()
        text = self._t(key_or_text) if is_key else key_or_text
        w = ctk.CTkLabel(parent, text=text, font=self._fonts[font_key], text_color=th[color_role], **kw)
        if is_key:
            self._reg_i18n(lambda wd=w, k=key_or_text: wd.configure(text=self._t(k)))
        self._reg_theme(w, lambda t, wd=w, cr=color_role: wd.configure(text_color=t[cr]))
        return w

    def _switch(self, parent, key_or_text: str, variable, command, font_key: str | None = None, is_key: bool = True, progress_color: str | None = None) -> ctk.CTkSwitch:
        th = self._c()
        text = self._t(key_or_text) if is_key else key_or_text
        kwargs = {
            "text": text,
            "variable": variable,
            "fg_color": th["track_bg"],
            "progress_color": progress_color or th["accent"],
            "button_color": th["switch_knob"],
            "button_hover_color": th["switch_knob_hover"],
            "text_color": th["text_primary"],
            "command": command,
        }
        if font_key is not None:
            kwargs["font"] = self._fonts[font_key]
        w = ctk.CTkSwitch(parent, **kwargs)
        if is_key:
            self._reg_i18n(lambda wd=w, k=key_or_text: wd.configure(text=self._t(k)))
        if progress_color is None:
            self._reg_theme(
                w,
                lambda t, wd=w: wd.configure(
                    fg_color=t["track_bg"],
                    progress_color=t["accent"],
                    button_color=t["switch_knob"],
                    button_hover_color=t["switch_knob_hover"],
                    text_color=t["text_primary"],
                ),
            )
        else:
            self._reg_theme(
                w,
                lambda t, wd=w: wd.configure(
                    fg_color=t["track_bg"],
                    button_color=t["switch_knob"],
                    button_hover_color=t["switch_knob_hover"],
                    text_color=t["text_primary"],
                ),
            )
        return w

    def _btn(
        self,
        parent,
        key_or_text: str,
        command,
        is_key: bool = True,
        bordered: bool = True,
        hover_override: str | None = None,
        font_key: str | None = None,
        **kw,
    ) -> ctk.CTkButton:
        th = self._c()
        text = self._t(key_or_text) if is_key else key_or_text
        if font_key is not None:
            kw["font"] = self._fonts[font_key]
        if bordered:
            kw.setdefault("border_width", 1)
            kw["border_color"] = th["control_border"]
        w = ctk.CTkButton(
            parent,
            text=text,
            fg_color=th["control_bg"],
            hover_color=hover_override or th["control_hover"],
            text_color=th["text_primary"],
            command=command,
            **kw,
        )
        if is_key:
            self._reg_i18n(lambda wd=w, k=key_or_text: wd.configure(text=self._t(k)))
        if bordered:
            self._reg_theme(
                w,
                lambda t, wd=w, hv=hover_override: wd.configure(
                    fg_color=t["control_bg"],
                    hover_color=hv or t["control_hover"],
                    text_color=t["text_primary"],
                    border_color=t["control_border"],
                ),
            )
        else:
            self._reg_theme(
                w,
                lambda t, wd=w, hv=hover_override: wd.configure(
                    fg_color=t["control_bg"],
                    hover_color=hv or t["control_hover"],
                    text_color=t["text_primary"],
                ),
            )
        return w

    def _optmenu(self, parent, variable, values, command, **kw) -> ctk.CTkOptionMenu:
        th = self._c()
        w = ctk.CTkOptionMenu(
            parent,
            variable=variable,
            values=values,
            fg_color=th["control_bg"],
            button_color=th["control_btn"],
            button_hover_color=th["control_hover"],
            dropdown_fg_color=th["dropdown_bg"],
            dropdown_hover_color=th["dropdown_hover"],
            dropdown_text_color=th["dropdown_text"],
            text_color=th["text_primary"],
            command=command,
            **kw,
        )
        self._reg_theme(
            w,
            lambda t, wd=w: wd.configure(
                fg_color=t["control_bg"],
                button_color=t["control_btn"],
                button_hover_color=t["control_hover"],
                dropdown_fg_color=t["dropdown_bg"],
                dropdown_hover_color=t["dropdown_hover"],
                dropdown_text_color=t["dropdown_text"],
                text_color=t["text_primary"],
            ),
        )
        return w

    def _wave_to_display(self, internal_val: str) -> str:
        mapping = {
            "Senoide": "wave_sine",
            "Triangular": "wave_tri",
            "Quadrada": "wave_sq",
            "Dente de Serra": "wave_saw",
            "Acorde": "wave_chord",
            "Sussurro (Ruído)": "wave_whisper",
        }
        k = mapping.get(internal_val)
        return self._t(k) if k else internal_val

    def _wave_to_internal(self, display_val: str) -> str:
        key_map = {
            "wave_sine": "Senoide",
            "wave_tri": "Triangular",
            "wave_sq": "Quadrada",
            "wave_saw": "Dente de Serra",
            "wave_chord": "Acorde",
            "wave_whisper": "Sussurro (Ruído)",
        }
        for lang in LANGUAGES:
            for k, internal in key_map.items():
                if tr(lang, k) == display_val:
                    return internal
        return display_val

    def _latency_to_display(self, val: str) -> str:
        if "256" in val:
            return self._t("lat_ultra")
        if "1024" in val:
            return self._t("lat_stable")
        return self._t("lat_low")

    def _build_splash_ui(self):
        th = self._c()
        local_id = self._get_local_build_identity()
        self.configure(fg_color=th["panel_bg"])
        self._splash_frame = ctk.CTkFrame(
            self, fg_color=th["panel_bg"], border_width=0, corner_radius=0
        )
        self._splash_frame.pack(fill="both", expand=True, padx=0, pady=0)

        top_strip = ctk.CTkFrame(
            self._splash_frame, fg_color=th["accent"], height=3, corner_radius=0, border_width=0
        )
        top_strip.pack(fill="x", side="top")

        hdr = ctk.CTkFrame(self._splash_frame, fg_color="transparent")
        hdr.pack(pady=(34, 8))

        if os.path.exists(ICON_PNG_PATH):
            try:
                raw_ico = tk.PhotoImage(file=ICON_PNG_PATH)
                factor = max(1, raw_ico.width() // 52)
                self._splash_icon_photo = raw_ico.subsample(factor, factor)
                tk.Label(hdr, image=self._splash_icon_photo, bg=th["panel_bg"], bd=0, highlightthickness=0).pack(
                    side="left", padx=(0, 12)
                )
            except Exception:
                pass

        titles = ctk.CTkFrame(hdr, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(
            titles, text="VoxCraft Studio", font=self._fonts["splash"], text_color=th["accent"]
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles,
            text=f"v{local_id['version']}",
            font=self._fonts["xs"],
            text_color=th["text_subtle"],
        ).pack(anchor="w")

        self._splash_lbl = ctk.CTkLabel(
            self._splash_frame,
            text=self._t("loading"),
            font=self._fonts["sm"],
            text_color=th["text_body"],
        )
        self._splash_lbl.pack(pady=(14, 10))

        self._splash_canvas = tk.Canvas(
            self._splash_frame, width=360, height=10, bg=th["track_bg"], highlightthickness=0
        )
        self._splash_canvas.pack()

    def _animate_splash(self):
        if self._is_quitting or self._is_loaded:
            return
        try:
            if not self._splash_frame.winfo_exists():
                return
            self._splash_disp += (self._splash_target - self._splash_disp) * 0.14
            self._splash_phase = (self._splash_phase + 0.06) % 1.0
            c = self._splash_canvas
            w = 360
            fill_w = max(12, min(w, int(w * self._splash_disp)))
            c.delete("all")
            c.create_rectangle(0, 0, fill_w, 10, fill="#2563eb", width=0)
            c.create_rectangle(0, 0, max(8, fill_w - 2), 6, fill="#38bdf8", width=0)
            # Brilho suave percorrendo a barra durante o carregamento
            if fill_w > 48:
                hx = int(self._splash_phase * (fill_w + 50)) - 40
                x0 = max(0, hx)
                x1 = min(fill_w, hx + 44)
                if x1 > x0:
                    c.create_rectangle(x0, 0, x1, 10, fill="#7dd3fc", width=0)
        except Exception:
            return
        self._splash_anim_job = self.after(16, self._animate_splash)

    def _start_async_boot(self):
        def _worker():
            try:
                _load_runtime_modules()
            except Exception as exc:
                self._import_error = str(exc)
            finally:
                self._import_done = True

        threading.Thread(target=_worker, daemon=True).start()
        self.after(25, self._poll_boot_imports)

    def _poll_boot_imports(self):
        if self._is_quitting:
            return
        if not self._import_done:
            self.after(25, self._poll_boot_imports)
            return
        if self._import_error:
            messagebox.showerror(self._t("boot_err_title"), self._t("boot_err_deps", err=self._import_error))
            self._quit_app()
            return
        self._splash_target = 0.78
        self._splash_lbl.configure(text=self._t("loading_ui"))
        self.after(20, self._boot_step_build_ui)

    def _boot_step_build_ui(self):
        if self._is_quitting:
            return
        try:
            self.dsp = RealTimeDSPEngine(48000.0)
            self.router = AudioRouter(self.dsp)
            self.params = DSPParams()

            self.builtin_presets = get_builtin_presets()
            self.user_presets = load_user_presets()
            self.app_config = load_app_config()
            if str(self.app_config.get("github_repo", "")).strip().lower() == "cakesweet/voxcraft_studio":
                self.app_config["github_repo"] = GITHUB_REPO
            cfg_theme = str(self.app_config.get("theme", self.ui_theme)).strip().lower()
            if cfg_theme in ("dark", "oled", "light"):
                self.ui_theme = cfg_theme
            cfg_lang = str(self.app_config.get("language", self.ui_lang)).strip().lower()
            if cfg_lang in LANGUAGES:
                self.ui_lang = cfg_lang
            ctk.set_appearance_mode(self._c()["ctk_mode"])

            self.in_devices: list[AudioDeviceItem] = []
            self.out_devices: list[AudioDeviceItem] = []
            self._syncing_ui = False

            # Atalho Global (Efeito <-> Voz Normal)
            self.hotkey_spec: str = "f9"
            self._hotkey_lock = threading.Lock()
            self._pressed_keys: set[str] = set()
            self._hotkey_is_down = False
            self._hold_base_bypass: bool | None = None
            self._capturing_hotkey = False
            self._capture_mods: set[str] = set()
            self._kb_listener = None
            self._win32_stop_event = threading.Event()
            self._win32_thread = None
            self._hotkey_enabled_cached: bool = True
            self._hotkey_hold_cached: bool = False

            self.main_container = ctk.CTkFrame(self, fg_color="transparent")
            self._build_layout()
        except Exception as exc:
            messagebox.showerror(self._t("boot_err_title"), self._t("boot_err_ui", err=exc))
            self._quit_app()
            return

        self._splash_target = 0.94
        self._splash_lbl.configure(text=self._t("loading_devices"))
        self.after(20, self._boot_step_devices)

    def _boot_step_devices(self):
        if self._is_quitting:
            return
        try:
            self._restore_saved_ui_prefs()
            self._refresh_devices(reinit_backend=False, initial_load=True)

            saved_preset = self._preset_to_internal(str(self.app_config.get("last_preset", "Normal")))
            if saved_preset in self.builtin_presets:
                self.preset_var.set(self._preset_to_display(saved_preset))
                self._apply_preset(saved_preset, save_cfg=False, preserve_bypass=True)
            elif saved_preset in self.user_presets:
                self.preset_var.set(f"★ {saved_preset}")
                self._apply_preset(saved_preset, save_cfg=False, preserve_bypass=True)
            else:
                self.preset_var.set(self._preset_to_display("Normal"))
                self._apply_preset("Normal", save_cfg=False, preserve_bypass=True)

            if self.app_config.pop("pending_update_restore", False):
                raw_params = self.app_config.pop("current_params", None)
                was_running_upd = bool(self.app_config.pop("was_running_before_update", False))
                if isinstance(raw_params, dict):
                    valid_fields = set(asdict(DSPParams()).keys())
                    filtered = {k: v for k, v in raw_params.items() if k in valid_fields}
                    try:
                        self._load_params_to_ui(DSPParams(**filtered), preserve_bypass=False)
                    except Exception:
                        pass
                self._save_config()
                self.status_lbl.configure(
                    text=self._t("restored_msg"),
                    text_color="#10b981",
                )
                if was_running_upd:
                    self.after(450, self._start_audio)
        except Exception as exc:
            messagebox.showerror(self._t("boot_err_title"), self._t("boot_err_dev", err=exc))
            self._quit_app()
            return

        self._splash_target = 1.0
        self._splash_lbl.configure(text=self._t("ready"))
        self.after(140, self._finish_splash_transition)

    def _finish_splash_transition(self):
        if self._is_quitting:
            return
        self._is_loaded = True
        if self._splash_anim_job is not None:
            try:
                self.after_cancel(self._splash_anim_job)
            except Exception:
                pass
            self._splash_anim_job = None

        try:
            self._splash_frame.destroy()
        except Exception:
            pass

        self.title("VoxCraft Studio")
        self.configure(fg_color=self._c()["window_bg"])
        w, h = 1220, 780
        scr_w = self.winfo_screenwidth()
        scr_h = self.winfo_screenheight()
        x = max(0, (scr_w - w) // 2)
        y = max(0, (scr_h - h) // 2)
        self.resizable(True, True)
        self.minsize(1060, 680)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.main_container.pack(fill="both", expand=True)
        self.update_idletasks()
        self._apply_window_icon()
        self._start_tray_icon()
        self._start_hotkey_listener()
        self.bind("<Map>", self._on_window_map)
        self._schedule_ui_loop()

    def _on_window_map(self, event=None):
        if event is not None and event.widget is not self:
            return
        self._last_ui_hidden = True
        self._last_in_norm = -1.0
        self._last_out_norm = -1.0
        self._last_gate_open = None
        self._last_wave_idle = False
        if self._active_tab_key == "tab_eq":
            self._schedule_eq_redraw()
        if self._ui_loop_job is not None:
            try:
                self.after_cancel(self._ui_loop_job)
            except Exception:
                pass
            self._ui_loop_job = None
        self.after(15, self._schedule_ui_loop)

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
                return
            except Exception:
                pass
        if os.path.exists(ICON_PNG_PATH):
            try:
                self._window_icon_photo = tk.PhotoImage(file=ICON_PNG_PATH)
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

        def _post_ui(fn):
            try:
                if not self._is_quitting:
                    self.after(0, fn)
            except Exception:
                pass

        def on_show(icon, item):
            _post_ui(self._restore_from_tray)

        def on_toggle_audio(icon, item):
            _post_ui(self._toggle_audio)

        def on_toggle_bypass(icon, item):
            def _flip():
                self.bypass_var.set(not self.bypass_var.get())
                self._on_param_change()
            _post_ui(_flip)

        def on_quit(icon, item):
            self._is_quitting = True
            router = getattr(self, "router", None)
            if router is not None:
                try:
                    router.abort_start()
                except Exception:
                    pass
            try:
                self.after(0, self._quit_app)
            except Exception:
                pass

            def _watchdog():
                time.sleep(1.3)
                try:
                    if router is not None:
                        router.stop()
                except Exception:
                    pass
                try:
                    icon.stop()
                except Exception:
                    pass
                try:
                    if _SINGLE_INSTANCE is not None:
                        _SINGLE_INSTANCE.release()
                except Exception:
                    pass
                os._exit(0)

            threading.Thread(target=_watchdog, daemon=True).start()

        menu = pystray.Menu(
            pystray.MenuItem(self._t("tray_open"), on_show, default=True),
            pystray.MenuItem(
                lambda item: self._t("stop_audio") if self.router.running else self._t("start_audio"),
                on_toggle_audio,
            ),
            pystray.MenuItem(
                self._t("original_voice_bypass"),
                on_toggle_bypass,
                checked=lambda item: bool(self.bypass_var.get()),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._t("tray_quit"), on_quit),
        )

        self._tray_icon = pystray.Icon("voxcraft", pil_img, "VoxCraft Studio", menu)
        self._tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
        self._tray_thread.start()

    def _restart_tray_icon(self):
        old_icon = self._tray_icon
        self._tray_icon = None
        if old_icon is not None:
            threading.Thread(target=lambda: old_icon.stop(), daemon=True).start()
        self._start_tray_icon()

    def _restore_from_tray(self):
        if self._is_quitting:
            return
        try:
            self.deiconify()
            self.state("normal")
            self.lift()
            self.attributes("-topmost", True)
            self.after(70, lambda: self.winfo_exists() and self.attributes("-topmost", False))
            self.focus_force()
        except Exception:
            pass
        self._on_window_map()

    def _minimize_to_tray(self):
        self.withdraw()
        if self._tray_icon is not None:
            try:
                self._tray_icon.notify(
                    self._t("tray_bg"),
                    "VoxCraft Studio",
                )
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Construção da Interface
    # ------------------------------------------------------------------ #
    def _build_layout(self):
        root = getattr(self, "main_container", self)
        th = self._c()
        self._i18n_hooks = []
        self._theme_hooks = []
        self._transparent_containers = [root]
        self._tab_frames = {}
        self._tab_buttons = {}
        self._active_tab_key = "tab_pitch"

        # Barra Superior
        topbar = self._card(root, role="panel", height=62, corner_radius=14)
        topbar.pack(fill="x", padx=14, pady=(12, 8))
        topbar.pack_propagate(False)

        title_box = ctk.CTkFrame(topbar, fg_color="transparent")
        title_box.pack(side="left", padx=(16, 14))
        self._lbl(title_box, "VoxCraft Studio", font_key="brand", color_role="accent", is_key=False).pack(anchor="w")

        # Controles de Preset no Topo
        preset_box = ctk.CTkFrame(topbar, fg_color="transparent")
        preset_box.pack(side="left", padx=6)
        self._lbl(preset_box, "preset", font_key="sm", color_role="text_muted").pack(side="left", padx=(0, 8))

        self.preset_var = ctk.StringVar(value=self._preset_to_display("Normal"))
        self.preset_menu = self._optmenu(
            preset_box,
            variable=self.preset_var,
            values=self._all_preset_names(),
            width=210,
            height=32,
            corner_radius=8,
            command=self._on_preset_selected,
        )
        self.preset_menu.pack(side="left", padx=3)

        self._btn(
            preset_box,
            "save",
            self._save_custom_preset,
            hover_override="#2563eb",
            width=66,
            height=32,
            corner_radius=8,
        ).pack(side="left", padx=3)
        self._btn(
            preset_box,
            "delete",
            self._delete_custom_preset,
            hover_override="#dc2626",
            width=64,
            height=32,
            corner_radius=8,
        ).pack(side="left", padx=3)

        # Botões da Direita
        right_top = ctk.CTkFrame(topbar, fg_color="transparent")
        right_top.pack(side="right", padx=12)

        self.settings_btn = self._btn(
            right_top,
            "settings",
            self._open_settings_dialog,
            width=102,
            height=32,
            corner_radius=8,
        )
        self.settings_btn.pack(side="left", padx=3)

        self.update_btn = self._btn(
            right_top,
            "update",
            self._start_app_update,
            hover_override="#2563eb",
            width=82,
            height=32,
            corner_radius=8,
        )
        self.update_btn.pack(side="left", padx=3)

        self._btn(
            right_top,
            "discord",
            self._open_discord_guide,
            width=72,
            height=32,
            corner_radius=8,
        ).pack(side="left", padx=3)

        self.bypass_var = ctk.BooleanVar(value=False)
        self.bypass_btn = self._switch(
            right_top,
            "original_voice",
            self.bypass_var,
            self._on_param_change,
            progress_color="#f59e0b",
        )
        self.bypass_btn.pack(side="left", padx=(8, 8))

        self.power_btn = ctk.CTkButton(
            right_top,
            text=self._t("start_audio"),
            width=128,
            height=36,
            corner_radius=9,
            font=self._fonts["md_b"],
            fg_color="#059669",
            hover_color="#10b981",
            text_color="#ffffff",
            command=self._toggle_audio,
        )
        self.power_btn.pack(side="left", padx=2)
        self._reg_i18n(
            lambda: self.power_btn.configure(text=self._t("stop_audio" if self.router.running else "start_audio"))
        )

        # Corpo Principal: Sidebar (Esquerda) + Workbench (Direita)
        body = ctk.CTkFrame(root, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self._transparent_containers.append(body)

        self._build_sidebar(body)
        self._build_workbench(body)

    def _build_sidebar(self, parent):
        th = self._c()
        side = self._scroll(parent, role="panel", width=316, corner_radius=14)
        side.pack(side="left", fill="y", padx=(0, 10))

        # Card: Roteamento
        route_card = self._card(side, role="card", corner_radius=12)
        route_card.pack(fill="x", padx=8, pady=(8, 6))

        self._lbl(route_card, "audio_section", font_key="lg_b", color_role="text_primary").pack(
            anchor="w", padx=12, pady=(10, 6)
        )
        self._lbl(route_card, "microphone", font_key="sm", color_role="text_muted").pack(anchor="w", padx=12)
        self.in_dev_var = ctk.StringVar()
        self.in_dev_menu = self._optmenu(
            route_card,
            variable=self.in_dev_var,
            values=[""],
            width=276,
            height=30,
            corner_radius=8,
            command=self._on_device_changed,
        )
        self.in_dev_menu.pack(padx=12, pady=(3, 8))

        self._lbl(route_card, "output", font_key="sm", color_role="text_muted").pack(anchor="w", padx=12)
        self.out_dev_var = ctk.StringVar()
        self.out_dev_menu = self._optmenu(
            route_card,
            variable=self.out_dev_var,
            values=[""],
            width=276,
            height=30,
            corner_radius=8,
            command=self._on_device_changed,
        )
        self.out_dev_menu.pack(padx=12, pady=(3, 8))

        self.monitor_var = ctk.BooleanVar(value=False)
        self._switch(route_card, "monitor_voice", self.monitor_var, self._on_routing_pref_changed).pack(
            anchor="w", padx=12, pady=(4, 4)
        )
        self.mon_dev_var = ctk.StringVar()
        self.mon_dev_menu = self._optmenu(
            route_card,
            variable=self.mon_dev_var,
            values=[""],
            width=276,
            height=30,
            corner_radius=8,
            command=self._on_device_changed,
        )
        self.mon_dev_menu.pack(padx=12, pady=(3, 8))

        lat_row = ctk.CTkFrame(route_card, fg_color="transparent")
        lat_row.pack(fill="x", padx=12, pady=(2, 8))
        self._lbl(lat_row, "latency", font_key="sm", color_role="text_muted").pack(side="left")
        self.latency_var = ctk.StringVar(value=self._t("lat_low"))
        self.latency_menu = self._optmenu(
            lat_row,
            variable=self.latency_var,
            values=[self._t("lat_ultra"), self._t("lat_low"), self._t("lat_stable")],
            width=145,
            height=28,
            corner_radius=8,
            command=lambda _: self._on_routing_pref_changed(),
        )
        self.latency_menu.pack(side="right")

        self.minimize_to_tray_var = ctk.BooleanVar(value=pystray is not None)
        self._switch(route_card, "minimize_tray", self.minimize_to_tray_var, self._save_config).pack(
            anchor="w", padx=12, pady=(2, 8)
        )

        self._btn(
            route_card,
            "refresh_devices",
            lambda: self._refresh_devices(reinit_backend=True),
            height=30,
            corner_radius=8,
        ).pack(fill="x", padx=12, pady=(2, 8))

        self.status_lbl = ctk.CTkLabel(
            route_card, text=self._t("stopped"), font=self._fonts["xs"], text_color=th["text_muted"], wraplength=272
        )
        self.status_lbl.pack(anchor="w", padx=12, pady=(0, 10))
        self._reg_i18n(lambda: None if self.router.running else self.status_lbl.configure(text=self._t("stopped")))
        self._reg_theme(
            self.status_lbl,
            lambda t: None if self.router.running else self.status_lbl.configure(text_color=t["text_muted"]),
        )

        # Card: Atalho Global
        hk_card = self._card(side, role="card", corner_radius=12)
        hk_card.pack(fill="x", padx=8, pady=6)

        self._lbl(hk_card, "hotkey_section", font_key="md_b", color_role="text_primary").pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        self.hotkey_en_var = ctk.BooleanVar(value=True)
        self._switch(hk_card, "enable_hotkey", self.hotkey_en_var, self._on_hotkey_setting_changed).pack(
            anchor="w", padx=12, pady=(0, 6)
        )

        hk_row = ctk.CTkFrame(hk_card, fg_color="transparent")
        hk_row.pack(fill="x", padx=12, pady=(0, 6))
        self._lbl(hk_row, "key_label", font_key="sm", color_role="text_muted").pack(side="left")
        self.hotkey_btn = self._btn(
            hk_row,
            "F9",
            self._toggle_hotkey_capture,
            is_key=False,
            font_key="sm_b",
            height=28,
            corner_radius=8,
        )
        self.hotkey_btn.pack(side="left", fill="x", expand=True, padx=(10, 0))

        self.hotkey_hold_var = ctk.BooleanVar(value=False)
        self._switch(hk_card, "hold_key", self.hotkey_hold_var, self._on_hotkey_setting_changed).pack(
            anchor="w", padx=12, pady=(2, 4)
        )

        self.hotkey_hint_lbl = ctk.CTkLabel(
            hk_card,
            text="",
            font=self._fonts["xs"],
            text_color=th["accent"],
            wraplength=265,
            justify="left",
        )
        self.hotkey_hint_lbl.pack(anchor="w", padx=12, pady=(2, 10))

        # Card: Níveis & Osciloscópio
        meter_card = self._card(side, role="card", corner_radius=12)
        meter_card.pack(fill="x", padx=8, pady=6)

        self._lbl(meter_card, "levels_section", font_key="md_b", color_role="text_primary").pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        row_in = ctk.CTkFrame(meter_card, fg_color="transparent")
        row_in.pack(fill="x", padx=12)
        self._lbl(row_in, "input_lbl", font_key="xs", color_role="text_muted", width=55, anchor="w").pack(side="left")
        self.in_bar = ctk.CTkProgressBar(row_in, height=8, fg_color=th["track_bg"], progress_color=th["accent"])
        self.in_bar.set(0)
        self.in_bar.pack(side="left", fill="x", expand=True, padx=6)
        self._reg_theme(self.in_bar, lambda t: self.in_bar.configure(fg_color=t["track_bg"], progress_color=t["accent"]))

        row_out = ctk.CTkFrame(meter_card, fg_color="transparent")
        row_out.pack(fill="x", padx=12, pady=(6, 4))
        self._lbl(row_out, "output_lbl", font_key="xs", color_role="text_muted", width=55, anchor="w").pack(side="left")
        self.out_bar = ctk.CTkProgressBar(row_out, height=8, fg_color=th["track_bg"], progress_color="#10b981")
        self.out_bar.set(0)
        self.out_bar.pack(side="left", fill="x", expand=True, padx=6)
        self._reg_theme(self.out_bar, lambda t: self.out_bar.configure(fg_color=t["track_bg"]))

        self.gate_led = ctk.CTkLabel(
            meter_card, text=self._t("gate_open"), font=self._fonts["xs"], text_color="#10b981"
        )
        self.gate_led.pack(anchor="w", padx=12, pady=(2, 4))
        self._reg_i18n(
            lambda: self.gate_led.configure(text=self._t("gate_open" if self._last_gate_open is not False else "gate_closed"))
        )

        self.wave_canvas = tk.Canvas(
            meter_card, height=64, bg=th["canvas_bg"], highlightthickness=1, highlightbackground=th["canvas_border"]
        )
        self.wave_canvas.pack(fill="x", padx=12, pady=(2, 12))
        self._reg_theme(
            self.wave_canvas,
            lambda t: self.wave_canvas.configure(bg=t["canvas_bg"], highlightbackground=t["canvas_border"]),
        )

        # Card: Dinâmica & Ganho
        dyn_card = self._card(side, role="card", corner_radius=12)
        dyn_card.pack(fill="x", padx=8, pady=(6, 10))
        self._lbl(dyn_card, "dynamics_section", font_key="md_b", color_role="text_primary").pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        self.input_gain_var = self._add_slider(dyn_card, "input_gain", -18.0, 24.0, 0.0, "dB")
        self.gate_en_var = ctk.BooleanVar(value=False)
        self._switch(dyn_card, "noise_gate", self.gate_en_var, self._on_param_change).pack(
            anchor="w", padx=12, pady=(6, 0)
        )
        self.gate_thresh_var = self._add_slider(dyn_card, "gate_thresh", -65.0, -15.0, -42.0, "dB")

        self.comp_en_var = ctk.BooleanVar(value=True)
        self._switch(dyn_card, "compressor", self.comp_en_var, self._on_param_change).pack(
            anchor="w", padx=12, pady=(6, 0)
        )
        self.comp_thresh_var = self._add_slider(dyn_card, "comp_thresh", -36.0, -4.0, -18.0, "dB")
        self.output_gain_var = self._add_slider(dyn_card, "output_vol", -24.0, 24.0, 0.0, "dB")

    def _build_workbench(self, parent):
        th = self._c()
        shell = self._card(parent, role="panel", corner_radius=14)
        shell.pack(side="left", fill="both", expand=True)

        tab_bar = self._card(shell, role="tabbar", corner_radius=10)
        tab_bar.pack(fill="x", padx=12, pady=(10, 4))

        self._tab_content = ctk.CTkFrame(shell, fg_color="transparent")
        self._tab_content.pack(fill="both", expand=True, padx=4, pady=(0, 6))
        self._transparent_containers.append(self._tab_content)

        specs = [
            ("tab_pitch", self._build_pitch_tab),
            ("tab_eq", self._build_eq_tab),
            ("tab_mod", self._build_mod_tab),
            ("tab_fx", self._build_fx_tab),
            ("tab_space", self._build_space_tab),
            ("tab_mixer", self._build_mixer_tab),
        ]
        for tk_key, builder in specs:
            btn = ctk.CTkButton(
                tab_bar,
                text=self._t(tk_key),
                height=30,
                corner_radius=8,
                font=self._fonts["sm_b"],
                fg_color=th["tab_sel"] if tk_key == self._active_tab_key else th["tab_bg"],
                hover_color=th["tab_sel_hover"] if tk_key == self._active_tab_key else th["tab_unsel_hover"],
                text_color=th["seg_text"],
                command=lambda k=tk_key: self._select_tab(k),
            )
            btn.pack(side="left", fill="x", expand=True, padx=3, pady=4)
            self._tab_buttons[tk_key] = btn
            self._reg_i18n(lambda b=btn, k=tk_key: b.configure(text=self._t(k)))
            self._reg_theme(btn, lambda _t, k=tk_key: self._style_tab_button(k))

            frame = ctk.CTkFrame(self._tab_content, fg_color="transparent")
            self._tab_frames[tk_key] = frame
            self._transparent_containers.append(frame)
            builder(frame)

        self._tab_frames[self._active_tab_key].pack(fill="both", expand=True)

    def _style_tab_button(self, tab_key: str):
        btn = self._tab_buttons.get(tab_key)
        if btn is None:
            return
        th = self._c()
        is_sel = tab_key == self._active_tab_key
        btn.configure(
            fg_color=th["tab_sel"] if is_sel else th["tab_bg"],
            hover_color=th["tab_sel_hover"] if is_sel else th["tab_unsel_hover"],
            text_color=th["seg_text"],
        )

    def _select_tab(self, tab_key: str):
        if tab_key == self._active_tab_key or tab_key not in self._tab_frames:
            return
        old_key = self._active_tab_key
        self._tab_frames[old_key].pack_forget()
        self._active_tab_key = tab_key
        self._tab_frames[tab_key].pack(fill="both", expand=True)
        self._style_tab_button(old_key)
        self._style_tab_button(tab_key)
        if tab_key == "tab_eq":
            self._schedule_eq_redraw()

    def _build_pitch_tab(self, tab):
        scroll = self._scroll(tab)
        scroll.pack(fill="both", expand=True)

        # Card: Alterar Tom
        card1 = self._card(scroll, role="card", corner_radius=12)
        card1.pack(fill="x", padx=10, pady=8)

        hdr1 = ctk.CTkFrame(card1, fg_color="transparent")
        hdr1.pack(fill="x", padx=16, pady=(12, 8))
        self.pitch_en_var = ctk.BooleanVar(value=False)
        self._switch(hdr1, "pitch_shift", self.pitch_en_var, self._on_param_change, font_key="h3_b").pack(side="left")

        self.pitch_st_var = self._add_slider(card1, "semitones", -12.0, 12.0, 0.0, "st", step=0.1)
        self.pitch_cents_var = self._add_slider(card1, "fine_tune", -100.0, 100.0, 0.0, "ct", step=1.0)
        self.pitch_mix_var = self._add_slider(card1, "mix", 0.0, 100.0, 100.0, "%", step=1.0)

        qrow = ctk.CTkFrame(card1, fg_color="transparent")
        qrow.pack(fill="x", padx=14, pady=(6, 14))
        for label, st_val in [
            ("-12 st", -12.0),
            ("-5 st", -5.0),
            ("-2 st", -2.0),
            ("0 st", 0.0),
            ("+4 st", 4.0),
            ("+7 st", 7.0),
            ("+12 st", 12.0),
        ]:
            self._btn(
                qrow,
                label,
                lambda v=st_val: self._quick_pitch(v),
                is_key=False,
                bordered=False,
                width=74,
                height=28,
                corner_radius=8,
            ).pack(side="left", padx=4)

        # Card: Frequency Shifter
        card2 = self._card(scroll, role="card", corner_radius=12)
        card2.pack(fill="x", padx=10, pady=8)

        hdr2 = ctk.CTkFrame(card2, fg_color="transparent")
        hdr2.pack(fill="x", padx=16, pady=(12, 8))
        self.fshift_en_var = ctk.BooleanVar(value=False)
        self._switch(hdr2, "freq_shift", self.fshift_en_var, self._on_param_change, font_key="h3_b").pack(side="left")

        self.fshift_hz_var = self._add_slider(card2, "shift_hz", -500.0, 500.0, 0.0, "Hz", step=1.0)
        self.fshift_mix_var = self._add_slider(card2, "mix", 0.0, 100.0, 100.0, "%", step=1.0)

        qrow2 = ctk.CTkFrame(card2, fg_color="transparent")
        qrow2.pack(fill="x", padx=14, pady=(6, 14))
        for label, hz_val in [("-120 Hz", -120.0), ("-30 Hz", -30.0), ("0 Hz", 0.0), ("+50 Hz", 50.0), ("+180 Hz", 180.0)]:
            self._btn(
                qrow2,
                label,
                lambda v=hz_val: self._quick_fshift(v),
                is_key=False,
                bordered=False,
                width=82,
                height=28,
                corner_radius=8,
            ).pack(side="left", padx=4)

        # Card: Vocoder
        card3 = self._card(scroll, role="card", corner_radius=12)
        card3.pack(fill="x", padx=10, pady=8)

        hdr3 = ctk.CTkFrame(card3, fg_color="transparent")
        hdr3.pack(fill="x", padx=16, pady=(12, 8))
        self.voc_en_var = ctk.BooleanVar(value=False)
        self._switch(hdr3, "vocoder", self.voc_en_var, self._on_param_change, font_key="h3_b").pack(side="left")

        voc_row = ctk.CTkFrame(card3, fg_color="transparent")
        voc_row.pack(fill="x", padx=16, pady=(0, 8))
        self._lbl(voc_row, "carrier", font_key="sm", color_role="text_muted").pack(side="left", padx=(0, 12))
        self.voc_carrier_var = ctk.StringVar(value=self._t("wave_saw"))
        self.voc_carrier_menu = self._optmenu(
            voc_row,
            variable=self.voc_carrier_var,
            values=[self._t("wave_saw"), self._t("wave_chord"), self._t("wave_sq"), self._t("wave_whisper")],
            corner_radius=8,
            command=lambda _: self._on_param_change(),
        )
        self.voc_carrier_menu.pack(side="left")

        self.voc_freq_var = self._add_slider(card3, "base_freq", 55.0, 300.0, 110.0, "Hz", step=1.0)
        self.voc_smooth_var = self._add_slider(card3, "smoothness", 10.0, 95.0, 45.0, "%", step=1.0)
        self.voc_mix_var = self._add_slider(card3, "mix", 0.0, 100.0, 85.0, "%", step=1.0)

    def _build_eq_tab(self, tab):
        th = self._c()
        top = self._card(tab, role="card", corner_radius=12)
        top.pack(fill="x", padx=10, pady=8)

        hdr = ctk.CTkFrame(top, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(10, 6))
        self.eq_en_var = ctk.BooleanVar(value=True)
        self._switch(hdr, "equalizer", self.eq_en_var, self._on_param_change, font_key="h3_b").pack(side="left")

        self._btn(
            hdr,
            "reset_eq",
            self._reset_eq,
            bordered=False,
            width=96,
            height=28,
            corner_radius=8,
        ).pack(side="right")

        self.eq_canvas = tk.Canvas(
            top, height=190, bg=th["canvas_bg"], highlightthickness=1, highlightbackground=th["canvas_border"]
        )
        self.eq_canvas.pack(fill="x", padx=16, pady=(4, 14))
        self.eq_canvas.bind("<Configure>", lambda _e: self._schedule_eq_redraw())
        self._reg_theme(
            self.eq_canvas,
            lambda t: self.eq_canvas.configure(bg=t["canvas_bg"], highlightbackground=t["canvas_border"]),
        )

        bot = self._card(tab, role="card", corner_radius=12)
        bot.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        cuts = ctk.CTkFrame(bot, fg_color="transparent")
        cuts.pack(fill="x", padx=14, pady=(12, 6))

        hpf_box = self._card(cuts, role="subcard", corner_radius=10)
        hpf_box.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.hpf_en_var = ctk.BooleanVar(value=True)
        self._switch(hpf_box, "hpf", self.hpf_en_var, self._on_param_change).pack(anchor="w", padx=12, pady=(8, 0))
        self.hpf_hz_var = self._add_slider(hpf_box, "frequency", 20.0, 1000.0, 80.0, "Hz", step=5.0)

        lpf_box = self._card(cuts, role="subcard", corner_radius=10)
        lpf_box.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.lpf_en_var = ctk.BooleanVar(value=False)
        self._switch(lpf_box, "lpf", self.lpf_en_var, self._on_param_change).pack(anchor="w", padx=12, pady=(8, 0))
        self.lpf_hz_var = self._add_slider(lpf_box, "frequency", 1200.0, 18000.0, 12000.0, "Hz", step=100.0)

        bands_frame = ctk.CTkFrame(bot, fg_color="transparent")
        bands_frame.pack(fill="both", expand=True, padx=14, pady=8)

        self.eq_b1_var = self._add_vertical_eq_band(bands_frame, "eq_b1")
        self.eq_b2_var = self._add_vertical_eq_band(bands_frame, "eq_b2")
        self.eq_b3_var = self._add_vertical_eq_band(bands_frame, "eq_b3")
        self.eq_b4_var = self._add_vertical_eq_band(bands_frame, "eq_b4")
        self.eq_b5_var = self._add_vertical_eq_band(bands_frame, "eq_b5")

    def _build_mod_tab(self, tab):
        scroll = self._scroll(tab)
        scroll.pack(fill="both", expand=True)

        c1 = self._card(scroll, role="card", corner_radius=12)
        c1.pack(fill="x", padx=10, pady=8)
        self.phaser_en_var = ctk.BooleanVar(value=False)
        self._switch(
            c1, "Phaser", self.phaser_en_var, self._on_param_change, font_key="h3_b", is_key=False
        ).pack(anchor="w", padx=16, pady=(12, 8))
        self.phaser_stages_var = self._add_slider(c1, "stages", 2.0, 12.0, 6.0, "x", step=2.0)
        self.phaser_freq_var = self._add_slider(c1, "lfo_speed", 0.1, 6.0, 0.8, "Hz", step=0.1)
        self.phaser_depth_var = self._add_slider(c1, "depth", 0.0, 100.0, 70.0, "%", step=1.0)
        self.phaser_fb_var = self._add_slider(c1, "feedback", -90.0, 90.0, 45.0, "%", step=1.0)
        self.phaser_mix_var = self._add_slider(c1, "mix", 0.0, 100.0, 60.0, "%", step=1.0)

        c2 = self._card(scroll, role="card", corner_radius=12)
        c2.pack(fill="x", padx=10, pady=8)
        self.wah_en_var = ctk.BooleanVar(value=False)
        self._switch(
            c2, "Wah-Wah", self.wah_en_var, self._on_param_change, font_key="h3_b", is_key=False
        ).pack(anchor="w", padx=16, pady=(12, 8))
        self.wah_freq_var = self._add_slider(c2, "lfo_freq", 0.2, 8.0, 1.5, "Hz", step=0.1)
        self.wah_depth_var = self._add_slider(c2, "depth", 0.0, 100.0, 75.0, "%", step=1.0)
        self.wah_res_var = self._add_slider(c2, "resonance", 0.5, 8.0, 2.8, "x", step=0.1)
        self.wah_mix_var = self._add_slider(c2, "mix", 0.0, 100.0, 75.0, "%", step=1.0)

        c3 = self._card(scroll, role="card", corner_radius=12)
        c3.pack(fill="x", padx=10, pady=8)
        self.chorus_en_var = ctk.BooleanVar(value=False)
        self._switch(c3, "chorus_flanger", self.chorus_en_var, self._on_param_change, font_key="h3_b").pack(
            anchor="w", padx=16, pady=(12, 8)
        )
        self.chorus_rate_var = self._add_slider(c3, "lfo_speed", 0.1, 8.0, 1.2, "Hz", step=0.1)
        self.chorus_delay_var = self._add_slider(c3, "base_delay", 1.5, 35.0, 14.0, "ms", step=0.5)
        self.chorus_depth_var = self._add_slider(c3, "modulation", 0.5, 15.0, 4.5, "ms", step=0.5)
        self.chorus_fb_var = self._add_slider(c3, "feedback", 0.0, 85.0, 25.0, "%", step=1.0)
        self.chorus_mix_var = self._add_slider(c3, "mix", 0.0, 100.0, 50.0, "%", step=1.0)

        c4 = self._card(scroll, role="card", corner_radius=12)
        c4.pack(fill="x", padx=10, pady=8)
        self.trem_en_var = ctk.BooleanVar(value=False)
        self._switch(
            c4, "Tremolo", self.trem_en_var, self._on_param_change, font_key="h3_b", is_key=False
        ).pack(anchor="w", padx=16, pady=(12, 8))
        trem_row = ctk.CTkFrame(c4, fg_color="transparent")
        trem_row.pack(fill="x", padx=16, pady=(0, 8))
        self._lbl(trem_row, "waveform", font_key="sm", color_role="text_muted").pack(side="left", padx=(0, 12))
        self.trem_wave_var = ctk.StringVar(value=self._t("wave_sine"))
        self.trem_wave_menu = self._optmenu(
            trem_row,
            variable=self.trem_wave_var,
            values=[self._t("wave_sine"), self._t("wave_tri"), self._t("wave_sq"), self._t("wave_saw")],
            corner_radius=8,
            command=lambda _: self._on_param_change(),
        )
        self.trem_wave_menu.pack(side="left")
        self.trem_freq_var = self._add_slider(c4, "frequency", 0.5, 25.0, 6.0, "Hz", step=0.5)
        self.trem_depth_var = self._add_slider(c4, "intensity", 0.0, 100.0, 65.0, "%", step=1.0)

    def _build_fx_tab(self, tab):
        scroll = self._scroll(tab)
        scroll.pack(fill="both", expand=True)

        c1 = self._card(scroll, role="card", corner_radius=12)
        c1.pack(fill="x", padx=10, pady=8)
        self.ring_en_var = ctk.BooleanVar(value=False)
        self._switch(c1, "ring_mod", self.ring_en_var, self._on_param_change, font_key="h3_b").pack(
            anchor="w", padx=16, pady=(12, 8)
        )

        wave_row = ctk.CTkFrame(c1, fg_color="transparent")
        wave_row.pack(fill="x", padx=16, pady=(0, 8))
        self._lbl(wave_row, "waveform", font_key="sm", color_role="text_muted").pack(side="left", padx=(0, 12))
        self.ring_wave_var = ctk.StringVar(value=self._t("wave_sine"))
        self.ring_wave_menu = self._optmenu(
            wave_row,
            variable=self.ring_wave_var,
            values=[self._t("wave_sine"), self._t("wave_sq"), self._t("wave_tri")],
            corner_radius=8,
            command=lambda _: self._on_param_change(),
        )
        self.ring_wave_menu.pack(side="left")

        self.ring_freq_var = self._add_slider(c1, "carrier_freq", 5.0, 400.0, 60.0, "Hz", step=1.0)
        self.ring_mix_var = self._add_slider(c1, "mix", 0.0, 100.0, 70.0, "%", step=1.0)

        c2 = self._card(scroll, role="card", corner_radius=12)
        c2.pack(fill="x", padx=10, pady=8)
        self.dist_en_var = ctk.BooleanVar(value=False)
        self._switch(c2, "dist_bit", self.dist_en_var, self._on_param_change, font_key="h3_b").pack(
            anchor="w", padx=16, pady=(12, 8)
        )

        self.dist_drive_var = self._add_slider(c2, "drive_sat", 1.0, 25.0, 3.0, "x", step=0.2)
        self.dist_bits_var = self._add_slider(c2, "resolution", 4.0, 16.0, 16.0, "bits", step=1.0)
        self.dist_down_var = self._add_slider(c2, "downsample", 1.0, 16.0, 1.0, "x", step=1.0)
        self.dist_mix_var = self._add_slider(c2, "mix", 0.0, 100.0, 70.0, "%", step=1.0)

    def _build_space_tab(self, tab):
        scroll = self._scroll(tab)
        scroll.pack(fill="both", expand=True)

        c1 = self._card(scroll, role="card", corner_radius=12)
        c1.pack(fill="x", padx=10, pady=8)
        self.echo_en_var = ctk.BooleanVar(value=False)
        self._switch(c1, "echo_delay", self.echo_en_var, self._on_param_change, font_key="h3_b").pack(
            anchor="w", padx=16, pady=(12, 8)
        )

        self.echo_delay_var = self._add_slider(c1, "delay", 10.0, 700.0, 220.0, "ms", step=2.0)
        self.echo_fb_var = self._add_slider(c1, "feedback", 0.0, 85.0, 35.0, "%", step=1.0)
        self.echo_mix_var = self._add_slider(c1, "echo_vol", 0.0, 100.0, 35.0, "%", step=1.0)

        c2 = self._card(scroll, role="card", corner_radius=12)
        c2.pack(fill="x", padx=10, pady=8)
        self.rev_en_var = ctk.BooleanVar(value=False)
        self._switch(c2, "reverb", self.rev_en_var, self._on_param_change, font_key="h3_b").pack(
            anchor="w", padx=16, pady=(12, 8)
        )
        self.rev_room_var = self._add_slider(c2, "room_size", 0.0, 100.0, 60.0, "%", step=1.0)
        self.rev_damp_var = self._add_slider(c2, "damping", 5.0, 92.0, 45.0, "%", step=1.0)
        self.rev_mix_var = self._add_slider(c2, "mix", 0.0, 100.0, 30.0, "%", step=1.0)

    def _build_mixer_tab(self, tab):
        box = self._scroll(tab)
        box.pack(fill="both", expand=True, padx=6, pady=6)

        self._lbl(box, "effects_chain", font_key="h3_b", color_role="text_primary").pack(
            anchor="w", padx=12, pady=(8, 8)
        )

        modules = [
            ("noise_gate", True, self.gate_en_var),
            ("compressor", True, self.comp_en_var),
            ("pitch_shift", True, self.pitch_en_var),
            ("freq_shift", True, self.fshift_en_var),
            ("vocoder", True, self.voc_en_var),
            ("equalizer", True, self.eq_en_var),
            ("Phaser", False, self.phaser_en_var),
            ("Wah-Wah", False, self.wah_en_var),
            ("chorus_flanger", True, self.chorus_en_var),
            ("Tremolo", False, self.trem_en_var),
            ("ring_mod_short", True, self.ring_en_var),
            ("dist_bit", True, self.dist_en_var),
            ("echo_delay", True, self.echo_en_var),
            ("reverb", True, self.rev_en_var),
        ]

        grid = ctk.CTkFrame(box, fg_color="transparent")
        grid.pack(fill="x", padx=8, pady=4)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        for idx, (label_key, is_k, var) in enumerate(modules):
            card = self._card(grid, role="card", corner_radius=10)
            card.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=6, pady=6)
            self._switch(card, label_key, var, self._on_param_change, font_key="md", is_key=is_k).pack(
                anchor="w", padx=14, pady=12
            )

        self._btn(
            box,
            "reset_effects",
            lambda: self._apply_preset("Normal"),
            hover_override="#dc2626",
            corner_radius=8,
            height=34,
        ).pack(pady=16)

    # ------------------------------------------------------------------ #
    # Helpers de Widgets
    # ------------------------------------------------------------------ #
    def _add_slider(self, parent, label_key: str, vmin: float, vmax: float, default: float, unit: str, step: float = 0.5):
        th = self._c()
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=14, pady=4)

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x")
        self._lbl(top, label_key, font_key="sm", color_role="text_body").pack(side="left")
        val_lbl = self._lbl(top, f"{default:.1f} {unit}", font_key="sm_b", color_role="accent", is_key=False)
        val_lbl.pack(side="right")

        var = ctk.DoubleVar(value=default)
        steps = max(1, int(round((vmax - vmin) / step)))

        def on_slide(v):
            if unit in ("Hz", "ms", "%", "bits", "x", "ct") and step >= 1.0:
                val_lbl.configure(text=f"{int(round(float(v)))} {unit}")
            else:
                val_lbl.configure(text=f"{float(v):.1f} {unit}")
            self._on_param_change()

        slider = ctk.CTkSlider(
            frame,
            from_=vmin,
            to=vmax,
            number_of_steps=steps,
            height=16,
            fg_color=th["track_bg"],
            progress_color=th["accent_deep"],
            button_color=th["accent"],
            button_hover_color=th["accent_hover"],
            variable=var,
            command=on_slide,
        )
        slider.pack(fill="x", pady=(2, 4))
        self._reg_theme(
            slider,
            lambda t, s=slider: s.configure(
                fg_color=t["track_bg"],
                progress_color=t["accent_deep"],
                button_color=t["accent"],
                button_hover_color=t["accent_hover"],
            ),
        )
        var._val_lbl = val_lbl
        var._unit = unit
        var._step = step
        return var

    def _add_vertical_eq_band(self, parent, title_key: str):
        th = self._c()
        col = self._card(parent, role="subcard", corner_radius=10)
        col.pack(side="left", fill="both", expand=True, padx=4)

        val_lbl = self._lbl(col, "0.0 dB", font_key="xs_b", color_role="accent", is_key=False)
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
            fg_color=th["track_bg"],
            progress_color=th["accent_deep"],
            button_color=th["accent"],
            button_hover_color=th["accent_hover"],
            variable=var,
            command=on_slide,
        )
        slider.pack(pady=4)
        self._reg_theme(
            slider,
            lambda t, s=slider: s.configure(
                fg_color=t["track_bg"],
                progress_color=t["accent_deep"],
                button_color=t["accent"],
                button_hover_color=t["accent_hover"],
            ),
        )

        self._lbl(col, title_key, font_key="xs", color_role="text_muted", justify="center").pack(pady=(2, 8))
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
            vocoder_carrier=self._wave_to_internal(str(self.voc_carrier_var.get())),
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
            tremolo_waveform=self._wave_to_internal(str(self.trem_wave_var.get())),
            tremolo_depth=float(self.trem_depth_var.get()) / 100.0,
            ring_enabled=bool(self.ring_en_var.get()),
            ring_freq_hz=float(self.ring_freq_var.get()),
            ring_waveform=self._wave_to_internal(str(self.ring_wave_var.get())),
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
        self._update_hotkey_hint()
        eq_sig = (
            p.eq_enabled,
            p.eq_hpf_enabled,
            round(p.eq_hpf_hz, 1),
            p.eq_lpf_enabled,
            round(p.eq_lpf_hz, 1),
            round(p.eq_band1_db, 2),
            round(p.eq_band2_db, 2),
            round(p.eq_band3_db, 2),
            round(p.eq_band4_db, 2),
            round(p.eq_band5_db, 2),
        )
        if eq_sig != self._last_eq_sig:
            self._last_eq_sig = eq_sig
            self._schedule_eq_redraw()

    def _load_params_to_ui(self, p: DSPParams, preserve_bypass: bool = False):
        self._syncing_ui = True
        try:
            if not preserve_bypass:
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
            self.voc_carrier_var.set(self._wave_to_display(p.vocoder_carrier))
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
            self.trem_wave_var.set(self._wave_to_display(p.tremolo_waveform))
            self.trem_depth_var.set(p.tremolo_depth * 100.0)

            self.ring_en_var.set(p.ring_enabled)
            self.ring_freq_var.set(p.ring_freq_hz)
            self.ring_wave_var.set(self._wave_to_display(p.ring_waveform))
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
        names = [self._preset_to_display(k) for k in self.builtin_presets.keys()]
        for u in self.user_presets.keys():
            names.append(f"★ {u}")
        return names

    def _on_preset_selected(self, choice: str):
        clean = choice[2:] if choice.startswith("★ ") else self._preset_to_internal(choice)
        self._apply_preset(clean)

    def _apply_preset(self, name: str, save_cfg: bool = True, preserve_bypass: bool = True):
        canonical = self._preset_to_internal(name)
        if canonical in self.builtin_presets:
            self._load_params_to_ui(self.builtin_presets[canonical].copy(), preserve_bypass=preserve_bypass)
            if save_cfg:
                self._save_config()
        elif name in self.user_presets:
            self._load_params_to_ui(self.user_presets[name].copy(), preserve_bypass=preserve_bypass)
            if save_cfg:
                self._save_config()

    def _save_custom_preset(self):
        name = simpledialog.askstring(self._t("save_preset_title"), self._t("save_preset_prompt"), parent=self)
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
            messagebox.showinfo(self._t("warn_title"), self._t("delete_preset_warn"))
            return
        name = sel[2:]
        if name in self.user_presets:
            del self.user_presets[name]
            save_user_presets(self.user_presets)
            self.preset_menu.configure(values=self._all_preset_names())
            self.preset_var.set(self._preset_to_display("Normal"))
            self._apply_preset("Normal")

    # ------------------------------------------------------------------ #
    # Persistência de Entradas, Saídas e Preferências
    # ------------------------------------------------------------------ #
    def _restore_saved_ui_prefs(self):
        cfg = self.app_config or {}
        if "bypass_enabled" in cfg:
            self.bypass_var.set(bool(cfg["bypass_enabled"]))
        if "monitor_enabled" in cfg:
            self.monitor_var.set(bool(cfg["monitor_enabled"]))
        saved_lat = str(cfg.get("latency", ""))
        if any(tok in saved_lat for tok in ("256", "512", "1024")):
            self.latency_var.set(self._latency_to_display(saved_lat))
        if "minimize_to_tray" in cfg and pystray is not None:
            self.minimize_to_tray_var.set(bool(cfg["minimize_to_tray"]))
        if "hotkey_enabled" in cfg:
            self.hotkey_en_var.set(bool(cfg["hotkey_enabled"]))
        if isinstance(cfg.get("hotkey_spec"), str) and cfg["hotkey_spec"].strip():
            self.hotkey_spec = cfg["hotkey_spec"].strip().lower()
        if "hotkey_hold_mode" in cfg:
            self.hotkey_hold_var.set(bool(cfg["hotkey_hold_mode"]))
        self.hotkey_btn.configure(text=self._format_hotkey_label(self.hotkey_spec))
        self._sync_hotkey_cache()
        self._update_hotkey_hint()

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
        clean_preset = preset_choice[2:] if preset_choice.startswith("★ ") else self._preset_to_internal(preset_choice)
        self.app_config["last_preset"] = clean_preset
        self.app_config["theme"] = self.ui_theme
        self.app_config["language"] = self.ui_lang
        self.app_config["bypass_enabled"] = bool(self.bypass_var.get())
        self.app_config["monitor_enabled"] = bool(self.monitor_var.get())
        lat_txt = str(self.latency_var.get())
        if "256" in lat_txt:
            self.app_config["latency"] = "Ultra (256)"
        elif "1024" in lat_txt:
            self.app_config["latency"] = "Estável (1024)"
        else:
            self.app_config["latency"] = "Baixa (512)"
        self.app_config["minimize_to_tray"] = bool(self.minimize_to_tray_var.get())
        self.app_config["hotkey_enabled"] = bool(self.hotkey_en_var.get())
        self.app_config["hotkey_spec"] = str(self.hotkey_spec)
        self.app_config["hotkey_hold_mode"] = bool(self.hotkey_hold_var.get())
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

    def _apply_device_list_to_ui(
        self,
        in_devices: list[AudioDeviceItem],
        out_devices: list[AudioDeviceItem],
        prev_in: AudioDeviceItem | None,
        prev_out: AudioDeviceItem | None,
        prev_mon: AudioDeviceItem | None,
        was_running: bool,
        initial_load: bool,
    ):
        self.in_devices, self.out_devices = in_devices, out_devices

        in_labels = [d.label for d in self.in_devices] or [self._t("no_mic")]
        out_labels = [d.label for d in self.out_devices] or [self._t("no_out")]

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
                text=self._t("devices_updated", ins=len(self.in_devices), outs=len(self.out_devices)),
                text_color=self._c()["accent"],
            )

    def _refresh_devices(self, reinit_backend: bool = True, initial_load: bool = False):
        was_running = self.router.running
        prev_in = self._selected_device_item(self.in_dev_var.get(), self.in_devices)
        prev_out = self._selected_device_item(self.out_dev_var.get(), self.out_devices)
        prev_mon = self._selected_device_item(self.mon_dev_var.get(), self.out_devices)

        if not reinit_backend:
            in_devs, out_devs = AudioRouter.list_devices()
            self._apply_device_list_to_ui(in_devs, out_devs, prev_in, prev_out, prev_mon, was_running, initial_load)
            return

        self._audio_op_seq += 1
        op_seq = self._audio_op_seq
        self.router.abort_start()
        self.status_lbl.configure(text=self._t("refreshing_devices"), text_color=self._c()["accent"])
        self.power_btn.configure(text=self._t("start_audio"), fg_color="#059669", hover_color="#10b981")

        def _worker():
            with self._audio_worker_lock:
                if was_running or self.router.running:
                    self.router.stop()
                in_devs, out_devs = AudioRouter.refresh_backend()

            def _done():
                if self._is_quitting or op_seq != self._audio_op_seq:
                    return
                self._apply_device_list_to_ui(in_devs, out_devs, prev_in, prev_out, prev_mon, was_running, initial_load)

            try:
                self.after(0, _done)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

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

    def _stop_audio_async(self):
        self._audio_op_seq += 1
        self.router.abort_start()
        self.power_btn.configure(text=self._t("start_audio"), fg_color="#059669", hover_color="#10b981")
        self.status_lbl.configure(text=self._t("stopped"), text_color=self._c()["text_muted"])

        def _worker():
            with self._audio_worker_lock:
                self.router.stop()

        threading.Thread(target=_worker, daemon=True).start()

    def _toggle_audio(self):
        if self.router.running:
            self._stop_audio_async()
        else:
            self._start_audio()

    def _start_audio(self):
        in_idx = self._selected_device_index(self.in_dev_var.get(), self.in_devices)
        out_idx = self._selected_device_index(self.out_dev_var.get(), self.out_devices)
        mon_idx = self._selected_device_index(self.mon_dev_var.get(), self.out_devices)

        if in_idx is None or out_idx is None:
            messagebox.showerror(self._t("err_title"), self._t("err_invalid_devs"))
            return

        self._audio_op_seq += 1
        op_seq = self._audio_op_seq
        blocksize = self._get_blocksize()
        mon_en = bool(self.monitor_var.get())

        self.router.abort_start()
        self.status_lbl.configure(text=self._t("connecting_audio"), text_color=self._c()["accent"])

        def _worker():
            ok, msg = False, "Interrompido"
            with self._audio_worker_lock:
                if self._is_quitting or op_seq != self._audio_op_seq:
                    return
                try:
                    ok, msg = self.router.start(
                        in_idx=in_idx,
                        out_idx=out_idx,
                        blocksize=blocksize,
                        monitor_enabled=mon_en,
                        monitor_idx=mon_idx,
                    )
                except Exception as exc:
                    ok, msg = False, str(exc)

            def _done():
                if self._is_quitting or op_seq != self._audio_op_seq:
                    if ok:
                        threading.Thread(target=self.router.stop, daemon=True).start()
                    return
                if ok:
                    self.power_btn.configure(text=self._t("stop_audio"), fg_color="#dc2626", hover_color="#ef4444")
                    self.status_lbl.configure(text=msg, text_color="#10b981")
                    self._schedule_eq_redraw()
                    if self._ui_loop_job is not None:
                        try:
                            self.after_cancel(self._ui_loop_job)
                        except Exception:
                            pass
                        self._ui_loop_job = None
                    self._ui_loop_job = self.after(20, self._schedule_ui_loop)
                else:
                    self.power_btn.configure(text=self._t("start_audio"), fg_color="#059669", hover_color="#10b981")
                    if msg != "Interrompido":
                        messagebox.showerror(self._t("err_audio_title"), msg)
                        self.status_lbl.configure(text=msg, text_color="#ef4444")
                    else:
                        self.status_lbl.configure(text=self._t("stopped"), text_color=self._c()["text_muted"])

            try:
                self.after(0, _done)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _restart_if_running(self):
        if self.router.running:
            self._start_audio()

    # ------------------------------------------------------------------ #
    # Gráficos em Tempo Real (Curva EQ & Osciloscópio)
    # ------------------------------------------------------------------ #
    def _schedule_eq_redraw(self):
        if self._eq_redraw_job is not None:
            try:
                self.after_cancel(self._eq_redraw_job)
            except Exception:
                pass
        self._eq_redraw_job = self.after(35, self._draw_eq_curve)

    def _draw_eq_curve(self):
        self._eq_redraw_job = None
        if self._rebuilding_ui or self._is_quitting:
            return
        try:
            if self.state() == "iconic":
                return
        except Exception:
            pass
        th = self._c()
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
            color = th["grid_zero"] if db == 0 else th["grid_line"]
            c.create_line(pad_x, y, w - pad_x, y, fill=color, dash=(3, 3) if db != 0 else ())
            c.create_text(pad_x - 6, y, text=f"{db:+d}", fill=th["grid_text"], font=("Segoe UI", 8), anchor="e")

        # Grade logarítmica de frequências (20 Hz -> 20 kHz)
        f_min, f_max = 20.0, 20000.0
        log_span = np.log10(f_max / f_min)
        for f in (30, 60, 120, 250, 500, 1000, 2000, 4000, 8000, 16000):
            x = pad_x + (np.log10(f / f_min) / log_span) * gw
            c.create_line(x, pad_y, x, h - pad_y, fill=th["grid_line"])
            lbl = f"{f // 1000}k" if f >= 1000 else str(f)
            c.create_text(x, h - 5, text=lbl, fill=th["grid_text"], font=("Segoe UI", 8))

        if not self.params.eq_enabled:
            y0 = pad_y + 0.5 * gh
            c.create_line(pad_x, y0, w - pad_x, y0, fill=th["text_subtle"], width=2)
            c.create_text(w / 2, y0 - 14, text=self._t("eq_flat"), fill=th["grid_text"], font=("Segoe UI", 10))
            return

        sr = self.dsp.sr
        sos = build_eq_sos(self.params, sr)
        freqs = np.logspace(np.log10(f_min), np.log10(min(f_max, sr * 0.48)), 160)
        _, resp = signal.sosfreqz(sos, worN=freqs, fs=sr)
        db_resp = np.clip(20.0 * np.log10(np.maximum(np.abs(resp), 1e-5)), -20.0, 20.0)

        xs = pad_x + (np.log10(freqs / f_min) / log_span) * gw
        ys = np.clip(pad_y + (18.0 - db_resp) / 36.0 * gh, pad_y, h - pad_y)
        pts = np.column_stack((xs, ys)).ravel().tolist()

        if len(pts) >= 4:
            c.create_line(*pts, fill=th["accent"], width=2, smooth=True)

    def _schedule_ui_loop(self):
        self._ui_loop_job = None
        if self._is_quitting or self._rebuilding_ui:
            return
        try:
            is_hidden = (self.state() == "iconic") or (not self.winfo_viewable())
        except Exception:
            is_hidden = False

        if is_hidden:
            self._last_ui_hidden = True
            self._ui_loop_job = self.after(220, self._schedule_ui_loop)
            return

        next_ms = 110
        try:
            th = self._c()
            force_refresh = self._last_ui_hidden
            self._last_ui_hidden = False

            # Atualiza VU meters apenas se houve variação visível
            in_norm = max(0.0, min(1.0, (self.dsp.input_peak_db + 60.0) / 60.0))
            out_norm = max(0.0, min(1.0, (self.dsp.output_peak_db + 60.0) / 60.0))
            if force_refresh or abs(in_norm - self._last_in_norm) >= 0.005:
                self._last_in_norm = in_norm
                self.in_bar.set(in_norm)
            if force_refresh or abs(out_norm - self._last_out_norm) >= 0.005:
                self._last_out_norm = out_norm
                self.out_bar.set(out_norm)

            gate_open = bool(self.dsp.gate_is_open)
            if force_refresh or gate_open != self._last_gate_open:
                self._last_gate_open = gate_open
                if gate_open:
                    self.gate_led.configure(text=self._t("gate_open"), text_color="#10b981")
                else:
                    self.gate_led.configure(text=self._t("gate_closed"), text_color="#f59e0b")

            # Osciloscópio sem delete("all"): reutiliza os mesmos itens do Canvas (zero GDI/Tk churn)
            wc = self.wave_canvas
            ww = max(200, wc.winfo_width())
            wh = max(50, wc.winfo_height())
            mid = wh / 2.0
            if self._wave_mid_id is None:
                self._wave_mid_id = wc.create_line(0, mid, ww, mid, fill=th["control_bg"])
            else:
                wc.coords(self._wave_mid_id, 0, mid, ww, mid)
                wc.itemconfigure(self._wave_mid_id, fill=th["control_bg"])

            wave = self.dsp.last_waveform
            if self.router.running and len(wave) > 1:
                self._last_wave_idle = False
                n_w = len(wave)
                if self._wave_xs is None or self._wave_cached_w != ww or self._wave_cached_len != n_w:
                    self._wave_xs = np.linspace(0.0, float(ww), n_w)
                    self._wave_cached_w = ww
                    self._wave_cached_len = n_w
                ys = mid - np.clip(wave, -1.0, 1.0) * (mid - 4.0)
                pts = np.column_stack((self._wave_xs, ys)).ravel().tolist()
                color = "#f59e0b" if self.params.bypass else th["accent"]
                if self._wave_line_id is None:
                    self._wave_line_id = wc.create_line(*pts, fill=color, width=2)
                else:
                    wc.coords(self._wave_line_id, *pts)
                    wc.itemconfigure(self._wave_line_id, fill=color, state="normal")
                next_ms = 33
            elif force_refresh or not self._last_wave_idle:
                self._last_wave_idle = True
                if self._wave_line_id is not None:
                    wc.itemconfigure(self._wave_line_id, state="hidden")
        except Exception:
            next_ms = 120

        if not self._is_quitting:
            self._ui_loop_job = self.after(next_ms, self._schedule_ui_loop)

    # ------------------------------------------------------------------ #
    # Atualização do Aplicativo (Git / GitHub / .zip Local)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _run_cmd(args: list[str], cwd: str) -> tuple[int, str]:
        kwargs = {"cwd": cwd, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True}
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            res = subprocess.run(args, timeout=60, **kwargs)
            return res.returncode, (res.stdout or "").strip()
        except FileNotFoundError:
            return 127, f"Comando não encontrado: {args[0]}"
        except Exception as e:
            return 1, str(e)

    @staticmethod
    def _read_build_info() -> dict:
        try:
            if os.path.exists(BUILD_INFO_PATH):
                with open(BUILD_INFO_PATH, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
        return {}

    @staticmethod
    def _parse_version_tuple(raw: str) -> tuple[int, ...]:
        if not raw:
            return ()
        m = re.search(r"(\d+(?:\.\d+)+)", str(raw).strip())
        if not m:
            return ()
        try:
            return tuple(int(part) for part in m.group(1).split("."))
        except Exception:
            return ()

    def _get_local_build_identity(self) -> dict[str, str]:
        binfo = self._read_build_info()
        cfg = getattr(self, "app_config", None) or {}
        ver_raw = ""
        for cand in (
            binfo.get("version"),
            binfo.get("tag"),
            cfg.get("installed_version"),
            cfg.get("installed_tag"),
            APP_VERSION,
        ):
            vt = self._parse_version_tuple(str(cand or ""))
            if vt:
                ver_raw = ".".join(str(x) for x in vt)
                break
        if not ver_raw:
            ver_raw = APP_VERSION
        tag = str(binfo.get("tag") or cfg.get("installed_tag") or f"v{ver_raw}").strip()
        commit = str(binfo.get("commit") or cfg.get("installed_commit_sha") or "").strip()
        return {"version": ver_raw, "tag": tag, "commit": commit}

    def _detect_github_repo(self) -> str:
        legacy_slugs = {"cakesweet/voxcraft_studio"}
        saved = str((self.app_config or {}).get("github_repo", "")).strip().strip("/").removesuffix(".git")
        if saved and "/" in saved and saved.lower() not in legacy_slugs:
            return saved
        binfo = self._read_build_info()
        ci_repo = str(binfo.get("repo", "")).strip().strip("/").removesuffix(".git")
        if ci_repo and "/" in ci_repo and ci_repo.lower() not in legacy_slugs:
            return ci_repo
        if os.path.isdir(os.path.join(BASE_DIR, ".git")) and shutil.which("git"):
            rc, url = self._run_cmd(["git", "config", "--get", "remote.origin.url"], BASE_DIR)
            if rc == 0 and url:
                m = re.search(r"github\.com[:/]([^/]+/[^/.\s]+)", url)
                if m:
                    found = m.group(1).removesuffix(".git")
                    if found.lower() not in legacy_slugs:
                        return found
        return GITHUB_REPO

    @staticmethod
    def _download_bytes(
        url: str,
        timeout: int = 25,
        token: str = "",
        accept: str = "",
        method: str = "GET",
    ) -> tuple[bytes, str]:
        class _CrossHostAuthStripRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
                if new_req is not None:
                    old_host = urllib.parse.urlparse(req.full_url).netloc.lower()
                    new_host = urllib.parse.urlparse(new_req.full_url).netloc.lower()
                    if old_host != new_host:
                        for h in ("Authorization", "authorization"):
                            new_req.headers.pop(h, None)
                            new_req.unredirected_hdrs.pop(h, None)
                return new_req

        headers = {"User-Agent": "VoxCraft-Studio-Updater/1.0"}
        if accept:
            headers["Accept"] = accept
        if token:
            headers["Authorization"] = f"Bearer {token.strip()}"

        req = urllib.request.Request(url, headers=headers, method=method)

        def _open_with_ctx(ctx=None):
            handlers = [_CrossHostAuthStripRedirect()]
            if ctx is not None:
                handlers.append(urllib.request.HTTPSHandler(context=ctx))
            opener = urllib.request.build_opener(*handlers)
            with opener.open(req, timeout=timeout) as resp:
                data = b"" if method == "HEAD" else resp.read()
                return data, resp.geturl()

        try:
            return _open_with_ctx()
        except Exception as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                ctx = ssl._create_unverified_context()
                return _open_with_ctx(ctx=ctx)
            raise

    @staticmethod
    def _extract_zip_preserving_config(raw_or_path) -> int:
        preserved = {"voxcraft_config.json", "user_presets.json"}
        count = 0
        with zipfile.ZipFile(raw_or_path) as zf:
            members = [m for m in zf.infolist() if not m.is_dir()]
            # Detecta se o ZIP possui pasta raiz única (padrão GitHub archive)
            top_dirs = {m.filename.split("/", 1)[0] for m in members if "/" in m.filename}
            strip_prefix = len(top_dirs) == 1 and any(
                m.filename.endswith(("/app.py", "/dsp_engine.py", "/requirements.txt")) for m in members
            )
            base_norm = os.path.normpath(BASE_DIR)
            for member in members:
                rel = member.filename
                if strip_prefix and "/" in rel:
                    rel = rel.split("/", 1)[1]
                if not rel or rel in preserved:
                    continue
                if rel.startswith(".") and rel != ".gitignore":
                    continue
                dest = os.path.normpath(os.path.join(BASE_DIR, rel))
                if not dest.startswith(base_norm + os.sep) and dest != base_norm:
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with zf.open(member) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                count += 1
        return count

    def _start_app_update(self):
        # Salva imediatamente entradas, saídas, preset, atalho e parâmetros atuais
        self._save_config(include_params=True)

        existing = getattr(self, "_update_win", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass

        th = self._c()

        win = ctk.CTkToplevel(self)
        self._update_win = win
        win.title(self._t("upd_win_title"))
        w, h = 580, 240
        self.update_idletasks()
        px = self.winfo_rootx() + max(0, (self.winfo_width() - w) // 2)
        py = self.winfo_rooty() + max(0, (self.winfo_height() - h) // 2)
        win.geometry(f"{w}x{h}+{px}+{py}")
        win.resizable(False, False)
        win.transient(self)
        win.configure(fg_color=th["modal_bg"])

        def _close_update():
            self._update_win = None
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", _close_update)

        local_id = self._get_local_build_identity()

        hdr_row = ctk.CTkFrame(win, fg_color="transparent")
        hdr_row.pack(fill="x", padx=20, pady=(18, 6))
        ctk.CTkLabel(
            hdr_row, text=self._t("upd_header"), font=self._fonts["h2_b"], text_color=th["accent"]
        ).pack(side="left")
        ctk.CTkLabel(
            hdr_row, text=f"v{local_id['version']}", font=self._fonts["xs_b"], text_color=th["text_subtle"]
        ).pack(side="right")

        msg_lbl = ctk.CTkLabel(
            win,
            text=self._t("upd_checking"),
            justify="left",
            wraplength=540,
            font=self._fonts["sm"],
            text_color=th["text_body"],
        )
        msg_lbl.pack(anchor="w", padx=20, pady=(8, 12))

        progress = ctk.CTkProgressBar(win, mode="indeterminate", width=540, fg_color=th["track_bg"], progress_color=th["accent"])
        progress.pack(padx=20, pady=(2, 16))
        progress.start()

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(4, 16))

        action_btn = ctk.CTkButton(
            btn_row,
            text=self._t("upd_now_btn"),
            width=172,
            height=34,
            corner_radius=8,
            fg_color="#059669",
            hover_color="#10b981",
            text_color="#ffffff",
            state="disabled",
        )
        action_btn.pack(side="left")

        local_btn = ctk.CTkButton(
            btn_row,
            text=self._t("upd_local_btn"),
            width=148,
            height=34,
            corner_radius=8,
            fg_color=th["control_bg"],
            hover_color="#2563eb",
            text_color=th["text_primary"],
            border_width=1,
            border_color=th["control_border"],
        )
        local_btn.pack(side="left", padx=(8, 0))

        recheck_btn = ctk.CTkButton(
            btn_row,
            text=self._t("upd_check_btn"),
            width=92,
            height=34,
            corner_radius=8,
            fg_color=th["control_bg"],
            hover_color="#2563eb",
            text_color=th["text_primary"],
            border_width=1,
            border_color=th["control_border"],
        )
        recheck_btn.pack(side="left", padx=(8, 0))

        close_btn = ctk.CTkButton(
            btn_row,
            text=self._t("close"),
            width=90,
            height=34,
            corner_radius=8,
            fg_color=th["control_bg"],
            hover_color=th["control_hover"],
            text_color=th["text_primary"],
            border_width=1,
            border_color=th["control_border"],
            command=_close_update,
        )
        close_btn.pack(side="right")

        win.update_idletasks()
        win.lift()
        win.focus_force()

        def safe_ui(fn):
            def _run_on_main():
                try:
                    if win.winfo_exists():
                        fn()
                except Exception:
                    pass
            try:
                self.after(0, _run_on_main)
            except Exception:
                pass

        def _set_busy(text: str):
            safe_ui(lambda: (
                action_btn.configure(state="disabled"),
                local_btn.configure(state="disabled"),
                recheck_btn.configure(state="disabled"),
                close_btn.configure(state="disabled"),
                progress.configure(mode="indeterminate"),
                progress.start(),
                msg_lbl.configure(text=text, text_color=th["accent"]),
            ))

        def finish_message(text: str, color: str | None = None, enable_action: bool = False, btn_text: str | None = None, cmd=None):
            use_color = color or th["text_primary"]
            use_btn_text = btn_text or self._t("upd_now_btn")

            def _ui():
                progress.stop()
                progress.configure(mode="determinate")
                progress.set(1.0)
                msg_lbl.configure(text=text, text_color=use_color)
                if enable_action and cmd is not None:
                    action_btn.configure(state="normal", text=use_btn_text, command=cmd)
                else:
                    action_btn.configure(state="disabled")
                close_btn.configure(state="normal")
                local_btn.configure(state="normal")
                recheck_btn.configure(state="normal")
            safe_ui(_ui)

        def install_deps_and_relaunch():
            if not IS_FROZEN:
                safe_ui(lambda: msg_lbl.configure(text=self._t("upd_installing_deps")))
                self._run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"], BASE_DIR)
            safe_ui(lambda: self._relaunch_after_update(win))

        def _launch_exe_installer(exe_path: str, release_meta: dict | None = None):
            self.app_config["pending_update_restore"] = True
            self.app_config["was_running_before_update"] = bool(self.router.running)
            if isinstance(release_meta, dict):
                if release_meta.get("tag"):
                    self.app_config["installed_tag"] = str(release_meta["tag"])
                if release_meta.get("version"):
                    self.app_config["installed_version"] = str(release_meta["version"])
            self._save_config(include_params=True)
            if _SINGLE_INSTANCE is not None:
                _SINGLE_INSTANCE.release()
            try:
                win.destroy()
            except Exception:
                pass
            try:
                exe_name = os.path.basename(exe_path).lower()
                if IS_FROZEN and sys.platform == "win32":
                    bat_path = os.path.join(tempfile.gettempdir(), "voxcraft_auto_update.bat")
                    app_exe = sys.executable
                    if "setup" in exe_name:
                        script = (
                            "@echo off\r\n"
                            "chcp 65001 >nul\r\n"
                            "ping -n 3 127.0.0.1 >nul\r\n"
                            f'"{exe_path}" /SILENT /NORESTART /CLOSEAPPLICATIONS\r\n'
                            f'if exist "{app_exe}" start "" "{app_exe}" --relaunch\r\n'
                            'del "%~f0"\r\n'
                        )
                    else:
                        script = (
                            "@echo off\r\n"
                            "chcp 65001 >nul\r\n"
                            "ping -n 3 127.0.0.1 >nul\r\n"
                            f'copy /y "{exe_path}" "{app_exe}" >nul\r\n'
                            f'start "" "{app_exe}" --relaunch\r\n'
                            'del "%~f0"\r\n'
                        )
                    with open(bat_path, "w", encoding="utf-8") as bf:
                        bf.write(script)
                    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    subprocess.Popen(["cmd.exe", "/c", bat_path], cwd=tempfile.gettempdir(), creationflags=flags)
                else:
                    subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path) or tempfile.gettempdir())
            except Exception as err:
                messagebox.showerror(
                    self._t("upd_err_open_title"),
                    self._t("upd_err_open_body", path=exe_path, err=err),
                )
            self._quit_app()

        def apply_local_file():
            filetypes = (
                [(self._t("upd_ft_exe_zip"), "*.exe *.zip"), (self._t("upd_ft_exe"), "*.exe"), (self._t("upd_ft_zip"), "*.zip")]
                if IS_FROZEN
                else [(self._t("upd_ft_zip_exe"), "*.zip *.exe"), (self._t("upd_ft_zip"), "*.zip"), (self._t("upd_ft_exe"), "*.exe")]
            )
            picked = filedialog.askopenfilename(
                parent=win,
                title=self._t("upd_pick_title"),
                filetypes=filetypes,
            )
            if not picked:
                return

            def _worker():
                _set_busy(self._t("upd_preparing"))
                try:
                    if picked.lower().endswith(".exe"):
                        safe_ui(lambda: _launch_exe_installer(picked))
                        return

                    if IS_FROZEN:
                        with zipfile.ZipFile(picked) as zf:
                            exe_members = [
                                m for m in zf.infolist()
                                if not m.is_dir() and m.filename.lower().endswith(".exe")
                            ]
                            if not exe_members:
                                finish_message(self._t("upd_no_exe_in_zip"), "#f59e0b")
                                return
                            chosen_m = next(
                                (m for m in exe_members if "setup" in os.path.basename(m.filename).lower()),
                                exe_members[0],
                            )
                            out_exe = os.path.join(tempfile.gettempdir(), os.path.basename(chosen_m.filename))
                            with zf.open(chosen_m) as src, open(out_exe, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                        safe_ui(lambda: _launch_exe_installer(out_exe))
                        return

                    n_files = self._extract_zip_preserving_config(picked)
                    if n_files == 0:
                        finish_message(self._t("upd_no_valid_zip"), "#ef4444")
                        return
                    install_deps_and_relaunch()
                except Exception as e:
                    finish_message(self._t("upd_err_process", err=e), "#ef4444")

            threading.Thread(target=_worker, daemon=True).start()

        local_btn.configure(command=apply_local_file)

        def _run_git_update(target_ref: str, force_reset: bool = False):
            _set_busy(self._t("upd_git_applying"))
            if force_reset:
                rc, out = self._run_cmd(["git", "reset", "--hard", target_ref], BASE_DIR)
            else:
                rc, out = self._run_cmd(["git", "pull", "--ff-only"], BASE_DIR)
                if rc != 0:
                    remote_branch = target_ref.split("/", 1)[-1] if "/" in target_ref else "main"
                    rc, out = self._run_cmd(["git", "pull", "--autostash", "origin", remote_branch], BASE_DIR)
                if rc != 0:
                    rc, out = self._run_cmd(["git", "reset", "--hard", target_ref], BASE_DIR)
            if rc != 0:
                finish_message(self._t("upd_git_fail", out=out[:260]), "#ef4444")
                return
            install_deps_and_relaunch()

        def apply_git_update(target_ref: str, force_reset: bool = False):
            threading.Thread(target=lambda: _run_git_update(target_ref, force_reset), daemon=True).start()

        def _run_github_zip_update(repo_slug: str, tok: str = "", commit_sha: str = ""):
            _set_busy(self._t("upd_downloading_gh", repo=repo_slug))
            raw_zip = None
            last_err = ""
            for branch in ("main", "master"):
                url = (
                    f"https://api.github.com/repos/{repo_slug}/zipball/{branch}"
                    if tok
                    else f"https://github.com/{repo_slug}/archive/refs/heads/{branch}.zip"
                )
                try:
                    raw_zip, _ = self._download_bytes(url, timeout=30, token=tok)
                    break
                except Exception as e:
                    last_err = str(e)
            if not raw_zip:
                finish_message(self._t("upd_gh_fail", repo=repo_slug, err=last_err), "#ef4444")
                return
            try:
                self._extract_zip_preserving_config(io.BytesIO(raw_zip))
                if commit_sha:
                    self.app_config["installed_commit_sha"] = commit_sha
                    self._save_config()
            except Exception as e:
                finish_message(self._t("upd_extract_fail", err=e), "#ef4444")
                return
            install_deps_and_relaunch()

        def _download_and_launch_exe(
            download_url: str,
            asset_name: str,
            api_asset_url: str = "",
            tok: str = "",
            release_meta: dict | None = None,
        ):
            _set_busy(self._t("upd_downloading_rel", name=asset_name))
            try:
                if tok and api_asset_url:
                    raw_exe, _ = self._download_bytes(
                        api_asset_url,
                        timeout=120,
                        token=tok,
                        accept="application/octet-stream",
                    )
                else:
                    raw_exe, _ = self._download_bytes(download_url, timeout=120)
                out_path = os.path.join(tempfile.gettempdir(), asset_name)
                with open(out_path, "wb") as f:
                    f.write(raw_exe)
            except Exception as e:
                finish_message(self._t("upd_dl_exe_fail", err=e), "#ef4444")
                return

            safe_ui(lambda p=out_path, m=release_meta: _launch_exe_installer(p, m))

        def run_check():
            repo_slug = self._detect_github_repo()
            token = str((self.app_config or {}).get("github_token", "")).strip()

            _set_busy(self._t("upd_consulting"))

            def check_worker():
                try:
                    cur_local = self._get_local_build_identity()
                    local_ver = self._parse_version_tuple(cur_local["version"])
                    local_commit = cur_local["commit"]

                    if IS_FROZEN:
                        rel = None
                        last_err = None
                        saw_empty_releases = False
                        api_accept = "application/vnd.github+json"

                        for api_url in (
                            f"https://api.github.com/repos/{repo_slug}/releases/latest",
                            f"https://api.github.com/repos/{repo_slug}/releases?per_page=10",
                            f"https://api.github.com/repos/{repo_slug}/releases/tags/latest",
                        ):
                            try:
                                raw, _ = self._download_bytes(api_url, timeout=15, token=token, accept=api_accept)
                                parsed = json.loads(raw.decode("utf-8"))
                                if isinstance(parsed, list):
                                    if len(parsed) == 0:
                                        saw_empty_releases = True
                                    non_draft = [r for r in parsed if not r.get("draft")]
                                    rel = next(
                                        (
                                            r
                                            for r in non_draft
                                            if any(str(a.get("name", "")).lower().endswith(".exe") for a in (r.get("assets") or []))
                                        ),
                                        non_draft[0] if non_draft else None,
                                    )
                                elif isinstance(parsed, dict) and parsed.get("id"):
                                    rel = parsed
                                if rel:
                                    break
                            except Exception as e:
                                last_err = e

                        if rel is None and not token:
                            direct_url = f"https://github.com/{repo_slug}/releases/latest/download/VoxCraftStudio_Setup.exe"
                            try:
                                _, final_url = self._download_bytes(direct_url, timeout=12, method="HEAD")
                                m_tag = re.search(r"/releases/download/([^/]+)/", final_url)
                                redir_tag = m_tag.group(1) if m_tag else "latest"
                                redir_ver = self._parse_version_tuple(redir_tag)
                                if redir_ver and local_ver and redir_ver > local_ver:
                                    rel_meta = {
                                        "tag": redir_tag,
                                        "version": ".".join(str(x) for x in redir_ver),
                                    }
                                    _download_and_launch_exe(final_url, "VoxCraftStudio_Setup.exe", release_meta=rel_meta)
                                    return
                                msg_up = (
                                    f"{self._t('upd_up_to_date_ver', ver=cur_local['version'])}\n"
                                    f"{self._t('upd_no_newer_note', local_ver=cur_local['version'], remote_tag=redir_tag)}"
                                )
                                finish_message(
                                    msg_up,
                                    "#10b981",
                                    enable_action=True,
                                    btn_text=self._t("upd_force_reinstall"),
                                    cmd=lambda u=final_url: threading.Thread(
                                        target=_download_and_launch_exe,
                                        args=(u, "VoxCraftStudio_Setup.exe"),
                                        daemon=True,
                                    ).start(),
                                )
                                return
                            except Exception:
                                pass

                        if rel is None:
                            if saw_empty_releases:
                                finish_message(self._t("upd_no_releases", repo=repo_slug), "#f59e0b")
                                return

                            repo_exists = False
                            try:
                                self._download_bytes(
                                    f"https://api.github.com/repos/{repo_slug}",
                                    timeout=10,
                                    token=token,
                                    accept=api_accept,
                                )
                                repo_exists = True
                            except Exception:
                                repo_exists = False

                            if repo_exists:
                                finish_message(self._t("upd_repo_no_rel", repo=repo_slug), "#f59e0b")
                            else:
                                hint = self._t("upd_bad_token_hint") if token else self._t("upd_private_hint")
                                finish_message(self._t("upd_no_access", repo=repo_slug, err=last_err, hint=hint), "#f59e0b")
                            return

                        assets = rel.get("assets") or []
                        chosen = next(
                            (
                                a
                                for a in assets
                                if str(a.get("name", "")).lower().endswith(".exe")
                                and "setup" in str(a.get("name", "")).lower()
                            ),
                            None,
                        )
                        if chosen is None:
                            chosen = next((a for a in assets if str(a.get("name", "")).lower().endswith(".exe")), None)

                        remote_tag = str(rel.get("tag_name") or "").strip()
                        remote_ver = (
                            self._parse_version_tuple(remote_tag)
                            or self._parse_version_tuple(str(chosen.get("name", "") if chosen else ""))
                            or self._parse_version_tuple(str(rel.get("name", "")))
                        )
                        remote_ver_str = ".".join(str(x) for x in remote_ver) if remote_ver else ""
                        is_newer = bool(remote_ver and local_ver and remote_ver > local_ver)

                        if not is_newer:
                            shown_tag = remote_tag or "latest"
                            msg_up = (
                                f"{self._t('upd_up_to_date_ver', ver=cur_local['version'])}\n"
                                f"{self._t('upd_no_newer_note', local_ver=cur_local['version'], remote_tag=shown_tag)}"
                            )
                            if chosen and (chosen.get("browser_download_url") or chosen.get("url")):
                                asset_name = chosen["name"]
                                dl_url = chosen.get("browser_download_url", "")
                                api_asset_url = chosen.get("url", "")
                                rel_meta = {"tag": remote_tag, "version": remote_ver_str}
                                finish_message(
                                    msg_up,
                                    "#10b981",
                                    enable_action=True,
                                    btn_text=self._t("upd_force_reinstall"),
                                    cmd=lambda d=dl_url, n=asset_name, au=api_asset_url, tk_=token, rm=rel_meta: threading.Thread(
                                        target=_download_and_launch_exe,
                                        args=(d, n, au, tk_, rm),
                                        daemon=True,
                                    ).start(),
                                )
                            else:
                                finish_message(msg_up, "#10b981")
                            return

                        if chosen and (chosen.get("browser_download_url") or chosen.get("url")):
                            asset_name = chosen["name"]
                            dl_url = chosen.get("browser_download_url", "")
                            api_asset_url = chosen.get("url", "")
                            rel_meta = {"tag": remote_tag, "version": remote_ver_str}
                            _download_and_launch_exe(dl_url, asset_name, api_asset_url, token, rel_meta)
                            return

                        finish_message(self._t("upd_no_exe_rel", repo=repo_slug), "#f59e0b")
                        return

                    git_dir = os.path.join(BASE_DIR, ".git")
                    has_git = os.path.isdir(git_dir) and (shutil.which("git") is not None)

                    if has_git:
                        rc, out = self._run_cmd(["git", "fetch", "origin"], BASE_DIR)
                        if rc == 0:
                            rc_u, upstream = self._run_cmd(
                                ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], BASE_DIR
                            )
                            target = upstream if rc_u == 0 and upstream else "origin/main"
                            rc_r, remote_sha = self._run_cmd(["git", "rev-parse", target], BASE_DIR)
                            if rc_r != 0:
                                target = "origin/master"
                                rc_r, remote_sha = self._run_cmd(["git", "rev-parse", target], BASE_DIR)
                            rc_h, local_sha = self._run_cmd(["git", "rev-parse", "HEAD"], BASE_DIR)
                            if rc_h == 0 and rc_r == 0 and local_sha == remote_sha:
                                finish_message(
                                    self._t("upd_git_up_to_date"),
                                    "#10b981",
                                    enable_action=True,
                                    btn_text=self._t("upd_force_reinstall"),
                                    cmd=lambda tgt=target: apply_git_update(tgt, force_reset=True),
                                )
                                return

                            _run_git_update(target, force_reset=False)
                            return

                    # Instalação via código-fonte sem .git: verifica SHA remoto antes de baixar/reiniciar
                    remote_head_sha = ""
                    try:
                        raw_head, _ = self._download_bytes(
                            f"https://api.github.com/repos/{repo_slug}/commits/HEAD",
                            timeout=12,
                            token=token,
                            accept="application/vnd.github+json",
                        )
                        parsed_head = json.loads(raw_head.decode("utf-8"))
                        if isinstance(parsed_head, dict):
                            remote_head_sha = str(parsed_head.get("sha") or "").strip()
                    except Exception:
                        remote_head_sha = ""

                    if remote_head_sha and local_commit and remote_head_sha == local_commit:
                        finish_message(
                            self._t("upd_src_up_to_date"),
                            "#10b981",
                            enable_action=True,
                            btn_text=self._t("upd_force_reinstall"),
                            cmd=lambda rs=repo_slug, tk_=token, sha=remote_head_sha: threading.Thread(
                                target=_run_github_zip_update,
                                args=(rs, tk_, sha),
                                daemon=True,
                            ).start(),
                        )
                        return

                    _run_github_zip_update(repo_slug, token, remote_head_sha)
                except Exception as exc:
                    finish_message(self._t("upd_check_err", err=exc), "#ef4444")

            threading.Thread(target=check_worker, daemon=True).start()

        recheck_btn.configure(command=run_check)
        run_check()

    def _relaunch_after_update(self, modal_win=None):
        self.app_config["pending_update_restore"] = True
        self.app_config["was_running_before_update"] = bool(self.router.running)
        self._save_config(include_params=True)
        if _SINGLE_INSTANCE is not None:
            _SINGLE_INSTANCE.release()
        if modal_win is not None:
            try:
                modal_win.destroy()
            except Exception:
                pass
        try:
            cmd = [sys.executable, "--relaunch"] if IS_FROZEN else [sys.executable, os.path.abspath(__file__), "--relaunch"]
            subprocess.Popen(cmd, cwd=BASE_DIR)
        except Exception as e:
            messagebox.showerror(self._t("upd_done_title"), self._t("upd_done_body", err=e))
        self._quit_app()

    # ------------------------------------------------------------------ #
    # Configurações (Tema, Idioma e Inicialização com o Sistema)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _get_autostart_command() -> str:
        if IS_FROZEN:
            return f'"{os.path.abspath(sys.executable)}"'
        script_path = os.path.abspath(__file__)
        if sys.platform == "win32":
            py_dir = os.path.dirname(os.path.abspath(sys.executable))
            pyw = os.path.join(py_dir, "pythonw.exe")
            interp = pyw if os.path.exists(pyw) else sys.executable
            return f'"{interp}" "{script_path}"'
        return f'"{sys.executable}" "{script_path}"'

    @staticmethod
    def _get_linux_desktop_autostart_path() -> str:
        cfg_home = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
        return os.path.join(cfg_home, "autostart", "voxcraft-studio.desktop")

    def _is_autostart_enabled(self) -> bool:
        if sys.platform == "win32" and winreg is not None:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_READ,
                ) as key:
                    val, _ = winreg.QueryValueEx(key, "VoxCraftStudio")
                    return bool(str(val).strip())
            except FileNotFoundError:
                return False
            except Exception:
                return bool((self.app_config or {}).get("autostart_enabled", False))
        desktop_path = self._get_linux_desktop_autostart_path()
        if os.path.exists(desktop_path):
            try:
                with open(desktop_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "X-GNOME-Autostart-enabled=false" in content or "Hidden=true" in content:
                    return False
                return True
            except Exception:
                return True
        return False

    def _set_autostart_enabled(self, enabled: bool) -> tuple[bool, str]:
        if sys.platform == "win32" and winreg is not None:
            try:
                with winreg.CreateKeyEx(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_SET_VALUE,
                ) as key:
                    if enabled:
                        winreg.SetValueEx(key, "VoxCraftStudio", 0, winreg.REG_SZ, self._get_autostart_command())
                    else:
                        try:
                            winreg.DeleteValue(key, "VoxCraftStudio")
                        except FileNotFoundError:
                            pass
                self.app_config["autostart_enabled"] = bool(enabled)
                self._save_config()
                return True, ""
            except Exception as exc:
                return False, str(exc)

        desktop_path = self._get_linux_desktop_autostart_path()
        try:
            if enabled:
                os.makedirs(os.path.dirname(desktop_path), exist_ok=True)
                icon_val = ICON_PNG_PATH if os.path.exists(ICON_PNG_PATH) else "voxcraft-studio"
                entry = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Version=1.0\n"
                    "Name=VoxCraft Studio\n"
                    "Comment=Real-Time Voice Modulator & DSP Studio\n"
                    f"Exec={self._get_autostart_command()}\n"
                    f"Icon={icon_val}\n"
                    "Terminal=false\n"
                    "Categories=AudioVideo;Audio;\n"
                    "X-GNOME-Autostart-enabled=true\n"
                )
                with open(desktop_path, "w", encoding="utf-8") as f:
                    f.write(entry)
            else:
                if os.path.exists(desktop_path):
                    os.remove(desktop_path)
            self.app_config["autostart_enabled"] = bool(enabled)
            self._save_config()
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def _open_settings_dialog(self):
        existing = getattr(self, "_settings_win", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass

        th = self._c()
        win = ctk.CTkToplevel(self)
        self._settings_win = win
        win.title(self._t("settings_title"))
        w, h = 460, 355
        px = self.winfo_rootx() + max(0, (self.winfo_width() - w) // 2)
        py = self.winfo_rooty() + max(0, (self.winfo_height() - h) // 2)
        win.geometry(f"{w}x{h}+{px}+{py}")
        win.resizable(False, False)
        win.transient(self)
        win.configure(fg_color=th["modal_bg"])

        def _close_settings():
            self._settings_win = None
            self._refresh_settings_modal = None
            try:
                win.grab_release()
            except Exception:
                pass
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", _close_settings)

        title_lbl = ctk.CTkLabel(
            win,
            text=self._t("settings_title"),
            font=self._fonts["h1_b"],
            text_color=th["accent"],
        )
        title_lbl.pack(anchor="w", padx=22, pady=(18, 12))

        updating_modal = False

        # Tema
        theme_card = ctk.CTkFrame(
            win, fg_color=th["card_bg"], corner_radius=12, border_width=1, border_color=th["card_border"]
        )
        theme_card.pack(fill="x", padx=22, pady=(0, 12))
        theme_lbl = ctk.CTkLabel(
            theme_card,
            text=self._t("theme_label"),
            font=self._fonts["md_b"],
            text_color=th["text_primary"],
        )
        theme_lbl.pack(anchor="w", padx=14, pady=(10, 6))

        def _get_theme_options():
            return [
                ("dark", self._t("theme_dark")),
                ("oled", self._t("theme_oled")),
                ("light", self._t("theme_light")),
            ]

        theme_options = _get_theme_options()
        theme_label_to_key = {lbl: key for key, lbl in theme_options}
        cur_theme_lbl = next((lbl for key, lbl in theme_options if key == self.ui_theme), self._t("theme_dark"))
        theme_var = ctk.StringVar(value=cur_theme_lbl)

        def on_theme_change(choice: str):
            if updating_modal:
                return
            new_theme = theme_label_to_key.get(choice, "dark")
            if new_theme != self.ui_theme:
                self.after(15, lambda nt=new_theme: self._apply_theme_and_language(nt, self.ui_lang))

        theme_seg = ctk.CTkSegmentedButton(
            theme_card,
            variable=theme_var,
            values=[lbl for _, lbl in theme_options],
            fg_color=th["tab_bg"],
            selected_color=th["seg_selected"],
            selected_hover_color=th["seg_selected_hover"],
            unselected_color=th["control_bg"],
            unselected_hover_color=th["control_hover"],
            text_color=th["seg_text"],
            height=32,
            command=on_theme_change,
        )
        theme_seg.pack(fill="x", padx=14, pady=(0, 12))

        # Idioma (somente Português, English, Español)
        lang_card = ctk.CTkFrame(
            win, fg_color=th["card_bg"], corner_radius=12, border_width=1, border_color=th["card_border"]
        )
        lang_card.pack(fill="x", padx=22, pady=(0, 12))
        lang_lbl = ctk.CTkLabel(
            lang_card,
            text=self._t("language_label"),
            font=self._fonts["md_b"],
            text_color=th["text_primary"],
        )
        lang_lbl.pack(anchor="w", padx=14, pady=(10, 6))

        lang_label_to_code = {LANGUAGE_LABELS[code]: code for code in LANGUAGES}
        lang_var = ctk.StringVar(value=LANGUAGE_LABELS.get(self.ui_lang, "Português"))

        def on_lang_change(choice: str):
            if updating_modal:
                return
            new_lang = lang_label_to_code.get(choice, "pt")
            if new_lang != self.ui_lang:
                self.after(15, lambda nl=new_lang: self._apply_theme_and_language(self.ui_theme, nl))

        lang_seg = ctk.CTkSegmentedButton(
            lang_card,
            variable=lang_var,
            values=[LANGUAGE_LABELS[code] for code in LANGUAGES],
            fg_color=th["tab_bg"],
            selected_color=th["seg_selected"],
            selected_hover_color=th["seg_selected_hover"],
            unselected_color=th["control_bg"],
            unselected_hover_color=th["control_hover"],
            text_color=th["seg_text"],
            height=32,
            command=on_lang_change,
        )
        lang_seg.pack(fill="x", padx=14, pady=(0, 12))

        # Iniciar com o Windows / Sistema
        startup_key = "startup_label" if sys.platform == "win32" else "startup_label_linux"
        startup_card = ctk.CTkFrame(
            win, fg_color=th["card_bg"], corner_radius=12, border_width=1, border_color=th["card_border"]
        )
        startup_card.pack(fill="x", padx=22, pady=(0, 14))
        startup_var = ctk.BooleanVar(value=self._is_autostart_enabled())

        def on_startup_toggle():
            if updating_modal:
                return
            desired = bool(startup_var.get())
            ok, err = self._set_autostart_enabled(desired)
            if not ok:
                startup_var.set(not desired)
                messagebox.showerror(self._t("err_title"), self._t("startup_err", err=err), parent=win)

        startup_switch = ctk.CTkSwitch(
            startup_card,
            text=self._t(startup_key),
            variable=startup_var,
            font=self._fonts["md_b"],
            fg_color=th["track_bg"],
            progress_color=th["accent"],
            button_color=th["switch_knob"],
            button_hover_color=th["switch_knob_hover"],
            text_color=th["text_primary"],
            command=on_startup_toggle,
        )
        startup_switch.pack(anchor="w", padx=14, pady=12)

        close_btn = ctk.CTkButton(
            win,
            text=self._t("close"),
            width=120,
            height=34,
            corner_radius=8,
            fg_color=th["control_bg"],
            hover_color=th["control_hover"],
            text_color=th["text_primary"],
            border_width=1,
            border_color=th["control_border"],
            command=_close_settings,
        )
        close_btn.pack(pady=(2, 12))

        def _refresh_modal(lang_changed: bool = True):
            nonlocal updating_modal, theme_options, theme_label_to_key
            if not win.winfo_exists():
                return
            updating_modal = True
            try:
                t_now = self._c()
                win.title(self._t("settings_title"))
                win.configure(fg_color=t_now["modal_bg"])
                title_lbl.configure(text=self._t("settings_title"), text_color=t_now["accent"])
                theme_card.configure(fg_color=t_now["card_bg"], border_color=t_now["card_border"], bg_color="transparent")
                theme_lbl.configure(text=self._t("theme_label"), text_color=t_now["text_primary"])
                theme_options = _get_theme_options()
                theme_label_to_key = {lbl: key for key, lbl in theme_options}
                cur_lbl = next((lbl for key, lbl in theme_options if key == self.ui_theme), self._t("theme_dark"))
                seg_kw = {
                    "fg_color": t_now["tab_bg"],
                    "selected_color": t_now["seg_selected"],
                    "selected_hover_color": t_now["seg_selected_hover"],
                    "unselected_color": t_now["control_bg"],
                    "unselected_hover_color": t_now["control_hover"],
                    "text_color": t_now["seg_text"],
                    "bg_color": "transparent",
                }
                if lang_changed:
                    seg_kw["values"] = [lbl for _, lbl in theme_options]
                theme_seg.configure(**seg_kw)
                theme_var.set(cur_lbl)

                lang_card.configure(fg_color=t_now["card_bg"], border_color=t_now["card_border"], bg_color="transparent")
                lang_lbl.configure(text=self._t("language_label"), text_color=t_now["text_primary"])
                lang_seg.configure(
                    fg_color=t_now["tab_bg"],
                    selected_color=t_now["seg_selected"],
                    selected_hover_color=t_now["seg_selected_hover"],
                    unselected_color=t_now["control_bg"],
                    unselected_hover_color=t_now["control_hover"],
                    text_color=t_now["seg_text"],
                    bg_color="transparent",
                )
                lang_var.set(LANGUAGE_LABELS.get(self.ui_lang, "Português"))

                startup_card.configure(fg_color=t_now["card_bg"], border_color=t_now["card_border"], bg_color="transparent")
                startup_switch.configure(
                    text=self._t(startup_key),
                    fg_color=t_now["track_bg"],
                    progress_color=t_now["accent"],
                    button_color=t_now["switch_knob"],
                    button_hover_color=t_now["switch_knob_hover"],
                    text_color=t_now["text_primary"],
                    bg_color="transparent",
                )

                close_btn.configure(
                    text=self._t("close"),
                    fg_color=t_now["control_bg"],
                    hover_color=t_now["control_hover"],
                    text_color=t_now["text_primary"],
                    border_color=t_now["control_border"],
                    bg_color="transparent",
                )
            finally:
                updating_modal = False

        self._refresh_settings_modal = _refresh_modal
        win.lift()
        win.after(40, lambda: win.winfo_exists() and (win.lift(), win.focus_force()))

    def _apply_theme_and_language(self, new_theme: str, new_lang: str):
        if new_theme not in ("dark", "oled", "light"):
            new_theme = "dark"
        if new_lang not in LANGUAGES:
            new_lang = "pt"
        if new_theme == self.ui_theme and new_lang == self.ui_lang:
            return

        old_ctk_mode = self._c()["ctk_mode"]
        theme_changed = new_theme != self.ui_theme
        lang_changed = new_lang != self.ui_lang
        self.ui_theme = new_theme
        self.ui_lang = new_lang

        if lang_changed:
            self._apply_i18n_in_place()
        if theme_changed:
            self._apply_theme_in_place(old_ctk_mode)

        settings_win = getattr(self, "_settings_win", None)
        refresh_fn = getattr(self, "_refresh_settings_modal", None)
        if settings_win is not None and refresh_fn is not None:
            try:
                if settings_win.winfo_exists():
                    refresh_fn(lang_changed=lang_changed)
                    if theme_changed and self._c()["ctk_mode"] != old_ctk_mode:
                        self.after(
                            25,
                            lambda w=settings_win: w.winfo_exists() and (w.deiconify(), w.lift(), w.focus_force()),
                        )
            except Exception:
                pass

        self._save_config()

        if lang_changed and pystray is not None:
            self._restart_tray_icon()

    def _apply_i18n_in_place(self):
        for fn in self._i18n_hooks:
            try:
                fn()
            except Exception:
                pass

        cur_p = self.preset_var.get()
        if cur_p and not cur_p.startswith("★ "):
            self.preset_var.set(self._preset_to_display(self._preset_to_internal(cur_p)))
        self.preset_menu.configure(values=self._all_preset_names())

        self.latency_var.set(self._latency_to_display(str(self.latency_var.get())))
        self.latency_menu.configure(values=[self._t("lat_ultra"), self._t("lat_low"), self._t("lat_stable")])

        voc_int = self._wave_to_internal(str(self.voc_carrier_var.get()))
        self.voc_carrier_var.set(self._wave_to_display(voc_int))
        self.voc_carrier_menu.configure(
            values=[self._t("wave_saw"), self._t("wave_chord"), self._t("wave_sq"), self._t("wave_whisper")]
        )

        trem_int = self._wave_to_internal(str(self.trem_wave_var.get()))
        self.trem_wave_var.set(self._wave_to_display(trem_int))
        self.trem_wave_menu.configure(
            values=[self._t("wave_sine"), self._t("wave_tri"), self._t("wave_sq"), self._t("wave_saw")]
        )

        ring_int = self._wave_to_internal(str(self.ring_wave_var.get()))
        self.ring_wave_var.set(self._wave_to_display(ring_int))
        self.ring_wave_menu.configure(
            values=[self._t("wave_sine"), self._t("wave_sq"), self._t("wave_tri")]
        )

        if not self.in_devices:
            no_mic = self._t("no_mic")
            self.in_dev_menu.configure(values=[no_mic])
            self.in_dev_var.set(no_mic)
        if not self.out_devices:
            no_out = self._t("no_out")
            self.out_dev_menu.configure(values=[no_out])
            self.mon_dev_menu.configure(values=[no_out])
            self.out_dev_var.set(no_out)
            self.mon_dev_var.set(no_out)

        if not self._capturing_hotkey:
            self.hotkey_btn.configure(text=self._format_hotkey_label(self.hotkey_spec))
        self._update_hotkey_hint()
        if self._active_tab_key == "tab_eq":
            self._schedule_eq_redraw()

    def _apply_theme_in_place(self, old_ctk_mode: str):
        th = self._c()

        def _paint_all():
            self.configure(fg_color=th["window_bg"])
            for cont in getattr(self, "_transparent_containers", ()):
                try:
                    cont.configure(fg_color="transparent", bg_color="transparent")
                except Exception:
                    pass
            for wd, fn in self._theme_hooks:
                try:
                    if hasattr(wd, "winfo_exists") and not wd.winfo_exists():
                        continue
                    fn(th)
                except Exception:
                    pass

        # Atualiza primeiro os fundos dos containers pais antes de trocar o modo do CustomTkinter,
        # evitando que bordas e cantos arredondados memorizem o branco do tema Light.
        _paint_all()

        if th["ctk_mode"] != old_ctk_mode:
            try:
                cur_grab = self.grab_current()
                if cur_grab is not None:
                    cur_grab.grab_release()
            except Exception:
                pass
            ctk.set_appearance_mode(th["ctk_mode"])
            _paint_all()

        if self._capturing_hotkey:
            self.hotkey_btn.configure(
                fg_color="#d97706",
                hover_color="#b45309",
                text_color="#ffffff",
            )

        self._last_eq_sig = None
        self._last_wave_idle = False
        self._update_hotkey_hint()
        if self._active_tab_key == "tab_eq":
            self._schedule_eq_redraw()
        try:
            self.update_idletasks()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Guia Discord & Fechamento / Bandeja
    # ------------------------------------------------------------------ #
    def _open_discord_guide(self):
        existing = getattr(self, "_discord_win", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass

        th = self._c()
        win = ctk.CTkToplevel(self)
        self._discord_win = win
        win.title(self._t("discord_title"))
        win.geometry("540x400")
        win.configure(fg_color=th["modal_bg"])
        win.transient(self)

        def _close_discord():
            self._discord_win = None
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", _close_discord)

        ctk.CTkLabel(
            win, text=self._t("discord_header"), font=self._fonts["h2_b"], text_color=th["accent"]
        ).pack(anchor="w", padx=20, pady=(18, 10))
        ctk.CTkLabel(
            win, text=self._t("discord_body"), justify="left", font=self._fonts["sm"], text_color=th["text_body"], wraplength=500
        ).pack(anchor="w", padx=20, pady=4)
        ctk.CTkButton(
            win,
            text=self._t("got_it"),
            width=120,
            height=32,
            corner_radius=8,
            fg_color=th["control_bg"],
            hover_color=th["control_hover"],
            text_color=th["text_primary"],
            border_width=1,
            border_color=th["control_border"],
            command=_close_discord,
        ).pack(pady=16)
        win.lift()
        win.focus_force()

    # ------------------------------------------------------------------ #
    # Tecla de Atalho Configurável (Global mesmo em 2º plano / jogos)
    # ------------------------------------------------------------------ #
    def _format_hotkey_label(self, spec: str) -> str:
        if not spec:
            return self._t("define_key")
        nice = {
            "ctrl": "Ctrl",
            "ctrl_l": self._t("hk_ctrl_l"),
            "ctrl_r": self._t("hk_ctrl_r"),
            "shift": "Shift",
            "shift_l": self._t("hk_shift_l"),
            "shift_r": self._t("hk_shift_r"),
            "alt": "Alt",
            "alt_l": self._t("hk_alt_l"),
            "alt_r": self._t("hk_alt_r"),
            "alt_gr": "AltGr",
            "caps_lock": "Caps Lock",
            "space": self._t("hk_space"),
            "tab": "Tab",
            "enter": "Enter",
            "backspace": "Backspace",
            "insert": "Insert",
            "delete": "Delete",
            "home": "Home",
            "end": "End",
            "page_up": "Page Up",
            "page_down": "Page Down",
            "pause": "Pause",
            "scroll_lock": "Scroll Lock",
            "print_screen": "Print Screen",
            "mouse4": self._t("hk_mouse4"),
            "mouse5": self._t("hk_mouse5"),
            "up": "↑",
            "down": "↓",
            "left": "←",
            "right": "→",
        }
        parts = [nice.get(p, p.upper()) for p in spec.split("+") if p]
        return " + ".join(parts) if parts else self._t("define_key")

    @staticmethod
    def _token_to_win32_vks(tok: str) -> tuple[int, ...]:
        vk_map = {
            "ctrl": (0x11,),
            "ctrl_l": (0xA2,),
            "ctrl_r": (0xA3,),
            "shift": (0x10,),
            "shift_l": (0xA0,),
            "shift_r": (0xA1,),
            "alt": (0x12,),
            "alt_l": (0xA4,),
            "alt_r": (0xA5,),
            "alt_gr": (0xA5,),
            "caps_lock": (0x14,),
            "space": (0x20,),
            "tab": (0x09,),
            "enter": (0x0D,),
            "backspace": (0x08,),
            "insert": (0x2D,),
            "delete": (0x2E,),
            "home": (0x24,),
            "end": (0x23,),
            "page_up": (0x21,),
            "page_down": (0x22,),
            "pause": (0x13,),
            "scroll_lock": (0x91,),
            "print_screen": (0x2C,),
            "left": (0x25,),
            "up": (0x26,),
            "right": (0x27,),
            "down": (0x28,),
            "mouse4": (0x05,),
            "mouse5": (0x06,),
        }
        if tok in vk_map:
            return vk_map[tok]
        if tok.startswith("f") and tok[1:].isdigit():
            num = int(tok[1:])
            if 1 <= num <= 24:
                return (0x70 + num - 1,)
        if len(tok) == 1:
            ch = tok.upper()
            if ("A" <= ch <= "Z") or ("0" <= ch <= "9"):
                return (ord(ch),)
            if sys.platform == "win32":
                try:
                    res = ctypes.windll.user32.VkKeyScanW(ord(tok))
                    if (res & 0xFF) != 0xFF:
                        return (res & 0xFF,)
                except Exception:
                    pass
        return ()

    @staticmethod
    def _normalize_tk_keysym(keysym: str) -> str | None:
        if not keysym:
            return None
        low = keysym.lower()
        mapping = {
            "control_l": "ctrl_l",
            "control_r": "ctrl_r",
            "shift_l": "shift_l",
            "shift_r": "shift_r",
            "alt_l": "alt_l",
            "alt_r": "alt_r",
            "iso_level3_shift": "alt_gr",
            "caps_lock": "caps_lock",
            "return": "enter",
            "kp_enter": "enter",
            "prior": "page_up",
            "next": "page_down",
            "print": "print_screen",
            "break": "pause",
        }
        if low in mapping:
            return mapping[low]
        if low in {
            "space", "tab", "backspace", "insert", "delete", "home", "end",
            "pause", "scroll_lock", "up", "down", "left", "right",
        }:
            return low
        if low.startswith("f") and low[1:].isdigit():
            num = int(low[1:])
            if 1 <= num <= 24:
                return low
        if len(keysym) == 1 and keysym.isprintable():
            return keysym.lower()
        return None

    @staticmethod
    def _normalize_pynput_key(key) -> str | None:
        if pynput_kb is None:
            return None
        if isinstance(key, pynput_kb.Key):
            name = str(key.name).lower()
            if name == "return":
                return "enter"
            return name
        vk = getattr(key, "vk", None)
        if isinstance(vk, int):
            if 65 <= vk <= 90:
                return chr(vk).lower()
            if 48 <= vk <= 57:
                return chr(vk)
            if 112 <= vk <= 135:
                return f"f{vk - 111}"
            if vk == 32:
                return "space"
        ch = getattr(key, "char", None)
        if isinstance(ch, str) and len(ch) == 1 and ord(ch) >= 32:
            return ch.lower()
        return None

    @staticmethod
    def _hotkey_matches(spec: str, pressed: set[str]) -> bool:
        if not spec:
            return False
        tokens = [t for t in spec.split("+") if t]
        if not tokens:
            return False
        for tok in tokens:
            if tok == "ctrl":
                if not (pressed & {"ctrl", "ctrl_l", "ctrl_r"}):
                    return False
            elif tok == "shift":
                if not (pressed & {"shift", "shift_l", "shift_r"}):
                    return False
            elif tok == "alt":
                if not (pressed & {"alt", "alt_l", "alt_r", "alt_gr"}):
                    return False
            elif tok not in pressed:
                return False
        return True

    def _has_global_hotkey_backend(self) -> bool:
        return (sys.platform == "win32") or (self._kb_listener is not None) or (pynput_kb is not None)

    def _update_hotkey_hint(self):
        if not hasattr(self, "hotkey_hint_lbl"):
            return
        th = self._c()
        lbl_key = self._format_hotkey_label(self.hotkey_spec)
        is_normal = bool(self.bypass_var.get())
        state_txt = self._t("hk_normal") if is_normal else self._t("hk_active")
        color = "#f59e0b" if is_normal else th["accent"]
        if not self.hotkey_en_var.get():
            self.hotkey_hint_lbl.configure(
                text=f"● {state_txt} ({self._t('hk_disabled')})",
                text_color=th["text_muted"],
            )
        elif self.hotkey_hold_var.get():
            hint_scope = self._t("hk_global") if self._has_global_hotkey_backend() else self._t("hk_window")
            self.hotkey_hint_lbl.configure(
                text=f"● {state_txt} | {self._t('hk_hold')} {lbl_key} • {hint_scope}",
                text_color=color,
            )
        else:
            hint_scope = self._t("hk_global") if self._has_global_hotkey_backend() else self._t("hk_window")
            self.hotkey_hint_lbl.configure(
                text=f"● {state_txt} | {self._t('hk_press')} {lbl_key} • {hint_scope}",
                text_color=color,
            )

    def _sync_hotkey_cache(self):
        self._hotkey_enabled_cached = bool(self.hotkey_en_var.get())
        self._hotkey_hold_cached = bool(self.hotkey_hold_var.get())

    def _on_hotkey_setting_changed(self):
        self._sync_hotkey_cache()
        with self._hotkey_lock:
            self._hotkey_is_down = False
            self._hold_base_bypass = None
        self._update_hotkey_hint()
        self._save_config()

    def _toggle_hotkey_capture(self):
        if self._capturing_hotkey:
            self._stop_hotkey_capture(cancelled=True)
            return
        self._capturing_hotkey = True
        self._capture_mods.clear()
        with self._hotkey_lock:
            self._hotkey_is_down = False
            self._hold_base_bypass = None
        self.hotkey_btn.configure(
            text=self._t("press_key_prompt"),
            fg_color="#d97706",
            hover_color="#b45309",
            text_color="#ffffff",
        )
        self.focus_force()
        self._cap_press_id = self.bind("<KeyPress>", self._on_capture_keypress, add="+")
        self._cap_release_id = self.bind("<KeyRelease>", self._on_capture_keyrelease, add="+")
        if sys.platform == "win32":
            self.after(30, self._poll_win32_mouse_capture)

    def _poll_win32_mouse_capture(self):
        if not self._capturing_hotkey or sys.platform != "win32":
            return
        try:
            u32 = ctypes.windll.user32
            if u32.GetAsyncKeyState(0x05) & 0x8000:
                self.hotkey_spec = "mouse4"
                self._stop_hotkey_capture(cancelled=False)
                return
            if u32.GetAsyncKeyState(0x06) & 0x8000:
                self.hotkey_spec = "mouse5"
                self._stop_hotkey_capture(cancelled=False)
                return
        except Exception:
            pass
        self.after(30, self._poll_win32_mouse_capture)

    def _stop_hotkey_capture(self, cancelled: bool = False):
        self._capturing_hotkey = False
        self._capture_mods.clear()
        try:
            if hasattr(self, "_cap_press_id"):
                self.unbind("<KeyPress>", self._cap_press_id)
            if hasattr(self, "_cap_release_id"):
                self.unbind("<KeyRelease>", self._cap_release_id)
        except Exception:
            pass
        th = self._c()
        self.hotkey_btn.configure(
            text=self._format_hotkey_label(self.hotkey_spec),
            fg_color=th["control_bg"],
            hover_color=th["control_hover"],
            text_color=th["text_primary"],
        )
        self._update_hotkey_hint()
        if not cancelled:
            self._save_config()

    def _on_capture_keypress(self, event):
        if not self._capturing_hotkey:
            return
        if str(event.keysym).lower() == "escape":
            self._stop_hotkey_capture(cancelled=True)
            return "break"
        tok = self._normalize_tk_keysym(event.keysym)
        if not tok:
            return "break"
        mod_tokens = {"ctrl_l", "ctrl_r", "shift_l", "shift_r", "alt_l", "alt_r", "alt_gr"}
        if tok in mod_tokens:
            self._capture_mods.add(tok)
            return "break"

        parts = []
        if self._capture_mods & {"ctrl_l", "ctrl_r"}:
            parts.append("ctrl")
        if self._capture_mods & {"alt_l", "alt_r", "alt_gr"}:
            parts.append("alt")
        if self._capture_mods & {"shift_l", "shift_r"}:
            parts.append("shift")
        parts.append(tok)
        self.hotkey_spec = "+".join(parts)
        self._stop_hotkey_capture(cancelled=False)
        return "break"

    def _on_capture_keyrelease(self, event):
        if not self._capturing_hotkey:
            return
        tok = self._normalize_tk_keysym(event.keysym)
        if tok and tok in self._capture_mods:
            self.hotkey_spec = tok
            self._stop_hotkey_capture(cancelled=False)
            return "break"

    def _win32_hotkey_loop(self):
        user32 = ctypes.windll.user32
        while not self._win32_stop_event.is_set() and not self._is_quitting:
            if not self._capturing_hotkey and self._hotkey_enabled_cached and self.hotkey_spec:
                tokens = [t for t in self.hotkey_spec.split("+") if t]
                vk_groups = [self._token_to_win32_vks(t) for t in tokens]
                if vk_groups and all(vg for vg in vk_groups):
                    is_down = all(any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in vg) for vg in vk_groups)
                    hold = self._hotkey_hold_cached
                    with self._hotkey_lock:
                        if is_down and not self._hotkey_is_down:
                            self._hotkey_is_down = True
                            if hold:
                                self.after(0, self._on_hotkey_hold_down)
                            else:
                                self.after(0, self._on_hotkey_toggle)
                        elif not is_down and self._hotkey_is_down:
                            self._hotkey_is_down = False
                            if hold:
                                self.after(0, self._on_hotkey_hold_up)
            time.sleep(0.012)

    def _start_hotkey_listener(self):
        self._sync_hotkey_cache()
        # No Windows, usa API nativa GetAsyncKeyState: funciona globalmente mesmo minimizado/bandeja/jogos sem depender de pynput
        if sys.platform == "win32":
            self._win32_stop_event.clear()
            self._win32_thread = threading.Thread(target=self._win32_hotkey_loop, daemon=True)
            self._win32_thread.start()
            self._update_hotkey_hint()
            return

        if pynput_kb is not None:
            def on_press(key):
                if self._is_quitting or self._capturing_hotkey or not self._hotkey_enabled_cached:
                    return
                tok = self._normalize_pynput_key(key)
                if not tok:
                    return
                with self._hotkey_lock:
                    self._pressed_keys.add(tok)
                    matched = self._hotkey_matches(self.hotkey_spec, self._pressed_keys)
                    if matched and not self._hotkey_is_down:
                        self._hotkey_is_down = True
                        hold = self._hotkey_hold_cached
                        if hold:
                            self.after(0, self._on_hotkey_hold_down)
                        else:
                            self.after(0, self._on_hotkey_toggle)

            def on_release(key):
                tok = self._normalize_pynput_key(key)
                if not tok:
                    return
                with self._hotkey_lock:
                    self._pressed_keys.discard(tok)
                    if self._hotkey_is_down and not self._hotkey_matches(self.hotkey_spec, self._pressed_keys):
                        self._hotkey_is_down = False
                        if self._hotkey_hold_cached and not self._capturing_hotkey and self._hotkey_enabled_cached:
                            self.after(0, self._on_hotkey_hold_up)

            try:
                self._kb_listener = pynput_kb.Listener(on_press=on_press, on_release=on_release)
                self._kb_listener.daemon = True
                self._kb_listener.start()
                self._update_hotkey_hint()
                return
            except Exception:
                self._kb_listener = None

        # Fallback dentro da janela caso não esteja no Windows e pynput não esteja instalado
        self.bind("<KeyPress>", self._on_tk_fallback_keypress, add="+")
        self.bind("<KeyRelease>", self._on_tk_fallback_keyrelease, add="+")
        self._update_hotkey_hint()

    def _stop_hotkey_listener(self):
        self._win32_stop_event.set()
        if self._kb_listener is not None:
            try:
                self._kb_listener.stop()
            except Exception:
                pass
            self._kb_listener = None

    def _on_tk_fallback_keypress(self, event):
        if self._capturing_hotkey or not self.hotkey_en_var.get():
            return
        tok = self._normalize_tk_keysym(event.keysym)
        if not tok:
            return
        with self._hotkey_lock:
            self._pressed_keys.add(tok)
            if self._hotkey_matches(self.hotkey_spec, self._pressed_keys) and not self._hotkey_is_down:
                self._hotkey_is_down = True
                if self.hotkey_hold_var.get():
                    self._on_hotkey_hold_down()
                else:
                    self._on_hotkey_toggle()

    def _on_tk_fallback_keyrelease(self, event):
        tok = self._normalize_tk_keysym(event.keysym)
        if not tok:
            return
        with self._hotkey_lock:
            self._pressed_keys.discard(tok)
            if self._hotkey_is_down and not self._hotkey_matches(self.hotkey_spec, self._pressed_keys):
                self._hotkey_is_down = False
                if self.hotkey_hold_var.get() and not self._capturing_hotkey and self.hotkey_en_var.get():
                    self._on_hotkey_hold_up()

    def _set_bypass_state(self, bypass_val: bool):
        self.bypass_var.set(bool(bypass_val))
        self._on_param_change()

    def _on_hotkey_toggle(self):
        self._set_bypass_state(not bool(self.bypass_var.get()))

    def _on_hotkey_hold_down(self):
        if self._hold_base_bypass is None:
            self._hold_base_bypass = bool(self.bypass_var.get())
        self._set_bypass_state(not self._hold_base_bypass)

    def _on_hotkey_hold_up(self):
        if self._hold_base_bypass is not None:
            base = self._hold_base_bypass
            self._hold_base_bypass = None
            self._set_bypass_state(base)

    def _on_close(self):
        if (
            self._is_loaded
            and not self._is_quitting
            and hasattr(self, "minimize_to_tray_var")
            and self.minimize_to_tray_var.get()
            and self._tray_icon is not None
        ):
            self._minimize_to_tray()
            return
        self._quit_app()

    def _quit_app(self):
        if getattr(self, "_quit_executed", False):
            return
        self._quit_executed = True
        self._is_quitting = True
        self._audio_op_seq += 1

        # Garante encerramento definitivo mesmo se algum driver de áudio/Win32 segurar uma thread
        safety_timer = threading.Timer(0.75, lambda: os._exit(0))
        safety_timer.daemon = True
        safety_timer.start()

        for job_attr in ("_splash_anim_job", "_ui_loop_job", "_eq_redraw_job"):
            job = getattr(self, job_attr, None)
            if job is not None:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
                setattr(self, job_attr, None)

        if self._is_loaded:
            try:
                self._stop_hotkey_listener()
            except Exception:
                pass
            try:
                self._save_config()
            except Exception:
                pass
            router = getattr(self, "router", None)
            if router is not None:
                try:
                    router.abort_start()
                except Exception:
                    pass
                stop_t = threading.Thread(target=router.stop, daemon=True)
                stop_t.start()
                stop_t.join(timeout=0.45)

        tray_icon = self._tray_icon
        self._tray_icon = None
        if tray_icon is not None:
            tray_t = threading.Thread(target=tray_icon.stop, daemon=True)
            tray_t.start()
            tray_t.join(timeout=0.25)

        if _SINGLE_INSTANCE is not None:
            try:
                _SINGLE_INSTANCE.release()
            except Exception:
                pass

        for attr in ("_settings_win", "_update_win", "_discord_win"):
            sub = getattr(self, attr, None)
            if sub is not None:
                try:
                    sub.destroy()
                except Exception:
                    pass
                setattr(self, attr, None)

        try:
            self.quit()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    _SINGLE_INSTANCE = _VoxCraftSingleInstance()
    _wait_sec = 2.5 if "--relaunch" in sys.argv else 0.0
    if not _SINGLE_INSTANCE.acquire(wait_timeout=_wait_sec):
        if "--relaunch" not in sys.argv:
            _SINGLE_INSTANCE.notify_existing()
        sys.exit(0)

    app = VoxCraftApp()
    _SINGLE_INSTANCE.start_ipc_server(lambda: app.after(0, app._restore_from_tray))
    try:
        app.mainloop()
    finally:
        _SINGLE_INSTANCE.release()
    os._exit(0)
