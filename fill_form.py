#!/usr/bin/env python3
"""P2（路径 B）：Playwright 半自动填写钉钉宜搭「报工周报」。

无显示器服务器工作流：
  1) 首次登录（扫码）:  .venv/bin/python fill_form.py --login
     浏览器 headless 打开表单页 → 登录二维码持续截图到 output/shots/login.png
     → 在 VSCode 里打开该图，用手机钉钉扫码 → 登录态存 ~/.config/dtwr/state.json
  2) 填表:            .venv/bin/python fill_form.py weeks/week_report_20260713.json
     自动填开始日期/附件/特殊说明/工作详情逐行 → 全页截图核对
     → 终端输入 yes 才点「提交」（或加 --submit 跳过确认）。任何一步失败截图留证。
  3) 诊断:            .venv/bin/python fill_form.py --dump
     保存表单页 HTML + 截图 + 识别到的字段清单，供选择器联调。

子表按「列头文本 → 列号」定位单元格（不猜 DOM 顺序）；本地仿真表单 e2e 见 tests/。
⚠️ 真实宜搭页面首轮联调仍可能要按 --dump/报错截图微调选择器。
"""
import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
STATE = Path.home() / ".config" / "dtwr" / "state.json"
SHOTS = HERE / "output" / "shots"

DETAIL_COLS = ["报工日期", "项目类型", "项目/产品名称", "工作状态", "工作时长", "主要工作内容"]


def log(msg):
    print(f"[fill_form] {msg}", flush=True)


