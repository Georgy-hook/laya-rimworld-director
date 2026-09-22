from __future__ import annotations

import argparse
import ctypes
import json
import os
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Any

import rimworld_laya as bridge
import colony_architect as architect
import colony_professions as professions
import colony_events as events
import colony_strategy as strategy
import laya_preferences


RESEARCH_ROUTE = [
    "Electricity",
    "Batteries",
    "MicroelectronicsBasics",
    "MultiAnalyzer",
    "Fabrication",
    "AdvancedFabrication",
    "ShipBasics",
    "ShipCryptosleep",
    "ShipReactor",
    "ShipEngine",
    "ShipComputerCore",
    "ShipSensorCluster",
]

PATIENT_FEED_RETRY_TICKS = 12000

ACTION_DESCRIPTIONS = {
    "plan_architecture": "Choose a needed building program first, then let Laya select one procedurally generated, resource- and technology-aware layout. Housing alone provides 24 varied designs without storing 24 rigid blueprints.",
    "improve_room_lighting": "Add a real light source to one dark high-value room selected by Laya; work rooms and hospital treatment should not operate in darkness.",
    "develop_colonist_skill": "Choose a colonist, skill and matching live WorkType using current level, small/large passion flames, learning traits, health and the colony's strategic gaps.",
    "optimize_night_owl_schedule": "Move one Night Owl colonist's sleep to 11:00-18:59 and leave the night flexible for work and recreation.",
    "upgrade_workbench": "Build an unlocked successor workbench beside the old one; keep the old bench until the upgrade is completed so production never disappears mid-transition.",
    "unforbid_supplies": "Remove the red forbidden marks from landed supplies so colonists can eat, equip and haul them.",
    "create_food_stockpile": "Create a high-priority food-only stockpile inside the planned freezer.",
    "build_sleeping_spots": "Place free sleeping spots first; these cannot waste scarce construction materials in botched attempts.",
    "build_basic_beds": "Replace emergency sleeping spots with real beds once a capable builder and enough material are available.",
    "build_animal_spots": "Place free animal sleeping spots so injured colony animals can rest and receive treatment.",
    "care_for_injured_animal": "Send the best available doctor to the most seriously injured colony animal and assign animal bed rest.",
    "feed_hungry_animal": "Immediately feed the hungriest resting colony animal before starvation becomes critical.",
    "feed_hungry_colonist": "Immediately feed the hungriest downed colonist who cannot walk to available food.",
    "build_cemetery": "Create a real graveyard outside the living and food areas so human corpses can be buried normally.",
    "create_human_corpse_dump": "Create a critical-priority human-corpse dumping stockpile far outside colonist sight; this is faster than digging many graves.",
    "create_animal_corpse_dump": "Create a critical-priority animal-corpse stockpile beside the butcher area so carcasses are hauled and processed efficiently.",
    "create_stone_chunk_dump": "Create a preferred stone-chunk dumping stockpile beside the stonecutter to remove long hauling trips.",
    "build_crematorium": "Build an electric crematorium and configure corpse cremation when power, steel, components and labor justify it.",
    "build_prison": "Build a small enclosed two-bed prison so a downed hostile can be captured through the normal Capture job.",
    "build_hospital": "Build a small enclosed two-bed clinic and later mark its completed beds medical.",
    "configure_hospital_beds": "Mark the completed clinic beds as medical beds.",
    "floor_critical_room": "Floor a real kitchen, food room or hospital chosen by Laya with an affordable material, balancing cleanliness, fire, work and reserves.",
    "build_pathways": "Build an affordable two-wide path between the colony core, stores and fields to improve routine movement speed.",
    "build_temple": "Build an Ideology-compatible ritual room around the colony's actual altar or ideogram precept, with no beds or work facilities.",
    "choose_colony_doctrine": "Choose or deliberately revise a persistent colony doctrine: settlement form/material, peaceful or aggressive posture, military investment, and production identity. Existing buildings are never replaced merely because the doctrine changes.",
    "build_private_bedroom": "Build one separate private bedroom in the current settlement material, improving sleep privacy and enabling an impressive-bedroom mood bonus without rebuilding existing rooms.",
    "excavate_mountain_bedroom": "Mine a compact bedroom into a verified solid natural-rock block, leaving natural rock walls and a one-cell entrance; furnish it only after excavation completes.",
    "finish_mountain_bedroom": "Furnish the already excavated mountain bedroom with a door, bed, light and climate control without replacing older housing.",
    "commission_sculptures": "Build or use an art bench and commission small sculptures so Laya can later place actual finished art in the highest-value room.",
    "install_sculpture": "Install one actual finished sculpture in a room selected by Laya: usually a shared dining/rec room, a weak bedroom, hospital, or long-duration workshop.",
    "build_weapon_shelves": "Build high-priority shelves for weapons and armor, protecting equipment from deterioration and removing loose-item beauty penalties.",
    "prioritize_armament": "Prioritize the doctrine's weapon or armor research and configure normal crafting bills when the required workshop and resources exist.",
    "build_animal_barn": "Build a temperature-aware animal barn with sleeping places and optional low-filth straw matting, preserving fire safety and hay reserves.",
    "pause_late_sowing": "Disable sowing in existing outdoor growing zones when present temperature and remaining growing season make a harvest unlikely; existing mature crops remain harvestable.",
    "resume_seasonal_sowing": "Re-enable sowing when outdoor growing conditions become viable again.",
    "unforbid_corpses": "Remove forbidden marks from corpses so haulers can bury people and butcher usable animal carcasses.",
    "prioritize_burial": "Give Hauling priority 1 so exposed corpses are taken to graves or the butcher area.",
    "build_freezer": "Build a compact powered freezer around the food stockpile.",
    "create_stockpile": "Create an organized stockpile so materials are hauled into one known place.",
    "expand_stockpile": "Expand general storage because at least 90% of current stockpile cells are occupied.",
    "create_growing_zone": "Create a rice growing zone to establish renewable food production.",
    "build_starter_base": "Place legitimate construction blueprints for a roofable shelter, beds, dining, cooking and a simple research bench.",
    "configure_food_bills": "Add sustainable simple-meal and butchering bills to completed work tables.",
    "advance_research": "Select the next available project on the default route toward fabrication and starflight.",
    "advance_doctrine_research": "Let Laya choose one currently available research project whose live definition advances the selected economy, technology, defense or endgame direction.",
    "build_power": "Place blueprints for a wood generator, battery, lighting and conduits.",
    "build_hitech_lab": "Place blueprints for a hi-tech research bench and multi-analyzer.",
    "build_fabrication": "Place a fabrication bench needed for advanced components.",
    "build_ship": "Place a connected starter starship blueprint with reactor, engine, computer, sensor and cryptosleep caskets.",
    "income_drugs": "Adopt a psychoid cash-crop route: grow surplus psychoid, research drug production, and later make sale-only flake/yayo.",
    "income_tailoring": "Adopt a textile route: grow cotton and turn surplus textiles/leather into trade apparel.",
    "income_art": "Adopt an art route: build a sculptor table and make sale sculptures from renewable wood or stone.",
    "income_livestock": "Adopt an animal route: prioritize handling and sell surplus animals, wool, milk and leather without starving the herd.",
    "income_biofuel": "Adopt a chemfuel route: tame boomalopes when safe and refine surplus organics after Biofuel Refining.",
    "income_mining": "Adopt a mining route: mine local gold/silver first, then research long-range scanning for guarded resource expeditions.",
    "income_crops": "Adopt a low-tech surplus-crop route: grow corn after the emergency rice supply is secure and sell only the reserve above colony needs.",
    "income_brewing": "Adopt a beer route: grow hops, research brewing, make wort and ferment it into a durable trade product.",
    "income_travel_food": "Adopt a caravan-food route: make pemmican or packaged survival meals for sale and for longer trade expeditions.",
    "income_orbital": "Adopt an orbital trade route: research microelectronics and build a comms console plus beacon for passing ships.",
    "income_organs": "Adopt a prisoner-organ trade route, balancing doctor skill, medicine, surgery risk, ideology and colony mood against organ value.",
    "build_income_infrastructure": "Build the missing workshop for the chosen income strategy after its prerequisite research is complete.",
    "build_killbox": "Build an early open-path defensive funnel with cover and spike traps; it is only the outer layer, not the whole defense.",
    "build_fallback_defense": "Build an internal fallback firing line and melee choke so breachers, drop pods and infestations do not bypass every defense.",
    "build_turret_defense": "Add powered turrets with spaced cover after Gun Turrets research; colonists still provide the main firepower.",
    "build_mortar_post": "Add a protected mortar position after Mortars research to answer sieges and enemies waiting at the map edge.",
    "build_firefoam_defense": "Place firefoam coverage near power, fuel and the defensive line so incendiary raids do not destroy the colony.",
    "start_stonecutting": "Research/build stonecutting and cut the stone type chosen by Laya from actual nearby chunks into fireproof blocks.",
    "start_taming": "Designate the exact nearby species and sex chosen by Laya for taming, considering handler skill and revenge risk.",
    "breed_animals": "Keep a chosen adult male/female pair of the same tame species together and prioritize handling so they can reproduce naturally.",
    "plan_human_reproduction": "Choose an existing romantic couple and a reproductive approach only when food, housing and safety can support a child.",
    "process_mechanoids": "Research/build machining and add a bill to dismantle mechanoid corpses for useful materials.",
    "prepare_trade_caravan": "Prepare a guarded trade expedition to a friendly settlement, keeping enough defenders, food and medicine at home.",
    "configure_income_production": "Configure the chosen workshop with a repeatable sale-goods bill while preserving survival reserves.",
    "prioritize_construction": "Give Construction priority 1 to the healthiest best builder so issued blueprints are completed.",
    "prioritize_construction_project": "Let Laya choose one exact unfinished blueprint/frame and a suitable builder, then issue a normal forced construction job.",
    "prioritize_research": "Give Research priority 1 to the healthiest best researcher so the starflight route advances.",
    "prioritize_cooking": "Give Cooking priority 1 to a capable healthy cook while prepared meals are scarce.",
    "prioritize_growing": "Give Growing priority 1 to a capable healthy grower so crops are planted and harvested.",
    "harvest_local_plants": "Let Laya choose one real nearby mature wild plant type, then designate only those exact plants for harvesting.",
    "prioritize_hauling": "Give Hauling priority 1 so unlocked food reaches the protected food stockpile.",
    "prioritize_hunting": "Give Hunting priority 1 to the best healthy shooter.",
    "prioritize_handling": "Give Handling priority 1 so colony animals are fed, trained and managed.",
    "prioritize_plant_cutting": "Give Plant Cutting priority 1 for wood and wild-food gathering.",
    "prioritize_cleaning": "Give Cleaning priority 1 to reduce filth, infection and food poisoning risk.",
    "prioritize_rescue": "Give Basic priority 1 so a healthy colonist rescues downed allies before routine work.",
    "prioritize_doctor": "Give Doctor priority 1 so injuries are treated before routine work.",
    "designate_safe_hunting": "Let Laya choose one exact nearby animal using meat/leather/value, revenge risk and the colony's available fighters; thrumbos require a strong firing team.",
    "leave_wildlife_alone": "Deliberately leave nearby valuable or dangerous wildlife alone when taming and hunting are not worth the present risk or workload.",
    "hold_survival": "Issue no new project while colonists eat, sleep, recover or finish already-issued survival work.",
}

ACTION_LABELS = {
    "plan_architecture": "архитектурный проект",
    "improve_room_lighting": "освещение комнаты",
    "develop_colonist_skill": "развитие навыка",
    "optimize_night_owl_schedule": "расписание совы",
    "upgrade_workbench": "модернизация верстака",
    "unforbid_supplies": "разрешить припасы",
    "create_food_stockpile": "пищевой склад",
    "build_sleeping_spots": "спальные места",
    "build_basic_beds": "обычные кровати",
    "build_animal_spots": "лежанки животных",
    "care_for_injured_animal": "лечение животного",
    "feed_hungry_animal": "кормление животного",
    "feed_hungry_colonist": "кормление лежачего колониста",
    "build_cemetery": "кладбище",
    "create_human_corpse_dump": "дальняя свалка человеческих трупов",
    "create_animal_corpse_dump": "свалка туш у разделки",
    "create_stone_chunk_dump": "склад каменных глыб у камнетёса",
    "build_crematorium": "крематорий",
    "build_prison": "тюрьма",
    "build_hospital": "больница",
    "configure_hospital_beds": "медицинские койки",
    "floor_critical_room": "пол в критической комнате",
    "build_pathways": "дорожки",
    "build_temple": "храм и ритуальная комната",
    "choose_colony_doctrine": "доктрина колонии",
    "build_private_bedroom": "отдельная спальня",
    "excavate_mountain_bedroom": "вырубить спальню в скале",
    "finish_mountain_bedroom": "обставить спальню в скале",
    "commission_sculptures": "заказать скульптуры",
    "install_sculpture": "поставить скульптуру",
    "build_weapon_shelves": "полки оружия и брони",
    "prioritize_armament": "оружие и броня",
    "build_animal_barn": "дом для животных",
    "pause_late_sowing": "остановить поздний посев",
    "resume_seasonal_sowing": "возобновить сезонный посев",
    "unforbid_corpses": "разрешить перенос трупов",
    "prioritize_burial": "захоронение и трупы",
    "build_freezer": "морозилка",
    "create_stockpile": "общий склад",
    "expand_stockpile": "расширение склада",
    "create_growing_zone": "рисовое поле",
    "build_starter_base": "жилой блок",
    "configure_food_bills": "рецепты еды",
    "advance_research": "новое исследование",
    "advance_doctrine_research": "исследование по доктрине",
    "build_power": "электросеть",
    "build_hitech_lab": "лаборатория",
    "build_fabrication": "станок компонентов",
    "build_ship": "космический корабль",
    "income_drugs": "доход: психоид",
    "income_tailoring": "доход: одежда",
    "income_art": "доход: скульптуры",
    "income_livestock": "доход: животные",
    "income_biofuel": "доход: химтопливо",
    "income_mining": "доход: ценные руды",
    "income_crops": "доход: излишки урожая",
    "income_brewing": "доход: пиво",
    "income_travel_food": "доход: дорожная еда",
    "income_orbital": "доход: орбитальная торговля",
    "income_organs": "доход: органы пленных",
    "build_income_infrastructure": "цех выбранного дохода",
    "build_killbox": "защитный коридор",
    "build_fallback_defense": "внутренняя линия обороны",
    "build_turret_defense": "турельная линия",
    "build_mortar_post": "миномётная позиция",
    "build_firefoam_defense": "противопожарная защита",
    "start_stonecutting": "каменные блоки",
    "start_taming": "приручение животного",
    "breed_animals": "разведение животных",
    "plan_human_reproduction": "планирование ребёнка",
    "process_mechanoids": "разбор механоидов",
    "prepare_trade_caravan": "торговая вылазка",
    "configure_income_production": "производство на продажу",
    "prioritize_construction": "строительство",
    "prioritize_construction_project": "приоритет конкретной постройки",
    "prioritize_research": "исследования",
    "prioritize_cooking": "готовка",
    "prioritize_growing": "растениеводство",
    "prioritize_hauling": "переноска",
    "prioritize_hunting": "охота",
    "prioritize_handling": "животноводство",
    "prioritize_plant_cutting": "заготовка растений",
    "prioritize_cleaning": "уборка",
    "prioritize_rescue": "спасение раненых",
    "prioritize_doctor": "лечение",
    "designate_safe_hunting": "безопасная охота",
    "leave_wildlife_alone": "оставить диких животных в покое",
    "harvest_local_plants": "сбор дикоросов",
    "hold_survival": "наблюдать",
}


def load_state(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"maps": {}}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def position(x: int, z: int) -> dict[str, int]:
    return {"x": int(x), "y": 0, "z": int(z)}


def building(def_name: str, x: int, z: int, *, stuff: str | None = None, rotation: int = 0) -> dict[str, Any]:
    result: dict[str, Any] = {"def_name": def_name, "rel_x": x, "rel_z": z, "rotation": rotation}
    if stuff:
        result["stuff_def_name"] = stuff
    return result


def floor(def_name: str, x: int, z: int) -> dict[str, Any]:
    return {"def_name": def_name, "rel_x": int(x), "rel_z": int(z)}


def blueprint(buildings: list[dict[str, Any]], width: int, height: int, floors: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"width": width, "height": height, "floors": floors or [], "buildings": buildings}


def starter_base_blueprint(colonist_count: int) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for x in range(11):
        if x != 5:
            items.append(building("Wall", x, 0, stuff="WoodLog"))
        items.append(building("Wall", x, 7, stuff="WoodLog"))
    for z in range(1, 7):
        items.append(building("Wall", 0, z, stuff="WoodLog"))
        items.append(building("Wall", 10, z, stuff="WoodLog"))
    items.append(building("Door", 5, 0, stuff="WoodLog"))
    items.extend(
        [
            building("Table2x2c", 4, 3, stuff="WoodLog"),
            building("Stool", 3, 3, stuff="WoodLog"),
            building("Stool", 7, 3, stuff="WoodLog"),
            building("FueledStove", 2, 5, rotation=2),
            building("ButcherSpot", 5, 5, rotation=2),
            building("SimpleResearchBench", 7, 5, stuff="WoodLog", rotation=2),
            building("TorchLamp", 5, 2),
        ]
    )
    return blueprint(items, 11, 8)


def animal_spots_blueprint(animal_count: int) -> dict[str, Any]:
    count = max(1, min(6, int(animal_count)))
    return blueprint([building("AnimalSleepingSpot", index * 2, 0) for index in range(count)], count * 2, 1)


