"""Deterministic raid rehearsals against the decision and order layers."""

import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import colony_combat
import rimworld_laya as bridge


def fighter(pawn_id, *, ranged=True, weapon="Gun_Revolver", armor=0.0, distance=12,
            health=1.0, moving=1.0, range_cells=25):
    return {
        "id": pawn_id, "name": f"Colonist {pawn_id}", "health": health,
        "is_dead": False, "is_downed": False, "is_drafted": False,
        "has_ranged_weapon": ranged, "weapon_def": weapon, "weapon_label": weapon,
        "weapon_range": range_cells, "armor_sharp": armor, "moving": moving,
        "manipulation": 1.0, "sight": 1.0, "shooting_skill": 8,
        "melee_skill": 8, "distance_to_nearest_opponent": distance,
        "position": {"x": 10 + pawn_id, "z": 10}, "current_job": "Wait",
    }


def raid(fighters, hostiles, defenses=()):
    return {
        "game": {"is_paused": True},
        "map": {"id": 1, "enemies": len(hostiles)},
        "colonists": [{"id": pawn["id"], "rest": 0.8, "hunger": 0.8} for pawn in fighters],
        "combat": {
            "available": True, "colonists": fighters, "hostiles": hostiles,
            "available_weapons": [], "defenses": list(defenses),
        },
    }


