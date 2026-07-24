#!/usr/bin/env python3
import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "dingtalk-weekly-report" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dtwr_validation import ValidationError, validate_config, validate_report
from extract_week import date_near_week, pick_monday


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(
            (ROOT / "tests/fixtures/config.json").read_text(encoding="utf-8"))
        cls.report = json.loads(
            (ROOT / "tests/fixtures/week_report_20260713.json").read_text(encoding="utf-8"))

    def test_config_fixture_is_valid(self):
        validate_config(self.config)

    def test_config_placeholder_is_rejected(self):
        value = copy.deepcopy(self.config)
        value["name"] = "你的姓名"
        with self.assertRaisesRegex(ValidationError, "模板占位值"):
            validate_config(value)

    def test_config_nested_hours_are_validated(self):
        value = copy.deepcopy(self.config)
        value["standup"]["hours"] = "0.5"
        with self.assertRaisesRegex(ValidationError, "standup.hours"):
            validate_config(value)

    def test_default_week_monday_uses_previous_week(self):
        self.assertEqual(
            pick_monday(["extract_week.py"], date(2026, 7, 20)),
            date(2026, 7, 13),
        )

    def test_default_week_friday_uses_current_week(self):
        self.assertEqual(
            pick_monday(["extract_week.py"], date(2026, 7, 24)),
            date(2026, 7, 20),
        )

    def test_cross_year_heading_uses_nearest_year(self):
        self.assertEqual(
            date_near_week(1, 1, date(2025, 12, 29)),
            date(2026, 1, 1),
        )

    def test_report_fixture_is_valid(self):
        validate_report(self.report)

    def test_report_todo_is_rejected(self):
        value = copy.deepcopy(self.report)
        value["summary"]["done"] = "TODO"
        with self.assertRaisesRegex(ValidationError, "仍含 TODO"):
            validate_report(value)

    def test_report_long_content_is_rejected(self):
        value = copy.deepcopy(self.report)
        value["days"][1]["content"] = "长" * 201
        with self.assertRaisesRegex(ValidationError, "超过 200"):
            validate_report(value)

    def test_report_wrong_week_is_rejected(self):
        value = copy.deepcopy(self.report)
        value["week"]["end"] = "2026-07-18"
        with self.assertRaisesRegex(ValidationError, "week.end"):
            validate_report(value)

    def test_report_missing_workday_is_rejected(self):
        value = copy.deepcopy(self.report)
        value["days"] = value["days"][:-1]
        with self.assertRaisesRegex(ValidationError, "工作日未覆盖"):
            validate_report(value)

    def test_report_missing_project_is_rejected(self):
        value = copy.deepcopy(self.report)
        value["days"][1]["project"] = ""
        with self.assertRaisesRegex(ValidationError, "project 不能为空"):
            validate_report(value)

    def test_report_daily_total_over_24_is_rejected(self):
        value = copy.deepcopy(self.report)
        extra = copy.deepcopy(value["days"][1])
        extra["hours"] = 17
        value["days"].append(extra)
        with self.assertRaisesRegex(ValidationError, "合计工时超过 24"):
            validate_report(value)


if __name__ == "__main__":
    unittest.main()
