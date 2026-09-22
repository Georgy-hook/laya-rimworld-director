from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .services import BASE_DIR, RESOURCE_DIR
from .theme import COLORS, FONTS, ShadowCard, configure_styles


DEFAULT_RIMWORLD = Path(r"C:\Program Files (x86)\Steam\steamapps\common\RimWorld")

SETUP_TEXT = {
    "ru": {
        "title": "Установка Laya", "subtitle": "Несколько понятных шагов — без командной строки.",
        "game": "Папка RimWorld", "browse": "Выбрать…", "device": "Как запускать модель", "auto": "Автоматически", "cuda": "Видеокарта NVIDIA", "cpu": "Процессор",
        "install": "Установить всё", "working": "Установка…", "ready": "Готово к установке", "python_missing": "Python 3.10–3.12 не найден. Открыть страницу загрузки Python?",
        "done": "Установка завершена. Включите Harmony и RIMAPI — Laya Director в списке модов RimWorld, перезапустите игру и откройте Laya-Control-Center.exe.",
        "invalid": "В выбранной папке не найден RimWorldWin64.exe.", "error": "Не удалось завершить установку",
        "step_python": "Создаю отдельное окружение Python…", "step_packages": "Устанавливаю модель и необходимые пакеты…", "step_mod": "Подключаю игровой мод…", "step_config": "Сохраняю настройки…",
        "privacy": "Модель работает локально. Установщик не просит ключ API и не отправляет сохранения в интернет.",
    },
    "en": {
        "title": "Install Laya", "subtitle": "A few clear steps, with no command line required.",
        "game": "RimWorld folder", "browse": "Browse…", "device": "Run the model using", "auto": "Automatic", "cuda": "NVIDIA GPU", "cpu": "CPU",
        "install": "Install everything", "working": "Installing…", "ready": "Ready to install", "python_missing": "Python 3.10–3.12 was not found. Open the Python download page?",
        "done": "Installation is complete. Enable Harmony and RIMAPI — Laya Director in RimWorld's mod list, restart the game, then open Laya-Control-Center.exe.",
        "invalid": "RimWorldWin64.exe was not found in the selected folder.", "error": "Setup could not finish",
        "step_python": "Creating an isolated Python environment…", "step_packages": "Installing the model and required packages…", "step_mod": "Connecting the game mod…", "step_config": "Saving settings…",
        "privacy": "The model runs locally. Setup does not ask for an API key or upload save files.",
    },
}


class SetupWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        if os.environ.get("LAYA_GUI_SMOKE_TEST") == "1":
            self.withdraw()
        self.language = "ru"
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.title("Laya Setup 0.0.2")
        self.geometry("760x620")
        self.resizable(False, False)
        self.configure(bg=COLORS["window"])
        configure_styles(self)
        self.rimworld_var = tk.StringVar(value=str(DEFAULT_RIMWORLD))
        self.device_code = "auto"
        self.device_var = tk.StringVar(value="")
        self._build()
        self.after(100, self._poll_events)

    def t(self, key: str) -> str:
        return SETUP_TEXT[self.language][key]

    def _build(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        header = tk.Frame(self, bg=COLORS["sidebar"], height=155)
        header.pack(fill="x")
        header.pack_propagate(False)
        asset = RESOURCE_DIR / "assets" / "gui" / "laya-orbit-mascot.png"
        try:
            original = tk.PhotoImage(file=str(asset))
            self.mascot = original.subsample(10, 10)
            tk.Label(header, image=self.mascot, bg=COLORS["sidebar"]).pack(side="left", padx=26)
        except tk.TclError:
            tk.Label(header, text="✦", bg=COLORS["sidebar"], fg=COLORS["cyan"], font=("Segoe UI Symbol", 44)).pack(side="left", padx=35)
        title_box = tk.Frame(header, bg=COLORS["sidebar"])
        title_box.pack(side="left", fill="y", pady=30)
        tk.Label(title_box, text=self.t("title"), bg=COLORS["sidebar"], fg=COLORS["text"], font=FONTS["display"]).pack(anchor="w")
        tk.Label(title_box, text=self.t("subtitle"), bg=COLORS["sidebar"], fg=COLORS["muted"], font=FONTS["body"]).pack(anchor="w", pady=(4, 0))
        tk.Button(header, text="EN" if self.language == "ru" else "RU", command=self._toggle_language, bg=COLORS["panel_alt"], fg=COLORS["cyan"], relief="flat", padx=12, pady=7).pack(side="right", padx=22, pady=22, anchor="ne")

        card = ShadowCard(self, padx=22, pady=20)
        card.pack(fill="both", expand=True, padx=24, pady=22)
        tk.Label(card.body, text=self.t("game"), bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["heading"]).pack(anchor="w")
        folder = tk.Frame(card.body, bg=COLORS["panel"])
        folder.pack(fill="x", pady=(8, 18))
        tk.Entry(folder, textvariable=self.rimworld_var, bg=COLORS["panel_alt"], fg=COLORS["text"], insertbackground=COLORS["cyan"], relief="flat", font=FONTS["body"]).pack(side="left", fill="x", expand=True, ipady=8)
        ttk.Button(folder, text=self.t("browse"), style="Soft.TButton", command=self._browse).pack(side="right", padx=(8, 0))

        tk.Label(card.body, text=self.t("device"), bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["heading"]).pack(anchor="w")
        device_labels = {"auto": self.t("auto"), "cuda": self.t("cuda"), "cpu": self.t("cpu")}
        self.device_var.set(device_labels.get(self.device_code, self.t("auto")))
        self.device = ttk.Combobox(card.body, state="readonly", textvariable=self.device_var, values=tuple(device_labels.values()), width=28)
        self.device.bind("<<ComboboxSelected>>", lambda _event: setattr(self, "device_code", next((key for key, value in device_labels.items() if value == self.device_var.get()), "auto")))
        self.device.pack(anchor="w", pady=(8, 18))
        tk.Label(card.body, text=self.t("privacy"), bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["small"], justify="left", wraplength=650).pack(anchor="w", pady=(0, 14))
        self.progress = ttk.Progressbar(card.body, mode="indeterminate")
        self.progress.pack(fill="x", pady=(4, 7))
        self.status = tk.Label(card.body, text=self.t("ready"), bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["small"])
        self.status.pack(anchor="w")
        self.install_button = ttk.Button(card.body, text=self.t("install"), style="Accent.TButton", command=self._begin)
        self.install_button.pack(side="bottom", anchor="e", pady=(16, 0))

    def _toggle_language(self) -> None:
        self.language = "en" if self.language == "ru" else "ru"
        self._build()

    def _browse(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.rimworld_var.get() or str(DEFAULT_RIMWORLD))
        if selected:
            self.rimworld_var.set(selected)

    def _begin(self) -> None:
        rimworld = Path(self.rimworld_var.get()).resolve()
        if not (rimworld / "RimWorldWin64.exe").exists():
            messagebox.showerror(self.t("title"), self.t("invalid"))
            return
        python = self._find_python()
        if not python:
            if messagebox.askyesno(self.t("title"), self.t("python_missing")):
                webbrowser.open("https://www.python.org/downloads/windows/")
            return
        self.install_button.configure(state="disabled", text=self.t("working"))
        self.progress.start(12)
        threading.Thread(target=self._install, args=(python, rimworld, self.device_code), daemon=True).start()

    @staticmethod
    def _find_python() -> Path | None:
        candidates = []
        if not getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable))
        for name in ("py", "python"):
            executable = shutil.which(name)
            if not executable:
                continue
            command = [executable, "-3.12", "-c", "import sys;print(sys.executable)"] if name == "py" else [executable, "-c", "import sys;print(sys.executable)"]
            try:
                output = subprocess.check_output(command, text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
                candidates.append(Path(output))
            except (OSError, subprocess.SubprocessError):
                pass
        for candidate in candidates:
            try:
                version = subprocess.check_output([str(candidate), "-c", "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')"], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
                major, minor = map(int, version.split("."))
                if major == 3 and 10 <= minor <= 12:
                    return candidate
            except (OSError, ValueError, subprocess.SubprocessError):
                continue
        return None

    def _emit(self, kind: str, value: str) -> None:
        self.events.put((kind, value))

    def _run(self, args: list[str]) -> None:
        subprocess.run(args, cwd=BASE_DIR, check=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def _install(self, python: Path, rimworld: Path, device: str) -> None:
        try:
            venv = BASE_DIR / ".venv"
            venv_python = venv / "Scripts" / "python.exe"
            self._emit("status", self.t("step_python"))
            if not venv_python.exists():
                self._run([str(python), "-m", "venv", str(venv)])
            self._emit("status", self.t("step_packages"))
            self._run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
            self._run([str(venv_python), "-m", "pip", "install", "-r", str(BASE_DIR / "requirements.txt")])
            self._emit("status", self.t("step_mod"))
            source = (BASE_DIR / "vendor" / "RIMAPI").resolve()
            mods = (rimworld / "Mods").resolve()
            target = (mods / "RIMAPI").resolve()
            if mods not in target.parents or not source.exists():
                raise RuntimeError("Invalid RIMAPI source or target path")
            if target.exists():
                backup = mods / f"RIMAPI.backup-{datetime.now():%Y%m%d-%H%M%S}"
                shutil.move(str(target), str(backup))
            shutil.copytree(source, target)
            self._emit("status", self.t("step_config"))
            config = {
                "python_exe": str(venv_python), "director_script": str(BASE_DIR / "colony_director.py"),
                "api_url": "http://localhost:8765", "device": device, "interval": 10,
            }
            (BASE_DIR / "laya-control.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            self._emit("done", self.t("done"))
        except Exception as exc:
            self._emit("error", f"{self.t('error')}: {exc}")

    def _poll_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                self.status.configure(text=value, fg=COLORS["red"] if kind == "error" else COLORS["green"] if kind == "done" else COLORS["muted"])
                if kind in {"done", "error"}:
                    self.progress.stop()
                    self.install_button.configure(state="normal", text=self.t("install"))
                    (messagebox.showinfo if kind == "done" else messagebox.showerror)(self.t("title"), value)
        except queue.Empty:
            pass
        self.after(100, self._poll_events)


def run() -> None:
    SetupWindow().mainloop()
