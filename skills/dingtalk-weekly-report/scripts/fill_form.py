#!/usr/bin/env python3
"""P2（路径 B）：Playwright 半自动填写钉钉「报工周报」（氚云 H3yun 表单）。

真机已验证（2026-07-21，worker dev box headless chromium）：
  登录态(token 链接免扫码)/新增打开/报工开始日期(结束日期联动)/子表行日期(星期联动)/
  项目类型与工作状态下拉选中/工时(系统字段联动)/主要工作内容 —— 全部走通。
  「项目/产品名称」关联下拉暂不出数据（前端不发数据查询，原因待与手工行为对比），
  填不上时告警跳过，由人工在草稿里补。

用法：
  登录(免扫码):   .venv/bin/python fill_form.py --login-url '<打印内部二维码解出的 entry/auth 链接>'
  登录(扫码):     .venv/bin/python fill_form.py --login   # 二维码截图 output/shots/login.png
  填表:           .venv/bin/python fill_form.py weeks/week_report_20260713.json
                  默认填完截图停下；--draft 点「暂存」（推荐：钉钉里人工核对草稿后再提交）；
                  --submit 点「提交」。
  诊断:           .venv/bin/python fill_form.py --dump
"""
import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dtwr_common import workdir

WORK = workdir()
CONFIG = json.loads((WORK / "config.json").read_text(encoding="utf-8"))
STATE = Path.home() / ".config" / "dtwr" / "state.json"
SHOTS = WORK / "output" / "shots"

SUBGRID_ID = "2ee34a58f62e4c81b0076a2a3623a4aa"   # 工作详情子表（见 FIELDS.md）
SUB = f'[id="{SUBGRID_ID}"]'
F = {  # 字段 id → 控件 DOM id（氚云直接用字段编码做 id）
    "start_date": "#F0000001",
    "attach": "#F0000062",
    "note": "#F0000068",
    "row_date": "#F0000003",
    "row_type": "#F0000005",
    "row_project": "#F0000041",
    "row_status": "#F0000004",
    "row_hours": "#F0000012",
    "row_content": "#F0000009",
}


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
        sys.exit("缺表单 URL：config.json 填 form_url，或 --url 传入")
    return url


def is_mock(url):
    return url.startswith("file://")


# ---------------- 登录 ----------------

def do_login_url(auth_url):
    """带 token 的一次性登录链接（打印内部二维码解出，48h 有效）直接建立登录态，免扫码。"""
    STATE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1700, "height": 1100})
        page = ctx.new_page()
        page.goto(auth_url, wait_until="domcontentloaded")
        page.wait_for_timeout(6000)
        shot(page, "login-url-landed")
        if "entry/auth" in page.url or "login" in page.url.lower():
            sys.exit(f"登录链接未完成跳转（现在在 {page.url}），token 可能过期；重新打印二维码取新链接")
        ctx.storage_state(path=str(STATE))
        STATE.chmod(0o600)
        log(f"登录态已保存: {STATE}")
        browser.close()


def do_login(url):
    STATE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        log("等待扫码：VSCode 打开 output/shots/login.png，手机钉钉扫码确认（5 分钟内）")
        deadline = time.time() + 300
        while time.time() < deadline:
            shot(page, "login")
            if "login" not in page.url.lower() and "h3yun" in page.url:
                page.wait_for_timeout(3000)
                if "login" not in page.url.lower():
                    ctx.storage_state(path=str(STATE))
                    STATE.chmod(0o600)
                    shot(page, "login-ok")
                    log(f"登录态已保存: {STATE}")
                    browser.close()
                    return
            page.wait_for_timeout(2500)
        shot(page, "login-timeout")
        sys.exit("300s 内未完成扫码登录；重跑 --login")


# ---------------- 表单定位 ----------------

