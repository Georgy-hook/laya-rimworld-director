# Stream Observer

Open **Stream / Эфир** in RimWorld Autopilot and select **Enable Observer / Включить наблюдателя** after loading a colony. The status and current shot appear on that page. **Disable / Выключить** stops the camera process. The observer is independent of Laya's colony director: it never assigns jobs, drafts colonists, or changes Laya's choices. It can run while the GUI is closed; reopening the GUI shows the same process. If enabled in preferences, reopening the GUI also restarts it after a prior exit.

The shot order is based on real elapsed time:

1. A colonist death gets one 20-second close-up and an English caption with the cause reported by RIMAPI. If the game does not report a cause, the caption says so or names the last known condition. After that, the camera returns to a living colonist. A departure from the map alone is not treated as death.
2. Active fights take priority. The camera starts close, moves to a medium view after 10 seconds, and rotates among multiple fighters every 30 seconds.
3. New raiders receive a montage of up to 30 seconds, divided between the visible enemies, before the camera returns to the colony. Active fighting interrupts this montage.
4. Injured or sick colonists get occasional priority shots, with a cooldown so one patient cannot monopolize the broadcast.
5. During quieter work, the camera rotates between colonists every 45 seconds: 10 seconds close, then a wide view. Every 10 minutes it takes a short five-stop tour of the map at wide zoom.

While this mode is on, the observer resumes any game pause—including a manual pause—and requests 3× speed. It retries every five real seconds so raids or other events that force 1× do not leave the broadcast slow. Shot lengths and camera rotations still use real seconds, regardless of game speed. Turn the mode off if you want the game to stay paused. The observer waits for the next loaded colony when the game is at the main menu or temporarily unavailable. This mode does not start an OBS or Twitch broadcast by itself.

The script can also run without the GUI, using the configured Python environment:

```powershell
.\.venv\Scripts\python.exe stream_observer.py `
  --pid-file logs\observer.pid `
  --status logs\observer-status.json `
  --log logs\observer.jsonl
```

The local RIMAPI address defaults to `http://localhost:8765`; use `--api-url` if you configured another loopback address. Only run one observer process against a game at a time. The GUI owns its observer process and writes status/log files alongside the director logs; installed builds place them under `%LOCALAPPDATA%\RimWorld Autopilot\logs`.
