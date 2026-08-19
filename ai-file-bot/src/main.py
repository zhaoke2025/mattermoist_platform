from __future__ import annotations

import logging
import os
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import requests
from openai import OpenAI

from .commands import CommandError, parse_command
from .extractors import ExtractionError, extract_text


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("ai-file-bot")


MM_URL = os.environ["MATTERMOST_URL"].rstrip("/")
MM_TOKEN = os.environ["MATTERMOST_TOKEN"]
BOT_USERNAME = os.getenv("BOT_USERNAME", "filebot").lower()
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "3"))
MAX_FILES_PER_REQUEST = int(os.getenv("MAX_FILES_PER_REQUEST", "3"))
JITSI_BASE_URL = os.getenv("JITSI_BASE_URL", "https://meet.rongsunai.com").rstrip("/")

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "2048"))


class MattermostClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {MM_TOKEN}"})
        self.bot_user_id = ""
        self.channel_last_seen: dict[str, int] = {}
        self.start_time_ms = int(time.time() * 1000)

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.session.request(method, f"{MM_URL}{path}", timeout=30, **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return None

    def init_identity(self) -> None:
        me = self.request("GET", "/api/v4/users/me")
        self.bot_user_id = me["id"]
        LOGGER.info("connected as @%s (%s)", me["username"], self.bot_user_id)

    def get_my_channels(self) -> list[dict[str, Any]]:
        return self.request("GET", "/api/v4/users/me/channels")

    def get_new_mentions(self) -> list[dict[str, Any]]:
        mentions: list[dict[str, Any]] = []
        for channel in self.get_my_channels():
            channel_id = channel["id"]
            since = self.channel_last_seen.get(channel_id, self.start_time_ms)
            posts = self.request(
                "GET",
                f"/api/v4/channels/{channel_id}/posts",
                params={"since": str(since), "per_page": "60"},
            )

            max_seen = since
            for post_id in posts.get("order", []):
                post = posts.get("posts", {}).get(post_id) or {}
                create_at = post.get("create_at", 0)
                max_seen = max(max_seen, create_at)
                if (
                    create_at > since
                    and post.get("user_id") != self.bot_user_id
                    and _mentions_bot(post.get("message", ""))
                ):
                    mentions.append(post)

            self.channel_last_seen[channel_id] = max_seen

        mentions.sort(key=lambda post: post.get("create_at", 0))
        return mentions

    def get_thread(self, post_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/v4/posts/{post_id}/thread")

    def get_channel_posts(self, channel_id: str, before_post_id: str) -> dict[str, Any]:
        params = {"before": before_post_id, "per_page": "30"}
        return self.request("GET", f"/api/v4/channels/{channel_id}/posts", params=params)

    def get_file_info(self, file_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/v4/files/{file_id}/info")

    def get_user(self, user_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/v4/users/{user_id}")

    def download_file(self, file_id: str, dest: Path) -> None:
        response = self.session.get(f"{MM_URL}/api/v4/files/{file_id}", timeout=120)
        response.raise_for_status()
        dest.write_bytes(response.content)

    def create_post(self, channel_id: str, message: str, root_id: str) -> None:
        body = {
            "channel_id": channel_id,
            "message": message,
            "root_id": root_id,
        }
        self.request("POST", "/api/v4/posts", json=body)


def _mentions_bot(message: str) -> bool:
    return re.search(rf"(^|\s)@{re.escape(BOT_USERNAME)}(\s|$)", message, re.IGNORECASE) is not None


def collect_file_ids(mm: MattermostClient, post: dict[str, Any]) -> list[str]:
    root_id = post.get("root_id") or post["id"]
    thread = mm.get_thread(root_id)
    ordered_ids = thread.get("order", [])
    posts = thread.get("posts", {})
    file_ids: list[str] = []

    for post_id in ordered_ids:
        candidate = posts.get(post_id) or {}
        file_ids.extend(candidate.get("file_ids") or [])

    if not file_ids:
        channel_posts = mm.get_channel_posts(post["channel_id"], post["id"])
        for post_id in channel_posts.get("order", []):
            candidate = channel_posts.get("posts", {}).get(post_id) or {}
            file_ids.extend(candidate.get("file_ids") or [])

    return list(dict.fromkeys(file_ids))[:MAX_FILES_PER_REQUEST]


def analyze_files(mm: MattermostClient, file_ids: list[str], instruction: str) -> str:
    if not file_ids:
        return (
            "未找到可分析的附件。请在附件消息下方回复："
            "`@filebot 分析并总结这个附件`。"
        )

    extracted_parts: list[str] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for file_id in file_ids:
            info = mm.get_file_info(file_id)
            name = info.get("name") or f"{file_id}.bin"
            dest = tmp / file_id
            try:
                mm.download_file(file_id, dest)
                text = extract_text(dest, name)
                extracted_parts.append(f"File name: {name}\nFile ID: {file_id}\nContent:\n{text}")
            except ExtractionError as exc:
                extracted_parts.append(f"File name: {name}\nExtraction failed: {exc}")
            except Exception as exc:
                LOGGER.exception("failed to process file %s", file_id)
                extracted_parts.append(f"File name: {name}\nProcessing failed: {exc}")

    prompt = build_prompt(instruction, extracted_parts)
    return ask_llm(prompt)


def build_prompt(instruction: str, extracted_parts: list[str]) -> str:
    joined = "\n\n====================\n\n".join(extracted_parts)
    return f"""You are a document analysis assistant inside an enterprise chat system.
Analyze the extracted attachment content according to the user request.

User request:
{instruction}

Requirements:
1. Answer in Chinese by default.
2. Start with a short conclusion, then list key points.
3. If extraction failed or information is insufficient, say so clearly.
4. Do not invent facts that are not present in the attachment.

Extracted attachment content:
{joined}
"""


def ask_llm(prompt: str) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a careful enterprise document analysis assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=OPENAI_MAX_TOKENS,
        temperature=0.2,
    )
    return response.choices[0].message.content or "No valid analysis result was generated."


def create_meeting(post: dict[str, Any], creator_username: str, title: str, duration: int | None) -> str:
    room_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{MM_URL}/posts/{post['id']}")
    meeting_url = f"{JITSI_BASE_URL}/{room_id}"
    duration_text = f"{duration} 分钟" if duration else "未设置"
    return (
        "### 会议已创建\n"
        f"- 会议标题：{title}\n"
        f"- 会议入口：[点击加入会议]({meeting_url})\n"
        f"- 创建人：@{creator_username}\n"
        f"- 预计时长：{duration_text}"
    )


def handle_post(mm: MattermostClient, post: dict[str, Any]) -> None:
    root_id = post.get("root_id") or post["id"]
    try:
        command = parse_command(
            post.get("message", ""),
            BOT_USERNAME,
            allow_legacy_filebot=BOT_USERNAME == "filebot",
        )
    except CommandError as exc:
        mm.create_post(
            post["channel_id"],
            f"### 执行失败\n- 错误码：{exc.code}\n- 原因：{exc}",
            root_id,
        )
        return

    try:
        if command.domain == "meeting" and command.action == "create":
            creator = mm.get_user(post["user_id"])
            answer = create_meeting(
                post,
                creator.get("username") or post["user_id"],
                command.instruction,
                command.duration_minutes,
            )
        else:
            file_ids = collect_file_ids(mm, post)
            LOGGER.info("post %s matched, files=%s", post["id"], file_ids)
            answer = analyze_files(mm, file_ids, command.instruction)
    except Exception as exc:
        LOGGER.exception("failed to handle post %s", post.get("id"))
        answer = f"### 执行失败\n- 错误码：BOT-UPSTREAM-ERROR\n- 原因：{exc}"
    mm.create_post(post["channel_id"], answer, root_id)


def main() -> None:
    mm = MattermostClient()
    mm.init_identity()
    LOGGER.info("polling mentions for @%s", BOT_USERNAME)
    while True:
        try:
            for post in mm.get_new_mentions():
                handle_post(mm, post)
        except Exception:
            LOGGER.exception("poll loop failed")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
