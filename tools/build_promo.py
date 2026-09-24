"""Build the local promo from the four edited source clips and genuine Laya HUD footage.

This script only writes derived files. It never changes the four clips in
artifacts/promo/final. Run it from any working directory after installing
requirements-promo.txt. It uses imageio-ffmpeg's bundled executable.
"""

from __future__ import annotations

import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


ROOT = Path(__file__).resolve().parents[1]
PROMO = ROOT / "artifacts" / "promo"
FINAL = PROMO / "final"
WORK = PROMO / "work" / "render"
ASSETS = ROOT / "assets" / "promo"
FFMPEG = (
    Path(imageio_ffmpeg.get_ffmpeg_exe())
    if imageio_ffmpeg is not None
    else ROOT / ".build-venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries" / "ffmpeg-win-x86_64-v7.1.exe"
)
FONT_BOLD = Path("C:/Windows/Fonts/bahnschrift.ttf")
FONT_SMALL = Path("C:/Windows/Fonts/segoeuib.ttf")
FPS = 30
WIDTH = 1920
HEIGHT = 1080
TRANSITION = 0.7
SCENES = (
    ("Combat", FINAL / "01-combat.mp4", "combat"),
    ("Building", FINAL / "02-building.mp4", "building"),
    ("Harvest", FINAL / "03-foraging.mp4", "harvest"),
    ("Care", FINAL / "04-medical.mp4", "care"),
)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    print("FFmpeg:", " ".join(str(a) for a in args[:8]), "...", flush=True)
    result = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-4000:]}")
    return result


def duration(path: Path) -> float:
    result = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-i", str(path)],
        text=True,
        capture_output=True,
    )
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError(f"No video duration for {path}: {result.stderr[-1000:]}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def rgba_text(
    canvas: Image.Image,
    text: str,
    center: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    alpha: int,
    *,
    fill: tuple[int, int, int] = (255, 255, 255),
    shadow: bool = True,
) -> None:
    if shadow:
        layer = Image.new("RGBA", canvas.size)
        draw = ImageDraw.Draw(layer)
        draw.text((center[0] + 3, center[1] + 6), text, anchor="mm", font=font, fill=(0, 0, 0, min(190, alpha)))
        canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(12)))
    ImageDraw.Draw(canvas).text((*center,), text, anchor="mm", font=font, fill=(*fill, alpha))


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def alpha_envelope(time: float, length: float, fade_in: float = 0.32, fade_out: float = 0.42) -> int:
    return round(255 * min(1.0, time / fade_in, max(0.0, (length - time) / fade_out)))


