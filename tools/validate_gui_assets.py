from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

from PIL import Image


def main(asset_root: Path) -> None:
    root = tk.Tk()
    root.withdraw()
    errors: list[str] = []
    try:
        for path in sorted(asset_root.glob("*.png")):
            with Image.open(path) as decoded:
                expected = decoded.size
            photo = tk.PhotoImage(file=str(path.resolve()))
            actual = (photo.width(), photo.height())
            if actual != expected:
                errors.append(f"{path.name}: Pillow={expected}, Tk={actual}")
    finally:
        root.destroy()
    if errors:
        raise SystemExit("GUI assets are not Tk-compatible PNGs:\n" + "\n".join(errors))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
