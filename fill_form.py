#!/usr/bin/env python3
"""P2（路径 B）：Playwright 半自动填写钉钉宜搭「报工周报」。

无显示器服务器工作流：
  1) 首次登录（扫码）:  .venv/bin/python fill_form.py --login
     浏览器 headless 打开表单页 → 登录二维码持续截图到 output/shots/login.png
     → 在 VSCode 里打开该图，用手机钉钉扫码 → 登录态存 ~/.config/dtwr/state.json
  2) 填表:            .venv/bin/python fill_form.py weeks/week_report_20260713.json
     自动填开始日期/附件/特殊说明/工作详情逐行 → 全页截图到 output/shots/
     → 终端输入 yes 才点「提交」（或加 --submit 跳过确认）。任何一步失败截图留证。

⚠️ 实验性：宜搭 DOM 选择器以「字段 label 文本」定位，首次联调需真表单页面配合微调；
   config.json 里 form_url 必填（钉钉里复制「报工周报-新增」链接）。
"""
import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
STATE = Path.home() / ".config" / "dtwr" / "state.json"
SHOTS = HERE / "output" / "shots"
WEEKDAY = "一二三四五六日"


def log(msg):
    print(f"[fill_form] {msg}", flush=True)


def shot(page, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    p = SHOTS / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    log(f"截图: {p}")
    return p


def form_url():
    url = CONFIG.get("form_url", "")
    if not url:
        sys.exit("config.json 缺 form_url（钉钉里打开「报工周报-新增」→ 复制链接填入）")
    return url


def do_login():
    """headless 扫码登录：二维码持续截图，登录成功后保存 storageState。"""
    STATE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(form_url(), wait_until="domcontentloaded")
        log("等待扫码：请在 VSCode 打开 output/shots/login.png，用手机钉钉扫码并确认")
        deadline = time.time() + 300
        while time.time() < deadline:
            shot(page, "login")
            # 登录成功判据：跳离登录域，回到宜搭表单页
            if "login" not in page.url and ("aliwork" in page.url or "yida" in page.url):
                # 再等表单渲染，确认不是又被重定向回登录
                page.wait_for_timeout(3000)
                if "login" not in page.url:
                    break
            page.wait_for_timeout(2500)
        else:
            shot(page, "login-timeout")
            sys.exit("300s 内未完成扫码登录；重跑 --login")
        ctx.storage_state(path=str(STATE))
        STATE.chmod(0o600)
        shot(page, "login-ok")
        log(f"登录态已保存: {STATE}")
        browser.close()


def item(page, label):
    """按字段 label 文本定位宜搭表单项容器（兜底若干种 DOM 结构）。"""
    for sel in (
        f'div.next-form-item:has(label:has-text("{label}"))',
        f'div[class*="form-item"]:has(label:has-text("{label}"))',
        f'div[class*="field"]:has(:text("{label}"))',
    ):
        loc = page.locator(sel).first
        if loc.count():
            return loc
    raise RuntimeError(f"找不到字段: {label}")


def pick_select(scope, value, page):
    """点开 next-select 下拉并按文本选值。"""
    scope.locator('[class*="next-select"]').first.click()
    page.locator(f'li[class*="next-menu-item"]:has-text("{value}")').first.click()


def fill_date(scope, page, value):
    inp = scope.locator("input").first
    inp.click()
    inp.fill(value)
    page.keyboard.press("Enter")


def do_fill(report_path, auto_submit):
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    w = report["week"]
    monday = w["start"]
    attach = HERE / "output" / (
        monday.replace("-", "") + "-" +
        # 周五
        __import__("datetime").date.fromordinal(date.fromisoformat(monday).toordinal() + 4).strftime("%Y%m%d")
        + "本周工作总结与下周计划.xlsx")
    if not attach.exists():
        sys.exit(f"附件不存在: {attach}（先跑 gen_attachment.py）")
    if not STATE.exists():
        sys.exit("无登录态，先跑: fill_form.py --login")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=str(STATE), viewport={"width": 1600, "height": 1000})
        page = ctx.new_page()
        try:
            page.goto(form_url(), wait_until="networkidle")
            if "login" in page.url:
                shot(page, "state-expired")
                sys.exit("登录态过期，重跑 --login")
            shot(page, "00-form-open")

            log("填报工开始日期")
            fill_date(item(page, "报工开始日期"), page, monday)

            log("上传附件")
            item(page, "工作计划及完成情况").locator('input[type="file"]').first.set_input_files(str(attach))
            page.wait_for_timeout(3000)  # 等上传完成

            note = report.get("special_note", "")
            if note:
                log("填特殊情况说明")
                item(page, "本周特殊情况说明").locator("textarea,input").first.fill(note)

            log(f"工作详情 {len(report['days'])} 行")
            for i, d in enumerate(report["days"], 1):
                page.get_by_role("button", name="新增").last.click()
                page.wait_for_timeout(800)
                row = page.locator('tr[class*="next-table-row"], div[class*="table-row"]').last
                log(f"  行{i}: {d['date']} {d['status']} {d['hours']}h")
                # 报工日期（行内第一个 input）
                fill_date_input = row.locator("input").first
                fill_date_input.click()
                fill_date_input.fill(d["date"])
                page.keyboard.press("Enter")
                # 项目类型（行内第一个 select）
                if row.locator('[class*="next-select"]').count():
                    pick_select(row, d["project_type"], page)
                if d.get("project"):
                    sel2 = row.locator('[class*="next-select"]').nth(1)
                    sel2.click()
                    page.keyboard.type(d["project"][:12])
                    page.wait_for_timeout(800)
                    page.locator(f'li[class*="next-menu-item"]:has-text("{d["project"][:12]}")').first.click()
                # 工作状态
                st = row.locator('[class*="next-select"]').last
                st.click()
                page.locator(f'li[class*="next-menu-item"]:has-text("{d["status"]}")').first.click()
                # 工时 + 内容
                row.locator('input[type="number"], input[class*="number"]').last.fill(str(d["hours"]))
                row.locator("textarea").last.fill(d.get("content", ""))
                shot(page, f"10-row-{i:02d}")

            shot(page, "20-filled-review")
            log("已填完。请查看 output/shots/20-filled-review.png 核对")
            if not auto_submit:
                ans = input("确认提交? 输入 yes 提交，其它任意键放弃: ").strip().lower()
                if ans != "yes":
                    log("已放弃提交（表单未保存）")
                    return
            page.get_by_role("button", name="提交").first.click()
            page.wait_for_timeout(4000)
            shot(page, "30-submitted")
            log("已点提交，看 30-submitted.png 确认结果")
        except (PWTimeout, RuntimeError) as e:
            shot(page, "99-error")
            sys.exit(f"失败: {e}（现场截图 output/shots/99-error.png，把截图发给 Claude 联调选择器）")
        finally:
            browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report_json", nargs="?")
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--submit", action="store_true", help="跳过终端确认直接提交")
    args = ap.parse_args()
    if args.login:
        do_login()
    elif args.report_json:
        do_fill(args.report_json, args.submit)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