def open_new_form(page, url, mock):
    """打开列表页→点新增→返回表单所在 frame（真机=FormAdapter iframe；mock=主 frame）。"""
    page.goto(url, wait_until="domcontentloaded" if mock else "networkidle")
    if mock:
        return page.main_frame
    if "login" in page.url.lower():
        shot(page, "state-expired")
        sys.exit("登录态过期，重跑 --login / --login-url")
    page.get_by_text("新增", exact=False).first.click()
    for _ in range(30):
        page.wait_for_timeout(1000)
        fr = next((f for f in page.frames if "FormAdapter" in f.url), None)
        if fr and fr.get_by_text("报工开始日期").count():
            page.wait_for_timeout(1500)
            return fr
    shot(page, "form-not-rendered")
    sys.exit("30s 内表单未渲染（FormAdapter frame 无字段）；看 form-not-rendered.png")


def fill_ant_date(fr, page, scope, value):
    """ant-calendar readonly input：点开 → 面板输入框敲日期 → Enter。"""
    scope.locator("input").first.click()
    page.wait_for_timeout(600)
    cal = fr.locator(".ant-calendar-input")
    if not cal.count():
        raise RuntimeError("日期面板未弹出（.ant-calendar-input 不存在）")
    cal.first.fill(value)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)


def pick_dropdown(fr, page, scope, value, required=True):
    """氚云 h3-dropdown：点开控件 → 按选项文本精确点选。

    同名选项会以隐藏 li 残留在此前行的菜单里（ant-select 菜单不销毁），
    必须从后往前找**可见**的那个命中项。
    """
    scope.click()
    page.wait_for_timeout(1000)
    opt = fr.get_by_text(value, exact=True)
    for k in range(opt.count() - 1, -1, -1):
        el = opt.nth(k)
        if el.is_visible():
            el.click()
            page.wait_for_timeout(500)
            return True
    page.keyboard.press("Escape")
    if required:
        raise RuntimeError(f"下拉无可见选项「{value}」")
    return False


# ---------------- 填表 ----------------

def attach_path(monday_str):
    monday = date.fromisoformat(monday_str)
    friday = monday + timedelta(days=4)
    return WORK / "output" / (
        f"{monday.strftime('%Y%m%d')}-{friday.strftime('%Y%m%d')}本周工作总结与下周计划.xlsx")


def do_fill(report_path, url, action):
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    w = report["week"]
    attach = attach_path(w["start"])
    if not attach.exists():
        sys.exit(f"附件不存在: {attach}（先跑 gen_attachment.py）")
    mock = is_mock(url)
    if not mock and not STATE.exists():
        sys.exit("无登录态，先跑: fill_form.py --login / --login-url")

    warnings = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            storage_state=None if mock else str(STATE),
            viewport={"width": 1700, "height": 1100})
        page = ctx.new_page()
        try:
            fr = open_new_form(page, url, mock)
            shot(page, "00-form-open")

            log(f"报工开始日期 {w['start']}")
            fill_ant_date(fr, page, fr.locator(F["start_date"]), w["start"])

            log(f"上传附件 {attach.name}")
            fr.locator(f'{F["attach"]} input[type="file"], input[type="file"]').first.set_input_files(str(attach))
            page.wait_for_timeout(500 if mock else 4000)

            note = report.get("special_note", "")
            if note:
                log("特殊情况说明")
                fr.locator(f'{F["note"]} textarea, {F["note"]} input').first.fill(note)

            log(f"工作详情 {len(report['days'])} 行")
            # 只取外层行：行内滚动容器与行同名 .subgrid-sheet__row，直匹配会翻倍并覆盖上一行
            rows = fr.locator(f"{SUB} .ant-spin-container > .subgrid-sheet__row")
            for i, d in enumerate(report["days"]):
                if i >= rows.count():  # 首行表单自带，后续行点「新增」并确认行数真的涨了
                    for attempt in range(3):
                        fr.locator(SUB).get_by_text("新增", exact=False).first.click()
                        page.wait_for_timeout(300 if mock else 1200)
                        if rows.count() >= i + 1:
                            break
                    else:
                        raise RuntimeError(f"点「新增」3 次后子表仍只有 {rows.count()} 行（期望 ≥{i+1}）")
                row = rows.nth(i)
                log(f"  行{i+1}: {d['date']} {d['status']} {d['hours']}h")
                fill_ant_date(fr, page, row.locator(F["row_date"]), d["date"])
                pick_dropdown(fr, page, row.locator(F["row_type"]).first, d["project_type"])
                if d.get("project"):
                    ok = pick_dropdown(fr, page, row.locator(F["row_project"]).first,
                                       d["project"], required=False)
                    if not ok:
                        warnings.append(f"行{i+1} 项目/产品名称「{d['project']}」下拉无数据，已跳过（草稿里人工补）")
                pick_dropdown(fr, page, row.locator(F["row_status"]).first, d["status"])
                row.locator(f'{F["row_hours"]} input').first.fill(str(d["hours"]))
                content = d.get("content", "")
                if len(content) > 200:
                    warnings.append(f"行{i+1} 主要工作内容 {len(content)} 字超 200 上限，控件会截断——回 json 精简")
                row.locator(f'{F["row_content"]} textarea, {F["row_content"]} input').first.fill(content)

            shot(page, "20-filled-review")
            for msg in warnings:
                log(f"⚠ {msg}")
            log("已填完，核对 output/shots/20-filled-review.png")

            if action == "review":
                log("未保存（默认只填不存）。要落草稿加 --draft，直接提交加 --submit")
                return
            btn_name = "暂 存" if action == "draft" else "提 交"
            fr.get_by_text(btn_name, exact=True).first.click()
            page.wait_for_timeout(500 if mock else 4000)
            shot(page, "30-saved")
            if mock:
                print("MOCK_RESULT:", fr.locator("#result").inner_text())
            log(f"已点「{btn_name.replace(' ', '')}」，看 30-saved.png 确认结果")
        except (PWTimeout, RuntimeError) as e:
            shot(page, "99-error")
            sys.exit(f"失败: {e}（截图 output/shots/99-error.png 发给 Claude 联调）")
        finally:
            browser.close()


