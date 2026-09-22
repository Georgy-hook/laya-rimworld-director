from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import Callable


COLORS = {
    "window": "#090B12",
    "sidebar": "#0F121C",
    "panel": "#161A27",
    "panel_alt": "#202638",
    "shadow": "#03050A",
    "line": "#30374D",
    "text": "#F5F7FF",
    "muted": "#A8B1C7",
    "cyan": "#63E6FF",
    "violet": "#AA92FF",
    "amber": "#FFD078",
    "green": "#70E5AC",
    "red": "#FF7D91",
    "navy": "#0D1731",
    "hover": "#343D5A",
    "focus": "#8DEBFF",
}

FONTS = {
    "display": ("Segoe UI Variable Display Semib", 25),
    "title": ("Segoe UI Variable Display Semib", 16),
    "heading": ("Segoe UI Variable Text Semibold", 12),
    "body": ("Segoe UI Variable Text", 10),
    "small": ("Segoe UI Variable Text", 9),
    "mono": ("Cascadia Mono", 9),
    "button": ("Segoe UI Variable Text Semibold", 10),
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
    style.configure("Accent.TButton", padding=(16, 10), background=COLORS["violet"], foreground="#10121A", font=FONTS["button"], borderwidth=0)
    style.map("Accent.TButton", background=[("active", COLORS["cyan"]), ("disabled", COLORS["line"])])
    style.configure("Soft.TButton", padding=(14, 9), background=COLORS["panel_alt"], foreground=COLORS["text"], borderwidth=0)
    style.map("Soft.TButton", background=[("active", "#30374D")])
    style.configure("Danger.TButton", padding=(14, 9), background="#3A1F2A", foreground="#FFB2BE", borderwidth=0)
    style.map("Danger.TButton", background=[("active", "#542536")])
    style.configure("TCheckbutton", background=COLORS["panel"], foreground=COLORS["text"])
    style.map("TCheckbutton", background=[("active", COLORS["panel"])])
    style.configure("Treeview", background=COLORS["panel"], fieldbackground=COLORS["panel"], foreground=COLORS["text"], rowheight=32, borderwidth=0)
    style.configure("Treeview.Heading", background=COLORS["panel_alt"], foreground=COLORS["muted"], font=("Segoe UI Variable Text Semibold", 9), relief="flat")
    style.map("Treeview", background=[("selected", "#39335E")], foreground=[("selected", COLORS["text"])])
    style.configure("Horizontal.TScale", background=COLORS["panel"], troughcolor=COLORS["line"], sliderthickness=16)
    style.configure("TCombobox", fieldbackground=COLORS["panel_alt"], background=COLORS["panel_alt"], foreground=COLORS["text"])
    return style


class ShadowCard(tk.Frame):
    """Rounded native-Tk card with a soft offset shadow and a normal child frame."""

    def __init__(self, master: tk.Misc, *, padx: int = 18, pady: int = 16, radius: int = 18, **kwargs) -> None:
        outer = _widget_background(master)
        super().__init__(master, bg=outer, **kwargs)
        self.radius = radius
        self.canvas = tk.Canvas(self, bg=outer, highlightthickness=0, bd=0, width=280, height=90)
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=COLORS["panel"], padx=padx, pady=pady, highlightthickness=1, highlightbackground=COLORS["line"])
        self.body.configure(highlightthickness=0)
        self._body_window = self.canvas.create_window(14, 12, anchor="nw", window=self.body)
        self.canvas.bind("<Configure>", self._redraw)
        self.body.bind("<Configure>", self._sync_request)
        self.after_idle(self._sync_request)

    def _sync_request(self, _event=None) -> None:
        requested_height = max(60, self.body.winfo_reqheight() + 28)
        requested_width = max(220, self.body.winfo_reqwidth() + 28)
        if int(float(self.canvas.cget("height"))) != requested_height:
            self.canvas.configure(height=requested_height)
        if int(float(self.canvas.cget("width"))) < requested_width:
            self.canvas.configure(width=requested_width)

    def _redraw(self, event: tk.Event) -> None:
        width, height = max(1, event.width), max(1, event.height)
        self.canvas.delete("surface")
        _rounded_rectangle(self.canvas, 4, 7, width - 2, height - 1, self.radius, fill=COLORS["shadow"], outline="", tags="surface")
        _rounded_rectangle(self.canvas, 1, 1, width - 5, height - 6, self.radius, fill=COLORS["panel"], outline=COLORS["line"], width=1, tags="surface")
        self.canvas.tag_lower("surface")
        self.canvas.coords(self._body_window, 14, 12)
        self.canvas.itemconfigure(self._body_window, width=max(1, width - 32), height=max(1, height - 30))


