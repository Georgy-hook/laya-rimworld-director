# 0.0.2 — hierarchical decisions and colony logistics

Development release focused on correcting the decision architecture and the survival failures observed in live colonies.

Highlights:

- hierarchical Laya/Jev flow: domain → action family → action → only the selected action's parameters;
- exact construction-project and builder selection through normal RimWorld work givers;
- real beds after emergency sleeping spots, with skill and resource gates;
- distant human-corpse dumps, animal-carcass storage by butchering, graves, cremation, and Laya-selected corpse haulers;
- stone-chunk storage next to stonecutting;
- outdoor roads limited to stone flagstone; early paths are one cell wide;
- freezers are not placed without enough steel/components and either existing power or the resources for a generator;
- full pawn context for traits, visible injuries, missing body parts, pain, consciousness, movement, manipulation and sight;
- Laya-selected combat roster using that pawn context;
- optional prisoner-organ economy with explicit nonlethal/lethal plans and normal surgery bills;
- Ideology context plus a ritual-room plan using the colony's actual altar or ideogram;
- stockpile priorities now preserve RimWorld's complete 0–5 range, so Critical food/corpse zones work as intended;
- 34 deterministic Python tests and a zero-warning C# build.

The branch remains experimental. Use copied saves and review the GUI/overlay decision history.

# 0.0.1 — experimental public preview

First open-source release of an autonomous RimWorld colony director driven by the local Laya decision model.

Highlights:

- local inference; no remote gameplay service;
- normal RimWorld jobs and designations, with no spawning or instant construction;
- food, farming, storage, rooms, animals, health, research, industry, trade, caravans and long-term starflight planning;
- contextual combat handling for staging raids, insects and mechanoids;
- Ancient Danger is treated as a sealed strategic site, not a raid, and verified threat auto-pauses are resumed after a decision;
- persistent doctrine covering settlement form, materials, economy, diplomacy, military emphasis and beauty;
- in-game decision overlay and Windows control center with exportable history;
- 25 automated Python tests and a reproducible modified RIMAPI source tree.

This is an experiment, not a promise of competent play. Back up your saves.
