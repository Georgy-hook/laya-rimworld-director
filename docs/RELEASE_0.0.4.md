# RimWorld Autopilot 0.0.4

An experimental Laya-directed RimWorld 1.6 autopilot for Windows. This release brings the updated local Laya SDK, richer choice context, squad-combat tactics, procedural construction choices, GUI decision feedback, and a short promotional montage.

## Install

Download **RimWorld-Autopilot-0.0.4-Setup.exe** below. It installs the app, offers a desktop shortcut, registers a Windows uninstaller, and opens a one-time configuration assistant. You need RimWorld 1.6, Harmony, Python 3.10–3.12, and Internet access for the first Laya model download. The model weights are not bundled with the installer. The ZIP is a portable/source inspection package for maintainers.

## Highlights

- Laya 0.3.7 receives compact colony context and compares feasible choices; the bridge validates live game IDs, costs, and commands. Single-outcome decisions bypass the model.
- Thirty-six situational combat tactics cover mixed melee/ranged squads, bounded kiting, short trap-free advances, regrouping, and threat-aware retreat trade-offs.
- Construction plans expose material, entrance, room-style, and component trade-offs, with stable layout variations.
- The GUI can collect local decision corrections for future training data. Corrections do **not** retrain the bundled checkpoint.
- The English in-game HUD displays unequal yellow bars from actual model option weights. Those weights are **not** probabilities of success.
- The promo montage and five gameplay source clips are attached here; four lightweight GIF previews appear in the README.

Validation: 153 Python tests, GUI/setup smoke checks, GUI asset validation, and a C# RIMAPI build with zero warnings and errors. Fresh PyInstaller, ZIP, and Inno Setup packages were built for this tag. This is **not** an exhaustive live-game benchmark. Autonomy is experimental; use a copied save and expect possible colony failure.

The project's [README](https://github.com/Georgy-hook/rimworld-autopilot#readme) has installation details and acknowledgments. Full changes are in [RELEASE_NOTES.md](https://github.com/Georgy-hook/rimworld-autopilot/blob/main/RELEASE_NOTES.md).
