from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_API_URL = "http://localhost:8765"
DEFAULT_MODEL = "convaiinnovations/laya"
__version__ = "0.0.2"
SAFE_WORK_TYPES = {
    "prioritize_cooking": "Cooking",
    "prioritize_growing": "Growing",
    "prioritize_hauling": "Hauling",
    "prioritize_construction": "Construction",
    "prioritize_cleaning": "Cleaning",
}
COMBAT_CHOICES = {
    "engage_ranged",
    "engage_melee",
    "equip_ranged_weapon",
    "equip_melee_weapon",
    "draft_best_defender",
    "hold_and_observe",
    "stand_down",
    "remain_drafted",
    "prepare_undrafted",
    "preemptive_strike",
    "equip_emp_weapon",
    "focus_mechanoids",
    "focus_insects",
}


class RimApiError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def unwrap(envelope: Any, endpoint: str) -> Any:
    if not isinstance(envelope, dict):
        raise RimApiError(f"{endpoint}: expected a JSON object")
    if envelope.get("success") is False:
        errors = envelope.get("errors") or ["unknown RIMAPI error"]
        raise RimApiError(f"{endpoint}: {'; '.join(map(str, errors))}")
    return envelope.get("data", envelope)


@dataclass
class RimApiClient:
    base_url: str = DEFAULT_API_URL
    timeout: float = 8.0

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("RIMAPI URL must be a local http:// address")
        self.base_url = self.base_url.rstrip("/") + "/"

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
    ) -> Any:
        url = urljoin(self.base_url, endpoint.lstrip("/"))
        if query:
            url += "?" + urlencode(query)
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8-sig"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RimApiError(f"{endpoint}: HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RimApiError(f"{endpoint}: {exc}") from exc
        return unwrap(payload, endpoint)

    def get(self, endpoint: str, **query: Any) -> Any:
        return self.request("GET", endpoint, query=query or None)

    def post(self, endpoint: str, *, query: dict[str, Any] | None = None, body: Any | None = None) -> Any:
        return self.request("POST", endpoint, query=query, body=body)


