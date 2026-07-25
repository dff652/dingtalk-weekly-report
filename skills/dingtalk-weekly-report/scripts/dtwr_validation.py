"""配置与周报 JSON 的共享校验。"""
import re
from datetime import date, timedelta
from urllib.parse import urlparse

from dtwr_fields import (
    FORM_FIELD_KEYS,
    FORM_TEXT_KEYS,
    VOCABULARY_LIST_KEYS,
    VOCABULARY_VALUE_KEYS,
)


class ValidationError(ValueError):
    pass


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _has_todo(value) -> bool:
    return "TODO" in str(value).upper()


def _hours_ok(value) -> bool:
    return (isinstance(value, (int, float))
            and not isinstance(value, bool)
            and 0 < value <= 24)


def _string_list(value, label: str, errors: list[str]) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} 必须是非空字符串列表")
        return ()
    result = tuple(_text(item) for item in value)
    if any(not item for item in result):
        errors.append(f"{label} 不能包含空值")
    if len(set(result)) != len(result):
        errors.append(f"{label} 不能包含重复值")
    return result


def _validate_vocabulary(container: dict, errors: list[str]) -> dict:
    value = container.get("vocabulary")
    if not isinstance(value, dict):
        errors.append("vocabulary 必须是对象")
        return {
            "project_types": (),
            "statuses": (),
            "attachment_task_types": (),
            "operations_project_type": "",
            "leave_status": "",
        }

    lists = {
        key: _string_list(value.get(key), f"vocabulary.{key}", errors)
        for key in VOCABULARY_LIST_KEYS
    }
    scalars = {}
    for key in VOCABULARY_VALUE_KEYS:
        scalars[key] = _text(value.get(key))
        if not scalars[key]:
            errors.append(f"vocabulary.{key} 不能为空")

    if (scalars["operations_project_type"]
            and scalars["operations_project_type"] not in lists["project_types"]):
        errors.append(
            "vocabulary.operations_project_type 必须属于 project_types")
    if scalars["leave_status"] and scalars["leave_status"] not in lists["statuses"]:
        errors.append("vocabulary.leave_status 必须属于 statuses")
    invalid_attachment = (
        set(lists["attachment_task_types"]) - set(lists["project_types"]))
    if invalid_attachment:
        errors.append(
            "vocabulary.attachment_task_types 必须是 project_types 子集: "
            + ", ".join(sorted(invalid_attachment)))
    return {**lists, **scalars}


def _validate_form_metadata(config: dict, errors: list[str]) -> None:
    fields = config.get("form_fields")
    if not isinstance(fields, dict):
        errors.append("form_fields 必须是对象")
    else:
        for key in FORM_FIELD_KEYS:
            value = _text(fields.get(key))
            if not value:
                errors.append(f"form_fields.{key} 不能为空")
            elif not re.fullmatch(r"[A-Za-z0-9_-]+", value):
                errors.append(
                    f"form_fields.{key} 只能包含字母、数字、下划线或连字符")

    texts = config.get("form_texts")
    if not isinstance(texts, dict):
        errors.append("form_texts 必须是对象")
    else:
        for key in FORM_TEXT_KEYS:
            if not _text(texts.get(key)):
                errors.append(f"form_texts.{key} 不能为空")
        save_draft = re.sub(r"\s+", "", _text(texts.get("save_draft")))
        if "提交" in save_draft or "submit" in save_draft.casefold():
            errors.append("form_texts.save_draft 不得指向提交按钮")
        success = texts.get("success_messages")
        _string_list(success, "form_texts.success_messages", errors)


def _validate_form_url(value, errors: list[str]) -> None:
    form_url = _text(value)
    if not form_url:
        errors.append("form_url 不能为空")
        return
    parsed = urlparse(form_url)
    if (parsed.scheme != "https"
            or not (parsed.hostname == "h3yun.com"
                    or (parsed.hostname or "").endswith(".h3yun.com"))):
        errors.append("form_url 必须是 https://*.h3yun.com 表单地址")
    if "/entry/auth" in parsed.path:
        errors.append("form_url 不得保存一次性 entry/auth 登录链接")


def validate_config(config: dict) -> None:
    errors = []
    if not isinstance(config, dict):
        raise ValidationError("config.json 顶层必须是对象")

    required = (
        "config_version", "name", "form_url", "form_project", "attach_project",
        "project_type", "status", "hours", "leave_hours",
        "standup", "monday_meeting", "vocabulary",
        "form_fields", "form_texts",
    )
    for key in required:
        if key not in config:
            errors.append(f"缺少配置项 {key}")
    if config.get("config_version") != 2:
        errors.append("config_version 必须为 2；旧配置请按升级说明迁移")

    placeholders = (
        "你的姓名", "XXXXX", "项目全名", "项目下拉完整原文",
        "附件关联项目或活动", "测试用户",
    )
    for key in ("name", "form_project", "attach_project"):
        value = _text(config.get(key))
        if not value:
            errors.append(f"{key} 不能为空")
        elif any(mark in value for mark in placeholders):
            errors.append(f"{key} 仍是模板占位值")

    _validate_form_url(config.get("form_url"), errors)
    _validate_form_metadata(config, errors)
    vocabulary = _validate_vocabulary(config, errors)
    if config.get("project_type") not in vocabulary["project_types"]:
        errors.append(f"project_type 非法: {config.get('project_type')!r}")
    if config.get("status") not in vocabulary["statuses"]:
        errors.append(f"status 非法: {config.get('status')!r}")
    for key in ("hours", "leave_hours"):
        if not _hours_ok(config.get(key)):
            errors.append(f"{key} 必须是 0~24 的数字")

    for key in ("standup", "monday_meeting"):
        value = config.get(key)
        if not isinstance(value, dict):
            errors.append(f"{key} 必须是对象")
            continue
        for subkey in ("content", "hours", "status"):
            if subkey not in value:
                errors.append(f"{key}.{subkey} 缺失")
        if not _text(value.get("content")):
            errors.append(f"{key}.content 不能为空")
        if not _hours_ok(value.get("hours")):
            errors.append(f"{key}.hours 必须是 0~24 的数字")
        if value.get("status") not in vocabulary["statuses"]:
            errors.append(f"{key}.status 非法: {value.get('status')!r}")
        project_type = value.get("project_type", config.get("project_type"))
        if project_type not in vocabulary["project_types"]:
            errors.append(f"{key}.project_type 非法")

    if errors:
        raise ValidationError("config.json 未就绪:\n- " + "\n- ".join(errors))


