# Decision architecture

Version 0.0.2 follows the way the Laya/Jev ecosystem is used in public examples: deterministic application code projects state and defines typed alternatives; the model ranks a bounded choice; application code validates and reduces the answer into an effect.

References reviewed before this redesign:

- [Laya SDK](https://github.com/NandhaKishorM/laya) — typed `choice`, `score`, and `noul` decisions over compact state.
- [Laya + Jev laboratory](https://github.com/yibie/laya-jev-lab) — practical composition of the local model and typed decision layer.
- [JevLoop](https://github.com/zjunlp/JevLoop) and [Typesafe Jev examples](https://github.com/rajivkuriakose/typesafe-jev-examples) — narrow typed decisions inside a deterministic control loop.
- [Jev use-case playbook](https://github.com/Anil-matcha/awesome-jev-by-typesafe/blob/main/docs/jev-use-case-playbook.md) — conditional follow-up questions are built after the selected branch is known.

## Pipeline

```text
RIMAPI snapshot
  → deterministic feasibility and safety gates
  → decision domain (only when the candidate set is large)
  → action family (only when still large)
  → one concrete action
  → parameters for that action only
  → validation against the same snapshot
  → ordinary RimWorld job / bill / zone / blueprint / designation
  → decision log and overlay
```

Hunting, taming, wild harvesting, flooring, paths, doctrine, sculpture placement, temples, construction projects, trade and combat rosters therefore have conditional parameter stages. A rejected branch cannot accidentally select or execute one of its targets.

## Responsibility boundary

Laya decides preferences and trade-offs. Code remains responsible for facts and invariants:

- target IDs must exist in the current snapshot;
- research, skills, materials, temperature and power prerequisites must be satisfied;
- remote API addresses and cheat endpoints are rejected;
- dangerous/lethal organ plans are explicit, never a side effect of a sale/recruit choice;
- battle candidates carry weapon, trait, injury, pain and body-capacity context;
- repeated orders are suppressed, while stalled plans can be retried after a bounded interval.

This is intentionally not a free-form agent that invents API calls. Adding a capability requires a typed candidate, compact context, validation, a normal-game executor and a deterministic test.
