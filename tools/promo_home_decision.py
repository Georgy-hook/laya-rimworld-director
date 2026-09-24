"""Run one genuine Laya development decision for the visible home-map promo shot.

The normal director intentionally prioritizes a threatened away map. This
one-shot test harness targets the currently visible home colony instead, and
keeps its state and log separate from the user's ordinary director history.
Use it only with a copied test save.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import colony_director as director  # noqa: E402
import rimworld_laya as bridge  # noqa: E402


class VisibleHomeClient(bridge.RimApiClient):
    def get(self, endpoint: str, **query: object) -> object:
        response = super().get(endpoint, **query)
        if endpoint != "/api/v1/maps":
            return response
        if not isinstance(response, list):
            raise bridge.RimApiError("Expected a list of loaded maps")
        visible_home = [
            row for row in response
            if isinstance(row, dict) and row.get("is_current_map") and row.get("is_player_home")
        ]
        if len(visible_home) != 1:
            raise bridge.RimApiError("Exactly one visible home map is required for the promo decision")
        return visible_home


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--replay-last", action="store_true",
                        help="Redisplay the last genuine model decision for filming; do not ask or act again")
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    client = VisibleHomeClient()
    state_path = args.work_dir / "promo-home-state.json"
    log_path = args.work_dir / "promo-home-decisions.jsonl"
    if args.replay_last:
        lines = log_path.read_text(encoding="utf-8").splitlines()
        if not lines:
            raise RuntimeError("No genuine promo decision has been recorded yet")
        record = json.loads(lines[-1])
        snapshot = director.collect_development(client, bridge.collect_snapshot(client))
        director.publish_overlay(client, snapshot, record["candidates"], record["decision"])
        print(json.dumps({"replayed_choice": record["decision"]["choice"],
                          "original_timestamp": record["timestamp"]}), flush=True)
        return 0
    agent = bridge.load_agent(bridge.DEFAULT_MODEL, args.device)
    state = director.load_state(state_path)
    record = director.run_development_cycle(client, agent, state, state_path, log_path)
    raw = record["decision"].get("raw") or {}
    answers = raw.get("answers") or {}
    answer = answers.get("colony_goal_action") or {}
    print(json.dumps({
        "timestamp": record["timestamp"],
        "map_seed": record["map_seed"],
        "choice": record["decision"]["choice"],
        "result": record["result"],
        "option_probabilities": answer.get("probabilities") or {},
    }, ensure_ascii=False, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
