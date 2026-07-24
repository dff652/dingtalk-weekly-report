#!/usr/bin/env python3
"""week_report.json → 钉钉「报工周报」表单粘贴块（路径 C 的人工填表助手）。

用法: python3 print_form_rows.py weeks/week_report_20260713.json
days 是「行」列表（同一天可多行：站会/开发/临时会议/休假），字段与表单工作详情逐列对应。
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dtwr_validation import ValidationError, validate_report

WEEKDAY = "一二三四五六日"


def main():
    if len(sys.argv) != 2:
        sys.exit("用法: python3 print_form_rows.py weeks/week_report_YYYYMMDD.json")
    r = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    try:
        validate_report(r)
    except ValidationError as exc:
        sys.exit(str(exc))
    w = r["week"]

    monday = date.fromisoformat(w["start"])
    friday = monday + timedelta(days=4)
    print("=" * 72)
    print(f"报工周报 · {w['start']} ~ {w['end']}")
    print("=" * 72)
    print(f"报工开始日期: {w['start']}   (结束日期表单自动带出 {w['end']})")
    print(f"附件: output/{monday.strftime('%Y%m%d')}-{friday.strftime('%Y%m%d')}本周工作总结与下周计划.xlsx")
    note = r.get("special_note", "")
    print(f"本周特殊情况说明: {note if note else '(空，不填)'}")
    print()
    print("工作详情（逐行「新增」，同一天可多行；列: 报工日期|项目类型|项目/产品名称|工作状态|工时|主要工作内容）")
    print("-" * 72)
    cur = None
    for i, d in enumerate(r["days"], 1):
        dt = date.fromisoformat(d["date"])
        if d["date"] != cur:
            cur = d["date"]
            print(f"—— {d['date']} 星期{WEEKDAY[dt.weekday()]} ——")
        proj = d.get("project", "")
        print(f"[{i}] {d['project_type']} | {d['status']} | {d['hours']}h"
              + (f" | 项目: {proj}" if proj else " | 项目: (空)"))
        if d.get("content"):
            print(f"    内容: {d['content']}")
    print()
    total = sum(d["hours"] for d in r["days"])
    print(f"合计工时 {total}h（表单系统字段自动统计，此处仅核对）")
    print("提交前检查: ① 周一 17:00 前 ② 附件已传 ③ 休假日状态「休假」8h ④ 周末未报")


if __name__ == "__main__":
    main()
