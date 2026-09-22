import importlib.util
import pathlib
import sys
import unittest

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

    def test_combat_tactics_use_existing_defenses_and_detect_kidnapper(self):
        snapshot = {"combat": {
            "colonists": [{"id": 1, "health": 1, "has_ranged_weapon": True, "is_dead": False,
                            "is_downed": False, "distance_to_nearest_opponent": 12}],
            "hostiles": [{"id": 9, "health": 1, "is_dead": False, "is_downed": False,
                           "current_job": "Kidnap", "carrying_pawn_id": 3}],
            "defenses": [{"kind": "trap"}, {"kind": "door"}], "available_weapons": [],
        }}
        options = colony_combat.available_tactics(snapshot)
        self.assertIn("intercept_kidnapper", options)
        self.assertIn("killbox_hold", options)
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
            "hunger": 0.2,
            "downed": True,
            "current_job": "LayDown",
        }))

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
                              "meat_amount": 18, "leather_amount": 8, "market_value": 60}],
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
        agent = self.FakeAgent(["plan_architecture", "residence", "compact", "house_compact_1"])
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
        self.assertEqual(result["architecture_house_style"], "compact")
        self.assertEqual(result["architecture_variant"], "house_compact_1")
        self.assertEqual(len(agent.calls), 4)

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
            "compact", "manufacturing", "industrial", "ranged_firepower", "pragmatic",
            "ship_escape", "peaceful_trade", "WoodLog", "balanced", "components",
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


if __name__ == "__main__":
    unittest.main()
