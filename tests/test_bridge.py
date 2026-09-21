import importlib.util
import pathlib
import sys
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "rimworld_laya.py"
SPEC = importlib.util.spec_from_file_location("rimworld_laya", MODULE_PATH)
bridge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = bridge
SPEC.loader.exec_module(bridge)


class FakeAgent:
    def __init__(self, choice="prioritize_cooking", confidence=0.9):
        self.choice = choice
        self.confidence = confidence

    def predict(self, state, questions):
        question_id = next(iter(questions))
        return {
            "answers": {
                question_id: {
                    "choice": self.choice,
                    "confidence": self.confidence,
                    "probabilities": {self.choice: 1.0},
                }
            }
        }


class BridgeTests(unittest.TestCase):
    def snapshot(self):
        return {
            "game": {"is_paused": False},
            "map": {
                "id": 0,
                "enemies": 0,
                "growing_zones": 1,
                "plants": 10,
                "expected_yield": 50,
                "resources": {"food": 5, "meals": 1},
            },
            "colonists": [
                {
                    "id": 10,
                    "name": "Ada",
                    "health": 1.0,
                    "mood": 0.8,
                    "hunger": 0.5,
                    "rest": 0.9,
                    "joy": 0.7,
                    "bleeding_rate": 0.0,
                    "current_job": "Hauling",
                    "skills": {"Cooking": {"level": 10, "passion": 1, "disabled": False}},
                    "work_priorities": {"Cooking": {"priority": 3, "disabled": False}},
                }
            ],
            "combat": {"available": True, "colonists": [], "hostiles": []},
        }

    def test_low_confidence_becomes_noop(self):
        decision = bridge.decide(FakeAgent(confidence=0.2), self.snapshot(), 0.6)
        self.assertEqual(decision["choice"], "keep_current_plan")

    def test_threat_without_target_ids_undrafts_instead_of_exhausting_colonists(self):
        snapshot = self.snapshot()
        snapshot["map"]["enemies"] = 2
        snapshot["combat"] = {"available": False, "colonists": [], "hostiles": []}
        decision = bridge.decide(None, snapshot, 0.6)
        self.assertEqual(decision["choice"], "prepare_undrafted")

    def test_staging_raid_offers_rest_or_preemptive_strike_not_idle_draft(self):
        snapshot = self.snapshot()
        snapshot["map"]["enemies"] = 2
        snapshot["combat"] = {
            "available": True,
            "colonists": [{
                "id": 10, "name": "Ada", "health": 1.0, "is_dead": False,
                "is_downed": False, "is_drafted": True, "has_ranged_weapon": True,
                "distance_to_nearest_opponent": 90, "current_job": "Wait_Combat",
            }, {
                "id": 11, "name": "Bo", "health": 1.0, "is_dead": False,
                "is_downed": False, "is_drafted": False, "has_ranged_weapon": True,
                "distance_to_nearest_opponent": 92, "current_job": "Wait",
            }],
            "hostiles": [
                {"id": 99, "current_job": "Wait_Combat"},
                {"id": 100, "current_job": "Wait_Wander"},
            ],
            "available_weapons": [],
        }
        criteria = bridge.make_questions(snapshot)["threat_action"]["criteria"]
        self.assertEqual(set(criteria), {"prepare_undrafted", "preemptive_strike"})
        action = bridge.plan_action(snapshot, {"choice": "prepare_undrafted"})
        self.assertEqual(action["commands"][0]["body"], {"pawn_id": 10, "is_drafted": False})

    def test_work_priority_is_whitelisted(self):
        decision = bridge.decide(FakeAgent(), self.snapshot(), 0.6)
        action = bridge.plan_action(self.snapshot(), decision)
        self.assertEqual(action["kind"], "work_priority")
        self.assertEqual(action["body"], {"id": 10, "work": "Cooking", "priority": 1})

    def test_laya_combat_choice_targets_real_hostile(self):
        snapshot = self.snapshot()
        snapshot["map"]["enemies"] = 1
        snapshot["combat"] = {
            "available": True,
            "colonists": [
                {
                    "id": 10,
                    "name": "Ada",
                    "health": 1.0,
                    "is_dead": False,
                    "is_downed": False,
                    "has_ranged_weapon": True,
                    "shooting_skill": 12,
                    "melee_skill": 3,
                    "distance_to_nearest_opponent": 8,
                    "position": {"x": 10, "z": 10},
                }
            ],
            "hostiles": [
                {"id": 99, "name": "Raider", "health": 1.0, "is_dead": False, "is_downed": False, "position": {"x": 18, "z": 10}}
            ],
        }
        decision = bridge.decide(FakeAgent(choice="engage_ranged"), snapshot, 0.0)
        action = bridge.plan_action(snapshot, decision)
        self.assertEqual(action["commands"][1]["body"]["job_def"], "AttackStatic")
        self.assertEqual(action["commands"][1]["body"]["target_thing_id"], 99)

    def test_paused_threat_resumes_after_combat_order(self):
        snapshot = self.snapshot()
        snapshot["game"]["is_paused"] = True
        snapshot["map"]["enemies"] = 1
        snapshot["combat"] = {
            "available": True,
            "colonists": [{
                "id": 10, "name": "Ada", "health": 1.0, "is_dead": False,
                "is_downed": False, "has_ranged_weapon": True,
                "shooting_skill": 12, "melee_skill": 3,
                "distance_to_nearest_opponent": 8, "position": {"x": 10, "z": 10},
            }],
            "hostiles": [{
                "id": 99, "name": "Raider", "health": 1.0,
                "is_dead": False, "is_downed": False, "position": {"x": 18, "z": 10},
            }],
            "available_weapons": [],
        }
        action = bridge.plan_action(snapshot, {"choice": "engage_ranged"})
        self.assertEqual(action["commands"][-1], {
            "endpoint": "/api/v1/game/speed", "query": {"speed": 1}
        })
        self.assertEqual(action["commands"][1]["body"]["job_def"], "AttackStatic")

    def test_ranged_engagement_equips_before_attacking(self):
        snapshot = self.snapshot()
        snapshot["map"]["enemies"] = 1
        snapshot["combat"] = {
            "available": True,
            "colonists": [{
                "id": 10, "name": "Ada", "health": 1.0, "is_dead": False,
                "is_downed": False, "has_ranged_weapon": False,
                "shooting_skill": 12, "melee_skill": 3,
                "distance_to_nearest_opponent": 8, "position": {"x": 10, "z": 10},
            }],
            "hostiles": [{
                "id": 99, "name": "Raider", "health": 1.0,
                "is_dead": False, "is_downed": False, "position": {"x": 18, "z": 10},
            }],
            "available_weapons": [{
                "id": 77, "label": "rifle", "is_ranged": True,
                "is_forbidden": True, "position": {"x": 11, "z": 10},
            }],
        }
        action = bridge.plan_action(snapshot, {"choice": "engage_ranged"})
        self.assertIn("Ada -> rifle", action["description"])
        self.assertEqual(action["commands"][-1]["endpoint"], "/api/v1/pawn/job")
        self.assertEqual(action["commands"][-1]["body"]["job_def"], "Equip")

    def test_ranged_defense_uses_all_healthy_shooters(self):
        snapshot = self.snapshot()
        snapshot["map"]["enemies"] = 1
        snapshot["combat"] = {
            "available": True,
            "colonists": [
                {"id": 10, "name": "Ada", "health": 1.0, "is_dead": False, "is_downed": False,
                 "has_ranged_weapon": True, "shooting_skill": 12, "melee_skill": 3,
                 "distance_to_nearest_opponent": 8, "position": {"x": 10, "z": 10}},
                {"id": 11, "name": "Bo", "health": 0.9, "is_dead": False, "is_downed": False,
                 "has_ranged_weapon": True, "shooting_skill": 8, "melee_skill": 5,
                 "distance_to_nearest_opponent": 9, "position": {"x": 9, "z": 10}},
            ],
            "hostiles": [{"id": 99, "name": "Squirrel", "health": 1.0, "is_dead": False,
                          "is_downed": False, "position": {"x": 18, "z": 10}}],
            "available_weapons": [],
        }
        action = bridge.plan_action(snapshot, {"choice": "engage_ranged"})
        attack_commands = [command for command in action["commands"] if command.get("body", {}).get("job_def") == "AttackStatic"]
        self.assertEqual({command["body"]["pawn_id"] for command in attack_commands}, {10, 11})
        self.assertTrue(all(command["body"]["target_thing_id"] == 99 for command in attack_commands))

    def test_remote_api_is_rejected(self):
        with self.assertRaises(ValueError):
            bridge.RimApiClient("https://example.com:8765")


if __name__ == "__main__":
    unittest.main()
