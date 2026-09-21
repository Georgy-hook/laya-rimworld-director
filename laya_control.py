from __future__ import annotations

import csv
import ctypes
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, filedialog, messagebox
import tkinter as tk
from tkinter import ttk
from urllib.error import URLError
from urllib.request import Request, urlopen


APP_NAME = "Laya Control Center 0.0.1"
BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "laya-control.json"
DEFAULT_CONFIG = {
    "python_exe": str(BASE_DIR / ".venv" / "Scripts" / "python.exe"),
    "director_script": str(BASE_DIR / "colony_director.py"),
    "api_url": "http://localhost:8765",
    "device": "cuda",
    "interval": 10,
}


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    try:
        loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            config.update(loaded)
    except (OSError, json.JSONDecodeError):
        pass
    for key in ("python_exe", "director_script"):
        value = Path(str(config[key]))
        if not value.is_absolute():
            config[key] = str((BASE_DIR / value).resolve())
    return config


def process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    process = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if not process:
        return False
    ctypes.windll.kernel32.CloseHandle(process)
    return True


def read_pid(path: Path) -> int | None:
    try:
        pid = int(path.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return None
    if process_running(pid):
        return pid
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    return None


def tail_jsonl(path: Path, limit: int = 500) -> list[dict]:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            block = 65536
            data = b""
            while size > 0 and data.count(b"\n") <= limit:
                take = min(block, size)
                size -= take
                handle.seek(size)
                data = handle.read(take) + data
        rows = []
        for line in data.splitlines()[-limit:]:
            try:
                value = json.loads(line.decode("utf-8"))
                if isinstance(value, dict):
                    rows.append(value)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        return rows
    except OSError:
        return []


def request_json(url: str, method: str = "GET") -> dict:
    req = Request(url, method=method, headers={"Accept": "application/json"})
    with urlopen(req, timeout=1.5) as response:
        return json.loads(response.read().decode("utf-8-sig"))


class ControlCenter(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.config_data = load_config()
        self.log_dir = BASE_DIR / "logs"
        self.log_path = self.log_dir / "decisions.jsonl"
        self.state_path = self.log_dir / "colony-state.json"
        self.pid_path = self.log_dir / "director.pid"
        self.records: list[dict] = []
        self.last_log_signature: tuple[int, int] | None = None
        self.game_online = False
        self.title(APP_NAME)
        self.geometry("1180x760")
        self.minsize(900, 600)
        self.configure(bg="#10151d")
        self._build_style()
        self._build_ui()
        self.after(200, self.refresh_all)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background="#10151d", foreground="#e6edf3", fieldbackground="#18202b")
        style.configure("TFrame", background="#10151d")
        style.configure("Card.TFrame", background="#18202b")
        style.configure("TLabel", background="#10151d", foreground="#e6edf3", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 18), foreground="#f0f6fc")
        style.configure("Status.TLabel", font=("Segoe UI Semibold", 10))
        style.configure("TButton", padding=(13, 8), font=("Segoe UI Semibold", 9))
        style.map("TButton", background=[("active", "#2f81f7")])
        style.configure("Treeview", background="#131a23", fieldbackground="#131a23", foreground="#d8dee9", rowheight=28)
        style.configure("Treeview.Heading", background="#212b38", foreground="#f0f6fc", font=("Segoe UI Semibold", 9))
        style.map("Treeview", background=[("selected", "#1f6feb")])

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=X, padx=18, pady=(16, 10))
        ttk.Label(header, text="Laya Control Center", style="Title.TLabel").pack(side=LEFT)
        self.game_label = ttk.Label(header, text="● RimWorld API: проверка…", style="Status.TLabel")
        self.game_label.pack(side=RIGHT, padx=(18, 0))
        self.laya_label = ttk.Label(header, text="● Laya: проверка…", style="Status.TLabel")
        self.laya_label.pack(side=RIGHT)

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=X, padx=18, pady=(0, 12))
        ttk.Button(toolbar, text="▶ Запустить Laya", command=self.start_laya).pack(side=LEFT, padx=(0, 7))
        ttk.Button(toolbar, text="■ Остановить", command=self.stop_laya).pack(side=LEFT, padx=(0, 7))
        ttk.Button(toolbar, text="⏸ Пауза RimWorld", command=lambda: self.set_speed(0)).pack(side=LEFT, padx=(0, 7))
        ttk.Button(toolbar, text="▶ Продолжить", command=lambda: self.set_speed(1)).pack(side=LEFT, padx=(0, 7))
        ttk.Button(toolbar, text="Экспорт истории", command=self.export_history).pack(side=RIGHT, padx=(7, 0))
        ttk.Button(toolbar, text="Экспорт Laya", command=self.export_bundle).pack(side=RIGHT, padx=(7, 0))
        ttk.Button(toolbar, text="Открыть папку", command=lambda: os.startfile(BASE_DIR)).pack(side=RIGHT)

        self.doctrine_label = ttk.Label(
            self,
            text="Доктрина: Laya ещё не выбрала долгосрочное направление",
            foreground="#d2a8ff",
        )
        self.doctrine_label.pack(fill=X, padx=20, pady=(0, 10))

        paned = ttk.Panedwindow(self, orient=tk.VERTICAL)
        paned.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        history_frame = ttk.Frame(paned, style="Card.TFrame")
        details_frame = ttk.Frame(paned, style="Card.TFrame")
        paned.add(history_frame, weight=3)
        paned.add(details_frame, weight=2)

        columns = ("time", "mode", "choice", "confidence", "result")
        self.tree = ttk.Treeview(history_frame, columns=columns, show="headings", selectmode="browse")
        headings = {"time": "Время", "mode": "Режим", "choice": "Выбор Laya", "confidence": "Уверенность", "result": "Результат"}
        widths = {"time": 150, "mode": 135, "choice": 245, "confidence": 105, "result": 470}
        for name in columns:
            self.tree.heading(name, text=headings[name])
            self.tree.column(name, width=widths[name], anchor="w")
        scroll = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True, padx=(10, 0), pady=10)
        scroll.pack(side=RIGHT, fill=Y, padx=(0, 10), pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.show_selected)

        ttk.Label(details_frame, text="Состояние и все варианты выбора", font=("Segoe UI Semibold", 11), background="#18202b").pack(anchor="w", padx=12, pady=(10, 5))
        self.details = tk.Text(
            details_frame, bg="#0d1117", fg="#c9d1d9", insertbackground="#ffffff",
            relief="flat", font=("Cascadia Mono", 9), wrap="word", padx=10, pady=8,
        )
        self.details.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        self.footer = ttk.Label(self, text="Готово", foreground="#8b949e")
        self.footer.pack(fill=X, padx=20, pady=(0, 10))

    def start_laya(self) -> None:
        if read_pid(self.pid_path):
            messagebox.showinfo(APP_NAME, "Laya уже запущена.")
            return
        python_exe = Path(self.config_data["python_exe"])
        director = Path(self.config_data["director_script"])
        if not python_exe.exists() or not director.exists():
            messagebox.showerror(APP_NAME, f"Не найден Python или директор.\n{python_exe}\n{director}")
            return
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stdout = (self.log_dir / "director.stdout.log").open("ab")
        stderr = (self.log_dir / "director.stderr.log").open("ab")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        args = [
            str(python_exe), "-u", str(director),
            "--device", str(self.config_data.get("device", "cuda")),
            "--interval", str(self.config_data.get("interval", 10)),
            "--api-url", str(self.config_data.get("api_url", "http://localhost:8765")),
            "--log", str(self.log_path), "--state", str(self.state_path), "--pid-file", str(self.pid_path),
        ]
        try:
            process = subprocess.Popen(args, cwd=BASE_DIR, stdout=stdout, stderr=stderr, creationflags=flags)
            self.pid_path.write_text(str(process.pid), encoding="ascii")
            self.footer.configure(text=f"Laya запускается, PID {process.pid}. Загрузка модели может занять несколько секунд.")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Не удалось запустить Laya: {exc}")
        finally:
            stdout.close()
            stderr.close()

    def stop_laya(self) -> None:
        pid = read_pid(self.pid_path)
        if not pid:
            self.footer.configure(text="Laya уже остановлена.")
            return
        try:
            os.kill(pid, signal.SIGTERM)
            self.pid_path.unlink(missing_ok=True)
            self.footer.configure(text=f"Laya остановлена (PID {pid}).")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Не удалось остановить процесс {pid}: {exc}")

    def set_speed(self, speed: int) -> None:
        url = f"{str(self.config_data['api_url']).rstrip('/')}/api/v1/game/speed?speed={speed}"
        try:
            result = request_json(url, method="POST")
            if not result.get("success", False):
                raise RuntimeError("; ".join(result.get("errors") or ["неизвестная ошибка"]))
            self.footer.configure(text="RimWorld поставлен на паузу." if speed == 0 else "RimWorld продолжен на обычной скорости.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Команда RimWorld не выполнена: {exc}")

    def export_history(self) -> None:
        target = filedialog.asksaveasfilename(
            title="Экспорт истории Laya", defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("JSON Lines", "*.jsonl")],
            initialfile=f"laya-history-{datetime.now():%Y%m%d-%H%M}.csv",
        )
        if not target:
            return
        destination = Path(target)
        try:
            if destination.suffix.lower() == ".jsonl":
                shutil.copy2(self.log_path, destination)
            else:
                records = tail_jsonl(self.log_path, limit=100000)
                with destination.open("w", encoding="utf-8-sig", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["timestamp", "mode", "choice", "confidence", "candidates", "result"])
                    for row in records:
                        decision = row.get("decision") or {}
                        writer.writerow([
                            row.get("timestamp"), row.get("mode"), decision.get("choice"), decision.get("confidence"),
                            ", ".join(row.get("candidates") or []), json.dumps(row.get("result"), ensure_ascii=False),
                        ])
            self.footer.configure(text=f"История экспортирована: {destination}")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Ошибка экспорта: {exc}")

    def export_bundle(self) -> None:
        target = filedialog.asksaveasfilename(
            title="Экспорт Laya", defaultextension=".zip", filetypes=[("ZIP", "*.zip")],
            initialfile=f"laya-export-{datetime.now():%Y%m%d-%H%M}.zip",
        )
        if not target:
            return
        try:
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
                for pattern in ("*.py", "*.md", "*.ps1", "*.json"):
                    for path in BASE_DIR.glob(pattern):
                        archive.write(path, path.name)
                for path in (self.log_path, self.state_path):
                    if path.exists():
                        archive.write(path, f"logs/{path.name}")
            self.footer.configure(text=f"Laya экспортирована: {target}")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Ошибка экспорта: {exc}")

    def refresh_all(self) -> None:
        pid = read_pid(self.pid_path)
        self.laya_label.configure(
            text=f"● Laya: работает (PID {pid})" if pid else "● Laya: остановлена",
            foreground="#3fb950" if pid else "#f85149",
        )
        threading.Thread(target=self._probe_game, daemon=True).start()
        self._refresh_doctrine()
        self._refresh_history()
        self.after(2000, self.refresh_all)

    def _refresh_doctrine(self) -> None:
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            maps = state.get("maps") or {}
            map_state = next(reversed(maps.values())) if maps else {}
            doctrine = map_state.get("doctrine") or {}
        except (OSError, json.JSONDecodeError, StopIteration):
            doctrine = {}
        if not doctrine:
            text = "Доктрина: Laya ещё не выбрала долгосрочное направление"
        else:
            text = (
                f"Доктрина: {doctrine.get('settlement_form', '—')} · {doctrine.get('material', '—')} · "
                f"экономика {doctrine.get('economy', '—')} · дипломатия {doctrine.get('diplomacy', '—')} · "
                f"армия {doctrine.get('military', '—')} · красота {doctrine.get('beauty', '—')}"
            )
        self.doctrine_label.configure(text=text)

    def _probe_game(self) -> None:
        try:
            url = f"{str(self.config_data['api_url']).rstrip('/')}/api/v1/game/state"
            result = request_json(url)
            online = bool(result.get("success"))
        except (OSError, URLError, ValueError, json.JSONDecodeError):
            online = False
        self.after(0, lambda: self.game_label.configure(
            text="● RimWorld API: подключён" if online else "● RimWorld API: недоступен",
            foreground="#3fb950" if online else "#f85149",
        ))

    def _refresh_history(self) -> None:
        try:
            stat = self.log_path.stat()
            signature = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            signature = None
        if signature == self.last_log_signature:
            return
        self.last_log_signature = signature
        self.records = tail_jsonl(self.log_path)
        selected = self.tree.selection()
        selected_index = int(selected[0]) if selected else None
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(self.records):
            decision = row.get("decision") or {}
            result = row.get("result") or {}
            timestamp = str(row.get("timestamp") or "")
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone().strftime("%d.%m %H:%M:%S")
            except ValueError:
                pass
            choice = decision.get("choice") or row.get("error") or "—"
            confidence = decision.get("confidence")
            confidence_text = f"{float(confidence) * 100:.1f}%" if confidence is not None else "—"
            if result.get("applied") is True:
                result_text = "выполнено"
            elif result.get("reason"):
                result_text = str(result.get("reason"))
            elif row.get("error"):
                result_text = str(row.get("error"))
            else:
                result_text = json.dumps(result, ensure_ascii=False)[:180]
            self.tree.insert("", END, iid=str(index), values=(timestamp, row.get("mode", "—"), choice, confidence_text, result_text))
        if self.records:
            target = str(selected_index if selected_index is not None and selected_index < len(self.records) else len(self.records) - 1)
            self.tree.selection_set(target)
            self.tree.see(target)
            self.show_selected()

    def show_selected(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        index = int(selection[0])
        if not 0 <= index < len(self.records):
            return
        row = self.records[index]
        decision = row.get("decision") or {}
        raw = decision.get("raw") or {}
        probabilities = {}
        try:
            answer = next(iter(raw.get("answers", {}).values()))
            probabilities = answer.get("probabilities") or {}
        except (StopIteration, AttributeError):
            pass
        summary = {
            "время": row.get("timestamp"),
            "режим": row.get("mode"),
            "доступные варианты": row.get("candidates") or list(probabilities),
            "вероятности": {key: f"{float(value) * 100:.1f}%" for key, value in probabilities.items()},
            "выбор": decision.get("choice"),
            "уверенность": decision.get("confidence"),
            "действие": row.get("action"),
            "результат": row.get("result"),
            "ошибка": row.get("error"),
        }
        self.details.delete("1.0", END)
        self.details.insert("1.0", json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    ControlCenter().mainloop()