class CombatScenarioTests(unittest.TestCase):
    def test_unarmed_colonists_can_choose_trap_free_retreat_instead_of_idle_melee(self):
        snapshot = raid(
            [fighter(1, ranged=False, weapon=None, distance=8)],
            [{"id": 99, "kind_def": "Raider", "current_job": "AttackMelee", "health": 1.0,
              "position": {"x": 22, "z": 10}}],
        )
        options = bridge.make_questions(snapshot)["threat_action"]["criteria"]
        self.assertIn("civilian_retreat", options)
        self.assertNotIn("engage_melee", options)
        action = bridge.plan_action(snapshot, {"choice": "civilian_retreat"})
        tactic = next(row for row in action["commands"] if row["endpoint"] == "/api/v1/combat/tactic")
        self.assertEqual(tactic["body"]["fighter_ids"], [1])
        self.assertEqual(tactic["body"]["tactic"], "civilian_retreat")

    def test_staging_raid_offers_weapon_equipping_as_a_real_choice(self):
        snapshot = raid(
            [fighter(1, ranged=False, weapon=None, distance=80)],
            [{"id": 99, "kind_def": "Raider", "current_job": "Wait_Wander", "position": {"x": 100, "z": 100}}],
        )
        snapshot["combat"]["available_weapons"] = [{"id": 71, "def_name": "Gun_BoltActionRifle", "is_ranged": True, "is_forbidden": True}]
        options = bridge.make_questions(snapshot)["threat_action"]["criteria"]
        self.assertIn("equip_ranged_weapon", options)
        action = bridge.plan_action(snapshot, {"choice": "equip_ranged_weapon"})
        self.assertEqual([row["endpoint"] for row in action["commands"][:2]],
                         ["/api/v1/things/set-forbidden", "/api/v1/pawn/job"])

    def test_far_assault_does_not_draft_shooters_before_weapon_range(self):
        shooters = [fighter(1, distance=120, range_cells=37), fighter(2, distance=122, range_cells=26)]
        snapshot = raid(shooters, [{"id": 99, "kind_def": "Raider", "current_job": "Goto",
                                    "distance_to_nearest_opponent": 120, "weapon_range": 0,
                                    "position": {"x": 120, "z": 120}}])
        criteria = bridge.make_questions(snapshot)["threat_action"]["criteria"]
        self.assertEqual(set(criteria), {"prepare_undrafted", "hold_and_observe"})
        shooters[0]["distance_to_nearest_opponent"] = 22
        snapshot["combat"]["hostiles"][0]["distance_to_nearest_opponent"] = 22
        self.assertIn("focus_fire", bridge.make_questions(snapshot)["threat_action"]["criteria"])

    def test_focus_fire_uses_only_shooters_whose_weapons_can_reach(self):
        shooters = [fighter(1, distance=25, range_cells=37), fighter(2, distance=25, range_cells=20)]
        snapshot = raid(shooters, [{"id": 99, "kind_def": "Raider", "health": 1.0,
                                    "current_job": "AttackMelee", "position": {"x": 36, "z": 10}}])
        action = bridge.plan_action(snapshot, {"choice": "focus_fire"})
        tactic = next(row for row in action["commands"] if row["endpoint"] == "/api/v1/combat/tactic")
        self.assertEqual(tactic["body"]["fighter_ids"], [1])

    def test_squirrel_raid_does_not_send_unarmed_civilian_into_melee(self):
        snapshot = raid(
            [fighter(1), fighter(2, ranged=False, weapon=None)],
            [{"id": 99, "kind_def": "Squirrel", "health": 1.0, "position": {"x": 22, "z": 10}}],
        )
        options = colony_combat.available_tactics(snapshot)
        self.assertIn("focus_fire", options)
        self.assertNotIn("melee_block", options)
        self.assertNotIn("rush_ranged", options)
        action = bridge.plan_action(snapshot, {"choice": "focus_fire"})
        bodies = [row["body"] for row in action["commands"] if row["endpoint"] == "/api/v1/combat/tactic"]
        self.assertEqual(bodies[0]["fighter_ids"], [1])
        self.assertEqual(bodies[0]["target_pawn_id"], 99)
        self.assertEqual(action["commands"][-1]["query"], {"speed": 1})

    def test_distant_preparing_raid_cannot_provoke_with_short_range_or_unarmed_pawns(self):
        snapshot = raid(
            [fighter(1, distance=80, range_cells=15), fighter(2, ranged=False, weapon=None, distance=80)],
            [{"id": 99, "kind_def": "Raider", "current_job": "Wait_Combat", "position": {"x": 100, "z": 100}}],
        )
        options = bridge.make_questions(snapshot)["threat_action"]["criteria"]
        self.assertEqual(set(options), {"prepare_undrafted", "hold_and_observe"})

    def test_enemy_goto_is_an_assault_not_preparation(self):
        snapshot = raid(
            [fighter(1, distance=80, range_cells=37), fighter(2, distance=82, range_cells=26)],
            [{"id": 99, "kind_def": "Raider", "current_job": "Goto", "position": {"x": 100, "z": 100}}],
        )
        self.assertNotIn("preemptive_strike", bridge.make_questions(snapshot)["threat_action"]["criteria"])

    def test_stage_lord_counts_as_preparation_before_first_pawn_job(self):
        shooters = [fighter(1, distance=80, range_cells=37), fighter(2, distance=82, range_cells=26)]
        hostile = {"id": 99, "kind_def": "Raider", "current_job": None,
                   "lord_toil_name": "LordToil_Stage", "position": {"x": 100, "z": 100}}
        snapshot = raid(shooters, [hostile])
        self.assertTrue(colony_combat.hostile_is_preparing(hostile))
        self.assertIn("preemptive_strike", bridge.make_questions(snapshot)["threat_action"]["criteria"])
        hostile["current_job"] = "Goto"
        self.assertFalse(colony_combat.hostile_is_preparing(hostile))

    def test_outnumbered_or_insect_raid_does_not_offer_preemptive_strike(self):
        shooters = [fighter(1, distance=85, range_cells=37), fighter(2, distance=86, range_cells=26)]
        hostiles = [
            {"id": 90 + index, "kind_def": "Megaspider", "health": 1.0,
             "current_job": "Wait_Wander", "position": {"x": 100 + index, "z": 100}}
            for index in range(3)
        ]
        snapshot = raid(shooters, hostiles)
        options = bridge.make_questions(snapshot)["threat_action"]["criteria"]
        self.assertEqual(set(options), {"prepare_undrafted", "hold_and_observe"})

    def test_ranged_raider_does_not_offer_unsupported_preemptive_charge(self):
        snapshot = raid(
            [fighter(1, distance=80, range_cells=37), fighter(2, distance=82, range_cells=26)],
            [{"id": 99, "kind_def": "Raider", "current_job": "Wait_Wander",
              "has_ranged_weapon": True, "weapon_def": "Gun_Autopistol", "position": {"x": 100, "z": 100}}],
        )
        self.assertNotIn("preemptive_strike", bridge.make_questions(snapshot)["threat_action"]["criteria"])

    def test_staging_does_not_undraft_active_defenders_near_the_enemy(self):
        shooters = [fighter(1, distance=48, range_cells=37), fighter(2, distance=50, range_cells=26)]
        shooters[0].update(is_drafted=True, current_job="AttackStatic", current_job_target_id=99)
        snapshot = raid(shooters, [{"id": 99, "kind_def": "Raider", "health": 1.0,
                                    "current_job": "Wait_Wander", "position": {"x": 100, "z": 100}}])
        self.assertNotIn("prepare_undrafted", bridge.make_questions(snapshot)["threat_action"]["criteria"])

    def test_wounded_or_reserved_fighter_is_actually_undrafted(self):
        shooters = [fighter(1), fighter(2, health=0.57)]
        for pawn in shooters:
            pawn["is_drafted"] = True
        snapshot = raid(shooters, [{"id": 99, "kind_def": "Raider", "health": 1.0,
                                    "current_job": "AttackMelee", "position": {"x": 22, "z": 10}}])
        action = bridge.plan_action(snapshot, {"choice": "focus_fire", "selected_fighter_ids": [1]})
        self.assertEqual(action["commands"][0]["body"], {"pawn_id": 2, "is_drafted": False})
        self.assertEqual(action["commands"][1]["body"]["fighter_ids"], [1])

    def test_kidnapper_is_priority_target_over_more_valuable_raider(self):
        snapshot = raid(
            [fighter(1)],
            [{"id": 98, "kind_def": "Raider", "combat_power": 100, "health": 1.0, "position": {"x": 15, "z": 10}},
             {"id": 99, "kind_def": "Raider", "combat_power": 20, "health": 1.0, "carrying_pawn_id": 3,
              "current_job": "Kidnap", "position": {"x": 25, "z": 10}}],
        )
        self.assertEqual(colony_combat.choose_default_target(snapshot, "focus_fire"), 99)

    def test_infestation_choke_requires_real_door_armed_armored_melee(self):
        insect = {"id": 99, "kind_def": "Megaspider", "health": 1.0, "position": {"x": 22, "z": 10}}
        unarmored = raid([fighter(1, ranged=False, weapon="MeleeWeapon_Gladius")], [insect], [{"kind": "door"}])
        self.assertNotIn("infestation_choke", colony_combat.available_tactics(unarmored))
        armored = raid([fighter(1, ranged=False, weapon="MeleeWeapon_Gladius", armor=0.55)], [insect], [{"kind": "door"}])
        self.assertIn("infestation_choke", colony_combat.available_tactics(armored))

    def test_combat_prompt_starts_with_live_battle_instead_of_farm_data(self):
        snapshot = raid([fighter(1)], [{"id": 99, "kind_def": "Raider", "health": 1.0, "current_job": "AttackStatic"}], [{"kind": "barricade"}])
        state = bridge.decision_state(snapshot)
        self.assertIn("fighters", state)
        self.assertIn("hostiles", state)
        self.assertIn("barricade", state["defenses"])
        self.assertNotIn("farm", state)
        self.assertIn("range=25", state["fighters"][0])


if __name__ == "__main__":
    unittest.main()