def validate_report(report: dict, require_complete: bool = True) -> None:
    errors = []
    if not isinstance(report, dict):
        raise ValidationError("week_report.json 顶层必须是对象")

    for key in ("schema_version", "name", "form_project", "attach_project", "vocabulary",
                "week", "days", "summary", "next_week"):
        if key not in report:
            errors.append(f"缺少必填节 {key}")
    if errors:
        raise ValidationError("week_report.json 校验失败:\n- " + "\n- ".join(errors))
    if report.get("schema_version") != 2:
        errors.append("schema_version 必须为 2")

    vocabulary = _validate_vocabulary(report, errors)
    for key in ("name", "form_project", "attach_project"):
        if not _text(report.get(key)):
            errors.append(f"{key} 不能为空")

    try:
        monday = date.fromisoformat(report["week"]["start"])
        end = date.fromisoformat(report["week"]["end"])
        if monday.weekday() != 0:
            errors.append(f"week.start 不是周一: {monday}")
        if end != monday + timedelta(days=6):
            errors.append(f"week.end 应为 {monday + timedelta(days=6)}，实际为 {end}")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"week 日期非法: {exc}")
        monday = None

    days = report.get("days")
    if not isinstance(days, list) or not days:
        errors.append("days 必须是非空列表")
        days = []

    covered = set()
    daily_hours = {}
    for i, row in enumerate(days, 1):
        label = f"days[{i}]"
        if not isinstance(row, dict):
            errors.append(f"{label} 必须是对象")
            continue
        row_date = None
        try:
            row_date = date.fromisoformat(row["date"])
            covered.add(row_date)
            daily_hours.setdefault(row_date, 0)
            if monday and not (monday <= row_date <= monday + timedelta(days=6)):
                errors.append(f"{label}.date {row_date} 不在目标周")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{label}.date 非法")

        project_type = row.get("project_type")
        status = row.get("status")
        if project_type not in vocabulary["project_types"]:
            errors.append(f"{label}.project_type 非法: {project_type!r}")
        if status not in vocabulary["statuses"]:
            errors.append(f"{label}.status 非法: {status!r}")
        if (status != vocabulary["leave_status"]
                and project_type != vocabulary["operations_project_type"]
                and not _text(row.get("project"))):
            errors.append(f"{label}.project 不能为空")

        hours = row.get("hours")
        if not _hours_ok(hours):
            errors.append(f"{label}.hours 必须是 0~24 的数字")
        elif row_date is not None:
            daily_hours[row_date] += hours

        content = _text(row.get("content"))
        if status != vocabulary["leave_status"] and not content:
            errors.append(f"{label}.content 不能为空")
        if len(content) > 200:
            errors.append(f"{label}.content 超过 200 字（当前 {len(content)}）")
        if _has_todo(content):
            errors.append(f"{label}.content 仍含 TODO")

    for row_date, total in daily_hours.items():
        if total > 24:
            errors.append(f"{row_date} 合计工时超过 24 小时（当前 {total}）")

    if require_complete and monday:
        missing = [str(monday + timedelta(days=i)) for i in range(5)
                   if monday + timedelta(days=i) not in covered]
        if missing:
            errors.append("工作日未覆盖: " + ", ".join(missing))

    for section, fields in (
        ("summary", ("tasks", "deliverables", "done")),
        ("next_week", ("tasks", "deliverables")),
    ):
        value = report.get(section)
        if not isinstance(value, dict):
            errors.append(f"{section} 必须是对象")
            continue
        for field in fields:
            text = _text(value.get(field))
            if not text:
                errors.append(f"{section}.{field} 不能为空")
            elif _has_todo(text):
                errors.append(f"{section}.{field} 仍含 TODO")
        task_type = value.get("task_type")
        if task_type not in vocabulary["attachment_task_types"]:
            errors.append(f"{section}.task_type 非法: {task_type!r}")

    if errors:
        raise ValidationError("week_report.json 校验失败:\n- " + "\n- ".join(errors))


def validate_report_against_config(report: dict, config: dict) -> None:
    if report.get("vocabulary") != config.get("vocabulary"):
        raise ValidationError(
            "week_report.json 的 vocabulary 与当前 config.json 不一致；"
            "请确认是否切换过组织/表单配置")
