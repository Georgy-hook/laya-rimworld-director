from __future__ import annotations

from typing import Any


# These are strategic templates, not scripts with fixed coordinates.  RIMAPI
# resolves positions against the live map and rejects every route that crosses
# a friendly trap.  Keeping the catalogue here lets the model compare tactics
# without making the low-level safety code part of its prompt.
TACTICS: dict[str, dict[str, Any]] = {
    "hold_cover": {
        "label": "Hold strong cover",
        "description": "Use nearby walls, barricades, sandbags or shelves and make the enemy cross open ground.",
        "tags": {"general", "ranged", "defense"},
    },
    "focus_fire": {
        "label": "Concentrated fire",
        "description": "All safe shooters attack one high-priority target, reducing enemy damage quickly instead of spreading wounds.",
        "tags": {"general", "ranged"},
    },
    "firing_line": {
        "label": "Safe firing line",
        "description": "Form a spaced line behind cover; adjacent shooters remain inside the short friendly-fire-safe envelope.",
        "tags": {"general", "ranged", "defense"},
    },
    "spread_out": {
        "label": "Disperse against explosives",
        "description": "Keep several cells between fighters to limit rockets, grenades, fire and area psycasts.",
        "tags": {"explosive", "siege", "drop_pod", "mechanoid"},
    },
    "kite": {
        "label": "Kite slow melee enemies",
        "description": "A fast ranged pawn draws pursuit while the firing group shoots; retreat paths must contain no friendly traps.",
        "tags": {"melee_enemy", "animal", "insect", "open_field"},
    },
    "staggered_retreat": {
        "label": "Staggered retreat",
        "description": "One element moves to the fallback line while the other covers, preventing a simultaneous rout.",
        "tags": {"general", "fallback", "ranged"},
    },
    "melee_block": {
        "label": "Three-on-one melee block",
        "description": "Hold a one-cell doorway or choke with up to three armored melee pawns and shoot over them from directly behind.",
        "tags": {"melee_enemy", "insect", "animal", "choke"},
    },
    "door_defense": {
        "label": "Doorway defense",
        "description": "Use an owned doorway as a controlled choke with short retreat access to the hospital and inner base.",
        "tags": {"melee_enemy", "drop_pod", "breach", "defense"},
    },
    "killbox_hold": {
        "label": "Hold the prepared kill zone",
        "description": "Occupy the colony's actual funnel and firing positions instead of chasing enemies outside it.",
        "tags": {"assault", "killbox", "defense"},
    },
    "fallback_line": {
        "label": "Withdraw to internal defenses",
        "description": "Use the verified inner firing line when breachers, drop pods or insects bypass the outer defenses.",
        "tags": {"breach", "drop_pod", "insect", "fallback"},
    },
    "wide_flank": {
        "label": "Wide flanking arc",
        "description": "Split healthy shooters between the main position and a safe side angle to negate one-direction cover.",
        "tags": {"siege", "staging", "ranged", "open_field"},
    },
    "pincer": {
        "label": "Two-sided pincer",
        "description": "Use two mutually supporting groups against a static or cover-dependent enemy; never isolate a single pawn.",
        "tags": {"siege", "staging", "cluster", "ranged"},
    },
    "counter_snipe": {
        "label": "Counter-snipe",
        "description": "Only long-range shooters expose themselves; everyone else remains behind cover or in reserve.",
        "tags": {"siege", "sniper", "staging"},
    },
    "rush_ranged": {
        "label": "Melee rush on ranged threats",
        "description": "Armored, mobile melee fighters close on isolated gunners so those enemies cannot continue firing.",
        "tags": {"ranged_enemy", "close_quarters"},
    },
    "emp_control": {
        "label": "EMP control",
        "description": "Stun mechanoids or shields with a verified EMP weapon while conventional fire focuses one disabled target.",
        "tags": {"mechanoid", "shield"},
    },
    "smoke_advance": {
        "label": "Smoke-covered advance",
        "description": "Advance under smoke against turrets or static guns, with melee and short-range weapons protected by the screen.",
        "tags": {"turret", "cluster", "siege"},
    },
    "siege_harass": {
        "label": "Hit-and-run against a siege",
        "description": "Long-range mobile shooters fire from maximum range and withdraw before the preparing enemy can answer.",
        "tags": {"siege", "staging", "open_field"},
    },
    "mortar_counterbattery": {
        "label": "Mortar counter-battery",
        "description": "Use completed, supplied mortars from the protected mortar post instead of crossing the map on foot.",
        "tags": {"siege", "cluster", "mortar"},
    },
    "drop_pod_encircle": {
        "label": "Encircle drop pods",
        "description": "Evacuate civilians, spread armed pawns around the landing room and attack from multiple doors after pods open.",
        "tags": {"drop_pod", "close_quarters"},
    },
    "infestation_choke": {
        "label": "Contain an infestation at a choke",
        "description": "Do not enter the hive room piecemeal; block its exit and concentrate short-range fire behind armored melee.",
        "tags": {"insect", "choke"},
    },
    "infestation_burn": {
        "label": "Controlled infestation burn",
        "description": "Only burn a sealed stone compartment after checking escape routes, temperature exposure and valuable contents.",
        "tags": {"insect", "fire"},
    },
    "cluster_poke": {
        "label": "Wake a mech cluster from range",
        "description": "Use maximum range or indirect fire, then withdraw to prepared EMP and firing positions before machines engage.",
        "tags": {"mechanoid", "cluster", "staging"},
    },
    "intercept_kidnapper": {
        "label": "Intercept a kidnapper",
        "description": "Fast healthy fighters cut off a fleeing pawn carrying a colonist; other defenders cover the route and hospital access.",
        "tags": {"kidnap", "rescue"},
    },
    "covered_rescue": {
        "label": "Rescue under covering fire",
        "description": "A mobile reserve rescues a downed ally only after shooters suppress the nearest threat and the route is clear.",
        "tags": {"rescue", "general"},
    },
    "fire_retreat": {
        "label": "Retreat from fire and heat",
        "description": "Break contact through a non-burning route and use the firefoam-protected fallback rather than fighting in superheated rooms.",
        "tags": {"fire", "fallback"},
    },
    "psycast_control": {
        "label": "Psychic crowd control",
        "description": "Use a feasible hostile psycast such as stun, vertigo, berserk, skip or wall control without exceeding heat or psyfocus limits.",
        "tags": {"psycast", "general"},
    },
    "psycast_support": {
        "label": "Psychic mobility/support",
        "description": "Use a feasible allied psycast such as focus, invisibility, waterskip or skip to rescue, reposition or protect the line.",
        "tags": {"psycast", "rescue", "general"},
    },
    "stand_down": {
        "label": "Stand down",
        "description": "Undraft everyone when the combat API verifies that no hostile pawn remains.",
        "tags": {"post_combat"},
    },
}


