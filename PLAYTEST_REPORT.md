# Colony playtest log

App version: **0.0.4** (development branch; the tests below may use unreleased changes).

This log tracks real, unattended runs. “Cause” is the last condition reported by the game API, not a medically certain cause of death. Wall-clock runtime excludes intentional development pauses when noted.

## Test 1 — 25 September 2026

- Colony: Pepe, Triv and Bolton; Doc joined later. Cassandra, seed `16622162`.
- Decision log: 07:59–09:08 UTC, about 45 minutes of active decisions with a development pause between 08:29 and 08:53.
- End state: Pepe and Triv were both downed; the run was stopped rather than observed to their deaths.

| Colonist | Outcome | Time (UTC) | Last reported condition / context |
| --- | --- | --- | --- |
| Doc | Died | 09:06 | Scratch wound to arm; the group had engaged a rhinoceros in melee. |
| Bolton | Died | 09:07 | Bruise to torso; the same rhinoceros fight. |
| Pepe | Downed at stop | 09:08 | Could not be fed because no mobile feeder was available. |
| Triv | Downed at stop | 09:08 | Cause of incapacitation was not established from the retained log. |

Main Laya failures: it repeatedly chose to wait despite unfinished survival work, then sent multiple colonists into melee against a rhinoceros. Post-fight care could not feed the remaining downed people.

## Test 2 — 25 September 2026

- Colony: restarted from an earlier save with Pepe, Triv and Bolton; same seed `16622162`.
- Decision log: 09:16–10:22 UTC, about 66 minutes elapsed.
- End state: Pepe remained as the sole colonist.

| Colonist | Outcome | Time (UTC) | Last reported condition / context |
| --- | --- | --- | --- |
| Bolton | Died | 10:16 | Arm wound infection. |
| Triv | Died | 10:17 | Scratch wound to torso; the death caption incorrectly repeated on later camera passes. |
| Pepe | Alive at stop | 10:22 | Sole survivor. |

Main Laya failures: wounds and infection still overwhelmed care; the camera replayed Triv's death instead of showing it once. Laya attempted orbital trading without powered communications infrastructure, and the shelter was still unfinished. A visiting trader transaction did succeed earlier in the run (five medicine purchased).

## Test 3 — 25 September 2026

- Colony: seed `16622162`, Cassandra, new three-person start.
- Observed: 10:56–12:00 UTC; approximately 60 minutes of active play plus a four-minute development pause.
- End state: one survivor (Skagnetti); the game was paused for fixes. The founding colony failed to sustain its population.

| Colonist | Outcome | Time (UTC) | Last reported condition / context |
| --- | --- | --- | --- |
| Merandil | Died | 11:20 | Stab wound to torso; injury and infection were present during the run. |
| Ivy | Died | 11:47 | Scratch wound to neck; wounded after a melee raid. |
| Sleepy | Died | 11:48 | Stab wound to arm; downed during the same raid. |
| Skagnetti | Alive at stop | 12:00 | Joined later; the only remaining colonist. |

Notes and main Laya failures:

- The first housing plan was too large and displaced from the dry-site check. Walls, beds and floors did not become a complete roofed home; several beds existed but colonists still used ground spots.
- Laya queued dozens of projects while wood and construction labor were scarce. It continued to consider research and hunting with shelter unfinished.
- During a close melee raid, two armed colonists selected a melee response rather than keeping a shooting lane. Both eventually died. The choice context exposed their weapons, but the final tactical comparison omitted a retreat-and-fire option.
- The observer restored 3× after raid speed resets; death captions and camera dwell were checked. The game UI and API were cross-checked during the run.
- Fixes prompted by this test are being developed and must be judged by a fresh colony, not credited retroactively to this run.

## Test 4 — 25 September 2026

- Colony: Shen, Lee and Miray; Kaiser joined later. Cassandra, temperate forest on seed `16622162`, tile `20942`.
- Observed: about 13:27–14:37 UTC, approximately 70 minutes elapsed, including development pauses and director restarts. The colony reached 1 Jugust 5501.
- End state: Miray and Kaiser alive. Lee and Shen were kidnapped in separate raids; neither was confirmed dead. The run was stopped because the remaining crew had no eligible builder, no stored food, and no completed cooking station.

| Colonist | Outcome | Time (UTC) | Last reported condition / context |
| --- | --- | --- | --- |
| Lee | Kidnapped | About 14:00 | Taken by Trash Packers in the first major raid; a future rescue opportunity may appear. |
| Shen | Kidnapped | About 14:29 | Taken in a later raid after repeated fighting and mental breaks. |
| Miray | Alive at stop | 14:37 | Could haul and grow, but could not do Construction. Food reserves were empty. |
| Kaiser | Alive at stop | 14:37 | Joined after Shen was taken; was hunting, but could not do Construction. |

Notes and main Laya failures:

- The verified dry-site start produced a roofed barracks, but real beds were initially scattered outdoors or in distant rooms. A later roof collapse and raids left only sleeping spots.
- Starting food ran out without a finished cooking station. Laya could designate hunts and harvests, but no one left in the colony could build a campfire after Shen was captured.
- Shen suffered exhaustion- and mood-related breaks. Persephone, a bonded yorkshire terrier, died during the run, further affecting Miray's mood.
- The first rescue handler repeatedly accepted an unrelated quest for Makoto as if it rescued Lee. This was fixed during the run; the mistaken acceptance is not a successful Lee rescue.
- Other live fixes addressed notification letters interrupting the decision loop, an oversized decision context, a lost medical-bed/fire-target selection, and rapid work-priority reversals. They need a fresh colony to verify their long-term effect.
