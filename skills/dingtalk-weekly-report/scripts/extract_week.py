#!/usr/bin/env python3
"""从 PROGRESS_REPORT.md 抽取指定周的内容，生成 week_report.json 草稿（供人工审改）。

用法: python3 extract_week.py 2026-07-13  # 参数=周一日期；缺省=周一取上周、其他日期取本周
输出: weeks/week_report_YYYYMMDD.json（已存在则拒绝覆盖，防止冲掉人工修改）

抽取策略（草稿性质，产出后必须人工过目）：
- 逐日内容：取「## 3. 每日工作详情」里 `### N月N日（标题）` 的标题作为该日「主要工作内容」初稿；
  区间标题（`### 7月18日 ~ 7月19日`）与无标题日置 TODO 占位并告警——宁可留空逼人补，不静默凑数。
- 周总结/下周计划：取「## 4. 周报」里覆盖该周的 `### Week N（起 ~ 止）— 标题` 生成骨架，
  详情仍需人工从该节挑选粘贴（LLM 压缩润色建议在 Claude Code 会话里做）。
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from dtwr_common import workdir
from dtwr_validation import ValidationError, validate_config
from dtwr_week import date_near_week, pick_monday

DAY_RE = re.compile(r"^### (\d{1,2})月(\d{1,2})日(?:\s*[~～]\s*(\d{1,2})月(\d{1,2})日)?(?:（(.*?)）)?", re.M)
WEEK_RE = re.compile(r"^### Week \d+（(\d{4}-\d{2}-\d{2}) ~ ?(\d{4}-\d{2}-\d{2})?[^）]*）—\s*(.*)$", re.M)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("用法: python3 extract_week.py [YYYY-MM-DD周一日期]")
        return
    work = workdir()
    config = json.loads((work / "config.json").read_text(encoding="utf-8"))
    try:
        validate_config(config)
        monday = pick_monday(sys.argv)
    except ValidationError as exc:
        sys.exit(str(exc))
    except ValueError as exc:
        sys.exit(str(exc))
    workdays = [monday + timedelta(days=i) for i in range(5)]
    source = config.get("progress_report", "").strip()
    if source:
        source_path = Path(source).expanduser()
        if not source_path.is_file():
            sys.exit(f"已配置的 progress_report 不存在或不是文件: {source_path}；"
                     "请修正路径，若没有工作日志则将该项留空")
        text = source_path.read_text(encoding="utf-8")
    else:
        text = ""
        print("未配置 progress_report：将生成逐日 TODO 骨架，请通过访谈/手工补齐后再生成附件",
              file=sys.stderr)

    titles = {}  # date -> 标题
    for m in DAY_RE.finditer(text):
        try:
            d1 = date_near_week(int(m.group(1)), int(m.group(2)), monday)
        except ValueError as exc:
            sys.exit(f"工作日志日期标题非法「{m.group(0)}」: {exc}")
        if m.group(3):  # 区间标题：区间内所有天都标记为存在但无独立标题
            try:
                d2 = date_near_week(int(m.group(3)), int(m.group(4)), monday)
            except ValueError as exc:
                sys.exit(f"工作日志日期标题非法「{m.group(0)}」: {exc}")
            if d2 < d1:
                try:
                    d2 = date(d1.year + 1, d2.month, d2.day)
                except ValueError as exc:
                    sys.exit(f"工作日志跨年日期非法「{m.group(0)}」: {exc}")
            d = d1
            while d <= d2:
                titles.setdefault(d, "")
                d += timedelta(days=1)
        else:
            titles[d1] = m.group(5) or ""

    days, missing = [], []
    for i, d in enumerate(workdays):
        # 周一=算法团队周例会，其余=产品研发站会（历史填报模式，可在 json 里增删）
        meet = config["monday_meeting"] if i == 0 else config["standup"]
        days.append({
            "date": str(d),
            "project_type": meet.get("project_type", config["project_type"]),
            "project": "" if meet.get("project_type") == "公司和部门运营活动" else config["form_project"],
            "status": meet["status"],
            "hours": meet["hours"],
            "content": meet["content"],
        })
        title = titles.get(d, "")
        if not title:
            missing.append(str(d))
            title = "TODO(人工补充：该日在 PROGRESS_REPORT.md 无独立标题——现场/传输/会议等非提交工作也要写)"
        days.append({
            "date": str(d),
            "project_type": config["project_type"],
            "project": config["form_project"],
            "status": config["status"],
            "hours": config["hours"],
            "content": title,
        })

    week_title = ""
    for m in WEEK_RE.finditer(text):
        start = date.fromisoformat(m.group(1))
        if start <= monday <= start + timedelta(days=6):
            week_title = m.group(3).strip()
    if not week_title:
        print(f"警告: 周报节未找到覆盖 {monday} 的 Week 条目——先更新 PROGRESS_REPORT.md 再生成周报", file=sys.stderr)

    report = {
        "name": config["name"],
        "form_project": config["form_project"],
        "attach_project": config["attach_project"],
        "dept_goal": config["dept_goal"],
        "week": {"start": str(monday), "end": str(monday + timedelta(days=6))},
        "days": days,
        "special_note": "",
        "summary": {
            "tasks": f"TODO(参考 Week 标题: {week_title})",
            "task_type": config["project_type"],
            "deliverables": "TODO",
            "done": "TODO(编号列表，逐任务/交付物说明完成状态)",
            "remark": "",
        },
        "next_week": {"tasks": "TODO", "task_type": config["project_type"], "deliverables": "TODO"},
    }

    out = work / "weeks" / f"week_report_{monday.strftime('%Y%m%d')}.json"
    out.parent.mkdir(exist_ok=True)
    if out.exists():
        sys.exit(f"{out} 已存在，拒绝覆盖（如需重生成先手动删除）")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"草稿已生成: {out}")
    if missing:
        print(f"待人工补齐的日期: {', '.join(missing)}", file=sys.stderr)
    print("下一步: 人工审改 json → python3 gen_attachment.py <json> → python3 print_form_rows.py <json>")


if __name__ == "__main__":
    main()
