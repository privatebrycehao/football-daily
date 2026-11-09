import unittest
from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

from lib import espn
from lib.display import format_match_result, format_standings
from lib.webhook import (
    _payload_size,
    create_discord_messages,
    create_lark_messages,
    detect_webhook_type,
    send_webhook,
)


class WebhookTests(unittest.TestCase):
    def test_detects_supported_hostnames_without_substring_false_positives(self):
        self.assertEqual(
            detect_webhook_type("https://open.larkoffice.com/open-apis/bot/v2/hook/fake-token"),
            "lark",
        )
        self.assertEqual(
            detect_webhook_type("https://discord.com/api/webhooks/fake-id/fake-token"),
            "discord",
        )
        for url in (
            "https://open.larkoffice.com.evil.example/hook",
            "https://example.test/open.larkoffice.com/hook",
            "https://discord.com.evil.example/webhook",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                detect_webhook_type(url)

    def test_discord_long_content_is_split_within_embed_limit(self):
        content = ("一行内容\n" * 1200).rstrip()
        payloads = create_discord_messages("日报", content)
        self.assertGreater(len(payloads), 1)
        chunks = [payload["embeds"][0]["description"] for payload in payloads]
        self.assertTrue(all(len(chunk) <= 4096 for chunk in chunks))
        self.assertEqual("\n".join(chunks), content)

    def test_lark_long_content_is_split_by_utf8_body_size(self):
        content = "中文内容\n" * 3000
        limit = 1800
        payloads = create_lark_messages("日报", content, limit=limit)
        self.assertGreater(len(payloads), 1)
        self.assertTrue(all(_payload_size(payload) <= limit for payload in payloads))
        chunks = [
            payload["card"]["elements"][0]["text"]["content"].split("\n\n", 1)[1]
            for payload in payloads
        ]
        self.assertEqual("".join(chunks), content)

    @patch("lib.webhook.requests.post")
    def test_lark_sends_every_payload_and_rejects_business_error(self, post):
        ok = Mock(status_code=200)
        ok.json.return_value = {"code": 0}
        post.return_value = ok
        payloads = create_lark_messages("标题", "内容" * 1000, limit=800)
        send_webhook("https://open.larkoffice.com/open-apis/bot/v2/hook/fake", "lark", payloads)
        self.assertEqual(post.call_count, len(payloads))
        for call in post.call_args_list:
            self.assertIsInstance(call.kwargs["data"], bytes)
            self.assertLessEqual(len(call.kwargs["data"]), 800)

        failed = Mock(status_code=200)
        failed.json.return_value = {"code": 19001}
        post.reset_mock()
        post.return_value = failed
        with self.assertRaisesRegex(RuntimeError, "code=19001"):
            send_webhook(
                "https://open.larkoffice.com/open-apis/bot/v2/hook/fake",
                "lark",
                [{"msg_type": "text"}],
            )


class DisplayTests(unittest.TestCase):
    def test_home_away_fields_determine_display_order(self):
        event = {
            "competitions": [{"competitors": [
                {"homeAway": "away", "score": "1", "team": {"displayName": "客队"}},
                {"homeAway": "home", "score": "2", "team": {"displayName": "Home Team"}},
            ]}]
        }
        result = format_match_result({"event": event})
        self.assertEqual(result, "主队 **Home Team** 2 - 1 客队 客队")

    def test_standings_use_readable_team_list(self):
        entries = [{
            "team": "中文 Team",
            "stats": [
                {"name": "rank", "displayValue": "1"},
                {"name": "gamesPlayed", "displayValue": "8"},
                {"name": "wins", "displayValue": "6"},
                {"name": "ties", "displayValue": "1"},
                {"name": "losses", "displayValue": "1"},
                {"name": "pointDifferential", "displayValue": "+9"},
                {"name": "points", "displayValue": "19"},
            ],
        }]
        text = format_standings(entries, "联赛")
        self.assertIn("- **1. 中文 Team**｜19 分", text)
        self.assertNotIn("```", text)


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
        return value if tz else value.replace(tzinfo=None)


class FootballDataTests(unittest.TestCase):
    @patch.object(espn, "LEAGUES", {"Fake League": "fake.1"})
    @patch.object(espn, "get_pacific_time_date", return_value=date(2026, 1, 10))
    @patch.object(espn, "get_match_summary", return_value=None)
    @patch.object(espn, "datetime", FrozenDateTime)
    @patch.object(espn.requests, "get")
    def test_filters_last_24_hours_and_deduplicates_events(self, get, _summary, _date):
        recent = {
            "id": "recent",
            "date": "2026-01-10T01:00:00Z",
            "status": {"type": {"name": "STATUS_FINAL"}},
        }
        old = {
            "id": "old",
            "date": "2026-01-09T11:59:59Z",
            "status": {"type": {"name": "STATUS_FINAL"}},
        }
        response = Mock(status_code=200)
        response.json.return_value = {"events": [recent, old]}
        get.return_value = response

        matches, _standings = espn.get_football_matches_from_espn()

        self.assertEqual([match["event"]["id"] for match in matches], ["recent"])
        self.assertEqual(get.call_count, 3)

    @patch.object(espn, "LEAGUES", {"Fake League": "fake.1"})
    @patch.object(espn, "get_pacific_time_date", return_value=date(2026, 1, 10))
    @patch.object(espn.requests, "get", side_effect=espn.requests.RequestException("offline"))
    def test_raises_when_every_football_request_fails(self, _get, _date):
        with self.assertRaisesRegex(RuntimeError, "全部失败"):
            espn.get_football_matches_from_espn()


if __name__ == "__main__":
    unittest.main()
