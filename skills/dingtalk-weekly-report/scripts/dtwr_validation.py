"""配置与周报 JSON 的共享校验。"""
from datetime import date, timedelta

from dtwr_fields import PROJECT_TYPES, STATUSES


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


def validate_config(config: dict) -> None:
    errors = []
    if not isinstance(config, dict):
        raise ValidationError("config.json 顶层必须是对象")

    required = ("name", "form_url", "form_project", "attach_project",
                "project_type", "status", "hours", "standup", "monday_meeting")
    for key in required:
        if key not in config:
            errors.append(f"缺少配置项 {key}")

    placeholders = ("你的姓名", "XXXXX", "项目全名", "测试用户")
    for key in ("name", "form_project", "attach_project"):
        value = _text(config.get(key))
        if not value:
            errors.append(f"{key} 不能为空")
        elif any(mark in value for mark in placeholders):
            errors.append(f"{key} 仍是模板占位值")

    if not _text(config.get("form_url")):
        errors.append("form_url 不能为空")
    if config.get("project_type") not in PROJECT_TYPES:
        errors.append(f"project_type 非法: {config.get('project_type')!r}")
    if config.get("status") not in STATUSES:
        errors.append(f"status 非法: {config.get('status')!r}")
    hours = config.get("hours")
    if not _hours_ok(hours):
        errors.append("hours 必须是 0~24 的数字")

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
        nested_hours = value.get("hours")
        if not _hours_ok(nested_hours):
            errors.append(f"{key}.hours 必须是 0~24 的数字")
        if value.get("status") not in STATUSES:
            errors.append(f"{key}.status 非法: {value.get('status')!r}")
        if value.get("project_type", config.get("project_type")) not in PROJECT_TYPES:
            errors.append(f"{key}.project_type 非法")

    if errors:
        raise ValidationError("config.json 未就绪:\n- " + "\n- ".join(errors))


def validate_report(report: dict, require_complete: bool = True) -> None:
    errors = []
    if not isinstance(report, dict):
        raise ValidationError("week_report.json 顶层必须是对象")

    for key in ("name", "form_project", "attach_project", "week",
                "days", "summary", "next_week"):
        if key not in report:
            errors.append(f"缺少必填节 {key}")
    if errors:
        raise ValidationError("week_report.json 校验失败:\n- " + "\n- ".join(errors))

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
        if project_type not in PROJECT_TYPES:
            errors.append(f"{label}.project_type 非法: {project_type!r}")
        if status not in STATUSES:
            errors.append(f"{label}.status 非法: {status!r}")
        if status != "休假" and project_type != "公司和部门运营活动" and not _text(row.get("project")):
            errors.append(f"{label}.project 不能为空")

        hours = row.get("hours")
        if not _hours_ok(hours):
            errors.append(f"{label}.hours 必须是 0~24 的数字")
        elif row_date is not None:
            daily_hours[row_date] += hours

        content = _text(row.get("content"))
        if status != "休假" and not content:
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

    if errors:
        raise ValidationError("week_report.json 校验失败:\n- " + "\n- ".join(errors))
