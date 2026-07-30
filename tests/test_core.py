#!/usr/bin/env python3
import copy
import datetime
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
from configure import FIELD_SPECS, apply_assignments, configuration_plan
from dtwr_fields import FORM_FIELD_KEYS, FORM_TEXT_KEYS
from dtwr_validation import (
    ValidationError,
    validate_config,
    validate_report,
    validate_report_against_config,
)
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

    def test_config_allows_empty_attach_field(self):
        """留空 attach = 本表单无附件项，是合法组织配置，不是配置未就绪。"""
        value = copy.deepcopy(self.config)
        value["form_fields"]["attach"] = ""
        validate_config(value)

    def test_config_still_requires_other_form_fields(self):
        value = copy.deepcopy(self.config)
        value["form_fields"]["subgrid_id"] = ""
        with self.assertRaisesRegex(ValidationError, "subgrid_id 不能为空"):
            validate_config(value)

    def test_workdays_skip_holidays_and_include_makeup_days(self):
        """中国假期制度两头都会偏离周一到周五：法定假日不上班、调休时周末上班。"""
        from dtwr_week import workdays_for
        monday = datetime.date(2026, 9, 28)
        self.assertEqual(
            [str(d) for d in workdays_for(monday, {datetime.date(2026, 10, 1),
                                                   datetime.date(2026, 10, 2)})],
            ["2026-09-28", "2026-09-29", "2026-09-30"])
        self.assertEqual(
            [str(d) for d in workdays_for(
                monday, {datetime.date(2026, 10, 1)},
                {datetime.date(2026, 10, 3)})],
            ["2026-09-28", "2026-09-29", "2026-09-30", "2026-10-02", "2026-10-03"])

    def test_workdays_ignore_makeup_days_outside_target_week(self):
        from dtwr_week import workdays_for
        monday = datetime.date(2026, 9, 28)
        self.assertNotIn(
            "2026-10-10",
            [str(d) for d in workdays_for(monday, (), {datetime.date(2026, 10, 10)})])

    def test_config_rejects_day_that_is_both_holiday_and_workday(self):
        value = copy.deepcopy(self.config)
        value["holidays"] = ["2026-10-01"]
        value["extra_workdays"] = ["2026-10-01"]
        with self.assertRaisesRegex(ValidationError, "既是假期又是调休"):
            validate_config(value)

    def test_config_rejects_malformed_holiday(self):
        value = copy.deepcopy(self.config)
        value["holidays"] = ["2026/10/01"]
        with self.assertRaisesRegex(ValidationError, "holidays 含非法日期"):
            validate_config(value)

    def test_report_coverage_follows_workdays_snapshot(self):
        value = copy.deepcopy(self.report)
        value["workdays"] = ["2026-07-13", "2026-07-14"]
        value["days"] = [r for r in value["days"]
                         if r["date"] in ("2026-07-13", "2026-07-14")]
        validate_report(value)          # 假期周只报两天也应通过

    def test_report_without_snapshot_still_requires_five_weekdays(self):
        value = copy.deepcopy(self.report)
        value.pop("workdays", None)
        value["days"] = [r for r in value["days"] if r["date"] != "2026-07-17"]
        with self.assertRaisesRegex(ValidationError, "工作日未覆盖"):
            validate_report(value)

    def test_xlsx_strips_illegal_control_characters(self):
        """XML 1.0 不允许的控制字符会产出 Excel 打不开的文件；escape() 不管这些。"""
        from xlsxlite import xml_text
        self.assertEqual(xml_text("正常\x0b内容\x00结束"), "正常内容结束")
        self.assertEqual(xml_text("换行\n制表\t保留"), "换行\n制表\t保留")

    def test_hours_policy_blocks_over_daily_cap(self):
        """会议含在每日上限内；超了必须拦——加班要显式说明，不能默默多报。"""
        value = copy.deepcopy(self.report)
        value["hours_policy"] = {"daily_hours": 8, "weekly_hours_cap": 40}
        validate_report(value)                       # 每日 8h 应通过
        over = copy.deepcopy(value)
        over["days"][1]["hours"] = 10
        with self.assertRaisesRegex(ValidationError, "超过每日上限"):
            validate_report(over)

    def test_hours_policy_blocks_over_weekly_cap(self):
        value = copy.deepcopy(self.report)
        value["hours_policy"] = {"weekly_hours_cap": 30}
        with self.assertRaisesRegex(ValidationError, "超过每周上限"):
            validate_report(value)

    def test_report_without_hours_policy_is_unconstrained(self):
        """没配口径的旧报告不受新上限影响，向后兼容。"""
        value = copy.deepcopy(self.report)
        value.pop("hours_policy", None)
        validate_report(value)

    def test_config_rejects_bad_hours_policy(self):
        value = copy.deepcopy(self.config)
        value["daily_hours"] = 0
        with self.assertRaisesRegex(ValidationError, "daily_hours"):
            validate_config(value)

    def test_config_rejects_submit_button_as_draft_action(self):
        value = copy.deepcopy(self.config)
        value["form_texts"]["save_draft"] = "提 交"
        with self.assertRaisesRegex(ValidationError, "不得指向提交按钮"):
            validate_config(value)

    def test_incomplete_config_allows_onboarding_but_not_final_check(self):
        value = json.loads(
            (SKILL / "assets/config.example.json").read_text(encoding="utf-8"))
        validate_config(value, allow_incomplete=True)
        with self.assertRaisesRegex(ValidationError, "config.json 未就绪"):
            validate_config(value)

    def test_incomplete_config_still_rejects_unsafe_nonempty_values(self):
        value = json.loads(
            (SKILL / "assets/config.example.json").read_text(encoding="utf-8"))
        value["form_url"] = "https://www.h3yun.com/entry/auth?token=secret"
        value["form_texts"]["save_draft"] = "提交"
        with self.assertRaisesRegex(ValidationError, "entry/auth"):
            validate_config(value, allow_incomplete=True)
        value["form_url"] = ""
        with self.assertRaisesRegex(ValidationError, "不得指向提交按钮"):
            validate_config(value, allow_incomplete=True)

    def test_configuration_plan_separates_user_input_from_form_discovery(self):
        value = json.loads(
            (SKILL / "assets/config.example.json").read_text(encoding="utf-8"))
        plan = configuration_plan(value)
        self.assertEqual(
            [item["path"] for item in plan["needs_user"]],
            [
                "name",
                "form_url",
                "form_project",
                "attach_project",
                "form_texts.report_title",
            ],
        )
        form_paths = {item["path"] for item in plan["needs_form"]}
        self.assertIn("form_fields.subgrid_id", form_paths)
        self.assertIn("vocabulary.project_types", form_paths)
        self.assertNotIn("form_texts.report_title", form_paths)
        self.assertNotIn("form_fields.attach", form_paths)
        self.assertNotIn("progress_report", form_paths)
        self.assertFalse(plan["ready"])

    def test_configure_guided_can_save_partial_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            config_path = work / "config.json"
            config_path.write_text(
                (SKILL / "assets/config.example.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS / "configure.py"),
                    "--guided",
                    "--set", "name=引导验收人员",
                    "--set", "form_project=产品研发",
                    "--yes",
                ],
                env={**os.environ, "DTWR_HOME": str(work)},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            updated = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["name"], "引导验收人员")
            self.assertEqual(updated["form_project"], "产品研发")
            self.assertIn("仍需用户提供", result.stdout)
            self.assertTrue((work / "config.json.bak").exists())
            strict = subprocess.run(
                [sys.executable, str(SCRIPTS / "configure.py"), "--check"],
                env={**os.environ, "DTWR_HOME": str(work)},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(strict.returncode, 0)

    def test_discovery_can_save_fields_before_full_config_is_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            config_path = work / "config.json"
            config_path.write_text(
                (SKILL / "assets/config.example.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            proposal = work / "proposal.json"
            proposal.write_text(json.dumps({
                "proposal": {
                    "subgrid_id": {
                        "id": "subgrid-safe-id",
                        "confidence": "high",
                        "why": "测试候选",
                    },
                },
                "observed": {},
                "ambiguous": {},
            }, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS / "configure.py"),
                    "--from-discovery", str(proposal), "--yes",
                ],
                env={**os.environ, "DTWR_HOME": str(work)},
                input="y\n",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            updated = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(
                updated["form_fields"]["subgrid_id"], "subgrid-safe-id")
            self.assertIn("仍需用户提供", result.stdout)

    def test_configure_missing_json_never_prints_current_values(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            config_path = work / "config.json"
            value = json.loads(
                (SKILL / "assets/config.example.json").read_text(encoding="utf-8"))
            value["name"] = "不应出现在计划中的姓名"
            config_path.write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS / "configure.py"),
                    "--missing", "--json",
                ],
                env={**os.environ, "DTWR_HOME": str(work)},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertNotIn("不应出现在计划中的姓名", result.stdout)
            self.assertNotIn(
                "name", [item["path"] for item in plan["needs_user"]])

    def test_configure_marks_legacy_config_as_version_two(self):
        value = copy.deepcopy(self.config)
        value.pop("config_version")
        candidate, changed = apply_assignments(value, [])
        self.assertEqual(candidate["config_version"], 2)
        self.assertIn("config_version", changed)

    def test_configure_updates_valid_config_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            config_path = work / "config.json"
            original = json.dumps(
                self.config, ensure_ascii=False, indent=2) + "\n"
            config_path.write_text(original, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS / "configure.py"),
                    "--set", "name=新验收人员", "--yes",
                ],
                env={**os.environ, "DTWR_HOME": str(work)},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            updated = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["name"], "新验收人员")
            self.assertEqual(
                (work / "config.json.bak").read_text(encoding="utf-8"),
                original,
            )

    def test_configure_interactive_update(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            config_path = work / "config.json"
            config_path.write_text(
                json.dumps(self.config, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            user_input = (
                "交互验收人员\n"
                + "\n" * (len(FIELD_SPECS) - 1)
                + "y\n"
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "configure.py")],
                env={**os.environ, "DTWR_HOME": str(work)},
                input=user_input,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            updated = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["name"], "交互验收人员")

    def test_configure_rejects_invalid_update_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            config_path = work / "config.json"
            original = json.dumps(
                self.config, ensure_ascii=False, indent=2) + "\n"
            config_path.write_text(original, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS / "configure.py"),
                    "--set", "hours=25", "--yes",
                ],
                env={**os.environ, "DTWR_HOME": str(work)},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("hours 必须", result.stderr)
            self.assertEqual(
                config_path.read_text(encoding="utf-8"), original)
            self.assertFalse((work / "config.json.bak").exists())

    def test_configure_rejects_auth_url_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            config_path = work / "config.json"
            original = json.dumps(
                self.config, ensure_ascii=False, indent=2) + "\n"
            config_path.write_text(original, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS / "configure.py"),
                    "--set",
                    "form_url=https://www.h3yun.com/entry/auth?token=secret",
                    "--yes",
                ],
                env={**os.environ, "DTWR_HOME": str(work)},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("不得保存", result.stderr)
            self.assertEqual(
                config_path.read_text(encoding="utf-8"), original)

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

    def test_runtime_form_metadata_is_documented(self):
        fields = (SKILL / "references/FIELDS.md").read_text(encoding="utf-8")
        for key in (*FORM_FIELD_KEYS, *FORM_TEXT_KEYS):
            self.assertIn(f"`{key}`", fields)

    def test_report_vocabulary_matches_config_fixture(self):
        self.assertEqual(
            self.report["vocabulary"], self.config["vocabulary"])

    def test_report_vocabulary_must_match_current_config(self):
        config = copy.deepcopy(self.config)
        config["vocabulary"]["statuses"].append("新增状态")
        with self.assertRaisesRegex(ValidationError, "不一致"):
            validate_report_against_config(self.report, config)

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

    def test_workdir_rejects_source_repository_as_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / "config.json").write_text("{}", encoding="utf-8")
            skill = work / "skills" / "dingtalk-weekly-report"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\n", encoding="utf-8")
            with patch.dict(
                    os.environ, {"DTWR_HOME": str(work)}, clear=False):
                with self.assertRaisesRegex(SystemExit, "源码仓库"):
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
