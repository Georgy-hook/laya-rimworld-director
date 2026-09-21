# Contributing

Issues and pull requests are welcome. Please keep gameplay automation honest: use normal RimWorld jobs, designations, bills, blueprints, research and trade. Do not add resource spawning, stat editing, teleportation, fog-of-war leaks or instant construction.

Before opening a pull request:

```powershell
python -m py_compile colony_director.py rimworld_laya.py laya_control.py
python -m unittest discover -s tests -v
dotnet build vendor/RIMAPI/Source/RIMAPI/RIMAPI.csproj -c Release-1.6
```

Never include a save or files from `logs/` in a bug report. Redact pawn names and other player-specific data from diagnostics.
