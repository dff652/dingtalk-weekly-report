#!/usr/bin/env python3
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path(os.environ.get(
    "DTWR_SKILL", ROOT / "skills" / "dingtalk-weekly-report"))
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dtwr_common import resolve_progress_report, require_owned, workdir
from dtwr_fields import ATTACHMENT_TASK_TYPES, PROJECT_TYPES, STATUSES
from dtwr_validation import ValidationError, validate_config, validate_report
from dtwr_week import date_near_week, pick_monday


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

    def test_invalid_heading_date_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "无效月日"):
            date_near_week(2, 30, date(2026, 2, 23))

    def test_runtime_enums_are_documented(self):
        fields = (SKILL / "references/FIELDS.md").read_text(encoding="utf-8")
        for value in (*PROJECT_TYPES, *ATTACHMENT_TASK_TYPES, *STATUSES):
            self.assertIn(f"`{value}`", fields)

    @unittest.skipUnless(hasattr(os, "geteuid"), "POSIX owner check")
    def test_require_owned_rejects_different_uid(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("dtwr_common.os.geteuid",
                       return_value=os.geteuid() + 1):
                with self.assertRaisesRegex(SystemExit, "不属于当前用户"):
                    require_owned(Path(directory), "测试目录")

    def test_workdir_uses_user_root_pointer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            work = root / "work"
            pointer = home / ".config" / "dtwr" / "root"
            pointer.parent.mkdir(parents=True)
            work.mkdir()
            (work / "config.json").write_text("{}", encoding="utf-8")
            pointer.write_text(f"{work}\n", encoding="utf-8")
            with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                os.environ.pop("DTWR_HOME", None)
                os.environ.pop("XDG_CONFIG_HOME", None)
                with patch("dtwr_common.Path.home", return_value=home):
                    self.assertEqual(workdir(), work.resolve())

    def test_workdir_rejects_empty_root_pointer(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            pointer = home / ".config" / "dtwr" / "root"
            pointer.parent.mkdir(parents=True)
            pointer.write_text("\n", encoding="utf-8")
            with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                os.environ.pop("DTWR_HOME", None)
                os.environ.pop("XDG_CONFIG_HOME", None)
                with patch("dtwr_common.Path.home", return_value=home):
                    with self.assertRaisesRegex(SystemExit, "指针.*为空"):
                        workdir()

    def test_progress_report_empty_uses_interview_mode(self):
        self.assertIsNone(resolve_progress_report("  "))

    def test_progress_report_accepts_file(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "work-log.md"
            report.write_text("# 工作日志\n", encoding="utf-8")
            self.assertEqual(resolve_progress_report(str(report)), report)

    def test_progress_report_resolves_project_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            report = project / "docs" / "report" / "PROGRESS_REPORT.md"
            report.parent.mkdir(parents=True)
            report.write_text("# 项目进展\n", encoding="utf-8")
            self.assertEqual(resolve_progress_report(str(project)), report)

    def test_progress_report_directory_requires_standard_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "docs/report/PROGRESS_REPORT.md"):
                resolve_progress_report(directory)

    def test_progress_report_missing_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with self.assertRaisesRegex(ValueError, "不存在"):
                resolve_progress_report(str(missing))

    def test_extract_week_accepts_project_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            source = project / "docs" / "report" / "PROGRESS_REPORT.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                (ROOT / "tests/fixtures/progress_report.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            work = root / "work"
            work.mkdir()
            config = copy.deepcopy(self.config)
            config["progress_report"] = str(project)
            (work / "config.json").write_text(
                json.dumps(config, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "extract_week.py"), "2026-07-13"],
                env={**os.environ, "DTWR_HOME": str(work)},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(
                (work / "weeks/week_report_20260713.json").read_text(
                    encoding="utf-8"))
            self.assertTrue(any(
                row["date"] == "2026-07-13"
                and row["content"] == "输入校验完成"
                for row in report["days"]
            ))

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
