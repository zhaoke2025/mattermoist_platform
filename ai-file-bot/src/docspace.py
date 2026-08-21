from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests


class DocSpaceClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            }
        )

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            timeout=30,
            **kwargs,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("response")

    def create_room(self, title: str, description: str) -> dict[str, Any]:
        return self.request(
            "POST",
            "/api/2.0/files/rooms",
            json={"title": title, "description": description, "roomType": 2},
        )

    def get_room(self, room_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/2.0/files/rooms/{room_id}")

    def find_user(self, email: str) -> dict[str, Any] | None:
        response = self.request(
            "GET",
            f"/api/2.0/people?filterValue={quote(email)}",
        )
        if isinstance(response, dict):
            users = response.get("items") or []
        else:
            users = response or []
        normalized = email.strip().lower()
        return next(
            (
                user
                for user in users
                if user.get("email", "").strip().lower() == normalized
            ),
            None,
        )

    def invite_users(self, room_id: str, emails: list[str]) -> None:
        if not emails:
            return
        self.request(
            "PUT",
            f"/api/2.0/files/rooms/{room_id}/share",
            json={
                "invitations": [
                    {"email": email, "access": "Editing"} for email in emails
                ],
                "notify": True,
                "message": "您已被邀请加入 Mattermost 频道对应的 DocSpace 协作房间。",
            },
        )

    def room_url(self, room_id: str) -> str:
        return f"{self.base_url}/rooms/shared/{room_id}"
