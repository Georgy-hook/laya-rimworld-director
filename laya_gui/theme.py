from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    "window": "#0B0D14",
    "sidebar": "#11141E",
    "panel": "#171B28",
    "panel_alt": "#1E2333",
    "shadow": "#05070B",
    "line": "#2A3044",
    "text": "#F4F6FF",
    "muted": "#9AA4BD",
    "cyan": "#5DE4FF",
    "violet": "#A78BFA",
    "amber": "#FFCB6B",
    "green": "#66E3A4",
    "red": "#FF7185",
}

FONTS = {
    "display": ("Segoe UI Semibold", 24),
    "title": ("Segoe UI Semibold", 16),
    "heading": ("Segoe UI Semibold", 12),
    "body": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "mono": ("Cascadia Mono", 9),
}


def configure_styles(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=COLORS["window"], foreground=COLORS["text"], font=FONTS["body"])
    style.configure("TFrame", background=COLORS["window"])
    style.configure("Panel.TFrame", background=COLORS["panel"])
    style.configure("Sidebar.TFrame", background=COLORS["sidebar"])
    style.configure("TLabel", background=COLORS["window"], foreground=COLORS["text"])
    style.configure("Panel.TLabel", background=COLORS["panel"], foreground=COLORS["text"])
    style.configure("Muted.Panel.TLabel", background=COLORS["panel"], foreground=COLORS["muted"])
    style.configure("Title.TLabel", font=FONTS["display"], foreground=COLORS["text"])
    style.configure("Heading.Panel.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=FONTS["heading"])
    style.configure("Accent.TButton", padding=(16, 10), background=COLORS["violet"], foreground="#10121A", font=("Segoe UI Semibold", 10), borderwidth=0)
    style.map("Accent.TButton", background=[("active", COLORS["cyan"]), ("disabled", COLORS["line"])])
    style.configure("Soft.TButton", padding=(14, 9), background=COLORS["panel_alt"], foreground=COLORS["text"], borderwidth=0)
    style.map("Soft.TButton", background=[("active", "#30374D")])
    style.configure("Danger.TButton", padding=(14, 9), background="#3A1F2A", foreground="#FFB2BE", borderwidth=0)
    style.map("Danger.TButton", background=[("active", "#542536")])
    style.configure("TCheckbutton", background=COLORS["panel"], foreground=COLORS["text"])
    style.map("TCheckbutton", background=[("active", COLORS["panel"])])
    style.configure("Treeview", background=COLORS["panel"], fieldbackground=COLORS["panel"], foreground=COLORS["text"], rowheight=32, borderwidth=0)
    style.configure("Treeview.Heading", background=COLORS["panel_alt"], foreground=COLORS["muted"], font=("Segoe UI Semibold", 9), relief="flat")
    style.map("Treeview", background=[("selected", "#39335E")], foreground=[("selected", COLORS["text"])])
    style.configure("Horizontal.TScale", background=COLORS["panel"], troughcolor=COLORS["line"], sliderthickness=16)
    style.configure("TCombobox", fieldbackground=COLORS["panel_alt"], background=COLORS["panel_alt"], foreground=COLORS["text"])
    return style


class ShadowCard(tk.Frame):
    """A simple two-layer card that reads as a soft shadow in native Tk."""

    def __init__(self, master: tk.Misc, *, padx: int = 18, pady: int = 16, **kwargs) -> None:
        super().__init__(master, bg=COLORS["shadow"], padx=2, pady=3, **kwargs)
        self.body = tk.Frame(self, bg=COLORS["panel"], padx=padx, pady=pady, highlightthickness=1, highlightbackground=COLORS["line"])
        self.body.pack(fill="both", expand=True)


def status_color(online: bool) -> str:
    return COLORS["green"] if online else COLORS["red"]
