"""One focused live Laya choice for a repeatable wild-plant filming scene."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import colony_director as director  # noqa: E402
import rimworld_laya as bridge  # noqa: E402
from laya_decisions import ask_laya_choice  # noqa: E402


def main() -> None:
    client = bridge.RimApiClient(bridge.DEFAULT_API_URL)
    snapshot = director.collect_development(client, bridge.collect_snapshot(client))
    map_state = {"anchor": director.anchor_from_snapshot(snapshot), "issued": {}}
    director.candidate_actions(client, snapshot, map_state)
    groups = {
        name: row for name, row in (snapshot["development"].get("wild_plant_options") or {}).items()
        if row.get("count", 0) >= 3 and row.get("ids")
    }
    if len(groups) < 2:
        raise RuntimeError("At least two live wild-plant types are required for a Laya choice")
    options = {
        name: f"{row['label']}; {row['count']} plants; yield {row['expected_yield']} {row['harvested_thing']}"
        for name, row in groups.items()
    }
    agent = bridge.load_agent(bridge.DEFAULT_MODEL, "cuda")
    state = director.fit_model_context(agent, director.model_decision_context(snapshot))
    selected, raw = ask_laya_choice(
        agent, state, "promo_wild_plant_type",
        "Choose one nearby mature wild plant type to harvest for the colony's current needs.",
        options,
    )
    answer = raw["answers"]["promo_wild_plant_type"]
    anchor = map_state["anchor"]
    plants_by_id = {int(row["thing_id"]): row for row in snapshot["development"].get("plants", [])}
    selected_ids = sorted(
        (int(plant_id) for plant_id in groups[selected]["ids"]),
        key=lambda plant_id: sum(
            (int((plants_by_id[plant_id].get("position") or {}).get(axis) or 0) - int(anchor[axis])) ** 2
            for axis in ("x", "z")
        ),
    )[:25]
    result = client.post("/api/v1/map/plants/harvest", body={
        "map_id": snapshot["map"]["id"],
        "plant_ids": selected_ids,
    })
    cutters = director.worker_criteria(snapshot, "PlantCutting")
    worker_answer = None
    worker_id = None
    ordered_job = None
    if cutters and selected_ids:
        if len(cutters) > 1:
            worker_id, worker_raw = ask_laya_choice(
                agent, state, "promo_plant_cutter", "Choose a healthy plant cutter to start the harvest.", cutters,
            )
            worker_answer = worker_raw["answers"]["promo_plant_cutter"]
        else:
            worker_id = next(iter(cutters))
        ordered_job = client.post("/api/v1/pawn/job", body={
            "pawn_id": int(worker_id), "job_def": "CutPlant", "target_thing_id": selected_ids[0],
        })
    ranked = sorted(answer["probabilities"].items(), key=lambda item: item[1], reverse=True)
    bars = [{
        "label": str(groups[name]["label"]).capitalize()[:38],
        "value": float(probability),
        "selected": name == selected,
    } for name, probability in ranked[:5]]
    client.post("/api/v1/ui/announce", body={
        "text": f"LAYA - FORAGING\nChosen: {groups[selected]['label']}\nWild plants designated for harvest",
        "duration": 180.0, "color": "#D8FFD7", "scale": 1.0,
        "panel": True, "compact": True, "bars": bars,
    })
    print(json.dumps({
        "colonists": [{"id": row["id"], "name": row["name"]} for row in snapshot["colonists"]],
        "choice": selected, "options": options, "answer": answer,
        "designated": len(selected_ids), "nearest_plant_id": selected_ids[0],
        "worker_id": worker_id, "worker_answer": worker_answer,
        "ordered_job": ordered_job, "result": result,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
