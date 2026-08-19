from __future__ import annotations

import re
from dataclasses import dataclass


DEFAULT_FILE_ANALYSIS_INSTRUCTION = "请分析并总结附件内容"
DEFAULT_MEETING_TITLE = "临时会议"


@dataclass(frozen=True)
class ParsedCommand:
    domain: str
    action: str
    instruction: str
    duration_minutes: int | None = None


class CommandError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_command(
    message: str,
    bot_username: str,
    *,
    allow_legacy_filebot: bool = False,
) -> ParsedCommand:
    content = re.sub(
        rf"(^|\s)@{re.escape(bot_username)}(?=\s|$)",
        " ",
        message,
        count=1,
        flags=re.IGNORECASE,
    ).strip()

    parts = content.split(maxsplit=2)
    if len(parts) >= 2 and parts[0].lower() == "file" and parts[1].lower() == "analyze":
        instruction = parts[2].strip() if len(parts) == 3 else DEFAULT_FILE_ANALYSIS_INSTRUCTION
        return ParsedCommand("file", "analyze", instruction)

    meeting_match = re.fullmatch(
        r"meeting\s+create(?:\s+(.*?))?(?:\s+--duration\s+(\S+))?",
        content,
        flags=re.IGNORECASE,
    )
    if meeting_match:
        title = (meeting_match.group(1) or DEFAULT_MEETING_TITLE).strip()
        duration_value = meeting_match.group(2)
        duration = None
        if duration_value:
            if not duration_value.isdigit() or not 1 <= int(duration_value) <= 480:
                raise CommandError(
                    "BOT-MEETING-DURATION-INVALID",
                    "会议时长必须是 1 到 480 分钟之间的整数。",
                )
            duration = int(duration_value)
        return ParsedCommand("meeting", "create", title, duration)

    if allow_legacy_filebot:
        return ParsedCommand(
            "file",
            "analyze",
            content or DEFAULT_FILE_ANALYSIS_INSTRUCTION,
        )

    raise CommandError(
        "BOT-COMMAND-INVALID",
        "命令格式不正确，请使用 `@assistant file analyze [分析要求]` 或 "
        "`@assistant meeting create [会议标题] [--duration 分钟]`。",
    )