MECH_TOKENS = ("mech", "scyther", "lancer", "centipede", "pikeman", "militor", "tesseron", "termite", "diabolus", "war queen")
INSECT_TOKENS = ("insect", "megaspider", "spelopede", "megascarab")
EXPLOSIVE_TOKENS = ("grenade", "doomsday", "triple rocket", "inferno", "mortar")


def _text(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(key) or "") for key in ("name", "kind_def", "faction", "weapon_def", "weapon_label", "current_job")).lower()


def _defense_types(snapshot: dict[str, Any]) -> set[str]:
    return {str(row.get("kind") or "").lower() for row in snapshot.get("combat", {}).get("defenses", [])}


def available_tactics(snapshot: dict[str, Any]) -> dict[str, str]:
    combat = snapshot.get("combat", {})
    hostiles = [row for row in combat.get("hostiles", []) if not row.get("is_dead") and not row.get("is_downed")]
    fighters = [row for row in combat.get("colonists", []) if not row.get("is_dead") and not row.get("is_downed") and float(row.get("health") or 0) >= 0.6]
    if not hostiles:
        return {"stand_down": TACTICS["stand_down"]["description"]} if any(row.get("is_drafted") for row in fighters) else {}

    hostile_text = [_text(row) for row in hostiles]
    hostile_jobs = " ".join(hostile_text)
    defenses = _defense_types(snapshot)
    ranged = [row for row in fighters if row.get("has_ranged_weapon")]
    melee = [row for row in fighters if not row.get("has_ranged_weapon") or int(row.get("melee_skill") or 0) >= int(row.get("shooting_skill") or 0) + 3]
    psycasts = [ability for pawn in fighters for ability in (pawn.get("psycasts") or []) if ability.get("can_cast")]
    weapons = combat.get("available_weapons", [])
    has_emp = any("emp" in _text(row) for row in weapons + fighters)
    has_smoke = any("smoke" in _text(row) for row in weapons + fighters)
    has_explosives = any(any(token in text for token in EXPLOSIVE_TOKENS) for text in hostile_text)
    has_mechs = any(any(token in text for token in MECH_TOKENS) for text in hostile_text)
    has_insects = any(any(token in text for token in INSECT_TOKENS) for text in hostile_text)
    has_kidnapper = "kidnap" in hostile_jobs or any(row.get("carrying_pawn_id") for row in hostiles)
    staging = all(float(row.get("distance_to_nearest_opponent") or 0) > 35 for row in fighters) and not any(
        token in hostile_jobs for token in ("attack", "breach", "sap", "kidnap", "steal")
    )

    names: list[str] = ["hold_cover", "focus_fire"]
    if len(ranged) >= 2:
        names += ["firing_line", "staggered_retreat"]
    if has_explosives or len(hostiles) >= 8:
        names.append("spread_out")
    if melee:
        names += ["melee_block", "door_defense"]
    if "killbox" in defenses or "trap" in defenses:
        names.append("killbox_hold")
    if "fallback" in defenses or "door" in defenses or "barricade" in defenses:
        names.append("fallback_line")
    if staging and len(ranged) >= 3:
        names += ["wide_flank", "pincer", "counter_snipe", "siege_harass"]
    if "mortar" in defenses and staging:
        names.append("mortar_counterbattery")
    if any("drop" in text for text in hostile_text) or "waitmaintainposture" in hostile_jobs:
        names.append("drop_pod_encircle")
    if has_mechs:
        names.append("cluster_poke")
        if has_emp:
            names.append("emp_control")
        if has_smoke:
            names.append("smoke_advance")
    if has_insects:
        names += ["infestation_choke", "kite"]
        if "firefoam" in defenses:
            names.append("infestation_burn")
    if any("animal" in text or "manhunter" in text for text in hostile_text):
        names.append("kite")
    if any("gun" in text or "sniper" in text or "lancer" in text for text in hostile_text) and melee:
        names.append("rush_ranged")
    if has_kidnapper:
        names.insert(0, "intercept_kidnapper")
    if any(row.get("is_downed") for row in combat.get("colonists", [])):
        names.append("covered_rescue")
    if psycasts:
        if any(ability.get("hostile") for ability in psycasts):
            names.append("psycast_control")
        if any(not ability.get("hostile") for ability in psycasts):
            names.append("psycast_support")

    result: dict[str, str] = {}
    for name in names:
        if name not in result:
            result[name] = TACTICS[name]["description"]
    return result


