from __future__ import annotations

import unittest

from src.commands import (
    DEFAULT_FILE_ANALYSIS_INSTRUCTION,
    DEFAULT_MEETING_TITLE,
    CommandError,
    parse_command,
)


class ParseCommandTest(unittest.TestCase):
    def test_unified_file_analyze_with_instruction(self) -> None:
        command = parse_command(
            "@assistant file analyze 请提取合同金额和截止日期",
            "assistant",
        )

        self.assertEqual(command.domain, "file")
        self.assertEqual(command.action, "analyze")
        self.assertEqual(command.instruction, "请提取合同金额和截止日期")

    def test_unified_file_analyze_uses_default_instruction(self) -> None:
        command = parse_command("@assistant file analyze", "assistant")

        self.assertEqual(command.instruction, DEFAULT_FILE_ANALYSIS_INSTRUCTION)

    def test_invalid_unified_command_returns_stable_error(self) -> None:
        with self.assertRaises(CommandError) as raised:
            parse_command("@assistant summarize this file", "assistant")

        self.assertEqual(raised.exception.code, "BOT-COMMAND-INVALID")

    def test_legacy_filebot_instruction_is_preserved(self) -> None:
        command = parse_command(
            "@filebot 请总结这个附件",
            "filebot",
            allow_legacy_filebot=True,
        )

        self.assertEqual(command.domain, "file")
        self.assertEqual(command.action, "analyze")
        self.assertEqual(command.instruction, "请总结这个附件")

    def test_meeting_create_with_title_and_duration(self) -> None:
        command = parse_command(
            "@assistant meeting create 项目周会 --duration 60",
            "assistant",
        )

        self.assertEqual(command.domain, "meeting")
        self.assertEqual(command.action, "create")
        self.assertEqual(command.instruction, "项目周会")
        self.assertEqual(command.duration_minutes, 60)

    def test_meeting_create_uses_default_title(self) -> None:
        command = parse_command("@assistant meeting create", "assistant")

        self.assertEqual(command.instruction, DEFAULT_MEETING_TITLE)
        self.assertIsNone(command.duration_minutes)

    def test_meeting_create_rejects_invalid_duration(self) -> None:
        with self.assertRaises(CommandError) as raised:
            parse_command(
                "@assistant meeting create 项目周会 --duration 500",
                "assistant",
            )

        self.assertEqual(raised.exception.code, "BOT-MEETING-DURATION-INVALID")

    def test_legacy_filebot_can_create_meeting(self) -> None:
        command = parse_command(
            "@filebot meeting create 项目周会",
            "filebot",
            allow_legacy_filebot=True,
        )

        self.assertEqual(command.domain, "meeting")
        self.assertEqual(command.action, "create")

    def test_room_create_with_title(self) -> None:
        command = parse_command(
            "@assistant room create 项目资料室",
            "assistant",
        )

        self.assertEqual(command.domain, "room")
        self.assertEqual(command.action, "create")
        self.assertEqual(command.instruction, "项目资料室")

    def test_room_bind(self) -> None:
        command = parse_command("@assistant room bind 123", "assistant")

        self.assertEqual(command.domain, "room")
        self.assertEqual(command.action, "bind")
        self.assertEqual(command.instruction, "123")

    def test_room_show(self) -> None:
        command = parse_command("@assistant room show", "assistant")

        self.assertEqual(command.domain, "room")
        self.assertEqual(command.action, "show")

    def test_room_sync(self) -> None:
        command = parse_command("@assistant room sync", "assistant")

        self.assertEqual(command.domain, "room")
        self.assertEqual(command.action, "sync")


if __name__ == "__main__":
    unittest.main()
