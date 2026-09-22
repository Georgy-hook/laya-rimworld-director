# Security

The director accepts only loopback RIMAPI URLs (`localhost`, `127.0.0.1`, or `::1`). Do not expose RIMAPI to the public internet.

Do not commit saves, decision logs, colony-state files, access tokens, model cache contents, or a populated `rimworld-autopilot.json`. The supplied `.gitignore` excludes these and legacy local configuration names by default.

This software can issue real in-game orders and can lose a colony. Use a copied save while testing. Report security issues privately to the repository owner through GitHub's security advisory feature when available.
