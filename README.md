# RimWorld Autopilot

> Experimental autonomous colony management for RimWorld 1.6, powered by the local open-weight Laya decision model.

Version **0.0.2 (developing)** · Windows · Python 3.10+ · RimWorld 1.6 · GPL-3.0

RimWorld Autopilot reads a colony through a modified local RIMAPI mod, gives the Laya model a bounded set of real and currently feasible choices, and converts the selected choice into ordinary RimWorld work priorities, designations, bills, blueprints, research, caravans and combat orders.

It is not a prerecorded build order. Laya sees compact context, chooses between alternatives with probabilities, keeps a persistent colony doctrine, and can revise that doctrine when resources or conditions change. The long-term objective is a self-sufficient colony pursuing the ending or continuity strategy Laya selected from the content actually loaded in the game.

The project is unofficial and experimental. It can make bad decisions and lose a colony. **Use a copied save.**

## What 0.0.2 can do

- Food: unforbid starting supplies, create food storage/freezer space, cook, butcher, hunt and harvest wild edible plants.
- Farming: select crops, consider current season and forecast temperatures, pause late sowing without destroying existing crops, and resume viable seasonal sowing.
- Storage: expand near-full stockpiles, configure dedicated weapon shelves, place stone chunks beside the stonecutter, animal carcasses beside butchering, and human corpses in a distant critical-priority dump.
- Housing and rooms: choose compact, courtyard, separate-house or mountain development; choose real available construction materials; build private bedrooms without replacing existing rooms.
- Procedural architecture: choose a building program before its layout; generate 24 residential designs plus context-aware compounds, dining/rec halls, kitchens, hospitals, throne rooms, temples, workshops, factories, labs, warehouses, prisons, barns, nurseries, defenses and utility blocks from the definitions loaded by the current game.
- Psycasts: expose every live vanilla/DLC/mod psycast with caster, level, range, target mode, cooldown, charges, psyfocus cost and neural heat; Laya may choose an exact cast, while RIMAPI rejects invalid targets, insufficient focus and unsafe heat overflow.
- Combat doctrine: compare 28 situational tactics including focus fire, firing lines, kiting, staggered retreats, doorway/melee blocking, flanks, pincers, anti-explosive spacing, EMP/smoke operations, siege harassment, drop-pod encirclement, infestation containment, mech-cluster pokes and kidnapper interception.
- Defensive integration: tactical positions are selected from defenses that actually exist on the map (doors, cover, traps, turrets, mortars, firefoam and fallback structures); every issued movement route is inspected and rejected if it crosses a friendly trap.
- Event director: observe every loaded incident dynamically, classify known event families, surface unknown DLC/mod events conservatively, and deduplicate each occurrence while active conditions, letters and quest targets remain visible to Laya.
- Kidnapping and rescue: track kidnapped world pawns, inspect rescue/ransom quest sites and estimated threat, accept a selected quest, then form a reserve-aware rescue caravan that enters the actual quest site.
- Live trade: detect visiting traders and passing orbital ships, show their current stock/departure time and the best negotiator, then perform a normal reserve- and budget-aware transaction selected by Laya.
- Workforce direction: inspect every loaded `WorkTypeDef` (including DLC/mod jobs), score long-term specializations against the actual colonists, and persist the chosen specialization in the colony doctrine.
- Skills and passions: compare current level, disabled work, health, learning traits and no/small/large passion flames (35%/100%/150% XP multipliers), then let Laya choose a colonist-skill-work training plan.
- Schedules: detect the Night Owl trait and let Laya move that colonist to daytime sleep (11:00–18:59) with a flexible nighttime schedule.
- Beauty and hygiene: measure room cleanliness and impressiveness, choose kitchen/hospital floors, commission sculptures and install finished art in a selected real room.
- Light and climate: measure actual glow and temperature per room, expose dark work/medical rooms to Laya, and add powered lamps or torches to verified free cells. Darkness begins below 30% light and can reduce movement/work speed; surgery benefits from at least 50% light.
- Hospitals: progress from ordinary medical beds to hospital beds, central vitals monitoring and sterile/metal flooring as research, skill and materials become available.
- Production progression: offer normal successor benches (butcher spot → table, fueled → electric, simple → hi-tech, machining → fabrication) only after research and costs are satisfied, while retaining the old bench until the replacement is built.
- Animals: feed and rescue colony animals, avoid repeatedly treating an already-bandaged animal, make sleeping spots, build climate-aware barns, use optional straw matting, tame a selected species/sex and plan breeding.
- Industry and income: stonecutting, drugs, clothing, sculptures, livestock products, chemfuel, valuable minerals, crops, beer, travel food, orbital trade, and an explicit high-risk prisoner-organ route.
- Diplomacy and travel: choose a real friendly settlement, form a safe trade caravan, retain home defenders and supplies, and resolve prisoner recruit/release/sale plans through normal systems.
- Defense: layered firing positions, traps, turrets, mortars, firefoam, weapons/armor research and equipment priorities.
- Combat: distinguish staging raids from active assaults, either prepare undrafted or strike, resume verified raid auto-pauses, and let Laya select the roster using skills, weapons, traits, pain, missing parts, movement, manipulation and sight.
- Construction: choose an exact unfinished blueprint/frame and builder; avoid outdoor steel roads; build a freezer only when its cooler, power and component prerequisites are affordable.
- Ideology: inspect the current colony ideology and build a ritual room around its exact required altar or ideogram.
- Ancient Danger: treat the proximity warning as a sealed strategic site rather than a raid; Laya chooses to leave it, prepare, or designate a normal wall-deconstruction job to open it, then resumes the warning pause.
- Content-aware doctrine v2: 30 Core/DLC strategic archetypes are composed with settlement, economy, technology, defense, society, diplomacy and all official endgame axes. Inactive DLC choices are hidden; the selected course, available catalogue and every cascade probability appear in the GUI.
- Observability: an optional compact in-game HUD shows the selected action and yellow probability bars; the Windows control center shows choices, results, exportable history and real heartbeat-based states instead of treating a surviving PID as proof that Laya is healthy.
- Decision integrity: a single feasible outcome is resolved deterministically by the bridge and is never sent to Laya as a fake choice; the model is invoked only when at least two real alternatives remain.
- Friendly control center: dark fancy-cartoon dashboard with rounded cards, animated buttons and orbit effects, a panoramic colony scene, a coordinated original icon set, responsive scrollable pages, modern scrollbars, real flag artwork, Russian/English UI, friendly decision explanations and an optional technical view.
- Player guidance: eight priority weights, a personal instruction and peaceful/safety boundaries are read by development, combat and event decisions without bypassing feasibility gates.
- Standard Windows installer: `RimWorld-Autopilot-0.0.2-Setup.exe` installs to Program Files, offers a desktop shortcut, registers a Windows uninstaller, then opens the friendly one-time assistant for Python, local-model and RIMAPI configuration. The temporary assistant is removed when setup finishes.

