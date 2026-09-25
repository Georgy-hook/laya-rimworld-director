import unittest

from laya_gui.services import active_map_key


class GuiMapStateTests(unittest.TestCase):
    def test_active_map_key_prefers_current_map(self) -> None:
        response = {"data": [
            {"seed": 12, "tile_id": 100, "id": 0, "is_player_home": True},
            {"seed": 12, "tile_id": 200, "id": 1, "is_current_map": True},
        ]}
        self.assertEqual(active_map_key(response), "12:200:1")

    def test_active_map_key_uses_home_when_current_missing(self) -> None:
        response = {"data": [{"seed": 12, "tile_id": 100, "id": 0, "is_player_home": True}]}
        self.assertEqual(active_map_key(response), "12:100:0")

    def test_active_map_key_does_not_guess_when_no_map_loaded(self) -> None:
        self.assertIsNone(active_map_key({"data": []}))


if __name__ == "__main__":
    unittest.main()