def shot(page, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    p = SHOTS / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    return p


def resolve_url(args):
    url = args.url or CONFIG.get("form_url", "")
    if not url:
        sys.exit("缺表单 URL：config.json 填 form_url，或 --url 传入（钉钉里复制「报工周报-新增」链接）")
    return url


def is_mock(url):
    return url.startswith("file://")


# ---------------- 登录 ----------------

def do_login(url):
    STATE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        log("等待扫码：VSCode 打开 output/shots/login.png，用手机钉钉扫码并确认（5 分钟内）")
        deadline = time.time() + 300
        ok = False
        while time.time() < deadline:
            shot(page, "login")
            if "login" not in page.url and ("aliwork" in page.url or "yida" in page.url):
                page.wait_for_timeout(3000)
                if "login" not in page.url:
                    ok = True
                    break
            page.wait_for_timeout(2500)
        if not ok:
            shot(page, "login-timeout")
            sys.exit("300s 内未完成扫码登录；重跑 --login")
        ctx.storage_state(path=str(STATE))
        STATE.chmod(0o600)
        shot(page, "login-ok")
        log(f"登录态已保存: {STATE}")
        browser.close()


# ---------------- 页面操作原语 ----------------

def form_item(page, label):
    """按字段 label 文本定位表单项容器。"""
    for sel in (
        f'div.next-form-item:has(label:has-text("{label}"))',
        f'div[class*="form-item"]:has(label:has-text("{label}"))',
        f'div[class*="field"]:has(:text("{label}"))',
    ):
        loc = page.locator(sel).first
        if loc.count():
            return loc
    raise RuntimeError(f"找不到字段: {label}")


def detail_table(page):
    t = page.locator('table:has(th:has-text("报工日期"))').first
    if not t.count():
        raise RuntimeError("找不到工作详情子表（无「报工日期」列头的 table）")
    return t


def column_map(table):
    """列头文本(contains) → 列号。"""
    ths = table.locator("thead th")
    texts = [ths.nth(i).inner_text().strip() for i in range(ths.count())]
    cols = {}
    for want in DETAIL_COLS:
        for i, t in enumerate(texts):
            if want in t:
                cols[want] = i
                break
        else:
            raise RuntimeError(f"子表缺列: {want}（现有列头: {texts}）")
    return cols


def cell(row, cols, name):
    return row.locator("td").nth(cols[name])


def pick_select(scope, page, value, type_first=None):
    """点开下拉并按文本选值；type_first 给搜索型下拉先敲关键字。"""
    scope.locator('[class*="select"]').first.click()
    if type_first:
        page.keyboard.type(type_first)
        page.wait_for_timeout(600)
    key = (type_first or value)[:14]
    page.locator(f'li[class*="menu-item"]:has-text("{key}")').first.click()


def fill_input(scope, page, value, press_enter=False):
    inp = scope.locator("input").first
    inp.click()
    inp.fill(str(value))
    if press_enter:
        page.keyboard.press("Enter")


# ---------------- 填表 ----------------

def attach_path(monday_str):
    monday = date.fromisoformat(monday_str)
    friday = monday + timedelta(days=4)
    return HERE / "output" / (
        f"{monday.strftime('%Y%m%d')}-{friday.strftime('%Y%m%d')}本周工作总结与下周计划.xlsx")


def do_fill(report_path, url, auto_submit):
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    w = report["week"]
    attach = attach_path(w["start"])
    if not attach.exists():
        sys.exit(f"附件不存在: {attach}（先跑 gen_attachment.py）")
    mock = is_mock(url)
    if not mock and not STATE.exists():
        sys.exit("无登录态，先跑: fill_form.py --login")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            storage_state=None if mock else str(STATE),
            viewport={"width": 1600, "height": 1000})
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded" if mock else "networkidle")
            if not mock and "login" in page.url:
                shot(page, "state-expired")
                sys.exit("登录态过期，重跑 --login")
            shot(page, "00-form-open")

            log("填报工开始日期")
            fill_input(form_item(page, "报工开始日期"), page, w["start"], press_enter=True)

            log(f"上传附件 {attach.name}")
            form_item(page, "工作计划及完成情况").locator('input[type="file"]').first.set_input_files(str(attach))
            page.wait_for_timeout(500 if mock else 3000)

            note = report.get("special_note", "")
            if note:
                log("填特殊情况说明")
                form_item(page, "本周特殊情况说明").locator("textarea, input").first.fill(note)

            log(f"工作详情 {len(report['days'])} 行")
            table = detail_table(page)
            cols = column_map(table)
            for i, d in enumerate(report["days"], 1):
                page.get_by_role("button", name="新增").last.click()
                page.wait_for_timeout(200 if mock else 800)
                row = table.locator("tbody tr").last
                log(f"  行{i}: {d['date']} {d['status']} {d['hours']}h")
                fill_input(cell(row, cols, "报工日期"), page, d["date"], press_enter=True)
                pick_select(cell(row, cols, "项目类型"), page, d["project_type"])
                if d.get("project"):
                    pick_select(cell(row, cols, "项目/产品名称"), page, d["project"],
                                type_first=d["project"][:10])
                pick_select(cell(row, cols, "工作状态"), page, d["status"])
                fill_input(cell(row, cols, "工作时长"), page, d["hours"])
                cell(row, cols, "主要工作内容").locator("textarea, input").first.fill(d.get("content", ""))

            shot(page, "20-filled-review")
            log("已填完。核对 output/shots/20-filled-review.png")
            if not auto_submit:
                ans = input("确认提交? 输入 yes 提交，其它任意键放弃: ").strip().lower()
                if ans != "yes":
                    log("已放弃提交（表单未保存）")
                    return
            page.get_by_role("button", name="提交").first.click()
            page.wait_for_timeout(500 if mock else 4000)
            shot(page, "30-submitted")
            if mock:
                print("MOCK_RESULT:", page.locator("#result").inner_text())
            log("已点提交，看 30-submitted.png 确认结果")
        except (PWTimeout, RuntimeError) as e:
            shot(page, "99-error")
            sys.exit(f"失败: {e}（截图 output/shots/99-error.png，发给 Claude 联调选择器）")
        finally:
            browser.close()


# ---------------- 诊断 ----------------

def do_dump(url):
    mock = is_mock(url)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=None if mock or not STATE.exists() else str(STATE),
                                  viewport={"width": 1600, "height": 1000})
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded" if mock else "networkidle")
        page.wait_for_timeout(2000)
        SHOTS.mkdir(parents=True, exist_ok=True)
        (SHOTS / "dump.html").write_text(page.content(), encoding="utf-8")
        shot(page, "dump")
        labels = page.locator("label").all_inner_texts()
        log(f"URL: {page.url}")
        log(f"识别到 label: {[t.strip() for t in labels if t.strip()]}")
        log("已存 output/shots/dump.html + dump.png，发给 Claude 即可精调选择器")
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report_json", nargs="?")
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--dump", action="store_true", help="保存表单页 HTML/截图/字段清单供联调")
    ap.add_argument("--url", help="覆盖 config.form_url（联调/仿真用）")
    ap.add_argument("--submit", action="store_true", help="跳过终端确认直接提交")
    args = ap.parse_args()
    if args.login:
        do_login(resolve_url(args))
    elif args.dump:
        do_dump(resolve_url(args))
    elif args.report_json:
        do_fill(args.report_json, resolve_url(args), args.submit)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