class FancyButton(tk.Canvas):
    """Rounded button with a short color animation and no UI-framework dependency."""

    PALETTES = {
        "accent": (COLORS["violet"], COLORS["cyan"], "#0C1020"),
        "soft": (COLORS["panel_alt"], COLORS["hover"], COLORS["text"]),
        "danger": ("#3A1F2A", "#5A2B3B", "#FFB2BE"),
        "ghost": (COLORS["sidebar"], COLORS["panel_alt"], COLORS["muted"]),
    }

    def __init__(
        self,
        master: tk.Misc,
        *,
        text: str,
        command: Callable[[], None] | None = None,
        variant: str = "soft",
        width: int | None = None,
        height: int = 40,
        icon: str = "",
        image: tk.PhotoImage | None = None,
        align: str = "center",
    ) -> None:
        self._ready = False
        self._text = text
        self._icon = icon
        self._image = image
        self._align = align
        self._command = command
        self._variant = variant if variant in self.PALETTES else "soft"
        self._state = "normal"
        self._hover = 0.0
        self._focused = False
        self._animation: str | None = None
        self._font = FONTS["button"]
        measured = tkfont.Font(font=self._font).measure(f"{icon}  {text}" if icon else text) + (76 if image else 34)
        super().__init__(
            master,
            width=width or max(104, measured),
            height=height,
            bg=_widget_background(master),
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            takefocus=1,
        )
        self._ready = True
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Enter>", lambda _event: self._animate_to(1.0))
        self.bind("<Leave>", lambda _event: self._animate_to(0.0))
        self.bind("<ButtonPress-1>", lambda _event: self.focus_set())
        self.bind("<ButtonRelease-1>", self._activate)
        self.bind("<FocusIn>", self._set_focus)
        self.bind("<FocusOut>", self._set_focus)
        self.bind("<Return>", self._activate)
        self.bind("<space>", self._activate)
        self._draw()

    def _draw(self) -> None:
        if not self._ready:
            return
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        base, hover, foreground = self.PALETTES[self._variant]
        if self._state == "disabled":
            base, hover, foreground = COLORS["line"], COLORS["line"], COLORS["muted"]
        fill = _mix_color(self, base, hover, self._hover)
        self.delete("all")
        outline = COLORS["focus"] if self._focused else ""
        outline_width = 2 if self._focused else 0
        _rounded_rectangle(
            self, 2, 2, width - 3, height - 3, min(15, height // 2),
            fill=fill, outline=outline, width=outline_width,
        )
        label = f"{self._icon}  {self._text}" if self._icon else self._text
        if self._align == "left":
            if self._image:
                self.create_image(27, height / 2, image=self._image)
                text_x = 56
            else:
                text_x = 18
            self.create_text(text_x, height / 2, text=label, fill=foreground, font=self._font, anchor="w")
        else:
            if self._image:
                image_x = width / 2 - tkfont.Font(font=self._font).measure(label) / 2 - 18
                self.create_image(image_x, height / 2, image=self._image)
                self.create_text(image_x + 26, height / 2, text=label, fill=foreground, font=self._font, anchor="w")
            else:
                self.create_text(width / 2, height / 2, text=label, fill=foreground, font=self._font)

    def _animate_to(self, target: float) -> None:
        if self._state == "disabled":
            return
        if self._animation:
            self.after_cancel(self._animation)
        delta = target - self._hover
        if abs(delta) < 0.04:
            self._hover = target
            self._draw()
            return
        self._hover += 0.22 if delta > 0 else -0.22
        self._hover = max(0.0, min(1.0, self._hover))
        self._draw()
        self._animation = self.after(18, lambda: self._animate_to(target))

    def _activate(self, _event=None) -> None:
        if self._state != "disabled" and self._command:
            self._command()
        return "break"

    def _set_focus(self, event: tk.Event) -> None:
        self._focused = event.type == tk.EventType.FocusIn
        self._draw()

    def configure(self, cnf=None, **kwargs):
        if not getattr(self, "_ready", False):
            return super().configure(cnf, **kwargs)
        if "text" in kwargs:
            self._text = str(kwargs.pop("text"))
        if "state" in kwargs:
            self._state = str(kwargs.pop("state"))
            super().configure(cursor="" if self._state == "disabled" else "hand2", takefocus=0 if self._state == "disabled" else 1)
        if "variant" in kwargs:
            variant = str(kwargs.pop("variant"))
            if variant in self.PALETTES:
                self._variant = variant
        result = super().configure(cnf, **kwargs) if cnf or kwargs else None
        self._draw()
        return result

    config = configure


class ModernScrollbar(tk.Canvas):
    """A compact rounded scrollbar without legacy arrow buttons."""

    def __init__(self, master: tk.Misc, *, command: Callable[..., object], width: int = 12) -> None:
        super().__init__(
            master,
            width=width,
            bg=_widget_background(master),
            bd=0,
            highlightthickness=0,
            takefocus=1,
            cursor="hand2",
        )
        self._command = command
        self._first = 0.0
        self._last = 1.0
        self._drag_offset: float | None = None
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda _event: setattr(self, "_drag_offset", None))
        self.bind("<Up>", lambda _event: self._scroll(-1, "units"))
        self.bind("<Down>", lambda _event: self._scroll(1, "units"))
        self.bind("<Prior>", lambda _event: self._scroll(-1, "pages"))
        self.bind("<Next>", lambda _event: self._scroll(1, "pages"))
        self.bind("<Home>", lambda _event: self._move_to(0.0))
        self.bind("<End>", lambda _event: self._move_to(1.0))

    def set(self, first: str | float, last: str | float) -> None:
        self._first = max(0.0, min(1.0, float(first)))
        self._last = max(self._first, min(1.0, float(last)))
        self._draw()

    def _geometry(self) -> tuple[float, float, float, float]:
        height = max(1.0, float(self.winfo_height()))
        top, bottom = 4.0, height - 4.0
        track = max(1.0, bottom - top)
        thumb_top = top + track * self._first
        thumb_bottom = top + track * self._last
        if thumb_bottom - thumb_top < 30:
            center = (thumb_top + thumb_bottom) / 2
            thumb_top = max(top, center - 15)
            thumb_bottom = min(bottom, thumb_top + 30)
            thumb_top = max(top, thumb_bottom - 30)
        return top, bottom, thumb_top, thumb_bottom

    def _draw(self) -> None:
        width = max(1, self.winfo_width())
        top, bottom, thumb_top, thumb_bottom = self._geometry()
        self.delete("all")
        _rounded_rectangle(self, 3, top, width - 3, bottom, 4, fill=COLORS["panel_alt"], outline="")
        if self._last - self._first < 0.999:
            _rounded_rectangle(self, 2, thumb_top, width - 2, thumb_bottom, 5, fill=COLORS["violet"], outline="")

    def _press(self, event: tk.Event) -> None:
        self.focus_set()
        top, bottom, thumb_top, thumb_bottom = self._geometry()
        if thumb_top <= event.y <= thumb_bottom:
            self._drag_offset = event.y - thumb_top
            return
        viewport = max(0.0, self._last - self._first)
        fraction = (event.y - top) / max(1.0, bottom - top) - viewport / 2
        self._move_to(fraction)

    def _drag(self, event: tk.Event) -> None:
        if self._drag_offset is None:
            return
        top, bottom, _thumb_top, _thumb_bottom = self._geometry()
        viewport = max(0.0, self._last - self._first)
        fraction = (event.y - self._drag_offset - top) / max(1.0, bottom - top)
        self._move_to(min(1.0 - viewport, max(0.0, fraction)))

    def _move_to(self, fraction: float) -> str:
        self._command("moveto", max(0.0, min(1.0, fraction)))
        return "break"

    def _scroll(self, amount: int, what: str) -> str:
        self._command("scroll", amount, what)
        return "break"


