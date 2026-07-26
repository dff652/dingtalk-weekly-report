#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""week_report.json → 「YYYYMMDD-YYYYMMDD本周工作总结与下周计划.xlsx」附件。

用法: python3 gen_attachment.py weeks/week_report_20260713.json [-o output/]
任务类型枚举来自 week_report.json 的 vocabulary。
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dtwr_common import workdir
from xlsxlite import Workbook
from dtwr_validation import ValidationError, validate_report

NOTE = """注：

1. 任务与交付物尽量量化，并说明完成状态。
2. 备注用于说明未完成项、风险或需要协调的事项。
3. 实际填写要求以所在组织的周报制度为准。"""

THIS_HEADERS = ["序号", "姓名", "周任务", "任务类型", "周交付物", "完成情况", "备注", "所关联的项目/活动", "所关联的部门目标"]
NEXT_HEADERS = ["序号", "姓名", "周任务", "任务类型", "周交付物", "所关联的项目/活动", "所关联的部门目标"]
def compact(d: str) -> str:
    return d.replace("-", "")


def est_height(*texts, base=14.5, minimum=20):
    lines = max((str(t).count("\n") + 1) for t in texts if t is not None)
    return max(minimum, round(lines * base + 6))


def build(report: dict, out_dir: Path) -> Path:
    week = report["week"]
    monday = date.fromisoformat(week["start"])
    friday = monday + timedelta(days=4)
    nxt_monday = monday + timedelta(days=7)
    nxt_friday = nxt_monday + timedelta(days=4)

    s = report["summary"]
    n = report["next_week"]
    task_types = report["vocabulary"]["attachment_task_types"]
    default_task_type = task_types[0]

    wb = Workbook()
    sh = wb.add_sheet("周工作总结与计划")
    widths = {1: 6, 2: 10, 3: 42, 4: 12, 5: 34, 6: 56, 7: 14, 8: 34, 9: 22}
    sh.col_widths.update(widths)

    r = 1
    sh.cell(r, 1, f"本周工作总结 周：{compact(str(monday))}-{compact(str(friday))}", style=3)
    sh.merge(f"A{r}:I{r}")
    r += 1
    for c, h in enumerate(THIS_HEADERS, 1):
        sh.cell(r, c, h, style=2)
    r += 1
    attach_project = report.get("attach_project", report.get("project", ""))
    row_vals = [1, report.get("name", ""), s["tasks"], s.get("task_type", default_task_type),
                s["deliverables"], s["done"], s.get("remark", ""),
                attach_project, report.get("dept_goal", "")]
    for c, v in enumerate(row_vals, 1):
        sh.cell(r, c, v, style=1)
    sh.row_heights[r] = est_height(s["tasks"], s["deliverables"], s["done"])
    r += 2
    sh.cell(r, 1, NOTE, style=0)
    sh.merge(f"A{r}:I{r}")
    sh.row_heights[r] = est_height(NOTE)
    r += 2
    sh.cell(r, 1, f"下周工作总结 周：{compact(str(nxt_monday))}-{compact(str(nxt_friday))}", style=3)
    sh.merge(f"A{r}:G{r}")
    r += 1
    for c, h in enumerate(NEXT_HEADERS, 1):
        sh.cell(r, c, h, style=2)
    r += 1
    nxt_vals = [1, report.get("name", ""), n["tasks"], n.get("task_type", default_task_type),
                n["deliverables"], attach_project, report.get("dept_goal", "")]
    for c, v in enumerate(nxt_vals, 1):
        sh.cell(r, c, v, style=1)
    sh.row_heights[r] = est_height(n["tasks"], n["deliverables"])

    sh2 = wb.add_sheet("说明")
    sh2.col_widths.update({1: 12, 2: 12, 3: 12, 4: 12, 5: 12, 6: 12})
    sh2.cell(2, 1, "任务类型：", style=3)
    for c, t in enumerate(task_types, 2):
        sh2.cell(2, c, t, style=1)

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{compact(str(monday))}-{compact(str(friday))}本周工作总结与下周计划.xlsx"
    wb.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report_json")
    # 默认落 $WORK/output，与 fill_form 读取的位置同源；
    # 原先用 cwd 相对 "output"，跑错目录就会产出 fill_form 找不到的附件。
    ap.add_argument("-o", "--out-dir", default=None)
    args = ap.parse_args()
    report = json.loads(Path(args.report_json).read_text(encoding="utf-8"))
    try:
        validate_report(report)
    except ValidationError as exc:
        sys.exit(str(exc))
    out_dir = Path(args.out_dir) if args.out_dir else workdir() / "output"
    out = build(report, out_dir)
    print(f"已生成: {out}")


if __name__ == "__main__":
    main()
