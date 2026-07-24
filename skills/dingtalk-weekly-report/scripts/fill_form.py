#!/usr/bin/env python3
"""P2（路径 B）：Playwright 半自动填写钉钉「报工周报」（氚云 H3yun 表单）。

真机已验证（2026-07-21，worker dev box headless chromium）：
  登录态(token 链接免扫码)/新增打开/报工开始日期(结束日期联动)/子表行日期(星期联动)/
  项目类型与工作状态下拉选中/工时(系统字段联动)/主要工作内容 —— 全部走通。
  「项目/产品名称」关联下拉必须成功选中；失败时阻断，不保存不完整草稿。

用法：
  登录(免扫码):   .venv/bin/python fill_form.py --login-url '<打印内部二维码解出的 entry/auth 链接>'
  登录(扫码):     .venv/bin/python fill_form.py --login   # 二维码截图 output/shots/login.png
  填表:           .venv/bin/python fill_form.py weeks/week_report_20260713.json
                  默认填完截图停下；人工确认内容并检查旧草稿后，
                  --draft --confirmed 点「暂存」；本工具不提供提交能力。
  诊断:           .venv/bin/python fill_form.py --dump
"""
import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dtwr_common import require_owned, workdir
from dtwr_validation import ValidationError, validate_config, validate_report

WORK = None
CONFIG = {}
STATE = Path.home() / ".config" / "dtwr" / "state.json"
SHOTS = None

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


def init_runtime():
    global WORK, CONFIG, SHOTS
    WORK = workdir()
    CONFIG = json.loads((WORK / "config.json").read_text(encoding="utf-8"))
    SHOTS = WORK / "output" / "shots"


def validate_form_url(url):
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return
    if parsed.scheme != "https" or not (
            parsed.hostname == "h3yun.com"
            or (parsed.hostname or "").endswith(".h3yun.com")):
        raise ValueError("表单 URL 必须是 https://*.h3yun.com；file:// 仅用于本地仿真")


def validate_auth_url(auth_url):
    parsed = urlparse(auth_url)
    if (parsed.scheme != "https"
            or not (parsed.hostname == "h3yun.com"
                    or (parsed.hostname or "").endswith(".h3yun.com"))
            or "/entry/auth" not in parsed.path
            or not parse_qs(parsed.query).get("token")):
        raise ValueError("--login-url 必须是含 token 的 https://*.h3yun.com/entry/auth 链接")


def resolve_url(args):
    url = args.url or CONFIG.get("form_url", "")
    if not url:
        sys.exit("缺表单 URL：config.json 填 form_url，或 --url 传入")
    try:
        validate_form_url(url)
    except ValueError as exc:
        sys.exit(str(exc))
    return url


def is_mock(url):
    return url.startswith("file://")


# ---------------- 登录 ----------------

def ensure_state_owner():
    require_owned(STATE.parent, "登录态目录")
    require_owned(STATE, "登录态文件")


def do_login_url(auth_url):
    """带 token 的一次性登录链接（打印内部二维码解出，48h 有效）直接建立登录态，免扫码。"""
    try:
        validate_auth_url(auth_url)
    except ValueError as exc:
        sys.exit(str(exc))
    ensure_state_owner()
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
    ensure_state_owner()
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


def pick_dropdown(fr, page, scope, value):
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
            return
    page.keyboard.press("Escape")
    raise RuntimeError(f"下拉无可见选项「{value}」")


# ---------------- 填表 ----------------

def attach_path(monday_str):
    monday = date.fromisoformat(monday_str)
    friday = monday + timedelta(days=4)
    return WORK / "output" / (
        f"{monday.strftime('%Y%m%d')}-{friday.strftime('%Y%m%d')}本周工作总结与下周计划.xlsx")


def verify_draft_saved(fr, page, mock):
    if mock:
        result = json.loads(fr.locator("#result").inner_text())
        if result.get("kind") != "draft":
            raise RuntimeError(f"仿真表单动作错误: {result.get('kind')!r}")
        print("MOCK_RESULT:", json.dumps(result, ensure_ascii=False))
        return

    error_selector = (
        ".ant-message-error, .ant-notification-notice-error, "
        ".has-error .ant-form-explain"
    )
    success_selector = ".ant-message-success, .ant-notification-notice-success"
    for frame in page.frames:
        errors = frame.locator(error_selector)
        for i in range(errors.count()):
            if errors.nth(i).is_visible():
                raise RuntimeError(f"暂存失败: {errors.nth(i).inner_text().strip()}")
        success = frame.locator(success_selector)
        if any(success.nth(i).is_visible() for i in range(success.count())):
            return
        for text in ("暂存成功", "保存成功", "操作成功"):
            matches = frame.get_by_text(text, exact=False)
            if any(matches.nth(i).is_visible() for i in range(matches.count())):
                return
    raise RuntimeError("点击暂存后未检测到可见的成功提示，不能确认草稿已保存")


def do_fill(report_path, url, save_draft):
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    try:
        validate_report(report)
    except ValidationError as exc:
        sys.exit(str(exc))
    w = report["week"]
    attach = attach_path(w["start"])
    if not attach.exists():
        sys.exit(f"附件不存在: {attach}（先跑 gen_attachment.py）")
    mock = is_mock(url)
    if not mock and not STATE.exists():
        sys.exit("无登录态，先跑: fill_form.py --login / --login-url")

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
                    pick_dropdown(fr, page, row.locator(F["row_project"]).first,
                                  d["project"])
                pick_dropdown(fr, page, row.locator(F["row_status"]).first, d["status"])
                row.locator(f'{F["row_hours"]} input').first.fill(str(d["hours"]))
                content = d.get("content", "")
                row.locator(f'{F["row_content"]} textarea, {F["row_content"]} input').first.fill(content)

            shot(page, "20-filled-review")
            log("已填完，核对 output/shots/20-filled-review.png")

            if not save_draft:
                log("未保存（默认只填不存）。人工确认内容并检查旧草稿后，加 --draft --confirmed")
                return
            btn_name = "暂 存"
            fr.get_by_text(btn_name, exact=True).first.click()
            page.wait_for_timeout(500 if mock else 4000)
            verify_draft_saved(fr, page, mock)
            shot(page, "30-saved")
            log("草稿暂存成功，见 30-saved.png")
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
    ensure_state_owner()
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
    ap.add_argument("--draft", action="store_true", help="填完点「暂存」落草稿")
    ap.add_argument("--confirmed", action="store_true",
                    help="确认内容已经人工审核、同周旧草稿已经检查（与 --draft 同用）")
    args = ap.parse_args()
    if args.draft and not args.confirmed:
        ap.error("--draft 必须同时提供 --confirmed，表示已完成人审和同周旧草稿检查")
    if args.confirmed and not args.draft:
        ap.error("--confirmed 只能与 --draft 同用")
    if not any((args.login_url, args.login, args.keepalive, args.dump, args.report_json)):
        ap.print_help()
        return
    init_runtime()
    try:
        validate_config(CONFIG)
    except ValidationError as exc:
        sys.exit(str(exc))
    if args.login_url:
        do_login_url(args.login_url)
    elif args.login:
        do_login(resolve_url(args))
    elif args.keepalive:
        do_keepalive(resolve_url(args))
    elif args.dump:
        do_dump(resolve_url(args))
    elif args.report_json:
        do_fill(args.report_json, resolve_url(args), args.draft)


if __name__ == "__main__":
    main()
