import json
import tempfile
import unittest
from pathlib import Path

from laya_gui.services import tail_jsonl


class GuiHistoryTests(unittest.TestCase):
    def test_large_history_is_capped_without_parsing_partial_record(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "decisions.jsonl"
            rows = [{"index": index, "payload": "x" * 4000} for index in range(30)]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            latest = tail_jsonl(path, limit=80, max_bytes=15000)
            self.assertTrue(latest)
            self.assertEqual(latest[-1]["index"], 29)
            self.assertLess(len(latest), 10)
            self.assertEqual(tail_jsonl(path, limit=100, max_bytes=None), rows)


if __name__ == "__main__":
    unittest.main()
