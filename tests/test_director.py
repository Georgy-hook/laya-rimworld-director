import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import colony_combat
import colony_events
import colony_strategy


ROOT = pathlib.Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location("colony_director", ROOT / "colony_director.py")
director = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = director
SPEC.loader.exec_module(director)


class DirectorTests(unittest.TestCase):
    class FakeAgent:
        def __init__(self, choices):
            self.choices = iter(choices)
            self.calls = []

        def predict(self, state, questions):
            self.calls.append(questions)
            answers = {}
            for question_id, question in questions.items():
                if question.get("type") == "choice":
                    assert len(question["criteria"]) >= 2, f"Fake model received one-option question {question_id}"
                requested = next(self.choices)
                self.assert_choice(requested, question["criteria"])
                answers[question_id] = {
                    "choice": requested,
                    "confidence": 0.9,
                    "probabilities": {name: 1.0 if name == requested else 0.0 for name in question["criteria"]},
                }
            return {"answers": answers}

        @staticmethod
        def assert_choice(choice, criteria):
            if choice not in criteria:
                raise AssertionError(f"{choice!r} not in {list(criteria)!r}")

    def test_combat_catalog_contains_distinct_positioning_and_threat_tactics(self):
        required = {
            "kite", "melee_block", "wide_flank", "staggered_retreat", "drop_pod_encircle",
            "infestation_choke", "cluster_poke", "intercept_kidnapper", "psycast_control",
        }
        self.assertTrue(required.issubset(colony_combat.TACTICS))
        self.assertGreaterEqual(len(colony_combat.TACTICS), 25)

    def test_psycast_options_include_focus_and_neural_heat_context(self):
        snapshot = {"combat": {"colonists": [{
            "id": 7, "name": "Psy", "health": 1, "is_dead": False, "is_downed": False,
            "psyfocus": 0.62, "neural_heat": 12, "neural_heat_limit": 50,
            "psycasts": [{"def_name": "Stun", "label": "Stun", "description": "brief stun", "hostile": True,
                           "can_cast": True, "psyfocus_cost": 0.02, "entropy_gain": 8}],
        }]}}
        options = colony_combat.psycast_options(snapshot, hostile=True)
        self.assertIn("7:Stun", options)
        self.assertIn("heat 12/50", options["7:Stun"]["summary"])

    def test_combat_tactics_use_existing_defenses_and_focus_kidnapper(self):
        snapshot = {"combat": {
            "colonists": [{"id": 1, "health": 1, "has_ranged_weapon": True, "is_dead": False,
                            "is_downed": False, "distance_to_nearest_opponent": 12}],
            "hostiles": [{"id": 9, "health": 1, "is_dead": False, "is_downed": False,
                           "current_job": "Kidnap", "carrying_pawn_id": 3}],
            "defenses": [{"kind": "trap"}, {"kind": "door"}], "available_weapons": [],
        }}
        options = colony_combat.available_tactics(snapshot)
        self.assertIn("focus_fire", options)
        self.assertNotIn("intercept_kidnapper", options)
        self.assertNotIn("killbox_hold", options)
        self.assertIn("fallback_line", options)

    def test_unknown_mod_event_gets_safe_generic_handler(self):
        event = {"def_name": "MyMod_RealityFold", "label": "Reality fold", "category": "MyModSpecial"}
        self.assertEqual(colony_events.classify_event(event), "unknown")
        options = colony_events.response_options({"family": "unknown"}, {})
        self.assertIn("ask_laya_generic", options)
        self.assertIn("observe_event", options)

    def test_rescue_event_only_offers_mission_after_acceptance_and_site(self):
        event = {"family": "kidnap_rescue"}
        offered = {"active_quests": [{"quest_def": "PrisonerRescue", "ever_accepted": False, "look_targets": [{"world_object_id": 5}]}]}
        self.assertNotIn("prepare_rescue_mission", colony_events.response_options(event, offered))
        accepted = {"active_quests": [{"quest_def": "PrisonerRescue", "ever_accepted": True, "look_targets": [{"world_object_id": 5}]}]}
        self.assertIn("prepare_rescue_mission", colony_events.response_options(event, accepted))

    def test_event_history_deduplicates_same_occurrence(self):
        context = {"recent_incidents": [{"incident_def": "HeatWave", "incident_hour": 100, "label": "Heat wave"}]}
        first = colony_events.pending_events(context, set())
        self.assertEqual(len(first), 1)
        self.assertEqual(colony_events.pending_events(context, {first[0]["signature"]}), [])

    def test_bandaged_animal_is_not_retreated_for_low_health_alone(self):
        self.assertFalse(director.animal_needs_tending({
            "health": 0.42,
            "bleeding_rate": 0.0,
            "tendable_now": False,
        }))
        self.assertTrue(director.animal_needs_tending({
            "health": 0.95,
            "bleeding_rate": 0.0,
            "tendable_now": True,
        }))

    def test_hungry_mobile_animal_is_not_forced_into_patient_feeding(self):
        self.assertFalse(director.animal_needs_assisted_feeding({
            "hunger": 0.2,
            "downed": False,
            "current_job": "GotoWander",
        }))
        self.assertTrue(director.animal_needs_assisted_feeding({
            "hunger": 0.0,
            "downed": True,
            "current_job": "LayDown",
        }))
        self.assertTrue(director.animal_needs_assisted_feeding({
            "hunger": 0.2,
            "downed": True,
            "current_job": "LayDown",
        }))

    def test_only_downed_hungry_colonist_is_force_fed(self):
        self.assertFalse(director.colonist_needs_assisted_feeding({"hunger": 0.0, "downed": False}))
        self.assertTrue(director.colonist_needs_assisted_feeding({"hunger": 0.0, "downed": True}))
        self.assertFalse(director.colonist_needs_assisted_feeding({"hunger": 0.8, "downed": True}))

    def test_successful_patient_feed_has_a_real_completion_cooldown(self):
        state = {"issued": {"animal_feed:7": 1000, "colonist_feed:8": 1000}}
        self.assertTrue(director.issued_recently(
            state, "animal_feed:7", 1000 + director.PATIENT_FEED_RETRY_TICKS - 1,
            retry_ticks=director.PATIENT_FEED_RETRY_TICKS,
        ))
        self.assertTrue(director.issued_recently(
            state, "colonist_feed:8", 1000 + director.PATIENT_FEED_RETRY_TICKS - 1,
            retry_ticks=director.PATIENT_FEED_RETRY_TICKS,
        ))

    def test_model_state_discards_verbose_mod_metadata_and_stays_bounded(self):
        skills = {
            f"Skill{index}": {"level": index, "passion": index % 3, "disabled": False}
            for index in range(20)
        }
        colonists = [{
            "id": index, "name": f"Colonist {index}", "health": 1.0, "hunger": 0.5,
            "rest": 0.6, "mood": 0.7, "downed": False, "current_job": "Work",
            "traits": [{"label": f"Trait {item}"} for item in range(8)],
            "capacities": {"moving": 1.0, "manipulation": 1.0, "sight": 1.0},
            "health_conditions": [{"label": f"Condition {item}", "part": "arm"} for item in range(10)],
            "skills": skills,
        } for index in range(16)]
        directions = {
            f"direction_{index}": {
                "label": "direction " + ("x" * 200), "fit_score": 100 - index,
                "people": [{"pawn": "A", "skill": "Crafting", "level": 10, "flame": "++"}],
                "work_types": ["Crafting"] * 20, "building_programs": ["factory"] * 20,
            }
            for index in range(30)
        }
        snapshot = {
            "game": {"date": "5500", "wealth": 1000},
            "map": {"resources": {"food": 20}, "enemies": 0},
            "colonists": colonists,
            "animals": [{"hunger": 0.0}],
            "development": {
                "building_counts": {f"Building{index}": index for index in range(200)},
                "zones": [{"label": f"Zone {index}"} for index in range(100)],
                "current_research": {"name": "Electricity"},
                "finished_research": [f"Research{index}" for index in range(200)],
                "corpses": [], "item_counts": {}, "rooms": [],
                "active_mods": [{
                    "name": f"Mod {index}", "package_id": f"mod.{index}",
                    "description": "verbose metadata " * 1000,
                } for index in range(40)],
                "profession_context": {
                    "directions": directions,
                    "work_types": [{
                        "def_name": f"Work{index}", "label": "work " + ("y" * 200),
                        "relevant_skills": ["Crafting"],
                    } for index in range(100)],
                },
                "building_catalog_summary": {
                    "total_player_buildings": 500, "available_now": 300,
                    "categories": {f"Category{index}": index for index in range(50)},
                    "worktables": [f"Bench{index}" for index in range(100)],
                    "programs": {f"Program{index}": {"label": "program"} for index in range(50)},
                },
                "user_preferences": {},
            },
        }
        encoded = json.dumps(director.build_decision_state(snapshot), ensure_ascii=False, separators=(",", ":"))
        self.assertLessEqual(len(encoded), 12000)
        self.assertNotIn("verbose metadata", encoded)
        self.assertEqual(json.loads(encoded)["colony_animals"]["hungry"], 1)

    def test_doctrine_execution_uses_strategy_module_without_name_shadowing(self):
        map_state = {"anchor": {"x": 10, "z": 10}, "issued": {}}
        result = director.execute_action(
            None,
            {"map": {"id": 1}, "game": {"tick": 50}},
            map_state,
            "choose_colony_doctrine",
            {
                "doctrine_selection": {"economy_product": "art"},
                "doctrine_direction_audit": {"coverage": {}, "expansions": {}, "available": {}, "unavailable": {}},
            },
        )
        self.assertTrue(result["applied"])
        self.assertEqual(map_state["income_strategy"], "art")

    def test_failed_action_uses_bounded_exponential_backoff(self):
        state = {}
        first = director.register_action_failure(state, "build_freezer", "missing component", now=100.0)
        self.assertEqual(first["count"], 1)
        self.assertEqual(director.action_backoff_remaining(state, "build_freezer", now=100.0), 30.0)
        second = director.register_action_failure(state, "build_freezer", "still missing", now=131.0)
        self.assertEqual(second["count"], 2)
        self.assertEqual(director.action_backoff_remaining(state, "build_freezer", now=131.0), 60.0)
        for index in range(8):
            final = director.register_action_failure(state, "build_freezer", f"failure {index}", now=200.0 + index)
        self.assertEqual(float(final["retry_after"]) - 207.0, 300.0)

    def test_success_clears_action_backoff(self):
        state = {}
        director.register_action_failure(state, "build_freezer", "temporary", now=100.0)
        director.clear_action_failure(state, "build_freezer")
        self.assertEqual(director.action_backoff_remaining(state, "build_freezer", now=100.0), 0.0)

    def test_backed_off_event_option_is_removed_without_hiding_alternatives(self):
        state = {}
        director.register_action_failure(state, "event:heat:pause_sowing", "rejected")
        available, blocked = director.filter_backed_off_choices(
            state,
            {"pause_sowing": "Pause", "emergency_harvest": "Harvest"},
            prefix="event:heat:",
        )
        self.assertEqual(available, ["emergency_harvest"])
        self.assertIn("pause_sowing", blocked)

    def test_cycle_errors_back_off_but_missing_game_stays_responsive(self):
        delay, count = director.cycle_retry_policy("error", 0, 10.0)
        self.assertEqual((delay, count), (10.0, 1))
        delay, count = director.cycle_retry_policy("error", 5, 10.0)
        self.assertEqual((delay, count), (300.0, 6))
        delay, count = director.cycle_retry_policy("waiting", 5, 10.0)
        self.assertEqual((delay, count), (10.0, 0))

    def test_combat_signature_does_not_reissue_order_while_pawns_walk(self):
        snapshot = {"combat": {
            "colonists": [{
                "id": 1, "health": 1.0, "is_dead": False, "is_downed": False,
                "is_drafted": True, "weapon_def": "Gun_Revolver", "current_job": "Goto",
                "position": {"x": 10, "z": 10}, "distance_to_nearest_opponent": 20,
            }],
            "hostiles": [{
                "id": 9, "health": 1.0, "is_dead": False, "is_downed": False,
                "current_job": "AttackStatic", "position": {"x": 60, "z": 60},
            }],
        }}
        first = director.combat_order_signature(snapshot)
        snapshot["combat"]["colonists"][0]["position"] = {"x": 35, "z": 32}
        snapshot["combat"]["colonists"][0]["current_job"] = "Wait_Combat"
        snapshot["combat"]["hostiles"][0]["position"] = {"x": 49, "z": 47}
        self.assertEqual(first, director.combat_order_signature(snapshot))
        snapshot["combat"]["hostiles"][0]["health"] = 0.79
        self.assertEqual(first, director.combat_order_signature(snapshot))
        snapshot["combat"]["colonists"][0]["health"] = 0.79
        self.assertNotEqual(first, director.combat_order_signature(snapshot))

    def test_combat_order_has_minimum_and_maximum_replan_intervals(self):
        first = ("active", 1)
        changed = ("active", 2)
        self.assertTrue(director.combat_replan_due(first, None, 0, False))
        self.assertFalse(director.combat_replan_due(changed, first, 2, True))
        self.assertTrue(director.combat_replan_due(changed, first, 5, True))
        self.assertFalse(director.combat_replan_due(first, first, 29, True))
        self.assertTrue(director.combat_replan_due(first, first, 30, True))
        self.assertTrue(director.combat_replan_due(changed, first, 1, True, urgent=True))

    def test_preemptive_advance_is_short_hop_then_replans_on_assault(self):
        snapshot = {"combat": {
            "colonists": [{"id": 1, "health": 1.0, "current_job": "Wait_Combat"},
                          {"id": 2, "health": 1.0, "current_job": "Wait_Combat"}],
            "hostiles": [{"id": 9, "current_job": "GotoWander", "health": 1.0}],
        }}
        record = {
            "decision": {"choice": "preemptive_strike"},
            "action": {"commands": [{"endpoint": "/api/v1/combat/tactic", "body": {
                "tactic": "preemptive_strike", "fighter_ids": [1, 2], "target_pawn_id": 9,
            }}]},
            "result": {"responses": [{"positioned_pawn_ids": [1, 2], "attacking_pawn_ids": []}]},
        }
        self.assertEqual(director.preemptive_advance_state(snapshot, record, 1)[0], "wait")
        self.assertEqual(director.preemptive_advance_state(snapshot, record, 3)[0], "advance")
        snapshot["combat"]["colonists"][0]["current_job"] = "Goto"
        self.assertEqual(director.preemptive_advance_state(snapshot, record, 3)[0], "wait")
        snapshot["combat"]["hostiles"][0]["current_job"] = "AttackMelee"
        self.assertEqual(director.preemptive_advance_state(snapshot, record, 3)[0], "replan")

    def test_laya_can_resume_colony_decisions_during_raid_staging(self):
        snapshot = {"combat": {
            "colonists": [{"id": 1, "is_drafted": False}],
            "hostiles": [{"id": 9, "current_job": "Wait_Wander", "is_dead": False, "is_downed": False,
                          "distance_to_nearest_opponent": 80}],
        }, "map": {"enemies": 1, "resources": {}}, "development": {}, "colonists": [], "animals": []}
        prepared = {"decision": {"choice": "prepare_undrafted"}}
        self.assertTrue(director.staging_development_allowed(snapshot, prepared))
        context = director.model_decision_context(snapshot)
        self.assertEqual(context["threat_state"], {"phase": "preparing", "nearest": 80})
        snapshot["combat"]["colonists"][0]["is_drafted"] = True
        self.assertFalse(director.staging_development_allowed(snapshot, prepared))
        snapshot["combat"]["colonists"][0]["is_drafted"] = False
        snapshot["combat"]["hostiles"][0]["current_job"] = "AttackMelee"
        self.assertFalse(director.staging_development_allowed(snapshot, prepared))
        self.assertEqual(director.model_decision_context(snapshot)["threat_state"]["phase"], "active")

    def test_locked_heartbeat_replace_falls_back_without_crashing(self):
        with tempfile.TemporaryDirectory() as folder:
            target = pathlib.Path(folder) / "runtime-status.json"
            with mock.patch.object(pathlib.Path, "replace", side_effect=PermissionError("locked")):
                written = director.write_runtime_status(target, "running", "healthy")
            self.assertTrue(written)
            self.assertIn('"state": "running"', target.read_text(encoding="utf-8"))

    def test_loading_older_save_discards_orders_from_future_ticks(self):
        state = {"issued": {"priority:Hunting": 5000, "growing": 6000, "old": 50}}
        removed = director.reconcile_issued_timeline(state, 1000)
        self.assertEqual(set(removed), {"priority:Hunting", "growing"})
        self.assertEqual(state["issued"], {"old": 50})
        state["issued"]["future"] = 2000
        self.assertFalse(director.issued_recently(state, "future", 1000))
        self.assertNotIn("future", state["issued"])

    def test_starving_colony_offers_food_actions_before_waiting(self):
        snapshot = {
            "game": {"tick": 1000},
            "map": {"resources": {"food": 0, "raw_food": 0, "meals": 0}},
            "colonists": [{"id": 1, "hunger": 0.05, "position": {"x": 10, "z": 10}}],
            "animals": [],
            "wild_animals": [{
                "id": 9, "def": "Hare", "predator": False, "harm_revenge_chance": 0,
                "combat_power": 33, "meat_amount": 31, "position": {"x": 20, "z": 20},
            }],
            "combat": {"colonists": [{
                "id": 1, "has_ranged_weapon": True, "is_downed": False,
                "health": 1.0, "shooting_skill": 8,
            }]},
            "development": {
                "building_counts": {}, "zones": [], "finished_research": [], "current_research": {},
                "item_counts": {}, "forbidden": [], "corpses": [], "plants": [{
                    "thing_id": 7, "def_name": "Plant_Berry", "label": "berry bush",
                    "harvestable_now": True, "harvest_yield": 10, "harvested_thing_def": "RawBerries",
                    "position": {"x": 30, "z": 20},
                }],
            },
        }
        candidates, details = director.candidate_actions(None, snapshot, {"anchor": {"x": 10, "z": 10}, "issued": {}})
        self.assertIn("harvest_local_plants", candidates)
        self.assertIn("designate_safe_hunting", candidates)
        self.assertIn("hold_survival", candidates)
        self.assertIn("create_food_stockpile", candidates)
        self.assertIn("choose_colony_doctrine", candidates)
        self.assertTrue(details["food_emergency_context"]["safe_hunt_targets"])

        medical = copy.deepcopy(snapshot)
        medical["map"]["resources"] = {"food": 50, "raw_food": 20, "meals": 10, "medicine": 1}
        medical["development"]["zones"] = [
            {"type": "Stockpile", "label": "Laya Food"},
            {"id": 7, "type": "Growing", "label": "Growing zone"},
        ]
        medical["development"]["building_counts"] = {"SleepingSpot": 2}
        medical["development"]["work_tables"] = []
        medical["development"]["current_research"] = {"name": "Electricity"}
        medical["development"]["weather"] = {"growth_season_now": True}
        medical["colonists"][0].update(hunger=0.8, health=0.55, bleeding_rate=0.12, downed=False)
        doctor = {"id": 2, "name": "Doctor", "health": 1.0, "hunger": 0.8,
                  "position": {"x": 12, "z": 10}}
        medical["colonists"].append(doctor)
        with mock.patch.object(director.bridge, "choose_worker", return_value=doctor):
            choices, _ = director.candidate_actions(
                None, medical, {"anchor": {"x": 10, "z": 10}, "issued": {}},
            )
        self.assertIn("prioritize_doctor", choices)
        self.assertIn("harvest_local_plants", choices)

    def test_decodes_rle_terrain(self):
        width, height, cells = director.decode_terrain({
            "width": 3,
            "height": 2,
            "palette": ["Soil", "Sand"],
            "grid": [3, 0, 3, 1],
        })
        self.assertEqual((width, height), (3, 2))
        self.assertEqual(cells, ["Soil"] * 3 + ["Sand"] * 3)

    def test_finds_fertile_rectangle(self):
        result = director.find_terrain_rect(
            {"width": 6, "height": 6, "palette": ["Sand", "Soil"], "grid": [7, 0, 4, 1, 2, 0, 4, 1, 19, 0]},
            {"x": 2, "z": 2},
            2,
            2,
            {"Soil"},
            radius=5,
        )
        self.assertEqual(result, {"x": 2, "z": 1})

    def test_single_feasible_action_does_not_call_model(self):
        decision = director.choose_action(None, {}, ["create_stockpile"])
        self.assertEqual(decision["choice"], "create_stockpile")
        self.assertEqual(decision["raw"]["mode"], "single_feasible_action")

    def test_overlay_uses_real_family_probabilities_after_singleton_narrowing(self):
        snapshot = {"map": {"resources": {"food": 39}, "enemies": 0},
                    "colonists": [], "animals": [], "development": {"corpses": [], "trade_value": 0}}
        decision = {"choice": "choose_colony_doctrine", "raw": {
            "answers": {"colony_goal_action": {"choice": "choose_colony_doctrine",
                                                "probabilities": {"choose_colony_doctrine": 1.0}}},
            "family": {"answers": {"colony_goal_family": {
                "choice": "choose_colony_doctrine",
                "probabilities": {"choose_colony_doctrine": 0.3, "hold_survival": 0.7},
            }}},
        }}
        with mock.patch.object(director, "show_overlay") as overlay:
            director.publish_overlay(None, snapshot, ["choose_colony_doctrine"], decision)
        bars = overlay.call_args.kwargs["bars"]
        self.assertEqual(len(bars), 2)
        self.assertEqual({bar["value"] for bar in bars}, {0.3, 0.7})
        self.assertTrue(next(bar for bar in bars if bar["selected"])["value"] < 1.0)

    def test_overlay_shortens_labels_without_changing_probabilities(self):
        bars = director.probability_bars(
            {"trade_now": 0.43, "skip_trade": 0.57},
            {"trade_now": "A very long trader option explaining every possible detail of the transaction",
             "skip_trade": "Skip trade"},
            "skip_trade", 5,
        )
        self.assertLessEqual(len(bars[1]["label"]), 44)
        self.assertEqual([bar["value"] for bar in bars], [0.57, 0.43])

    def test_english_game_overlay_has_no_cyrillic(self):
        class Client:
            def __init__(self):
                self.body = None

            def get(self, path):
                self.assert_path = path
                return {"language": "English"}

            def post(self, path, body):
                self.body = body

        client = Client()
        snapshot = {"map": {"resources": {"food": 39}, "enemies": 0},
                    "colonists": [], "animals": [], "development": {"corpses": [], "trade_value": 0}}
        decision = {"choice": "build_starter_base", "raw": {"answers": {
            "colony_goal_action": {"choice": "build_starter_base", "probabilities": {
                "build_starter_base": 0.62, "hold_survival": 0.38,
            }}}}}
        director.publish_overlay(client, snapshot, ["build_starter_base", "hold_survival"], decision)
        self.assertEqual(client.assert_path, "/api/v1/game/settings")
        self.assertIn("Chosen: Starter base", client.body["text"])
        self.assertFalse(any("\u0400" <= char <= "\u04ff" for char in client.body["text"]))
        self.assertFalse(any("\u0400" <= char <= "\u04ff"
                             for bar in client.body["bars"] for char in bar["label"]))

    def test_live_moded_research_is_a_model_choice_not_ship_route(self):
        snapshot = {"colonists": [], "game": {}, "map": {"resources": {}}, "development": {
            "building_counts": {}, "zones": [], "research_tree": [
                {"name": "ShipBasics", "can_start_now": False, "is_finished": False},
                {"name": "Mod_AlgaePower", "label": "Algae generators", "can_start_now": True, "research_points": 350},
            ], "current_research": {"name": "none"},
        }}
        options = director.live_research_options(snapshot)
        self.assertEqual(set(options), {"Mod_AlgaePower"})
        agent = self.FakeAgent(["select_research"])
        snapshot["development"]["live_research_options"] = options
        decision = director.choose_action(agent, snapshot, ["hold_survival", "select_research"])
        self.assertEqual(decision["research_target"], "Mod_AlgaePower")
        self.assertEqual(len(agent.calls), 1)  # no fake one-option target question

    def test_live_mod_work_asks_work_then_worker_then_priority(self):
        colonists = [{"id": 7, "name": "Ada", "health": 0.8, "pain": 0.1, "downed": False,
                      "work_priorities": {"Mod_AlgaeFarming": {"priority": 3, "disabled": False}},
                      "skills": {"Plants": {"level": 12, "passion": 2}}, "traits": []}]
        snapshot = {"colonists": colonists, "game": {}, "map": {"resources": {}}, "development": {
            "building_counts": {}, "zones": [], "work_types": [{"def_name": "Mod_AlgaeFarming", "label": "Algae farming", "relevant_skills": ["Plants"]}],
        }}
        snapshot["development"]["live_work_options"] = director.live_work_options(snapshot)
        self.assertIn("Mod_AlgaeFarming", snapshot["development"]["live_work_options"])
        agent = self.FakeAgent(["set_work_priority", "1"])
        decision = director.choose_action(agent, snapshot, ["hold_survival", "set_work_priority"])
        self.assertEqual((decision["work_type"], decision["worker_pawn"], decision["work_priority"]),
                         ("Mod_AlgaeFarming", 7, 1))
        self.assertEqual(len(agent.calls), 2)  # one-option work/worker resolved by code
        self.assertIn("Plants 12", director.worker_criteria(snapshot, "Mod_AlgaeFarming")["7"])

        class Client:
            def __init__(self):
                self.calls = []
            def post(self, endpoint, **kwargs):
                self.calls.append((endpoint, kwargs))
                return {"success": True}

        client = Client()
        result = director.execute_action(client, {**snapshot, "map": {"id": 1, "resources": {}}},
                                         {"issued": {}, "anchor": {"x": 10, "z": 10}},
                                         "set_work_priority", decision)
        self.assertTrue(result["applied"])
        self.assertEqual(client.calls[0][1]["body"], {"id": 7, "work": "Mod_AlgaeFarming", "priority": 1})

    def test_large_option_set_keeps_last_option_reachable(self):
        options = {f"option_{index}": f"Project {index}" for index in range(17)}
        class TailAgent:
            def __init__(self):
                self.calls = []
            def predict(self, state, questions):
                self.calls.append(questions)
                question_id, question = next(iter(questions.items()))
                criteria = question["criteria"]
                chosen = "option_16" if "option_16" in criteria else next(iter(criteria))
                return {"answers": {question_id: {"choice": chosen, "confidence": 0.9}}}
        agent = TailAgent()
        selected, raw = director.ask_laya_choice(agent, {}, "project", "Choose a project", options)
        self.assertEqual(selected, "option_16")
        self.assertEqual(len(agent.calls), 4)
        self.assertEqual(len(raw["narrowing"]), 3)
        self.assertEqual(set().union(*(set(next(iter(call.values()))["criteria"]) for call in agent.calls[:-1])), set(options))

    def test_rejected_hunting_does_not_ask_for_a_target(self):
        agent = self.FakeAgent(["hold_survival"])
        snapshot = {"colonists": [], "game": {}, "map": {"resources": {}}, "development": {
            "hunt_options": [{"id": 7, "def": "Hare"}], "fighter_context": {}, "building_counts": {}, "zones": [],
        }}
        result = director.choose_action(agent, snapshot, ["designate_safe_hunting", "hold_survival"])
        self.assertEqual(result["choice"], "hold_survival")
        self.assertEqual(len(agent.calls), 1)
        self.assertEqual(set(agent.calls[0]), {"colony_goal_action"})

    def test_selected_hunting_asks_target_in_second_stage_only(self):
        agent = self.FakeAgent(["designate_safe_hunting", "7"])
        snapshot = {"colonists": [], "game": {}, "map": {"resources": {}}, "development": {
            "hunt_options": [{"id": 7, "def": "Hare", "gender": "Female", "combat_power": 10, "harm_revenge_chance": 0,
                              "meat_amount": 18, "leather_amount": 8, "market_value": 60},
                             {"id": 8, "def": "Deer", "gender": "Male", "combat_power": 30, "harm_revenge_chance": 0.02,
                              "meat_amount": 55, "leather_amount": 20, "market_value": 150}],
            "wild_plant_options": {"Plant_Ambrosia": {"count": 4}}, "fighter_context": {}, "building_counts": {}, "zones": [],
        }}
        result = director.choose_action(agent, snapshot, ["designate_safe_hunting", "hold_survival"])
        self.assertEqual(result["hunt_target"], 7)
        self.assertEqual(len(agent.calls), 2)
        self.assertEqual(set(agent.calls[1]), {"hunt_target"})
        self.assertNotIn("wild_plant_type", agent.calls[1])

    def test_rejected_wild_harvest_does_not_ask_which_plant(self):
        agent = self.FakeAgent(["hold_survival"])
        snapshot = {"colonists": [], "game": {}, "map": {"resources": {}}, "development": {
            "wild_plant_options": {"Plant_Ambrosia": {"label": "ambrosia", "count": 4, "expected_yield": 16, "harvested_thing": "Ambrosia"}},
            "building_counts": {}, "zones": [],
        }}
        director.choose_action(agent, snapshot, ["harvest_local_plants", "hold_survival"])
        self.assertEqual(len(agent.calls), 1)

    def test_starter_blueprint_contains_real_work(self):
        layout = director.starter_base_blueprint(3)
        defs = [row["def_name"] for row in layout["buildings"]]
        self.assertIn("FueledStove", defs)
        self.assertIn("SimpleResearchBench", defs)
        self.assertLessEqual(layout["width"], 11)

    def test_emergency_sleeping_spots_do_not_consume_materials(self):
        layout = director.sleeping_spots_blueprint(3)
        self.assertEqual(
            [row["def_name"] for row in layout["buildings"]],
            ["SleepingSpot", "SleepingSpot", "SleepingSpot", "SleepingSpot"],
        )
        self.assertTrue(all("stuff_def_name" not in row for row in layout["buildings"]))

    def test_animal_sleeping_spots_are_free_markers(self):
        layout = director.animal_spots_blueprint(2)
        self.assertEqual(
            [row["def_name"] for row in layout["buildings"]],
            ["AnimalSleepingSpot", "AnimalSleepingSpot"],
        )
        self.assertTrue(all("stuff_def_name" not in row for row in layout["buildings"]))

    def test_cemetery_contains_spaced_real_graves(self):
        layout = director.cemetery_blueprint(8)
        self.assertEqual(len(layout["buildings"]), 8)
        self.assertTrue(all(row["def_name"] == "Grave" for row in layout["buildings"]))
        self.assertEqual(len({(row["rel_x"], row["rel_z"]) for row in layout["buildings"]}), 8)

    def test_prison_is_enclosed_and_uses_normal_sleeping_spots(self):
        layout = director.prison_blueprint()
        defs = [row["def_name"] for row in layout["buildings"]]
        self.assertEqual(defs.count("SleepingSpot"), 2)
        self.assertEqual(defs.count("Door"), 1)
        self.assertGreaterEqual(defs.count("Wall"), 20)

    def test_room_floor_blueprint_uses_only_real_room_cells(self):
        layout, origin = director.room_floor_blueprint(
            [{"x": 10, "z": 20}, {"x": 11, "z": 20}, {"x": 10, "z": 21}],
            "Concrete",
        )
        self.assertEqual(origin, {"x": 10, "z": 20})
        self.assertEqual(len(layout["floors"]), 3)
        self.assertTrue(all(row["def_name"] == "Concrete" for row in layout["floors"]))

    def test_sterile_floor_requires_large_reserves_and_skill(self):
        scarce = director.affordable_floor_options(
            {"Steel": 100, "Silver": 200}, {"SterileMaterials"}, 20, 6
        )
        rich = director.affordable_floor_options(
            {"Steel": 1000, "Silver": 2000}, {"SterileMaterials", "Smithing"}, 20, 6
        )
        self.assertNotIn("SterileTile", scarce)
        self.assertIn("SterileTile", rich)

    def test_outdoor_paths_never_offer_steel_floors(self):
        options = director.affordable_floor_options(
            {"Steel": 5000, "BlocksGranite": 1000}, {"Stonecutting", "Smithing"}, 60, 12, pathway=True
        )
        self.assertNotIn("Concrete", options)
        self.assertNotIn("MetalTile", options)
        self.assertIn("FlagstoneGranite", options)

    def test_freezer_can_reuse_existing_generator(self):
        layout = director.freezer_blueprint(include_generator=False)
        defs = [row["def_name"] for row in layout["buildings"]]
        self.assertIn("Cooler", defs)
        self.assertNotIn("WoodFiredGenerator", defs)

    def test_freezer_is_not_offered_without_components(self):
        missing = director.freezer_resource_plan(
            {}, {"Steel": 500, "WoodLog": 500, "ComponentIndustrial": 2}, 8, {"Electricity"}
        )
        powered = director.freezer_resource_plan(
            {"SolarGenerator": 1}, {"Steel": 500, "WoodLog": 500, "ComponentIndustrial": 3}, 8, {"Electricity"}
        )
        self.assertIsNone(missing)
        self.assertFalse(powered["include_generator"])

    def test_basic_beds_are_real_beds(self):
        layout = director.basic_beds_blueprint(2)
        self.assertEqual([row["def_name"] for row in layout["buildings"]], ["Bed", "Bed"])

    def test_temple_is_floored_and_has_no_beds_or_worktables(self):
        layout = director.temple_blueprint("Altar_Small", "BlocksGranite")
        defs = [row["def_name"] for row in layout["buildings"]]
        self.assertIn("Altar_Small", defs)
        self.assertEqual(len(layout["floors"]), 49)
        self.assertTrue(all(row["def_name"] == "TileGranite" for row in layout["floors"]))
        self.assertFalse(any(name in {"Bed", "SleepingSpot", "FueledStove", "SimpleResearchBench"} for name in defs))

    def test_killbox_keeps_an_open_entrance_and_uses_traps(self):
        layout = director.killbox_blueprint()
        defs = [row["def_name"] for row in layout["buildings"]]
        self.assertIn("TrapSpike", defs)
        self.assertIn("Barricade", defs)
        self.assertFalse(any(row["def_name"] == "Wall" and row["rel_x"] == 4 and row["rel_z"] == 0 for row in layout["buildings"]))

    def test_structure_materials_exclude_scarce_wood_and_offer_fireproof_stone(self):
        scarce = director.structure_material_options({"WoodLog": 180, "BlocksGranite": 160})
        stocked = director.structure_material_options({"WoodLog": 500, "BlocksGranite": 400})
        self.assertNotIn("WoodLog", scarce)
        self.assertNotIn("BlocksGranite", scarce)
        self.assertIn("WoodLog", stocked)
        self.assertIn("BlocksGranite", stocked)
        self.assertIn("fireproof", stocked["BlocksGranite"])

    def test_private_bedroom_is_enclosed_and_uses_selected_material(self):
        layout = director.private_bedroom_blueprint("BlocksGranite", powered=True, complex_furniture=True)
        walls = [row for row in layout["buildings"] if row["def_name"] == "Wall"]
        self.assertEqual(len(walls), 23)
        self.assertTrue(all(row["stuff_def_name"] == "BlocksGranite" for row in walls))
        self.assertIn("Bed", [row["def_name"] for row in layout["buildings"]])
        self.assertIn("Dresser", [row["def_name"] for row in layout["buildings"]])

    def test_animal_barn_can_use_straw_and_sleeping_spots(self):
        layout = director.animal_barn_blueprint("BlocksLimestone", 3, straw_floor=True, powered=True, climate="cold")
        defs = [row["def_name"] for row in layout["buildings"]]
        self.assertIn("AnimalFlap", defs)
        self.assertGreaterEqual(defs.count("AnimalSleepingSpot"), 3)
        self.assertIn("Heater", defs)
        self.assertTrue(layout["floors"])
        self.assertTrue(all(row["def_name"] == "StrawMatting" for row in layout["floors"]))

    def test_mountain_bedroom_requires_full_verified_rock_block(self):
        cells = [z * 20 + x for z in range(4, 11) for x in range(5, 12)]
        rect = director.mining_bedroom_rect({
            "map_width": 20,
            "ores": {"MineableGranite": {"cells": cells}},
        }, {"x": 8, "z": 8})
        self.assertEqual(rect, ({"x": 5, "y": 0, "z": 4}, {"x": 11, "y": 0, "z": 10}))

    def test_architect_generates_twenty_four_distinct_lit_houses(self):
        candidates = director.architect.generate_house_candidates(
            "BlocksGranite",
            [],
            {"Stonecutting", "Electricity", "ComplexFurniture"},
            {"BlocksGranite": 5000, "WoodLog": 2000},
            powered=True,
            climate="temperate",
            seed=91,
        )
        self.assertEqual(len(candidates), 24)
        signatures = {
            (row["style"], row["width"], row["height"], row["summary"])
            for row in candidates.values()
        }
        self.assertEqual(len(signatures), 24)
        for row in candidates.values():
            defs = [item["def_name"] for item in row["layout"]["buildings"]]
            self.assertIn("Door", defs)
            self.assertIn("StandingLamp", defs)
            self.assertTrue("Bed" in defs or "DoubleBed" in defs)

    def test_house_generation_is_deterministic_for_saved_seed(self):
        args = ("WoodLog", [], {"Electricity"}, {"WoodLog": 4000})
        first = director.architect.generate_house_candidates(*args, powered=True, climate="cold", seed=7)
        second = director.architect.generate_house_candidates(*args, powered=True, climate="cold", seed=7)
        self.assertEqual(first, second)

    def test_house_entrance_is_laya_chosen_but_door_offset_varies_by_seed(self):
        context = {"material": "BlocksGranite", "entry_side": "west", "building_catalog": [],
                   "finished_research": [], "item_counts": {"BlocksGranite": 2000, "WoodLog": 1000},
                   "powered": False, "climate": "temperate"}
        door_positions = set()
        for seed in range(8):
            variants = director.architect.generate_program_variants("residence", context, seed=seed)
            layout = variants["house_compact_1"]["layout"]
            door = next(row for row in layout["buildings"] if row["def_name"] == "Door")
            self.assertEqual(door["rel_x"], 0)
            self.assertTrue(all(row["stuff_def_name"] == "BlocksGranite"
                                for row in layout["buildings"] if row["def_name"] == "Wall"))
            door_positions.add((door["rel_x"], door["rel_z"]))
            self.assertEqual(variants, director.architect.generate_program_variants("residence", context, seed=seed))
        self.assertGreater(len(door_positions), 1)

    def test_architecture_materials_exclude_unfinishable_wall_plans(self):
        context = {"building_catalog": [], "finished_research": [], "item_counts": {"WoodLog": 205},
                   "material": "WoodLog", "powered": False, "climate": "temperate"}
        options = director.architect.affordable_material_options("residence", context,
                                                                   {"WoodLog": "205 wood"}, seed=1)
        self.assertEqual(options, {})
        context["item_counts"]["WoodLog"] = 1000
        options = director.architect.affordable_material_options("residence", context,
                                                                   {"WoodLog": "1000 wood"}, seed=1)
        self.assertIn("WoodLog", options)

    def test_generated_architecture_has_no_overlapping_anchors(self):
        base = {"building_catalog": [], "finished_research": ["Electricity"],
                "item_counts": {"WoodLog": 9000, "Steel": 5000},
                "material": "WoodLog", "powered": True, "climate": "cold"}
        for program in director.architect.PROGRAM_CATALOG:
            for entry_side in ("north", "east", "south", "west"):
                for seed in range(4):
                    variants = director.architect.generate_program_variants(
                        program, {**base, "entry_side": entry_side}, seed=seed)
                    self.assertTrue(variants)
                    for key, variant in variants.items():
                        with self.subTest(program=program, side=entry_side, seed=seed, variant=key):
                            self.assertEqual(director.architect.layout_anchor_conflicts(
                                variant["layout"]), [])

    def test_freezer_cooler_does_not_replace_selected_east_entrance(self):
        context = {"building_catalog": [], "finished_research": [],
                   "item_counts": {"WoodLog": 9000}, "material": "WoodLog",
                   "entry_side": "east", "powered": False, "climate": "temperate"}
        for seed in range(8):
            layout = director.architect.generate_program_variants("freezer", context, seed=seed)["freezer_1"]["layout"]
            door = next(item for item in layout["buildings"] if item["def_name"] == "Door")
            cooler = next(item for item in layout["buildings"] if item["def_name"] == "Cooler")
            self.assertEqual(door["rel_x"], layout["width"] - 1)
            self.assertNotEqual((door["rel_x"], door["rel_z"]),
                                (cooler["rel_x"], cooler["rel_z"]))

    def test_freezer_plan_needs_unlocked_cooler_and_components(self):
        context = {"building_catalog": [{"def_name": "Cooler", "available_now": False,
                                         "cost_list": [{"thing_def": "Steel", "count": 90},
                                                       {"thing_def": "ComponentIndustrial", "count": 3}]}],
                   "finished_research": [],
                   "item_counts": {"WoodLog": 2000, "Steel": 500, "ComponentIndustrial": 2},
                   "material": "WoodLog", "powered": True, "climate": "temperate"}
        self.assertEqual(director.architect.generate_program_variants("freezer", context), {})
        context["building_catalog"][0]["available_now"] = True
        variants = director.architect.generate_program_variants("freezer", context)
        self.assertEqual(director.architect.affordable_variants(variants, context), {})
        context["item_counts"]["ComponentIndustrial"] = 4
        feasible = director.architect.affordable_variants(variants, context)
        self.assertTrue(feasible)
        self.assertEqual(feasible["freezer_1"]["estimated_stuff_cost"]["ComponentIndustrial"], 3)

    def test_architecture_cost_includes_known_floor_materials(self):
        layout = director.architect.blueprint(
            [director.architect.building("Wall", 0, 0, stuff="BlocksGranite")], 2, 2,
            [director.architect.floor("TileGranite", 1, 1)])
        self.assertEqual(director.architect.estimated_stuff_cost(layout, []), {"BlocksGranite": 9})

    def test_stone_throne_room_uses_compatible_fabric_drapes(self):
        context = {"building_catalog": [{"def_name": "Drape", "available_now": True,
                                         "cost_stuff_count": 20, "stuff_categories": ["Fabric"]}],
                   "finished_research": [], "item_counts": {"BlocksGranite": 9000, "Cloth": 1000},
                   "material": "BlocksGranite", "powered": False}
        layout = director.architect.generate_program_variants("throne_room", context)["throne_room_1"]["layout"]
        drapes = [item for item in layout["buildings"] if item["def_name"] == "Drape"]
        self.assertTrue(drapes)
        self.assertTrue(all(item["stuff_def_name"] == "Cloth" for item in drapes))
        context["item_counts"].pop("Cloth")
        context["item_counts"]["ComponentIndustrial"] = 10000
        self.assertEqual(director.architect.generate_program_variants("throne_room", context), {})

    def test_selected_wall_material_is_not_silently_replaced(self):
        context = {"building_catalog": [{"def_name": "Wall", "available_now": True,
                                         "cost_stuff_count": 5, "stuff_categories": ["Woody", "Stony"]}],
                   "finished_research": [], "item_counts": {"WoodLog": 2000},
                   "material": "BlocksGranite", "powered": False}
        self.assertEqual(director.architect.generate_program_variants("residence", context), {})

    def test_hospital_variant_upgrades_beds_monitor_floor_and_light(self):
        catalog = [
            {"def_name": name, "available_now": True}
            for name in ("HospitalBed", "VitalsMonitor", "StandingLamp", "Shelf", "Wall", "Door")
        ]
        variants = director.architect.generate_program_variants("hospital", {
            "building_catalog": catalog,
            "finished_research": ["Electricity", "SterileMaterials"],
            "item_counts": {"Silver": 10000, "Steel": 5000},
            "material": "BlocksGranite",
            "powered": True,
            "climate": "temperate",
        })
        expanded = variants["hospital_3"]["layout"]
        defs = [row["def_name"] for row in expanded["buildings"]]
        self.assertGreaterEqual(defs.count("HospitalBed"), 4)
        self.assertIn("VitalsMonitor", defs)
        self.assertIn("StandingLamp", defs)
        self.assertTrue(expanded["floors"])
        self.assertTrue(all(row["def_name"] == "SterileTile" for row in expanded["floors"]))

    def test_throne_room_never_contains_beds_or_workbenches(self):
        catalog = [
            {"def_name": name, "available_now": True}
            for name in ("Throne", "GrandThrone", "Brazier", "Column", "Drape", "StandingLamp")
        ]
        layout = director.architect.generate_program_variants("throne_room", {
            "building_catalog": catalog,
            "finished_research": ["Electricity", "Stonecutting"],
            "item_counts": {"BlocksGranite": 10000},
            "material": "BlocksGranite",
            "powered": True,
            "royalty": {"colonists": [{"title_def_name": "Count"}]},
        })["throne_room_2"]["layout"]
        defs = {row["def_name"] for row in layout["buildings"]}
        self.assertIn("GrandThrone", defs)
        self.assertFalse(defs & {"Bed", "HospitalBed", "SimpleResearchBench", "FueledStove"})

    def test_profession_direction_uses_large_passion_not_level_alone(self):
        colonists = [
            {"id": 1, "name": "Veteran", "health": 1, "skills": {"Crafting": {"level": 9, "passion": 0}}},
            {"id": 2, "name": "Apprentice", "health": 1, "skills": {"Crafting": {"level": 5, "passion": 2}}},
        ]
        work = [{"def_name": "Crafting", "label": "Craft", "relevant_skills": ["Crafting"]}]
        context = director.professions.profession_context(colonists, work)
        craft_people = context["directions"]["craft_industry"]["people"]
        self.assertEqual(craft_people[0]["pawn"], "Apprentice")
        self.assertEqual(context["skills"]["Crafting"]["learning_percent"], 150)

    def test_training_plan_maps_skill_to_live_modded_work_type(self):
        colonists = [{
            "id": 3, "name": "Learner", "health": 1, "downed": False,
            "skills": {"Crafting": {"level": 4, "passion": 2, "disabled": False}},
            "work_priorities": {"ModdedFabrication": {"disabled": False}}, "traits": [], "capacities": {},
        }]
        work = [{"def_name": "ModdedFabrication", "relevant_skills": ["Crafting"], "natural_priority": 10}]
        options = director.professions.training_options(colonists, work)
        self.assertEqual(next(iter(options.values()))["work_type"], "ModdedFabrication")
        self.assertEqual(next(iter(options.values()))["xp_percent"], 150)

    def test_night_owl_schedule_sleeps_in_daytime_window(self):
        schedule = director.professions.night_owl_schedule()
        self.assertTrue(all(schedule[hour] == "Sleep" for hour in range(11, 19)))
        self.assertTrue(all(schedule[hour] == "Anything" for hour in list(range(0, 11)) + list(range(19, 24))))

    def test_workbench_upgrade_waits_for_research_and_costs(self):
        base = {
            "building_counts": {"FueledStove": 1},
            "item_counts": {"Steel": 200, "ComponentIndustrial": 5},
            "building_catalog": [{
                "def_name": "ElectricStove", "available_now": False,
                "cost_list": [{"thing_def": "Steel", "count": 80}, {"thing_def": "ComponentIndustrial", "count": 2}],
            }],
        }
        self.assertNotIn("FueledStove|ElectricStove", director.architect.workbench_upgrade_options(base))
        base["building_catalog"][0]["available_now"] = True
        self.assertIn("FueledStove|ElectricStove", director.architect.workbench_upgrade_options(base))

    def test_rejected_architecture_does_not_ask_program_or_layout(self):
        agent = self.FakeAgent(["hold_survival"])
        snapshot = {"colonists": [], "game": {}, "map": {"resources": {}}, "development": {
            "building_counts": {}, "zones": [],
            "architecture_program_options": {"residence": "housing shortage"},
            "architecture_context": {},
        }}
        result = director.choose_action(agent, snapshot, ["plan_architecture", "hold_survival"])
        self.assertEqual(result["choice"], "hold_survival")
        self.assertEqual(len(agent.calls), 1)

    def test_selected_residence_uses_program_style_variant_hierarchy(self):
        agent = self.FakeAgent(["plan_architecture", "south", "compact", "house_compact_1"])
        snapshot = {"colonists": [], "game": {}, "map": {"resources": {}}, "development": {
            "building_counts": {}, "zones": [],
            "architecture_program_options": {"residence": "housing shortage"},
            "architecture_context": {
                "building_catalog": [], "finished_research": [], "item_counts": {"WoodLog": 2000},
                "material": "WoodLog", "powered": False, "climate": "temperate", "variant_seed": 1,
            },
        }}
        result = director.choose_action(agent, snapshot, ["plan_architecture", "hold_survival"])
        self.assertEqual(result["architecture_program"], "residence")
        self.assertEqual(result["architecture_material"], "WoodLog")
        self.assertEqual(result["architecture_entry"], "south")
        self.assertEqual(result["architecture_house_style"], "compact")
        self.assertEqual(result["architecture_variant"], "house_compact_1")
        self.assertEqual(len(agent.calls), 4)

    def test_laya_selects_wall_material_before_layout(self):
        agent = self.FakeAgent(["plan_architecture", "BlocksGranite", "west",
                                "compact", "house_compact_1"])
        context = {"building_catalog": [], "finished_research": [],
                   "item_counts": {"WoodLog": 2000, "BlocksGranite": 2000},
                   "material_options": {"WoodLog": "wood", "BlocksGranite": "fireproof stone"},
                   "material": "WoodLog", "powered": False, "climate": "temperate", "variant_seed": 5}
        snapshot = {"colonists": [], "game": {}, "map": {"resources": {}}, "development": {
            "building_counts": {}, "zones": [], "architecture_program_options": {"residence": "need homes"},
            "architecture_context": context}}
        result = director.choose_action(agent, snapshot, ["plan_architecture", "hold_survival"])
        self.assertEqual(result["architecture_material"], "BlocksGranite")
        self.assertEqual(result["architecture_entry"], "west")
        self.assertEqual(len(agent.calls), 5)

    def test_architecture_execution_uses_layas_saved_design(self):
        context = {"building_catalog": [], "finished_research": [],
                   "item_counts": {"WoodLog": 2000, "BlocksGranite": 2000},
                   "material_options": {"WoodLog": "wood", "BlocksGranite": "stone"},
                   "material": "WoodLog", "powered": False, "climate": "temperate", "variant_seed": 5}
        agent = self.FakeAgent(["plan_architecture", "BlocksGranite", "west",
                                "compact", "house_compact_1"])
        snapshot = {"colonists": [], "game": {"tick": 500}, "map": {"id": 1, "resources": {}},
                    "development": {"building_counts": {}, "zones": [],
                                    "architecture_program_options": {"residence": "need homes"},
                                    "architecture_context": context}}
        decision = director.choose_action(agent, snapshot, ["plan_architecture", "hold_survival"])

        class Client:
            def __init__(self):
                self.posts = []

            def get(self, endpoint, **kwargs):
                return {}

            def post(self, endpoint, **kwargs):
                self.posts.append((endpoint, kwargs))
                return {"success": True}

        client = Client()
        with mock.patch.object(director, "find_terrain_rect", return_value={"x": 40, "z": 20}), \
             mock.patch.object(director, "prioritize", return_value={"applied": True}):
            result = director.execute_action(client, snapshot, {"issued": {}, "anchor": {"x": 10, "z": 10}},
                                             "plan_architecture", {**decision, "architecture_context": context})
        self.assertTrue(result["applied"])
        self.assertEqual(result["project"]["material"], "BlocksGranite")
        self.assertEqual(result["project"]["entry"], "west")
        endpoint, request = client.posts[0]
        self.assertEqual(endpoint, "/api/v1/builder/blueprint")
        buildings = request["body"]["blueprint"]["buildings"]
        self.assertTrue(all(item["stuff_def_name"] == "BlocksGranite"
                            for item in buildings if item["def_name"] == "Wall"))
        self.assertEqual(next(item for item in buildings if item["def_name"] == "Door")["rel_x"], 0)

    def test_architecture_execution_refuses_stale_material(self):
        context = {"building_catalog": [], "finished_research": [],
                   "item_counts": {"WoodLog": 2000}, "material_options": {"WoodLog": "wood"},
                   "material": "WoodLog", "powered": False, "variant_seed": 2}
        result = director.execute_action(None, {"map": {"id": 1}, "game": {"tick": 1}},
                                         {"anchor": {"x": 5, "z": 5}, "issued": {}}, "plan_architecture",
                                         {"architecture_program": "residence", "architecture_variant": "house_compact_1",
                                          "architecture_material": "BlocksGranite", "architecture_entry": "south",
                                          "architecture_context": context})
        self.assertFalse(result["applied"])

    def test_strategy_catalog_covers_core_and_every_official_expansion(self):
        expansions = {row.get("expansion") or "core" for row in colony_strategy.DIRECTIONS.values()}
        self.assertEqual(expansions, {"core", "royalty", "ideology", "biotech", "anomaly", "odyssey"})
        self.assertGreaterEqual(len(colony_strategy.DIRECTIONS), 30)
        self.assertEqual(set(colony_strategy.DOMAIN_LABELS), {row["domain"] for row in colony_strategy.DIRECTIONS.values()})

    def test_direction_audit_filters_inactive_content(self):
        core = colony_strategy.audit_directions({"active_mods": [{"package_id": "ludeon.rimworld"}]})
        self.assertIn("research_starflight", core["available"])
        self.assertIn("gravship_nomads", core["unavailable"])
        odyssey = colony_strategy.audit_directions({"active_mods": [
            {"package_id": "ludeon.rimworld"}, {"package_id": "ludeon.rimworld.odyssey"},
        ]})
        self.assertIn("gravship_nomads", odyssey["available"])

    def test_doctrine_is_a_conditional_cascade(self):
        choices = [
            "choose_colony_doctrine", "prosperity", "industrial_manufacturing",
            "compact", "manufacturing", "industrial", "industrial", "ranged_firepower", "pragmatic",
            "ship_escape", "peaceful_trade", "expansionist", "peaceful_trade", "balanced", "components",
        ]
        agent = self.FakeAgent(choices)
        context = {
            "material_options": {"WoodLog": "wood"}, "profession_choices": {},
            "active_mods": [{"package_id": "ludeon.rimworld"}], "research_tree": [],
            "building_catalog": [], "profession_directions": {},
        }
        context["direction_audit"] = colony_strategy.audit_directions(context)
        snapshot = {"colonists": [], "game": {}, "map": {"resources": {}}, "development": {
            "building_counts": {}, "zones": [], "doctrine_context": context,
        }}
        result = director.choose_action(agent, snapshot, ["choose_colony_doctrine", "hold_survival"])
        doctrine = result["doctrine_selection"]
        self.assertEqual(doctrine["primary_direction"], "industrial_manufacturing")
        self.assertEqual(doctrine["economy_family"], "manufacturing")
        self.assertEqual(doctrine["economy_product"], "components")
        self.assertNotIn("doctrine_mining_product", result["raw"]["answers"])
        direction_question = agent.calls[2]["doctrine_primary_direction"]["criteria"]
        self.assertTrue(direction_question)
        self.assertTrue(all(colony_strategy.DIRECTIONS[key]["domain"] == "prosperity" for key in direction_question))

    def test_doctrine_research_uses_only_live_startable_projects(self):
        doctrine = {"primary_direction": "industrial_manufacturing", "technology": "industrial", "economy_product": "components"}
        tree = [
            {"name": "Fabrication", "label": "Fabrication", "description": "Make advanced components", "can_start_now": True, "is_finished": False, "research_points": 4000},
            {"name": "BlockedMachining", "label": "Machining", "can_start_now": False, "is_finished": False, "research_points": 1000},
            {"name": "FinishedComponents", "label": "Components", "can_start_now": True, "is_finished": True, "research_points": 1000},
        ]
        options = colony_strategy.doctrine_research_candidates(doctrine, tree)
        self.assertIn("Fabrication", options)
        self.assertNotIn("BlockedMachining", options)
        self.assertNotIn("FinishedComponents", options)

    def test_architecture_includes_strategic_building_programs(self):
        options = director.architect.program_options({
            "building_counts": {"SimpleResearchBench": 1}, "rooms": [], "colonists": [], "animals": [],
            "buildings": [], "storage": {}, "professions": {"directions": {}},
            "doctrine": {"primary_direction": "industrial_manufacturing", "building_programs": ["factory"]},
            "finished_research": [], "building_catalog": [],
        })
        self.assertIn("factory", options)

    def test_unavailable_rimapi_is_waiting_not_a_laya_cycle_error(self):
        state, detail, prefix = director.classify_runtime_problem(
            "/api/v1/game/state: <urlopen error [WinError 10061] connection refused>"
        )
        self.assertEqual(state, "waiting")
        self.assertIn("RimWorld", detail)
        self.assertEqual(prefix, "Waiting for RimWorld/RIMAPI")

    def test_real_cycle_failure_remains_an_error(self):
        state, detail, prefix = director.classify_runtime_problem("invalid combat target")
        self.assertEqual(state, "error")
        self.assertEqual(detail, "invalid combat target")
        self.assertEqual(prefix, "Decision cycle problem")

    def test_post_combat_care_selects_patient_and_doctor_then_avoids_duplicate_job(self):
        class Client:
            def __init__(self):
                self.posts = []

            def post(self, endpoint, body=None, query=None):
                self.posts.append((endpoint, body, query))
                return {"success": True}

        patient = {"id": 1, "name": "Patient", "health": 0.51, "bleeding_rate": 0.2,
                   "tendable_now": True, "is_down": False, "is_downed": True}
        doctor = {"id": 2, "name": "Doctor", "health": 1.0, "medicine_skill": 9,
                  "moving": 1.0, "manipulation": 1.0, "tendable_now": False}
        snapshot = {"combat": {"hostiles": [], "colonists": [patient, doctor]},
                    "game": {"is_paused": False}, "map": {"resources": {"medicine": 1}}}
        self.assertIn("tend_1_2", director.post_combat_care_options(snapshot))
        client = Client()
        with tempfile.TemporaryDirectory() as folder:
            record = director.run_post_combat_care_cycle(
                client, self.FakeAgent(["tend_1_2"]), snapshot, pathlib.Path(folder) / "care.jsonl"
            )
        self.assertEqual(record["decision"]["choice"], "tend_1_2")
        self.assertEqual(client.posts[-1][1]["patient_pawn_id"], 1)
        self.assertEqual(client.posts[-1][1]["doctor_pawn_id"], 2)
        doctor.update(current_job="TendPatient", current_job_target_id=1)
        self.assertEqual(director.post_combat_care_options(snapshot), {})
        self.assertTrue(director.treatment_job_in_progress(snapshot))
        patient["tendable_now"] = False
        self.assertFalse(director.treatment_job_in_progress(snapshot))

    def test_post_combat_care_excludes_doctor_with_disabled_medicine(self):
        snapshot = {"combat": {"colonists": [
            {"id": 1, "name": "Patient", "tendable_now": True, "is_downed": True},
            {"id": 2, "name": "Belken", "medicine_skill": 5, "moving": 1, "manipulation": 1},
            {"id": 3, "name": "Four Eyes", "medicine_skill": 0, "moving": 1, "manipulation": 1},
        ]}, "colonists": [
            {"id": 2, "skills": {"Medicine": {"disabled": False}}},
            {"id": 3, "skills": {"Medicine": {"disabled": True}}},
        ]}
        options = director.post_combat_care_options(snapshot)
        self.assertIn("tend_1_2", options)
        self.assertNotIn("tend_1_3", options)

    def test_chosen_treatment_keeps_mobile_bleeding_patient_in_doctor_reach(self):
        class Client:
            def __init__(self):
                self.posts = []

            def post(self, endpoint, body=None, query=None):
                self.posts.append((endpoint, body))
                return {"success": True}

        snapshot = {"combat": {"hostiles": [], "colonists": [
            {"id": 1, "name": "Patient", "health": 0.5, "bleeding_rate": 1.4,
             "tendable_now": True, "is_downed": False, "current_job": "HaulToCell"},
            {"id": 2, "name": "Doctor", "medicine_skill": 5,
             "moving": 1, "manipulation": 1, "current_job": "Sow"},
        ]}, "game": {"is_paused": False}, "map": {"resources": {"medicine": 2}}}
        client = Client()
        with tempfile.TemporaryDirectory() as folder:
            record = director.run_post_combat_care_cycle(
                client, self.FakeAgent(["tend_1_2"]), snapshot,
                pathlib.Path(folder) / "care.jsonl",
            )
        self.assertEqual([endpoint for endpoint, _ in client.posts[-2:]],
                         ["/api/v1/pawn/job", "/api/v1/pawn/medical/tend"])
        self.assertEqual(client.posts[-2][1]["job_def"], "Wait_MaintainPosture")
        self.assertTrue(record["result"]["patient_hold"]["success"])

    def test_completed_short_advance_requests_a_new_shooting_decision(self):
        record = {"action": {"commands": [{"endpoint": "/api/v1/combat/tactic", "body": {
            "tactic": "focus_fire", "fighter_ids": [1], "target_pawn_id": 99,
        }}]}, "result": {"responses": [{"positioned_pawn_ids": [1]}]}}
        snapshot = {"combat": {"colonists": [{"id": 1, "current_job": "Goto"}]}}
        self.assertFalse(director.combat_positioning_finished(snapshot, record, 1.0))
        self.assertFalse(director.combat_positioning_finished(snapshot, record, 3.0))
        snapshot["combat"]["colonists"][0]["current_job"] = "Wait"
        self.assertTrue(director.combat_positioning_finished(snapshot, record, 3.0))

    def test_post_combat_care_can_be_deferred_even_if_only_one_treatment_exists(self):
        class Client:
            def __init__(self):
                self.posts = []

            def post(self, endpoint, body=None, query=None):
                self.posts.append((endpoint, body, query))

        snapshot = {"combat": {"hostiles": [], "colonists": [
            {"id": 1, "name": "Patient", "health": 0.6, "bleeding_rate": 0.1,
             "tendable_now": True, "is_downed": True},
            {"id": 2, "name": "Doctor", "health": 1, "moving": 1, "manipulation": 1,
             "medicine_skill": 8},
        ]}, "game": {"is_paused": False}, "map": {"resources": {"medicine": 0}}}
        client = Client()
        agent = self.FakeAgent(["defer_care"])
        with tempfile.TemporaryDirectory() as folder:
            record = director.run_post_combat_care_cycle(
                client, agent, snapshot, pathlib.Path(folder) / "care.jsonl"
            )
        self.assertTrue(record["result"]["deferred"])
        self.assertTrue(record["result"]["revisit"])
        self.assertFalse(any(endpoint == "/api/v1/pawn/medical/tend" for endpoint, _, _ in client.posts))
        self.assertTrue(any(endpoint == "/api/v1/ui/announce" for endpoint, _, _ in client.posts))
        self.assertIn("tend_1_2", agent.calls[0]["post_combat_care"]["criteria"])
        self.assertIn("resume_colony_decisions", agent.calls[0]["post_combat_care"]["criteria"])

    def test_returning_to_colony_decisions_does_not_force_another_care_prompt(self):
        class Client:
            def post(self, endpoint, body=None, query=None):
                if endpoint != "/api/v1/ui/announce":
                    raise AssertionError("No treatment or pause command is needed")
                return {"success": True}

        snapshot = {"combat": {"hostiles": [], "colonists": [
            {"id": 1, "name": "Patient", "health": 0.6, "bleeding_rate": 0.1,
             "tendable_now": True, "is_downed": True},
            {"id": 2, "name": "Doctor", "health": 1, "moving": 1, "manipulation": 1,
             "medicine_skill": 8},
        ]}, "game": {"is_paused": False}, "map": {"resources": {"medicine": 0}}}
        with tempfile.TemporaryDirectory() as folder:
            record = director.run_post_combat_care_cycle(
                Client(), self.FakeAgent(["resume_colony_decisions"]),
                snapshot, pathlib.Path(folder) / "care.jsonl",
            )
        self.assertTrue(record["result"]["deferred"])
        self.assertFalse(record["result"]["revisit"])


if __name__ == "__main__":
    unittest.main()
