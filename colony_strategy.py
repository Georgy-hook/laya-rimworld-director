"""Cascaded, content-aware long-term strategy for the colony.

The catalogue describes strategic directions, not a fixed build order.  It is
filtered against the active RimWorld content packs reported by the running
game, then scored with the live workforce, research tree and building defs.
This keeps DLC and mod content visible without offering mechanics that are not
loaded in the current game.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from laya_decisions import ask_laya_choice


EXPANSION_PACKAGES = {
    "royalty": "ludeon.rimworld.royalty",
    "ideology": "ludeon.rimworld.ideology",
    "biotech": "ludeon.rimworld.biotech",
    "anomaly": "ludeon.rimworld.anomaly",
    "odyssey": "ludeon.rimworld.odyssey",
}

DOMAIN_LABELS = {
    "survival": "Выживание и устойчивость",
    "prosperity": "Производство и богатство",
    "technology": "Наука и преобразование людей",
    "society": "Общество, вера и наследие",
    "power": "Военная и политическая сила",
    "exploration": "Экспедиции и мобильность",
    "endgame": "Долгосрочная победа",
}


def _direction(
    domain: str,
    label: str,
    summary: str,
    *,
    expansion: str | None = None,
    professions: tuple[str, ...] = (),
    buildings: tuple[str, ...] = (),
    research: tuple[str, ...] = (),
    mechanics: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "domain": domain,
        "label": label,
        "summary": summary,
        "expansion": expansion,
        "professions": professions,
        "building_programs": buildings,
        "research_tokens": research,
        "mechanics": mechanics,
    }


# Coverage intentionally spans Core and every official expansion.  Mods remain
# covered by live WorkTypeDef/building/research catalogues and can contribute to
# scores and milestones even when they do not have a named vanilla archetype.
DIRECTIONS: dict[str, dict[str, Any]] = {
    "resilient_settlement": _direction(
        "survival", "Устойчивая автономная колония",
        "Запасы, надёжная энергия, медицина, пожарная безопасность и резервные производственные цепочки.",
        professions=("food_agriculture", "colony_services", "medicine_biotech"),
        buildings=("storage", "power_utility", "hospital", "freezer"),
        research=("electric", "battery", "geothermal", "hospital", "medicine", "firefoam"),
        mechanics=("food reserves", "redundant power", "hospital", "climate resilience"),
    ),
    "agrarian_colony": _direction(
        "survival", "Земледельческая колония",
        "Сезонные посевы, теплицы, питание, лекарственные и товарные культуры.",
        professions=("food_agriculture",), buildings=("kitchen", "freezer", "storage"),
        research=("hydropon", "tree sow", "devilstrand", "drug", "brewing"),
        mechanics=("crop rotation", "greenhouse", "food processing", "cash crops"),
    ),
    "ranching_colony": _direction(
        "survival", "Ранчо и животноводство",
        "Разведение, молоко, шерсть, яйца, вьючные и боевые животные с контролем кормов.",
        professions=("animal_husbandry", "food_agriculture"), buildings=("barn", "freezer", "workshop"),
        research=("animal", "pen", "shelf", "food"), mechanics=("breeding", "animal products", "pack animals", "combat animals"),
    ),
    "medical_sanctuary": _direction(
        "survival", "Медицинское убежище",
        "Сильная больница, протезирование, спасение людей, реабилитация и медицинская торговля.",
        professions=("medicine_biotech", "trade_diplomacy"), buildings=("hospital", "research_lab", "prison"),
        research=("hospital", "medicine", "prosthetic", "bionic", "biosculpt"),
        mechanics=("clean treatment", "surgery", "prosthetics", "humanitarian rescue"),
    ),
    "industrial_manufacturing": _direction(
        "prosperity", "Индустриальный производственный центр",
        "Компоненты, оружие, броня, одежда и серийное производство с короткой логистикой.",
        professions=("craft_industry", "mining_metallurgy"), buildings=("workshop", "factory", "storage", "power_utility"),
        research=("machining", "fabrication", "component", "smith", "armor", "weapon"),
        mechanics=("workshop chains", "components", "quality production", "industrial export"),
    ),
    "mining_metallurgy": _direction(
        "prosperity", "Горнодобыча и металлургия",
        "Каменные блоки, сканирование, глубокое бурение и переработка ценных руд.",
        professions=("mining_metallurgy", "construction_architecture"), buildings=("workshop", "factory", "storage"),
        research=("stonecut", "deep drill", "scanner", "mining", "smelt"),
        mechanics=("local veins", "deep drilling", "mineral expeditions", "stone industry"),
    ),
    "luxury_artisans": _direction(
        "prosperity", "Ремесло, искусство и роскошь",
        "Скульптуры, качественная мебель, одежда и красивые помещения как источник дохода и настроения.",
        professions=("art_culture", "craft_industry"), buildings=("workshop", "dining_recreation", "residence"),
        research=("stonecut", "furniture", "carpet", "clothing"), mechanics=("art export", "quality apparel", "room beauty", "royal-quality goods"),
    ),
    "trade_hub": _direction(
        "prosperity", "Торговый и логистический узел",
        "Караваны, орбитальная торговля, склады, переговоры и закупка дефицитных технологий.",
        professions=("trade_diplomacy", "colony_services"), buildings=("storage", "dining_recreation", "power_utility"),
        research=("microelectronic", "transport", "pod", "shelf"), mechanics=("caravan trade", "orbital trade", "alliances", "inventory reserves"),
    ),
    "research_starflight": _direction(
        "technology", "Научная колония и звёздный корабль",
        "Максимальный темп исследований, высокотехнологичное производство и собственный запуск с планеты.",
        professions=("research_technology", "craft_industry"), buildings=("research_lab", "factory", "power_utility"),
        research=("multi-analyzer", "fabrication", "advanced component", "ship", "starflight"), mechanics=("research throughput", "advanced components", "reactor", "cryptosleep launch"),
    ),
    "royal_court": _direction(
        "society", "Имперский двор",
        "Титулы, тронный зал, престиж, разрешения Империи и королевское завершение игры.",
        expansion="royalty", professions=("art_culture", "trade_diplomacy"), buildings=("throne_room", "residence", "dining_recreation"),
        research=("royal", "prestige", "harp", "piano"), mechanics=("honor", "titles", "permits", "high stellarch hospitality"),
    ),
    "tribal_psychic": _direction(
        "technology", "Природная псионическая традиция",
        "Медитация у анима-дерева, развитие пси-связи и применение псионики без имперской зависимости.",
        expansion="royalty", professions=("art_culture", "security_hunting"), buildings=("temple", "dining_recreation"),
        research=("psy", "anima", "meditat"), mechanics=("anima grass", "natural meditation", "psylink", "psycast support"),
    ),
    "ideological_community": _direction(
        "society", "Идеологическая община",
        "Роли, ритуалы, храм, обращение и развитие в соответствии с реальными мемами и предписаниями колонии.",
        expansion="ideology", professions=("art_culture", "trade_diplomacy"), buildings=("temple", "dining_recreation"),
        research=("biosculpt", "neural", "sleep acceler"), mechanics=("roles", "rituals", "conversion", "precept compliance"),
    ),
    "dryad_ecology": _direction(
        "society", "Дриады и экологическая община",
        "Гауранленовые деревья, связь с природой, минимизация вырубки и специализированные дриады.",
        expansion="ideology", professions=("food_agriculture", "animal_husbandry"), buildings=("dining_recreation", "temple"),
        research=("tree", "gauranlen", "nature"), mechanics=("dryads", "tree connection", "ecological building", "specialized castes"),
    ),
    "archonexus_pilgrimage": _direction(
        "endgame", "Путь Архонексуса",
        "Наращивание ценности поселения, продажа колоний и перенос ключевых людей и реликвий к Архонексусу.",
        expansion="ideology", professions=("trade_diplomacy", "art_culture", "research_technology"), buildings=("temple", "storage", "dining_recreation"),
        research=("archonexus",), mechanics=("wealth threshold", "colony sale", "relic preservation", "multi-settlement reset"),
    ),
    "mechanitor_swarm": _direction(
        "technology", "Механитор и рой механоидов",
        "Рабочие и боевые мехи, пропускная способность управления, босс-чипы и безопасное обслуживание.",
        expansion="biotech", professions=("research_technology", "craft_industry", "security_hunting"), buildings=("factory", "research_lab", "power_utility"),
        research=("mechtech", "mechanoid", "gestator", "band node", "subcore"), mechanics=("mechanitor bandwidth", "labor mechs", "combat mechs", "boss progression"),
    ),
    "xenogenetics": _direction(
        "technology", "Ксеногенетическая лаборатория",
        "Сбор генов, банк генов, ксеногермы и специализация колонистов под климат, работу и бой.",
        expansion="biotech", professions=("medicine_biotech", "research_technology"), buildings=("research_lab", "hospital", "factory"),
        research=("gene", "xenogen", "xenogerm"), mechanics=("gene extraction", "gene banking", "xenogerms", "xenotype diplomacy"),
    ),
    "family_dynasty": _direction(
        "society", "Семейная династия и образование",
        "Рождение и усыновление детей, ясли, обучение, выбор черт и поколенческое развитие навыков.",
        expansion="biotech", professions=("colony_services", "medicine_biotech", "food_agriculture"), buildings=("nursery", "residence", "hospital"),
        research=("fertility", "growth vat", "embryo"), mechanics=("pregnancy", "childcare", "learning", "growth moments"),
    ),
    "sanguophage_coven": _direction(
        "society", "Сангвофаги и бессмертие",
        "Гемоген, безопасный сон смерти, передача генов и управление потребностями кровопийц.",
        expansion="biotech", professions=("medicine_biotech", "security_hunting"), buildings=("hospital", "prison", "residence"),
        research=("deathrest", "hemogen", "sanguophage"), mechanics=("hemogen supply", "deathrest", "implantation", "fire vulnerability"),
    ),
    "pollution_adaptation": _direction(
        "technology", "Токсическая индустрия",
        "Переработка отходов, заморозка отходных пакетов и адаптация генами или снаряжением к загрязнению.",
        expansion="biotech", professions=("research_technology", "colony_services"), buildings=("factory", "storage", "power_utility"),
        research=("wastepack", "pollution", "atomizer"), mechanics=("waste refrigeration", "pollution control", "detoxification", "waster adaptation"),
    ),
    "anomaly_containment": _direction(
        "technology", "Комплекс содержания аномалий",
        "Прочные камеры, удерживающие платформы, исследование сущностей и контролируемое извлечение ресурсов.",
        expansion="anomaly", professions=("research_technology", "medicine_biotech", "security_hunting"), buildings=("research_lab", "hospital", "defense", "power_utility"),
        research=("contain", "entity", "anomaly", "bioferrite"), mechanics=("containment strength", "entity study", "escape prevention", "bioferrite harvest"),
    ),
    "void_ritualists": _direction(
        "power", "Ритуалы Бездны",
        "Психические ритуалы и аномальные инструменты с отдельной оценкой риска, морали и ответного события.",
        expansion="anomaly", professions=("art_culture", "research_technology"), buildings=("temple", "research_lab", "defense"),
        research=("ritual", "void", "anomaly"), mechanics=("psychic rituals", "void provocation", "bioferrite weapons", "risk containment"),
    ),
    "anomaly_mastery": _direction(
        "endgame", "Пробуждение монолита",
        "Постепенное изучение монолита, подготовка к финальному кризису и выбор судьбы после победы над машинным богом.",
        expansion="anomaly", professions=("research_technology", "security_hunting", "medicine_biotech"), buildings=("research_lab", "defense", "hospital"),
        research=("monolith", "anomaly", "void"), mechanics=("monolith tiers", "dark research", "containment readiness", "void ending"),
    ),
    "fortress_state": _direction(
        "power", "Крепость и эшелонированная оборона",
        "Внешний коридор, внутренняя линия, защита от десанта, сапёров, пожаров, осад, жуков и механоидов.",
        professions=("security_hunting", "construction_architecture"), buildings=("defense", "hospital", "power_utility"),
        research=("turret", "mortar", "armor", "weapon", "firefoam", "shield"), mechanics=("layered defense", "fallback lines", "anti-drop response", "siege response"),
    ),
    "raider_empire": _direction(
        "power", "Рейдерская экспансия",
        "Разведка целей, мобильные ударные группы, добыча и управление дипломатической ценой войны.",
        professions=("security_hunting", "trade_diplomacy"), buildings=("defense", "hospital", "storage"),
        research=("transport", "pod", "weapon", "armor", "scanner"), mechanics=("settlement raids", "loot logistics", "war diplomacy", "expedition recovery"),
    ),
    "caravan_nomads": _direction(
        "exploration", "Караванные кочевники",
        "Вьючные животные, дорожная еда, сезонные маршруты, торговля и экспедиции без гравикорабля.",
        professions=("trade_diplomacy", "animal_husbandry", "security_hunting"), buildings=("storage", "barn", "workshop"),
        research=("pemmican", "survival meal", "transport", "bedroll"), mechanics=("pack animals", "travel supplies", "seasonal routes", "mobile trade"),
    ),
    "quest_expeditionary": _direction(
        "exploration", "Экспедиционный корпус",
        "Квесты, спасение, руины и ресурсные вылазки с сохранением гарнизона и запасов дома.",
        professions=("security_hunting", "medicine_biotech", "trade_diplomacy"), buildings=("hospital", "storage", "defense"),
        research=("transport", "scanner", "pod", "shuttle"), mechanics=("quest evaluation", "rescue teams", "site combat", "safe return"),
    ),
    "gravship_nomads": _direction(
        "exploration", "Мобильная колония-гравикорабль",
        "Жилой гравикорабль с топливом, мастерскими, больницей и экспедициями по планете.",
        expansion="odyssey", professions=("construction_architecture", "research_technology", "colony_services"), buildings=("residence", "factory", "hospital", "power_utility"),
        research=("grav", "thruster", "flight"), mechanics=("gravcores", "mobile base", "landing logistics", "fuel range"),
    ),
    "orbital_salvagers": _direction(
        "exploration", "Орбитальные добытчики",
        "Астероиды, станции, вакуумная защита, воздушные шлюзы и быстрый вывоз редких материалов.",
        expansion="odyssey", professions=("mining_metallurgy", "security_hunting", "research_technology"), buildings=("factory", "storage", "hospital"),
        research=("vac", "oxygen", "airlock", "grav", "orbital"), mechanics=("vacuum survival", "asteroid mining", "station salvage", "orbital combat"),
    ),
    "fishing_wildlife": _direction(
        "prosperity", "Рыболовство и специализированная фауна",
        "Рыбалка, продукты моря, обучение необычных животных и торговля редкой фауной.",
        expansion="odyssey", professions=("animal_husbandry", "food_agriculture"), buildings=("barn", "freezer", "storage"),
        research=("fish", "sentience", "animal"), mechanics=("fishing", "animal abilities", "sentience catalyst", "wildlife trade"),
    ),
    "mechhive_crusade": _direction(
        "endgame", "Поход против мехулья",
        "Орбитальные экспедиции, специализированное вооружение и финальный выбор уничтожить или подчинить мехулей.",
        expansion="odyssey", professions=("security_hunting", "research_technology", "craft_industry"), buildings=("factory", "defense", "hospital"),
        research=("mechhive", "grav", "weapon", "vac"), mechanics=("orbital campaign", "mechhive assault", "unique weapons", "hive-mind choice"),
    ),
}


ECONOMY_FAMILIES: dict[str, dict[str, Any]] = {
    "food_crops": {"label": "Поля и переработка еды", "products": {
        "crops": "Излишки долговечных культур", "drugs": "Психоид и наркотики", "brewing": "Хмель и пиво", "travel_food": "Пеммикан и дорожные рационы"}},
    "animals": {"label": "Животные и их продукты", "products": {
        "livestock": "Продажа животных, молока, шерсти, яиц и кожи", "biofuel": "Бумалопы и химтопливо"}},
    "manufacturing": {"label": "Ремесло и промышленность", "products": {
        "tailoring": "Одежда", "art": "Скульптуры", "stoneblocks": "Каменные блоки", "weapons": "Оружие", "armor": "Броня", "components": "Компоненты"}},
    "extraction": {"label": "Добыча ресурсов", "products": {
        "mining": "Руды, глубокое бурение и дальнее сканирование"}},
    "commerce": {"label": "Торговля и услуги", "products": {
        "caravan_trade": "Караванная торговля", "orbital": "Орбитальная торговля", "quest_rewards": "Квесты и награды"}},
    "biotech": {"label": "Биотехнологии", "requires": "biotech", "products": {
        "genes": "Гены и ксеногермы", "mechanoids": "Механоиды и субядра", "organs": "Органы пленных с учётом морали"}},
    "anomaly": {"label": "Аномальная индустрия", "requires": "anomaly", "products": {
        "bioferrite": "Биоферрит и содержание сущностей", "anomaly_arms": "Аномальные сыворотки и оружие"}},
    "salvage_raiding": {"label": "Трофеи и экспедиционная добыча", "products": {
        "raiding": "Набеги на поселения", "salvage": "Руины и квестовые объекты", "orbital_salvage": "Орбитальная добыча"}},
}

PRODUCT_REQUIREMENTS = {"genes": "biotech", "mechanoids": "biotech", "bioferrite": "anomaly", "anomaly_arms": "anomaly", "orbital_salvage": "odyssey"}

TECHNOLOGY = {
    "starflight": ("Звёздный корабль", None), "industrial": ("Промышленность и компоненты", None),
    "agriculture": ("Сельское хозяйство и питание", None), "medical": ("Медицина и протезирование", None),
    "military": ("Вооружение и оборона", None), "energy": ("Энергия и климат", None),
    "trade_logistics": ("Связь, транспорт и логистика", None), "psycasting": ("Псионика", "royalty"),
    "royal_permits": ("Имперские технологии и разрешения", "royalty"), "transhumanism": ("Биоскульптинг и нейроулучшения", "ideology"),
    "mechanitor": ("Механиторы и мехи", "biotech"), "genetics": ("Генетика", "biotech"),
    "pollution": ("Отходы и загрязнение", "biotech"), "containment": ("Содержание и изучение сущностей", "anomaly"),
    "void_research": ("Технологии Бездны", "anomaly"), "gravtech": ("Гравитех и полёт", "odyssey"),
    "orbital_life_support": ("Вакуум и жизнеобеспечение", "odyssey"),
}

DEFENSE = {
    "fortified_depth": ("Эшелонированная крепость", None), "mobile_response": ("Мобильный резерв", None),
    "ranged_firepower": ("Дальнобойный огонь", None), "melee_chokepoints": ("Ближний бой в проходах", None),
    "turret_mortar": ("Турели и миномёты", None), "peaceful_deterrence": ("Минимальная оборона и сдерживание", None),
    "psychic_force": ("Псионическая поддержка", "royalty"), "mechanized_force": ("Боевые мехи", "biotech"),
    "anomaly_weapons": ("Сущности и технологии Бездны", "anomaly"), "gravship_security": ("Оборона мобильного корабля", "odyssey"),
}

SOCIETY = {
    "pragmatic": ("Прагматичная община", None), "egalitarian": ("Равноправная община", None),
    "hierarchical": ("Иерархическая специализация", None), "royal": ("Имперский двор", "royalty"),
    "ideological": ("Следование реальным предписаниям идеологии", "ideology"), "family": ("Семья и образование детей", "biotech"),
    "transhumanist": ("Трансгуманизм", "ideology"), "xenodiverse": ("Ксенотипическое разнообразие", "biotech"),
    "mechanitor": ("Автоматизированная механиторская колония", "biotech"), "sanguophage": ("Сангвофагическая община", "biotech"),
    "anomaly_scholars": ("Исследователи аномалий", "anomaly"), "nomadic_crew": ("Команда мобильного гравикорабля", "odyssey"),
}

ENDGAMES = {
    "enduring_colony": ("Бессрочно процветающая колония", None), "ship_escape": ("Собственный корабль и запуск", None),
    "imperial_ascension": ("Приём верховного стелларха и отлёт с Империей", "royalty"),
    "archonexus": ("Архонексус", "ideology"), "anomaly_void": ("Финал монолита и машинного бога", "anomaly"),
    "mechhive": ("Мехулей и орбитальная кампания", "odyssey"),
}

DIPLOMACY = {
    "peaceful_trade": "Торговля и мир", "alliance_builder": "Союзы и благосклонность", "quest_contractors": "Квесты за награды",
    "humanitarian": "Спасение и помощь", "defensive": "Оборона без лишних войн", "isolationist": "Минимум внешних контактов",
    "expansionist": "Активные экспедиции и силовое давление", "raider": "Систематические набеги",
}

SETTLEMENTS = {
    "compact": ("Компактная связанная база", None), "separate_houses": ("Отдельные дома", None),
    "courtyard": ("Поселение с двором", None), "tribal_village": ("Низкотехнологичная деревня", None),
    "industrial_complex": ("Промышленный комплекс", None), "noble_estate": ("Дворянское поместье", "royalty"),
    "ideological_commune": ("Идеологическая община вокруг храма", "ideology"),
    "mechanitor_hub": ("Автоматизированный механиторский узел", "biotech"),
    "containment_facility": ("Исследовательский комплекс содержания", "anomaly"),
    "gravship": ("Мобильный гравикорабль", "odyssey"),
}

BEAUTY = {"shared_first": "Столовая и отдых", "bedrooms_first": "Спальни", "hospital_work_first": "Больница и рабочие комнаты", "balanced": "Самое слабое важное помещение"}

RESEARCH_TOKENS = {
    "starflight": ("ship", "starflight", "cryptosleep"), "industrial": ("machining", "fabrication", "component"),
    "agriculture": ("hydropon", "devilstrand", "tree sow", "drug", "brewing"), "medical": ("hospital", "medicine", "prosthetic", "bionic"),
    "military": ("weapon", "armor", "turret", "mortar", "gunsmith"), "energy": ("electric", "battery", "geothermal", "biofuel"),
    "trade_logistics": ("microelectronic", "transport", "pod", "scanner"), "psycasting": ("psy", "anima"),
    "royal_permits": ("royal", "prestige"), "transhumanism": ("biosculpt", "neural", "sleep acceler"),
    "mechanitor": ("mechtech", "mechanoid", "gestator", "subcore"), "genetics": ("gene", "xenogen"),
    "pollution": ("wastepack", "pollution", "atomizer"), "containment": ("contain", "entity", "bioferrite"),
    "void_research": ("void", "anomaly", "monolith"), "gravtech": ("grav", "flight"),
    "orbital_life_support": ("vac", "oxygen", "airlock", "orbital"),
}

PRODUCT_RESEARCH_TOKENS = {
    "drugs": ("drug production", "psychite"), "brewing": ("brewing",), "travel_food": ("pemmican", "survival meal"),
    "biofuel": ("biofuel",), "tailoring": ("clothing", "devilstrand"), "art": ("stonecut",),
    "weapons": ("gunsmith", "weapon", "machining"), "armor": ("armor", "smith"), "components": ("fabrication", "component"),
    "mining": ("deep drill", "scanner", "mining"), "orbital": ("microelectronic",), "genes": ("gene", "xenogen"),
    "mechanoids": ("mechtech", "mechanoid", "gestator"), "bioferrite": ("bioferrite", "contain"),
    "anomaly_arms": ("void", "anomaly"), "orbital_salvage": ("grav", "vac", "orbital"),
}


def active_expansions(context: dict[str, Any]) -> dict[str, bool]:
    package_ids = {
        str(row.get("package_id") or row.get("packageId") or "").lower()
        for row in context.get("active_mods") or [] if isinstance(row, dict)
    }
    flags = {name: package.lower() in package_ids for name, package in EXPANSION_PACKAGES.items()}
    # These two existing API contexts are reliable fallbacks on older RIMAPI
    # versions where the mods list may be unavailable.
    if (context.get("ideology") or {}).get("active"):
        flags["ideology"] = True
    if (context.get("royalty") or {}).get("active"):
        flags["royalty"] = True
    return flags


def _requires_available(requirement: str | None, flags: dict[str, bool]) -> bool:
    return not requirement or bool(flags.get(requirement))


def audit_directions(context: dict[str, Any]) -> dict[str, Any]:
    flags = active_expansions(context)
    professions = context.get("profession_directions") or {}
    buildings = context.get("building_catalog") or []
    research = context.get("research_tree") or []
    building_text = " ".join(
        f"{row.get('def_name', '')} {row.get('label', '')} {row.get('description', '')}".lower()
        for row in buildings if isinstance(row, dict)
    )
    research_text = " ".join(
        f"{row.get('name', '')} {row.get('label', '')} {row.get('description', '')}".lower()
        for row in research if isinstance(row, dict)
    )
    available: dict[str, dict[str, Any]] = {}
    unavailable: dict[str, dict[str, Any]] = {}
    by_domain: Counter[str] = Counter()
    for name, spec in DIRECTIONS.items():
        expansion = spec.get("expansion")
        if not _requires_available(expansion, flags):
            unavailable[name] = {**spec, "reason": f"requires inactive {expansion} content"}
            continue
        workforce = sum(float((professions.get(key) or {}).get("fit_score") or 0) for key in spec.get("professions") or ())
        tokens = tuple(str(token).lower() for token in spec.get("research_tokens") or ())
        live_signals = sum(1 for token in tokens if token in research_text or token in building_text)
        score = round(workforce + live_signals * 8.0, 1)
        row = {**spec, "fit_score": score, "live_signals": live_signals}
        available[name] = row
        by_domain[str(spec["domain"])] += 1
    return {
        "schema_version": 2,
        "expansions": flags,
        "available": dict(sorted(available.items(), key=lambda item: (-item[1]["fit_score"], item[0]))),
        "unavailable": unavailable,
        "domains": dict(by_domain),
        "coverage": {"total": len(DIRECTIONS), "available": len(available), "unavailable": len(unavailable)},
    }


def domain_options(audit: dict[str, Any]) -> dict[str, str]:
    return {
        domain: f"{DOMAIN_LABELS[domain]} — {count} доступных направлений"
        for domain, count in (audit.get("domains") or {}).items() if count
    }


def direction_options(audit: dict[str, Any], domain: str) -> dict[str, str]:
    return {
        name: (
            f"{row['label']}: {row['summary']} Кадровое/контентное соответствие {row['fit_score']}; "
            f"механики: {', '.join(row.get('mechanics') or ())}"
        )
        for name, row in (audit.get("available") or {}).items() if row.get("domain") == domain
    }


def _filter_axis(rows: dict[str, tuple[str, str | None]], flags: dict[str, bool]) -> dict[str, str]:
    return {name: label for name, (label, requirement) in rows.items() if _requires_available(requirement, flags)}


def _ask(agent: Any, state: dict[str, Any], question_id: str, instructions: str, criteria: dict[str, str]) -> tuple[str, dict[str, Any]]:
    if not criteria:
        return "", {"answers": {}}
    return ask_laya_choice(agent, state, question_id, instructions, criteria)


def choose_cascaded_doctrine(agent: Any, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    audit = context.get("direction_audit") or audit_directions(context)
    flags = audit.get("expansions") or {}
    raw_steps: list[dict[str, Any]] = []
    answers: dict[str, Any] = {}

    domain, raw = _ask(agent, state, "doctrine_domain", "Choose the colony's broad development domain first.", domain_options(audit))
    raw_steps.append(raw); answers.update(raw.get("answers", {}))
    direction, raw = _ask(agent, state, "doctrine_primary_direction", "Now choose one exact long-term direction supported by live workforce and loaded content.", direction_options(audit, domain))
    raw_steps.append(raw); answers.update(raw.get("answers", {}))

    settlements = _filter_axis(SETTLEMENTS, flags)
    if context.get("mountain_possible"):
        settlements["mountain"] = "Горная база: защищённая и пожаростойкая, но медленная и уязвимая для заражений"
    family_options = {
        key: str(row["label"]) for key, row in ECONOMY_FAMILIES.items()
        if _requires_available(row.get("requires"), flags)
    }
    independent = {
        "doctrine_settlement_form": {"type": "choice", "instructions": "Choose future settlement topology; never rebuild existing rooms only to match it.", "criteria": settlements},
        "doctrine_economy_family": {"type": "choice", "instructions": "Choose the economic family. A product question will follow only for this family.", "criteria": family_options},
        "doctrine_technology": {"type": "choice", "instructions": "Choose the primary technology focus; research still respects live prerequisites.", "criteria": _filter_axis(TECHNOLOGY, flags)},
        "doctrine_military": {"type": "choice", "instructions": "Choose a defense doctrine that will filter fortifications, research and combat preparation.", "criteria": _filter_axis(DEFENSE, flags)},
        "doctrine_society": {"type": "choice", "instructions": "Choose social organization without violating the colony's actual ideology precepts.", "criteria": _filter_axis(SOCIETY, flags)},
        "doctrine_endgame": {"type": "choice", "instructions": "Choose the long-horizon victory or continuity objective.", "criteria": _filter_axis(ENDGAMES, flags)},
        "doctrine_diplomacy": {"type": "choice", "instructions": "Choose the external posture; individual quests and wars still require live risk evaluation.", "criteria": dict(DIPLOMACY)},
        "doctrine_material": {"type": "choice", "instructions": "Choose the default material for new structures only, from sufficient current reserves.", "criteria": dict(context.get("material_options") or {"WoodLog": "wood"})},
        "doctrine_beauty": {"type": "choice", "instructions": "Choose where beauty investment has priority.", "criteria": dict(BEAUTY)},
    }
    profession_choices = context.get("profession_choices") or {}
    if profession_choices:
        independent["doctrine_specialization"] = {
            "type": "choice", "instructions": "Choose the workforce specialization supported by actual skills, passions and disabled work.", "criteria": profession_choices,
        }
    for question_id, question in independent.items():
        _, raw_axis = _ask(agent, state, question_id, str(question["instructions"]), dict(question["criteria"]))
        raw_steps.append(raw_axis)
        answers.update(raw_axis.get("answers", {}))

    family = str(answers["doctrine_economy_family"]["choice"])
    products = {
        name: description for name, description in (ECONOMY_FAMILIES.get(family) or {}).get("products", {}).items()
        if _requires_available(PRODUCT_REQUIREMENTS.get(name), flags)
    }
    product, raw = _ask(agent, state, "doctrine_economy_product", "The economic family is fixed; choose its exact product or revenue mechanism.", products)
    raw_steps.append(raw); answers.update(raw.get("answers", {}))

    mining_product = None
    if product == "mining":
        minerals = {
            str(name): f"{count} видимых клеток руды"
            for name, count in (context.get("ores") or {}).items()
            if int(count or 0) > 0 and any(token in str(name).lower() for token in ("gold", "silver", "jade", "uranium", "plasteel", "steel"))
        }
        if minerals:
            mining_product, raw = _ask(agent, state, "doctrine_mining_product", "Mining was selected; choose the verified local mineral priority.", minerals)
            raw_steps.append(raw); answers.update(raw.get("answers", {}))

    selection = {
        "schema_version": 2,
        "domain": domain,
        "primary_direction": direction,
        "settlement_form": answers["doctrine_settlement_form"]["choice"],
        "economy_family": family,
        "economy_product": product,
        "economy": product,
        "mining_product": mining_product,
        "technology": answers["doctrine_technology"]["choice"],
        "military": answers["doctrine_military"]["choice"],
        "society": answers["doctrine_society"]["choice"],
        "endgame": answers["doctrine_endgame"]["choice"],
        "diplomacy": answers["doctrine_diplomacy"]["choice"],
        "material": answers["doctrine_material"]["choice"],
        "beauty": answers["doctrine_beauty"]["choice"],
        "specialization": (answers.get("doctrine_specialization") or {}).get("choice") or "food_agriculture",
        "building_programs": list((DIRECTIONS.get(direction) or {}).get("building_programs") or ()),
        "labels": doctrine_labels({
            "domain": domain, "primary_direction": direction, "settlement_form": answers["doctrine_settlement_form"]["choice"],
            "economy_family": family, "economy_product": product, "technology": answers["doctrine_technology"]["choice"],
            "military": answers["doctrine_military"]["choice"], "society": answers["doctrine_society"]["choice"],
            "endgame": answers["doctrine_endgame"]["choice"], "diplomacy": answers["doctrine_diplomacy"]["choice"],
        }),
    }
    return {"selection": selection, "answers": answers, "raw_steps": raw_steps, "audit": audit}


def doctrine_labels(doctrine: dict[str, Any]) -> dict[str, str]:
    def axis_label(rows: dict[str, tuple[str, str | None]], key: str) -> str:
        return (rows.get(str(doctrine.get(key))) or (str(doctrine.get(key) or "—"), None))[0]
    direction = DIRECTIONS.get(str(doctrine.get("primary_direction"))) or {}
    family = ECONOMY_FAMILIES.get(str(doctrine.get("economy_family"))) or {}
    product = str(doctrine.get("economy_product") or doctrine.get("economy") or "—")
    product_label = str((family.get("products") or {}).get(product) or product)
    return {
        "domain": DOMAIN_LABELS.get(str(doctrine.get("domain")), str(doctrine.get("domain") or "—")),
        "primary_direction": str(direction.get("label") or doctrine.get("primary_direction") or "—"),
        "settlement_form": str(doctrine.get("settlement_form") or "—"),
        "economy": product_label,
        "technology": axis_label(TECHNOLOGY, "technology"),
        "military": axis_label(DEFENSE, "military"),
        "society": axis_label(SOCIETY, "society"),
        "endgame": axis_label(ENDGAMES, "endgame"),
        "diplomacy": DIPLOMACY.get(str(doctrine.get("diplomacy")), str(doctrine.get("diplomacy") or "—")),
    }


def legacy_income(doctrine: dict[str, Any]) -> str:
    return str(doctrine.get("economy_product") or doctrine.get("economy") or "crops")


def doctrine_research_candidates(doctrine: dict[str, Any], research_tree: list[dict[str, Any]], limit: int = 12) -> dict[str, str]:
    direction = DIRECTIONS.get(str(doctrine.get("primary_direction"))) or {}
    tokens = list(direction.get("research_tokens") or ())
    tokens.extend(RESEARCH_TOKENS.get(str(doctrine.get("technology")), ()))
    tokens.extend(PRODUCT_RESEARCH_TOKENS.get(str(doctrine.get("economy_product") or doctrine.get("economy")), ()))
    endgame_tokens = {
        "ship_escape": ("ship", "cryptosleep"), "imperial_ascension": ("royal", "prestige"),
        "archonexus": ("archonexus",), "anomaly_void": ("anomaly", "void", "monolith"), "mechhive": ("grav", "mechhive", "vac"),
    }
    tokens.extend(endgame_tokens.get(str(doctrine.get("endgame")), ()))
    lowered = tuple(dict.fromkeys(str(token).lower() for token in tokens if token))
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for row in research_tree or []:
        if not isinstance(row, dict) or row.get("is_finished") or not row.get("can_start_now"):
            continue
        name = str(row.get("name") or "")
        if not name:
            continue
        text = f"{name} {row.get('label', '')} {row.get('description', '')}".lower()
        matches = sum(1 for token in lowered if token in text)
        if matches <= 0:
            continue
        score = matches * 10.0 - float(row.get("research_points") or 0) / 10000.0
        scored.append((score, name, row))
    result: dict[str, str] = {}
    for _, name, row in sorted(scored, reverse=True)[:limit]:
        result[name] = (
            f"{row.get('label') or name}; {row.get('tech_level')}; cost {row.get('research_points')}; "
            f"prerequisites {row.get('prerequisites') or []}; {str(row.get('description') or '')[:220]}"
        )
    return result
