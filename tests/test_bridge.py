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


class RosterAgent:
    def __init__(self):
        self.calls = []

    def predict(self, state, questions):
        self.calls.append(questions)
        answers = {}
        for question_id, question in questions.items():
            if question_id == "threat_action":
                choice = "engage_ranged"
            elif question_id == "fighter_10":
                choice = "reserve"
            else:
                choice = "deploy"
            answers[question_id] = {"choice": choice, "confidence": 0.9, "probabilities": {choice: 1.0}}
        return {"answers": answers}


class BridgeTests(unittest.TestCase):
    def test_single_option_is_resolved_without_calling_laya(self):
        class RecordingAgent:
            def __init__(self):
                self.calls = []

            def predict(self, state, questions):
                self.calls.append(questions)
                return {
                    "model": "fake",
                    "answers": {
                        "real_choice": {
                            "choice": "second",
                            "probabilities": {"first": 0.2, "second": 0.8},
                            "confidence": 0.6,
                        }
                    },
                }

        inner = RecordingAgent()
        agent = bridge.SafeDecisionAgent(inner)
        result = agent.predict({}, {
            "only_choice": {"type": "choice", "instructions": "No decision exists", "criteria": {"automatic": "the sole feasible option"}},
            "real_choice": {"type": "choice", "instructions": "Choose", "criteria": {"first": "A", "second": "B"}},
        })
        self.assertEqual(len(inner.calls), 1)
        self.assertEqual(set(inner.calls[0]), {"real_choice"})
        self.assertEqual(result["answers"]["only_choice"]["choice"], "automatic")
        self.assertTrue(result["answers"]["only_choice"]["resolved_without_model"])

    def test_all_single_option_questions_skip_laya_entirely(self):
        class ExplodingAgent:
            def predict(self, state, questions):
                raise AssertionError("Laya must not receive a one-option question")

        result = bridge.SafeDecisionAgent(ExplodingAgent()).predict({}, {
            "target": {"type": "choice", "instructions": "Choose", "criteria": {"42": "only valid target"}},
        })
        self.assertEqual(result["answers"]["target"]["probabilities"], {"42": 1.0})

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

    def test_laya_selects_combat_roster_using_health_context(self):
        snapshot = self.snapshot()
        snapshot["map"]["enemies"] = 1
        snapshot["combat"] = {
            "available": True,
            "colonists": [
                {"id": 10, "name": "Ada", "health": 0.9, "is_dead": False, "is_downed": False,
                 "has_ranged_weapon": True, "shooting_skill": 12, "melee_skill": 3,
                 "manipulation": 0.45, "moving": 1.0, "sight": 1.0, "pain": 0.2,
                 "health_conditions": ["MissingBodyPart:Arm"], "traits": [],
                 "distance_to_nearest_opponent": 8, "position": {"x": 10, "z": 10}},
                {"id": 11, "name": "Bo", "health": 1.0, "is_dead": False, "is_downed": False,
                 "has_ranged_weapon": True, "shooting_skill": 8, "melee_skill": 5,
                 "manipulation": 1.0, "moving": 1.0, "sight": 1.0, "pain": 0.0,
                 "health_conditions": [], "traits": ["Tough"],
                 "distance_to_nearest_opponent": 9, "position": {"x": 9, "z": 10}},
            ],
            "hostiles": [{"id": 99, "name": "Raider", "health": 1.0, "is_dead": False,
                          "is_downed": False, "position": {"x": 18, "z": 10}, "current_job": "AttackStatic"}],
            "available_weapons": [],
        }
        agent = RosterAgent()
        decision = bridge.decide(agent, snapshot, 0.0)
        self.assertEqual(decision["selected_fighter_ids"], [11])
        self.assertEqual(len(agent.calls), 2)
        action = bridge.plan_action(snapshot, decision)
        attacks = [c for c in action["commands"] if c.get("body", {}).get("job_def") == "AttackStatic"]
        self.assertEqual([c["body"]["pawn_id"] for c in attacks], [11])

    def test_remote_api_is_rejected(self):
        with self.assertRaises(ValueError):
            bridge.RimApiClient("https://example.com:8765")


if __name__ == "__main__":
    unittest.main()
