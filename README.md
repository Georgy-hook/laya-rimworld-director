# Laya RimWorld Director

> Experimental autonomous colony management for RimWorld 1.6, powered by the local open-weight Laya decision model.

Version **0.0.1** · Windows · Python 3.10+ · RimWorld 1.6 · GPL-3.0

Laya RimWorld Director reads a colony through a modified local RIMAPI mod, gives the model a bounded set of real and currently feasible choices, and converts the selected choice into ordinary RimWorld work priorities, designations, bills, blueprints, research, caravans and combat orders.

It is not a prerecorded build order. Laya sees compact context, chooses between alternatives with probabilities, keeps a persistent colony doctrine, and can revise that doctrine when resources or conditions change. The long-term objective is a self-sufficient colony that researches, builds and launches a ship.

The project is unofficial and experimental. It can make bad decisions and lose a colony. **Use a copied save.**

## What 0.0.1 can do

- Food: unforbid starting supplies, create food storage/freezer space, cook, butcher, hunt and harvest wild edible plants.
- Farming: select crops, consider current season and forecast temperatures, pause late sowing without destroying existing crops, and resume viable seasonal sowing.
- Storage: expand near-full stockpiles and configure dedicated weapon shelves.
- Housing and rooms: choose compact, courtyard, separate-house or mountain development; choose real available construction materials; build private bedrooms without replacing existing rooms.
- Beauty and hygiene: measure room cleanliness and impressiveness, choose kitchen/hospital floors, commission sculptures and install finished art in a selected real room.
- Animals: feed and rescue colony animals, avoid repeatedly treating an already-bandaged animal, make sleeping spots, build climate-aware barns, use optional straw matting, tame a selected species/sex and plan breeding.
- Industry and income: stonecutting, drugs, clothing, sculptures, livestock products, chemfuel, valuable minerals, crops, beer, travel food and orbital trade.
- Diplomacy and travel: choose a real friendly settlement, form a safe trade caravan, retain home defenders and supplies, and resolve prisoner recruit/release/sale plans through normal systems.
- Defense: layered firing positions, traps, turrets, mortars, firefoam, weapons/armor research and equipment priorities.
- Combat: distinguish staging raids from active assaults, either prepare undrafted or strike, resume verified raid auto-pauses, coordinate several healthy fighters, and prioritize insects, mechanoids or EMP where appropriate.
- Ancient Danger: treat the proximity warning as a sealed strategic site rather than a raid; Laya chooses to leave it, prepare, or designate a normal wall-deconstruction job to open it, then resumes the warning pause.
- Long-term doctrine: settlement form, default material, economy, diplomacy, military emphasis, mining product and beauty priority persist across cycles and appear in the GUI.
- Observability: an in-game overlay and Windows control center show choices, probabilities, results and exportable history.

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

Download the `laya-rimworld-director-0.0.1.zip` release, extract it, open PowerShell in the extracted folder and run:

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

The installer creates `.venv`, installs `laya==0.3.4`, backs up an existing local `Mods\RIMAPI` folder, installs the modified build, and creates a machine-local `laya-control.json`.

Then:

1. In RimWorld, enable Harmony and **RIMAPI — Laya Director fork**.
2. Restart RimWorld.
3. Load a copied colony save.
4. Run `Start-Autonomous.ps1` or open `Laya-Control-Center.exe` from the release and click **Запустить Laya**.
5. The first start downloads `convaiinnovations/laya` from Hugging Face.

Stop the console director with `Ctrl+C`, or click **Остановить** in the GUI.

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

Each cycle follows four stages:

1. Collect a bounded snapshot from local RIMAPI endpoints.
2. Build only feasible choices using verified IDs, resources, skills, research, temperature, rooms, factions and map state.
3. Ask Laya one or more typed choice questions and retain its probabilities.
4. Validate the selected choice again and translate it into normal game commands.

Emergency survival gates run before long-horizon planning. Combat is checked much more often than ordinary development. Repeated orders are suppressed using a persistent state file and signatures of active combatants/jobs.

The model is a fast decision classifier, not a text-generating agent. The controller — not the model — defines the allowed actions and validates their parameters.

## Architecture

```text
RimWorld 1.6
  ↕ localhost:8765
modified RIMAPI (C#, Harmony)
  ↕ verified JSON state / normal gameplay commands
colony_director.py
  ↕ typed questions + probabilities
convaiinnovations/laya (local PyTorch model)

laya_control.py / in-game overlay
  ↳ status, doctrine, candidate history, export, start/stop
```

Important files:

- `colony_director.py` — long-horizon autonomous planner and executor.
- `rimworld_laya.py` — local API client and combat decision loop.
- `laya_control.py` — Windows GUI.
- `vendor/RIMAPI/` — complete corresponding source and compiled RimWorld 1.6 assembly for the modified GPL-3.0 mod.
- `tests/` — deterministic unit tests for safety and blueprint logic.
- `CUSTOM-RIMAPI.md` — added endpoint summary.

## Build and test

Python:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m py_compile colony_director.py rimworld_laya.py laya_control.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Modified RIMAPI (requires the .NET 8 SDK; targets .NET Framework 4.7.2 through reference packages):

```powershell
dotnet build vendor\RIMAPI\Source\RIMAPI\RIMAPI.csproj -c Release-1.6
```

The 0.0.1 release passes 25 Python tests and compiles the C# mod with zero warnings/errors.

## Data and privacy

- Inference is local.
- The model is downloaded from Hugging Face on first run.
- The game API listens locally; do not expose port 8765 to a network.
- `logs/`, save files, model caches and `laya-control.json` are excluded from Git.
- Decision logs may contain pawn names and colony details. Review them before sharing an export.

## Limitations

- RimWorld is a complex, partially observable simulation; successful starflight is not guaranteed.
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