def psycast_options(snapshot: dict[str, Any], hostile: bool | None = None) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for pawn in snapshot.get("combat", {}).get("colonists", []):
        if pawn.get("is_dead") or pawn.get("is_downed"):
            continue
        for ability in pawn.get("psycasts") or []:
            if not ability.get("can_cast"):
                continue
            if hostile is not None and bool(ability.get("hostile")) != hostile:
                continue
            key = f"{int(pawn['id'])}:{ability.get('def_name')}"
            result[key] = {
                "pawn_id": int(pawn["id"]),
                "pawn": pawn.get("name"),
                **ability,
                "summary": (
                    f"{pawn.get('name')} — {ability.get('label') or ability.get('def_name')}; "
                    f"focus {float(pawn.get('psyfocus') or 0) * 100:.0f}%, "
                    f"heat {float(pawn.get('neural_heat') or 0):.0f}/{float(pawn.get('neural_heat_limit') or 0):.0f}; "
                    f"cost {float(ability.get('psyfocus_cost') or 0) * 100:.1f}% focus, "
                    f"+{float(ability.get('entropy_gain') or 0):.0f} heat; {ability.get('description') or ''}"
                ),
            }
    return result


def choose_default_target(snapshot: dict[str, Any], tactic: str) -> int | None:
    hostiles = [row for row in snapshot.get("combat", {}).get("hostiles", []) if not row.get("is_dead") and not row.get("is_downed")]
    if not hostiles:
        return None
    if tactic == "intercept_kidnapper":
        kidnapping = [row for row in hostiles if "kidnap" in _text(row) or row.get("carrying_pawn_id")]
        if kidnapping:
            hostiles = kidnapping
    if tactic in {"emp_control", "cluster_poke"}:
        mechs = [row for row in hostiles if any(token in _text(row) for token in MECH_TOKENS)]
        if mechs:
            hostiles = mechs
    return int(max(hostiles, key=lambda row: (float(row.get("combat_power") or 0), float(row.get("market_value") or 0), -float(row.get("health") or 1))).get("id"))
