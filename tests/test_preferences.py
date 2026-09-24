import tempfile
import json
import unittest
from pathlib import Path

import laya_preferences
import colony_combat
import colony_director
from laya_gui.i18n import humanize
from laya_gui.services import append_feedback


class PreferenceTests(unittest.TestCase):
    def test_human_correction_records_visible_context_without_changing_model(self):
        record = {
            "timestamp": "2026-09-23T12:00:00Z", "map_seed": "test",
            "candidates": ["hold_survival", "harvest_local_plants"],
            "decision": {"choice": "hold_survival", "raw": {"visible_state": {"needs": {"food": 0}},
                         "action": {"question": {"criteria": {"hold_survival": "wait", "harvest_local_plants": "food"}}}}},
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "feedback.jsonl"
            append_feedback(path, record, "harvest_local_plants", "Starving")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["human_choice"], "harvest_local_plants")
            self.assertEqual(saved["visible_state"]["needs"]["food"], 0)
            with self.assertRaises(ValueError):
                append_feedback(path, record, "build_ship")

    def test_preferences_round_trip_and_clamp_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preferences.json"
            laya_preferences.save_preferences({
                "language": "en", "technical_logging": True,
                "priorities": {"food": 140, "research": -12},
                "personal_note": "Protect medicine",
                "safety": {"avoid_unprovoked_attacks": True},
            }, path)
            loaded = laya_preferences.load_preferences(path)
            self.assertEqual(loaded["language"], "en")
            self.assertTrue(loaded["technical_logging"])
            self.assertEqual(loaded["priorities"]["food"], 100)
            self.assertEqual(loaded["priorities"]["research"], 0)
            self.assertTrue(loaded["safety"]["avoid_unprovoked_attacks"])

    def test_overlay_preferences_default_to_compact_and_can_be_hidden(self):
        defaults = laya_preferences.load_preferences_from_value({})
        self.assertTrue(defaults["overlay"]["enabled"])
        self.assertTrue(defaults["overlay"]["compact"])
        changed = laya_preferences.load_preferences_from_value({
            "overlay": {"enabled": False, "compact": False, "max_options": 99},
        })
        self.assertFalse(changed["overlay"]["enabled"])
        self.assertFalse(changed["overlay"]["compact"])
        self.assertEqual(changed["overlay"]["max_options"], 8)

    def test_autopilot_preferences_use_product_name(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(
                laya_preferences.preferences_path(Path(folder)).name,
                "autopilot-preferences.json",
            )

    def test_peace_boundary_removes_unprovoked_raid_candidates(self):
        preferences = laya_preferences.load_preferences_from_value({
            "safety": {"avoid_unprovoked_attacks": True},
        })
        choices = laya_preferences.filter_candidates(
            ["raid_to:17", "income_organs", "prepare_trade_caravan"], preferences
        )
        self.assertEqual(choices, ["income_organs", "prepare_trade_caravan"])

    def test_model_context_keeps_note_and_weights(self):
        preferences = laya_preferences.load_preferences_from_value({
            "personal_note": "Build food reserves before luxury rooms",
            "priorities": {"food": 96, "construction": 22},
        })
        context = laya_preferences.model_context(preferences)
        self.assertEqual(context["priority_weights_0_to_100"]["food"], 96)
        self.assertIn("food reserves", context["personal_guidance"])
        self.assertIn("safety", context["instruction"])

    def test_friendly_history_translates_strategy_keys(self):
        examples = ["ranged_firepower", "food_crops", "separate_houses", "research_technology"]
        for language in ("ru", "en"):
            for value in examples:
                friendly = humanize(value, language)
                self.assertNotIn("_", friendly)
                self.assertNotEqual(value, friendly)

    def test_friendly_history_names_architecture_choices(self):
        for language in ("ru", "en"):
            for value in ("residence", "freezer_2", "house_artisan_3", "BlocksGranite", "west"):
                friendly = humanize(value, language)
                self.assertNotIn("_", friendly)
                self.assertNotEqual(value, friendly)

    def test_friendly_history_translates_every_known_action_and_tactic(self):
        names = set(colony_director.ACTION_LABELS) | set(colony_combat.TACTICS)
        names.update({"prepare_undrafted", "preemptive_strike", "keep_current_plan", "equip_emp_weapon"})
        for language in ("ru", "en"):
            for value in names:
                self.assertNotIn("_", humanize(value, language), (language, value))


if __name__ == "__main__":
    unittest.main()