def render_scene_titles() -> None:
    title_length = 2.55
    count = math.ceil(FPS * title_length)
    for scene_index, (title, _, slug) in enumerate(SCENES, start=1):
        title_dir = WORK / "titles" / slug
        title_dir.mkdir(parents=True, exist_ok=True)
        for frame in range(count):
            time = frame / FPS
            alpha = alpha_envelope(time, title_length)
            rise = ease_out_cubic(min(1.0, time / 0.65))
            scale = 0.79 + 0.21 * rise + 0.025 * math.sin(math.pi * min(1.0, time / 0.65))
            center_y = round(190 + (1 - rise) * 18)
            img = Image.new("RGBA", (WIDTH, 360))
            large = ImageFont.truetype(str(FONT_BOLD), round(112 * scale))
            small = ImageFont.truetype(str(FONT_SMALL), 21)
            rgba_text(img, title.upper(), (1270, center_y), large, alpha)
            d = ImageDraw.Draw(img)
            line_alpha = round(alpha * min(1.0, time / 0.55))
            line_width = round(360 * min(1.0, ease_out_cubic(time / 0.65)))
            d.rounded_rectangle((1270 - line_width // 2, 257, 1270 + line_width // 2, 263), radius=3, fill=(255, 194, 70, line_alpha))
            rgba_text(img, f"LAYA  /  {scene_index:02d}", (1270, 300), small, round(alpha * 0.9), fill=(249, 224, 165), shadow=False)
            img.save(title_dir / f"frame_{frame:04d}.png", optimize=True)
        print(f"Title frames: {title}", flush=True)


def render_outro_titles(seconds: float) -> None:
    out_dir = WORK / "titles" / "outro"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = round(seconds * FPS)
    for frame in range(count):
        time = frame / FPS
        img = Image.new("RGBA", (WIDTH, HEIGHT))
        fade_in = min(1.0, max(0.0, time / 0.7))
        fade_out = min(1.0, max(0.0, (seconds - time) / 0.9))
        alpha = round(255 * fade_in * fade_out)
        scale = 0.85 + 0.15 * ease_out_cubic(min(1.0, time / 1.1))
        y = round(505 + 24 * (1 - ease_out_cubic(min(1.0, time / 1.0))))
        large = ImageFont.truetype(str(FONT_BOLD), round(166 * scale))
        medium = ImageFont.truetype(str(FONT_BOLD), round(63 * scale))
        small = ImageFont.truetype(str(FONT_SMALL), 42)
        rgba_text(img, "LAYA", (960, y), large, alpha)
        rgba_text(img, "RIMWORLD AUTOPILOT", (960, y + 122), medium, alpha)
        d = ImageDraw.Draw(img)
        line = round(520 * min(1.0, ease_out_cubic(max(0.0, time - 0.28) / 0.8)))
        d.rounded_rectangle((960 - line // 2, y + 178, 960 + line // 2, y + 184), radius=3, fill=(255, 194, 70, alpha))
        lower_alpha = round(alpha * min(1.0, max(0.0, (time - 0.65) / 0.55)))
        rgba_text(img, "TRY YOURSELF", (960, y + 258), small, lower_alpha)
        img.save(out_dir / f"frame_{frame:04d}.png", optimize=True)
    print("Outro title frames ready", flush=True)


def render_scenes() -> list[Path]:
    segments: list[Path] = []
    for title, source, slug in SCENES:
        output = WORK / f"scene-{slug}.mp4"
        titles = WORK / "titles" / slug / "frame_%04d.png"
        run(
            "-i", source,
            "-framerate", str(FPS), "-i", titles,
            "-filter_complex",
            "[0:v]fps=30,scale=1920:1080:flags=lanczos,setsar=1,format=rgba[base];"
            "[1:v]format=rgba[title];"
            "[base][title]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[v]",
            "-map", "[v]", "-an", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "faster", "-crf", "19", "-movflags", "+faststart", output,
        )
        print(f"Rendered scene: {title} ({duration(output):.2f}s)", flush=True)
        segments.append(output)
    return segments


def render_outro() -> Path:
    source = FINAL / "05-large-colony-laya.mp4"
    output = WORK / "scene-outro.mp4"
    # The HUD is cropped back from the *same genuine capture* after the scene
    # behind it is blurred. This preserves the model's actual unequal bars.
    run(
        "-ss", "4", "-t", "8.5", "-i", source,
        "-framerate", str(FPS), "-i", WORK / "titles" / "outro" / "frame_%04d.png",
        "-filter_complex",
        "[0:v]fps=30,scale=1920:1080:flags=lanczos,setsar=1,format=rgba,split=2[base][sharp];"
        "[base]gblur=sigma=14:steps=2,eq=brightness=-0.09:saturation=0.82[blur];"
        "[sharp]crop=568:226:19:112[hud];"
        "[blur][hud]overlay=19:112:format=auto[scene];"
        "[1:v]format=rgba[title];"
        "[scene][title]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[v]",
        "-map", "[v]", "-an", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "faster", "-crf", "19", "-movflags", "+faststart", output,
    )
    print(f"Rendered outro ({duration(output):.2f}s)", flush=True)
    return output


def generate_music(seconds: float, transitions: list[float]) -> Path:
    """An original restrained electronic cue; no external soundtrack/license."""
    sample_rate = 32000
    sample_count = math.ceil(seconds * sample_rate)
    audio = np.zeros(sample_count, dtype=np.float32)
    beat = 60 / 112
    chord_time = beat * 4
    chords = ((220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66))
    for number, start in enumerate(np.arange(0, seconds, chord_time)):
        length = min(chord_time + 0.35, seconds - start)
        n = max(1, round(length * sample_rate))
        time = np.arange(n, dtype=np.float32) / sample_rate
        fade = np.minimum(1.0, time / 0.24) * np.minimum(1.0, np.maximum(0.0, (length - time) / 0.42))
        chord = chords[number % len(chords)]
        wave_data = np.zeros(n, dtype=np.float32)
        for frequency in chord:
            wave_data += np.sin(2 * np.pi * frequency * time) * 0.018
            wave_data += np.sin(2 * np.pi * frequency * 2.004 * time) * 0.004
        wave_data += np.sin(2 * np.pi * chord[0] / 2 * time) * 0.034
        at = round(start * sample_rate)
        audio[at : at + n] += wave_data * fade
    rng = np.random.default_rng(4321)
    for number, start in enumerate(np.arange(0, seconds, beat / 2)):
        at = round(start * sample_rate)
        length = min(round(0.14 * sample_rate), sample_count - at)
        if length <= 0:
            break
        time = np.arange(length, dtype=np.float32) / sample_rate
        # Soft high hat/pulse, darker on off beats.
        noise = rng.standard_normal(length).astype(np.float32)
        hat = np.diff(noise, prepend=noise[0]) * np.exp(-time * 42) * (0.012 if number % 2 == 0 else 0.007)
        audio[at : at + length] += hat
    for number, start in enumerate(np.arange(0, seconds, beat)):
        at = round(start * sample_rate)
        length = min(round(0.28 * sample_rate), sample_count - at)
        if length <= 0:
            break
        time = np.arange(length, dtype=np.float32) / sample_rate
        kick = np.sin(2 * np.pi * (65 * time + 45 * (1 - np.exp(-time * 26)) / 26)) * np.exp(-time * 20) * 0.11
        audio[at : at + length] += kick
        if number % 4 == 2:
            snare_noise = rng.standard_normal(length).astype(np.float32)
            audio[at : at + length] += snare_noise * np.exp(-time * 22) * 0.026
    for start in transitions:
        at = round(max(0, start - 0.4) * sample_rate)
        length = min(round(0.85 * sample_rate), sample_count - at)
        if length <= 0:
            continue
        time = np.arange(length, dtype=np.float32) / sample_rate
        noise = rng.standard_normal(length).astype(np.float32)
        env = np.sin(np.pi * np.minimum(1.0, time / 0.85)) ** 2
        audio[at : at + length] += np.diff(noise, prepend=noise[0]) * env * 0.009
    fade = np.ones(sample_count, dtype=np.float32)
    edge = min(sample_count // 2, sample_rate)
    fade[:edge] *= np.linspace(0, 1, edge, dtype=np.float32)
    edge = min(sample_count // 2, sample_rate * 2)
    fade[-edge:] *= np.linspace(1, 0, edge, dtype=np.float32)
    audio *= fade
    audio = np.tanh(audio * 1.8) * 0.78
    # A short stereo delay gives width without inventing licensed music.
    delay = round(0.011 * sample_rate)
    stereo = np.stack((audio, np.roll(audio, delay) * 0.9), axis=1)
    output = WORK / "original-score.wav"
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes((stereo * 32767).astype("<i2").tobytes())
    return output


def assemble(segments: list[Path]) -> Path:
    lengths = [duration(path) for path in segments]
    offsets = []
    elapsed = lengths[0]
    for length in lengths[1:]:
        offsets.append(elapsed - TRANSITION)
        elapsed += length - TRANSITION
    music = generate_music(elapsed, offsets)
    inputs = []
    for path in segments:
        inputs += ["-i", path]
    inputs += ["-i", music]
    filters = []
    previous = "0:v"
    for index, offset in enumerate(offsets, start=1):
        target = f"x{index}"
        filters.append(f"[{previous}][{index}:v]xfade=transition=smoothleft:duration={TRANSITION}:offset={offset:.3f}[{target}]")
        previous = target
    filters.append(f"[{previous}]fade=t=out:st={max(0, elapsed - 0.75):.3f}:d=0.75,format=yuv420p[v]")
    output = FINAL / "RimWorld-Autopilot-promo.mp4"
    run(
        *inputs, "-filter_complex", ";".join(filters),
        "-map", "[v]", "-map", f"{len(segments)}:a",
        "-c:v", "libx264", "-preset", "faster", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", output,
    )
    print(f"Final montage: {output} ({duration(output):.2f}s)", flush=True)
    return output


def make_gifs() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for _, source, slug in SCENES:
        output = ASSETS / f"{slug}.gif"
        for width, fps, colors in ((480, 8, 96), (400, 7, 80), (360, 6, 64)):
            filters = (
                f"[0:v]fps={fps},scale={width}:-1:flags=lanczos,split[a][b];"
                f"[a]palettegen=max_colors={colors}:stats_mode=diff[p];"
                "[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle[v]"
            )
            run("-i", source, "-filter_complex", filters, "-map", "[v]", "-loop", "0", output)
            if output.stat().st_size <= 8_000_000:
                break
        print(f"GIF: {output.name} ({output.stat().st_size / 1_000_000:.1f} MB)", flush=True)


def main() -> None:
    if not FFMPEG.exists():
        raise FileNotFoundError(f"imageio-ffmpeg executable missing: {FFMPEG}")
    if not FONT_BOLD.exists() or not FONT_SMALL.exists():
        raise FileNotFoundError("Expected Windows fonts are missing")
    for _, source, _ in SCENES:
        if not source.exists():
            raise FileNotFoundError(source)
    outro_source = FINAL / "05-large-colony-laya.mp4"
    if not outro_source.exists():
        raise FileNotFoundError(outro_source)
    WORK.mkdir(parents=True, exist_ok=True)
    render_scene_titles()
    render_outro_titles(8.5)
    segments = render_scenes()
    segments.append(render_outro())
    assemble(segments)
    make_gifs()
    print("All promo derivatives ready; edited source videos were untouched.", flush=True)


if __name__ == "__main__":
    main()