class ScrollablePage(tk.Frame):
    """A vertically scrollable page that preserves a stable content width."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg=COLORS["window"])
        self.canvas = tk.Canvas(self, bg=COLORS["window"], highlightthickness=0, bd=0)
        self.scrollbar = ModernScrollbar(self, command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y", padx=(8, 0))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=COLORS["window"])
        self._window = self.canvas.create_window(0, 0, anchor="nw", window=self.body)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.body.bind("<Configure>", self._sync_region)
        self.canvas.bind("<Configure>", self._sync_width)
        self.canvas.bind("<MouseWheel>", self._mousewheel)
        self.body.bind("<MouseWheel>", self._mousewheel)

    def _sync_region(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _sync_width(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window, width=max(1, event.width))

    def _mousewheel(self, event: tk.Event) -> str:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"


def _widget_background(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("background"))
    except tk.TclError:
        return COLORS["window"]


def _rounded_rectangle(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float, radius: float, **kwargs):
    radius = max(1, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = (
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    )
    return canvas.create_polygon(points, smooth=True, splinesteps=30, **kwargs)


def _mix_color(widget: tk.Misc, first: str, second: str, amount: float) -> str:
    left = widget.winfo_rgb(first)
    right = widget.winfo_rgb(second)
    values = [int((a + (b - a) * amount) / 256) for a, b in zip(left, right)]
    return "#" + "".join(f"{value:02x}" for value in values)


def status_color(online: bool) -> str:
    return COLORS["green"] if online else COLORS["red"]
