#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""查看、校验或安全更新当前用户的 DTWR 配置。"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dtwr_common import resolve_progress_report, workdir
from dtwr_validation import ValidationError, validate_config


FIELD_SPECS = (
    ("name", "姓名", "text"),
    ("form_url", "氚云表单 URL", "text"),
    ("form_project", "表单项目完整原文", "text"),
    ("attach_project", "附件关联项目", "text"),
    ("dept_goal", "关联部门目标（可空）", "text"),
    ("vocabulary.project_types", "表单项目类型（逗号分隔）", "list"),
    ("vocabulary.statuses", "表单工作状态（逗号分隔）", "list"),
    ("vocabulary.attachment_task_types", "附件任务类型（逗号分隔）", "list"),
    ("vocabulary.operations_project_type", "无需项目名称的运营类型", "project_type"),
    ("vocabulary.leave_status", "休假状态", "status"),
    ("project_type", "默认项目类型", "project_type"),
    ("status", "默认工作状态", "status"),
    ("daily_hours", "每日合计工时上限（**会议含在内**，可空）", "number"),
    ("weekly_hours_cap", "每周合计工时上限（可空）", "number"),
    ("hours", "默认每日工时（未配 daily_hours 时用）", "number"),
    ("leave_hours", "休假日工时", "number"),
    ("standup.content", "站会名称", "text"),
    ("standup.hours", "站会工时", "number"),
    ("standup.status", "站会状态", "status"),
    ("monday_meeting.content", "周一例会名称", "text"),
    ("monday_meeting.hours", "周一例会工时", "number"),
    ("monday_meeting.status", "周一例会状态", "status"),
    ("monday_meeting.project_type", "周一例会项目类型", "project_type"),
    ("holidays", "法定假日，不报工的日期（逗号分隔 YYYY-MM-DD，可空）", "list"),
    ("extra_workdays", "调休上班日，通常是周末（逗号分隔 YYYY-MM-DD，可空）", "list"),
    ("progress_report", "工作日志文件或项目目录（可空）", "text"),
    ("submission_reminder", "人工提交提醒（可空）", "text"),
    ("form_fields.subgrid_id", "工作详情子表 DOM id", "text"),
    ("form_fields.start_date", "开始日期字段 DOM id", "text"),
    ("form_fields.attach", "附件字段 DOM id（本表单无附件项则留空）", "text"),
    ("form_fields.note", "特殊说明字段 DOM id", "text"),
    ("form_fields.row_date", "行日期字段 DOM id", "text"),
    ("form_fields.row_type", "行项目类型字段 DOM id", "text"),
    ("form_fields.row_project", "行项目字段 DOM id", "text"),
    ("form_fields.row_status", "行状态字段 DOM id", "text"),
    ("form_fields.row_hours", "行工时字段 DOM id", "text"),
    ("form_fields.row_content", "行内容字段 DOM id", "text"),
    ("form_texts.report_title", "列表页周报标题", "text"),
    ("form_texts.add_row", "新增行按钮文本", "text"),
    ("form_texts.start_date_label", "开始日期字段标签", "text"),
    ("form_texts.save_draft", "暂存按钮文本", "text"),
    ("form_texts.success_messages", "成功提示（逗号分隔）", "list"),
)
FIELD_MAP = {path: (label, kind) for path, label, kind in FIELD_SPECS}


def nested_get(config: dict, path: str):
    value = config
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def nested_set(config: dict, path: str, value) -> None:
    target = config
    parts = path.split(".")
    for part in parts[:-1]:
        current = target.get(part)
        if not isinstance(current, dict):
            current = {}
            target[part] = current
        target = current
    target[parts[-1]] = value


def parse_value(path: str, raw: str):
    if path not in FIELD_MAP:
        raise ValueError(f"不支持的配置项 {path}")
    _, kind = FIELD_MAP[path]
    value = raw.strip()
    if value == "-":
        value = ""
    if kind == "number":
        try:
            number = float(value)
        except ValueError as exc:
            raise ValueError(f"{path} 必须是数字") from exc
        return int(number) if number.is_integer() else number
    if kind == "list":
        if value == "":
            return []
        return [item.strip() for item in re.split(r"[,，]", value)
                if item.strip()]
    return value


def apply_assignments(config: dict, assignments: list[str]) -> tuple[dict, list[str]]:
    candidate = json.loads(json.dumps(config, ensure_ascii=False))
    changed = []
    if candidate.get("config_version") != 2:
        candidate["config_version"] = 2
        changed.append("config_version")
    for assignment in assignments:
        path, separator, raw = assignment.partition("=")
        path = path.strip()
        if not separator or not path:
            raise ValueError(f"--set 必须使用 KEY=VALUE，实际为 {assignment!r}")
        value = parse_value(path, raw)
        if nested_get(candidate, path) != value:
            nested_set(candidate, path, value)
            changed.append(path)
    return candidate, changed


def validate_candidate(config: dict) -> None:
    validate_config(config)
    resolve_progress_report(config.get("progress_report", ""))


