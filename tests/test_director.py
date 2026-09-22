import importlib.util
import pathlib
import sys
import unittest


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


if __name__ == "__main__":
    unittest.main()
