# Colony direction audit

This audit defines “all directions” as complete coverage of the strategic mechanics exposed by Core and every official expansion, not an impossible list of every player-created story. Laya composes a colony from an archetype plus independent settlement, economy, technology, defense, society, diplomacy and endgame axes. That makes mixed strategies possible without hard-coding every permutation.

Official sources checked for this audit:

- [RimWorld DLC catalogue](https://store.steampowered.com/dlc/294100/RimWorld/) — current official expansion set.
- [Royalty](https://store.steampowered.com/app/1149640/RimWorld__Royalty/) — titles, throne rooms, permits, psycasts, Empire quests and royal ascent.
- [Ideology](https://store.steampowered.com/app/1392840/RimWorld__Ideology/) — memes/precepts, roles, rituals, dryads and the Archonexus route.
- [Biotech](https://store.steampowered.com/app/1826140/RimWorld__Biotech/) — children, genes, sanguophages, mechanitors, mech armies and pollution.
- [Anomaly](https://store.steampowered.com/app/2380740/RimWorld__Anomaly/) — entity containment/research, bioferrite, rituals, monolith progression and the void ending.
- [Odyssey](https://store.steampowered.com/app/3022790/RimWorld__Odyssey/) — gravships, planetary/orbital exploration, vacuum survival, fishing, wildlife and the mechhive campaign.

The installed RimWorld data was checked as a second source of truth. This machine currently has Core, Royalty, Ideology, Biotech and Anomaly definitions. Odyssey is represented in the catalogue but is automatically hidden until its package is active.

## Coverage result

`colony_strategy.py` contains 30 strategic archetypes across all seven domains:

| Domain | Count | Covered play styles |
|---|---:|---|
| Survival | 4 | resilient settlement, farming, ranching, medical sanctuary |
| Prosperity | 5 | industry, mining, luxury/art, trade hub, fishing/wildlife frontier |
| Technology | 6 | starflight, tribal psycasting, mechanitors, genetics, pollution, Anomaly containment |
| Society | 5 | Royal court, ideology, dryads, family dynasty, sanguophages |
| Power | 3 | fortress, raiding, void ritualists |
| Exploration | 4 | caravans, quests, gravships, orbital salvage |
| Endgame | 3 | Archonexus pilgrimage, Anomaly mastery, mechhive campaign |

Expansion coverage is 13 Core, 2 Royalty, 3 Ideology, 5 Biotech, 3 Anomaly and 4 Odyssey archetypes. The composition axes add:

- 8 economy families with 24 exact products or revenue mechanisms;
- 17 technology emphases;
- 10 defense doctrines;
- 12 social models;
- 10 settlement forms plus a live-terrain-gated mountain base;
- 8 diplomatic postures;
- all six official continuity/victory choices: enduring colony, own ship, Royal ascent, Archonexus, Anomaly finale and Odyssey mechhive campaign.

## Runtime verification and cascade

The catalogue is not presented blindly. Before Laya chooses, the director reads active package IDs, the live `ResearchProjectDef` tree, loaded `BuildingDef` catalogue, all `WorkTypeDef` entries and the current colonists. Inactive DLC branches are removed and every remaining direction receives workforce and live-content signals.

Selection is conditional:

```text
broad domain
  → compatible exact direction
  → settlement/economy/technology/defense/society/endgame axes
  → product inside the selected economy family only
  → local mineral type only when mining was selected
```

The saved version-2 doctrine then changes actual future behavior:

- research candidates come only from live, unfinished and currently startable projects matching the doctrine;
- architecture programs merge the strategic direction with workforce specialization;
- fortification candidates are filtered by the selected defense doctrine;
- a ship is built only when ship escape is the selected ending;
- existing buildings are never demolished merely because a preference changes;
- the GUI displays the chosen course, subordinate axes, active expansions, available direction count and the complete list of currently valid archetypes;
- every cascade choice and probability distribution is retained in the decision history.

## Extension rule

Mods remain discoverable through live work, building and research definitions. A mod-specific named archetype can be added as one catalogue record with its package requirement, mechanics, building programs and research tokens; it does not require changing the selection pipeline. Unknown content can improve a direction's live score but is not allowed to bypass ordinary feasibility or safety checks.