def first_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_colonists(rows: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return result
    for row in rows:
        if not isinstance(row, dict):
            continue
        pawn = row.get("pawn") or row.get("colonist") or row
        details = row.get("detailes") or row
        medical = details.get("medical_info") or details.get("colonist_medical_info") or {}
        work = details.get("work_info") or details.get("colonist_work_info") or {}
        skills = {
            str(skill.get("name")): {
                "level": int(first_number(skill.get("level"))),
                "passion": int(first_number(skill.get("passion"))),
                "disabled": bool(skill.get("totally_disabled")),
            }
            for skill in (work.get("skills") or [])
            if isinstance(skill, dict) and skill.get("name")
        }
        priorities = {
            str(item.get("work_type")): {
                "priority": int(first_number(item.get("priority"))),
                "disabled": bool(item.get("is_totally_disabled")),
            }
            for item in (work.get("work_priorities") or [])
            if isinstance(item, dict) and item.get("work_type")
        }
        traits = [
            {
                "name": str(item.get("name") or ""),
                "label": str(item.get("label") or item.get("name") or ""),
                "description": str(item.get("description") or ""),
                "suppressed": bool(item.get("suppressed")),
            }
            for item in (work.get("traits") or [])
            if isinstance(item, dict) and not item.get("suppressed")
        ]
        hediffs = [
            {
                "def_name": str(item.get("def_name") or ""),
                "label": str(item.get("label") or item.get("label_cap") or ""),
                "part": str(item.get("part_label") or item.get("part_def_name") or ""),
                "severity": round(first_number(item.get("severity")), 3),
                "permanent": bool(item.get("is_permanent")),
                "bleeding": bool(item.get("bleeding")),
                "tendable_now": bool(item.get("tendable_now")),
            }
            for item in (medical.get("hediffs") or [])
            if isinstance(item, dict) and item.get("visible", True)
        ]
        pawn_id = pawn.get("id")
        if pawn_id is None:
            continue
        result.append(
            {
                "id": int(pawn_id),
                "name": str(pawn.get("name") or pawn_id),
                "gender": str(pawn.get("gender") or "None"),
                "age": int(first_number(pawn.get("age"))),
                "health": round(first_number(pawn.get("health"), 1.0), 3),
                "mood": round(first_number(pawn.get("mood"), 0.5), 3),
                "hunger": round(first_number(pawn.get("hunger"), 0.5), 3),
                "rest": round(first_number(details.get("sleep"), 0.5), 3),
                "joy": round(first_number(details.get("joy"), 0.5), 3),
                "bleeding_rate": round(first_number(medical.get("bleeding_rate"), 0.0), 3),
                "downed": bool(medical.get("is_downed")),
                "current_job": str(work.get("current_job") or work.get("job") or "unknown"),
                "inspiration": str(work.get("inspiration_def_name") or ""),
                "position": pawn.get("position") or {},
                "skills": skills,
                "work_priorities": priorities,
                "traits": traits,
                "health_conditions": hediffs,
                "capacities": {
                    "consciousness": round(first_number(medical.get("consciousness"), 1.0), 3),
                    "moving": round(first_number(medical.get("moving"), 1.0), 3),
                    "manipulation": round(first_number(medical.get("manipulation"), 1.0), 3),
                    "sight": round(first_number(medical.get("sight"), 1.0), 3),
                },
                "pain": round(first_number(medical.get("pain")), 3),
                "relations": (details.get("social_info") or {}).get("direct_relations") or [],
            }
        )
    return result


def summarize_resources(things: Any) -> dict[str, int]:
    totals = {"food": 0, "meals": 0, "medicine": 0, "wood": 0, "steel": 0, "components": 0}
    if not isinstance(things, list):
        return totals
    for item in things:
        if not isinstance(item, dict) or item.get("is_forbidden"):
            continue
        name = str(item.get("def_name") or "").lower()
        categories = " ".join(map(str, item.get("categories") or [])).lower()
        amount = max(0, int(first_number(item.get("stack_count"), 1)))
        if "food" in categories or name.startswith("meal") or name.endswith("meat"):
            totals["food"] += amount
        if name.startswith("meal") or "foodmeals" in categories:
            totals["meals"] += amount
        if "medicine" in name:
            totals["medicine"] += amount
        if name == "woodlog":
            totals["wood"] += amount
        if name == "steel":
            totals["steel"] += amount
        if "component" in name:
            totals["components"] += amount
    return totals


def normalize_resource_summary(summary: Any) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {"food": 0, "meals": 0, "raw_food": 0, "nutrition": 0.0, "medicine": 0, "weapons": 0}
    critical = summary.get("critical_resources") or {}
    food = critical.get("food_summary") or {}
    return {
        "food": int(first_number(food.get("food_total"))),
        "meals": int(first_number(food.get("meals_count"))),
        "raw_food": int(first_number(food.get("raw_food_count"))),
        "nutrition": round(first_number(food.get("total_nutrition")), 2),
        "medicine": int(first_number(critical.get("medicine_total"))),
        "weapons": int(first_number(critical.get("weapon_count"))),
    }


def safe_get(client: RimApiClient, endpoint: str, warnings: list[str], **query: Any) -> Any:
    try:
        return client.get(endpoint, **query)
    except RimApiError as exc:
        warnings.append(str(exc))
        return None


def collect_snapshot(client: RimApiClient) -> dict[str, Any]:
    warnings: list[str] = []
    game = client.get("/api/v1/game/state")
    maps = client.get("/api/v1/maps")
    if not isinstance(maps, list) or not maps:
        raise RimApiError("RIMAPI reports no loaded map; load a colony first")
    home = next((m for m in maps if m.get("is_player_home")), maps[0])
    map_id = int(home.get("id", home.get("index", 0)))

    raw_colonists = safe_get(client, "/api/v2/colonists/detailed", warnings)
    if raw_colonists is None:
        raw_colonists = client.get("/api/v1/colonists")
    colonists = normalize_colonists(raw_colonists)
    creatures = safe_get(client, "/api/v1/map/creatures/summary", warnings, map_id=map_id) or {}
    farm = safe_get(client, "/api/v1/map/farm/summary", warnings, map_id=map_id) or {}
    date_info = safe_get(client, "/api/v1/datetime", warnings) or {}
    resource_summary = safe_get(client, "/api/v1/resources/summary", warnings, map_id=map_id)
    combat = safe_get(client, "/api/v1/combat/state", warnings, map_id=map_id) or {}
    raw_animals = safe_get(client, "/api/v1/map/animals", warnings, map_id=map_id) or []
    hostiles = combat.get("hostiles") if isinstance(combat, dict) else []
    fighters = combat.get("colonists") if isinstance(combat, dict) else []
    weapons = combat.get("available_weapons") if isinstance(combat, dict) else []

    return {
        "captured_at": utc_now(),
        "game": {
            "tick": game.get("game_tick"),
            "wealth": game.get("colony_wealth"),
            "colonist_count": game.get("colonist_count", len(colonists)),
            "storyteller": game.get("storyteller"),
            "is_paused": bool(game.get("is_paused")),
            "date": date_info.get("datetime"),
        },
        "map": {
            "id": map_id,
            "seed": home.get("seed"),
            "tile_id": home.get("tile_id"),
            "enemies": len(hostiles) if isinstance(hostiles, list) else int(first_number(creatures.get("enemies_count"))),
            "animals": int(first_number(creatures.get("animals_count"))),
            "growing_zones": int(first_number(farm.get("total_growing_zones"))),
            "plants": int(first_number(farm.get("total_plants"))),
            "expected_yield": round(first_number(farm.get("total_expected_yield")), 2),
            "resources": normalize_resource_summary(resource_summary),
        },
        "colonists": colonists,
        "animals": [
            {
                "id": int(row.get("id")),
                "name": str(row.get("name") or row.get("def") or row.get("id")),
                "def": str(row.get("def") or ""),
                "is_colony_animal": bool(row.get("is_colony_animal")),
                "health": round(first_number(row.get("health"), 1.0), 3),
                "hunger": round(first_number(row.get("hunger"), 1.0), 3),
                "bleeding_rate": round(first_number(row.get("bleeding_rate")), 3),
                "tendable_now": bool(row.get("tendable_now")),
                "gender": str(row.get("gender") or "None"),
                "wildness": round(first_number(row.get("wildness"), 1.0), 3),
                "minimum_handling_skill": int(first_number(row.get("minimum_handling_skill"))),
                "manhunter_on_tame_fail_chance": round(first_number(row.get("manhunter_on_tame_fail_chance")), 3),
                "reproductive": bool(row.get("reproductive")),
                "pregnant": bool(row.get("pregnant")),
                "downed": bool(row.get("downed")),
                "dead": bool(row.get("dead")),
                "current_job": str(row.get("current_job") or "unknown"),
                "position": row.get("position") or {},
                "min_comfortable_temperature": round(first_number(row.get("min_comfortable_temperature"), -10.0), 1),
                "max_comfortable_temperature": round(first_number(row.get("max_comfortable_temperature"), 40.0), 1),
            }
            for row in raw_animals
            if isinstance(row, dict) and row.get("id") is not None and bool(row.get("is_colony_animal"))
        ],
        "wild_animals": [
            {
                "id": int(row.get("id")),
                "name": str(row.get("name") or row.get("def") or row.get("id")),
                "def": str(row.get("def") or ""),
                "gender": str(row.get("gender") or "None"),
                "wildness": round(first_number(row.get("wildness"), 1.0), 3),
                "minimum_handling_skill": int(first_number(row.get("minimum_handling_skill"))),
                "manhunter_on_tame_fail_chance": round(first_number(row.get("manhunter_on_tame_fail_chance")), 3),
                "reproductive": bool(row.get("reproductive")),
                "pregnant": bool(row.get("pregnant")),
                "can_tame": bool(row.get("can_be_designated_for_taming")),
                "market_value": round(first_number(row.get("market_value")), 1),
                "meat_amount": int(first_number(row.get("meat_amount"))),
                "leather_amount": int(first_number(row.get("leather_amount"))),
                "combat_power": round(first_number(row.get("combat_power")), 1),
                "predator": bool(row.get("predator")),
                "harm_revenge_chance": round(first_number(row.get("harm_revenge_chance")), 3),
                "position": row.get("position") or {},
                "min_comfortable_temperature": round(first_number(row.get("min_comfortable_temperature"), -10.0), 1),
                "max_comfortable_temperature": round(first_number(row.get("max_comfortable_temperature"), 40.0), 1),
            }
            for row in raw_animals
            if isinstance(row, dict) and row.get("id") is not None and not bool(row.get("is_colony_animal")) and not bool(row.get("dead"))
        ],
        "combat": {
            "available": bool(combat),
            "colonists": fighters if isinstance(fighters, list) else [],
            "hostiles": hostiles if isinstance(hostiles, list) else [],
            "available_weapons": weapons if isinstance(weapons, list) else [],
        },
        "warnings": warnings,
    }


def decision_state(snapshot: dict[str, Any]) -> dict[str, Any]:
    colonists = snapshot["colonists"]
    def stat(name: str, fn: Any, default: float) -> float:
        values = [first_number(c.get(name), default) for c in colonists]
        return round(fn(values), 3) if values else default

    has_hostiles = bool(snapshot["combat"]["hostiles"])
    has_drafted = any(bool(c.get("is_drafted")) for c in snapshot["combat"]["colonists"])
    if has_hostiles:
        task = "Choose one immediate defensive action against verified hostile pawns."
    elif has_drafted:
        task = "The API verifies that no hostile pawns remain; decide whether to end combat readiness."
    else:
        task = "Choose one safe colony work-priority action for the next short interval."
    return {
        "task": task,
        "game": snapshot["game"],
        "threats": snapshot["map"]["enemies"],
        "farm": {
            "zones": snapshot["map"]["growing_zones"],
            "plants": snapshot["map"]["plants"],
            "expected_yield": snapshot["map"]["expected_yield"],
        },
        "resources": snapshot["map"]["resources"],
        "colonist_welfare": {
            "count": len(colonists),
            "lowest_health": stat("health", min, 1.0),
            "lowest_mood": stat("mood", min, 0.5),
            "lowest_food_level": stat("hunger", min, 0.5),
            "highest_bleeding_rate": stat("bleeding_rate", max, 0.0),
        },
        "current_jobs": [c["current_job"] for c in colonists[:8]],
        "combat": snapshot["combat"],
        "constraints": [
            "Do not cheat, spawn items, edit pawn stats, or force combat.",
            "During a threat, use only real drafted colonists and real hostile target IDs.",
            "Only one colonist work priority may be changed per cycle.",
        ],
    }


def make_questions(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if snapshot["combat"]["hostiles"]:
        fighters = [
            pawn for pawn in snapshot["combat"]["colonists"]
            if not pawn.get("is_dead") and not pawn.get("is_downed")
            and first_number(pawn.get("health")) >= 0.72
        ]
        armed_ranged = [pawn for pawn in fighters if pawn.get("has_ranged_weapon")]
        free_ranged = [weapon for weapon in snapshot["combat"].get("available_weapons", []) if weapon.get("is_ranged")]
        active_order = any(
            pawn.get("is_drafted") and str(pawn.get("current_job") or "").startswith("Attack")
            for pawn in fighters
        )
        distances = [first_number(pawn.get("distance_to_nearest_opponent"), 9999) for pawn in fighters]
        nearest = min(distances, default=9999)
        hostile_jobs = [str(row.get("current_job") or "").lower() for row in snapshot["combat"]["hostiles"]]
        hostile_text = [
            " ".join(str(row.get(key) or "") for key in ("name", "kind_def", "faction")).lower()
            for row in snapshot["combat"]["hostiles"]
        ]
        mech_tokens = ("mech", "scyther", "lancer", "centipede", "pikeman", "militor", "tesseron", "termite")
        insect_tokens = ("insect", "megaspider", "spelopede", "megascarab")
        has_mechanoids = any(any(token in text for token in mech_tokens) for text in hostile_text)
        has_insects = any(any(token in text for token in insect_tokens) for text in hostile_text)
        emp_weapons = [
            weapon for weapon in free_ranged
            if "emp" in (str(weapon.get("def_name") or "") + " " + str(weapon.get("label") or "")).lower()
        ]
        assault_jobs = ("attack", "goto", "breach", "sap", "kidnap", "steal")
        staging = nearest > 45 and not any(any(token in job for token in assault_jobs) for job in hostile_jobs)
        criteria: dict[str, str] = {}
        if staging:
            criteria["prepare_undrafted"] = "Raiders are still staging far away: undraft everyone so colonists eat, sleep, treat wounds and work while positions are monitored."
            if armed_ranged and len(fighters) >= 2:
                criteria["preemptive_strike"] = "Launch a coordinated preemptive ranged strike with healthy fighters instead of waiting in drafted mode."
            return {
                "threat_action": {
                    "type": "choice",
                    "instructions": "Raiders appear to be preparing rather than assaulting. Choose between a real coordinated preemptive strike and undrafted preparation. Never leave colonists drafted and idle for the preparation period.",
                    "criteria": criteria,
                }
            }
        if armed_ranged:
            criteria["engage_ranged"] = "Draft every healthy armed shooter and concentrate ranged fire on one nearby hostile."
            if has_mechanoids:
                criteria["focus_mechanoids"] = "Concentrate ranged fire on a verified mechanoid target; use cover and do not send an isolated melee pawn into charge-lance fire."
            if has_insects:
                criteria["focus_insects"] = "Concentrate ranged fire on the nearest insect while the group stays together; avoid waking or chasing a whole hive piecemeal."
        if has_mechanoids and emp_weapons:
            criteria["equip_emp_weapon"] = "Equip an available EMP weapon before the mechanoids close, so shields and machines can be stunned."
        if free_ranged and any(not pawn.get("has_ranged_weapon") for pawn in fighters):
            criteria["equip_ranged_weapon"] = "Equip healthy unarmed defenders with distinct nearby ranged weapons before attacking."
        if not armed_ranged:
            criteria["engage_melee"] = "Use a coordinated melee defense only because no healthy armed shooter is available."
        criteria["draft_best_defender"] = "The assault is active or close: draft healthy defenders together without ordering a long chase."
        if active_order:
            criteria["hold_and_observe"] = "Keep the already active coordinated combat order without replacing it."
        return {
            "threat_action": {
                "type": "choice",
                "instructions": "Choose one feasible coordinated defensive plan. Protect wounded colonists, avoid single-pawn chases, and prefer concentrated ranged fire.",
                "criteria": criteria,
            }
        }
    if any(bool(c.get("is_drafted")) for c in snapshot["combat"]["colonists"]):
        return {
            "post_combat_action": {
                "type": "choice",
                "instructions": "The combat API reports zero hostile pawns. Return colonists to normal work unless a verified current threat requires continued drafting.",
                "criteria": {
                    "remain_drafted": "Keep the drafted state only if the current state contains concrete evidence of continuing danger.",
                    "stand_down": "Undraft colonists and resume normal colony work because the verified hostile count is zero.",
                },
            }
        }
    return {
        "colony_action": {
            "type": "choice",
            "instructions": "Select the most useful safe action now. Prefer keep_current_plan unless the state clearly supports a change.",
            "criteria": {
                "keep_current_plan": "Make no changes when the colony is stable or evidence is insufficient.",
                "prioritize_cooking": "Set Cooking to priority 1 for one healthy colonist when ready food is low.",
                "prioritize_growing": "Set Growing to priority 1 for one healthy colonist when food production needs attention.",
                "prioritize_hauling": "Set Hauling to priority 1 for one healthy colonist when general logistics should be improved.",
                "prioritize_construction": "Set Construction to priority 1 for one healthy colonist when colony development is the best focus.",
                "prioritize_cleaning": "Set Cleaning to priority 1 for one healthy colonist when no urgent production need dominates.",
            },
        }
    }


def choose_worker(colonists: list[dict[str, Any]], work: str) -> dict[str, Any] | None:
    skill_for_work = {
        "Cooking": "Cooking",
        "Growing": "Plants",
        "PlantCutting": "Plants",
        "Construction": "Construction",
        "Research": "Intellectual",
        "Hunting": "Shooting",
        "Handling": "Animals",
        "Doctor": "Medicine",
    }
    skill_name = skill_for_work.get(work)
    eligible = []
    for colonist in colonists:
        priority = colonist.get("work_priorities", {}).get(work)
        if colonist["health"] < 0.75 or colonist["bleeding_rate"] > 0.0 or colonist.get("downed"):
            continue
        if priority and priority.get("disabled"):
            continue
        eligible.append(colonist)
    if not eligible:
        return None
    def score(colonist: dict[str, Any]) -> tuple[float, int]:
        skill = colonist.get("skills", {}).get(skill_name, {}) if skill_name else {}
        return (
            first_number(skill.get("level")) * 2
            + first_number(skill.get("passion"))
            + colonist["mood"]
            + colonist["rest"]
            + colonist["health"],
            colonist["id"],
        )
    return max(eligible, key=score)


def decide(agent: Any, snapshot: dict[str, Any], confidence_threshold: float) -> dict[str, Any]:
    if snapshot["map"]["enemies"] > 0 and not snapshot["combat"]["available"]:
        return {
            "choice": "prepare_undrafted",
            "confidence": 0.0,
            "reason": "Combat API is unavailable, so no target can be validated; undraft instead of exhausting colonists.",
            "raw": None,
        }
    questions = make_questions(snapshot)
    question_id = next(iter(questions))
    raw = agent.predict(decision_state(snapshot), questions)
    answer = raw["answers"][question_id]
    choice = str(answer["choice"])
    confidence = first_number(answer.get("confidence"))
    reason = "Laya decision"
    feasible = list(questions[question_id].get("criteria", {}))
    if choice not in feasible and feasible:
        reason = f"Model returned infeasible choice {choice}; using {feasible[0]}"
        choice = feasible[0]
    if confidence < confidence_threshold:
        reason = f"Confidence {confidence:.3f} is below threshold {confidence_threshold:.3f}"
        choice = "keep_current_plan"
    if choice not in SAFE_WORK_TYPES and choice not in COMBAT_CHOICES and choice != "keep_current_plan":
        reason = f"Blocked non-whitelisted choice: {choice}"
        choice = "keep_current_plan"
    selected_fighter_ids = None
    roster_choices = {
        "engage_ranged", "engage_melee", "draft_best_defender", "preemptive_strike",
        "focus_mechanoids", "focus_insects",
    }
    if choice in roster_choices:
        eligible = [
            pawn for pawn in snapshot["combat"].get("colonists", [])
            if not pawn.get("is_dead") and not pawn.get("is_downed") and first_number(pawn.get("health")) >= 0.72
        ]
        has_medical_tradeoff = any(
            pawn.get("health_conditions")
            or first_number(pawn.get("manipulation"), 1.0) < 0.8
            or first_number(pawn.get("moving"), 1.0) < 0.8
            or first_number(pawn.get("sight"), 1.0) < 0.8
            or first_number(pawn.get("pain")) > 0.25
            for pawn in eligible
        )
        if len(eligible) > 1 or has_medical_tradeoff:
            roster_questions: dict[str, dict[str, Any]] = {}
            for pawn in eligible:
                context = (
                    f"{pawn.get('name')}: Shooting {pawn.get('shooting_skill', 0)}, Melee {pawn.get('melee_skill', 0)}, "
                    f"weapon {pawn.get('weapon_label') or 'none'}, health {pawn.get('health')}, pain {pawn.get('pain', 0)}, "
                    f"moving {pawn.get('moving', 1)}, manipulation {pawn.get('manipulation', 1)}, sight {pawn.get('sight', 1)}, "
                    f"traits {pawn.get('traits') or []}, conditions {pawn.get('health_conditions') or []}."
                )
                roster_questions[f"fighter_{int(pawn['id'])}"] = {
                    "type": "choice",
                    "instructions": context + " Decide whether this exact colonist should deploy for the already selected combat plan. A missing arm, low movement/sight, pain or poor weapon can justify reserve; Tough and strong combat skills can justify deploy.",
                    "criteria": {"deploy": "Join the selected combat plan.", "reserve": "Remain undrafted for safety, rescue and home work."},
                }
            roster_raw = agent.predict(decision_state(snapshot), roster_questions)
            selected_fighter_ids = [
                int(question_id.removeprefix("fighter_"))
                for question_id, answer_row in roster_raw.get("answers", {}).items()
                if question_id.startswith("fighter_") and answer_row.get("choice") == "deploy"
            ]
            raw["roster"] = roster_raw
    return {
        "choice": choice, "confidence": confidence, "reason": reason, "raw": raw,
        "selected_fighter_ids": selected_fighter_ids,
    }


def plan_action(snapshot: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    choice = decision["choice"]
    resume_command = None
    if snapshot["map"]["enemies"] > 0 and snapshot["game"].get("is_paused"):
        resume_command = {"endpoint": "/api/v1/game/speed", "query": {"speed": 1}}
    if choice == "keep_current_plan":
        return {"kind": "noop", "description": "Keep current priorities"}
    if choice == "hold_and_observe" and resume_command:
        return {
            "kind": "commands",
            "description": "Resume at normal speed and observe the threat",
            "commands": [resume_command],
        }
    if choice in {"hold_and_observe", "remain_drafted"}:
        return {"kind": "noop", "description": choice.replace("_", " ")}
    if choice == "stand_down":
        drafted = [c for c in snapshot["combat"]["colonists"] if c.get("is_drafted")]
        return {
            "kind": "commands",
            "description": f"Undraft {len(drafted)} colonist(s)",
            "commands": [
                {"endpoint": "/api/v1/pawn/edit/status", "body": {"pawn_id": c["id"], "is_drafted": False}}
                for c in drafted
            ],
        }
    if choice == "prepare_undrafted":
        drafted = [c for c in snapshot["combat"]["colonists"] if c.get("is_drafted")]
        commands = [
            {"endpoint": "/api/v1/pawn/edit/status", "body": {"pawn_id": c["id"], "is_drafted": False}}
            for c in drafted
        ]
        if resume_command:
            commands.append(resume_command)
        return {
            "kind": "commands",
            "description": f"Raid preparation: undraft {len(drafted)} colonist(s), restore needs, and monitor movement",
            "commands": commands,
        }
    if choice in {"engage_ranged", "engage_melee", "draft_best_defender", "equip_ranged_weapon", "equip_melee_weapon", "preemptive_strike", "equip_emp_weapon", "focus_mechanoids", "focus_insects"}:
        fighters = [
            c for c in snapshot["combat"]["colonists"]
            if not c.get("is_dead") and not c.get("is_downed") and first_number(c.get("health")) >= 0.72
        ]
        if decision.get("selected_fighter_ids") is not None:
            selected = set(map(int, decision.get("selected_fighter_ids") or []))
            fighters = [pawn for pawn in fighters if int(pawn.get("id", -1)) in selected]
        hostiles = [h for h in snapshot["combat"]["hostiles"] if not h.get("is_dead") and not h.get("is_downed")]
        if not fighters or not hostiles:
            return {"kind": "noop", "description": "No eligible fighter or hostile target"}
        ranged = choice in {"engage_ranged", "equip_ranged_weapon", "preemptive_strike", "equip_emp_weapon", "focus_mechanoids", "focus_insects"}
        if ranged:
            armed = [c for c in fighters if c.get("has_ranged_weapon")]
            if armed:
                fighters = armed
        ranked_fighters = sorted(
            fighters,
            key=lambda c: (
                first_number(c.get("shooting_skill") if ranged else c.get("melee_skill")),
                first_number(c.get("health")),
                -first_number(c.get("distance_to_nearest_opponent"), 9999),
            ),
            reverse=True,
        )
        actor = ranked_fighters[0]
        needs_weapon = choice in {"equip_ranged_weapon", "equip_melee_weapon", "equip_emp_weapon"} or (
            choice == "engage_ranged" and not actor.get("has_ranged_weapon")
        )
        if needs_weapon:
            weapons = [
                w for w in snapshot["combat"].get("available_weapons", [])
                if bool(w.get("is_ranged")) == ranged
            ]
            if choice == "equip_emp_weapon":
                weapons = [
                    w for w in weapons
                    if "emp" in (str(w.get("def_name") or "") + " " + str(w.get("label") or "")).lower()
                ]
            if not weapons:
                return {"kind": "noop", "description": "No suitable free weapon is available"}
            ax = first_number((actor.get("position") or {}).get("x"))
            az = first_number((actor.get("position") or {}).get("z"))
            unarmed = [pawn for pawn in ranked_fighters if not pawn.get("has_ranged_weapon")] if ranged else ranked_fighters
            commands: list[dict[str, Any]] = []
            assignments: list[str] = []
            remaining = list(weapons)
            for defender in unarmed:
                if not remaining:
                    break
                dx = first_number((defender.get("position") or {}).get("x"))
                dz = first_number((defender.get("position") or {}).get("z"))
                weapon = min(remaining, key=lambda w: (
                    first_number((w.get("position") or {}).get("x")) - dx
                ) ** 2 + (
                    first_number((w.get("position") or {}).get("z")) - dz
                ) ** 2)
                remaining.remove(weapon)
                if weapon.get("is_forbidden"):
                    commands.append({
                        "endpoint": "/api/v1/things/set-forbidden",
                        "body": {"thing_ids": [weapon["id"]], "map_id": snapshot["map"]["id"], "forbidden": False},
                    })
                commands.append({
                    "endpoint": "/api/v1/pawn/job",
                    "body": {"pawn_id": defender["id"], "job_def": "Equip", "target_thing_id": weapon["id"]},
                })
                assignments.append(f"{defender.get('name')} -> {weapon.get('label')}")
            if resume_command:
                commands.append(resume_command)
            return {
                "kind": "commands",
                "description": f"{choice}: " + "; ".join(assignments),
                "commands": commands,
            }
        ax = first_number((actor.get("position") or {}).get("x"))
        az = first_number((actor.get("position") or {}).get("z"))
        target_pool = hostiles
        if choice == "focus_mechanoids":
            tokens = ("mech", "scyther", "lancer", "centipede", "pikeman", "militor", "tesseron", "termite")
            target_pool = [h for h in hostiles if any(t in (str(h.get("name")) + str(h.get("kind_def")) + str(h.get("faction"))).lower() for t in tokens)] or hostiles
        elif choice == "focus_insects":
            tokens = ("insect", "megaspider", "spelopede", "megascarab")
            target_pool = [h for h in hostiles if any(t in (str(h.get("name")) + str(h.get("kind_def")) + str(h.get("faction"))).lower() for t in tokens)] or hostiles
        target = min(
            target_pool,
            key=lambda h: (
                first_number((h.get("position") or {}).get("x")) - ax
            ) ** 2 + (
                first_number((h.get("position") or {}).get("z")) - az
            ) ** 2,
        )
        if choice in {"engage_ranged", "preemptive_strike", "focus_mechanoids", "focus_insects"}:
            attackers = [pawn for pawn in ranked_fighters if pawn.get("has_ranged_weapon")]
        elif choice == "engage_melee":
            attackers = ranked_fighters
        else:
            attackers = ranked_fighters
        commands = [
            {"endpoint": "/api/v1/pawn/edit/status", "body": {"pawn_id": pawn["id"], "is_drafted": True}}
            for pawn in attackers
        ]
        if choice != "draft_best_defender":
            commands.extend(
                {
                    "endpoint": "/api/v1/pawn/job",
                    "body": {
                        "pawn_id": pawn["id"],
                        "job_def": "AttackStatic" if ranged and pawn.get("has_ranged_weapon") else "AttackMelee",
                        "target_thing_id": target["id"],
                    },
                }
                for pawn in attackers
            )
        if resume_command:
            commands.append(resume_command)
        return {
            "kind": "commands",
            "description": f"{choice}: {', '.join(str(p.get('name')) for p in attackers)} -> {target.get('name')}",
            "commands": commands,
        }
    work = SAFE_WORK_TYPES[choice]
    target = choose_worker(snapshot["colonists"], work)
    if target is None:
        return {"kind": "noop", "description": "No healthy colonist is eligible for a priority change"}
    return {
        "kind": "work_priority",
        "description": f"Set {work}=1 for {target['name']} (id={target['id']})",
        "body": {"id": target["id"], "work": work, "priority": 1},
    }


def apply_action(client: RimApiClient, action: dict[str, Any]) -> Any:
    if action["kind"] == "noop":
        return {"applied": False, "reason": action["description"]}
    if action["kind"] == "commands":
        responses = []
        for command in action["commands"]:
            responses.append(client.post(command["endpoint"], query=command.get("query"), body=command.get("body")))
        return {"applied": bool(action["commands"]), "responses": responses}
    if action["kind"] == "work_priority":
        response = client.post("/api/v1/colonist/work-priority", body=action["body"])
        return {"applied": True, "response": response}
    raise RimApiError(f"Blocked unknown action kind: {action['kind']}")


def append_log(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def load_agent(model: str, device: str) -> Any:
    import laya

    selected = None if device == "auto" else device
    print(f"Loading Laya model {model!r} on {selected or 'auto'}...", flush=True)
    return laya.load(model, device=selected)


def run_cycle(
    client: RimApiClient,
    agent: Any,
    *,
    apply: bool,
    confidence: float,
    log_path: Path,
) -> dict[str, Any]:
    snapshot = collect_snapshot(client)
    decision = decide(agent, snapshot, confidence)
    action = plan_action(snapshot, decision)
    result = {"applied": False, "reason": "preview mode"}
    if apply:
        result = apply_action(client, action)
    record = {
        "timestamp": utc_now(),
        "mode": "apply" if apply else "preview",
        "snapshot": snapshot,
        "decision": decision,
        "action": action,
        "result": result,
    }
    append_log(log_path, record)
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safe Laya bridge for RimWorld RIMAPI")
    parser.add_argument("command", choices=["check", "suggest", "run-once", "watch", "download-model"])
    parser.add_argument("--api-url", default=os.environ.get("RIMAPI_URL", DEFAULT_API_URL))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--confidence", type=float, default=0.0)
    parser.add_argument("--interval", type=int, default=45)
    parser.add_argument("--apply", action="store_true", help="Actually send whitelisted commands to RIMAPI")
    parser.add_argument("--log", type=Path, default=Path(__file__).with_name("logs") / "decisions.jsonl")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not 0 <= args.confidence <= 1:
        raise SystemExit("--confidence must be between 0 and 1")
    if args.interval < 10:
        raise SystemExit("--interval must be at least 10 seconds")
    client = RimApiClient(args.api_url)

    if args.command == "check":
        print_json(collect_snapshot(client))
        return 0

    agent = load_agent(args.model, args.device)
    if args.command == "download-model":
        print("Laya model is ready.")
        return 0

    apply = bool(args.apply and args.command in {"run-once", "watch"})
    if args.command == "suggest":
        apply = False

    if args.command in {"suggest", "run-once"}:
        print_json(run_cycle(client, agent, apply=apply, confidence=args.confidence, log_path=args.log))
        return 0

    print(f"Watching every {args.interval}s in {'APPLY' if apply else 'PREVIEW'} mode. Ctrl+C stops safely.")
    try:
        while True:
            try:
                record = run_cycle(client, agent, apply=apply, confidence=args.confidence, log_path=args.log)
                print(f"[{record['timestamp']}] {record['action']['description']} | {record['result']}", flush=True)
            except Exception as exc:
                error = {"timestamp": utc_now(), "mode": "error", "error": repr(exc)}
                append_log(args.log, error)
                print(f"[{error['timestamp']}] {exc}", file=sys.stderr, flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped. No further commands will be sent.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
