# GUI architecture

The 0.0.2 RimWorld Autopilot control center is intentionally separate from the colony controller. `autopilot_control.py` is the public launcher (`laya_control.py` remains compatible); the implementation lives in `laya_gui/`:

- `app.py` composes the five user pages and animated navigation shell;
- `theme.py` owns the dark cartoon palette, typography, shadows and reusable cards;
- `i18n.py` owns Russian/English copy and friendly names for internal decisions;
- `services.py` owns process control, local API checks and export operations;
- `setup_app.py` is the graphical installation assistant;
- `laya_preferences.py` is shared with the autonomous director and validates player guidance.

## Pages

1. **Overview** — Laya/RimWorld status, start/stop/pause controls, current course, latest decision and active content.
2. **Strategy** — the selected doctrine and every direction available in the loaded Core/DLC set.
3. **Priorities** — eight 0–100 preference weights, a free-form personal note and explicit peaceful/safety boundaries.
4. **History** — friendly explanations by default; exact JSON is available only after enabling technical mode.
5. **Settings** — Russian/English switch, diagnostic logging, installer and exports.

The interface uses native Tk widgets and the standard library. It therefore adds no UI framework dependency to the already large local-model installation. Rounded cards, animated buttons and orbit particles are drawn locally. The emblem, panoramic colony art, setup illustration and five navigation illustrations are original project-local PNGs generated with the built-in ImageGen tool; prompts are preserved in `assets/gui/README.md`.

## Preference contract

The GUI writes `autopilot-preferences.json`. Installed builds keep writable settings and logs in `%LOCALAPPDATA%\RimWorld Autopilot`, while program files remain under Program Files. The file is local runtime state and is excluded from Git. An existing `laya-preferences.json` is read as a compatibility migration. The development planner, combat planner, incident director, downed-raider policy and Ancient Danger decisions read the same validated structure.

Weights guide ordering and model context. They cannot override emergency gates, missing research/resources, invalid targets or API safety checks. “Do not begin unprovoked attacks” additionally removes settlement raids from the feasible candidate set.

Normal logging keeps compact decisions, outcomes and probability paths. Technical logging additionally records the complete development snapshot/details; combat logging keeps full snapshots only in technical mode.

## Installer

`RimWorld-Autopilot-Setup.exe` is built from `autopilot_setup.py` and `laya_gui/setup_app.py`. It requests administrator rights because its default target is `C:\Program Files\RimWorld Autopilot`. It:

1. lets the player choose an application folder and a real RimWorld folder;
2. offers an optional desktop shortcut, enabled by default;
3. locates Python 3.10–3.12 or opens the official download page;
4. copies the application, bilingual UI and complete local artwork set;
5. creates `.venv` and installs `requirements.txt`;
6. backs up an existing `Mods/RIMAPI` directory with a timestamp;
7. copies the bundled modified RIMAPI source/build;
8. writes `rimworld-autopilot.json` and creates the shortcut when selected.

The installer does not request an API key, start RimWorld, alter saves or enable mods without the player.

The release EXE stays beside `requirements.txt`, the Python controller sources and `vendor/RIMAPI`; those adjacent files are the payload it installs. `Build-GUI.ps1` reproduces both unsigned Windows binaries and assembles `dist/rimworld-autopilot-0.0.2.zip` with that complete payload. Build-only dependencies are isolated in `.build-venv` and declared in `requirements-build.txt`.