## Safety model

The controller only accepts loopback API addresses. It deliberately does not expose or call RIMAPI cheats such as spawning resources, editing skills or health, teleporting pawns, completing research instantly or revealing Ancient Danger contents under fog of war.

Actions use normal game mechanics: work priorities, jobs, designations, zones, bills, blueprints, research and caravan formation. This is safer and more interesting, but it also means colonists can botch construction, ignore work they cannot perform, starve, break, or die.

## Quick install

Prerequisites:

1. RimWorld 1.6 on Windows.
2. Harmony enabled before RIMAPI in the RimWorld mod list.
3. Python 3.10 or newer (3.12 tested).
4. An NVIDIA GPU is recommended; CPU mode is supported but slower.
5. At least roughly 1 GB free for model weights and additional space for PyTorch.

Download **[RimWorld-Autopilot-0.0.2-Setup.exe](https://github.com/Georgy-hook/rimworld-autopilot/releases/download/v0.0.2/RimWorld-Autopilot-0.0.2-Setup.exe)** from the 0.0.2 release and open it. Choose whether to add a desktop shortcut. On the final page, leave **Configure Python, the local model and the RimWorld mod now** selected; the friendly assistant then verifies Python and RimWorld, creates the local environment and installs the bundled RIMAPI build without a command line.

Windows may show an Unknown Publisher warning because 0.0.2 is an unsigned open-source preview. Verify that the file came from this repository's GitHub release before running it. The ZIP asset is retained for maintainers and portable inspection; normal players should use the Setup EXE.

The PowerShell path remains available for maintainers:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Install.ps1
```

If RimWorld is installed elsewhere:

```powershell
.\Install.ps1 -RimWorldPath "D:\SteamLibrary\steamapps\common\RimWorld"
```

For CPU inference:

```powershell
.\Install.ps1 -Device cpu
```

The installer copies the application and local artwork, registers **RimWorld Autopilot 0.0.2** in Windows Installed apps, and creates only the selected shortcuts. Its temporary configuration assistant creates `.venv`, installs `laya==0.3.4`, backs up an existing local `Mods\RIMAPI` folder, installs the modified build, and writes `rimworld-autopilot.json`. Writable preferences and logs live under `%LOCALAPPDATA%\RimWorld Autopilot`, not Program Files.

Then:

1. In RimWorld, enable Harmony and **RIMAPI — RimWorld Autopilot**.
2. Restart RimWorld.
3. Load a copied colony save.
4. Run `Start-Autonomous.ps1` or open `RimWorld-Autopilot.exe` and click **Запустить Laya**.
5. The first start downloads `convaiinnovations/laya` from Hugging Face.

Stop the console director with `Ctrl+C`, or click **Остановить** in the GUI.

### Uninstall

Use **Settings → Apps → Installed apps → RimWorld Autopilot → Uninstall**, the Start-menu uninstall shortcut, or **Settings → App management → Uninstall Autopilot** inside the control center. The original Setup file is not kept in Program Files; Windows keeps only its standard `unins000.exe` uninstaller.

Uninstall removes the application and shortcuts. It intentionally preserves `%LOCALAPPDATA%\RimWorld Autopilot` and the installed `Mods\RIMAPI` folder so logs, preferences and a potentially shared mod are not destroyed unexpectedly. They can be removed manually after reviewing them.

## Manual commands

```powershell
# Verify the local API without loading the model
.\.venv\Scripts\python.exe .\rimworld_laya.py check

# Ask for one recommendation without applying it
.\.venv\Scripts\python.exe .\rimworld_laya.py suggest

# Continuous preview
.\Start-Preview.ps1

# Autonomous mode
.\Start-Autonomous.ps1
```

## How decisions work

Each cycle follows a hierarchical decision pipeline:

1. Collect a bounded snapshot from local RIMAPI endpoints.
2. Build only feasible choices using verified IDs, resources, skills, research, temperature, rooms, factions and map state.
3. If the list is large, choose a domain and action family first.
4. Choose one concrete action.
5. Ask only for parameters belonging to that selected action; rejecting hunting never asks for prey, and rejecting wild harvest never asks for a plant.
6. For architecture, choose program → house style when relevant → one bounded generated variant; the other programs and layouts are never evaluated.
7. For combat, choose tactic → exact roster → psycast/caster only when a psychic tactic was selected; RIMAPI then resolves trap-free positions against live defenses.
8. For events, choose one verified occurrence → response → trader/quest/mission parameters only when that branch needs them.
9. Validate the selected choice again and translate it into normal game commands.

Emergency survival gates run before long-horizon planning. Combat is checked much more often than ordinary development. Repeated orders are suppressed using a persistent state file and signatures of active combatants/jobs.

The model is a fast decision classifier, not a text-generating agent. The controller — not the model — defines the allowed actions and validates their parameters.

## Architecture

```text
RimWorld 1.6
  ↕ localhost:8765
modified RIMAPI (C#, Harmony)
  ↕ verified JSON state / normal gameplay commands
colony_director.py
  ↳ colony_professions.py (live professions, passions, training, schedules)
  ↳ colony_architect.py (programs, technology gates, procedural layouts)
  ↳ colony_strategy.py (DLC-aware strategy audit, cascaded doctrine, research matching)
  ↕ typed questions + probabilities
convaiinnovations/laya (local PyTorch model)

laya_gui/ via autopilot_control.py / in-game overlay
  ↳ status, doctrine, friendly history, personal priorities, export, start/stop
```

Important files:

- `colony_director.py` — long-horizon autonomous planner and executor.
- `colony_professions.py` — profession-fit scoring, passion-aware skill development and Night Owl schedules.
- `colony_architect.py` — live building catalog interpretation and procedural room/base design.
- `colony_strategy.py` — audited Core/DLC direction catalogue and conditional doctrine selection.
- `DIRECTION_AUDIT.md` — source-backed coverage matrix and extension contract.
- `rimworld_laya.py` — local API client and combat decision loop.
- `colony_combat.py` — tactical catalogue, threat-sensitive filtering and psycast choices.
- `colony_events.py` — extensible event-family classification and response hierarchy.
- `autopilot_control.py` — stable Windows GUI launcher (`laya_control.py` remains a compatibility entry point).
- `laya_gui/` — themed bilingual interface, friendly history, process/export services and graphical setup assistant.
- `laya_preferences.py` — validated player priority and safety guidance shared with all decision loops.
- `GUI.md` — interface architecture and installer contract.
- `vendor/RIMAPI/` — complete corresponding source and compiled RimWorld 1.6 assembly for the modified GPL-3.0 mod.
- `tests/` — deterministic unit tests for safety and blueprint logic.
- `CUSTOM-RIMAPI.md` — added endpoint summary.

## Build and test

Python:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m py_compile colony_director.py colony_professions.py colony_architect.py colony_strategy.py laya_preferences.py rimworld_laya.py autopilot_control.py autopilot_setup.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Modified RIMAPI (requires the .NET 8 SDK; targets .NET Framework 4.7.2 through reference packages):

```powershell
dotnet build vendor\RIMAPI\Source\RIMAPI\RimApi.csproj -c Release-1.6
```

Reproducible Windows GUI binaries (creates a separate build environment):

```powershell
.\Build-GUI.ps1
```

The same command assembles `dist/rimworld-autopilot-0.0.2.zip` and compiles `dist/RimWorld-Autopilot-0.0.2-Setup.exe` with Inno Setup 6.7+. The installer embeds the complete payload, a temporary post-install configuration assistant, the custom portrait artwork and standard Windows uninstall metadata.

The 0.0.2 development branch passes 82 Python tests, smoke-tests both Tk applications and compiles the C# mod with zero warnings/errors.

## Data and privacy

- Inference is local.
- The model is downloaded from Hugging Face on first run.
- The game API listens locally; do not expose port 8765 to a network.
- `logs/`, save files, model caches, `rimworld-autopilot.json` and `autopilot-preferences.json` are excluded from Git. Legacy Laya-named local files are ignored and migrated when present.
- Decision logs may contain pawn names and colony details. Review them before sharing an export.

## Limitations

- RimWorld is a complex, partially observable simulation; completion of the selected ending is not guaranteed.
- The current release targets Windows and RimWorld 1.6.
- Mod compatibility is not guaranteed.
- Trade purchasing is expressed as a priority; not every trader or transaction can satisfy it.
- Building placement is heuristic and may require later expansion or recovery from blocked terrain.
- The root Laya checkpoint is English-oriented, so internal decision prompts are English even though the GUI is Russian.

## Open-source thanks

Special thanks to:

- [Convai Innovations and Laya contributors](https://github.com/NandhaKishorM/laya) for releasing the Laya SDK and model weights under Apache‑2.0.
- [Ilya Chichkov / RedEyeDev and RIMAPI contributors](https://github.com/IlyaChichkov/RIMAPI) for the GPL‑3.0 RimWorld REST API this project extends.
- [Andreas Pardeike and Harmony contributors](https://github.com/pardeike/HarmonyRimWorld) for the RimWorld patching foundation.
- [Hugging Face Transformers contributors](https://github.com/huggingface/transformers) and [PyTorch contributors](https://github.com/pytorch/pytorch) for the local inference stack.
- The RimWorld modding community for years of mechanics documentation and experimentation.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for licensing details.

## License

This combined repository is licensed under **GNU GPL v3.0**. The Laya model and SDK remain under their own Apache‑2.0 license and are not redistributed here. Third-party components retain their original copyrights and licenses.

RimWorld is a trademark of Ludeon Studios. This project is unofficial and not affiliated with or endorsed by Ludeon Studios.
