#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""P2（路径 B）：Playwright 半自动填写钉钉「报工周报」（氚云 H3yun 表单）。

真机已验证（2026-07-21，worker dev box headless chromium）：
  登录态(token 链接免扫码)/新增打开/报工开始日期(结束日期联动)/子表行日期(星期联动)/
  项目类型与工作状态下拉选中/工时(系统字段联动)/主要工作内容 —— 全部走通。
  「项目/产品名称」关联下拉必须成功选中；失败时阻断，不保存不完整草稿。

用法：
  登录(首选扫码): .venv/bin/python fill_form.py --login
  登录(URL):      .venv/bin/python fill_form.py --login-url  # 用户在本机终端隐藏输入
  填表:           .venv/bin/python fill_form.py weeks/week_report_20260713.json
                  默认填完截图停下；人工确认内容并检查旧草稿后，
                  --draft --confirmed 点「暂存」；本工具不提供提交能力。
  诊断:           .venv/bin/python fill_form.py --dump
"""
import argparse
import json
import re
import sys
import time
from datetime import date, timedelta
from getpass import getpass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dtwr_common import dtwr_config_dir, require_owned, workdir
from dtwr_discover import analyse, propose_fields
from dtwr_validation import (
    ValidationError,
    validate_config,
    validate_report,
    validate_report_against_config,
)

WORK = None
CONFIG = {}
STATE = dtwr_config_dir() / "state.json"
SHOTS = None
SUB = None
F = {}
RUN_LOG = None

_URL_RE = re.compile(r"https?://([^\s/]+)\S*")


def redact(msg: str) -> str:
    """URL 只留 scheme+host。

    运行日志会被用户附到 issue 或发给协助排查的人，而表单 URL 带组织租户标识
    （见 SECURITY.md「报告安全问题」）。屏幕输出保留原样便于当场排查，落盘的一律脱敏。
    """
    return _URL_RE.sub(r"https://\1/…", msg)


def log(msg):
    print(f"[fill_form] {msg}", flush=True)
    if RUN_LOG is None:
        return
    try:
        with RUN_LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%F %T')} {redact(str(msg))}\n")
    except OSError:
        pass  # 日志落盘失败不该拖垮填表本身；屏幕输出仍在


def shot(page, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    p = SHOTS / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    return p


def init_runtime():
    global WORK, CONFIG, SHOTS, SUB, F, RUN_LOG
    WORK = workdir()
    CONFIG = json.loads((WORK / "config.json").read_text(encoding="utf-8"))
    SHOTS = WORK / "output" / "shots"
    # 截图只记录最终状态；失败时"第几行开始不对、等了多久超时"只有运行日志答得上来。
    try:
        (WORK / "output").mkdir(parents=True, exist_ok=True)
        RUN_LOG = WORK / "output" / "fill_form.log"
    except OSError:
        RUN_LOG = None
    fields = CONFIG.get("form_fields", {})
    SUB = f'[id="{fields.get("subgrid_id", "")}"]'
    F = {
        key: f'[id="{fields.get(key, "")}"]'
        for key in (
            "start_date", "attach", "note", "row_date", "row_type",
            "row_project", "row_status", "row_hours", "row_content",
        )
    }


def require_config_keys(config, paths):
    """诊断/登录模式只校验自己真正用到的键。

    `--dump` 的用途就是**找出字段 id**；若它像填表一样要求完整配置通过校验，拿不到字段 id
    的新用户就被死锁在门外（先有鸡还是先有蛋）。因此这些模式只查导航到表单所必需的项，
    字段 id 一概不查。
    """
    missing = []
    for path in paths:
        value = config
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if not (isinstance(value, str) and value.strip()):
            missing.append(path)
    if missing:
        sys.exit("本模式仍需以下配置:\n- " + "\n- ".join(missing)
                 + "\n（form_fields 里的字段 id 可以留空——找出它们正是 --dump 的用途）")


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


def prompt_auth_url():
    if not sys.stdin.isatty():
        sys.exit("--login-url 需要用户在本机交互终端运行；禁止通过聊天、参数或管道传递登录链接")
    auth_url = getpass("粘贴 h3yun entry/auth 登录链接（输入隐藏）: ").strip()
    if not auth_url:
        sys.exit("未输入登录链接")
    return auth_url


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
    """带 token 的一次性登录链接直接建立登录态，免扫码。"""
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
        for _ in range(10):                     # 等跳转落地，正向确认后才落盘
            if looks_logged_in(page):
                break
            page.wait_for_timeout(1000)
        else:
            shot(page, "login-url-failed")
            sys.exit("登录链接未能进入应用（token 可能已过期）；未写入登录态。"
                     "重新打印二维码取新链接，或改用 --login 扫码")
        ctx.storage_state(path=str(STATE))
        STATE.chmod(0o600)
        log(f"登录态已保存: {STATE}")
        browser.close()


def do_login(url, qr_entry=1):
    ensure_state_owner()
    STATE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        # 登录页默认落在「密码登录」，二维码不会自己出现——必须先点开扫码入口。
        # 此前 --login 从不点它，于是截出来的 login.png 永远没有二维码。
        entries = page.locator(QR_ENTRY_SELECTOR)
        count = entries.count()
        if count:
            index = min(max(qr_entry, 1), count) - 1
            log(f"点开扫码入口（第 {index + 1} / {count} 个图标）")
            entries.nth(index).click()
            page.wait_for_timeout(2500)
        else:
            log("未找到扫码入口图标；若截图里没有二维码，请检查登录页结构")
        # 打印绝对路径：提示里写相对路径时用户得先知道 $WORK 在哪才找得到
        log(f"等待扫码：用手机钉钉扫 {SHOTS / 'login.png'}（5 分钟内）")
        log("  该图每 2.5 秒刷新一次；VSCode 里若看不到变化，关掉标签页重开取最新的一张")
        deadline = time.time() + 300
        while time.time() < deadline:
            shot(page, "login")
            if looks_logged_in(page):
                page.wait_for_timeout(3000)
                if looks_logged_in(page):       # 复确认，避免抓到跳转中间态
                    ctx.storage_state(path=str(STATE))
                    STATE.chmod(0o600)
                    shot(page, "login-ok")
                    log(f"登录态已保存: {STATE}")
                    browser.close()
                    return
            page.wait_for_timeout(2500)
        shot(page, "login-timeout")
        sys.exit("300s 内未确认到已登录页面；未写入登录态。重跑 --login，"
                 "并确认手机上完成了扫码确认")


# ---------------- 表单定位 ----------------

def open_new_form(page, url, mock):
    """打开列表页→点新增→返回表单所在 frame（真机=FormAdapter iframe；mock=主 frame）。"""
    page.goto(url, wait_until="domcontentloaded" if mock else "networkidle")
    if mock:
        return page.main_frame
    if "login" in page.url.lower():
        shot(page, "state-expired")
        sys.exit("登录态过期，重跑 --login / --login-url")
    page.get_by_text(CONFIG["form_texts"]["add_row"], exact=False).first.click()
    for _ in range(30):
        page.wait_for_timeout(1000)
        fr = next((f for f in page.frames if "FormAdapter" in f.url), None)
        if fr and fr.get_by_text(
                CONFIG["form_texts"]["start_date_label"]).count():
            page.wait_for_timeout(1500)
            return fr
    shot(page, "form-not-rendered")
    sys.exit("30s 内表单未渲染（FormAdapter frame 无字段）；看 form-not-rendered.png")


def fill_ant_date(fr, page, scope, value):
    """ant-calendar readonly input：点开 → 面板输入框敲日期 → Enter。"""
    scope.locator("input").first.click()
    cal = fr.locator(".ant-calendar-input")
    for _ in range(10):                      # 等面板弹出，而不是赌固定 600ms
        page.wait_for_timeout(300)
        if cal.count():
            break
    else:
        raise RuntimeError("3s 内日期面板未弹出（.ant-calendar-input 不存在）")
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


def attachment_enabled():
    """本表单是否有附件字段——组织事实，由 `form_fields.attach` 是否配置推导。

    留空即该表单没有附件项，整个上传步骤跳过。**不提供 `--no-attach` 之类的开关**：
    那会成为「附件生成失败 → 加参数绕过 → 交出缺附件草稿」的逃生口。
    """
    return bool(str(CONFIG.get("form_fields", {}).get("attach", "")).strip())


def attachment_locator(fr):
    return fr.locator(
        f'{F["attach"]} input[type="file"], input[type="file"]').first


def verify_attachment_uploaded(fr, page, file_input, needle, mock,
                               timeout_ms=30000):
    """上传后必须拿到**完成证据**；定长 sleep 不是证据。

    两层：
    1. 文件控件真的持有文件——`set_input_files` 静默没生效会在这层暴露（两种模式都查）；
    2. 页面上出现附件名——与人工在 `20-filled-review.png` 上核对「附件已挂」同一判据。
       仿真表单是同步的，没有异步上传完成信号可等，故只做第 1 层。
    """
    held = file_input.evaluate("el => el.files.length")
    if held != 1:
        raise RuntimeError(f"附件未进入文件控件（files.length={held}）: {needle}")
    if mock:
        return
    deadline = time.time() + timeout_ms / 1000
    while True:
        matches = fr.get_by_text(needle, exact=False)
        if any(matches.nth(i).is_visible() for i in range(matches.count())):
            return
        if time.time() >= deadline:
            break
        page.wait_for_timeout(500)
    raise RuntimeError(
        f"上传后 {timeout_ms // 1000}s 内页面未出现附件名「{needle}」，"
        "无法确认上传完成——就此中止，不落缺附件的草稿")


def verify_draft_saved(fr, page, mock, success_messages=()):
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
    # 两趟：先扫遍**所有** frame 找错误，再找成功。
    # 单趟逐 frame「先查错再查成功、命中成功就返回」会漏掉出现在后置 frame 里的错误——
    # 语义应是「全 frame 无可见错误 ∧ 存在可见成功」。
    for frame in page.frames:
        errors = frame.locator(error_selector)
        for i in range(errors.count()):
            if errors.nth(i).is_visible():
                raise RuntimeError(f"暂存失败: {errors.nth(i).inner_text().strip()}")
    for frame in page.frames:
        success = frame.locator(success_selector)
        if any(success.nth(i).is_visible() for i in range(success.count())):
            return
        for text in success_messages:
            matches = frame.get_by_text(text, exact=False)
            if any(matches.nth(i).is_visible() for i in range(matches.count())):
                return
    raise RuntimeError("点击暂存后未检测到可见的成功提示，不能确认草稿已保存")


def do_fill(report_path, url, save_draft):
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    try:
        validate_report(report)
        validate_report_against_config(report, CONFIG)
    except ValidationError as exc:
        sys.exit(str(exc))
    w = report["week"]
    attach_required = attachment_enabled()
    attach = attach_path(w["start"]) if attach_required else None
    if attach_required and not attach.exists():
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

            if attach_required:
                log(f"上传附件 {attach.name}")
                file_input = attachment_locator(fr)
                file_input.set_input_files(str(attach))
                verify_attachment_uploaded(
                    fr, page, file_input, attach.stem, mock)
            else:
                log("未配置 form_fields.attach：本表单无附件字段，跳过上传")

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
                        fr.locator(SUB).get_by_text(
                            CONFIG["form_texts"]["add_row"],
                            exact=False).first.click()
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
            btn_name = CONFIG["form_texts"]["save_draft"]
            fr.get_by_text(btn_name, exact=True).first.click()
            # 轮询等结果而非定长等待：慢的时候 4s 不够（误判失败），快的时候白等。
            page.wait_for_timeout(500)
            deadline = time.time() + (0 if mock else 20)
            while True:
                try:
                    verify_draft_saved(
                        fr, page, mock, CONFIG["form_texts"]["success_messages"])
                    break
                except RuntimeError:
                    if time.time() >= deadline:
                        raise
                    page.wait_for_timeout(1000)
            shot(page, "30-saved")
            log("草稿暂存成功，见 30-saved.png")
        except (PWTimeout, RuntimeError) as e:
            shot(page, "99-error")
            log(f"失败: {e}")
            sys.exit(f"失败: {e}（截图 output/shots/99-error.png"
                     f" + 运行日志 output/fill_form.log 发给协助排查的人）")
        finally:
            browser.close()


# ---------------- 会话保活 ----------------

def do_keepalive(url):
    """每日 cron 调用：带登录态访问列表页，回存刷新后的 cookie 让会话滚动续命。
    失效时 fail-loud（cron 日志可见），此时需要用户本人重新登录。"""
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
            assert_logged_in(page, "keepalive")
            ctx.storage_state(path=str(STATE))
            STATE.chmod(0o600)
            print(f"keepalive OK: {time.strftime('%F %T')} 会话有效，cookie 已回存")
        finally:
            browser.close()


# ---------------- 诊断 ----------------

def looks_logged_in(page):
    """页面是否已进入应用（正向判据）。

    **不能**用「URL 里没有 login」来判断：实测氚云登录页 URL 恰恰不含 `login`，
    `--login` 因此在用户还没扫码时就把未登录的会话存成了 state.json 并报告成功——
    典型的静默成功，且后果是拿一份废登录态去跑后续所有步骤。
    """
    if "login" in page.url.lower() or "entry/auth" in page.url:
        return False
    title = (CONFIG.get("form_texts") or {}).get("report_title", "").strip()
    if not title:
        return False          # 没有正向判据就不认为已登录，宁可等超时
    try:
        return page.get_by_text(title).count() > 0
    except Exception:
        return False


def assert_logged_in(page, context):
    """正向确认已登录，而不是"没看到失败迹象"就继续。

    只看 URL 含不含 login/entry/auth 是不够的——实测氚云过期后落到的登录页 URL **不含**
    这两个字样，`--dump-list` 因此静默产出了一份登录页的 dump，还照常写文件、给统计。
    拿登录页去推断字段只会得到垃圾。判据必须是**看见预期页面标识**（与 keepalive 同款）。
    """
    if "login" in page.url.lower() or "entry/auth" in page.url:
        shot(page, "state-expired")
        sys.exit(f"{context}: 登录态过期，重跑 --login / --login-url")
    title = (CONFIG.get("form_texts") or {}).get("report_title", "").strip()
    if not title:
        log(f"{context}: 未配置 form_texts.report_title，无法正向确认登录态")
        return
    if not page.get_by_text(title).count():
        shot(page, "state-expired")
        sys.exit(f"{context}: 页面未出现「{title}」——多为登录态过期，"
                 "重跑 --login / --login-url（截图见 output/shots/state-expired.png）")


def do_dump_list(url):
    """dump **列表页**原样，并捞出打开历史记录的候选入口。

    `--dump` 打的是「新增」后的空白表单，只能看到控件 id、看不到值。要按值形状认字段
    （日期/工时/长文本各有形态），必须打开一条**已填的历史记录**——而"怎么点开一条记录"
    的选择器目前未知，本模式就是为取证而设：先把列表页整页存下来，再列出候选入口，
    据此再实现打开记录。只读，不点任何东西。
    """
    if not STATE.exists():
        sys.exit("无登录态，先跑: fill_form.py --login / --login-url")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=str(STATE),
                                  viewport={"width": 1700, "height": 1100})
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(3000)
            assert_logged_in(page, "dump-list")
            SHOTS.mkdir(parents=True, exist_ok=True)
            (SHOTS / "dump-list.html").write_text(page.content(), encoding="utf-8")
            shot(page, "dump-list")

            # 候选入口：带 id 参数的链接，或看起来是数据行的元素
            links = page.eval_on_selector_all(
                "a[href]", "els => els.map(e => e.getAttribute('href'))")
            record_links = [h for h in links if h and re.search(
                r"(objectid|bizobjectid|recordid|id)=", h, re.I)]
            log(f"列表页链接 {len(links)} 条，其中带记录标识的 {len(record_links)} 条")
            for selector in ("tr[data-row-key]", ".ant-table-row",
                             "[class*=list-row]", "[class*=grid-row]"):
                count = page.locator(selector).count()
                if count:
                    log(f"候选数据行 {selector}: {count} 个")
            log("已存 output/shots/dump-list.html + dump-list.png")
            log("下一步：把上面几行统计发给维护者（**不要发 html 本身**，它含组织数据）")
        finally:
            browser.close()


# 氚云列表页网格的通用 DOM 常量（与 .ant-calendar-input / FormAdapter 同类，属厂商结构而非组织数据）
LIST_ROW_LINK = "span.tg-link"
# 登录页默认是「密码登录」，二维码藏在「或」下面那排图标后面（无 alt/title，只能按序号点）
QR_ENTRY_SELECTOR = ".h3-login-type .content-icon img"


def _visible_option_texts(fr):
    """当前可见的候选项文本集合。

    氚云的 ant-select 菜单**点开后不销毁**（`pick_dropdown` 已记录此行为），所以不能只看
    "菜单里有哪些项"——那会混进此前打开过的菜单。用点击前后的差集把新菜单隔离出来。
    """
    items = fr.locator("li")
    texts = set()
    for i in range(min(items.count(), 200)):
        item = items.nth(i)
        try:
            if item.is_visible():
                text = item.inner_text().strip()
                if text:
                    texts.add(text)
        except Exception:
            continue
    return texts


def do_harvest_enums(url):
    """展开每个下拉，收集**完整**合法选项。

    理论上下拉展开才是枚举全集（历史只含**你用过的值**）。但实测在本表单上**孤立点开取不到
    选项**——与 `references/FIELDS.md` 早已记录的「关联下拉孤立探测无数据、正常流程有数据」
    是同一现象：菜单只渲染一个占位项。因此本模式**降级为诊断工具**；枚举的实用来源是
    `--dump-record` 跨多条历史记录取并集（见 `_report_proposal` 输出的「观察到的取值」）。

    **不填任何值、不保存。**
    """
    if not STATE.exists():
        sys.exit("无登录态，先跑: fill_form.py --login / --login-url")
    mock = is_mock(url)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=None if mock else str(STATE),
                                  viewport={"width": 1700, "height": 1100})
        page = ctx.new_page()
        try:
            fr = open_new_form(page, url, mock)
            try:                       # 加一行，让子表内的下拉渲染出来
                fr.locator(SUB).get_by_text(
                    CONFIG["form_texts"]["add_row"], exact=False).first.click()
                page.wait_for_timeout(1500)
            except Exception:
                log("未能新增子表行，只抓主表下拉")

            drops = fr.locator(".h3-dropdown")
            total = drops.count()
            log(f"发现下拉控件 {total} 个")
            harvested = {}
            visible = sum(1 for i in range(total) if drops.nth(i).is_visible())
            log(f"其中可见 {visible} 个")
            harvested = {}
            for i in range(total):
                node = drops.nth(i)
                if not node.is_visible():
                    continue
                owner = node.evaluate(
                    "el => { let n = el; while (n && !n.id) n = n.parentElement;"
                    " return n ? n.id : ''; }")
                before = _visible_option_texts(fr)
                node.click()
                page.wait_for_timeout(900)
                options = sorted(_visible_option_texts(fr) - before)
                page.keyboard.press("Escape")
                page.wait_for_timeout(400)
                key = owner or f"<无 id 的下拉 {i}>"
                if options and key not in harvested:
                    harvested[key] = options
                log(f"  {key}: {len(options)} 个选项")
            shot(page, "harvest-enums")
            log("——以下是抓到的完整选项，请对应填进 vocabulary——")
            for owner, options in harvested.items():
                log(f"  {owner}: {' / '.join(options)}")
            log("未填任何值、未保存；选项文本属组织数据，勿外发")
        finally:
            browser.close()


def _report_proposal(html):
    """按三重信号给出 form_fields 候选，**只打印不写盘**——组织私有面必须人确认。"""
    proposal, ambiguous = propose_fields(
        html, CONFIG.get("vocabulary"), CONFIG.get("form_project", ""))
    current = CONFIG.get("form_fields", {})
    log(f"字段候选：确定 {len(proposal)} 项，歧义 {len(ambiguous)} 项")
    for key, item in sorted(proposal.items()):
        mark = "=现配置" if current.get(key) == item["id"] else "≠现配置"
        log(f"  {key}: {item['id']} [{item['confidence']}] {mark} — {item['why']}")
    for key, options in sorted(ambiguous.items()):
        log(f"  {key}: 需人工二选一 → {', '.join(options)}")

    # 顺带把枚举学出来：下拉孤立探测取不到选项（见 do_harvest_enums），
    # 历史记录里**实际用过的值**才是可得的来源。跨多条记录取并集可提高覆盖，
    # 但仍**不等于全集**——没用过的选项（如从没休过假）永远学不到，必须人工补。
    _, candidates = analyse(html)
    for key in ("row_type", "row_status", "row_project"):
        field_id = proposal.get(key, {}).get("id")
        if not field_id or field_id not in candidates:
            continue
        seen = sorted(candidates[field_id].texts())
        if seen:
            log(f"  {key} 本条记录观察到的取值（{len(seen)} 个）: {' / '.join(seen)}")
    log("枚举来自历史仅为**用过的值**，不等于全部合法值；多跑几条记录取并集，仍需人工补全")
    payload = {
        "proposal": proposal,
        "ambiguous": ambiguous,
        "observed": {k: sorted(candidates[v["id"]].texts())
                     for k, v in proposal.items() if v["id"] in candidates},
    }
    out = WORK / "output" / "field-proposal.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    log(f"候选已写入 {out}")
    log("下一步：configure.py --from-discovery 逐项确认后写入（不会自动落盘）")


def do_dump_record(url, index):
    """打开第 index 条历史记录并 dump 其 DOM。**只读，不点保存、不改任何值。**

    `--dump` 打的是空白新增表单，只有控件 id 没有值；按值形状认字段（日期/工时/长文本/
    枚举各有形态）必须看一条**已填**记录。列表页的标题是 span.tg-link（不是 <a href>，
    所以无法用 URL 直取），只能点开。
    """
    if not STATE.exists():
        sys.exit("无登录态，先跑: fill_form.py --login / --login-url")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=str(STATE),
                                  viewport={"width": 1700, "height": 1100})
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(3000)
            assert_logged_in(page, "dump-record")
            links = page.locator(LIST_ROW_LINK)
            total = links.count()
            log(f"列表页记录标题 {total} 条，打开第 {index} 条")
            if total < index:
                sys.exit(f"列表页只有 {total} 条记录，取不到第 {index} 条")
            links.nth(index - 1).click()
            for _ in range(30):
                page.wait_for_timeout(1000)
                fr = next((f for f in page.frames if "FormAdapter" in f.url), None)
                if fr and fr.locator("[id]").count() > 20:
                    page.wait_for_timeout(2000)
                    break
            else:
                shot(page, "dump-record-not-rendered")
                sys.exit("30s 内记录未渲染；看 dump-record-not-rendered.png")
            SHOTS.mkdir(parents=True, exist_ok=True)
            html = fr.content()
            (SHOTS / "dump-record.html").write_text(html, encoding="utf-8")
            shot(page, "dump-record")
            log("已存 output/shots/dump-record.html + dump-record.png")
            _report_proposal(html)
            log("只读操作，未保存任何内容；html 含组织数据，勿外发")
        finally:
            browser.close()


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
    ap.add_argument("--qr-entry", type=int, default=1, metavar="N",
                    help="登录页「或」下面第 N 个图标是扫码入口（默认 1）")
    ap.add_argument("--login-url", action="store_true",
                    help="在本机交互终端隐藏输入一次性登录链接；不接受命令行参数")
    ap.add_argument("--dump", action="store_true",
                    help="打开「新增」空白表单并 dump DOM（找字段 id）")
    ap.add_argument("--dump-list", action="store_true",
                    help="只 dump 列表页并列出打开历史记录的候选入口（取证用，只读）")
    ap.add_argument("--dump-record", type=int, metavar="N",
                    help="打开列表第 N 条历史记录并 dump（只读，不保存）")
    ap.add_argument("--harvest-enums", action="store_true",
                    help="展开各下拉收集完整合法选项（不填值、不保存）")
    ap.add_argument("--keepalive", action="store_true", help="访问列表页续会话并回存 cookie（cron 用）")
    ap.add_argument("--url", help="覆盖 config.form_url（联调/仿真用）")
    ap.add_argument("--draft", action="store_true", help="填完点「暂存」落草稿")
    ap.add_argument("--confirmed", action="store_true",
                    help="确认内容已经人工审核、同周旧草稿已经检查（与 --draft 同用）")
    args = ap.parse_args()
    if args.login_url and args.report_json:
        ap.error("--login-url 不接受 URL 参数；请只输入 --login-url，再按隐藏提示粘贴")
    if args.draft and not args.confirmed:
        ap.error("--draft 必须同时提供 --confirmed，表示已完成人审和同周旧草稿检查")
    if args.confirmed and not args.draft:
        ap.error("--confirmed 只能与 --draft 同用")
    if not any((args.login_url, args.login, args.keepalive, args.dump,
                args.dump_list, args.dump_record, args.harvest_enums,
                args.report_json)):
        ap.print_help()
        return
    init_runtime()
    # 只记文件名不记路径：日志可能被附到 issue，绝对路径会带出用户名与目录结构
    shown = " ".join(Path(a).name if "/" in a else a for a in sys.argv[1:])
    log(f"=== run: {shown or '(no args)'} ===")
    if args.login_url:
        do_login_url(prompt_auth_url())          # 只需登录链接本身
    elif args.login:
        do_login(resolve_url(args), args.qr_entry)   # 只需 form_url，由 resolve_url 校验
    elif args.dump_list:
        do_dump_list(resolve_url(args))          # 只读列表页，无需任何字段配置
    elif args.dump_record:
        do_dump_record(resolve_url(args), args.dump_record)
    elif args.harvest_enums:
        require_config_keys(
            CONFIG, ("form_texts.add_row", "form_texts.start_date_label"))
        do_harvest_enums(resolve_url(args))
    elif args.dump:
        # 找字段 id 的诊断模式：只需能导航到表单，字段 id 正是它要找的东西
        require_config_keys(
            CONFIG, ("form_texts.add_row", "form_texts.start_date_label"))
        do_dump(resolve_url(args))
    else:
        # 保活与填表要真正操作表单，必须完整配置就绪
        try:
            validate_config(CONFIG)
        except ValidationError as exc:
            sys.exit(str(exc))
        if args.keepalive:
            do_keepalive(resolve_url(args))
        elif args.report_json:
            do_fill(args.report_json, resolve_url(args), args.draft)


if __name__ == "__main__":
    main()