def cemetery_blueprint(grave_count: int = 8) -> dict[str, Any]:
    """Two orderly rows of real 1x2 graves with walking space between them."""
    count = max(2, min(12, int(grave_count)))
    columns = min(4, count)
    items = [
        building("Grave", (index % columns) * 2, (index // columns) * 3)
        for index in range(count)
    ]
    rows = (count + columns - 1) // columns
    return blueprint(items, columns * 2 - 1, rows * 3 - 1)


def prison_blueprint() -> dict[str, Any]:
    """A legitimate enclosed two-bed prison; beds are marked for prisoners after construction."""
    items: list[dict[str, Any]] = []
    for x in range(7):
        if x != 3:
            items.append(building("Wall", x, 0, stuff="WoodLog"))
        items.append(building("Wall", x, 6, stuff="WoodLog"))
    for z in range(1, 6):
        items.append(building("Wall", 0, z, stuff="WoodLog"))
        items.append(building("Wall", 6, z, stuff="WoodLog"))
    items.extend([
        building("Door", 3, 0, stuff="WoodLog"),
        building("SleepingSpot", 2, 3),
        building("SleepingSpot", 4, 3),
        building("TorchLamp", 3, 5),
    ])
    return blueprint(items, 7, 7)


def hospital_blueprint() -> dict[str, Any]:
    """A small enclosed clinic; ordinary beds are later toggled medical by RIMAPI."""
    items: list[dict[str, Any]] = []
    for x in range(7):
        if x != 3:
            items.append(building("Wall", x, 0, stuff="WoodLog"))
        items.append(building("Wall", x, 6, stuff="WoodLog"))
    for z in range(1, 6):
        items.append(building("Wall", 0, z, stuff="WoodLog"))
        items.append(building("Wall", 6, z, stuff="WoodLog"))
    items.extend([
        building("Door", 3, 0, stuff="WoodLog"),
        building("Bed", 2, 3, stuff="WoodLog"),
        building("Bed", 4, 3, stuff="WoodLog"),
        building("TorchLamp", 3, 5),
    ])
    return blueprint(items, 7, 7)


def room_floor_blueprint(cells: list[dict[str, Any]], floor_def: str) -> tuple[dict[str, Any], dict[str, int]]:
    if not cells:
        raise ValueError("Room has no floorable cells")
    min_x = min(int(c.get("x") or 0) for c in cells)
    min_z = min(int(c.get("z") or 0) for c in cells)
    max_x = max(int(c.get("x") or 0) for c in cells)
    max_z = max(int(c.get("z") or 0) for c in cells)
    floors = [floor(floor_def, int(c.get("x") or 0) - min_x, int(c.get("z") or 0) - min_z) for c in cells]
    return blueprint([], max_x - min_x + 1, max_z - min_z + 1, floors), {"x": min_x, "z": min_z}


def pathway_blueprint(
    floor_def: str, anchor: dict[str, int], growing_anchor: dict[str, int]
) -> tuple[dict[str, Any], dict[str, int]]:
    """One-cell-wide outdoor route; broad paved plazas are an avoidable early-game expense."""
    min_x = min(int(growing_anchor["x"]), int(anchor["x"]) - 15)
    max_x = int(anchor["x"]) + 22
    min_z = int(anchor["z"])
    path_z = int(anchor["z"]) + 9
    absolute = {(x, path_z) for x in range(min_x, max_x + 1)}
    absolute |= {(int(anchor["x"]), z) for z in range(min_z, path_z + 1)}
    floors = [floor(floor_def, x - min_x, z - min_z) for x, z in sorted(absolute)]
    return blueprint([], max_x - min_x + 1, path_z - min_z + 1, floors), {"x": min_x, "z": min_z}


def affordable_floor_options(
    item_counts: dict[str, Any],
    finished: set[str],
    cell_count: int,
    best_builder: int,
    *,
    pathway: bool = False,
) -> dict[str, str]:
    """Return only materials that preserve a practical emergency reserve."""
    options: dict[str, str] = {}
    steel = int(item_counts.get("Steel") or 0)
    wood = int(item_counts.get("WoodLog") or 0)
    silver = int(item_counts.get("Silver") or 0)
    # Concrete is steel, despite looking like a cheap road. Outdoor paths use
    # renewable stone flagstone only; steel remains reserved for power, coolers,
    # weapons and the ship.
    if not pathway and "Stonecutting" in finished and steel >= cell_count + 100:
        options["Concrete"] = f"{cell_count} steel; fast, nonflammable, neutral cleanliness, ugly"
    for stone in ("Granite", "Limestone", "Sandstone", "Slate", "Marble"):
        blocks = int(item_counts.get(f"Blocks{stone}") or 0)
        if blocks >= cell_count * 4 + 80:
            def_name = f"Flagstone{stone}" if pathway else f"Tile{stone}"
            options[def_name] = f"{cell_count * 4} {stone.lower()} blocks; nonflammable, slower work"
    if not pathway and wood >= cell_count * 3 + 180:
        options["WoodPlankFloor"] = f"{cell_count * 3} wood; quick and cheap but flammable"
    if not pathway and "Smithing" in finished and best_builder >= 3 and steel >= cell_count * 7 + 150:
        options["MetalTile"] = f"{cell_count * 7} steel; +0.2 cleanliness and fast cleaning"
    if (
        not pathway and "SterileMaterials" in finished and best_builder >= 6
        and steel >= cell_count * 3 + 100 and silver >= cell_count * 12 + 300
    ):
        options["SterileTile"] = f"{cell_count * 3} steel + {cell_count * 12} silver; +0.6 cleanliness, very slow to build"
    return options


def structure_material_options(item_counts: dict[str, Any], *, minimum_units: int = 125) -> dict[str, str]:
    """Materials that can finish a small room while retaining a survival reserve."""
    options: dict[str, str] = {}
    wood = int(item_counts.get("WoodLog") or 0)
    if wood >= minimum_units + 80:
        options["WoodLog"] = f"{wood} available; fastest and renewable, but 100% flammable"
    stone_notes = {
        "Granite": "highest common stone wall durability and fireproof",
        "Limestone": "durable all-round stone and fireproof",
        "Sandstone": "fastest common stone to build and fireproof",
        "Slate": "lower durability but fireproof",
        "Marble": "+1 wall beauty and fireproof",
    }
    for stone, note in stone_notes.items():
        amount = int(item_counts.get(f"Blocks{stone}") or 0)
        if amount >= minimum_units + 50:
            options[f"Blocks{stone}"] = f"{amount} blocks available; {note}"
    steel = int(item_counts.get("Steel") or 0)
    if steel >= minimum_units + 300:
        options["Steel"] = f"{steel} available; fast and 300 HP, but steel structures remain 40% flammable"
    uranium = int(item_counts.get("Uranium") or 0)
    if uranium >= minimum_units + 250:
        options["Uranium"] = f"{uranium} available; 750 HP and nonflammable, but strategically scarce"
    plasteel = int(item_counts.get("Plasteel") or 0)
    if plasteel >= minimum_units + 300:
        options["Plasteel"] = f"{plasteel} available; 840 HP and nonflammable, but needed for advanced equipment and the ship"
    jade = int(item_counts.get("Jade") or 0)
    if jade >= minimum_units + 500:
        options["Jade"] = f"{jade} available; beautiful and fireproof but weak and valuable"
    silver = int(item_counts.get("Silver") or 0)
    if silver >= minimum_units + 3000:
        options["Silver"] = f"{silver} available; beautiful but weak, flammable and spendable"
    gold = int(item_counts.get("Gold") or 0)
    if gold >= minimum_units + 1500:
        options["Gold"] = f"{gold} available; extremely beautiful but weak and strategically valuable"
    return options


def private_bedroom_blueprint(
    wall_stuff: str,
    *,
    powered: bool = False,
    complex_furniture: bool = False,
    climate: str = "temperate",
) -> dict[str, Any]:
    """A 5x5 interior private bedroom; material changes apply only to this new room."""
    items: list[dict[str, Any]] = []
    for x in range(7):
        if x != 3:
            items.append(building("Wall", x, 0, stuff=wall_stuff))
        items.append(building("Wall", x, 6, stuff=wall_stuff))
    for z in range(1, 6):
        items.append(building("Wall", 0, z, stuff=wall_stuff))
        items.append(building("Wall", 6, z, stuff=wall_stuff))
    items.extend([
        building("Door", 3, 0, stuff=wall_stuff),
        building("Bed", 2, 3, stuff="WoodLog"),
        building("StandingLamp" if powered else "TorchLamp", 4, 4),
    ])
    if complex_furniture:
        items.extend([
            building("EndTable", 1, 3, stuff="WoodLog"),
            building("Dresser", 3, 5, stuff="WoodLog"),
        ])
    if powered and climate == "cold":
        items.append(building("Heater", 4, 2))
    elif climate == "hot":
        items.append(building("PassiveCooler", 4, 2))
    return blueprint(items, 7, 7)


def animal_barn_blueprint(
    wall_stuff: str,
    animal_count: int,
    *,
    straw_floor: bool,
    powered: bool,
    climate: str,
) -> dict[str, Any]:
    """Enclosed barn with an animal flap, beds and optional climate mitigation."""
    items: list[dict[str, Any]] = []
    for x in range(9):
        if x != 4:
            items.append(building("Wall", x, 0, stuff=wall_stuff))
        items.append(building("Wall", x, 6, stuff=wall_stuff))
    for z in range(1, 6):
        items.append(building("Wall", 0, z, stuff=wall_stuff))
        items.append(building("Wall", 8, z, stuff=wall_stuff))
    items.append(building("AnimalFlap", 4, 0, stuff=wall_stuff))
    for index in range(max(2, min(8, animal_count + 2))):
        items.append(building("AnimalSleepingSpot", 1 + index % 4 * 2, 2 + index // 4 * 2))
    if powered and climate == "cold":
        items.append(building("Heater", 7, 4))
    elif climate == "hot":
        items.append(building("PassiveCooler", 7, 4))
    floors = [floor("StrawMatting", x, z) for x in range(1, 8) for z in range(1, 6)] if straw_floor else []
    return blueprint(items, 9, 7, floors)


def weapon_shelves_blueprint(stuff: str) -> dict[str, Any]:
    return blueprint([
        building("Shelf", 0, 0, stuff=stuff),
        building("Shelf", 0, 2, stuff=stuff),
        building("Shelf", 0, 4, stuff=stuff),
    ], 2, 5)


def mining_bedroom_rect(ores: dict[str, Any], preferred_center: dict[str, int]) -> tuple[dict[str, int], dict[str, int]] | None:
    """Find a compact 7x7 fully mineable natural-rock block for a mountain bedroom."""
    width = int(ores.get("map_width") or 0)
    if width <= 0:
        return None
    natural: set[tuple[int, int]] = set()
    for name, group in (ores.get("ores") or {}).items():
        lowered = str(name).lower()
        if not lowered.startswith("mineable") or any(token in lowered for token in ("steel", "gold", "silver", "uranium", "component", "plasteel", "jade")):
            continue
        for value in group.get("cells") or []:
            cell = int(value)
            natural.add((cell % width, cell // width))
    if len(natural) < 49:
        return None
    candidates: list[tuple[int, int, int]] = []
    for x, z in natural:
        if all((x + dx, z + dz) in natural for dx in range(7) for dz in range(7)):
            distance = (x - int(preferred_center["x"])) ** 2 + (z - int(preferred_center["z"])) ** 2
            candidates.append((distance, x, z))
    if not candidates:
        return None
    _, x, z = min(candidates)
    return position(x, z), position(x + 6, z + 6)


def mineable_natural_rock_cells(ores: dict[str, Any]) -> set[tuple[int, int]]:
    width = int(ores.get("map_width") or 0)
    result: set[tuple[int, int]] = set()
    if width <= 0:
        return result
    for name, group in (ores.get("ores") or {}).items():
        lowered = str(name).lower()
        if not lowered.startswith("mineable") or any(token in lowered for token in ("steel", "gold", "silver", "uranium", "component", "plasteel", "jade")):
            continue
        for value in group.get("cells") or []:
            cell = int(value)
            result.add((cell % width, cell // width))
    return result


def mountain_bedroom_furnishing(*, powered: bool, climate: str) -> dict[str, Any]:
    items = [
        building("Door", 3, 0, stuff="WoodLog"),
        building("Bed", 2, 3, stuff="WoodLog"),
        building("StandingLamp" if powered else "TorchLamp", 4, 4),
    ]
    if powered and climate == "cold":
        items.append(building("Heater", 4, 2))
    elif climate == "hot":
        items.append(building("PassiveCooler", 4, 2))
    return blueprint(items, 7, 7)


def killbox_blueprint() -> dict[str, Any]:
    """An early-game open funnel: enemies retain a path while traps and cover shape it."""
    items: list[dict[str, Any]] = []
    for z in range(11):
        if z != 0:
            items.append(building("Wall", 0, z, stuff="WoodLog"))
            items.append(building("Wall", 8, z, stuff="WoodLog"))
    for x in range(1, 8):
        if x != 4:
            items.append(building("Wall", x, 0, stuff="WoodLog"))
    # A clear entrance at (4,0), staggered traps, and a protected firing line.
    for x, z in ((4, 2), (3, 4), (5, 6), (4, 8)):
        items.append(building("TrapSpike", x, z, stuff="WoodLog"))
    for x in range(2, 7):
        items.append(building("Barricade", x, 9, stuff="WoodLog"))
    return blueprint(items, 9, 11)


def fallback_defense_blueprint() -> dict[str, Any]:
    """A compact second line with a one-cell melee choke and ranged cover."""
    items = [
        building("Wall", 0, 0, stuff="WoodLog"),
        building("Wall", 1, 0, stuff="WoodLog"),
        building("Door", 2, 0, stuff="WoodLog"),
        building("Wall", 3, 0, stuff="WoodLog"),
        building("Wall", 4, 0, stuff="WoodLog"),
    ]
    for x in range(0, 5):
        items.append(building("Barricade", x, 3, stuff="WoodLog"))
    return blueprint(items, 5, 4)


def turret_defense_blueprint() -> dict[str, Any]:
    items = [
        building("TurretGun", 0, 0),
        building("TurretGun", 6, 0),
        building("Barricade", 2, 2, stuff="Steel"),
        building("Barricade", 3, 2, stuff="Steel"),
        building("Barricade", 4, 2, stuff="Steel"),
    ]
    for x in range(0, 7):
        items.append(building("PowerConduit", x, 1))
    return blueprint(items, 7, 3)


def mortar_post_blueprint() -> dict[str, Any]:
    items = [building("Mortar", 2, 2)]
    for x in range(5):
        items.append(building("Wall", x, 0, stuff="Steel"))
        items.append(building("Wall", x, 4, stuff="Steel"))
    for z in range(1, 4):
        items.append(building("Wall", 0, z, stuff="Steel"))
        if z != 2:
            items.append(building("Wall", 4, z, stuff="Steel"))
    items.append(building("Door", 4, 2, stuff="Steel"))
    return blueprint(items, 5, 5)


def orbital_trade_blueprint() -> dict[str, Any]:
    return blueprint([
        building("CommsConsole", 0, 0, rotation=2),
        building("OrbitalTradeBeacon", 5, 1),
    ], 8, 4)


def workshop_blueprint(def_name: str, *, stuff: str | None = None) -> dict[str, Any]:
    return blueprint([building(def_name, 0, 0, stuff=stuff, rotation=2)], 4, 3)


def sleeping_spots_blueprint(colonist_count: int) -> dict[str, Any]:
    count = max(3, min(colonist_count + 1, 8))
    return blueprint(
        [building("SleepingSpot", index * 2, 0) for index in range(count)],
        max(1, count * 2 - 1),
        1,
    )


def basic_beds_blueprint(colonist_count: int, stuff: str = "WoodLog") -> dict[str, Any]:
    count = max(1, min(int(colonist_count), 8))
    return blueprint(
        [building("Bed", (index % 4) * 2, (index // 4) * 3, stuff=stuff) for index in range(count)],
        max(1, min(4, count) * 2 - 1),
        max(2, ((count - 1) // 4) * 3 + 2),
    )


def freezer_blueprint(*, include_generator: bool = True, wall_stuff: str = "WoodLog") -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for x in range(6):
        items.append(building("Wall", x, 0, stuff=wall_stuff))
        items.append(building("Wall", x, 5, stuff=wall_stuff))
    for z in range(1, 5):
        items.append(building("Wall", 0, z, stuff=wall_stuff))
        if z != 2:
            items.append(building("Wall", 5, z, stuff=wall_stuff))
    items.append(building("Door", 3, 5, stuff=wall_stuff))
    items.append(building("Cooler", 5, 2, rotation=1))
    if include_generator:
        items.append(building("WoodFiredGenerator", 8, 1))
    for x in range(5, 9 if include_generator else 7):
        items.append(building("PowerConduit", x, 3))
    return blueprint(items, 11 if include_generator else 7, 6)


def freezer_resource_plan(
    building_counts: dict[str, Any], item_counts: dict[str, Any], best_builder: int, finished: set[str]
) -> dict[str, Any] | None:
    if "Electricity" not in finished or int(building_counts.get("Cooler", 0)) > 0 or best_builder < 3:
        return None
    power_defs = {"WoodFiredGenerator", "SolarGenerator", "WindTurbine", "WatermillGenerator", "GeothermalGenerator"}
    has_generator = any(int(building_counts.get(name, 0)) > 0 for name in power_defs)
    required = {
        "components": 3 + (0 if has_generator else 2),
        "steel": 90 + (0 if has_generator else 100),
        "wood": 150,
    }
    if (
        int(item_counts.get("ComponentIndustrial") or 0) < required["components"]
        or int(item_counts.get("Steel") or 0) < required["steel"]
        or int(item_counts.get("WoodLog") or 0) < required["wood"]
    ):
        return None
    return {"include_generator": not has_generator, "requirements": required}


def temple_blueprint(altar_def: str, wall_stuff: str) -> dict[str, Any]:
    """A floored 7x7-interior ritual room; no beds or work facilities."""
    items: list[dict[str, Any]] = []
    for x in range(9):
        if x != 4:
            items.append(building("Wall", x, 0, stuff=wall_stuff))
        items.append(building("Wall", x, 8, stuff=wall_stuff))
    for z in range(1, 8):
        items.append(building("Wall", 0, z, stuff=wall_stuff))
        items.append(building("Wall", 8, z, stuff=wall_stuff))
    items.extend([
        building("Door", 4, 0, stuff=wall_stuff),
        building(altar_def, 4, 5, stuff=wall_stuff, rotation=2),
        building("Column", 1, 1, stuff=wall_stuff),
        building("Column", 7, 1, stuff=wall_stuff),
        building("Column", 1, 7, stuff=wall_stuff),
        building("Column", 7, 7, stuff=wall_stuff),
        building("TorchLamp", 4, 2),
    ])
    floor_def = "WoodPlankFloor" if wall_stuff == "WoodLog" else (
        f"Tile{wall_stuff.removeprefix('Blocks')}" if wall_stuff.startswith("Blocks") else "Concrete"
    )
    floors = [floor(floor_def, x, z) for x in range(1, 8) for z in range(1, 8)]
    return blueprint(items, 9, 9, floors)


def power_blueprint() -> dict[str, Any]:
    items = [
        building("WoodFiredGenerator", 0, 0),
        building("Battery", 4, 0),
        building("StandingLamp", 7, 0),
    ]
    for x in range(2, 8):
        items.append(building("PowerConduit", x, 1))
    return blueprint(items, 9, 3)


def hitech_blueprint() -> dict[str, Any]:
    return blueprint(
        [
            building("HiTechResearchBench", 0, 0, rotation=2),
            building("MultiAnalyzer", 5, 1),
        ],
        8,
        4,
    )


def fabrication_blueprint() -> dict[str, Any]:
    return blueprint([building("FabricationBench", 0, 0, rotation=2)], 4, 3)


def ship_blueprint(colonist_count: int) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for x in range(2, 22, 2):
        items.append(building("Ship_Beam", x, 8))
    items.extend(
        [
            building("Ship_Reactor", 8, 5),
            building("Ship_ComputerCore", 12, 5),
            building("Ship_SensorCluster", 16, 5),
            building("Ship_Engine", 2, 5, rotation=3),
        ]
    )
    for index in range(max(3, min(colonist_count, 8))):
        items.append(building("Ship_CryptosleepCasket", 4 + index * 2, 9, rotation=0))
    return blueprint(items, 24, 14)


def anchor_from_snapshot(snapshot: dict[str, Any]) -> dict[str, int]:
    pawns = snapshot.get("colonists") or []
    xs = [int((p.get("position") or {}).get("x", 125)) for p in pawns]
    zs = [int((p.get("position") or {}).get("z", 125)) for p in pawns]
    center_x = round(sum(xs) / len(xs)) if xs else 125
    center_z = round(sum(zs) / len(zs)) if zs else 125
    return {"x": max(12, min(220, center_x + 12)), "z": max(12, min(220, center_z + 12))}


def decode_terrain(data: dict[str, Any]) -> tuple[int, int, list[str]]:
    width = int(data.get("width") or 0)
    height = int(data.get("height") or 0)
    palette = list(map(str, data.get("palette") or []))
    encoded = data.get("grid") or []
    cells: list[str] = []
    for index in range(0, len(encoded), 2):
        run = int(encoded[index])
        palette_index = int(encoded[index + 1])
        name = palette[palette_index] if 0 <= palette_index < len(palette) else "Unknown"
        cells.extend([name] * run)
    if width <= 0 or height <= 0 or len(cells) != width * height:
        raise ValueError("Invalid terrain grid returned by RIMAPI")
    return width, height, cells


def find_terrain_rect(
    terrain: dict[str, Any],
    center: dict[str, int],
    rect_width: int,
    rect_height: int,
    allowed: set[str],
    radius: int = 70,
) -> dict[str, int] | None:
    width, height, cells = decode_terrain(terrain)
    margin_x = 5 if width > rect_width + 10 else 0
    margin_z = 5 if height > rect_height + 10 else 0
    min_x = max(margin_x, center["x"] - radius)
    max_x = min(width - rect_width - margin_x, center["x"] + radius)
    min_z = max(margin_z, center["z"] - radius)
    max_z = min(height - rect_height - margin_z, center["z"] + radius)
    candidates: list[tuple[int, int, int]] = []
    for z in range(min_z, max_z + 1):
        for x in range(min_x, max_x + 1):
            valid = True
            for dz in range(rect_height):
                row = (z + dz) * width
                if any(cells[row + x + dx] not in allowed for dx in range(rect_width)):
                    valid = False
                    break
            if valid:
                distance = (x - center["x"]) ** 2 + (z - center["z"]) ** 2
                candidates.append((distance, x, z))
    if not candidates:
        return None
    _, x, z = min(candidates)
    return {"x": x, "z": z}


def collect_development(client: bridge.RimApiClient, snapshot: dict[str, Any]) -> dict[str, Any]:
    warnings = snapshot.setdefault("warnings", [])
    map_id = snapshot["map"]["id"]
    buildings = bridge.safe_get(client, "/api/v1/map/buildings", warnings, map_id=map_id) or []
    rooms_raw = bridge.safe_get(client, "/api/v1/map/rooms", warnings, map_id=map_id) or {}
    zones_raw = bridge.safe_get(client, "/api/v1/map/zones", warnings, map_id=map_id) or {}
    finished_raw = bridge.safe_get(client, "/api/v1/research/finished", warnings) or {}
    current = bridge.safe_get(client, "/api/v1/research/progress", warnings) or {}
    research_tree_raw = bridge.safe_get(client, "/api/v1/research/tree", warnings) or {}
    work_tables = bridge.safe_get(client, "/api/v1/map/work-tables", warnings, map_id=map_id) or []
    forbidden = bridge.safe_get(client, "/api/v1/things/forbidden", warnings, map_id=map_id) or []
    things = bridge.safe_get(client, "/api/v1/map/things", warnings, map_id=map_id) or []
    plants = bridge.safe_get(client, "/api/v1/map/plants", warnings, map_id=map_id) or []
    settlements = bridge.safe_get(client, "/api/v1/world/settlements", warnings) or []
    trade_destinations = bridge.safe_get(client, "/api/v1/world/trade/destinations", warnings, map_id=map_id) or []
    raid_destinations = bridge.safe_get(client, "/api/v1/world/raid/destinations", warnings, map_id=map_id) or []
    caravans = bridge.safe_get(client, "/api/v1/world/caravans", warnings) or []
    quests = bridge.safe_get(client, "/api/v1/quests", warnings, map_id=map_id) or []
    ores = bridge.safe_get(client, "/api/v1/map/ore", warnings, map_id=map_id) or {}
    storage = bridge.safe_get(client, "/api/v1/resources/storages/summary", warnings, map_id=map_id) or {}
    weather = bridge.safe_get(client, "/api/v1/map/weather", warnings, map_id=map_id) or {}
    farm = bridge.safe_get(client, "/api/v1/map/farm/summary", warnings, map_id=map_id) or {}
    projects_raw = bridge.safe_get(client, "/api/v1/builder/projects", warnings, map_id=map_id) or {}
    ideology = bridge.safe_get(client, "/api/v1/colony/ideology", warnings) or {}
    work_types = bridge.safe_get(client, "/api/v1/work-list/details", warnings) or []
    building_catalog = bridge.safe_get(client, "/api/v1/buildings/catalog", warnings) or []
    royalty = bridge.safe_get(client, "/api/v1/colony/royalty", warnings) or {}
    active_mods = bridge.safe_get(client, "/api/v1/mods/list", warnings) or []
    tile_id = snapshot.get("map", {}).get("tile_id")
    tile_details = bridge.safe_get(client, "/api/v1/world/tile/details", warnings, id=int(tile_id)) if tile_id is not None else {}
    zones = zones_raw.get("zones", []) if isinstance(zones_raw, dict) else []
    rooms = rooms_raw.get("rooms", []) if isinstance(rooms_raw, dict) else []
    finished = finished_raw.get("finished_projects", []) if isinstance(finished_raw, dict) else []
    corpses = [
        row for row in things if isinstance(row, dict)
        and any(str(category) in {"CorpsesHumanlike", "CorpsesAnimal"} for category in row.get("categories") or [])
    ]
    item_counts = Counter()
    trade_value = 0.0
    for row in things:
        if not isinstance(row, dict) or row.get("is_forbidden"):
            continue
        amount = max(1, int(row.get("stack_count") or 1))
        item_counts[str(row.get("def_name") or "")] += amount
        trade_value += float(row.get("market_value") or 0.0) * amount
    snapshot["development"] = {
        "building_counts": dict(Counter(str(row.get("def")) for row in buildings if isinstance(row, dict))),
        "buildings": buildings,
        "rooms": rooms,
        "zones": zones,
        "finished_research": finished,
        "current_research": current,
        "research_tree": research_tree_raw.get("projects", []) if isinstance(research_tree_raw, dict) else [],
        "work_tables": work_tables,
        "forbidden": forbidden,
        "things": things,
        "plants": plants,
        "corpses": corpses,
        "item_counts": dict(item_counts),
        "trade_value": round(trade_value, 1),
        "settlements": settlements,
        "trade_destinations": trade_destinations,
        "raid_destinations": raid_destinations,
        "caravans": caravans,
        "quests": quests,
        "ores": ores,
        "storage": storage,
        "weather": weather or {},
        "farm": farm or {},
        "tile_details": tile_details or {},
        "construction_projects": projects_raw.get("projects", []) if isinstance(projects_raw, dict) else [],
        "ideology": ideology if isinstance(ideology, dict) else {},
        "work_types": work_types if isinstance(work_types, list) else [],
        "building_catalog": building_catalog if isinstance(building_catalog, list) else [],
        "building_catalog_summary": architect.summarize_catalog(building_catalog if isinstance(building_catalog, list) else []),
        "royalty": royalty if isinstance(royalty, dict) else {},
        "active_mods": active_mods if isinstance(active_mods, list) else [],
    }
    snapshot["development"]["profession_context"] = professions.profession_context(
        snapshot.get("colonists", []), snapshot["development"]["work_types"]
    )
    return snapshot


def issued_recently(map_state: dict[str, Any], name: str, tick: int, retry_ticks: int = 60000) -> bool:
    issued = map_state.setdefault("issued", {})
    value = issued.get(name)
    if value is None:
        return False
    try:
        age = tick - int(value)
    except (TypeError, ValueError):
        issued.pop(name, None)
        return False
    if age < 0:
        # Loading an older save must not leave orders from the abandoned future
        # permanently suppressing food, construction, hauling or medical work.
        issued.pop(name, None)
        return False
    return age < retry_ticks


def reconcile_issued_timeline(map_state: dict[str, Any], tick: int) -> list[str]:
    """Discard future issue markers after a save rollback and report what changed."""
    issued = map_state.setdefault("issued", {})
    removed: list[str] = []
    for name, value in list(issued.items()):
        try:
            invalid = int(value) > tick
        except (TypeError, ValueError):
            invalid = True
        if invalid:
            removed.append(str(name))
            issued.pop(name, None)
    return removed


def relevant_forbidden(snapshot: dict[str, Any], radius: int = 40) -> list[dict[str, Any]]:
    pawn_positions = [
        (int((pawn.get("position") or {}).get("x", -1000)), int((pawn.get("position") or {}).get("z", -1000)))
        for pawn in snapshot.get("colonists", [])
    ]
    radius_squared = radius * radius
    result = []
    for thing in snapshot.get("development", {}).get("forbidden", []):
        categories = {str(value) for value in thing.get("categories") or []}
        if categories & {"CorpsesHumanlike", "CorpsesAnimal", "CorpsesMechanoid"}:
            continue
        pos = thing.get("position") or {}
        x = int(pos.get("x", -1000))
        z = int(pos.get("z", -1000))
        if any((x - px) ** 2 + (z - pz) ** 2 <= radius_squared for px, pz in pawn_positions):
            result.append(thing)
    return result


def corpse_rows(snapshot: dict[str, Any], category: str | None = None) -> list[dict[str, Any]]:
    rows = snapshot.get("development", {}).get("corpses", [])
    if category is None:
        return list(rows)
    return [row for row in rows if category in (row.get("categories") or [])]


def forbidden_corpses(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in corpse_rows(snapshot) if row.get("is_forbidden")]


def animal_needs_tending(animal: dict[str, Any]) -> bool:
    """True only when the game reports a treatable injury or active bleeding."""
    return bool(animal.get("tendable_now")) or float(animal.get("bleeding_rate") or 0.0) > 0.0


def animal_needs_assisted_feeding(animal: dict[str, Any]) -> bool:
    """Only patients that cannot walk to food should receive a forced feed job."""
    current_job = str(animal.get("current_job") or "").lower()
    is_patient = bool(animal.get("downed")) or any(
        marker in current_job for marker in ("laydown", "patient", "bedrest")
    )
    return is_patient and bridge.first_number(animal.get("hunger"), 1.0) < 0.35


def colonist_needs_assisted_feeding(colonist: dict[str, Any]) -> bool:
    """A conscious mobile colonist should reserve the normal self-feeding job."""
    return bool(colonist.get("downed") or colonist.get("is_downed")) and bridge.first_number(colonist.get("hunger"), 1.0) < 0.35


def action_backoff_remaining(map_state: dict[str, Any], choice: str, now: float | None = None) -> float:
    """Return the real-time cooldown left for an action that recently failed."""
    failure = (map_state.get("action_failures") or {}).get(choice) or {}
    return max(0.0, float(failure.get("retry_after") or 0.0) - (time.time() if now is None else now))


def register_action_failure(
    map_state: dict[str, Any],
    choice: str,
    error: Exception | str,
    now: float | None = None,
) -> dict[str, Any]:
    """Persist bounded exponential backoff so one rejected order cannot become a loop."""
    current_time = time.time() if now is None else now
    failures = map_state.setdefault("action_failures", {})
    previous = failures.get(choice) or {}
    count = min(8, int(previous.get("count") or 0) + 1)
    cooldown = min(300.0, 30.0 * (2 ** (count - 1)))
    failure = {
        "count": count,
        "error": str(error)[:500],
        "failed_at": current_time,
        "retry_after": current_time + cooldown,
    }
    failures[choice] = failure
    return failure


def clear_action_failure(map_state: dict[str, Any], choice: str) -> None:
    failures = map_state.get("action_failures")
    if isinstance(failures, dict):
        failures.pop(choice, None)


def filter_backed_off_choices(
    map_state: dict[str, Any],
    choices: list[str] | dict[str, Any],
    *,
    prefix: str = "",
) -> tuple[list[str], dict[str, float]]:
    """Remove temporarily failing choices while preserving their remaining delay."""
    names = list(choices)
    blocked = {
        name: action_backoff_remaining(map_state, f"{prefix}{name}")
        for name in names
        if action_backoff_remaining(map_state, f"{prefix}{name}") > 0.0
    }
    return [name for name in names if name not in blocked], blocked


def available_sale_categories(snapshot: dict[str, Any]) -> list[str]:
    found: set[str] = set()
    for row in snapshot.get("development", {}).get("things", []):
        if row.get("is_forbidden"):
            continue
        name = str(row.get("def_name") or "")
        categories = " ".join(map(str, row.get("categories") or []))
        if name in {"Flake", "Yayo", "SmokeleafJoint"}: found.add("drugs")
        if "Apparel" in categories: found.add("apparel")
        if "Sculpture" in name: found.add("art")
        if any(token in name for token in ("Wool", "Leather", "Milk")): found.add("animal_products")
        if name == "Chemfuel": found.add("chemfuel")
        if name in {"Gold", "Jade"}: found.add("precious")
        if name == "Beer": found.add("beer")
        if name in {"MealSurvivalPack", "Pemmican"}: found.add("travel_food")
        if name in {"RawCorn", "RawRice", "RawPotatoes", "AgaveFruit", "Berries"}: found.add("raw_food")
    plans = snapshot.get("development", {}).get("prisoner_plans") or {}
    prisoner_ids = {str(p.get("id")) for p in snapshot.get("combat", {}).get("prisoners", [])}
    if any(policy == "sell" and str(pawn_id) in prisoner_ids for pawn_id, policy in plans.items()):
        found.add("prisoners")
    return sorted(found)


def action_description(name: str, snapshot: dict[str, Any]) -> str:
    if name.startswith("prisoner_policy:"):
        _, pawn_id, policy = name.split(":", 2)
        pawn = next((p for p in snapshot.get("combat", {}).get("prisoners", []) if str(p.get("id")) == pawn_id), {})
        skills = ", ".join(map(str, pawn.get("top_skills") or [])) or "skills unknown"
        if policy == "recruit":
            return f"Recruit prisoner {pawn.get('name', pawn_id)}: {skills}; traits {pawn.get('traits') or []}; requires warden time and food."
        if policy == "release":
            return f"Release healed prisoner {pawn.get('name', pawn_id)} for goodwill when their faction permits it; current goodwill {pawn.get('faction_goodwill', 0)}."
        if policy == "organs_nonlethal":
            return (f"Schedule removal of one kidney and one lung from prisoner {pawn.get('name', pawn_id)} without intentionally killing them. "
                    f"Value {pawn.get('market_value', 0):.0f}; account for surgery failure, medicine, doctor skill, mood and ideology.")
        if policy == "organs_lethal":
            return (f"Schedule lethal heart removal from prisoner {pawn.get('name', pawn_id)}. This is irreversible and may cause severe mood, ideology and diplomatic costs; "
                    f"use only if the medical and social context clearly justifies it.")
        return f"Hold prisoner {pawn.get('name', pawn_id)} for sale; value {pawn.get('market_value', 0):.0f}, requiring food, guarding and a suitable trader."
    if name.startswith("human_reproduction:"):
        _, first_id, second_id, approach = name.split(":", 3)
        by_id = {str(c.get("id")): c.get("name") for c in snapshot.get("colonists", [])}
        return f"Set {by_id.get(first_id, first_id)} and {by_id.get(second_id, second_id)} to {approach}; TryForBaby also requires a shared double bed and strong reserves."
    if name.startswith("breed_animals:"):
        species = name.split(":", 1)[1]
        return f"Encourage natural breeding of the available healthy adult male/female {species} pair while preserving feed reserves."
    if name.startswith("trade_to:"):
        _, destination_id, sale = name.split(":", 2)
        row = next((d for d in snapshot["development"].get("trade_destinations", []) if str(d.get("settlement_id")) == destination_id), {})
        stock = row.get("known_stock") or []
        knowledge = f" known stock: {', '.join(str(x.get('label')) for x in stock[:8])}" if stock else " stock unknown until visited"
        prisoner_note = " buys prisoners" if row.get("will_buy_humanlike_prisoners") else " does not buy prisoners"
        return (f"Send a normal guarded caravan to {row.get('name', destination_id)} ({row.get('faction_name', '?')}, "
                f"{row.get('relation', '?')} goodwill {row.get('goodwill', 0)}, distance {row.get('approximate_distance_tiles', '?')} tiles) "
                f"selling {sale};{prisoner_note}.{knowledge}")
    if name.startswith("raid_to:"):
        destination_id = name.split(":", 1)[1]
        row = next((d for d in snapshot["development"].get("raid_destinations", []) if str(d.get("settlement_id")) == destination_id), {})
        return (f"Raid {row.get('name', destination_id)} of {row.get('faction_name', '?')}: estimated defenders "
                f"{row.get('estimated_defenders_min', '?')}-{row.get('estimated_defenders_max', '?')}, tech {row.get('tech_level', '?')}, "
                f"weapons {row.get('likely_weapon_tags', [])}, armor {row.get('likely_apparel_tags', [])}, "
                f"possible loot {row.get('possible_loot', [])}, starts war={row.get('would_start_war', False)}.")
    return ACTION_DESCRIPTIONS[name]


def action_label(name: str, snapshot: dict[str, Any]) -> str:
    if name.startswith("prisoner_policy:"):
        _, pawn_id, policy = name.split(":", 2)
        pawn = next((p for p in snapshot.get("combat", {}).get("prisoners", []) if str(p.get("id")) == pawn_id), {})
        labels = {
            "recruit": "вербовать", "release": "освободить", "sell": "продать",
            "organs_nonlethal": "почка и лёгкое", "organs_lethal": "летальное изъятие органа",
        }
        return f"пленный {pawn.get('name', pawn_id)}: {labels.get(policy, policy)}"
    if name.startswith("human_reproduction:"):
        return f"размножение колонистов: {name.rsplit(':', 1)[1]}"
    if name.startswith("breed_animals:"):
        return f"разведение: {name.split(':', 1)[1]}"
    if name.startswith("trade_to:"):
        _, destination_id, sale = name.split(":", 2)
        row = next((d for d in snapshot["development"].get("trade_destinations", []) if str(d.get("settlement_id")) == destination_id), {})
        return f"торговля: {row.get('name', destination_id)} / {sale}"
    if name.startswith("raid_to:"):
        destination_id = name.split(":", 1)[1]
        row = next((d for d in snapshot["development"].get("raid_destinations", []) if str(d.get("settlement_id")) == destination_id), {})
        return f"набег: {row.get('name', destination_id)}"
    return ACTION_LABELS.get(name, name)


def next_research(client: bridge.RimApiClient, finished: set[str], map_state: dict[str, Any] | None = None) -> str | None:
    income_strategy = str((map_state or {}).get("income_strategy") or "")
    doctrine = (map_state or {}).get("doctrine") or {}
    strategy_route = {
        "drugs": ["DrugProduction"],
        "tailoring": ["ComplexClothing", "Devilstrand"],
        "art": ["Stonecutting"],
        "livestock": ["ComplexFurniture"],
        "biofuel": ["BiofuelRefining"],
        "mining": ["Machining", "MicroelectronicsBasics", "LongRangeMineralScanner"],
        "crops": [],
        "brewing": ["Brewing"],
        "travel_food": ["Pemmican", "PackagedSurvivalMeal"],
        "orbital": ["MicroelectronicsBasics"],
    }.get(income_strategy, [])
    military_route = {
        "weapons": ["Smithing", "Machining", "Gunsmithing", "BlowbackOperation", "GasOperation"],
        "armor": ["Smithing", "PlateArmor", "Machining", "FlakArmor"],
        "fortifications": ["Machining", "GunTurrets", "Mortars", "Firefoam"],
        "balanced": ["Smithing", "Machining", "FlakArmor", "Gunsmithing", "GunTurrets"],
    }.get(str(doctrine.get("military") or "balanced"), [])
    route = ["Electricity", "Batteries", *military_route, *strategy_route, *RESEARCH_ROUTE[2:]]
    for name in dict.fromkeys(route):
        if name in finished:
            continue
        try:
            project = client.get("/api/v1/research/project", name=name)
        except bridge.RimApiError:
            continue
        if project.get("can_start_now"):
            return name
    return None


def candidate_actions(client: bridge.RimApiClient, snapshot: dict[str, Any], map_state: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    dev = snapshot["development"]
    counts = dev["building_counts"]
    zones = dev["zones"]
    tick = int(snapshot["game"].get("tick") or 0)
    finished = set(map(str, dev["finished_research"]))
    current = str((dev["current_research"] or {}).get("name") or "none")
    details: dict[str, Any] = {}
    one_time: list[str] = []
    item_counts = dev.get("item_counts", {})
    rolled_back_orders = reconcile_issued_timeline(map_state, tick)
    if rolled_back_orders:
        details["discarded_future_orders"] = rolled_back_orders

    if relevant_forbidden(snapshot) and not issued_recently(
        map_state, "unforbid_supplies", tick, retry_ticks=60000
    ):
        return ["unforbid_supplies"], details

    issued = map_state.setdefault("issued", {})
    resources = snapshot["map"]["resources"]
    lowest_food = min((float(c.get("hunger") or 0.0) for c in snapshot["colonists"]), default=1.0)
    hungry_colonist_patients = sorted(
        (colonist for colonist in snapshot["colonists"] if colonist_needs_assisted_feeding(colonist)),
        key=lambda colonist: bridge.first_number(colonist.get("hunger"), 1.0),
    )
    if int(resources.get("food") or 0) > 0 and hungry_colonist_patients:
        patient = hungry_colonist_patients[0]
        patient_id = int(patient["id"])
        if not issued_recently(
            map_state, f"colonist_feed:{patient_id}", tick,
            retry_ticks=PATIENT_FEED_RETRY_TICKS,
        ):
            details["hungry_colonist_id"] = patient_id
            details["hungry_colonist_name"] = str(patient.get("name") or patient_id)
            return ["feed_hungry_colonist"], details
    food_emergency = int(resources.get("food") or 0) <= 0 or lowest_food < 0.12
    if food_emergency:
        anchor = map_state.get("anchor") or {"x": 125, "z": 125}
        radius_squared = 180 ** 2
        wild_food_groups: dict[str, dict[str, Any]] = {}
        food_tokens = ("berry", "agave", "fruit", "ambrosia", "cocoa", "raw")
        for plant in dev.get("plants", []):
            harvested = str(plant.get("harvested_thing_def") or "")
            if not plant.get("harvestable_now") or not any(token in harvested.lower() for token in food_tokens):
                continue
            pos = plant.get("position") or {}
            if (int(pos.get("x") or 0) - int(anchor["x"])) ** 2 + (int(pos.get("z") or 0) - int(anchor["z"])) ** 2 > radius_squared:
                continue
            name = str(plant.get("def_name") or harvested)
            group = wild_food_groups.setdefault(name, {
                "label": str(plant.get("label") or name),
                "harvested_thing": harvested,
                "count": 0,
                "expected_yield": 0,
                "ids": [],
            })
            group["count"] += 1
            group["expected_yield"] += int(plant.get("harvest_yield") or 0)
            group["ids"].append(int(plant["thing_id"]))

        combat_rows = snapshot.get("combat", {}).get("colonists", [])
        healthy_armed = [
            row for row in combat_rows
            if row.get("has_ranged_weapon") and not row.get("is_downed") and float(row.get("health") or 0.0) >= 0.65
        ]
        emergency_hunt_options = []
        if healthy_armed:
            for animal in snapshot.get("wild_animals", []):
                pos = animal.get("position") or {}
                close = (int(pos.get("x") or 0) - int(anchor["x"])) ** 2 + (int(pos.get("z") or 0) - int(anchor["z"])) ** 2 <= radius_squared
                safe = (
                    close
                    and not animal.get("predator")
                    and "boom" not in str(animal.get("def") or "").lower()
                    and float(animal.get("harm_revenge_chance") or 0.0) <= 0.05
                    and float(animal.get("combat_power") or 0.0) <= 100
                    and not issued_recently(map_state, f"hunt:{animal.get('id')}", tick, retry_ticks=60000)
                )
                if safe:
                    emergency_hunt_options.append(animal)
        emergency_hunt_options.sort(
            key=lambda animal: (int(animal.get("meat_amount") or 0), -float(animal.get("combat_power") or 0.0)),
            reverse=True,
        )

        emergency_actions: list[str] = []
        if wild_food_groups and not issued_recently(map_state, "harvest", tick, retry_ticks=2500):
            details["wild_plant_options"] = wild_food_groups
            dev["wild_plant_options"] = wild_food_groups
            emergency_actions.append("harvest_local_plants")
        if emergency_hunt_options:
            details["hunt_options"] = emergency_hunt_options[:20]
            details["fighter_context"] = {
                "healthy_ranged": len(healthy_armed),
                "average_shooting": round(sum(int(row.get("shooting_skill") or 0) for row in healthy_armed) / len(healthy_armed), 1),
                "food_emergency": True,
            }
            dev["hunt_options"] = emergency_hunt_options[:20]
            dev["fighter_context"] = details["fighter_context"]
            emergency_actions.append("designate_safe_hunting")
        if wild_food_groups and not issued_recently(map_state, "priority:PlantCutting", tick, retry_ticks=15000):
            emergency_actions.append("prioritize_plant_cutting")
        if emergency_hunt_options and not issued_recently(map_state, "priority:Hunting", tick, retry_ticks=15000):
            emergency_actions.append("prioritize_hunting")
        if int(resources.get("raw_food") or 0) > 0 and not issued_recently(map_state, "priority:Cooking", tick, retry_ticks=15000):
            emergency_actions.append("prioritize_cooking")
        details["food_emergency_context"] = {
            "food": int(resources.get("food") or 0),
            "raw_food": int(resources.get("raw_food") or 0),
            "meals": int(resources.get("meals") or 0),
            "lowest_hunger": round(lowest_food, 3),
            "harvestable_food_types": list(wild_food_groups),
            "safe_hunt_targets": len(emergency_hunt_options),
        }
        dev["food_emergency_context"] = details["food_emergency_context"]
        if emergency_actions:
            return list(dict.fromkeys(emergency_actions)), details

    human_corpses = corpse_rows(snapshot, "CorpsesHumanlike")
    all_corpses = corpse_rows(snapshot)
    if forbidden_corpses(snapshot) and not issued_recently(map_state, "unforbid_corpses", tick, retry_ticks=15000):
        return ["unforbid_corpses"], details
    human_dump_exists = any("Laya Human Corpse Dump" in str(z.get("label") or "") for z in zones)
    animal_dump_exists = any("Laya Animal Carcasses" in str(z.get("label") or "") for z in zones)
    corpse_actions: list[str] = []
    if human_corpses and not human_dump_exists and "human_corpse_dump" not in issued:
        corpse_actions.append("create_human_corpse_dump")
    if human_corpses and counts.get("Grave", 0) < min(4, len(human_corpses)) and "cemetery" not in issued:
        details["grave_count"] = min(8, max(2, len(human_corpses)))
        corpse_actions.append("build_cemetery")
    stone_blocks = [name for name, amount in item_counts.items() if name.startswith("Blocks") and int(amount or 0) >= 170]
    if (
        human_corpses and counts.get("ElectricCrematorium", 0) == 0 and stone_blocks
        and int(item_counts.get("Steel") or 0) >= 70
        and int(item_counts.get("ComponentIndustrial") or 0) >= 4
        and max((int((c.get("skills", {}).get("Construction") or {}).get("level") or 0) for c in snapshot["colonists"]), default=0) >= 4
        and "crematorium" not in issued
    ):
        details["crematorium_stuff"] = stone_blocks[0]
        corpse_actions.append("build_crematorium")
    elif human_corpses and counts.get("ElectricCrematorium", 0) > 0 and not issued_recently(map_state, "crematorium_bill", tick, retry_ticks=60000):
        corpse_actions.append("build_crematorium")
    if any(corpse_rows(snapshot, "CorpsesAnimal")) and not animal_dump_exists and "animal_corpse_dump" not in issued:
        corpse_actions.append("create_animal_corpse_dump")
    if all_corpses and (human_dump_exists or animal_dump_exists or counts.get("Grave", 0) > 0) and not issued_recently(map_state, "priority:Burial", tick, retry_ticks=30000):
        corpse_actions.append("prioritize_burial")
    if corpse_actions:
        details["corpse_context"] = {
            "human": len(human_corpses),
            "animal": len(corpse_rows(snapshot, "CorpsesAnimal")),
            "colonists": len(snapshot["colonists"]),
            "human_dump_exists": human_dump_exists,
            "animal_dump_exists": animal_dump_exists,
            "graves": counts.get("Grave", 0),
            "crematorium": counts.get("ElectricCrematorium", 0),
        }
        dev["corpse_context"] = details["corpse_context"]
        return corpse_actions, details

    food_zone = any(
        "Stockpile" in str(z.get("type")) and "Laya Food" in str(z.get("label") or "")
        for z in zones
    )
    if not food_zone and "food_stockpile" not in map_state.setdefault("issued", {}):
        return ["create_food_stockpile"], details

    if counts.get("SleepingSpot", 0) < len(snapshot["colonists"]) and "sleeping_spots" not in map_state["issued"]:
        return ["build_sleeping_spots"], details

    best_builder = max(
        (int((c.get("skills", {}).get("Construction") or {}).get("level") or 0) for c in snapshot["colonists"]),
        default=0,
    )
    missing_beds = max(0, len(snapshot["colonists"]) - int(counts.get("Bed", 0)))
    if (
        missing_beds and best_builder >= 3
        and int(item_counts.get("WoodLog") or 0) >= missing_beds * 45 + 80
        and not issued_recently(map_state, "basic_beds", tick, retry_ticks=90000)
    ):
        details["basic_bed_count"] = missing_beds
        return ["build_basic_beds"], details

    colony_animals = [animal for animal in snapshot.get("animals", []) if not animal.get("dead")]
    # Low health after a wound has already been tended only needs rest. Reissuing
    # a tend job every cycle steals a doctor and cannot improve the animal.
    tendable_animals = sorted(
        (
            animal for animal in colony_animals
            if animal_needs_tending(animal)
        ),
        key=lambda animal: (
            bridge.first_number(animal.get("health"), 1.0),
            -bridge.first_number(animal.get("bleeding_rate"), 0.0),
        ),
    )
    hungry_animals = sorted(
        (animal for animal in colony_animals if animal_needs_assisted_feeding(animal)),
        key=lambda animal: bridge.first_number(animal.get("hunger"), 1.0),
    )
    animal_emergency: list[str] = []
    if colony_animals and counts.get("AnimalSleepingSpot", 0) < len(colony_animals) and "animal_spots" not in map_state["issued"]:
        animal_emergency.append("build_animal_spots")
    if tendable_animals:
        target = tendable_animals[0]
        details["injured_animal_id"] = int(target["id"])
        details["injured_animal_name"] = str(target["name"])
        if not issued_recently(map_state, f"animal_care:{target['id']}", tick, retry_ticks=2500):
            animal_emergency.append("care_for_injured_animal")
    if hungry_animals:
        hungry = hungry_animals[0]
        details["hungry_animal_id"] = int(hungry["id"])
        details["hungry_animal_name"] = str(hungry["name"])
        # A successful patient-feed order needs time to reserve food, walk to the
        # bed and complete ingestion. Reissuing it every few seconds interrupts
        # normal work and creates an apparent decision loop.
        if not issued_recently(
            map_state, f"animal_feed:{hungry['id']}", tick,
            retry_ticks=PATIENT_FEED_RETRY_TICKS,
        ):
            animal_emergency.insert(0, "feed_hungry_animal")
    if animal_emergency:
        return animal_emergency, details

    if not any("Growing" in str(z.get("type")) for z in zones) and "growing" not in map_state["issued"]:
        return ["create_growing_zone"], details

    finished_electricity = "Electricity" in finished
    freezer_plan = freezer_resource_plan(counts, item_counts, best_builder, finished)
    if freezer_plan and "freezer" not in map_state["issued"]:
        details["freezer_include_generator"] = freezer_plan["include_generator"]
        details["freezer_requirements"] = freezer_plan["requirements"]
        return ["build_freezer"], details

    if not any(
        "Stockpile" in str(z.get("type")) and "Laya Main" in str(z.get("label") or "")
        for z in zones
    ) and "stockpile" not in map_state["issued"]:
        one_time.append("create_stockpile")
    storage_utilization = int((dev.get("storage") or {}).get("utilization_percent") or 0)
    if storage_utilization >= 90 and not issued_recently(map_state, "expand_stockpile", tick, retry_ticks=120000):
        one_time.append("expand_stockpile")
    survival_stable = (
        int(resources.get("food") or 0) >= max(8, len(snapshot["colonists"]) * 3)
        and lowest_food >= 0.30
        and not any(c.get("downed") for c in snapshot["colonists"])
    )
    current_doctrine = map_state.get("doctrine") or {}
    profession_context = dev.get("profession_context") or professions.profession_context(
        snapshot.get("colonists", []), dev.get("work_types") or []
    )
    dev["profession_context"] = profession_context

    night_owls = professions.night_owl_options(snapshot.get("colonists", []))
    unscheduled_night_owls = {
        pawn_id: description for pawn_id, description in night_owls.items()
        if str(pawn_id) not in {str(value) for value in map_state.get("night_owl_schedules", [])}
    }
    if unscheduled_night_owls:
        details["night_owl_options"] = unscheduled_night_owls
        dev["night_owl_options"] = unscheduled_night_owls
        one_time.append("optimize_night_owl_schedule")

    training = professions.training_options(snapshot.get("colonists", []), dev.get("work_types") or [])
    if survival_stable and training and not issued_recently(map_state, "skill_development", tick, retry_ticks=180000):
        details["skill_training_options"] = training
        dev["skill_training_options"] = training
        one_time.append("develop_colonist_skill")
    if survival_stable and best_builder >= 4 and counts.get("SimpleResearchBench", 0) == 0 and "starter_base" not in map_state["issued"]:
        one_time.append("build_starter_base")
    tables = dev["work_tables"]
    if tables and not issued_recently(map_state, "food_bills", tick, retry_ticks=15000):
        one_time.append("configure_food_bills")
    if "Electricity" in finished and counts.get("WoodFiredGenerator", 0) == 0 and "power" not in map_state["issued"] and "freezer" not in map_state["issued"]:
        one_time.append("build_power")
    if "MicroelectronicsBasics" in finished and (counts.get("HiTechResearchBench", 0) == 0 or counts.get("MultiAnalyzer", 0) == 0) and "hitech" not in map_state["issued"]:
        one_time.append("build_hitech_lab")
    if "Fabrication" in finished and counts.get("FabricationBench", 0) == 0 and "fabrication" not in map_state["issued"]:
        one_time.append("build_fabrication")
    ship_ready = all(name in finished for name in RESEARCH_ROUTE[6:])
    chosen_endgame = str(current_doctrine.get("endgame") or "ship_escape")
    if ship_ready and chosen_endgame == "ship_escape" and counts.get("Ship_ComputerCore", 0) == 0 and "ship" not in map_state["issued"]:
        one_time.append("build_ship")
    if survival_stable and current.lower() == "none":
        doctrine_research = strategy.doctrine_research_candidates(
            current_doctrine, dev.get("research_tree") or []
        ) if current_doctrine else {}
        if doctrine_research:
            details["doctrine_research_options"] = doctrine_research
            dev["doctrine_research_options"] = doctrine_research
            one_time.append("advance_doctrine_research")
        else:
            target = next_research(client, finished, map_state)
            if target:
                one_time.append("advance_research")
                details["research_target"] = target
    anchor = map_state.get("anchor") or {"x": 125, "z": 125}
    weather = dev.get("weather") or {}
    outdoor_temperature = float(weather.get("temperature") or 0.0)
    climate_mode = "cold" if outdoor_temperature < 8 else "hot" if outdoor_temperature > 30 else "temperate"
    material_options = structure_material_options(item_counts)
    mountain_rect = mining_bedroom_rect(dev.get("ores") or {}, anchor)
    chosen_material = str(current_doctrine.get("material") or "")
    chosen_material_available = int(item_counts.get(chosen_material) or 0) if chosen_material else 0
    doctrine_due = (
        not current_doctrine
        or int(current_doctrine.get("schema_version") or 1) < 2
        or tick - int(map_state.get("doctrine_tick") or -999999) >= 3600000
    )
    doctrine_starved = bool(current_doctrine and chosen_material and chosen_material_available < 125 and material_options)
    if survival_stable and (doctrine_due or doctrine_starved):
        doctrine_context = {
            "current": current_doctrine,
            "material_options": material_options,
            "mountain_possible": mountain_rect is not None,
            "tile": dev.get("tile_details") or {},
            "weather": weather,
            "boom_animals_nearby": sum(1 for a in snapshot.get("wild_animals", []) if "boom" in str(a.get("def") or "").lower()),
            "ores": {name: len((group or {}).get("cells") or []) for name, group in (dev.get("ores", {}).get("ores") or {}).items()},
            "profession_directions": profession_context.get("directions") or {},
            "profession_choices": professions.direction_choice_descriptions(profession_context),
            "building_catalog": dev.get("building_catalog") or [],
            "research_tree": dev.get("research_tree") or [],
            "active_mods": dev.get("active_mods") or [],
            "ideology": dev.get("ideology") or {},
            "royalty": dev.get("royalty") or {},
        }
        doctrine_context["direction_audit"] = strategy.audit_directions(doctrine_context)
        details["doctrine_context"] = doctrine_context
        dev["doctrine_context"] = details["doctrine_context"]
        one_time.append("choose_colony_doctrine")

    doctrine_form = str(current_doctrine.get("settlement_form") or "")
    private_rooms = [
        room for room in dev.get("rooms", [])
        if "bedroom" in str(room.get("role_label") or "").lower() and not room.get("is_prison_cell")
    ]
    housing_shortage = len(private_rooms) < len(snapshot["colonists"])
    if survival_stable and current_doctrine and housing_shortage:
        if doctrine_form == "mountain" and mountain_rect is not None and not map_state.get("mountain_bedroom"):
            details["mountain_bedroom_rect"] = mountain_rect
            one_time.append("excavate_mountain_bedroom")
        elif doctrine_form == "mountain" and map_state.get("mountain_bedroom"):
            plan = map_state["mountain_bedroom"]
            natural = mineable_natural_rock_cells(dev.get("ores") or {})
            x, z = int(plan["x"]), int(plan["z"])
            interior = {(x + dx, z + dz) for dx in range(1, 6) for dz in range(1, 6)} | {(x + 3, z)}
            if not (interior & natural) and not plan.get("furnished"):
                one_time.append("finish_mountain_bedroom")
        # Surface settlements are handled by the procedural architecture
        # planner below. Mountain bedrooms retain their separate mining phase.

    upgrade_options = architect.workbench_upgrade_options(dev)
    if survival_stable and upgrade_options and not issued_recently(map_state, "workbench_upgrade", tick, retry_ticks=120000):
        details["workbench_upgrade_options"] = upgrade_options
        dev["workbench_upgrade_options"] = upgrade_options
        one_time.append("upgrade_workbench")

    dark_room_options: dict[str, dict[str, Any]] = {}
    for room in dev.get("rooms", []):
        if room.get("touches_map_edge") or not room.get("light_placement_cells"):
            continue
        role = str(room.get("role_label") or "room")
        defs = set(map(str, room.get("contained_thing_defs") or []))
        high_value = any(token in role.lower() for token in ("hospital", "kitchen", "workshop", "laboratory", "dining", "bedroom"))
        high_value = high_value or bool(defs & {"HospitalBed", "Bed", "FueledStove", "ElectricStove", "SimpleResearchBench", "HiTechResearchBench"})
        if high_value and float(room.get("dark_cells_percent") or 0.0) >= 40.0:
            dark_room_options[str(room.get("id"))] = {
                "room_id": int(room.get("id") or 0),
                "role": role,
                "average_glow": round(float(room.get("average_glow") or 0.0), 2),
                "dark_percent": round(float(room.get("dark_cells_percent") or 0.0), 1),
                "temperature": round(float(room.get("temperature") or 0.0), 1),
                "placement_cells": room.get("light_placement_cells") or [],
            }
    if survival_stable and dark_room_options and not issued_recently(map_state, "room_lighting", tick, retry_ticks=60000):
        details["dark_room_options"] = dark_room_options
        dev["dark_room_options"] = dark_room_options
        one_time.append("improve_room_lighting")

    architecture_material = chosen_material if chosen_material in material_options else next(iter(material_options), "")
    architecture_context = {
        "building_counts": counts,
        "buildings": dev.get("buildings") or [],
        "rooms": dev.get("rooms") or [],
        "colonists": snapshot.get("colonists") or [],
        "animals": colony_animals,
        "royalty": dev.get("royalty") or {},
        "ideology": dev.get("ideology") or {},
        "storage": dev.get("storage") or {},
        "professions": profession_context,
        "doctrine": current_doctrine,
        "finished_research": list(finished),
        "building_catalog": dev.get("building_catalog") or [],
        "item_counts": item_counts,
        "material": architecture_material,
        "powered": finished_electricity,
        "climate": climate_mode,
        "wealth": snapshot.get("game", {}).get("wealth") or 0,
        "animal_count": len(colony_animals),
        "potential_patients": [
            {
                "name": pawn.get("name"), "health": pawn.get("health"), "downed": pawn.get("downed"),
                "conditions": [condition.get("label") or condition.get("def_name") for condition in pawn.get("health_conditions", [])],
            }
            for pawn in snapshot.get("colonists", [])
            if pawn.get("downed") or bridge.first_number(pawn.get("health"), 1.0) < 0.9 or pawn.get("health_conditions")
        ],
        "variant_seed": int(snapshot.get("map", {}).get("id") or 0) * 1000003 + tick // 60000,
        "altar_defs": [str(row.get("def_name")) for row in (dev.get("ideology") or {}).get("ritual_buildings", []) if row.get("def_name")],
        "bench_defs": [str(row.get("def_name")) for row in dev.get("building_catalog", []) if row.get("is_work_table") and row.get("available_now")],
    }
    architecture_programs = architect.program_options(architecture_context) if architecture_material else {}
    pending_projects = dev.get("construction_projects") or []
    if (
        survival_stable and architecture_programs and not pending_projects
        and not issued_recently(map_state, "architecture_project", tick, retry_ticks=90000)
    ):
        details["architecture_context"] = architecture_context
        details["architecture_program_options"] = architecture_programs
        dev["architecture_context"] = architecture_context
        dev["architecture_program_options"] = architecture_programs
        one_time.append("plan_architecture")

    sculptures = [
        row for row in dev.get("things", [])
        if "sculpture" in str(row.get("inner_def_name") or row.get("def_name") or "").lower()
    ]
    valued_rooms = [
        room for room in dev.get("rooms", [])
        if not room.get("touches_map_edge") and room.get("cells")
        and any(token in str(room.get("role_label") or "").lower() for token in ("dining", "rec", "bedroom", "hospital", "workshop"))
        and float(room.get("impressiveness") or 0.0) < 120
    ]
    if survival_stable and sculptures and valued_rooms and not issued_recently(map_state, "install_sculpture", tick, retry_ticks=30000):
        install_options: dict[str, dict[str, Any]] = {}
        for sculpture in sculptures[:8]:
            for room in sorted(valued_rooms, key=lambda r: float(r.get("impressiveness") or 0.0))[:6]:
                key = f"{int(sculpture['thing_id'])}|{int(room['id'])}"
                install_options[key] = {
                    "thing_id": int(sculpture["thing_id"]),
                    "sculpture": sculpture.get("label"),
                    "beauty": sculpture.get("beauty", 0),
                    "quality": sculpture.get("inner_quality", -1),
                    "room_id": int(room["id"]),
                    "room_role": room.get("role_label"),
                    "impressiveness": round(float(room.get("impressiveness") or 0.0), 1),
                    "cells": room.get("cells") or [],
                }
        if install_options:
            details["sculpture_install_options"] = install_options
            dev["sculpture_install_options"] = install_options
            one_time.append("install_sculpture")
    elif survival_stable and not sculptures and not issued_recently(map_state, "commission_sculptures", tick, retry_ticks=120000):
        best_artist = max((int((c.get("skills", {}).get("Artistic") or {}).get("level") or 0) for c in snapshot["colonists"]), default=0)
        if best_artist >= 3 and (int(item_counts.get("WoodLog") or 0) >= 200 or any(name.startswith("Blocks") and int(value or 0) >= 100 for name, value in item_counts.items())):
            one_time.append("commission_sculptures")

    shelf_area = {
        "min_x": int(anchor["x"]) - 8, "max_x": int(anchor["x"]) - 7,
        "min_z": int(anchor["z"]) + 9, "max_z": int(anchor["z"]) + 13,
    }
    weapon_shelves = [
        b for b in dev.get("buildings", []) if str(b.get("def")) in {"Shelf", "ShelfSmall"}
        and shelf_area["min_x"] <= int((b.get("position") or {}).get("x") or -999) <= shelf_area["max_x"]
        and shelf_area["min_z"] <= int((b.get("position") or {}).get("z") or -999) <= shelf_area["max_z"]
    ]
    if survival_stable and int(snapshot["map"]["resources"].get("weapons") or 0) > 0 and "ComplexFurniture" in finished:
        if len(weapon_shelves) < 3 and not issued_recently(map_state, "weapon_shelves", tick, retry_ticks=90000):
            one_time.append("build_weapon_shelves")
        elif weapon_shelves and not map_state.get("weapon_shelves_configured"):
            details["weapon_shelf_ids"] = [int(b["id"]) for b in weapon_shelves]
            one_time.append("build_weapon_shelves")

    military_focus = str(current_doctrine.get("military") or "balanced")
    armament_focus = {
        "ranged_firepower": "weapons", "turret_mortar": "weapons",
        "melee_chokepoints": "armor", "fortified_depth": "balanced",
        "mobile_response": "balanced", "peaceful_deterrence": "balanced",
        "psychic_force": "balanced", "mechanized_force": "balanced",
        "anomaly_weapons": "weapons", "gravship_security": "balanced",
    }.get(military_focus, military_focus)
    if survival_stable and current_doctrine and not issued_recently(map_state, "armament", tick, retry_ticks=60000):
        underarmed = sum(1 for p in snapshot.get("combat", {}).get("colonists", []) if not p.get("has_ranged_weapon"))
        if underarmed or armament_focus in {"weapons", "armor", "balanced"}:
            details["armament_context"] = {
                "focus": armament_focus,
                "doctrine": military_focus,
                "unarmed_colonists": underarmed,
                "loose_weapons": snapshot.get("combat", {}).get("available_weapons", [])[:12],
                "steel": item_counts.get("Steel", 0),
                "components": item_counts.get("ComponentIndustrial", 0),
            }
            one_time.append("prioritize_armament")

    if colony_animals and current_doctrine and "animal_barn" not in map_state.setdefault("issued", {}) and material_options:
        min_comfort = min((float(a.get("min_comfortable_temperature") or -10) for a in colony_animals), default=-10)
        max_comfort = max((float(a.get("max_comfortable_temperature") or 40) for a in colony_animals), default=40)
        climate_risk = outdoor_temperature < min_comfort + 5 or outdoor_temperature > max_comfort - 5
        hay = int(item_counts.get("Hay") or item_counts.get("HayGrass") or 0)
        details["animal_barn_options"] = {
            "material_options": material_options,
            "straw_available": hay >= 100,
            "hay": hay,
            "climate_risk": climate_risk,
            "climate": climate_mode,
            "animal_count": len(colony_animals),
            "comfort_range": [min_comfort, max_comfort],
        }
        dev["animal_barn_options"] = details["animal_barn_options"]
        if climate_risk or len(colony_animals) >= 2:
            one_time.append("build_animal_barn")

    growing_zones = [z for z in zones if "Growing" in str(z.get("type"))]
    crop_days = [float(c.get("days_until_harvest") or 0.0) for c in (dev.get("farm") or {}).get("crop_types", []) if int(c.get("total_plants") or 0) > 0]
    future_temperatures = [float(v) for v in weather.get("next_twelfth_average_temperatures") or []]
    late_season = (not bool(weather.get("growth_season_now"))) or (future_temperatures and min(future_temperatures) < 6 and max(crop_days or [0]) > 5)
    if growing_zones and late_season and any(z.get("allow_sow") is not False for z in growing_zones):
        details["sowing_zone_ids"] = [int(z["id"]) for z in growing_zones if z.get("allow_sow") is not False]
        one_time.append("pause_late_sowing")
    elif growing_zones and bool(weather.get("growth_season_now")) and (not future_temperatures or min(future_temperatures[:2]) >= 6) and any(z.get("allow_sow") is False for z in growing_zones):
        details["sowing_zone_ids"] = [int(z["id"]) for z in growing_zones if z.get("allow_sow") is False]
        one_time.append("resume_seasonal_sowing")
    if survival_stable and int(item_counts.get("WoodLog") or 0) >= 140 and "prison_blueprint" not in map_state.setdefault("issued", {}):
        one_time.append("build_prison")
    hospital_a = {"x": int(anchor["x"]) + 25, "z": int(anchor["z"])}
    hospital_b = {"x": hospital_a["x"] + 6, "z": hospital_a["z"] + 6}
    hospital_rects = [(hospital_a, hospital_b)]
    for project in map_state.get("architecture_projects", []):
        if project.get("program") != "hospital":
            continue
        origin = project.get("origin") or {}
        start = {"x": int(origin.get("x") or 0), "z": int(origin.get("z") or 0)}
        end = {
            "x": start["x"] + int(project.get("width") or 1) - 1,
            "z": start["z"] + int(project.get("height") or 1) - 1,
        }
        hospital_rects.append((start, end))
    hospital_beds = [
        b for b in dev.get("buildings", [])
        if any(
            start["x"] <= int((b.get("position") or {}).get("x") or -999) <= end["x"]
            and start["z"] <= int((b.get("position") or {}).get("z") or -999) <= end["z"]
            for start, end in hospital_rects
        )
        and str(b.get("def") or "") in {"Bed", "HospitalBed", "SleepingSpot"}
    ]
    has_generated_hospital = any(row.get("program") == "hospital" for row in map_state.get("architecture_projects", []))
    if survival_stable and not has_generated_hospital and int(item_counts.get("WoodLog") or 0) >= 180 and "hospital_blueprint" not in map_state.setdefault("issued", {}):
        one_time.append("build_hospital")
    elif hospital_beds and not all(bool(b.get("medical")) for b in hospital_beds) and not issued_recently(map_state, "hospital_beds", tick, retry_ticks=15000):
        one_time.append("configure_hospital_beds")

    medical_bed_ids = {int(b["id"]) for b in dev.get("buildings", []) if b.get("medical") and b.get("id") is not None}
    critical_floor_options: dict[str, dict[str, Any]] = {}
    for room in dev.get("rooms", []):
        if f"floor_room:{int(room.get('id') or 0)}" in map_state.setdefault("issued", {}):
            continue
        cells = room.get("cells") or []
        if not cells or room.get("touches_map_edge") or int(room.get("cells_count") or 0) > 100:
            continue
        defs = set(map(str, room.get("contained_thing_defs") or []))
        role = str(room.get("role_label") or "").lower()
        is_kitchen = bool(defs & {"FueledStove", "ElectricStove", "Campfire"})
        is_hospital = role == "hospital" or bool(medical_bed_ids & set(map(int, room.get("contained_beds_ids") or [])))
        if not (is_kitchen or is_hospital):
            continue
        material_options = affordable_floor_options(item_counts, finished, len(cells), best_builder)
        for floor_def, cost in material_options.items():
            key = f"{int(room['id'])}|{floor_def}"
            critical_floor_options[key] = {
                "room_id": int(room["id"]),
                "room_kind": "hospital" if is_hospital else "kitchen",
                "cleanliness": round(float(room.get("cleanliness") or 0.0), 2),
                "cells": cells,
                "floor_def": floor_def,
                "cost": cost,
            }
    if survival_stable and critical_floor_options and not issued_recently(map_state, "critical_floor", tick, retry_ticks=120000):
        details["critical_floor_options"] = critical_floor_options
        dev["critical_floor_options"] = critical_floor_options
        one_time.append("floor_critical_room")
    path_options = affordable_floor_options(item_counts, finished, 60, best_builder, pathway=True)
    if survival_stable and path_options and "pathways" not in map_state.setdefault("issued", {}):
        details["path_floor_options"] = path_options
        dev["path_floor_options"] = path_options
        one_time.append("build_pathways")

    nearby_stones: Counter[str] = Counter()
    for row in dev.get("things", []):
        name = str(row.get("def_name") or "")
        if not name.startswith("Chunk") or name in {"ChunkSlagSteel", "ChunkMechanoidSlag"}:
            continue
        pos = row.get("position") or {}
        if (int(pos.get("x") or 0) - int(anchor["x"])) ** 2 + (int(pos.get("z") or 0) - int(anchor["z"])) ** 2 <= 60 ** 2:
            nearby_stones[name] += 1
    has_stonecutter = any(str(table.get("thing_def") or "") == "TableStonecutter" for table in dev.get("work_tables", []))
    stone_dump_exists = any("Laya Stone Chunks" in str(z.get("label") or "") for z in zones)
    if has_stonecutter and nearby_stones and not stone_dump_exists and "stone_chunk_dump" not in map_state.setdefault("issued", {}):
        stonecutter = next(
            (row for row in dev.get("work_tables", []) if str(row.get("thing_def") or "") == "TableStonecutter"),
            {},
        )
        details["stone_dump_anchor"] = stonecutter.get("position") or anchor
        one_time.append("create_stone_chunk_dump")
    stonecutting_needed = (
        ("Stonecutting" not in finished and current.lower() == "none")
        or ("Stonecutting" in finished and not has_stonecutter and not issued_recently(map_state, "stonecutting_table", tick, retry_ticks=60000))
        or (has_stonecutter and "stonecutting_complete" not in map_state.setdefault("issued", {}))
    )
    if survival_stable and nearby_stones and stonecutting_needed:
        details["stone_options"] = dict(nearby_stones)
        dev["stone_options"] = dict(nearby_stones)
        one_time.append("start_stonecutting")
    handler_rows = sorted(
        snapshot["colonists"],
        key=lambda c: int((c.get("skills", {}).get("Animals") or {}).get("level") or 0),
        reverse=True,
    )
    best_handler_row = handler_rows[0] if handler_rows else {}
    best_handler = int((best_handler_row.get("skills", {}).get("Animals") or {}).get("level") or 0)
    inspired_taming = "taming" in str(best_handler_row.get("inspiration") or "").lower()
    tame_options = []
    for animal in snapshot.get("wild_animals", []):
        pos = animal.get("position") or {}
        close = (int(pos.get("x") or 0) - int(anchor["x"])) ** 2 + (int(pos.get("z") or 0) - int(anchor["z"])) ** 2 <= 60 ** 2
        if (animal.get("can_tame") and close and f"tame:{animal.get('id')}" not in map_state.setdefault("issued", {})
                and int(animal.get("minimum_handling_skill") or 0) <= best_handler
                and (inspired_taming or float(animal.get("manhunter_on_tame_fail_chance") or 0.0) <= 0.20)):
            tame_options.append(animal)
    wildlife_paused = issued_recently(map_state, "wildlife_pause", tick, retry_ticks=15000)
    if survival_stable and tame_options and not wildlife_paused:
        details["tame_options"] = tame_options[:20]
        details["handler_context"] = {"name": best_handler_row.get("name"), "skill": best_handler, "inspiration": best_handler_row.get("inspiration")}
        dev["tame_options"] = tame_options[:20]
        dev["handler_context"] = details["handler_context"]
        one_time.append("start_taming")
    combat_rows = snapshot.get("combat", {}).get("colonists", [])
    healthy_armed = [
        row for row in combat_rows
        if row.get("has_ranged_weapon") and not row.get("is_downed") and float(row.get("health") or 0.0) >= 0.8
    ]
    average_shooting = sum(int(row.get("shooting_skill") or 0) for row in healthy_armed) / max(1, len(healthy_armed))
    serious_ranged = [
        row for row in healthy_armed
        if any(token in str(row.get("weapon_def") or "").lower() for token in (
            "rifle", "smg", "lmg", "minigun", "charge", "sniper", "needle", "launcher",
        ))
    ]
    hunt_options = []
    for animal in snapshot.get("wild_animals", []):
        pos = animal.get("position") or {}
        close = (int(pos.get("x") or 0) - int(anchor["x"])) ** 2 + (int(pos.get("z") or 0) - int(anchor["z"])) ** 2 <= 60 ** 2
        if not close or f"hunt:{animal.get('id')}" in map_state.setdefault("issued", {}):
            continue
        is_thrumbo = "thrumbo" in str(animal.get("def") or "").lower()
        safe_small_game = (
            not animal.get("predator")
            and float(animal.get("harm_revenge_chance") or 0.0) <= 0.05
            and float(animal.get("combat_power") or 0.0) <= 100
        )
        prepared_thrumbo_hunt = (
            is_thrumbo
            and len(healthy_armed) >= 4
            and len(serious_ranged) >= 3
            and average_shooting >= 10
        )
        if safe_small_game or prepared_thrumbo_hunt:
            hunt_options.append(animal)
    hunt_options.sort(key=lambda a: (
        "thrumbo" in str(a.get("def") or "").lower(),
        int(a.get("meat_amount") or 0) + int(a.get("leather_amount") or 0),
        float(a.get("market_value") or 0.0),
    ), reverse=True)
    if survival_stable and hunt_options and not wildlife_paused:
        details["hunt_options"] = hunt_options[:20]
        details["fighter_context"] = {
            "healthy_ranged": len(healthy_armed),
            "serious_ranged_weapons": len(serious_ranged),
            "average_shooting": round(average_shooting, 1),
        }
        dev["hunt_options"] = hunt_options[:20]
        dev["fighter_context"] = details["fighter_context"]
    if not wildlife_paused and (details.get("tame_options") or details.get("hunt_options")):
        one_time.append("leave_wildlife_alone")
    colony_animals = [a for a in snapshot.get("animals", []) if a.get("reproductive") and not a.get("pregnant")]
    breed_species = sorted({
        str(a.get("def")) for a in colony_animals
        if a.get("gender") == "Male" and any(b.get("def") == a.get("def") and b.get("gender") == "Female" for b in colony_animals)
    })
    for species in breed_species:
        if not issued_recently(map_state, f"breed:{species}", tick, retry_ticks=60000):
            one_time.append(f"breed_animals:{species}")
    colonists_by_id = {int(c["id"]): c for c in snapshot["colonists"]}
    couples: set[tuple[int, int]] = set()
    for colonist in snapshot["colonists"]:
        for relation in colonist.get("relations", []):
            if str(relation.get("relation_def_name")) not in {"Spouse", "Lover", "Fiance"}:
                continue
            digits = "".join(ch for ch in str(relation.get("other_pawn_id") or "") if ch.isdigit())
            if not digits or int(digits) not in colonists_by_id:
                continue
            pair = tuple(sorted((int(colonist["id"]), int(digits))))
            if pair[0] != pair[1]:
                couples.add(pair)
    for first_id, second_id in sorted(couples):
        if issued_recently(map_state, f"human_reproduction:{first_id}:{second_id}", tick, retry_ticks=3600000):
            continue
        if survival_stable and len(snapshot["colonists"]) >= 4 and int(resources.get("food") or 0) >= 40:
            one_time.extend([
                f"human_reproduction:{first_id}:{second_id}:TryForBaby",
                f"human_reproduction:{first_id}:{second_id}:Normal",
                f"human_reproduction:{first_id}:{second_id}:AvoidPregnancy",
            ])
    prisoner_plans = map_state.setdefault("prisoner_plans", {})
    best_doctor = max((int((c.get("skills", {}).get("Medicine") or {}).get("level") or 0) for c in snapshot["colonists"]), default=0)
    organ_context = {
        "doctor_skill": best_doctor,
        "medicine": int(snapshot["map"]["resources"].get("medicine") or 0),
        "colonist_traits": {
            str(c.get("name")): [str(t.get("label") or t.get("name")) for t in c.get("traits", [])]
            for c in snapshot["colonists"]
        },
        "ideology_precepts": (dev.get("ideology") or {}).get("precepts", []),
    }
    for prisoner in snapshot.get("combat", {}).get("prisoners", []):
        pawn_id = str(prisoner.get("id"))
        if pawn_id in prisoner_plans:
            continue
        if prisoner.get("recruitable", True):
            one_time.append(f"prisoner_policy:{pawn_id}:recruit")
        if prisoner.get("faction_can_give_goodwill") and not prisoner.get("faction_permanent_enemy"):
            one_time.append(f"prisoner_policy:{pawn_id}:release")
        one_time.append(f"prisoner_policy:{pawn_id}:sell")
        if best_doctor >= 8 and int(snapshot["map"]["resources"].get("medicine") or 0) >= 2:
            one_time.append(f"prisoner_policy:{pawn_id}:organs_nonlethal")
            one_time.append(f"prisoner_policy:{pawn_id}:organs_lethal")
            details["organ_context"] = organ_context
            dev["organ_context"] = organ_context
    # Laya chooses a profit specialization only after immediate food and medical
    # needs are stable. The choice controls later infrastructure and research,
    # but is deliberately revisited after one in-game year rather than permanent.
    strategy_tick = int(map_state.get("income_strategy_tick") or -999999)
    if survival_stable and not current_doctrine and (not map_state.get("income_strategy") or tick - strategy_tick >= 3600000):
        one_time.extend([
            "income_drugs",
            "income_tailoring",
            "income_art",
            "income_livestock",
            "income_biofuel",
            "income_mining",
            "income_crops",
            "income_brewing",
            "income_travel_food",
            "income_orbital",
            "income_organs",
        ])
    income_strategy = str(map_state.get("income_strategy") or "")
    strategy_tables = {
        "drugs": {"DrugLab"},
        "tailoring": {"HandTailoringBench", "ElectricTailoringBench"},
        "art": {"TableSculpting"},
        "biofuel": {"BiofuelRefinery"},
        "brewing": {"Brewery"},
        "travel_food": {"FueledStove", "ElectricStove"},
    }
    strategy_research = {
        "drugs": "DrugProduction",
        "biofuel": "BiofuelRefining",
        "brewing": "Brewing",
        "orbital": "MicroelectronicsBasics",
    }
    required_research = strategy_research.get(income_strategy)
    if (
        income_strategy in {"drugs", "biofuel", "brewing", "orbital"}
        and (required_research is None or required_research in finished)
        and not issued_recently(map_state, f"income_infrastructure:{income_strategy}", tick, retry_ticks=60000)
    ):
        present = any(
            str(table.get("thing_def") or "") in strategy_tables.get(income_strategy, set())
            for table in dev.get("work_tables", [])
        )
        if income_strategy == "orbital":
            present = counts.get("CommsConsole", 0) > 0 and counts.get("OrbitalTradeBeacon", 0) > 0
        if not present:
            one_time.append("build_income_infrastructure")
    if income_strategy in strategy_tables and any(
        str(table.get("thing_def") or "") in strategy_tables[income_strategy] for table in dev.get("work_tables", [])
    ) and not issued_recently(map_state, f"income_bills:{income_strategy}", tick, retry_ticks=30000):
        one_time.append("configure_income_production")

    ideology = dev.get("ideology") or {}
    ritual_buildings = ideology.get("ritual_buildings") or []
    if survival_stable and ideology.get("active") and ritual_buildings and "temple" not in map_state.setdefault("issued", {}):
        altar_options = {
            str(row.get("def_name")): (
                f"{row.get('label')} / {row.get('precept_name')}; size {row.get('size_x')}x{row.get('size_z')}; "
                f"stuff cost {row.get('cost_stuff_count')}"
            )
            for row in ritual_buildings if row.get("def_name") and counts.get(str(row.get("def_name")), 0) == 0
        }
        temple_materials = {
            name: note for name, note in structure_material_options(item_counts, minimum_units=500).items()
            if name == "WoodLog" or (name.startswith("Blocks") and "Stonecutting" in finished)
        }
        if altar_options and temple_materials:
            details["temple_options"] = {"altars": altar_options, "materials": temple_materials, "ideology": ideology.get("name")}
            dev["temple_options"] = details["temple_options"]
            one_time.append("build_temple")

    projects = [row for row in dev.get("construction_projects", []) if isinstance(row, dict)][:18]
    if projects and not issued_recently(map_state, "construction_project_priority", tick, retry_ticks=2500):
        details["construction_project_options"] = projects
        dev["construction_project_options"] = projects
        one_time.append("prioritize_construction_project")
    item_counts = dev.get("item_counts", {})
    defense_styles = {
        "fortified_depth": {"killbox", "fallback", "turret", "mortar", "firefoam"},
        "mobile_response": {"fallback", "firefoam"},
        "ranged_firepower": {"fallback", "turret", "mortar", "firefoam"},
        "melee_chokepoints": {"killbox", "fallback", "firefoam"},
        "turret_mortar": {"fallback", "turret", "mortar", "firefoam"},
        "peaceful_deterrence": {"fallback", "firefoam"},
        "psychic_force": {"fallback", "firefoam"},
        "mechanized_force": {"fallback", "turret", "firefoam"},
        "anomaly_weapons": {"fallback", "firefoam"},
        "gravship_security": {"fallback", "turret", "firefoam"},
    }
    allowed_defenses = defense_styles.get(str(current_doctrine.get("military") or ""), {"killbox", "fallback", "turret", "mortar", "firefoam"})
    if survival_stable and "killbox" in allowed_defenses and int(item_counts.get("WoodLog") or 0) >= 180 and "killbox" not in map_state["issued"]:
        one_time.append("build_killbox")
    if survival_stable and "fallback" in allowed_defenses and int(item_counts.get("WoodLog") or 0) >= 100 and "fallback_defense" not in map_state["issued"]:
        one_time.append("build_fallback_defense")
    if "turret" in allowed_defenses and "GunTurrets" in finished and int(item_counts.get("Steel") or 0) >= 220 and int(item_counts.get("ComponentIndustrial") or 0) >= 6 and "turret_defense" not in map_state["issued"]:
        one_time.append("build_turret_defense")
    if "mortar" in allowed_defenses and "Mortars" in finished and int(item_counts.get("Steel") or 0) >= 120 and int(item_counts.get("ReinforcedBarrel") or 0) >= 1 and "mortar_post" not in map_state["issued"]:
        one_time.append("build_mortar_post")
    if "firefoam" in allowed_defenses and "Firefoam" in finished and int(item_counts.get("Steel") or 0) >= 75 and "firefoam_defense" not in map_state["issued"]:
        one_time.append("build_firefoam_defense")
    mech_remains = [
        row for row in dev.get("things", [])
        if "Mechanoid" in str(row.get("def_name") or "")
        or "CorpsesMechanoid" in (row.get("categories") or [])
    ]
    if mech_remains and not issued_recently(map_state, "mech_processing", tick, retry_ticks=60000):
        one_time.append("process_mechanoids")
    planned_sale_ids = {str(k) for k, v in (map_state.get("prisoner_plans") or {}).items() if v == "sell"}
    prisoner_sale_value = sum(
        float(p.get("market_value") or 0.0)
        for p in snapshot.get("combat", {}).get("prisoners", [])
        if str(p.get("id")) in planned_sale_ids
    )
    trade_ready = (
        survival_stable
        and len(snapshot["colonists"]) >= 4
        and int(resources.get("food") or 0) >= 40
        and float(dev.get("trade_value") or 0.0) + prisoner_sale_value >= 2000.0
        and dev.get("settlements")
        and not dev.get("caravans")
        and not issued_recently(map_state, "trade_caravan", tick, retry_ticks=60000)
    )
    if trade_ready:
        sale_categories = available_sale_categories(snapshot)
        destinations = [row for row in dev.get("trade_destinations", []) if row.get("can_trade_now")][:5]
        for destination in destinations:
            for sale in sale_categories or ["mixed"]:
                one_time.append(f"trade_to:{int(destination['settlement_id'])}:{sale}")
    healthy_fighters = [
        pawn for pawn in snapshot["colonists"]
        if not pawn.get("downed") and float(pawn.get("health") or 0.0) >= 0.85
    ]
    raid_ready = (
        survival_stable
        and len(healthy_fighters) >= 6
        and int(resources.get("food") or 0) >= 80
        and int(resources.get("medicine") or 0) >= 15
        and not dev.get("caravans")
        and not issued_recently(map_state, "raid_caravan", tick, retry_ticks=120000)
    )
    if raid_ready:
        for destination in dev.get("raid_destinations", [])[:6]:
            one_time.append(f"raid_to:{int(destination['settlement_id'])}")
    maintenance: list[str] = []
    meals = int(resources.get("meals") or 0)
    medical_emergency = any(
        c.get("downed") or bridge.first_number(c.get("health"), 1.0) < 0.65
        for c in snapshot["colonists"]
    )
    if medical_emergency:
        if not issued_recently(map_state, "priority:BasicWorker", tick, retry_ticks=30000):
            maintenance.append("prioritize_rescue")
        if not issued_recently(map_state, "priority:Doctor", tick, retry_ticks=30000):
            maintenance.append("prioritize_doctor")
        # A downed or critically injured colonist is a hard feasibility boundary:
        # Laya still chooses the response, but routine work is not presented as an
        # equally valid alternative while somebody may die unattended.
        if maintenance:
            return maintenance, details
    if counts.get("Bed", 0) + counts.get("SleepingSpot", 0) < len(snapshot["colonists"]) or any(
        counts.get(name, 0) == 0 for name in ("FueledStove", "SimpleResearchBench")
    ):
        if not issued_recently(map_state, "priority:Construction", tick, retry_ticks=60000):
            maintenance.append("prioritize_construction")
    if current.lower() != "none":
        if survival_stable and not issued_recently(map_state, "priority:Research", tick, retry_ticks=60000):
            maintenance.append("prioritize_research")
    if meals < max(4, len(snapshot["colonists"]) * 2):
        if not issued_recently(map_state, "priority:Cooking", tick, retry_ticks=60000):
            maintenance.append("prioritize_cooking")
    if not issued_recently(map_state, "priority:Growing", tick, retry_ticks=60000):
        maintenance.append("prioritize_growing")
    if not issued_recently(map_state, "priority:Hauling", tick, retry_ticks=60000):
        maintenance.append("prioritize_hauling")
    if not issued_recently(map_state, "priority:PlantCutting", tick, retry_ticks=60000):
        maintenance.append("prioritize_plant_cutting")
    if not issued_recently(map_state, "priority:Cleaning", tick, retry_ticks=60000):
        maintenance.append("prioritize_cleaning")
    if snapshot["map"].get("animals", 0) > 0:
        if not issued_recently(map_state, "priority:Hunting", tick, retry_ticks=60000):
            maintenance.append("prioritize_hunting")
        if not issued_recently(map_state, "priority:Handling", tick, retry_ticks=60000):
            maintenance.append("prioritize_handling")
        if details.get("hunt_options") and not issued_recently(map_state, "safe_hunting", tick, retry_ticks=60000):
            maintenance.append("designate_safe_hunting")
    wild_plant_groups: dict[str, dict[str, Any]] = {}
    cultivated_defs = {"Plant_Rice", "Plant_Corn", "Plant_Potato", "Plant_Cotton", "Plant_Psychoid", "Plant_Hops", "Plant_Healroot"}
    for plant in dev.get("plants", []):
        if not plant.get("harvestable_now"):
            continue
        name = str(plant.get("def_name") or "")
        if name in cultivated_defs:
            continue
        pos = plant.get("position") or {}
        if (int(pos.get("x") or 0) - int(anchor["x"])) ** 2 + (int(pos.get("z") or 0) - int(anchor["z"])) ** 2 > 45 ** 2:
            continue
        group = wild_plant_groups.setdefault(name, {
            "label": str(plant.get("label") or name),
            "harvested_thing": str(plant.get("harvested_thing_def") or "unknown"),
            "count": 0,
            "expected_yield": 0,
            "ids": [],
        })
        group["count"] += 1
        group["expected_yield"] += int(plant.get("harvest_yield") or 0)
        group["ids"].append(int(plant["thing_id"]))
    if wild_plant_groups and not issued_recently(map_state, "harvest", tick, retry_ticks=30000):
        details["wild_plant_options"] = wild_plant_groups
        dev["wild_plant_options"] = wild_plant_groups
        maintenance.append("harvest_local_plants")
    return list(dict.fromkeys(one_time + maintenance)) or ["hold_survival"], details


def build_decision_state(snapshot: dict[str, Any]) -> dict[str, Any]:
    capabilities: dict[str, dict[str, Any]] = {}
    all_skill_names = sorted({
        str(skill_name)
        for colonist in snapshot.get("colonists", [])
        for skill_name in (colonist.get("skills") or {})
    })
    for skill_name in all_skill_names:
        ranked = sorted(snapshot.get("colonists", []), key=lambda c: int((c.get("skills", {}).get(skill_name) or {}).get("level") or 0), reverse=True)
        if ranked:
            skill = (ranked[0].get("skills", {}).get(skill_name) or {})
            capabilities[skill_name] = {
                "best": ranked[0].get("name"),
                "level": int(skill.get("level") or 0),
                "passion": professions.passion_info(skill.get("passion"))["icon"],
                "learning_percent": professions.passion_info(skill.get("passion"))["xp_percent"],
            }
    people = []
    colonists = snapshot.get("colonists", [])
    for c in colonists[:10]:
        skill_rows = sorted(
            (c.get("skills") or {}).items(),
            key=lambda item: (
                bool((item[1] or {}).get("passion")),
                int((item[1] or {}).get("level") or 0),
                not bool((item[1] or {}).get("disabled")),
            ),
            reverse=True,
        )[:8]
        people.append({
            "id": c.get("id"), "name": c.get("name"), "health": c.get("health"), "food": c.get("hunger"),
            "rest": c.get("rest"), "mood": c.get("mood"), "downed": c.get("downed"), "job": c.get("current_job"),
            "traits": [t.get("label") or t.get("name") for t in c.get("traits", [])[:5]],
            "capacities": {
                name: (c.get("capacities") or {}).get(name)
                for name in ("consciousness", "moving", "manipulation", "sight", "talking")
                if name in (c.get("capacities") or {})
            },
            "pain": c.get("pain", 0),
            "conditions": [
                f"{h.get('label') or h.get('def_name')}:{h.get('part')}"
                for h in c.get("health_conditions", [])[:6]
            ],
            "skills": {
                name: {
                    "level": int(row.get("level") or 0),
                    "flame": professions.passion_info(row.get("passion"))["icon"],
                    "disabled": bool(row.get("disabled")),
                }
                for name, row in skill_rows
            },
        })
    dev = snapshot.get("development", {})
    profession_directions = (dev.get("profession_context") or {}).get("directions", {})
    compact_directions = {
        name: {
            "label": row.get("label"),
            "fit": row.get("fit_score"),
            "best_people": [
                {
                    "pawn": person.get("pawn"), "skill": person.get("skill"),
                    "level": person.get("level"), "flame": person.get("flame"),
                }
                for person in (row.get("people") or [])[:2]
            ],
            "work": list(row.get("work_types") or [])[:5],
            "buildings": list(row.get("building_programs") or [])[:4],
        }
        for name, row in sorted(
            profession_directions.items(),
            key=lambda item: float((item[1] or {}).get("fit_score") or 0.0),
            reverse=True,
        )[:12]
    }
    work_types = []
    for row in (dev.get("profession_context") or {}).get("work_types", [])[:48]:
        if isinstance(row, dict):
            work_types.append({
                "name": row.get("def_name") or row.get("name"),
                "label": row.get("label"),
                "skills": list(row.get("relevant_skills") or [])[:3],
            })
        else:
            work_types.append(str(row))
    catalog = dev.get("building_catalog_summary") or {}
    compact_catalog = {
        "total": catalog.get("total_player_buildings"),
        "available_now": catalog.get("available_now"),
        "categories": dict(list((catalog.get("categories") or {}).items())[:20]),
        "worktables": list(catalog.get("worktables") or [])[:32],
        "programs": {
            name: (row or {}).get("label")
            for name, row in list((catalog.get("programs") or {}).items())[:24]
        },
    }
    active_mods = [
        {
            "name": row.get("name"),
            "package_id": row.get("package_id"),
            "version": row.get("version"),
        }
        for row in dev.get("active_mods", [])[:24]
        if isinstance(row, dict)
    ]
    weather = dev.get("weather") or {}
    state = {
        "goal": "A self-sufficient colony pursuing its saved doctrine and chosen long-term ending.",
        "player_preferences": laya_preferences.model_context(dev.get("user_preferences") or laya_preferences.load_preferences()),
        "colony": {
            "date": snapshot.get("game", {}).get("date"),
            "wealth": snapshot.get("game", {}).get("wealth"),
            "population": len(colonists),
            "people_omitted": max(0, len(colonists) - len(people)),
            "threats": snapshot.get("map", {}).get("enemies"),
        },
        "resources": snapshot.get("map", {}).get("resources", {}),
        "people": people,
        "capabilities": capabilities,
        "colony_animals": {
            "count": len(snapshot.get("animals", [])),
            "hungry": sum(
                1 for animal in snapshot.get("animals", [])
                if bridge.first_number(animal.get("hunger"), 1.0) < 0.3
            ),
        },
        "development": {
            "buildings": dict(list((dev.get("building_counts") or {}).items())[:80]),
            "zones": [z.get("label") for z in dev.get("zones", [])[:24]],
            "research": (dev.get("current_research") or {}).get("name"),
            "finished_research": list(dev.get("finished_research") or [])[:80],
            "human_corpses": len(corpse_rows(snapshot, "CorpsesHumanlike")), "animal_corpses": len(corpse_rows(snapshot, "CorpsesAnimal")),
            "corpse_context": dev.get("corpse_context"), "organ_context": dev.get("organ_context"),
            "trade_goods_value": dev.get("trade_value", 0), "income_strategy": dev.get("income_strategy"), "doctrine": dev.get("doctrine"),
            "doctrine_audit": dev.get("doctrine_audit"), "active_mods": active_mods,
            "weather": {
                name: weather.get(name)
                for name in (
                    "weather", "temperature", "growth_season_now", "day_of_year",
                    "quadrum", "current_twelfth", "next_twelfth_average_temperatures",
                )
                if name in weather
            },
            "growing_period": (dev.get("tile_details") or {}).get("growing_period"),
            "rooms": [{"id": r.get("id"), "role": r.get("role_label"), "cleanliness": r.get("cleanliness"), "impressiveness": r.get("impressiveness"), "temperature": r.get("temperature"), "average_glow": r.get("average_glow"), "dark_percent": r.get("dark_cells_percent")} for r in dev.get("rooms", []) if not r.get("touches_map_edge")][:20],
            "storage_utilization_percent": (dev.get("storage") or {}).get("utilization_percent", 0),
            "materials": {name: dev.get("item_counts", {}).get(name, 0) for name in ("Silver", "WoodLog", "Steel", "ComponentIndustrial", "MedicineHerbal", "MedicineIndustrial", "Ambrosia")},
            "profession_direction_fit": compact_directions,
            "all_loaded_work_types": work_types,
            "building_catalog": compact_catalog,
            "royalty": dev.get("royalty", {}),
        },
    }
    return enforce_model_state_budget(state)


def enforce_model_state_budget(state: dict[str, Any], max_characters: int = 12000) -> dict[str, Any]:
    """Bound Laya input without discarding survival, patients, threats or doctrine.

    Laya truncates the encoded state to its configured inference window, but its
    tokenizer first sees the whole JSON document.  Large mod descriptions and
    definition catalogs therefore caused tokenizer warnings and hid useful state
    behind irrelevant metadata.  The normal builder already summarizes those
    catalogs; this final guard also protects heavily modded and mature colonies.
    """
    def size() -> int:
        return len(json.dumps(state, ensure_ascii=False, separators=(",", ":"), default=str))

    if size() <= max_characters:
        return state
    development = state.get("development") or {}
    reductions = (
        ("all_loaded_work_types", lambda value: list(value or [])[:24]),
        ("profession_direction_fit", lambda value: dict(list((value or {}).items())[:8])),
        ("rooms", lambda value: list(value or [])[:10]),
        ("finished_research", lambda value: list(value or [])[:40]),
        ("active_mods", lambda value: list(value or [])[:12]),
        ("buildings", lambda value: dict(list((value or {}).items())[:40])),
    )
    for key, reducer in reductions:
        development[key] = reducer(development.get(key))
        if size() <= max_characters:
            return state
    catalog = development.get("building_catalog") or {}
    development["building_catalog"] = {
        "total": catalog.get("total"),
        "available_now": catalog.get("available_now"),
        "categories": catalog.get("categories", {}),
        "programs": catalog.get("programs", {}),
    }
    if size() <= max_characters:
        return state
    for person in state.get("people") or []:
        person["skills"] = dict(list((person.get("skills") or {}).items())[:4])
        person["conditions"] = list(person.get("conditions") or [])[:3]
    if size() <= max_characters:
        return state
    state["people"] = list(state.get("people") or [])[:6]
    development["rooms"] = list(development.get("rooms") or [])[:6]
    development["profession_direction_fit"] = dict(
        list((development.get("profession_direction_fit") or {}).items())[:5]
    )
    if size() <= max_characters:
        return state
    # Personal guidance remains present, but a pasted essay must not evict live
    # hunger, health and threat data from the model's short inference window.
    preferences = state.get("player_preferences")
    if isinstance(preferences, dict):
        state["player_preferences"] = {
            key: (value[:500] if isinstance(value, str) else value)
            for key, value in list(preferences.items())[:20]
        }
    if size() <= max_characters:
        return state
    # Last-resort shape for extremely modded saves. Candidate generation and
    # feasibility checks have already consumed the full snapshot, so removing
    # definition catalogs here cannot make an impossible action executable.
    state["resources"] = dict(list((state.get("resources") or {}).items())[:24])
    state["capabilities"] = dict(list((state.get("capabilities") or {}).items())[:12])
    state["development"] = {
        key: development.get(key)
        for key in (
            "research", "human_corpses", "animal_corpses", "corpse_context",
            "organ_context", "trade_goods_value", "income_strategy", "doctrine",
            "weather", "growing_period", "storage_utilization_percent", "materials",
        )
    }
    return state


def action_domain(name: str) -> str:
    if name.startswith(("income_", "trade_to:", "raid_to:", "prisoner_policy:")): return "economy_diplomacy"
    if name.startswith(("prioritize_", "harvest_", "designate_", "start_", "breed_")) or name in {"develop_colonist_skill", "optimize_night_owl_schedule"}: return "work_orders"
    if name.startswith(("build_killbox", "build_fallback", "build_turret", "build_mortar", "build_firefoam", "process_mechanoids")): return "defense"
    if name in {"care_for_injured_animal", "feed_hungry_animal", "feed_hungry_colonist", "build_hospital", "configure_hospital_beds", "build_prison"}: return "care"
    if name in {"unforbid_corpses", "create_human_corpse_dump", "create_animal_corpse_dump", "build_cemetery", "build_crematorium"}: return "corpse_management"
    if name.startswith(("build_", "create_", "expand_", "floor_", "install_", "commission_", "excavate_", "finish_")) or name in {"plan_architecture", "improve_room_lighting", "upgrade_workbench"}: return "construction"
    return "strategy"


def action_family(name: str) -> str:
    for prefix in ("trade_to:", "raid_to:", "prisoner_policy:", "human_reproduction:", "breed_animals:"):
        if name.startswith(prefix): return prefix.rstrip(":")
    if name.startswith("income_"): return "income_strategy"
    if name.startswith("prioritize_"): return "work_priority"
    if name.startswith("build_"): return "building_project"
    if name in {"plan_architecture", "improve_room_lighting", "upgrade_workbench"}: return "building_project"
    if name in {"develop_colonist_skill", "optimize_night_owl_schedule"}: return "workforce_development"
    if name.startswith("create_"): return "zone_or_production"
    return name.split(":", 1)[0]


def worker_criteria(snapshot: dict[str, Any], skill_name: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for pawn in snapshot.get("colonists", []):
        if pawn.get("downed") or float(pawn.get("health") or 0) < 0.65:
            continue
        work_name = "Hauling" if skill_name == "Hauling" else skill_name
        if (pawn.get("work_priorities", {}).get(work_name) or {}).get("disabled"):
            continue
        skill = int((pawn.get("skills", {}).get(skill_name) or {}).get("level") or 0)
        traits = ", ".join(str(t.get("label") or t.get("name")) for t in pawn.get("traits", [])) or "no notable traits"
        conditions = ", ".join(f"{h.get('label') or h.get('def_name')} {h.get('part')}" for h in pawn.get("health_conditions", [])) or "no visible injury"
        caps = pawn.get("capacities") or {}
        result[str(pawn["id"])] = (
            f"{pawn.get('name')}: {skill_name} {skill}; traits {traits}; health {pawn.get('health')}; pain {pawn.get('pain')}; "
            f"moving {caps.get('moving', 1)}, manipulation {caps.get('manipulation', 1)}, sight {caps.get('sight', 1)}; {conditions}"
        )
    return result


def subchoice_questions_for_action(action: str, snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    dev = snapshot.get("development", {})
    q: dict[str, dict[str, Any]] = {}
    if action == "plan_architecture" and dev.get("architecture_program_options"):
        q["architecture_program"] = {
            "type": "choice",
            "instructions": "Choose the function of the next building first. Layout, size and furniture are asked only after this program is selected.",
            "criteria": dict(dev["architecture_program_options"]),
        }
    elif action == "advance_doctrine_research" and dev.get("doctrine_research_options"):
        q["doctrine_research_target"] = {
            "type": "choice",
            "instructions": "Choose one currently startable project that best advances the saved doctrine. Only live ResearchProjectDefs are listed.",
            "criteria": dict(dev["doctrine_research_options"]),
        }
    elif action == "improve_room_lighting" and dev.get("dark_room_options"):
        q["lighting_room"] = {
            "type": "choice",
            "instructions": "Choose the room where darkness currently causes the most work, treatment or quality loss.",
            "criteria": {
                str(key): f"{row.get('role')} room {row.get('room_id')}; average glow {row.get('average_glow')}; {row.get('dark_percent')}% dark; {row.get('temperature')} C"
                for key, row in dev["dark_room_options"].items()
            },
        }
    elif action == "develop_colonist_skill" and dev.get("skill_training_options"):
        q["skill_training_plan"] = {
            "type": "choice",
            "instructions": "Choose one real colonist-skill-work plan. Large flame learns at 150%, small flame at 100%, no flame at 35%; also consider current competence, Fast/Slow Learner traits and colony gaps.",
            "criteria": {
                str(key): (
                    f"{row.get('pawn_name')}: {row.get('skill')} {row.get('level')} {row.get('flame')} "
                    f"({row.get('xp_percent')}% passion multiplier, learning factor {row.get('learning_trait_factor')}); "
                    f"train through {', '.join(row.get('work_types') or [])}; traits {row.get('traits')}"
                ) for key, row in dev["skill_training_options"].items()
            },
        }
    elif action == "optimize_night_owl_schedule" and dev.get("night_owl_options"):
        q["night_owl_pawn"] = {
            "type": "choice",
            "instructions": "Choose which Night Owl receives a day-sleep/night-awake timetable now.",
            "criteria": dict(dev["night_owl_options"]),
        }
    elif action == "upgrade_workbench" and dev.get("workbench_upgrade_options"):
        q["workbench_upgrade"] = {
            "type": "choice",
            "instructions": "Choose one unlocked and affordable production transition. The old bench remains until the new one is completed.",
            "criteria": {
                str(key): f"{row.get('old')} -> {row.get('new')}: {row.get('benefit')}; research {row.get('research')}; fixed costs {row.get('costs')}"
                for key, row in dev["workbench_upgrade_options"].items()
            },
        }
    elif action.startswith("trade_to:"):
        q["trade_purchase_plan"] = {"type": "choice", "instructions": "Choose a purchase priority; survival reserves are protected by code.", "criteria": {
            "medicine": "Medicine", "components": "Components and advanced components", "food": "Shelf-stable food",
            "weapons": "Weapons or armor", "livestock": "Productive or pack animals", "none": "Sell only and preserve silver",
        }}
    elif action == "start_stonecutting" and dev.get("stone_options"):
        q["stone_type"] = {"type": "choice", "instructions": "Choose the nearby chunk type to cut.", "criteria": {str(k): f"{v} nearby chunks" for k, v in dev["stone_options"].items()}}
    elif action == "start_taming" and dev.get("tame_options"):
        handler = dev.get("handler_context") or {}
        q["tame_target"] = {"type": "choice", "instructions": f"Choose an exact animal. Handler {handler}.", "criteria": {
            str(a["id"]): f"{a.get('def')} {a.get('gender')}; wildness {a.get('wildness')}; minimum skill {a.get('minimum_handling_skill')}; revenge {a.get('manhunter_on_tame_fail_chance')}; value {a.get('market_value')}"
            for a in dev["tame_options"]
        }}
    elif action == "designate_safe_hunting" and dev.get("hunt_options"):
        q["hunt_target"] = {"type": "choice", "instructions": f"Choose the exact target using food need and fighter context {dev.get('fighter_context')}.", "criteria": {
            str(a["id"]): f"{a.get('def')} {a.get('gender')}; power {a.get('combat_power')}; revenge {a.get('harm_revenge_chance')}; meat {a.get('meat_amount')}; leather {a.get('leather_amount')}; value {a.get('market_value')}"
            for a in dev["hunt_options"]
        }}
    elif action == "harvest_local_plants" and dev.get("wild_plant_options"):
        q["wild_plant_type"] = {"type": "choice", "instructions": "Choose one mature wild plant type using food, medicine, wood and trade needs.", "criteria": {
            str(k): f"{v.get('label')}: {v.get('count')} plants, expected {v.get('expected_yield')} {v.get('harvested_thing')}" for k, v in dev["wild_plant_options"].items()
        }}
    elif action == "floor_critical_room" and dev.get("critical_floor_options"):
        q["critical_floor_plan"] = {"type": "choice", "instructions": "Choose a real kitchen/hospital and affordable floor.", "criteria": {
            str(k): f"{v.get('room_kind')} {v.get('room_id')}; cleanliness {v.get('cleanliness')}; {v.get('floor_def')} {v.get('cost')}" for k, v in dev["critical_floor_options"].items()
        }}
    elif action == "build_pathways" and dev.get("path_floor_options"):
        q["path_material"] = {"type": "choice", "instructions": "Choose fireproof outdoor flagstone; steel floors are intentionally unavailable.", "criteria": dict(dev["path_floor_options"])}
    elif action == "install_sculpture" and dev.get("sculpture_install_options"):
        q["sculpture_install_plan"] = {"type": "choice", "instructions": "Choose the finished sculpture and room.", "criteria": {
            str(k): f"{v.get('sculpture')} beauty {v.get('beauty')} -> {v.get('room_role')} room {v.get('room_id')}" for k, v in dev["sculpture_install_options"].items()
        }}
    elif action == "build_animal_barn" and dev.get("animal_barn_options"):
        opts = dev["animal_barn_options"]
        q["animal_barn_material"] = {"type": "choice", "instructions": "Choose the barn wall material.", "criteria": dict(opts.get("material_options") or {})}
        if opts.get("straw_available"):
            q["animal_barn_floor"] = {"type": "choice", "instructions": "Choose straw or bare ground considering filth, hay and fire.", "criteria": {"straw": "Low filth, consumes hay, highly flammable", "bare": "Free, nonflammable natural ground"}}
    elif action == "build_temple" and dev.get("temple_options"):
        opts = dev["temple_options"]
        q["temple_altar"] = {"type": "choice", "instructions": f"Choose the exact ritual focus for {opts.get('ideology')}.", "criteria": dict(opts.get("altars") or {})}
        q["temple_material"] = {"type": "choice", "instructions": "Choose an affordable, preferably fireproof temple material.", "criteria": dict(opts.get("materials") or {})}
    elif action == "prioritize_construction_project" and dev.get("construction_project_options"):
        q["construction_project"] = {"type": "choice", "instructions": "Choose one exact unfinished project. Prefer survival-critical, nearly finished, and materially feasible work.", "criteria": {
            str(p["thing_id"]): f"{p.get('label')} ({p.get('kind')}) {float(p.get('percent_complete') or 0) * 100:.0f}% at {p.get('position')}; stuff {p.get('stuff_def_name')}" for p in dev["construction_project_options"]
        }}
        q["worker_pawn"] = {"type": "choice", "instructions": "Choose a builder using Construction, manipulation, movement, traits and injuries.", "criteria": worker_criteria(snapshot, "Construction")}
    elif action in {"prioritize_construction", "prioritize_burial"}:
        skill = "Construction" if action == "prioritize_construction" else "Hauling"
        q["worker_pawn"] = {"type": "choice", "instructions": "Choose the exact colonist. Corpse-tolerant traits reduce mood cost; injuries and missing limbs reduce throughput.", "criteria": worker_criteria(snapshot, skill)}
    elif action == "choose_colony_doctrine" and dev.get("doctrine_context"):
        # Doctrine uses its own conditional cascade in choose_action: broad
        # domain -> exact direction -> compatible axes -> economy product.
        return {}
    return {name: question for name, question in q.items() if question.get("criteria")}


def choose_action(agent: Any, snapshot: dict[str, Any], candidates: list[str]) -> dict[str, Any]:
    state = build_decision_state(snapshot)
    raw_domain = None
    raw_family = None
    player_preferences = snapshot.get("development", {}).get("user_preferences") or laya_preferences.load_preferences()
    considered = sorted(candidates, key=lambda name: laya_preferences.priority_for_action(name, player_preferences), reverse=True)
    if len(candidates) > 18:
        domains: dict[str, list[str]] = {}
        for name in candidates:
            domains.setdefault(action_domain(name), []).append(name)
        domain_question = {"colony_goal_domain": {"type": "choice", "instructions": "Choose the next decision domain. A second question will contain only feasible actions in that domain.", "criteria": {
            domain: "; ".join(action_label(name, snapshot) for name in names[:8]) for domain, names in domains.items()
        }}}
        raw_domain = agent.predict(state, domain_question)
        selected_domain = str(raw_domain.get("answers", {}).get("colony_goal_domain", {}).get("choice") or "")
        considered = domains.get(selected_domain) or next(iter(domains.values()))
    if len(considered) > 18:
        families: dict[str, list[str]] = {}
        for name in considered:
            families.setdefault(action_family(name), []).append(name)
        family_question = {"colony_goal_family": {"type": "choice", "instructions": "Choose a feasible action family; the next question will contain concrete actions only from it.", "criteria": {
            family: "; ".join(action_label(name, snapshot) for name in names[:8]) for family, names in families.items()
        }}}
        raw_family = agent.predict(state, family_question)
        selected_family = str(raw_family.get("answers", {}).get("colony_goal_family", {}).get("choice") or "")
        considered = families.get(selected_family) or next(iter(families.values()))
    considered = considered[:18]

    raw_action = None
    if len(considered) == 1:
        choice = considered[0]
        action_answer = {"choice": choice, "confidence": 1.0, "probabilities": {choice: 1.0}}
        mode = "single_feasible_action"
    else:
        action_question = {"colony_goal_action": {"type": "choice", "instructions": "Choose the next concrete feasible action for survival and the saved long-term doctrine. Respect the player's preference weights and personal guidance from state, but never bypass safety or feasibility. Parameters of unchosen actions will not be asked.", "criteria": {
            name: f"{action_description(name, snapshot)} Player priority: {laya_preferences.priority_for_action(name, player_preferences)}/100."
            for name in considered
        }}}
        raw_action = agent.predict(state, action_question)
        action_answer = raw_action.get("answers", {}).get("colony_goal_action", {})
        choice = str(action_answer.get("choice") or "")
        if choice not in considered: choice = considered[0]
        mode = "hierarchical"

    parsed: dict[str, Any] = {}
    merged_answers = {"colony_goal_action": action_answer}
    if choice == "choose_colony_doctrine":
        cascade = strategy.choose_cascaded_doctrine(
            agent, state, snapshot.get("development", {}).get("doctrine_context") or {}
        )
        parsed["doctrine_selection"] = cascade["selection"]
        parsed["doctrine_direction_audit"] = cascade["audit"]
        merged_answers.update(cascade["answers"])
        raw_details: dict[str, Any] | None = {"mode": "cascaded", "steps": cascade["raw_steps"]}
    else:
        detail_questions = subchoice_questions_for_action(choice, snapshot)
        raw_details = agent.predict(state, detail_questions) if detail_questions else None
        if raw_details:
            merged_answers.update(raw_details.get("answers", {}))
            for question_id, question in detail_questions.items():
                selected = str(raw_details.get("answers", {}).get(question_id, {}).get("choice") or "")
                if selected not in question["criteria"]:
                    continue
                if question_id in {"tame_target", "hunt_target", "worker_pawn", "construction_project", "night_owl_pawn"}:
                    parsed[question_id] = int(selected)
                else:
                    parsed[question_id] = selected

    if choice == "plan_architecture" and parsed.get("architecture_program"):
        program = str(parsed["architecture_program"])
        architecture_context = snapshot.get("development", {}).get("architecture_context") or {}
        variants = architect.generate_program_variants(
            program,
            architecture_context,
            seed=int(architecture_context.get("variant_seed") or 0),
        )
        considered_variants = variants
        if program == "residence" and variants:
            styles = {
                style: description for style, description in architect.HOUSE_STYLES.items()
                if any(row.get("style") == style for row in variants.values())
            }
            style_question = {
                "architecture_house_style": {
                    "type": "choice",
                    "instructions": "Choose a house character. Four generated size/door/furniture variants will then be compared inside this style (24 possible houses total).",
                    "criteria": styles,
                }
            }
            style_raw = agent.predict(state, style_question)
            style = str(style_raw.get("answers", {}).get("architecture_house_style", {}).get("choice") or "")
            if style not in styles:
                style = next(iter(styles))
            parsed["architecture_house_style"] = style
            considered_variants = {key: row for key, row in variants.items() if row.get("style") == style}
            merged_answers.update(style_raw.get("answers", {}))
        if considered_variants:
            variant_question = {
                "architecture_variant": {
                    "type": "choice",
                    "instructions": "Choose the exact generated layout. Every option is enclosed, lit and uses only the selected building program; code will still let RimWorld validate placement.",
                    "criteria": {key: row.get("summary") for key, row in considered_variants.items()},
                }
            }
            variant_raw = agent.predict(state, variant_question)
            variant = str(variant_raw.get("answers", {}).get("architecture_variant", {}).get("choice") or "")
            if variant not in considered_variants:
                variant = next(iter(considered_variants))
            parsed["architecture_variant"] = variant
            merged_answers.update(variant_raw.get("answers", {}))

    aliases = {"trade_purchase_plan": "trade_purchase"}
    for source, target in aliases.items():
        if source in parsed: parsed[target] = parsed.pop(source)
    raw = {"mode": mode, "domain": raw_domain, "family": raw_family, "action": raw_action, "details": raw_details, "answers": merged_answers}
    return {"choice": choice, "confidence": bridge.first_number(action_answer.get("confidence"), 1.0), **parsed, "raw": raw}


def probability_bars(
    probabilities: dict[str, Any],
    labels: dict[str, str],
    selected: str,
    limit: int,
) -> list[dict[str, Any]]:
    ranked = sorted(
        ((str(name), bridge.first_number(value)) for name, value in probabilities.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    visible = ranked[:limit]
    if selected in probabilities and selected not in {name for name, _ in visible}:
        visible = (visible[:-1] if visible else []) + [(selected, bridge.first_number(probabilities[selected]))]
    return [
        {
            "label": str(labels.get(name) or name),
            "value": max(0.0, min(1.0, value)),
            "selected": name == selected,
        }
        for name, value in visible
    ]


def show_overlay(
    client: bridge.RimApiClient,
    *,
    compact_lines: list[str],
    full_lines: list[str],
    bars: list[dict[str, Any]] | None = None,
    duration: float = 12.0,
    color: str = "#E8F4FF",
) -> None:
    overlay = laya_preferences.load_preferences().get("overlay") or {}
    if not overlay.get("enabled", True):
        client.post(
            "/api/v1/ui/announce",
            body={"text": "", "duration": 0.0, "color": color, "scale": 1.0, "panel": True, "compact": True, "bars": []},
        )
        return
    compact = bool(overlay.get("compact", True))
    max_options = max(3, min(8, int(overlay.get("max_options", 5))))
    client.post(
        "/api/v1/ui/announce",
        body={
            "text": "\n".join(compact_lines if compact else full_lines),
            "duration": duration,
            "color": color,
            "scale": 1.0,
            "panel": True,
            "compact": compact,
            "bars": list(bars or [])[:max_options],
        },
    )


def publish_overlay(
    client: bridge.RimApiClient,
    snapshot: dict[str, Any],
    candidates: list[str],
    decision: dict[str, Any],
) -> None:
    probabilities: dict[str, float] = {}
    raw = decision.get("raw") or {}
    try:
        probabilities = {
            str(name): float(value)
            for name, value in raw["answers"]["colony_goal_action"].get("probabilities", {}).items()
        }
    except (KeyError, TypeError, ValueError):
        if len(candidates) == 1:
            probabilities = {candidates[0]: 1.0}
    ordered = sorted(candidates, key=lambda name: probabilities.get(name, 0.0), reverse=True)
    choice = str(decision["choice"])
    option_lines = []
    for name in ordered:
        marker = ">" if name == choice else " "
        probability = probabilities.get(name)
        score = f" {probability * 100:4.1f}%" if probability is not None else ""
        option_lines.append(f"{marker} {action_label(name, snapshot)}{score}")
    for question_id, answer in (raw.get("answers") or {}).items():
        if question_id == "colony_goal_action" or not isinstance(answer, dict):
            continue
        sub_probabilities = answer.get("probabilities") or {}
        selected = str(answer.get("choice") or "")
        option_lines.append("")
        option_lines.append(f"{question_id}:")
        for name, value in sorted(sub_probabilities.items(), key=lambda item: float(item[1]), reverse=True)[:8]:
            option_lines.append(f"{'> ' if str(name) == selected else '  '}{name} {float(value) * 100:.1f}%")
    resources = snapshot["map"]["resources"]
    lowest_food = min((float(c.get("hunger") or 0.0) for c in snapshot["colonists"]), default=0.0)
    jobs = ", ".join(f"{c['name']}: {c['current_job']}" for c in snapshot["colonists"][:4])
    animal_status = ", ".join(
        f"{a['name']} {float(a['health']) * 100:.0f}%"
        for a in snapshot.get("animals", [])[:3]
    ) or "нет"
    corpses = snapshot.get("development", {}).get("corpses", [])
    doctrine_lines: list[str] = []
    doctrine = decision.get("doctrine_selection") or snapshot.get("development", {}).get("doctrine") or {}
    if doctrine:
        labels = doctrine.get("labels") or strategy.doctrine_labels(doctrine)
        doctrine_lines = [
            "",
            f"Курс: {labels.get('primary_direction', '—')} | финал: {labels.get('endgame', '—')}",
            f"Экономика: {labels.get('economy', '—')} | технологии: {labels.get('technology', '—')}",
            f"Оборона: {labels.get('military', '—')} | общество: {labels.get('society', '—')}",
        ]
    text = "\n".join(
        [
            "LAYA — автономный директор",
            f"Еда: {resources.get('food', 0)} | мин. сытость: {lowest_food * 100:.0f}% | враги: {snapshot['map']['enemies']}",
            f"Сейчас: {jobs}",
            f"Животные: {animal_status}",
            f"Незахоронённые трупы: {len(corpses)} | стоимость имущества: {snapshot['development'].get('trade_value', 0):.0f}",
            "",
            "Варианты этого цикла:",
            *option_lines,
            *doctrine_lines,
            "",
            f"Выбрано: {action_label(choice, snapshot)}",
        ]
    )
    bars = probability_bars(
        probabilities,
        {name: action_label(name, snapshot) for name in probabilities},
        choice,
        8,
    )
    show_overlay(
        client,
        compact_lines=[
            "LAYA — автономный директор",
            f"Еда: {resources.get('food', 0)} · враги: {snapshot['map']['enemies']}",
            f"Выбрано: {action_label(choice, snapshot)}",
        ],
        full_lines=text.splitlines(),
        bars=bars,
        duration=12.0,
        color="#E8F4FF",
    )


def publish_combat_overlay(client: bridge.RimApiClient, record: dict[str, Any], repeated: bool = False) -> None:
    snapshot = record["snapshot"]
    decision = record["decision"]
    choice = str(decision.get("choice") or "hold_and_observe")
    probabilities: dict[str, float] = {}
    try:
        answer = next(iter((decision.get("raw") or {})["answers"].values()))
        probabilities = {str(k): float(v) for k, v in answer.get("probabilities", {}).items()}
    except (KeyError, TypeError, ValueError, StopIteration):
        pass
    lines = [
        "LAYA — БОЕВОЙ РЕЖИМ",
        f"Противники: {len(snapshot['combat']['hostiles'])}",
        "",
        "Варианты:",
    ]
    for name, value in sorted(probabilities.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"{'> ' if name == choice else '  '}{name} {value * 100:.1f}%")
    lines.extend(["", f"Приказ: {record['action']['description']}"])
    if repeated:
        lines.append("Приказ уже выполняется; повторно не отправлен.")
    show_overlay(
        client,
        compact_lines=[
            "LAYA — БОЕВОЙ РЕЖИМ",
            f"Противники: {len(snapshot['combat']['hostiles'])}",
            f"Приказ: {record['action']['description']}",
            *(["Приказ уже выполняется"] if repeated else []),
        ],
        full_lines=lines,
        bars=probability_bars(probabilities, {name: name for name in probabilities}, choice, 8),
        duration=12.0,
        color="#FFD7D7",
    )


def post_blueprint(client: bridge.RimApiClient, map_id: int, anchor: dict[str, int], layout: dict[str, Any], dx: int = 0, dz: int = 0) -> Any:
    return client.post(
        "/api/v1/builder/blueprint",
        body={
            "map_id": map_id,
            "position": position(anchor["x"] + dx, anchor["z"] + dz),
            "blueprint": layout,
            "clear_obstacles": False,
        },
    )


def prioritize(client: bridge.RimApiClient, snapshot: dict[str, Any], work: str, pawn_id: int | None = None) -> Any:
    target = next(
        (p for p in snapshot["colonists"] if pawn_id is not None and int(p.get("id", -1)) == int(pawn_id)),
        None,
    )
    target = target or bridge.choose_worker(snapshot["colonists"], work)
    if target is None:
        return {"applied": False, "reason": f"No eligible colonist for {work}"}
    response = client.post(
        "/api/v1/colonist/work-priority",
        body={"id": target["id"], "work": work, "priority": 1},
    )
    return {"applied": True, "colonist": target["name"], "work": work, "response": response}


def configure_food_bills(client: bridge.RimApiClient, tables: list[dict[str, Any]]) -> dict[str, Any]:
    responses = []
    for table in tables:
        def_name = str(table.get("thing_def") or "")
        table_id = int(table.get("id"))
        try:
            bills = client.get("/api/v1/buildings/bills", building_id=table_id)
        except bridge.RimApiError:
            continue
        recipes = {str(row.get("recipe_def_name")) for row in bills if isinstance(row, dict)}
        if def_name in {"FueledStove", "ElectricStove"} and "CookMealSimple" not in recipes:
            responses.append(client.post(
                "/api/v1/buildings/bills/add",
                query={"building_id": table_id},
                body={"recipe_def_name": "CookMealSimple", "repeat_mode": "TargetCount", "target_count": 20, "pause_when_satisfied": True, "unpause_when_you_have": 8},
            ))
        if def_name in {"TableButcher", "ButcherSpot"} and "ButcherCorpseFlesh" not in recipes:
            responses.append(client.post(
                "/api/v1/buildings/bills/add",
                query={"building_id": table_id},
                body={"recipe_def_name": "ButcherCorpseFlesh", "repeat_mode": "Forever"},
            ))
    return {"applied": bool(responses), "responses": responses}


def ensure_bill(client: bridge.RimApiClient, table: dict[str, Any], recipe: str, target_count: int = 20) -> Any:
    table_id = int(table.get("id"))
    bills = client.get("/api/v1/buildings/bills", building_id=table_id)
    if any(str(row.get("recipe_def_name")) == recipe for row in bills if isinstance(row, dict)):
        return {"applied": False, "reason": f"{recipe} already configured"}
    return client.post(
        "/api/v1/buildings/bills/add",
        query={"building_id": table_id},
        body={
            "recipe_def_name": recipe,
            "repeat_mode": "TargetCount",
            "target_count": target_count,
            "pause_when_satisfied": True,
            "unpause_when_you_have": max(1, target_count // 3),
        },
    )


def select_research_if_available(client: bridge.RimApiClient, name: str) -> dict[str, Any]:
    project = client.get("/api/v1/research/project", name=name)
    if not project.get("can_start_now"):
        return {"applied": False, "reason": f"{name} prerequisites are not finished"}
    return client.post("/api/v1/research/target", query={"name": name, "force": False})


def execute_action(client: bridge.RimApiClient, snapshot: dict[str, Any], map_state: dict[str, Any], choice: str, details: dict[str, Any]) -> Any:
    map_id = snapshot["map"]["id"]
    tick = int(snapshot["game"].get("tick") or 0)
    anchor = map_state["anchor"]
    issued = map_state.setdefault("issued", {})

    if choice == "plan_architecture":
        program = str(details.get("architecture_program") or "")
        variant_id = str(details.get("architecture_variant") or "")
        context = details.get("architecture_context") or {}
        variants = architect.generate_program_variants(
            program, context, seed=int(context.get("variant_seed") or 0)
        ) if program else {}
        selected = variants.get(variant_id)
        if not selected:
            return {"applied": False, "reason": "Laya did not select a valid generated architecture variant"}
        sequence = int(map_state.get("architecture_sequence") or 0)
        desired = {
            "x": int(anchor["x"]) + 32 + (sequence % 3) * 16,
            "z": int(anchor["z"]) - 18 + (sequence // 3) * 16,
        }
        terrain = client.get("/api/v1/map/terrain", map_id=map_id)
        origin = find_terrain_rect(
            terrain,
            desired,
            int(selected["width"]),
            int(selected["height"]),
            {"Soil", "SoilRich", "Gravel", "Sand", "MarshyTerrain"},
            radius=35,
        ) or desired
        response = client.post("/api/v1/builder/blueprint", body={
            "map_id": map_id,
            "position": position(origin["x"], origin["z"]),
            "blueprint": selected["layout"],
            "clear_obstacles": False,
        })
        project = {
            "program": program,
            "variant": variant_id,
            "style": selected.get("style"),
            "origin": origin,
            "width": int(selected["width"]),
            "height": int(selected["height"]),
            "issued_tick": tick,
        }
        map_state.setdefault("architecture_projects", []).append(project)
        map_state["architecture_sequence"] = sequence + 1
        issued["architecture_project"] = tick
        issued[f"architecture:{program}:{sequence}"] = tick
        return {
            "applied": True,
            "project": project,
            "summary": selected.get("summary"),
            "blueprint": response,
            "construction": prioritize(client, snapshot, "Construction"),
        }

    if choice == "improve_room_lighting":
        key = str(details.get("lighting_room") or "")
        room = (details.get("dark_room_options") or {}).get(key)
        if not room or not room.get("placement_cells"):
            return {"applied": False, "reason": "No verified empty placement cell remains in the chosen dark room"}
        target = room["placement_cells"][0]
        powered = "Electricity" in set(map(str, snapshot.get("development", {}).get("finished_research") or []))
        light_def = "StandingLamp" if powered else "TorchLamp"
        response = client.post("/api/v1/builder/blueprint", body={
            "map_id": map_id,
            "position": position(int(target["x"]), int(target["z"])),
            "blueprint": architect.blueprint([architect.building(light_def, 0, 0)], 1, 1),
            "clear_obstacles": False,
        })
        issued["room_lighting"] = tick
        issued[f"room_lighting:{room.get('room_id')}"] = tick
        return {"applied": True, "room": room, "light": light_def, "response": response}

    if choice == "develop_colonist_skill":
        key = str(details.get("skill_training_plan") or "")
        plan = (details.get("skill_training_options") or {}).get(key)
        if not plan:
            return {"applied": False, "reason": "Laya did not select a valid skill-development plan"}
        response = client.post("/api/v1/colonist/work-priority", body={
            "id": int(plan["pawn_id"]),
            "work": str(plan["work_type"]),
            "priority": 2,
        })
        map_state.setdefault("skill_development_plans", {})[str(plan["pawn_id"])] = {
            "skill": plan["skill"], "work_type": plan["work_type"], "started_tick": tick,
            "passion": plan["passion"],
        }
        issued["skill_development"] = tick
        return {"applied": True, "plan": plan, "response": response}

    if choice == "optimize_night_owl_schedule":
        pawn_id = details.get("night_owl_pawn")
        if pawn_id is None or str(pawn_id) not in (details.get("night_owl_options") or {}):
            return {"applied": False, "reason": "Laya did not select a valid Night Owl colonist"}
        responses = [
            client.post("/api/v1/colonist/time-assignment", body={
                "pawn_id": int(pawn_id), "hour": hour, "assignment": assignment,
            })
            for hour, assignment in professions.night_owl_schedule().items()
        ]
        scheduled = map_state.setdefault("night_owl_schedules", [])
        if int(pawn_id) not in scheduled:
            scheduled.append(int(pawn_id))
        issued[f"night_owl:{int(pawn_id)}"] = tick
        return {"applied": True, "pawn_id": int(pawn_id), "schedule": professions.night_owl_schedule(), "responses": responses}

    if choice == "upgrade_workbench":
        key = str(details.get("workbench_upgrade") or "")
        plan = (details.get("workbench_upgrade_options") or {}).get(key)
        if not plan:
            return {"applied": False, "reason": "Laya did not select a valid workbench transition"}
        old = next((row for row in snapshot.get("development", {}).get("buildings", []) if str(row.get("def")) == str(plan["old"])), None)
        if not old:
            return {"applied": False, "reason": f"Source workbench {plan['old']} is no longer present"}
        old_pos = old.get("position") or anchor
        target_row = next((row for row in snapshot.get("development", {}).get("building_catalog", []) if row.get("def_name") == plan["new"]), {})
        stuff = plan.get("stuff")
        response = client.post("/api/v1/builder/blueprint", body={
            "map_id": map_id,
            "position": position(int(old_pos.get("x") or 0) + 4, int(old_pos.get("z") or 0)),
            "blueprint": architect.blueprint([architect.building(str(plan["new"]), 0, 0, stuff=stuff, rotation=2)], max(3, int(target_row.get("size_x") or 3)), max(2, int(target_row.get("size_z") or 2))),
            "clear_obstacles": False,
        })
        issued["workbench_upgrade"] = tick
        issued[f"workbench_upgrade:{plan['new']}"] = tick
        map_state.setdefault("workbench_upgrades", []).append({**plan, "issued_tick": tick, "old_retained": True})
        return {"applied": True, "transition": plan, "old_retained": True, "response": response}

    if choice == "choose_colony_doctrine":
        doctrine = dict(details.get("doctrine_selection") or {})
        if not doctrine:
            return {"applied": False, "reason": "The cascaded doctrine selection is incomplete"}
        map_state["doctrine"] = doctrine
        map_state["doctrine_audit"] = {
            "coverage": (details.get("doctrine_direction_audit") or {}).get("coverage", {}),
            "expansions": (details.get("doctrine_direction_audit") or {}).get("expansions", {}),
            "available_directions": list((details.get("doctrine_direction_audit") or {}).get("available", {})),
            "unavailable_directions": {
                name: row.get("reason") for name, row in (details.get("doctrine_direction_audit") or {}).get("unavailable", {}).items()
            },
        }
        map_state["doctrine_tick"] = tick
        map_state["income_strategy"] = strategy.legacy_income(doctrine)
        map_state["income_strategy_tick"] = tick
        issued["doctrine"] = tick
        return {
            "applied": True,
            "doctrine": doctrine,
            "audit": map_state["doctrine_audit"],
            "note": "Existing buildings remain unchanged; the doctrine affects only future research, projects and priorities.",
        }
    if choice == "build_private_bedroom":
        material = str(details.get("bedroom_material") or (map_state.get("doctrine") or {}).get("material") or "WoodLog")
        room_count = sum(1 for r in snapshot["development"].get("rooms", []) if "bedroom" in str(r.get("role_label") or "").lower())
        layout = private_bedroom_blueprint(
            material,
            powered="Electricity" in set(map(str, snapshot["development"].get("finished_research", []))),
            complex_furniture="ComplexFurniture" in set(map(str, snapshot["development"].get("finished_research", []))),
            climate="cold" if float((snapshot["development"].get("weather") or {}).get("temperature") or 0) < 8 else "hot" if float((snapshot["development"].get("weather") or {}).get("temperature") or 0) > 30 else "temperate",
        )
        result = post_blueprint(client, map_id, anchor, layout, dx=34 + (room_count % 3) * 8, dz=(room_count // 3) * 8)
        issued[f"private_bedroom:{room_count}"] = tick
        return {"applied": True, "material": material, "response": result}
    if choice == "excavate_mountain_bedroom":
        rect = details.get("mountain_bedroom_rect")
        if not rect:
            return {"applied": False, "reason": "No verified solid natural-rock room is available"}
        point_a, point_b = rect
        x, z = int(point_a["x"]), int(point_a["z"])
        responses = [
            client.post("/api/v1/order/designate/area", body={"map_id": map_id, "point_a": position(x + 1, z + 1), "point_b": position(x + 5, z + 5), "type": "mine"}),
            client.post("/api/v1/order/designate/area", body={"map_id": map_id, "point_a": position(x + 3, z), "point_b": position(x + 3, z), "type": "mine"}),
            prioritize(client, snapshot, "Mining"),
        ]
        map_state["mountain_bedroom"] = {"x": x, "z": z, "furnished": False}
        issued["mountain_bedroom_mine"] = tick
        return {"applied": True, "responses": responses}
    if choice == "finish_mountain_bedroom":
        plan = map_state.get("mountain_bedroom") or {}
        if not plan:
            return {"applied": False, "reason": "No excavated mountain bedroom plan exists"}
        temperature = float((snapshot["development"].get("weather") or {}).get("temperature") or 0)
        climate = "cold" if temperature < 8 else "hot" if temperature > 30 else "temperate"
        result = post_blueprint(client, map_id, {"x": int(plan["x"]), "z": int(plan["z"])}, mountain_bedroom_furnishing(powered="Electricity" in set(map(str, snapshot["development"].get("finished_research", []))), climate=climate))
        plan["furnished"] = True
        issued["mountain_bedroom_furnish"] = tick
        return {"applied": True, "response": result}
    if choice == "commission_sculptures":
        tables = [row for row in snapshot["development"].get("work_tables", []) if row.get("thing_def") == "TableSculpting"]
        if not tables:
            material = str((map_state.get("doctrine") or {}).get("material") or "WoodLog")
            if material not in {"WoodLog", "Steel"} and not material.startswith("Blocks"):
                material = "WoodLog"
            result = post_blueprint(client, map_id, anchor, workshop_blueprint("TableSculpting", stuff=material), dx=18, dz=24)
        else:
            result = ensure_bill(client, tables[0], "Make_SculptureSmall", 4)
        issued["commission_sculptures"] = tick
        return {"applied": True, "response": result, "art_work": prioritize(client, snapshot, "Art")}
    if choice == "install_sculpture":
        key = str(details.get("sculpture_install_plan") or "")
        plan = (details.get("sculpture_install_options") or {}).get(key)
        if not plan:
            return {"applied": False, "reason": "Laya did not select a valid sculpture and room"}
        cells = plan.get("cells") or []
        target = cells[len(cells) // 2] if cells else None
        if not target:
            return {"applied": False, "reason": "Selected room has no installation cell"}
        result = client.post("/api/v1/builder/install-minified", body={"map_id": map_id, "thing_id": int(plan["thing_id"]), "position": target, "rotation": 0})
        issued["install_sculpture"] = tick
        return {"applied": True, "room": plan.get("room_role"), "response": result}
    if choice == "build_weapon_shelves":
        shelf_ids = list(map(int, details.get("weapon_shelf_ids") or []))
        if shelf_ids:
            result = client.post("/api/v1/builder/storage/configure", body={"map_id": map_id, "building_ids": shelf_ids, "allowed_item_categories": ["Weapons"], "allowed_item_defs": [], "priority": 4})
            map_state["weapon_shelves_configured"] = True
            return {"applied": True, "phase": "configure", "response": result}
        material = str((map_state.get("doctrine") or {}).get("material") or "WoodLog")
        if material.startswith("Blocks"):
            material = "WoodLog"
        result = post_blueprint(client, map_id, anchor, weapon_shelves_blueprint(material), dx=-8, dz=9)
        issued["weapon_shelves"] = tick
        return {"applied": True, "phase": "build", "response": result}
    if choice == "prioritize_armament":
        unarmed = [p for p in snapshot.get("combat", {}).get("colonists", []) if not p.get("has_ranged_weapon") and not p.get("is_dead") and not p.get("is_downed")]
        weapons = [w for w in snapshot.get("combat", {}).get("available_weapons", []) if w.get("is_ranged")]
        responses = []
        for pawn, weapon in zip(unarmed, weapons):
            if weapon.get("is_forbidden"):
                responses.append(client.post("/api/v1/things/set-forbidden", body={"map_id": map_id, "thing_ids": [int(weapon["id"])], "forbidden": False}))
            responses.append(client.post("/api/v1/pawn/job", body={"pawn_id": int(pawn["id"]), "job_def": "Equip", "target_thing_id": int(weapon["id"])}))
        issued["armament"] = tick
        if responses:
            return {"applied": True, "phase": "equip", "responses": responses}
        target = next_research(client, set(map(str, snapshot["development"].get("finished_research", []))), map_state)
        return {"applied": bool(target), "phase": "research", "response": select_research_if_available(client, target) if target else None}
    if choice == "build_animal_barn":
        options = details.get("animal_barn_options") or {}
        material = str(details.get("animal_barn_material") or (map_state.get("doctrine") or {}).get("material") or "WoodLog")
        floor_choice = str(details.get("animal_barn_floor") or "bare")
        result = post_blueprint(client, map_id, anchor, animal_barn_blueprint(material, int(options.get("animal_count") or len(snapshot.get("animals", []))), straw_floor=floor_choice == "straw", powered="Electricity" in set(map(str, snapshot["development"].get("finished_research", []))), climate=str(options.get("climate") or "temperate")), dx=-22, dz=18)
        issued["animal_barn"] = tick
        return {"applied": True, "material": material, "floor": floor_choice, "response": result}
    if choice in {"pause_late_sowing", "resume_seasonal_sowing"}:
        allow = choice == "resume_seasonal_sowing"
        responses = [client.post("/api/v1/map/zone/growing/sowing", body={"map_id": map_id, "zone_id": int(zone_id), "allow_sow": allow}) for zone_id in details.get("sowing_zone_ids") or []]
        issued[choice] = tick
        return {"applied": bool(responses), "allow_sow": allow, "responses": responses}

    if choice == "unforbid_supplies":
        ids = [int(row["thing_id"]) for row in relevant_forbidden(snapshot) if row.get("thing_id") is not None]
        if not ids:
            return {"applied": False, "reason": "No forbidden supplies remain"}
        result = client.post(
            "/api/v1/things/set-forbidden",
            body={"map_id": map_id, "thing_ids": ids, "forbidden": False},
        )
        issued["unforbid_supplies"] = tick
        return {"applied": True, "stacks_unforbidden": len(ids), "response": result}
    if choice == "unforbid_corpses":
        ids = [int(row["thing_id"]) for row in forbidden_corpses(snapshot) if row.get("thing_id") is not None]
        if not ids:
            return {"applied": False, "reason": "No forbidden corpses remain"}
        result = client.post(
            "/api/v1/things/set-forbidden",
            body={"map_id": map_id, "thing_ids": ids, "forbidden": False},
        )
        issued["unforbid_corpses"] = tick
        return {"applied": True, "corpses_unforbidden": len(ids), "response": result}
    if choice == "build_cemetery":
        result = post_blueprint(
            client,
            map_id,
            anchor,
            cemetery_blueprint(int(details.get("grave_count") or 8)),
            dx=-12,
            dz=14,
        )
        issued["cemetery"] = tick
        return result
    if choice == "create_human_corpse_dump":
        dump_x = max(6, min(240, int(anchor["x"]) + (50 if int(anchor["x"]) < 125 else -50)))
        dump_z = max(6, min(240, int(anchor["z"]) + (45 if int(anchor["z"]) < 125 else -45)))
        terrain = client.get("/api/v1/map/terrain", map_id=map_id)
        dump_anchor = find_terrain_rect(
            terrain, {"x": dump_x, "z": dump_z}, 6, 6,
            {"Soil", "SoilRich", "Gravel", "Sand", "MarshyTerrain"}, radius=35,
        ) or {"x": dump_x, "z": dump_z}
        dump_x, dump_z = int(dump_anchor["x"]), int(dump_anchor["z"])
        result = client.post("/api/v1/map/zone/stockpile", body={
            "map_id": map_id,
            "point_a": position(dump_x, dump_z),
            "point_b": position(dump_x + 5, dump_z + 5),
            "name": "Laya Human Corpse Dump",
            "priority": 5,
            "allowed_item_categories": ["CorpsesHumanlike"],
        })
        issued["human_corpse_dump"] = tick
        return {"applied": True, "distance_from_base": abs(dump_x - int(anchor["x"])) + abs(dump_z - int(anchor["z"])), "response": result}
    if choice == "create_animal_corpse_dump":
        result = client.post("/api/v1/map/zone/stockpile", body={
            "map_id": map_id,
            "point_a": position(anchor["x"] + 15, anchor["z"] + 7),
            "point_b": position(anchor["x"] + 19, anchor["z"] + 10),
            "name": "Laya Animal Carcasses",
            "priority": 5,
            "allowed_item_categories": ["CorpsesAnimal"],
        })
        issued["animal_corpse_dump"] = tick
        return result
    if choice == "create_stone_chunk_dump":
        near = details.get("stone_dump_anchor") or anchor
        x, z = int((near or {}).get("x") or anchor["x"]), int((near or {}).get("z") or anchor["z"])
        result = client.post("/api/v1/map/zone/stockpile", body={
            "map_id": map_id,
            "point_a": position(x + 2, z - 2),
            "point_b": position(x + 5, z + 2),
            "name": "Laya Stone Chunks",
            "priority": 3,
            "allowed_item_categories": ["StoneChunks"],
        })
        issued["stone_chunk_dump"] = tick
        return result
    if choice == "build_crematorium":
        tables = [row for row in snapshot["development"].get("work_tables", []) if row.get("thing_def") == "ElectricCrematorium"]
        if tables:
            result = ensure_bill(client, tables[0], "CremateCorpse", 25)
            issued["crematorium_bill"] = tick
            return {"applied": True, "phase": "configure", "response": result}
        stuff = str(details.get("crematorium_stuff") or "BlocksGranite")
        result = post_blueprint(client, map_id, anchor, workshop_blueprint("ElectricCrematorium", stuff=stuff), dx=-18, dz=19)
        issued["crematorium"] = tick
        return {"applied": True, "phase": "build", "stuff": stuff, "response": result}
    if choice == "build_prison":
        result = post_blueprint(client, map_id, anchor, prison_blueprint(), dx=-12, dz=-8)
        issued["prison_blueprint"] = tick
        return {"applied": True, "blueprint": result, "construction": prioritize(client, snapshot, "Construction")}
    if choice == "build_hospital":
        result = post_blueprint(client, map_id, anchor, hospital_blueprint(), dx=25, dz=0)
        issued["hospital_blueprint"] = tick
        return {"applied": True, "blueprint": result, "construction": prioritize(client, snapshot, "Construction")}
    if choice == "configure_hospital_beds":
        generated_hospitals = [
            row for row in map_state.get("architecture_projects", [])
            if row.get("program") == "hospital"
        ]
        if generated_hospitals:
            hospital = generated_hospitals[-1]
            start = hospital["origin"]
            point_a = position(int(start["x"]), int(start["z"]))
            point_b = position(
                int(start["x"]) + int(hospital["width"]) - 1,
                int(start["z"]) + int(hospital["height"]) - 1,
            )
        else:
            point_a = position(anchor["x"] + 25, anchor["z"])
            point_b = position(anchor["x"] + 31, anchor["z"] + 6)
        result = client.post("/api/v1/map/beds/configure", body={
            "map_id": map_id,
            "point_a": point_a,
            "point_b": point_b,
            "medical": True,
            "for_prisoners": False,
        })
        issued["hospital_beds"] = tick
        return result
    if choice == "floor_critical_room":
        plan_key = str(details.get("critical_floor_plan") or "")
        plan = (details.get("critical_floor_options") or {}).get(plan_key)
        if not plan:
            return {"applied": False, "reason": "Laya did not select an available critical-room floor plan"}
        layout, origin = room_floor_blueprint(plan["cells"], str(plan["floor_def"]))
        result = client.post("/api/v1/builder/blueprint", body={
            "map_id": map_id,
            "position": position(origin["x"], origin["z"]),
            "blueprint": layout,
            "clear_obstacles": False,
        })
        issued[f"floor_room:{int(plan['room_id'])}"] = tick
        issued["critical_floor"] = tick
        return {"applied": True, "plan": plan_key, "cost": plan.get("cost"), "response": result}
    if choice == "build_pathways":
        material = str(details.get("path_material") or "")
        if material not in (details.get("path_floor_options") or {}):
            return {"applied": False, "reason": "Laya did not select an affordable path material"}
        layout, origin = pathway_blueprint(material, anchor, map_state.get("growing_anchor") or anchor)
        result = client.post("/api/v1/builder/blueprint", body={
            "map_id": map_id,
            "position": position(origin["x"], origin["z"]),
            "blueprint": layout,
            "clear_obstacles": False,
        })
        issued["pathways"] = tick
        return {"applied": True, "material": material, "response": result}
    if choice == "build_temple":
        altar = str(details.get("temple_altar") or "")
        material = str(details.get("temple_material") or "")
        options = details.get("temple_options") or {}
        if altar not in (options.get("altars") or {}) or material not in (options.get("materials") or {}):
            return {"applied": False, "reason": "Laya did not select a valid ideology altar and affordable material"}
        result = post_blueprint(client, map_id, anchor, temple_blueprint(altar, material), dx=35, dz=17)
        issued["temple"] = tick
        return {"applied": True, "altar": altar, "material": material, "response": result}
    if choice == "prioritize_burial":
        result = prioritize(client, snapshot, "Hauling", details.get("worker_pawn"))
        issued["priority:Burial"] = tick
        issued["priority:Hauling"] = tick
        return result
    if choice == "create_food_stockpile":
        result = client.post("/api/v1/map/zone/stockpile", body={
            "map_id": map_id,
            "point_a": position(anchor["x"] + 1, anchor["z"] + 1),
            "point_b": position(anchor["x"] + 4, anchor["z"] + 4),
            "name": "Laya Food Freezer",
            "priority": 2,
            "allowed_item_categories": ["FoodMeals", "FoodRaw"],
        })
        issued["food_stockpile"] = tick
        return result
    if choice == "build_sleeping_spots":
        result = post_blueprint(
            client,
            map_id,
            anchor,
            sleeping_spots_blueprint(len(snapshot["colonists"])),
            dx=1,
            dz=8,
        )
        issued["sleeping_spots"] = tick
        return result
    if choice == "build_basic_beds":
        count = int(details.get("basic_bed_count") or len(snapshot["colonists"]))
        result = post_blueprint(client, map_id, anchor, basic_beds_blueprint(count), dx=1, dz=11)
        issued["basic_beds"] = tick
        return {"applied": True, "beds": count, "response": result}
    if choice == "build_animal_spots":
        animals = [animal for animal in snapshot.get("animals", []) if not animal.get("dead")]
        result = post_blueprint(
            client,
            map_id,
            anchor,
            animal_spots_blueprint(len(animals)),
            dx=9,
            dz=8,
        )
        issued["animal_spots"] = tick
        return result
    if choice == "care_for_injured_animal":
        animal_id = int(details["injured_animal_id"])
        animal = next((row for row in snapshot.get("animals", []) if int(row.get("id", -1)) == animal_id), None)
        doctor = bridge.choose_worker(snapshot["colonists"], "Doctor")
        beds = [
            row for row in snapshot["development"]["buildings"]
            if isinstance(row, dict) and row.get("def") == "AnimalSleepingSpot"
        ]
        responses: list[Any] = []
        errors: list[str] = []
        bed = None
        if beds and animal:
            ax = float((animal.get("position") or {}).get("x") or 0)
            az = float((animal.get("position") or {}).get("z") or 0)
            bed = min(beds, key=lambda row: (
                float((row.get("position") or {}).get("x") or 0) - ax
            ) ** 2 + (
                float((row.get("position") or {}).get("z") or 0) - az
            ) ** 2)
        if bed and animal and animal.get("downed") and doctor is not None:
            bed_pos = bed.get("position") or {}
            animal_pos = animal.get("position") or {}
            distance = abs(int(bed_pos.get("x") or 0) - int(animal_pos.get("x") or 0)) + abs(
                int(bed_pos.get("z") or 0) - int(animal_pos.get("z") or 0)
            )
            if distance > 1:
                try:
                    responses.append(client.post(
                        "/api/v1/pawn/job",
                        body={
                            "pawn_id": int(doctor["id"]),
                            "job_def": "Rescue",
                            "target_thing_id": animal_id,
                            "target_thing_id_b": int(bed["id"]),
                        },
                    ))
                    issued[f"animal_care:{animal_id}"] = tick
                    return {
                        "applied": True,
                        "animal": details.get("injured_animal_name", animal_id),
                        "doctor": doctor.get("name"),
                        "phase": "rescue_to_animal_bed",
                        "responses": responses,
                        "errors": errors,
                    }
                except bridge.RimApiError as exc:
                    errors.append(str(exc))
        if bed and animal and not animal.get("downed"):
            try:
                responses.append(client.post(
                    "/api/v1/pawn/medical/bed-rest",
                    body={"patient_pawn_id": animal_id, "bed_building_id": int(bed["id"])},
                ))
            except bridge.RimApiError as exc:
                errors.append(str(exc))
        tend_body: dict[str, Any] = {"patient_pawn_id": animal_id}
        if doctor is not None:
            tend_body["doctor_pawn_id"] = int(doctor["id"])
        try:
            responses.append(client.post("/api/v1/pawn/medical/tend", body=tend_body))
        except bridge.RimApiError as exc:
            errors.append(str(exc))
        issued[f"animal_care:{animal_id}"] = tick
        return {
            "applied": bool(responses),
            "animal": details.get("injured_animal_name", animal_id),
            "doctor": doctor.get("name") if doctor else "automatic",
            "responses": responses,
            "errors": errors,
        }
    if choice == "feed_hungry_animal":
        animal_id = int(details["hungry_animal_id"])
        feeder = bridge.choose_worker(snapshot["colonists"], "Handling") or bridge.choose_worker(snapshot["colonists"], "Doctor")
        body: dict[str, Any] = {"patient_pawn_id": animal_id}
        if feeder is not None:
            body["feeder_pawn_id"] = int(feeder["id"])
        try:
            response = client.post("/api/v1/pawn/medical/feed", body=body)
        except bridge.RimApiError as exc:
            # The patient's state can change between observation and execution
            # (for example, an animal stands up and can eat by itself). Treat that
            # race as a skipped order instead of crashing every following cycle.
            issued[f"animal_feed:{animal_id}"] = tick
            return {
                "applied": False,
                "skipped": "patient_feeding_unavailable",
                "animal": details.get("hungry_animal_name", animal_id),
                "feeder": feeder.get("name") if feeder else "automatic",
                "error": str(exc),
            }
        issued[f"animal_feed:{animal_id}"] = tick
        return {
            "applied": True,
            "animal": details.get("hungry_animal_name", animal_id),
            "feeder": feeder.get("name") if feeder else "automatic",
            "response": response,
        }
    if choice == "feed_hungry_colonist":
        patient_id = int(details["hungry_colonist_id"])
        feeder = bridge.choose_worker(snapshot["colonists"], "Doctor") or bridge.choose_worker(snapshot["colonists"], "BasicWorker")
        body: dict[str, Any] = {"patient_pawn_id": patient_id}
        if feeder is not None and int(feeder.get("id", -1)) != patient_id:
            body["feeder_pawn_id"] = int(feeder["id"])
        try:
            response = client.post("/api/v1/pawn/medical/feed", body=body)
        except bridge.RimApiError as exc:
            issued[f"colonist_feed:{patient_id}"] = tick
            return {
                "applied": False,
                "skipped": "patient_feeding_unavailable",
                "colonist": details.get("hungry_colonist_name", patient_id),
                "feeder": feeder.get("name") if feeder else "automatic",
                "error": str(exc),
            }
        issued[f"colonist_feed:{patient_id}"] = tick
        return {
            "applied": True,
            "colonist": details.get("hungry_colonist_name", patient_id),
            "feeder": feeder.get("name") if feeder else "automatic",
            "response": response,
        }
    if choice == "build_freezer":
        result = post_blueprint(client, map_id, anchor, freezer_blueprint(include_generator=bool(details.get("freezer_include_generator", True))))
        issued["freezer"] = tick
        return result
    if choice == "create_stockpile":
        result = client.post("/api/v1/map/zone/stockpile", body={
            "map_id": map_id,
            "point_a": position(anchor["x"] - 8, anchor["z"] + 1),
            "point_b": position(anchor["x"] - 3, anchor["z"] + 6),
            "name": "Laya Main Stockpile",
            "priority": 1,
        })
        issued["stockpile"] = tick
        return result
    if choice == "expand_stockpile":
        expansion_index = int(map_state.get("stockpile_expansions") or 0)
        result = client.post("/api/v1/map/zone/stockpile", body={
            "map_id": map_id,
            "point_a": position(anchor["x"] - 15 - expansion_index * 7, anchor["z"] + 1),
            "point_b": position(anchor["x"] - 10 - expansion_index * 7, anchor["z"] + 6),
            "name": f"Laya Main Stockpile {expansion_index + 2}",
            "priority": 1,
        })
        map_state["stockpile_expansions"] = expansion_index + 1
        issued["expand_stockpile"] = tick
        return result
    if choice == "create_growing_zone":
        growing_anchor = map_state.get("growing_anchor", anchor)
        result = client.post("/api/v1/map/zone/growing", body={
            "map_id": map_id,
            "plant_def": "Plant_Rice",
            "point_a": position(growing_anchor["x"], growing_anchor["z"]),
            "point_b": position(growing_anchor["x"] + 9, growing_anchor["z"] + 7),
        })
        issued["growing"] = tick
        return result
    if choice == "build_starter_base":
        result = post_blueprint(client, map_id, anchor, starter_base_blueprint(len(snapshot["colonists"])), dx=12, dz=0)
        issued["starter_base"] = tick
        return result
    if choice == "configure_food_bills":
        result = configure_food_bills(client, snapshot["development"]["work_tables"])
        issued["food_bills"] = tick
        return result
    if choice == "advance_research":
        target = details["research_target"]
        result = client.post("/api/v1/research/target", query={"name": target, "force": False})
        issued[f"research:{target}"] = tick
        return result
    if choice == "advance_doctrine_research":
        target = str(details.get("doctrine_research_target") or "")
        if target not in (details.get("doctrine_research_options") or {}):
            return {"applied": False, "reason": "Laya did not select a live doctrine research project"}
        result = client.post("/api/v1/research/target", query={"name": target, "force": False})
        issued[f"research:{target}"] = tick
        return {"applied": True, "target": target, "doctrine": map_state.get("doctrine"), "response": result}
    if choice == "build_power":
        result = post_blueprint(client, map_id, anchor, power_blueprint(), dx=1, dz=13)
        issued["power"] = tick
        return result
    if choice == "build_hitech_lab":
        result = post_blueprint(client, map_id, anchor, hitech_blueprint(), dx=10, dz=13)
        issued["hitech"] = tick
        return result
    if choice == "build_fabrication":
        result = post_blueprint(client, map_id, anchor, fabrication_blueprint(), dx=19, dz=13)
        issued["fabrication"] = tick
        return result
    if choice == "build_ship":
        result = post_blueprint(client, map_id, anchor, ship_blueprint(len(snapshot["colonists"])), dx=-5, dz=25)
        issued["ship"] = tick
        return result
    if choice.startswith("human_reproduction:"):
        _, first_id, second_id, approach = choice.split(":", 3)
        first_id_int, second_id_int = int(first_id), int(second_id)
        responses: list[Any] = []
        if approach == "TryForBaby" and snapshot["development"]["building_counts"].get("DoubleBed", 0) == 0:
            if not issued_recently(map_state, "reproduction_double_bed", tick, retry_ticks=60000):
                responses.append(post_blueprint(
                    client, map_id, anchor,
                    workshop_blueprint("DoubleBed", stuff="WoodLog"), dx=7, dz=5,
                ))
                issued["reproduction_double_bed"] = tick
        responses.append(client.post("/api/v1/map/colonists/reproduction", body={
            "map_id": map_id,
            "first_pawn_id": first_id_int,
            "second_pawn_id": second_id_int,
            "approach": approach,
        }))
        issued[f"human_reproduction:{first_id_int}:{second_id_int}"] = tick
        map_state["human_reproduction_plan"] = {
            "first": first_id_int, "second": second_id_int, "approach": approach,
        }
        return {"applied": True, "approach": approach, "responses": responses}
    if choice.startswith("income_"):
        income_strategy = choice.removeprefix("income_")
        strategy_names = {
            "drugs": "drugs", "tailoring": "tailoring", "art": "art",
            "livestock": "livestock", "biofuel": "biofuel", "mining": "mining",
            "crops": "crops", "brewing": "brewing", "travel_food": "travel_food",
            "orbital": "orbital", "organs": "organs",
        }
        if income_strategy not in strategy_names:
            raise bridge.RimApiError(f"Unknown income strategy: {income_strategy}")
        map_state["income_strategy"] = strategy_names[income_strategy]
        map_state["income_strategy_tick"] = tick
        issued[f"income:{income_strategy}"] = tick
        if income_strategy == "drugs":
            response = client.post("/api/v1/map/zone/growing", body={
                "map_id": map_id,
                "plant_def": "Plant_Psychoid",
                "point_a": position(map_state["growing_anchor"]["x"], map_state["growing_anchor"]["z"] + 10),
                "point_b": position(map_state["growing_anchor"]["x"] + 9, map_state["growing_anchor"]["z"] + 17),
            })
            return {"applied": True, "strategy": income_strategy, "response": response}
        if income_strategy == "tailoring":
            grow = client.post("/api/v1/map/zone/growing", body={
                "map_id": map_id,
                "plant_def": "Plant_Cotton",
                "point_a": position(map_state["growing_anchor"]["x"] + 11, map_state["growing_anchor"]["z"] + 10),
                "point_b": position(map_state["growing_anchor"]["x"] + 18, map_state["growing_anchor"]["z"] + 17),
            })
            bench = post_blueprint(client, map_id, anchor, workshop_blueprint("HandTailoringBench", stuff="WoodLog"), dx=16, dz=12)
            return {"applied": True, "strategy": income_strategy, "responses": [grow, bench]}
        if income_strategy == "art":
            response = post_blueprint(client, map_id, anchor, workshop_blueprint("TableSculpting", stuff="WoodLog"), dx=16, dz=16)
            return {"applied": True, "strategy": income_strategy, "response": response}
        if income_strategy == "livestock":
            return {"applied": True, "strategy": income_strategy, "response": prioritize(client, snapshot, "Handling")}
        if income_strategy == "biofuel":
            response = select_research_if_available(client, "BiofuelRefining")
            return {"applied": bool(response.get("applied", True)), "strategy": income_strategy, "response": response}
        if income_strategy == "crops":
            response = client.post("/api/v1/map/zone/growing", body={
                "map_id": map_id,
                "plant_def": "Plant_Corn",
                "point_a": position(map_state["growing_anchor"]["x"] + 20, map_state["growing_anchor"]["z"]),
                "point_b": position(map_state["growing_anchor"]["x"] + 29, map_state["growing_anchor"]["z"] + 9),
            })
            return {"applied": True, "strategy": income_strategy, "response": response}
        if income_strategy == "brewing":
            grow = client.post("/api/v1/map/zone/growing", body={
                "map_id": map_id,
                "plant_def": "Plant_Hops",
                "point_a": position(map_state["growing_anchor"]["x"] + 20, map_state["growing_anchor"]["z"] + 11),
                "point_b": position(map_state["growing_anchor"]["x"] + 27, map_state["growing_anchor"]["z"] + 18),
            })
            research = select_research_if_available(client, "Brewing")
            return {"applied": True, "strategy": income_strategy, "responses": [grow, research]}
        if income_strategy == "travel_food":
            research = select_research_if_available(client, "PackagedSurvivalMeal")
            if not research.get("applied", True):
                research = select_research_if_available(client, "Pemmican")
            return {"applied": True, "strategy": income_strategy, "response": research}
        if income_strategy == "orbital":
            research = select_research_if_available(client, "MicroelectronicsBasics")
            return {"applied": bool(research.get("applied", True)), "strategy": income_strategy, "response": research}
        if income_strategy == "organs":
            return {
                "applied": True,
                "strategy": income_strategy,
                "note": "Organ harvesting remains per-prisoner and is offered only with doctor skill 8+, medicine, and explicit Laya selection.",
            }
        # Mine the compact local gold vein first. Long-range scanning is added to
        # the research route after local precious ore is exhausted.
        ores = snapshot["development"].get("ores", {}).get("ores", {})
        vein = ores.get("mineable_gold") or ores.get("mineable_silver") or {}
        cells = [int(value) for value in vein.get("cells", [])[:16]]
        if cells:
            width = int(snapshot["development"].get("ores", {}).get("map_width") or 250)
            xs = [cell % width for cell in cells]
            zs = [cell // width for cell in cells]
            response = client.post("/api/v1/order/designate/area", body={
                "map_id": map_id,
                "type": "mine",
                "point_a": position(min(xs), min(zs)),
                "point_b": position(max(xs), max(zs)),
            })
        else:
            response = select_research_if_available(client, "LongRangeMineralScanner")
        return {"applied": True, "strategy": income_strategy, "response": response}
    if choice == "build_income_infrastructure":
        income_strategy = str(map_state.get("income_strategy") or "")
        if income_strategy == "drugs":
            response = post_blueprint(client, map_id, anchor, workshop_blueprint("DrugLab"), dx=21, dz=16)
        elif income_strategy == "biofuel":
            response = post_blueprint(client, map_id, anchor, workshop_blueprint("BiofuelRefinery"), dx=21, dz=20)
        elif income_strategy == "brewing":
            layout = blueprint([
                building("Brewery", 0, 0, rotation=2),
                building("FermentingBarrel", 4, 0),
                building("FermentingBarrel", 5, 0),
                building("FermentingBarrel", 6, 0),
            ], 8, 3)
            response = post_blueprint(client, map_id, anchor, layout, dx=21, dz=24)
        elif income_strategy == "orbital":
            response = post_blueprint(client, map_id, anchor, orbital_trade_blueprint(), dx=21, dz=28)
        else:
            return {"applied": False, "reason": f"No separate infrastructure is required for {income_strategy}"}
        issued[f"income_infrastructure:{income_strategy}"] = tick
        return {"applied": True, "strategy": income_strategy, "response": response}
    if choice == "configure_income_production":
        income_strategy = str(map_state.get("income_strategy") or "")
        recipe_by_strategy = {
            "drugs": ("DrugLab", "Make_Flake", 50),
            "tailoring": ("HandTailoringBench", "Make_Duster", 10),
            "art": ("TableSculpting", "Make_SculptureSmall", 8),
            "biofuel": ("BiofuelRefinery", "Make_ChemfuelFromOrganics", 150),
            "brewing": ("Brewery", "Make_Wort", 50),
            "travel_food": ("FueledStove", "CookMealSurvivalPack", 30),
        }
        table_def, recipe, target = recipe_by_strategy[income_strategy]
        table = next(
            (row for row in snapshot["development"]["work_tables"] if str(row.get("thing_def")) == table_def),
            None,
        )
        if table is None and income_strategy == "tailoring":
            table = next((row for row in snapshot["development"]["work_tables"] if row.get("thing_def") == "ElectricTailoringBench"), None)
        if table is None and income_strategy == "travel_food":
            table = next((row for row in snapshot["development"]["work_tables"] if row.get("thing_def") == "ElectricStove"), None)
        if table is None:
            return {"applied": False, "reason": f"No completed workshop for {income_strategy}"}
        response = ensure_bill(client, table, recipe, target)
        issued[f"income_bills:{income_strategy}"] = tick
        return {"applied": True, "strategy": income_strategy, "response": response}
    if choice == "build_killbox":
        response = post_blueprint(client, map_id, anchor, killbox_blueprint(), dx=13, dz=-16)
        issued["killbox"] = tick
        return response
    if choice == "build_fallback_defense":
        response = post_blueprint(client, map_id, anchor, fallback_defense_blueprint(), dx=12, dz=-6)
        issued["fallback_defense"] = tick
        return response
    if choice == "build_turret_defense":
        response = post_blueprint(client, map_id, anchor, turret_defense_blueprint(), dx=12, dz=-10)
        issued["turret_defense"] = tick
        return response
    if choice == "build_mortar_post":
        response = post_blueprint(client, map_id, anchor, mortar_post_blueprint(), dx=-20, dz=-12)
        issued["mortar_post"] = tick
        return response
    if choice == "build_firefoam_defense":
        response = post_blueprint(client, map_id, anchor, workshop_blueprint("FirefoamPopper"), dx=5, dz=10)
        issued["firefoam_defense"] = tick
        return response
    if choice == "start_stonecutting":
        stone_type = str(details.get("stone_type") or map_state.get("stone_type") or "")
        if not stone_type:
            return {"applied": False, "reason": "Laya did not select a nearby stone type"}
        map_state["stone_type"] = stone_type
        finished = set(map(str, snapshot["development"]["finished_research"]))
        tables = [row for row in snapshot["development"]["work_tables"] if row.get("thing_def") == "TableStonecutter"]
        if "Stonecutting" not in finished:
            response = select_research_if_available(client, "Stonecutting")
            return {"applied": bool(response.get("applied", True)), "stone_type": stone_type, "phase": "research", "response": response}
        if not tables:
            response = post_blueprint(client, map_id, anchor, workshop_blueprint("TableStonecutter", stuff="WoodLog"), dx=16, dz=20)
            issued["stonecutting_table"] = tick
            return {"applied": True, "stone_type": stone_type, "phase": "build_table", "response": response}
        block_name = stone_type.removeprefix("Chunk")
        response = ensure_bill(client, tables[0], f"CutStoneBlocks_{block_name}", 300)
        issued["stonecutting_complete"] = tick
        return {"applied": True, "stone_type": stone_type, "phase": "bill", "response": response}
    if choice == "start_taming":
        animal_id = details.get("tame_target")
        animal = next((a for a in details.get("tame_options", []) if int(a.get("id", -1)) == int(animal_id or -1)), None)
        if animal is None:
            return {"applied": False, "reason": "Laya did not select an available taming target"}
        response = client.post("/api/v1/map/animal/tame", body={"map_id": map_id, "animal_id": int(animal_id)})
        issued[f"tame:{animal_id}"] = tick
        issued["priority:Handling"] = tick
        handling = prioritize(client, snapshot, "Handling")
        return {"applied": True, "animal": animal, "responses": [response, handling]}
    if choice.startswith("breed_animals:"):
        species = choice.split(":", 1)[1]
        issued[f"breed:{species}"] = tick
        map_state["animal_breeding_plan"] = species
        return {"applied": True, "species": species, "response": prioritize(client, snapshot, "Handling")}
    if choice == "process_mechanoids":
        tables = [row for row in snapshot["development"]["work_tables"] if row.get("thing_def") == "TableMachining"]
        if tables:
            response = ensure_bill(client, tables[0], "SmashCorpseMechanoid", 10)
        elif "Machining" in set(map(str, snapshot["development"]["finished_research"])):
            response = post_blueprint(client, map_id, anchor, workshop_blueprint("TableMachining", stuff="Steel"), dx=21, dz=12)
        else:
            response = select_research_if_available(client, "Machining")
        issued["mech_processing"] = tick
        return {"applied": True, "response": response}
    if choice.startswith("prisoner_policy:"):
        _, pawn_id_text, policy = choice.split(":", 2)
        pawn_id = int(pawn_id_text)
        if policy in {"organs_nonlethal", "organs_lethal"}:
            organs = ["Kidney", "Lung"] if policy == "organs_nonlethal" else ["Heart"]
            responses = [
                client.post("/api/v1/pawn/prisoner/organ-plan", body={
                    "prisoner_pawn_id": pawn_id,
                    "organ_def_name": organ,
                    "allow_lethal": policy == "organs_lethal",
                })
                for organ in organs
            ]
            map_state.setdefault("prisoner_plans", {})[str(pawn_id)] = policy
            issued[f"prisoner:{pawn_id}:{policy}"] = tick
            return {"applied": True, "prisoner_id": pawn_id, "policy": policy, "organs": organs, "responses": responses}
        response = client.post("/api/v1/pawn/prisoner/policy", body={
            "prisoner_pawn_id": pawn_id,
            "policy": policy,
        })
        map_state.setdefault("prisoner_plans", {})[str(pawn_id)] = policy
        issued[f"prisoner:{pawn_id}:{policy}"] = tick
        return {"applied": True, "prisoner_id": pawn_id, "policy": policy, "response": response}
    if choice.startswith("trade_to:"):
        _, destination_id, sale = choice.split(":", 2)
        sale_categories = available_sale_categories(snapshot) if sale == "mixed" else [sale]
        purchase = str(details.get("trade_purchase") or "none")
        sale_prisoner_ids = [
            int(pawn_id) for pawn_id, policy in (map_state.get("prisoner_plans") or {}).items()
            if policy == "sell" and any(int(p.get("id", -1)) == int(pawn_id) for p in snapshot.get("combat", {}).get("prisoners", []))
        ]
        response = client.post("/api/v1/world/caravan/trade/start", body={
            "map_id": map_id,
            "destination_settlement_id": int(destination_id),
            "minimum_home_defenders": 2,
            "minimum_food_at_home": 20,
            "minimum_medicine_at_home": 8,
            "sale_categories": sale_categories,
            "purchase_priorities": [] if purchase == "none" else [purchase],
            "prisoner_ids": sale_prisoner_ids,
        })
        issued["trade_caravan"] = tick
        map_state["caravan_plan"] = {"kind": "trade", "destination_id": int(destination_id), "purchase": purchase}
        return response
    if choice.startswith("raid_to:"):
        destination_id = int(choice.split(":", 1)[1])
        destination = next((d for d in snapshot["development"].get("raid_destinations", []) if int(d.get("settlement_id", -1)) == destination_id), {})
        response = client.post("/api/v1/world/caravan/raid/start", body={
            "map_id": map_id,
            "destination_settlement_id": destination_id,
            "minimum_home_defenders": 2,
            "minimum_food_at_home": 30,
            "minimum_medicine_at_home": 10,
            "allow_starting_war": bool(destination.get("would_start_war")),
        })
        issued["raid_caravan"] = tick
        map_state["caravan_plan"] = {"kind": "raid", "destination_id": destination_id}
        return response
    if choice == "prepare_trade_caravan":
        # The endpoint refuses unsafe parties and keeps at least two healthy
        # defenders, food and medicine at home.
        destination = next((row for row in snapshot["development"].get("trade_destinations", []) if row.get("can_trade_now")), None)
        if destination is None:
            return {"applied": False, "reason": "No safe trading destination is currently available"}
        response = client.post("/api/v1/world/caravan/trade/start", body={
            "map_id": map_id,
            "destination_settlement_id": int(destination["settlement_id"]),
            "minimum_home_defenders": 2,
            "minimum_food_at_home": 20,
            "minimum_medicine_at_home": 8,
        })
        issued["trade_caravan"] = tick
        return response
    if choice == "prioritize_construction":
        result = prioritize(client, snapshot, "Construction", details.get("worker_pawn"))
        issued["priority:Construction"] = tick
        return result
    if choice == "prioritize_construction_project":
        project_id = details.get("construction_project")
        worker_id = details.get("worker_pawn")
        if project_id is None or worker_id is None:
            return {"applied": False, "reason": "Laya did not select both an exact project and builder"}
        priority = prioritize(client, snapshot, "Construction", int(worker_id))
        response = client.post("/api/v1/builder/prioritize", body={
            "map_id": map_id,
            "project_thing_id": int(project_id),
            "pawn_id": int(worker_id),
        })
        issued["construction_project_priority"] = tick
        return {"applied": True, "project_id": int(project_id), "builder_id": int(worker_id), "responses": [priority, response]}
    if choice == "prioritize_research":
        result = prioritize(client, snapshot, "Research")
        issued["priority:Research"] = tick
        return result
    if choice == "prioritize_cooking":
        result = prioritize(client, snapshot, "Cooking")
        issued["priority:Cooking"] = tick
        return result
    if choice == "prioritize_growing":
        result = prioritize(client, snapshot, "Growing")
        issued["priority:Growing"] = tick
        return result
    if choice == "prioritize_hauling":
        result = prioritize(client, snapshot, "Hauling")
        issued["priority:Hauling"] = tick
        return result
    if choice == "prioritize_hunting":
        result = prioritize(client, snapshot, "Hunting")
        issued["priority:Hunting"] = tick
        return result
    if choice == "prioritize_handling":
        result = prioritize(client, snapshot, "Handling")
        issued["priority:Handling"] = tick
        return result
    if choice == "prioritize_plant_cutting":
        result = prioritize(client, snapshot, "PlantCutting")
        issued["priority:PlantCutting"] = tick
        return result
    if choice == "prioritize_cleaning":
        result = prioritize(client, snapshot, "Cleaning")
        issued["priority:Cleaning"] = tick
        return result
    if choice == "prioritize_rescue":
        result = prioritize(client, snapshot, "BasicWorker")
        issued["priority:BasicWorker"] = tick
        return result
    if choice == "prioritize_doctor":
        result = prioritize(client, snapshot, "Doctor")
        issued["priority:Doctor"] = tick
        return result
    if choice == "designate_safe_hunting":
        animal_id = details.get("hunt_target")
        animal = next((a for a in details.get("hunt_options", []) if int(a.get("id", -1)) == int(animal_id or -1)), None)
        if animal is None:
            return {"applied": False, "reason": "Laya did not select an available hunting target"}
        result = client.post("/api/v1/map/animal/hunt", body={"map_id": map_id, "animal_id": int(animal_id)})
        issued[f"hunt:{animal_id}"] = tick
        issued["safe_hunting"] = tick
        issued["priority:Hunting"] = tick
        hunting = prioritize(client, snapshot, "Hunting")
        return {"applied": True, "animal": animal, "responses": [result, hunting]}
    if choice == "leave_wildlife_alone":
        issued["wildlife_pause"] = tick
        return {"applied": False, "reason": "Laya chose to leave nearby wildlife alone for now"}
    if choice == "harvest_local_plants":
        plant_type = str(details.get("wild_plant_type") or "")
        selected = (details.get("wild_plant_options") or {}).get(plant_type)
        if not selected:
            return {"applied": False, "reason": "Laya did not select an available mature wild plant type"}
        result = client.post("/api/v1/map/plants/harvest", body={
            "map_id": map_id,
            "plant_ids": list(map(int, selected.get("ids", [])[:60])),
        })
        issued["harvest"] = tick
        return {"applied": True, "plant_type": plant_type, "expected_yield": selected.get("expected_yield"), "response": result}
    if choice == "hold_survival":
        return {"applied": False, "reason": "Survival work already issued; waiting for colonists"}
    raise bridge.RimApiError(f"Unknown colony director action: {choice}")


def run_development_cycle(client: bridge.RimApiClient, agent: Any, state: dict[str, Any], state_path: Path, log_path: Path) -> dict[str, Any]:
    snapshot = collect_development(client, bridge.collect_snapshot(client))
    player_preferences = laya_preferences.load_preferences()
    snapshot["development"]["user_preferences"] = player_preferences
    seed = str(snapshot["map"].get("seed") or snapshot["map"]["id"])
    map_state = state.setdefault("maps", {}).setdefault(seed, {"issued": {}})
    snapshot["development"]["income_strategy"] = map_state.get("income_strategy")
    snapshot["development"]["prisoner_plans"] = map_state.get("prisoner_plans", {})
    snapshot["development"]["doctrine"] = map_state.get("doctrine", {})
    snapshot["development"]["doctrine_audit"] = map_state.get("doctrine_audit", {})
    if "anchor" not in map_state or "growing_anchor" not in map_state:
        center = anchor_from_snapshot(snapshot)
        terrain = client.get("/api/v1/map/terrain", map_id=snapshot["map"]["id"])
        map_state.setdefault(
            "anchor",
            find_terrain_rect(terrain, center, 15, 11, {"Soil", "SoilRich", "Gravel"}) or center,
        )
        growing_center = {"x": max(12, center["x"] - 24), "z": center["z"]}
        map_state.setdefault(
            "growing_anchor",
            find_terrain_rect(terrain, growing_center, 10, 8, {"Soil", "SoilRich"}, radius=45) or growing_center,
        )
    candidates, details = candidate_actions(client, snapshot, map_state)
    candidates = laya_preferences.filter_candidates(candidates, player_preferences)
    candidates, blocked_actions = filter_backed_off_choices(map_state, candidates)
    if not candidates:
        candidates = ["hold_survival"]
    if blocked_actions:
        snapshot["development"]["temporarily_blocked_actions"] = {
            choice: round(remaining, 1) for choice, remaining in blocked_actions.items()
        }
    decision = choose_action(agent, snapshot, candidates)
    for key in (
        "trade_purchase", "stone_type", "tame_target", "wild_plant_type", "hunt_target",
        "critical_floor_plan", "path_material", "worker_pawn", "construction_project",
        "temple_altar", "temple_material",
        "doctrine_settlement_form", "doctrine_material", "doctrine_diplomacy",
        "doctrine_military", "doctrine_economy", "doctrine_mining_product",
        "doctrine_beauty", "doctrine_specialization", "sculpture_install_plan", "animal_barn_material",
        "animal_barn_floor", "architecture_program", "architecture_house_style",
        "architecture_variant", "lighting_room", "skill_training_plan",
        "night_owl_pawn", "workbench_upgrade", "doctrine_selection",
        "doctrine_direction_audit", "doctrine_research_target",
    ):
        if decision.get(key) is not None:
            details[key] = decision[key]
    choice = str(decision["choice"])
    try:
        result = execute_action(client, snapshot, map_state, choice, details)
    except bridge.RimApiError as exc:
        failure = register_action_failure(map_state, choice, exc)
        result = {
            "applied": False,
            "skipped": "api_error_backoff",
            "error": str(exc),
            "failure_count": failure["count"],
            "retry_in_seconds": round(float(failure["retry_after"]) - time.time(), 1),
        }
    else:
        clear_action_failure(map_state, choice)
    try:
        publish_overlay(client, snapshot, candidates, decision)
    except bridge.RimApiError as exc:
        snapshot.setdefault("warnings", []).append(f"Overlay: {exc}")
    record = {
        "timestamp": bridge.utc_now(),
        "mode": "colony-director",
        "goal": str((map_state.get("doctrine") or {}).get("endgame") or "self-sufficient_colony"),
        "map_seed": seed,
        "anchor": map_state["anchor"],
        "candidates": candidates,
        "decision": decision,
        "result": result,
    }
    if player_preferences.get("technical_logging"):
        record["technical"] = {"snapshot": snapshot, "details": details}
    save_state(state_path, state)
    bridge.append_log(log_path, record)
    return record


def _event_quest(context: dict[str, Any], event: dict[str, Any]) -> dict[str, Any] | None:
    quests = [row for row in context.get("active_quests") or [] if isinstance(row, dict)]
    event_id = event.get("id") if event.get("source") == "quest" else None
    if event_id is not None:
        exact = next((row for row in quests if int(row.get("id", -1)) == int(event_id)), None)
        if exact:
            return exact
    rescue = [row for row in quests if events.classify_event(row) == "kidnap_rescue"]
    return rescue[0] if rescue else (quests[0] if quests else None)


def _execute_event_response(
    client: bridge.RimApiClient,
    snapshot: dict[str, Any],
    map_state: dict[str, Any],
    event: dict[str, Any],
    context: dict[str, Any],
    response: str,
    details: dict[str, Any],
) -> Any:
    map_id = int(snapshot["map"]["id"])
    tick = int(snapshot["game"].get("tick") or 0)
    if response in {"observe_event", "skip_trade", "defer_rescue", "defer_quest", "evaluate_animals", "evaluate_recruit", "ask_laya_generic"}:
        return {"applied": False, "reason": response}
    if response == "delegate_to_combat_planner":
        return {"applied": False, "reason": "The combat planner owns verified hostile pawns and will run on the next combat tick."}
    if response == "prepare_undrafted":
        commands = []
        for pawn in snapshot.get("combat", {}).get("colonists", []):
            if pawn.get("is_drafted"):
                commands.append(client.post("/api/v1/pawn/edit/status", body={"pawn_id": int(pawn["id"]), "is_drafted": False}))
        if snapshot.get("game", {}).get("is_paused"):
            commands.append(client.post("/api/v1/game/speed", query={"speed": 1}))
        return {"applied": bool(commands), "responses": commands}
    if response == "prioritize_firefighting":
        return prioritize(client, snapshot, "Firefighter")
    if response == "prioritize_medical":
        return prioritize(client, snapshot, "Doctor")
    if response == "emergency_harvest":
        plants = snapshot.get("development", {}).get("plants", [])
        ids = [
            int(row["id"]) for row in plants
            if row.get("id") is not None and (
                row.get("can_harvest") or row.get("is_harvestable")
                or float(row.get("growth") or row.get("growth_progress") or 0) >= 0.95
            )
        ][:120]
        if not ids:
            return {"applied": False, "reason": "No verified mature plant is available for emergency harvest."}
        return client.post("/api/v1/map/plants/harvest", body={"map_id": map_id, "plant_ids": ids})
    if response == "pause_sowing":
        results = []
        for zone in snapshot.get("development", {}).get("zones", []):
            if zone.get("allow_sow") is True:
                results.append(client.post("/api/v1/map/zone/growing/sowing", body={"map_id": map_id, "zone_id": int(zone["id"]), "allow_sow": False}))
        return {"applied": bool(results), "responses": results}
    if response == "collect_event_resources":
        forbidden = snapshot.get("development", {}).get("forbidden", [])
        ids = [int(row["id"]) for row in forbidden if row.get("id") is not None][:100]
        if not ids:
            return {"applied": False, "reason": "No forbidden event resource is currently visible."}
        return client.post("/api/v1/things/set-forbidden", body={"map_id": map_id, "thing_ids": ids, "forbidden": False})
    if response in {"accept_rescue_quest", "accept_quest"}:
        quest = _event_quest(context, event)
        if not quest:
            return {"applied": False, "reason": "No live quest matches this event."}
        return client.post("/api/v1/quest/accept", body={"quest_id": int(quest["id"])})
    if response == "prepare_rescue_mission":
        quest = _event_quest(context, event)
        if not quest:
            return {"applied": False, "reason": "No rescue quest with a world target is active."}
        responses = []
        if not quest.get("ever_accepted"):
            responses.append(client.post("/api/v1/quest/accept", body={"quest_id": int(quest["id"])}))
        targets = [row for row in quest.get("look_targets") or [] if row.get("world_object_id") is not None]
        if not targets:
            return {"applied": bool(responses), "reason": "Quest accepted, but no visitable rescue site exists yet.", "responses": responses}
        target = min(targets, key=lambda row: float(row.get("estimated_threat_points") or 0))
        responses.append(client.post("/api/v1/world/caravan/rescue/start", body={
            "map_id": map_id,
            "quest_id": int(quest["id"]),
            "site_id": int(target["world_object_id"]),
            "minimum_home_defenders": 2,
            "minimum_food_at_home": max(20, len(snapshot.get("colonists", [])) * 5),
            "minimum_medicine_at_home": 8,
        }))
        map_state["rescue_mission"] = {"quest_id": int(quest["id"]), "site_id": int(target["world_object_id"]), "started_tick": tick}
        return {"applied": True, "responses": responses}
    if response == "trade_now":
        trader_id = str(details.get("trader_id") or "")
        if not any(str(row.get("id")) == trader_id for row in context.get("trade_opportunities") or []):
            return {"applied": False, "reason": "The selected trader has departed."}
        sale = str(details.get("sale_category") or "none")
        purchase = str(details.get("purchase_priority") or "none")
        body = {
            "map_id": map_id,
            "trader_id": trader_id,
            "sale_categories": [] if sale == "none" else [sale],
            "purchase_priorities": [] if purchase == "none" else [purchase],
            "minimum_silver_reserve": 300,
            "maximum_spend": 1800,
        }
        return client.post("/api/v1/trade/execute", body=body)
    if response in {"power_emergency", "weather_emergency", "psychic_schedule_response", "contain_anomaly", "use_opportunity", "rescue_arrival"}:
        if snapshot.get("game", {}).get("is_paused"):
            return client.post("/api/v1/game/speed", query={"speed": 1})
        return {"applied": False, "reason": f"{response}: context recorded; no universally safe forced order exists."}
    raise bridge.RimApiError(f"Unknown event response: {response}")


def publish_event_overlay(client: bridge.RimApiClient, event: dict[str, Any], options: dict[str, str], answer: dict[str, Any], result: Any) -> None:
    choice = str(answer.get("choice") or "observe_event")
    probabilities = answer.get("probabilities") or {}
    lines = [
        "LAYA — СОБЫТИЕ",
        f"{event.get('label') or event.get('name') or event.get('def_name') or event.get('incident_def')}",
        f"Семейство: {event.get('family')} | источник: {event.get('source')}",
        "",
        "Варианты:",
    ]
    for name in options:
        score = probabilities.get(name)
        suffix = f" {float(score) * 100:.1f}%" if score is not None else ""
        lines.append(f"{'> ' if name == choice else '  '}{name}{suffix}")
    lines.extend(["", f"Решение: {choice}", f"Результат: {str(result)[:180]}"])
    event_label = str(event.get("label") or event.get("name") or event.get("def_name") or event.get("incident_def") or "Событие")
    show_overlay(
        client,
        compact_lines=["LAYA — СОБЫТИЕ", event_label, f"Решение: {choice}"],
        full_lines=lines,
        bars=probability_bars(probabilities, {name: options.get(name, name) for name in options}, choice, 8),
        duration=15.0,
        color="#F3E6FF",
    )


def run_event_cycle(
    client: bridge.RimApiClient,
    agent: Any,
    state: dict[str, Any],
    state_path: Path,
    log_path: Path,
) -> dict[str, Any] | None:
    snapshot = collect_development(client, bridge.collect_snapshot(client))
    seed = str(snapshot["map"].get("seed") or snapshot["map"]["id"])
    map_state = state.setdefault("maps", {}).setdefault(seed, {"issued": {}})
    context = bridge.safe_get(client, "/api/v1/events/context", snapshot.setdefault("warnings", []), map_id=snapshot["map"]["id"]) or {}
    tick = int(snapshot["game"].get("tick") or 0)
    history = map_state.setdefault("handled_events", {})
    history = {str(key): int(value) for key, value in history.items() if tick - int(value) < 120000}
    map_state["handled_events"] = history
    pending = events.pending_events(context, set(history))
    if not pending:
        return None
    event = pending[0]
    options = events.response_options(event, context)
    failure_prefix = f"event:{event['signature']}:"
    available_responses, blocked_responses = filter_backed_off_choices(
        map_state, options, prefix=failure_prefix
    )
    if not available_responses:
        return None
    options = {name: options[name] for name in available_responses}
    event_model_context = events.event_context_for_model(event, context, snapshot)
    event_model_context["player_preferences"] = laya_preferences.model_context(laya_preferences.load_preferences())
    raw = agent.predict(event_model_context, {
        "event_response": {
            "type": "choice",
            "instructions": "Choose one proportional response to this verified live event. Prefer reversible normal-game actions and preserve food, medicine, defenders and deadlines.",
            "criteria": options,
        }
    })
    answer = raw.get("answers", {}).get("event_response", {})
    response = str(answer.get("choice") or "")
    if response not in options:
        response = next(iter(options))
        answer["choice"] = response
    details: dict[str, Any] = {}
    if response == "trade_now":
        traders = context.get("trade_opportunities") or []
        trader_question = {"event_trader": {
            "type": "choice",
            "instructions": "Choose the exact live trader using remaining time, stock, negotiator skill and orbital infrastructure.",
            "criteria": {
                str(row["id"]): f"{row.get('name')} ({row.get('trader_kind')}); orbital={row.get('orbital')}; departs in {row.get('ticks_until_departure')} ticks; stock {[(item.get('label'), item.get('count')) for item in (row.get('stock') or [])[:18]]}"
                for row in traders if row.get("id")
            },
        }}
        if trader_question["event_trader"]["criteria"]:
            trader_raw = agent.predict(event_model_context, trader_question)
            trader_id = str(trader_raw.get("answers", {}).get("event_trader", {}).get("choice") or "")
            if trader_id not in trader_question["event_trader"]["criteria"]:
                trader_id = next(iter(trader_question["event_trader"]["criteria"]))
            details["trader_id"] = trader_id
            policy_raw = agent.predict(event_model_context, {
                "sale_category": {"type": "choice", "instructions": "Choose one surplus category to sell; hard-coded reserves protect survival stocks.", "criteria": {
                    "none": "Buy only", "drugs": "Surplus drugs", "apparel": "Apparel", "art": "Sculptures", "animals": "Animals", "food": "Surplus food", "leather": "Leather/textiles", "weapons": "Spare weapons", "gold": "Precious resources",
                }},
                "purchase_priority": {"type": "choice", "instructions": "Choose the highest-value purchase need within the spending cap and silver reserve.", "criteria": {
                    "none": "Sell only", "medicine": "Medicine/neutroamine", "components": "Industrial components", "advanced_components": "Advanced components", "food": "Emergency food", "weapons": "Weapons", "armor": "Armor", "plasteel": "Plasteel",
                }},
            })
            details["sale_category"] = str(policy_raw.get("answers", {}).get("sale_category", {}).get("choice") or "none")
            details["purchase_priority"] = str(policy_raw.get("answers", {}).get("purchase_priority", {}).get("choice") or "none")
            raw["trade"] = {"trader": trader_raw, "policy": policy_raw}
    execution_failed = False
    try:
        result = _execute_event_response(client, snapshot, map_state, event, context, response, details)
    except bridge.RimApiError as exc:
        execution_failed = True
        failure = register_action_failure(map_state, f"{failure_prefix}{response}", exc)
        result = {
            "applied": False,
            "skipped": "event_api_error_backoff",
            "error": str(exc),
            "failure_count": failure["count"],
            "retry_in_seconds": round(float(failure["retry_after"]) - time.time(), 1),
        }
    else:
        clear_action_failure(map_state, f"{failure_prefix}{response}")
    # Quest acceptance is phase one; a fresh snapshot must be allowed to offer
    # the newly created/updated rescue site on the next cycle.
    if not execution_failed and response != "accept_rescue_quest":
        history[event["signature"]] = tick
    try:
        publish_event_overlay(client, event, options, answer, result)
    except bridge.RimApiError as exc:
        snapshot.setdefault("warnings", []).append(str(exc))
    record = {
        "timestamp": bridge.utc_now(), "mode": "event-director", "map_seed": seed,
        "event": event, "options": options, "blocked_options": blocked_responses,
        "decision": {"choice": response, "raw": raw, **details}, "result": result,
    }
    save_state(state_path, state)
    bridge.append_log(log_path, record)
    return record


def run_rescue_site_cycle(
    client: bridge.RimApiClient,
    state: dict[str, Any],
    state_path: Path,
    log_path: Path,
    snapshot: dict[str, Any],
) -> dict[str, Any] | None:
    active_plans = [
        map_state for map_state in state.setdefault("maps", {}).values()
        if isinstance(map_state, dict) and map_state.get("rescue_mission")
    ]
    if not active_plans or not snapshot.get("map", {}).get("is_temp_incident_map"):
        return None
    status = client.get("/api/v1/world/rescue/site/status", map_id=int(snapshot["map"]["id"]))
    if status.get("active_threat"):
        return None
    if status.get("captive_pawn_ids"):
        release_active = any(
            "releaseprisoner" in str(pawn.get("current_job") or "").replace("_", "").lower()
            for pawn in snapshot.get("combat", {}).get("colonists", [])
        )
        if release_active:
            result = {"applied": False, "reason": "normal prisoner release job is still active"}
            phase = "wait-for-release"
        else:
            result = client.post("/api/v1/world/rescue/site/secure", body={"map_id": int(snapshot["map"]["id"])})
            phase = "free-captive"
    elif status.get("can_return_home"):
        result = client.post("/api/v1/world/rescue/site/return", body={"map_id": int(snapshot["map"]["id"])})
        phase = "return-home"
        for map_state in active_plans:
            map_state["last_rescue_mission"] = map_state.pop("rescue_mission")
            map_state["last_rescue_mission"]["completed_tick"] = int(snapshot["game"].get("tick") or 0)
    else:
        return None
    record = {
        "timestamp": bridge.utc_now(), "mode": "rescue-site", "phase": phase,
        "status": status, "result": result,
    }
    try:
        rescue_lines = [
            "LAYA — СПАСАТЕЛЬНАЯ ОПЕРАЦИЯ",
            f"Этап: {phase}",
            f"Пленники: {', '.join(status.get('captive_names') or []) or 'освобождены'}",
        ]
        show_overlay(client, compact_lines=rescue_lines, full_lines=rescue_lines, duration=12.0, color="#CFFFE0")
    except bridge.RimApiError:
        pass
    save_state(state_path, state)
    bridge.append_log(log_path, record)
    return record


def run_downed_raider_cycle(
    client: bridge.RimApiClient,
    agent: Any,
    state: dict[str, Any],
    state_path: Path,
    log_path: Path,
) -> dict[str, Any]:
    """Let Laya resolve verified downed hostiles without treating them as an active assault."""
    snapshot = collect_development(client, bridge.collect_snapshot(client))
    seed = str(snapshot["map"].get("seed") or snapshot["map"]["id"])
    map_state = state.setdefault("maps", {}).setdefault(seed, {"issued": {}})
    if "anchor" not in map_state:
        map_state["anchor"] = anchor_from_snapshot(snapshot)
    anchor = map_state["anchor"]
    tick = int(snapshot["game"].get("tick") or 0)
    issued = map_state.setdefault("issued", {})
    downed = [h for h in snapshot["combat"]["hostiles"] if h.get("is_downed") and not h.get("is_dead")]
    prison_a = position(anchor["x"] - 12, anchor["z"] - 8)
    prison_b = position(anchor["x"] - 6, anchor["z"] - 2)
    prison_beds = [
        b for b in snapshot["development"].get("buildings", [])
        if b.get("for_prisoners")
        and prison_a["x"] <= int((b.get("position") or {}).get("x") or -999) <= prison_b["x"]
        and prison_a["z"] <= int((b.get("position") or {}).get("z") or -999) <= prison_b["z"]
    ]
    criteria: dict[str, str] = {
        "leave_downed_raiders": "Leave the downed enemies alone, keep colonists undrafted, and accept that they may bleed out, recover, or leave.",
    }
    if not prison_beds:
        if not issued_recently(map_state, "prison_blueprint", tick, retry_ticks=90000):
            criteria["build_prison"] = "Place a normal enclosed two-bed prison blueprint now; capture becomes possible only after colonists finish it."
        else:
            criteria["wait_for_prison"] = "Keep colonists undrafted and prioritize construction while the already-issued prison is completed."
    for hostile in downed:
        pawn_id = int(hostile["id"])
        name = str(hostile.get("name") or pawn_id)
        criteria[f"finish_downed:{pawn_id}"] = (
            f"Kill {name} with an ordinary drafted attack. Health {float(hostile.get('health') or 0) * 100:.0f}%, "
            f"bleeding {float(hostile.get('bleeding_rate') or 0):.2f}; this avoids prison costs but may affect mood or ideology."
        )
        if prison_beds:
            skills = ", ".join(map(str, hostile.get("top_skills") or [])) or "unknown skills"
            if hostile.get("recruitable", True):
                criteria[f"capture_recruit:{pawn_id}"] = (
                    f"Capture {name} and set Recruit. {hostile.get('gender')}, age {hostile.get('biological_age')}; "
                    f"top skills {skills}; traits {hostile.get('traits') or []}; value {hostile.get('market_value', 0):.0f}."
                )
            if hostile.get("faction_can_give_goodwill") and not hostile.get("faction_permanent_enemy"):
                criteria[f"capture_release:{pawn_id}"] = (
                    f"Capture and heal {name}, then Release for faction goodwill. Current goodwill {hostile.get('faction_goodwill', 0)}."
                )
            criteria[f"capture_sell:{pawn_id}"] = (
                f"Capture {name} and hold with no recruitment interaction for a later slaver/settlement sale; "
                f"market value {hostile.get('market_value', 0):.0f}, requiring food, guarding and transport."
            )
    resources = snapshot["map"]["resources"]
    material_counts = snapshot["development"].get("item_counts", {})
    context = {
        "goal": "Resolve downed raiders while preserving colony survival and future growth.",
        "player_preferences": laya_preferences.model_context(laya_preferences.load_preferences()),
        "colony": {
            "population": len(snapshot["colonists"]),
            "food": resources.get("food"),
            "medicine": resources.get("medicine"),
            "wood": material_counts.get("WoodLog", 0),
            "silver": material_counts.get("Silver", 0),
            "prison_beds_ready": len(prison_beds),
            "best_social": max((int((c.get("skills", {}).get("Social") or {}).get("level") or 0) for c in snapshot["colonists"]), default=0),
            "best_medicine": max((int((c.get("skills", {}).get("Medicine") or {}).get("level") or 0) for c in snapshot["colonists"]), default=0),
        },
        "downed_raiders": downed,
    }
    question = {"downed_raider_action": {
        "type": "choice",
        "instructions": "Choose one normal RimWorld action. Compare recruitable skills and value against prison food, treatment, escape and moral costs. A release helps only factions that can grant goodwill.",
        "criteria": criteria,
    }}
    raw = agent.predict(context, question)
    answer = raw["answers"]["downed_raider_action"]
    choice = str(answer.get("choice") or "leave_downed_raiders")
    if choice not in criteria:
        choice = "leave_downed_raiders"
    responses: list[Any] = []
    description = criteria[choice]
    if choice in {"leave_downed_raiders", "wait_for_prison"}:
        for pawn in snapshot["combat"]["colonists"]:
            if pawn.get("is_drafted"):
                responses.append(client.post("/api/v1/pawn/edit/status", body={"pawn_id": int(pawn["id"]), "is_drafted": False}))
        if choice == "wait_for_prison":
            responses.append(prioritize(client, snapshot, "Construction"))
        result: Any = {"applied": bool(responses), "responses": responses, "reason": choice}
    elif choice == "build_prison":
        responses.append(post_blueprint(client, snapshot["map"]["id"], anchor, prison_blueprint(), dx=-12, dz=-8))
        responses.append(prioritize(client, snapshot, "Construction"))
        issued["prison_blueprint"] = tick
        result = {"applied": True, "responses": responses}
    elif choice.startswith("finish_downed:"):
        target_id = int(choice.split(":", 1)[1])
        fighters = [p for p in snapshot["combat"]["colonists"] if not p.get("is_downed") and float(p.get("health") or 0) >= 0.75]
        ranged = [p for p in fighters if p.get("has_ranged_weapon")]
        actor = max(
            ranged or fighters,
            key=lambda p: int((p.get("shooting_skill") if ranged else p.get("melee_skill")) or 0),
            default=None,
        )
        if actor is None:
            result = {"applied": False, "reason": "No healthy colonist can finish the target"}
        else:
            responses.append(client.post("/api/v1/pawn/edit/status", body={"pawn_id": int(actor["id"]), "is_drafted": True}))
            responses.append(client.post("/api/v1/pawn/job", body={
                "pawn_id": int(actor["id"]),
                "job_def": "AttackStatic" if actor.get("has_ranged_weapon") else "AttackMelee",
                "target_thing_id": target_id,
            }))
            issued[f"finish_downed:{target_id}"] = tick
            result = {"applied": True, "actor": actor.get("name"), "target_id": target_id, "responses": responses}
    else:
        policy, target_text = choice.split(":", 1)
        target_id = int(target_text)
        policy_name = policy.removeprefix("capture_")
        result = client.post("/api/v1/pawn/prisoner/capture", body={
            "map_id": snapshot["map"]["id"],
            "prisoner_pawn_id": target_id,
            "point_a": prison_a,
            "point_b": prison_b,
            "policy": policy_name,
        })
        issued[f"prisoner:{target_id}:{policy_name}"] = tick
        map_state.setdefault("prisoner_plans", {})[str(target_id)] = policy_name
    record = {
        "timestamp": bridge.utc_now(),
        "mode": "downed-raider",
        "snapshot": snapshot,
        "decision": {"choice": choice, "confidence": bridge.first_number(answer.get("confidence")), "raw": raw},
        "action": {"description": description},
        "result": result,
    }
    save_state(state_path, state)
    bridge.append_log(log_path, record)
    publish_combat_overlay(client, record)
    return record


def get_ancient_danger(client: bridge.RimApiClient, map_id: int) -> dict[str, Any]:
    try:
        value = client.get("/api/v1/map/ancient-danger", map_id=map_id)
        return value if isinstance(value, dict) else {}
    except bridge.RimApiError:
        return {}


def run_ancient_danger_cycle(
    client: bridge.RimApiClient,
    agent: Any,
    state: dict[str, Any],
    state_path: Path,
    log_path: Path,
    status: dict[str, Any],
) -> dict[str, Any] | None:
    """Resolve the warning as a sealed site decision, never as a raid."""
    snapshot = collect_development(client, bridge.collect_snapshot(client))
    seed = str(snapshot["map"].get("seed") or snapshot["map"]["id"])
    map_state = state.setdefault("maps", {}).setdefault(seed, {"issued": {}})
    tick = int(snapshot["game"].get("tick") or 0)
    prior = map_state.get("ancient_danger") or {}
    same_notice = int(prior.get("detected_tick") or -1) == int(status.get("detected_tick") or -2)
    retry_after = 30000 if prior.get("policy") == "prepare_ancient_danger" else 600000
    if same_notice and tick - int(prior.get("decision_tick") or 0) < retry_after:
        if snapshot["game"].get("is_paused") and not prior.get("resumed"):
            client.post("/api/v1/game/speed", query={"speed": 1})
            prior["resumed"] = True
            save_state(state_path, state)
        return None

    healthy = [
        p for p in snapshot.get("combat", {}).get("colonists", [])
        if not p.get("is_dead") and not p.get("is_downed") and float(p.get("health") or 0) >= 0.75
    ]
    ranged = [p for p in healthy if p.get("has_ranged_weapon")]
    resources = snapshot["map"]["resources"]
    context = {
        "event": "A proximity warning revealed a sealed Ancient Danger. This is not an active raid.",
        "player_preferences": laya_preferences.model_context(laya_preferences.load_preferences()),
        "known_information": {
            "warning": status.get("notice"),
            "sealed": bool(status.get("sealed")),
            "contents": "unknown; do not assume hidden enemies or loot",
            "can_designate_opening_wall": bool(status.get("can_open")),
        },
        "colony": {
            "population": len(snapshot["colonists"]),
            "healthy_fighters": len(healthy),
            "healthy_ranged_fighters": len(ranged),
            "medicine": resources.get("medicine", 0),
            "food": resources.get("food", 0),
            "weapons": resources.get("weapons", 0),
            "current_doctrine": map_state.get("doctrine", {}),
        },
    }
    criteria = {
        "leave_ancient_danger_sealed": "Acknowledge the warning, keep the tomb sealed, undraft everyone, resume time, and revisit only much later or after a major strength increase.",
        "prepare_ancient_danger": "Keep it sealed, add a fallback firing line/traps using normal construction, resume time, and reconsider after colonists finish preparations.",
    }
    if status.get("can_open"):
        criteria["open_ancient_danger"] = "Designate one identified outer wall for normal deconstruction and resume time. Contents are unknown and may be immediately lethal; choose only if current fighters, weapons, medicine and fallback position justify it."
    question = {"ancient_danger_action": {
        "type": "choice",
        "instructions": "Choose autonomously whether to leave, prepare for, or open the sealed Ancient Danger. It is a strategic opportunity/risk, not a raid; never keep colonists drafted merely because the warning paused the game.",
        "criteria": criteria,
    }}
    raw = agent.predict(context, question)
    answer = raw.get("answers", {}).get("ancient_danger_action", {})
    choice = str(answer.get("choice") or "")
    if choice not in criteria:
        choice = "leave_ancient_danger_sealed"
    responses: list[Any] = []
    if choice == "prepare_ancient_danger":
        anchor = map_state.get("anchor") or anchor_from_snapshot(snapshot)
        map_state.setdefault("anchor", anchor)
        responses.append(post_blueprint(client, snapshot["map"]["id"], anchor, fallback_defense_blueprint(), dx=12, dz=-6))
        responses.append(prioritize(client, snapshot, "Construction"))
    elif choice == "open_ancient_danger":
        responses.append(client.post("/api/v1/map/ancient-danger/open", body={"map_id": snapshot["map"]["id"]}))
    # This is the only pause transition here: a verified Ancient Danger warning.
    if snapshot["game"].get("is_paused"):
        responses.append(client.post("/api/v1/game/speed", query={"speed": 1}))
    map_state["ancient_danger"] = {
        "policy": choice,
        "detected_tick": int(status.get("detected_tick") or 0),
        "decision_tick": tick,
        "resumed": bool(snapshot["game"].get("is_paused")),
        "position": status.get("position"),
    }
    probabilities = answer.get("probabilities") or {}
    lines = [
        "LAYA — ДРЕВНЯЯ ОПАСНОСТЬ",
        "Это запечатанная гробница, не активный рейд.",
        f"Бойцы: {len(healthy)} | стрелки: {len(ranged)} | медицина: {resources.get('medicine', 0)}",
        "",
        "Варианты:",
    ]
    for name in criteria:
        score = probabilities.get(name)
        suffix = f" {float(score) * 100:.1f}%" if score is not None else ""
        lines.append(f"{'> ' if name == choice else '  '}{name}{suffix}")
    lines.extend(["", f"Решение: {choice}", "Автопауза снята; колонисты не держатся мобилизованными из-за одного предупреждения."])
    try:
        show_overlay(
            client,
            compact_lines=[
                "LAYA — ДРЕВНЯЯ ОПАСНОСТЬ",
                f"Бойцы: {len(healthy)} · стрелки: {len(ranged)} · медицина: {resources.get('medicine', 0)}",
                f"Решение: {choice}",
            ],
            full_lines=lines,
            bars=probability_bars(probabilities, {name: name for name in criteria}, choice, 8),
            duration=16.0,
            color="#FFE5A8",
        )
    except bridge.RimApiError:
        pass
    record = {
        "timestamp": bridge.utc_now(),
        "mode": "ancient-danger",
        "snapshot": snapshot,
        "status": status,
        "decision": {"choice": choice, "confidence": bridge.first_number(answer.get("confidence")), "raw": raw},
        "result": {"applied": True, "responses": responses},
    }
    save_state(state_path, state)
    bridge.append_log(log_path, record)
    return record


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Long-horizon Laya colony director for RimWorld")
    p.add_argument("--api-url", default=bridge.DEFAULT_API_URL)
    p.add_argument("--model", default=bridge.DEFAULT_MODEL)
    p.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    p.add_argument("--interval", type=float, default=10.0)
    p.add_argument("--state", type=Path, default=Path(__file__).with_name("logs") / "colony-state.json")
    p.add_argument("--log", type=Path, default=Path(__file__).with_name("logs") / "decisions.jsonl")
    p.add_argument("--pid-file", type=Path, default=Path(__file__).with_name("logs") / "director.pid")
    p.add_argument("--runtime-status", type=Path, default=Path(__file__).with_name("logs") / "runtime-status.json")
    return p


def write_runtime_status(path: Path, state: str, detail: str = "") -> bool:
    """Publish health without ever letting a Windows file-sharing race stop Laya."""
    payload = {
        "pid": os.getpid(),
        "state": state,
        "detail": detail[:500],
        "updated_at": bridge.utc_now(),
    }
    serialized = json.dumps(payload, ensure_ascii=False)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    for attempt in range(4):
        try:
            temporary.write_text(serialized, encoding="utf-8")
            temporary.replace(path)
            return True
        except OSError:
            time.sleep(0.025 * (attempt + 1))
    # Antivirus and the GUI can briefly hold the destination without FILE_SHARE_DELETE.
    # A direct write is less atomic but still preferable to terminating the autopilot.
    try:
        path.write_text(serialized, encoding="utf-8")
        return True
    except OSError:
        return False
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def classify_runtime_problem(detail: str) -> tuple[str, str, str]:
    """Separate an unavailable game from an actual decision-cycle failure."""

    lowered = detail.lower()
    if "no loaded map" in lowered or "load a colony" in lowered:
        return "waiting", detail, "Waiting for a loaded colony"
    unavailable_markers = (
        "winerror 10061",
        "connection refused",
        "actively refused",
        "конечный компьютер отверг",
        "expecting value: line 1 column 1",
    )
    if any(marker in lowered for marker in unavailable_markers):
        return "waiting", "RimWorld or RIMAPI is not available yet", "Waiting for RimWorld/RIMAPI"
    return "error", detail, "Decision cycle problem"


def cycle_retry_policy(runtime_state: str, consecutive_errors: int, interval: float) -> tuple[float, int]:
    """Return retry delay and next error count without busy-looping the API."""
    if runtime_state == "waiting":
        return min(10.0, max(2.0, interval)), 0
    next_count = min(8, consecutive_errors + 1)
    delay = min(300.0, max(10.0, interval) * (2 ** (next_count - 1)))
    return delay, next_count


def combat_order_signature(snapshot: dict[str, Any]) -> tuple[Any, ...]:
    """Return only changes that justify replacing an active combat order.

    Exact positions and pawn jobs change while a drafted pawn walks to cover.
    Including them made the director re-plan and resend the same order every two
    seconds, which could keep a pawn from ever completing it. The signature still
    changes for casualties, material health loss, drafting, target changes and a
    transition from raid preparation to active attack.
    """
    combat = snapshot.get("combat") or {}
    colonists = list(combat.get("colonists") or [])
    hostiles = [row for row in (combat.get("hostiles") or []) if not row.get("is_dead")]

    def hostile_intent(row: dict[str, Any]) -> str:
        job = str(row.get("current_job") or "").lower()
        for intent, markers in (
            ("kidnap", ("kidnap", "capture")),
            ("flee", ("flee", "exitmap")),
            ("breach", ("breach", "sap")),
            ("steal", ("steal",)),
            ("attack", ("attack", "goto", "assault")),
            ("staging", ("wait", "prepare", "siege", "mortar")),
        ):
            if any(marker in job for marker in markers):
                return intent
        return "unknown"

    healthy = [
        row for row in colonists
        if row.get("id") is not None
        and not row.get("is_dead")
        and not row.get("is_downed")
        and bridge.first_number(row.get("health"), 0.0) >= 0.6
    ]
    hostile_intents = tuple(sorted(hostile_intent(row) for row in hostiles))
    staging = bool(healthy) and bool(hostiles) and all(
        bridge.first_number(row.get("distance_to_nearest_opponent"), 9999) > 45
        for row in healthy
    ) and not any(intent in {"attack", "breach", "kidnap", "steal"} for intent in hostile_intents)
    fighter_state = tuple(sorted(
        (
            int(row["id"]), bool(row.get("is_drafted")), bool(row.get("is_downed")),
            int(bridge.first_number(row.get("health"), 0.0) * 10),
            str(row.get("weapon_def") or ""),
        )
        for row in colonists if row.get("id") is not None
    ))
    hostile_state = tuple(sorted(
        (
            int(row["id"]), bool(row.get("is_downed")),
            int(bridge.first_number(row.get("health"), 0.0) * 10),
            hostile_intent(row), int(row.get("carrying_pawn_id") or 0),
        )
        for row in hostiles if row.get("id") is not None
    ))
    return ("staging" if staging else "active", fighter_state, hostile_state)


def main() -> int:
    args = parser().parse_args()
    singleton_handle = None
    if os.name == "nt":
        singleton_handle = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\RimWorldLayaColonyDirector")
        if ctypes.windll.kernel32.GetLastError() == 183:
            print("Another Laya colony director is already active; exiting duplicate process.", flush=True)
            return 2
    args.pid_file.parent.mkdir(parents=True, exist_ok=True)
    args.pid_file.write_text(str(os.getpid()), encoding="ascii")
    write_runtime_status(args.runtime_status, "starting", "Loading the local Laya model")
    client = bridge.RimApiClient(args.api_url)
    try:
        agent = bridge.load_agent(args.model, args.device)
        state = load_state(args.state)
    except Exception as exc:
        write_runtime_status(args.runtime_status, "error", f"Model startup failed: {exc}")
        raise
    last_wait_message = 0.0
    last_combat_signature: tuple[Any, ...] | None = None
    last_combat_record: dict[str, Any] | None = None
    next_colony_cycle = 0.0
    next_downed_cycle = 0.0
    retry_not_before = 0.0
    consecutive_cycle_errors = 0
    runtime_state = "running"
    runtime_detail = "Ready for the next decision cycle"
    print("Laya colony director active: survival -> doctrine -> chosen endgame. Ctrl+C stops safely.", flush=True)
    try:
        while True:
            started = time.monotonic()
            # Refresh the heartbeat without erasing a waiting/error state.  The
            # GUI must not briefly claim that a failing director is healthy
            # merely because another retry has started.
            write_runtime_status(args.runtime_status, runtime_state, runtime_detail)
            try:
                snapshot = bridge.collect_snapshot(client)
                remaining_retry = retry_not_before - time.monotonic()
                if remaining_retry > 0.0:
                    elapsed = time.monotonic() - started
                    time.sleep(max(0.0, min(2.0, remaining_retry) - elapsed))
                    continue
                if snapshot["map"]["enemies"] > 0 or any(c.get("is_drafted") for c in snapshot["combat"]["colonists"]):
                    next_colony_cycle = 0.0
                    living_hostiles = [h for h in snapshot["combat"]["hostiles"] if not h.get("is_dead")]
                    if living_hostiles and all(h.get("is_downed") for h in living_hostiles):
                        now = time.monotonic()
                        if now >= next_downed_cycle:
                            record = run_downed_raider_cycle(client, agent, state, args.state, args.log)
                            next_downed_cycle = now + args.interval
                            last_combat_record = record
                            print(f"[{record['timestamp']}] downed raider: {record['decision']['choice']} | {record['result']}", flush=True)
                        elif last_combat_record is not None:
                            publish_combat_overlay(client, last_combat_record, repeated=True)
                        elapsed = time.monotonic() - started
                        time.sleep(max(0.0, 2.0 - elapsed))
                        continue
                    next_downed_cycle = 0.0
                    signature = combat_order_signature(snapshot)
                    if signature == last_combat_signature and last_combat_record is not None:
                        publish_combat_overlay(client, last_combat_record, repeated=True)
                        print(f"[{bridge.utc_now()}] combat order still active; no duplicate command", flush=True)
                    else:
                        record = bridge.run_cycle(client, agent, apply=True, confidence=0.0, log_path=args.log)
                        publish_combat_overlay(client, record)
                        last_combat_signature = signature
                        last_combat_record = record
                        print(f"[{record['timestamp']}] combat: {record['action']['description']}", flush=True)
                else:
                    last_combat_signature = None
                    last_combat_record = None
                    now = time.monotonic()
                    rescue_record = run_rescue_site_cycle(client, state, args.state, args.log, snapshot)
                    away_site = bool(snapshot.get("map", {}).get("is_temp_incident_map"))
                    if rescue_record is not None:
                        next_colony_cycle = now + args.interval
                        print(f"[{rescue_record['timestamp']}] rescue site: {rescue_record['phase']} | {rescue_record['result']}", flush=True)
                    ancient = get_ancient_danger(client, snapshot["map"]["id"]) if rescue_record is None and not away_site else {}
                    ancient_record = None
                    event_record = None
                    if ancient.get("detected") and ancient.get("sealed"):
                        ancient_record = run_ancient_danger_cycle(client, agent, state, args.state, args.log, ancient)
                        if ancient_record is not None:
                            next_colony_cycle = now + args.interval
                            print(f"[{ancient_record['timestamp']}] ancient danger: {ancient_record['decision']['choice']}", flush=True)
                    if rescue_record is None and ancient_record is None and not away_site and now >= next_colony_cycle:
                        event_record = run_event_cycle(client, agent, state, args.state, args.log)
                        if event_record is not None:
                            next_colony_cycle = now + args.interval
                            print(f"[{event_record['timestamp']}] event: {event_record['decision']['choice']} | {event_record['result']}", flush=True)
                    if rescue_record is None and ancient_record is None and event_record is None and not away_site and now >= next_colony_cycle:
                        record = run_development_cycle(client, agent, state, args.state, args.log)
                        next_colony_cycle = now + args.interval
                        print(f"[{record['timestamp']}] colony: {record['decision']['choice']} | {record['result']}", flush=True)
                runtime_state = "running"
                runtime_detail = "Last decision cycle completed"
                consecutive_cycle_errors = 0
                retry_not_before = 0.0
                write_runtime_status(args.runtime_status, runtime_state, runtime_detail)
            except (bridge.RimApiError, OSError, ValueError, RuntimeError) as exc:
                now = time.monotonic()
                detail = str(exc)
                runtime_state, runtime_detail, prefix = classify_runtime_problem(detail)
                retry_delay, consecutive_cycle_errors = cycle_retry_policy(
                    runtime_state, consecutive_cycle_errors, args.interval
                )
                if runtime_state != "waiting":
                    runtime_detail = f"{runtime_detail} Retrying in {retry_delay:.0f}s."
                retry_not_before = time.monotonic() + retry_delay
                write_runtime_status(args.runtime_status, runtime_state, runtime_detail)
                if now - last_wait_message >= 60:
                    print(f"[{bridge.utc_now()}] {prefix}: {exc}", flush=True)
                    last_wait_message = now
                bridge.append_log(args.log, {"timestamp": bridge.utc_now(), "mode": runtime_state, "error": repr(exc)})
            except Exception as exc:
                retry_delay, consecutive_cycle_errors = cycle_retry_policy(
                    "error", consecutive_cycle_errors, args.interval
                )
                retry_not_before = time.monotonic() + retry_delay
                runtime_state = "error"
                runtime_detail = f"Unexpected cycle error: {exc}. Retrying in {retry_delay:.0f}s."
                write_runtime_status(args.runtime_status, runtime_state, runtime_detail)
                traceback.print_exc()
                bridge.append_log(args.log, {"timestamp": bridge.utc_now(), "mode": "error", "error": repr(exc)})
            elapsed = time.monotonic() - started
            time.sleep(max(0.0, 2.0 - elapsed))
    except KeyboardInterrupt:
        print("Stopped. No further commands will be sent.")
        return 0
    finally:
        try:
            write_runtime_status(args.runtime_status, "stopped", "Director stopped")
        except OSError:
            pass
        try:
            if args.pid_file.read_text(encoding="ascii").strip() == str(os.getpid()):
                args.pid_file.unlink(missing_ok=True)
        except OSError:
            pass
        if singleton_handle:
            ctypes.windll.kernel32.CloseHandle(singleton_handle)


if __name__ == "__main__":
    raise SystemExit(main())
