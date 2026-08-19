from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RoomMappingStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    @staticmethod
    def key(team_id: str, channel_id: str) -> str:
        return f"{team_id}:{channel_id}"

    def get(self, team_id: str, channel_id: str) -> dict[str, Any] | None:
        return self._load().get(self.key(team_id, channel_id))

    def bind(
        self,
        team_id: str,
        channel_id: str,
        room_id: str,
        room_title: str,
    ) -> dict[str, Any]:
        mappings = self._load()
        key = self.key(team_id, channel_id)
        existing = mappings.get(key)
        if existing:
            return existing

        mapping = {
            "team_id": team_id,
            "channel_id": channel_id,
            "room_id": str(room_id),
            "room_title": room_title,
        }
        mappings[key] = mapping
        self._save(mappings)
        return mapping

    def all(self) -> list[dict[str, Any]]:
        return list(self._load().values())

    def set_last_updated(
        self,
        team_id: str,
        channel_id: str,
        updated: str,
    ) -> None:
        mappings = self._load()
        mapping = mappings.get(self.key(team_id, channel_id))
        if not mapping:
            return
        mapping["last_notified_updated"] = updated
        self._save(mappings)

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, mappings: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(mappings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