def save_config(path: Path, config: dict) -> Path:
    backup = path.with_name(path.name + ".bak")
    text = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=path.parent,
                prefix=".config.", suffix=".tmp", delete=False) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        shutil.copy2(path, backup)
        try:
            backup.chmod(0o600)
            temp_path.chmod(0o600)
        except OSError:
            pass
        os.replace(temp_path, path)
        temp_path = None
        return backup
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def interactive_assignments(config: dict) -> list[str]:
    print("逐项输入新值；直接回车保留当前值，输入 - 清空可选项。")
    print("不要输入或保存一次性 entry/auth 登录链接。")
    assignments = []
    preview = json.loads(json.dumps(config, ensure_ascii=False))
    for path, label, kind in FIELD_SPECS:
        current = nested_get(preview, path)
        hint = "空" if current in (None, "", []) else str(current)
        if kind == "project_type":
            choices = nested_get(preview, "vocabulary.project_types") or []
            label = f"{label}（{' / '.join(choices)}）"
        elif kind == "status":
            choices = nested_get(preview, "vocabulary.statuses") or []
            label = f"{label}（{' / '.join(choices)}）"
        raw = input(f"{label} [{hint}]: ")
        if raw != "":
            assignments.append(f"{path}={raw}")
            nested_set(preview, path, parse_value(path, raw))
    return assignments



def assignments_from_discovery(config: dict, path: Path) -> list[str]:
    """把 `--dump-record` 产出的候选逐项交给用户确认。

    **绝不自动写入**：每一项都要人点头。组织私有面必须由人确认是本项目的不变量——
    自动发现只是把"手抄十个 id"降为"确认十几个候选"，不是把人从回路里拿掉。
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"读不到候选文件 {path}: {exc}") from exc

    current = config.get("form_fields", {})
    assignments = []
    print(f"候选来源: {path}")
    print("逐项确认；y=采纳，回车=跳过。歧义项输入编号选择。\n")

    for key, item in sorted(payload.get("proposal", {}).items()):
        target = f"form_fields.{key}"
        if key == "subgrid_id":
            target = "form_fields.subgrid_id"
        now = current.get(key, "")
        if now == item["id"]:
            print(f"[已一致] {key} = {item['id']}")
            continue
        observed = payload.get("observed", {}).get(key)
        hint = f"；历史取值: {' / '.join(observed)}" if observed else ""
        print(f"{key}: {now or '(空)'} -> {item['id']} "
              f"[{item['confidence']}] {item['why']}{hint}")
        if input("  采纳？[y/N]: ").strip().lower() in ("y", "yes"):
            assignments.append(f"{target}={item['id']}")

    for key, options in sorted(payload.get("ambiguous", {}).items()):
        print(f"{key}: 工具无法区分，请选择")
        for i, option in enumerate(options, 1):
            print(f"  {i}) {option}")
        raw = input("  选编号（回车跳过）: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            assignments.append(f"form_fields.{key}={options[int(raw) - 1]}")
    return assignments


def print_changes(before: dict, after: dict, changed: list[str]) -> None:
    print("待保存变更：")
    for path in changed:
        print(f"- {path}: {nested_get(before, path)!r} -> "
              f"{nested_get(after, path)!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="查看、校验或交互更新 dingtalk-weekly-report 的 config.json")
    parser.add_argument("--show", action="store_true", help="显示当前配置，不修改")
    parser.add_argument("--check", action="store_true", help="校验当前配置，不修改")
    parser.add_argument(
        "--set", action="append", default=[], metavar="KEY=VALUE",
        help="更新指定配置项；可重复使用，嵌套项使用 standup.hours 形式")
    parser.add_argument(
        "--from-discovery", nargs="?", const="", metavar="PATH",
        help="读取 --dump-record 产出的候选，逐项确认后写入 form_fields")
    parser.add_argument("--yes", action="store_true", help="确认写入，跳过保存确认")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if (args.show or args.check) and args.set:
        raise SystemExit("--show/--check 不能与 --set 同时使用")
    if args.show and args.check:
        raise SystemExit("--show 与 --check 不能同时使用")

    work = workdir()
    path = work / "config.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"无法读取 {path}: {exc}") from exc

    if args.show:
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return 0
    try:
        if args.check:
            validate_candidate(config)
            print(f"配置有效: {path}")
            return 0

        if args.from_discovery is not None:
            source = Path(args.from_discovery) if args.from_discovery else (
                work / "output" / "field-proposal.json")
            assignments = assignments_from_discovery(config, source)
        else:
            assignments = args.set or interactive_assignments(config)
        candidate, changed = apply_assignments(config, assignments)
        if not changed:
            validate_candidate(candidate)
            print("配置未变化。")
            return 0
        validate_candidate(candidate)
        print_changes(config, candidate, changed)
        if not args.yes:
            answer = input("确认保存？[y/N]: ").strip().lower()
            if answer not in ("y", "yes"):
                print("已取消，配置未修改。")
                return 0
        backup = save_config(path, candidate)
        print(f"配置已保存: {path}")
        print(f"旧配置备份: {backup}")
        return 0
    except (ValidationError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
