from __future__ import annotations

import csv
import ctypes
import json
import os
import shutil
import signal
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


APP_NAME = "Laya Control Center 0.0.2"
BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
CONFIG_PATH = BASE_DIR / "laya-control.json"
PREFERENCES_PATH = BASE_DIR / "laya-preferences.json"
DEFAULT_CONFIG = {
    "python_exe": str(BASE_DIR / ".venv" / "Scripts" / "python.exe"),
    "director_script": str(BASE_DIR / "colony_director.py"),
    "api_url": "http://localhost:8765",
    "device": "cuda",
    "interval": 10,
}


def load_config() -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    try:
        loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
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


def tail_jsonl(path: Path, limit: int = 500) -> list[dict[str, Any]]:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            data = b""
            while size > 0 and data.count(b"\n") <= limit:
                take = min(65536, size)
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


def request_json(url: str, method: str = "GET") -> dict[str, Any]:
    req = Request(url, method=method, headers={"Accept": "application/json"})
    with urlopen(req, timeout=1.5) as response:
        return json.loads(response.read().decode("utf-8-sig"))


def start_director(config: dict[str, Any], log_path: Path, state_path: Path, pid_path: Path) -> int:
    python_exe = Path(str(config["python_exe"]))
    director = Path(str(config["director_script"]))
    if not python_exe.exists() or not director.exists():
        raise FileNotFoundError(f"{python_exe}\n{director}")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    stdout = (log_path.parent / "director.stdout.log").open("ab")
    stderr = (log_path.parent / "director.stderr.log").open("ab")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    args = [
        str(python_exe), "-u", str(director), "--device", str(config.get("device", "cuda")),
        "--interval", str(config.get("interval", 10)), "--api-url", str(config.get("api_url", "http://localhost:8765")),
        "--log", str(log_path), "--state", str(state_path), "--pid-file", str(pid_path),
    ]
    try:
        process = subprocess.Popen(args, cwd=BASE_DIR, stdout=stdout, stderr=stderr, creationflags=flags)
        pid_path.write_text(str(process.pid), encoding="ascii")
        return process.pid
    finally:
        stdout.close()
        stderr.close()


def stop_director(pid_path: Path) -> int | None:
    pid = read_pid(pid_path)
    if not pid:
        return None
    os.kill(pid, signal.SIGTERM)
    pid_path.unlink(missing_ok=True)
    return pid


def export_history(log_path: Path, destination: Path) -> None:
    if destination.suffix.lower() == ".jsonl":
        shutil.copy2(log_path, destination)
        return
    records = tail_jsonl(log_path, limit=100000)
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "mode", "choice", "confidence", "candidates", "result"])
        for row in records:
            decision = row.get("decision") or {}
            writer.writerow([
                row.get("timestamp"), row.get("mode"), decision.get("choice"), decision.get("confidence"),
                ", ".join(row.get("candidates") or []), json.dumps(row.get("result"), ensure_ascii=False),
            ])


def export_bundle(destination: Path, log_path: Path, state_path: Path) -> None:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for pattern in ("*.py", "*.md", "*.ps1", "*.cmd", "*.json"):
            for path in BASE_DIR.glob(pattern):
                archive.write(path, path.name)
        for folder in ("laya_gui", "assets"):
            root = BASE_DIR / folder
            if root.exists():
                for path in root.rglob("*"):
                    if path.is_file() and "__pycache__" not in path.parts:
                        archive.write(path, path.relative_to(BASE_DIR))
        for path in (log_path, state_path):
            if path.exists():
                archive.write(path, f"logs/{path.name}")


def timestamped_export_name(prefix: str, suffix: str) -> str:
    return f"{prefix}-{datetime.now():%Y%m%d-%H%M}.{suffix}"
