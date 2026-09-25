# Steam Community Guide draft

Game: RimWorld
Category: Modding or Configuration
Language: English
Branding image: steam-guide-icon.png

## Title

Can Laya Run a RimWorld Colony? — Autopilot Experiment & Setup

## Short description

Give a local decision model the colony. Watch its choices, then try the free, open-source Windows build yourself.

## Section: The experiment

What happens when you hand a RimWorld colony to a neural net and let it make the calls?

I built RimWorld Autopilot to find out. It reads the live colony, weighs moves the game can actually carry out, and issues orders. Food, shelter, construction, research, raids, injuries, trade: Laya has to choose what matters now, then reconsider when the situation changes.

The optional in-game overlay shows the alternatives it weighed as yellow bars. The desktop app keeps a history of those decisions, lets you adjust priorities, and gives you a Stop button when you want the colony back.

## Section: Why Laya?

Laya isn't a chat model writing a long plan. It's an open-weight decision model: give it a compact picture of the colony and a set of possible moves, and it scores the choices. That makes it a good fit for a game full of small, time-sensitive decisions. It runs locally after the first model download, needs no API key, and makes its choices visible instead of hiding them inside a paragraph.

This is the experiment: can those decisions add up to a functioning colony when weather, hunger, and raids keep changing the problem?

## Section: See it play

[url=https://github.com/Georgy-hook/rimworld-autopilot/releases/download/v0.0.4/RimWorld-Autopilot-promo.mp4]Watch the gameplay reel[/url] — combat, building, foraging, and care, with Laya's choice bars on screen.

## Section: Try it

You'll need RimWorld 1.6 on Windows 10 (1809+) or Windows 11, Harmony, and Python 3.10–3.12.

1. [url=https://github.com/Georgy-hook/rimworld-autopilot/releases/latest/download/RimWorld-Autopilot-Installer.exe]Download the latest Windows installer[/url].
2. In Setup, leave “Configure Python, the local model and the RimWorld mod now” selected.
3. Enable Harmony above “RIMAPI — RimWorld Autopilot” in RimWorld's mod list, then restart the game.
4. Load a colony, open RimWorld Autopilot, and click “Start Laya”.

Start with a copy of a save: this is an experiment, and the colony's fate is part of it.

[url=https://github.com/Georgy-hook/rimworld-autopilot]Source code, screenshots, and full installation notes[/url]

RimWorld Autopilot is an unofficial, free, open-source community project.
