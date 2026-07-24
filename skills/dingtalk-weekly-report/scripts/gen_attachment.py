#!/usr/bin/env python3
"""week_report.json → 「YYYYMMDD-YYYYMMDD本周工作总结与下周计划.xlsx」附件。

用法: python3 gen_attachment.py weeks/week_report_20260713.json [-o output/]
模板逆向自 /home/team/test 示例文件；任务类型枚举见「说明」sheet。
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xlsxlite import Workbook
from dtwr_fields import ATTACHMENT_TASK_TYPES
from dtwr_validation import ValidationError, validate_report

NOTE = """注：

1. 任务务必细化，尽量量化
 - 比如开发特征提取算法，总共10类，本周开发3类，这个开发了的算法成熟度达到什么程度等
 - 比如调研文档的大致框架是什么，调研后就可以开发么，还是用来探索技术路径，怎么评估调研文档的调研质量，需要提炼出哪些点
2. 在【周交付物】一栏，陈述清楚对应任务的目的、预期效果、产出后下一步对接人/可以启动的任务。如，代码最终要达到什么效果，这个流程是不是可以直接对接到开发，原型更新达到UI可以直接出图、软件可以开发的程度，等等
3. 【完成情况】需要对每个任务、交付物进行完成状态说明
4. 【备注】里主要澄清没有完成任务/交付物的原因"""

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
    row_vals = [1, report.get("name", ""), s["tasks"], s.get("task_type", "产品研发"),
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
    nxt_vals = [1, report.get("name", ""), n["tasks"], n.get("task_type", "产品研发"),
                n["deliverables"], attach_project, report.get("dept_goal", "")]
    for c, v in enumerate(nxt_vals, 1):
        sh.cell(r, c, v, style=1)
    sh.row_heights[r] = est_height(n["tasks"], n["deliverables"])

    sh2 = wb.add_sheet("说明")
    sh2.col_widths.update({1: 12, 2: 12, 3: 12, 4: 12, 5: 12, 6: 12})
    sh2.cell(2, 1, "任务类型：", style=3)
    for c, t in enumerate(ATTACHMENT_TASK_TYPES, 2):
        sh2.cell(2, c, t, style=1)

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{compact(str(monday))}-{compact(str(friday))}本周工作总结与下周计划.xlsx"
    wb.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report_json")
    ap.add_argument("-o", "--out-dir", default="output")
    args = ap.parse_args()
    report = json.loads(Path(args.report_json).read_text(encoding="utf-8"))
    try:
        validate_report(report)
    except ValidationError as exc:
        sys.exit(str(exc))
    out = build(report, Path(args.out_dir))
    print(f"已生成: {out}")


if __name__ == "__main__":
    main()