# ---------------- 会话保活 ----------------

def do_keepalive(url):
    """每日 cron 调用：带登录态访问列表页，回存刷新后的 cookie 让会话滚动续命。
    失效时 fail-loud（cron 日志可见），此时需要用户重新给「打印内部二维码」链接。"""
    if not STATE.exists():
        sys.exit("keepalive: 无登录态文件")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=str(STATE), viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(3000)
            if "login" in page.url.lower() or "entry/auth" in page.url:
                sys.exit(f"keepalive: 会话已失效（落在 {page.url[:80]}）——需重新提供打印内部二维码链接")
            if not page.get_by_text("报工周报").count():
                sys.exit("keepalive: 页面未出现「报工周报」，会话状态可疑")
            ctx.storage_state(path=str(STATE))
            STATE.chmod(0o600)
            print(f"keepalive OK: {time.strftime('%F %T')} 会话有效，cookie 已回存")
        finally:
            browser.close()


# ---------------- 诊断 ----------------

def do_dump(url):
    mock = is_mock(url)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=None if mock or not STATE.exists() else str(STATE),
                                  viewport={"width": 1700, "height": 1100})
        page = ctx.new_page()
        fr = open_new_form(page, url, mock)
        SHOTS.mkdir(parents=True, exist_ok=True)
        (SHOTS / "dump.html").write_text(fr.content(), encoding="utf-8")
        shot(page, "dump")
        found = {k: fr.locator(v).count() for k, v in F.items()}
        log(f"URL: {page.url}")
        log(f"字段命中: {found}")
        log("已存 output/shots/dump.html + dump.png")
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report_json", nargs="?")
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--login-url", help="带 token 的一次性登录链接（免扫码；token 勿入 git）")
    ap.add_argument("--dump", action="store_true")
    ap.add_argument("--keepalive", action="store_true", help="访问列表页续会话并回存 cookie（cron 用）")
    ap.add_argument("--url", help="覆盖 config.form_url（联调/仿真用）")
    ap.add_argument("--draft", action="store_true", help="填完点「暂存」落草稿（推荐）")
    ap.add_argument("--submit", action="store_true", help="填完直接点「提交」")
    args = ap.parse_args()
    if args.login_url:
        do_login_url(args.login_url)
    elif args.login:
        do_login(resolve_url(args))
    elif args.keepalive:
        do_keepalive(resolve_url(args))
    elif args.dump:
        do_dump(resolve_url(args))
    elif args.report_json:
        action = "submit" if args.submit else ("draft" if args.draft else "review")
        do_fill(args.report_json, resolve_url(args), action)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
