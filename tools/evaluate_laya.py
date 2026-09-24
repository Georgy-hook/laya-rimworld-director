"""Small, repeatable *diagnostic* for the untrained Laya checkpoint.

Run with the configured model environment:
    .venv/Scripts/python.exe tools/evaluate_laya.py --device cuda

These human-labelled synthetic states are not a gameplay benchmark and are
never used as production policy. They expose obvious zero-shot failures before
spending time or colonists on a live evaluation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import colony_director as director
import rimworld_laya as bridge


def snapshot(*, food: int, hunger: float, health: float = 1.0,
             bleeding: float = 0.0, beds: int = 1) -> dict:
    return {
        "map": {"resources": {"food": food, "meals": food}, "enemies": 0},
        "colonists": [{"id": 1, "name": "Nyn", "hunger": hunger, "health": health,
                       "bleeding_rate": bleeding, "downed": False}],
        "animals": [],
        "development": {
            "building_counts": {"Bed": beds}, "corpses": [],
            "item_counts": {"WoodLog": 60, "Steel": 10},
            "weather": {"temperature": 14, "growth_season_now": True},
            "doctrine": {}, "current_research": {"name": "none"},
            "user_preferences": {"personal_note": "Grow a resilient colony."},
        },
    }


SCENARIOS = [
    ("starvation", snapshot(food=0, hunger=0.07), "harvest_berries"),
    ("bleeding", snapshot(food=30, hunger=0.85, health=0.35, bleeding=0.17), "tend_wound"),
    ("stable", snapshot(food=70, hunger=0.95), "research_power"),
]

OPTIONS = {
    "harvest_berries": "Harvest nearby edible berries for immediate meals.",
    "tend_wound": "Treat the colonist's bleeding wound using available medicine.",
    "research_power": "Begin an available power research project.",
    "wait": "Issue no new order and continue current work.",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="auto")
    args = parser.parse_args()
    agent = bridge.load_agent(bridge.DEFAULT_MODEL, args.device)
    correct = 0
    for name, colony, human_label in SCENARIOS:
        state = director.fit_model_context(agent, director.model_decision_context(colony))
        question = {"next_step": {"type": "choice", "instructions": "Choose the next colony action.",
                                  "criteria": OPTIONS}}
        answer = agent.predict(state, question)["answers"]["next_step"]
        correct += answer["choice"] == human_label
        print(json.dumps({"scenario": name, "human_label": human_label,
                          "laya_choice": answer["choice"], "weights": answer["probabilities"]},
                         ensure_ascii=False))
    print(f"Human-label matches: {correct}/{len(SCENARIOS)} (synthetic diagnostic, not a benchmark)")


if __name__ == "__main__":
    main()
