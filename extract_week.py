#!/usr/bin/env python3
"""从 PROGRESS_REPORT.md 抽取指定周的内容，生成 week_report.json 草稿（供人工审改）。

用法: python3 extract_week.py 2026-07-13          # 参数=周一日期；缺省=上一个周一
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

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))

DAY_RE = re.compile(r"^### (\d{1,2})月(\d{1,2})日(?:\s*[~～]\s*(\d{1,2})月(\d{1,2})日)?(?:（(.*?)）)?", re.M)
WEEK_RE = re.compile(r"^### Week \d+（(\d{4}-\d{2}-\d{2}) ~ ?(\d{4}-\d{2}-\d{2})?[^）]*）—\s*(.*)$", re.M)


def pick_monday(argv) -> date:
    if len(argv) > 1:
        d = date.fromisoformat(argv[1])
    else:
        today = date.today()
        d = today - timedelta(days=today.weekday() + 7)  # 上一个周一
    if d.weekday() != 0:
        sys.exit(f"{d} 不是周一；请传周一日期")
    return d


def main():
    monday = pick_monday(sys.argv)
    year = monday.year
    workdays = [monday + timedelta(days=i) for i in range(5)]
    text = Path(CONFIG["progress_report"]).read_text(encoding="utf-8")

    titles = {}  # date -> 标题
    for m in DAY_RE.finditer(text):
        d1 = date(year, int(m.group(1)), int(m.group(2)))
        if m.group(3):  # 区间标题：区间内所有天都标记为存在但无独立标题
            d2 = date(year, int(m.group(3)), int(m.group(4)))
            d = d1
            while d <= d2:
                titles.setdefault(d, "")
                d += timedelta(days=1)
        else:
            titles[d1] = m.group(5) or ""

    days, missing = [], []
    for d in workdays:
        title = titles.get(d, "")
        if not title:
            missing.append(str(d))
            title = "TODO(人工补充：该日在 PROGRESS_REPORT.md 无独立标题——现场/传输/会议等非提交工作也要写)"
        days.append({
            "date": str(d),
            "project_type": CONFIG["project_type"],
            "project": CONFIG["project"],
            "status": CONFIG["status"],
            "hours": CONFIG["hours"],
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
        "name": CONFIG["name"],
        "project": CONFIG["project"],
        "dept_goal": CONFIG["dept_goal"],
        "week": {"start": str(monday), "end": str(monday + timedelta(days=6))},
        "days": days,
        "special_note": "",
        "summary": {
            "tasks": f"TODO(参考 Week 标题: {week_title})",
            "task_type": CONFIG["project_type"],
            "deliverables": "TODO",
            "done": "TODO(编号列表，逐任务/交付物说明完成状态)",
            "remark": "",
        },
        "next_week": {"tasks": "TODO", "task_type": CONFIG["project_type"], "deliverables": "TODO"},
    }

    out = HERE / "weeks" / f"week_report_{monday.strftime('%Y%m%d')}.json"
    if out.exists():
        sys.exit(f"{out} 已存在，拒绝覆盖（如需重生成先手动删除）")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"草稿已生成: {out}")
    if missing:
        print(f"待人工补齐的日期: {', '.join(missing)}", file=sys.stderr)
    print("下一步: 人工审改 json → python3 gen_attachment.py <json> → python3 print_form_rows.py <json>")


if __name__ == "__main__":
    main()
