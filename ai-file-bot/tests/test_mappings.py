from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.mappings import RoomMappingStore


class RoomMappingStoreTest(unittest.TestCase):
    def test_bind_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RoomMappingStore(str(Path(directory) / "mappings.json"))

            first = store.bind("team-1", "channel-1", "10", "项目资料室")
            second = store.bind("team-1", "channel-1", "11", "另一个房间")

            self.assertEqual(first, second)
            self.assertEqual(second["room_id"], "10")

    def test_mapping_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "mappings.json")
            RoomMappingStore(path).bind("team-1", "channel-1", "10", "项目资料室")

            mapping = RoomMappingStore(path).get("team-1", "channel-1")

            self.assertIsNotNone(mapping)
            self.assertEqual(mapping["room_title"], "项目资料室")

    def test_last_updated_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "mappings.json")
            store = RoomMappingStore(path)
            store.bind("team-1", "channel-1", "10", "项目资料室")

            store.set_last_updated(
                "team-1",
                "channel-1",
                "2026-08-19T16:10:00+08:00",
            )

            mapping = RoomMappingStore(path).get("team-1", "channel-1")
            self.assertEqual(
                mapping["last_notified_updated"],
                "2026-08-19T16:10:00+08:00",
            )


if __name__ == "__main__":
    unittest.main()
