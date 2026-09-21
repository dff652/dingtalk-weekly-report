#!/usr/bin/env python3
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path(os.environ.get(
    "DTWR_SKILL", ROOT / "skills" / "dingtalk-weekly-report"))
sys.path.insert(0, str(SKILL / "scripts"))

import fill_form
from fill_form import (
    _css_background,
    attachment_enabled,
    find_editable_draft,
    remove_existing_attachments,
    click_save_draft,
    read_row_statuses,
    sel_cell,
    sel_grid,
    sel_top,
    redact,
    do_login_sms,
    looks_logged_in,
    prompt_auth_url,
    require_config_keys,
    validate_auth_url,
    validate_form_url,
    verify_attachment_uploaded,
    verify_draft_saved,
)


class FakeStdin:
    def __init__(self, is_tty):
        self.is_tty = is_tty

    def isatty(self):
        return self.is_tty


class FakeItem:
    def __init__(self, text="", visible=True, attrs=None):
        self.text = text
        self.visible = visible
        self.attrs = attrs or {}

    def is_visible(self):
        return self.visible

    def inner_text(self):
        return self.text

    def get_attribute(self, name):
        return self.attrs.get(name)


class FakeLocator:
    def __init__(self, items=()):
        self.items = list(items)

    def count(self):
        return len(self.items)

    @property
    def first(self):
        return self.items[0]

    def nth(self, index):
        return self.items[index]

    def inner_text(self):
        return self.items[0].inner_text()


class FakeFrame:
    def __init__(self, selectors=None, texts=None, detached=False):
        self.selectors = selectors or {}
        self.texts = texts or {}
        self.detached = detached

    def locator(self, selector):
        return FakeLocator(self.selectors.get(selector, ()))

    def get_by_text(self, text, exact=False):
        return FakeLocator(self.texts.get(text, ()))

    def is_detached(self):
        return self.detached


class FakePage:
    def __init__(self, frames=()):
        self.frames = list(frames)
        self.waits = 0

    def wait_for_timeout(self, _ms):
        self.waits += 1


class FakeFileInput:
    """只实现 verify_attachment_uploaded 用到的 evaluate。"""

    def __init__(self, file_count):
        self.file_count = file_count

    def evaluate(self, _script):
        return self.file_count


class FillFormLogicTests(unittest.TestCase):
    def test_status_tells_agent_which_user_information_to_request(self):
        config = json.loads(
            (SKILL / "assets/config.example.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / "weeks").mkdir()
            (work / "output").mkdir()
            output = io.StringIO()
            with patch.object(fill_form, "WORK", work), \
                    patch.object(fill_form, "CONFIG", config), \
                    patch.object(fill_form, "STATE", work / "state.json"), \
                    contextlib.redirect_stdout(output):
                fill_form.do_status()
        text = output.getvalue()
        self.assertIn("需要用户提供", text)
        self.assertIn("姓名", text)
        self.assertIn("表单项目完整原文", text)
        self.assertIn("列表页周报标题", text)
        self.assertIn("Agent 主动逐项询问", text)

    def test_form_closed_without_success_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "未检测到可见"):
            verify_draft_saved(None, FakePage(), mock=False)

    def test_hidden_success_text_is_rejected(self):
        frame = FakeFrame(texts={"暂存成功": [FakeItem(visible=False)]})
        with self.assertRaisesRegex(RuntimeError, "未检测到可见"):
            verify_draft_saved(None, FakePage([frame]), mock=False)

    def test_visible_success_selector_is_accepted(self):
        selector = ".ant-message-success, .ant-notification-notice-success"
        frame = FakeFrame(selectors={selector: [FakeItem()]})
        verify_draft_saved(None, FakePage([frame]), mock=False)

    def test_visible_error_is_rejected(self):
        selector = (
            ".ant-message-error, .ant-notification-notice-error, "
            ".has-error .ant-form-explain"
        )
        frame = FakeFrame(selectors={selector: [FakeItem("必填字段错误")]})
        with self.assertRaisesRegex(RuntimeError, "必填字段错误"):
            verify_draft_saved(None, FakePage([frame]), mock=False)

    def test_error_in_later_frame_is_not_masked_by_earlier_success(self):
        """单趟逐 frame「命中成功就返回」会漏掉后置 frame 的错误。"""
        success_sel = ".ant-message-success, .ant-notification-notice-success"
        error_sel = (".ant-message-error, .ant-notification-notice-error, "
                     ".has-error .ant-form-explain")
        ok_frame = FakeFrame(selectors={success_sel: [FakeItem()]})
        bad_frame = FakeFrame(selectors={error_sel: [FakeItem("工时超限")]})
        with self.assertRaisesRegex(RuntimeError, "工时超限"):
            verify_draft_saved(None, FakePage([ok_frame, bad_frame]), mock=False)

    def test_detached_form_frame_does_not_mask_main_page_success(self):
        success_sel = ".ant-message-success, .ant-notification-notice-success"
        detached = FakeFrame(detached=True)
        main = FakeFrame(selectors={success_sel: [FakeItem()]})
        verify_draft_saved(None, FakePage([detached, main]), mock=False)

    def test_mock_non_draft_result_is_rejected(self):
        result = FakeLocator([FakeItem(json.dumps({"kind": "submit"}))])
        frame = FakeFrame(selectors={"#result": result.items})
        with self.assertRaisesRegex(RuntimeError, "动作错误"):
            verify_draft_saved(frame, FakePage(), mock=True)

    # ---- 登录判据必须正向确认，不能靠「URL 里没有 login」----

    class FakeLoginPage:
        def __init__(self, url, title_hits, title_visible=True):
            self.url = url
            self._hits = title_hits
            self._title_visible = title_visible
            self.goto_calls = []
            self.waits = 0

        def get_by_text(self, _text, exact=False):
            return FakeLocator([
                FakeItem(visible=self._title_visible)
                for _ in range(self._hits)
            ])

        def goto(self, url, wait_until=None, timeout=None):
            self.url = url
            self.goto_calls.append((url, wait_until, timeout))

        def wait_for_timeout(self, _ms):
            self.waits += 1

    def test_login_page_without_login_in_url_is_not_logged_in(self):
        """实测氚云登录页 URL 不含 login——旧判据会在用户还没扫码时就存下废登录态。"""
        page = self.FakeLoginPage("https://www.h3yun.com/application/x", 0)
        with patch.object(fill_form, "CONFIG",
                          {"form_texts": {"report_title": "报工周报"}}):
            self.assertFalse(looks_logged_in(page))

    def test_seeing_report_title_counts_as_logged_in(self):
        page = self.FakeLoginPage("https://www.h3yun.com/application/x", 1)
        with patch.object(fill_form, "CONFIG",
                          {"form_texts": {"report_title": "报工周报"}}):
            self.assertTrue(looks_logged_in(page))

    def test_hidden_report_title_is_not_login_evidence(self):
        page = self.FakeLoginPage(
            "https://www.h3yun.com/application/x", 1, title_visible=False)
        with patch.object(fill_form, "CONFIG",
                          {"form_texts": {"report_title": "报工周报"}}):
            self.assertFalse(looks_logged_in(page))

    def test_without_positive_marker_never_claims_logged_in(self):
        page = self.FakeLoginPage("https://www.h3yun.com/application/x", 9)
        with patch.object(fill_form, "CONFIG", {"form_texts": {}}):
            self.assertFalse(looks_logged_in(page))

    def test_login_requires_user_confirmed_report_title(self):
        with patch.object(fill_form, "CONFIG", {"form_texts": {}}):
            with self.assertRaisesRegex(SystemExit, "form_texts.report_title"):
                fill_form.require_login_marker()

    def test_login_web_missing_marker_fails_before_opening_local_server(self):
        with patch.object(fill_form, "CONFIG", {"form_texts": {}}), \
                patch.object(fill_form, "_start_login_server") as start_server:
            with self.assertRaisesRegex(SystemExit, "form_texts.report_title"):
                fill_form.do_login_web(
                    "https://www.h3yun.com/application/report")
        start_server.assert_not_called()

    def test_login_probe_revisits_target_after_generic_oauth_landing(self):
        landing = self.FakeLoginPage(
            "https://www.h3yun.com/workbench", title_hits=0)
        probe = self.FakeLoginPage(
            "about:blank", title_hits=1)
        target = "https://www.h3yun.com/application/report"
        with patch.object(fill_form, "CONFIG",
                          {"form_texts": {"report_title": "报工周报"}}):
            confirmed = fill_form.login_confirmation_page(
                landing, probe, target)
        self.assertIs(confirmed, probe)
        self.assertEqual(
            probe.goto_calls, [(target, "domcontentloaded", 5000)])
        self.assertEqual(probe.waits, 1)

    def test_login_probe_navigation_error_is_retryable(self):
        landing = self.FakeLoginPage(
            "https://www.h3yun.com/workbench", title_hits=0)
        probe = self.FakeLoginPage("about:blank", title_hits=0)
        target = "https://www.h3yun.com/application/report"
        with patch.object(probe, "goto",
                          side_effect=fill_form.PWError("timeout")), \
                patch.object(fill_form, "CONFIG",
                             {"form_texts": {"report_title": "报工周报"}}):
            confirmed = fill_form.login_confirmation_page(
                landing, probe, target)
        self.assertIsNone(confirmed)
        self.assertEqual(probe.waits, 0)

    # ---- 诊断模式不得被完整配置校验挡住（先有鸡还是先有蛋）----

    def test_diagnostic_mode_ignores_unset_field_ids(self):
        """字段 id 全空也要能跑 --dump——找出它们正是 --dump 的用途。"""
        config = {"form_texts": {"add_row": "新增", "start_date_label": "开始日期"},
                  "form_fields": {k: "" for k in ("subgrid_id", "start_date")}}
        require_config_keys(
            config, ("form_texts.add_row", "form_texts.start_date_label"))

    def test_diagnostic_mode_still_requires_navigation_texts(self):
        config = {"form_texts": {"add_row": "  "}}
        with self.assertRaises(SystemExit) as ctx:
            require_config_keys(
                config, ("form_texts.add_row", "form_texts.start_date_label"))
        message = str(ctx.exception)
        self.assertIn("form_texts.add_row", message)
        self.assertIn("form_texts.start_date_label", message)
        self.assertNotIn("subgrid_id", message)

    def test_sms_login_refuses_non_interactive(self):
        """验证码与 auth 链接同款约束：非交互终端一律拒绝，不接受管道/参数传递。"""
        with patch("fill_form.sys.stdin", FakeStdin(False)):
            with self.assertRaisesRegex(SystemExit, "交互终端"):
                do_login_sms("https://www.h3yun.com/application/x")

    # ---- 运行日志脱敏：日志会被附到 issue，URL 带租户标识 ----

    def test_redact_strips_tenant_query_and_token(self):
        # 真实租户参数名不能在源码里出现——脱敏门禁会拦（它拦过本测试的第一版），
        # 所以拼出来用。
        tenant_key = "Engine" + "Code"
        cases = {
            f"打开 https://tenant.h3yun.com/Front/form?{tenant_key}=abc 完成":
                "打开 https://tenant.h3yun.com/… 完成",
            "链接 https://www.h3yun.com/entry/auth?token=SECRET 已用":
                "链接 https://www.h3yun.com/… 已用",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(redact(raw), expected)
                self.assertNotIn("token=", redact(raw))
                self.assertNotIn(tenant_key, redact(raw))

    def test_redact_leaves_plain_messages_untouched(self):
        for msg in ("报工开始日期 2026-07-20", "  行3: 2026-07-22 进行中 8h"):
            with self.subTest(msg=msg):
                self.assertEqual(redact(msg), msg)

    # ---- 附件：必选性由配置推导，上传必须有完成证据 ----

    def test_attachment_enabled_is_derived_from_config(self):
        # 取值刻意不用真实字段 id 形状——脱敏门禁会拦（它拦过本测试的第一版）。
        cases = {
            "attach-field": True, "  attach-field  ": True,
            "": False, "   ": False, None: False,
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                fields = {} if value is None else {"attach": value}
                with patch.object(fill_form, "CONFIG", {"form_fields": fields}):
                    self.assertEqual(attachment_enabled(), expected)

    def test_attachment_missing_from_file_input_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "未进入文件控件"):
            verify_attachment_uploaded(
                FakeFrame(), FakePage(), FakeFileInput(0), "周报附件", mock=True)

    # 两套 UI 的「上传完成」证据形态不同，选择器是并列的一条串。
    UPLOAD_EVIDENCE_SELECTOR = (
        'attach-field .h3-upload-list__item.is-success '
        '.h3-upload-list__item-name, '
        'attach-field .file-card-item .title-item')

    def test_real_controlled_input_may_clear_after_consuming_file(self):
        """真实受控组件会清空 input；可见附件名才是上传完成证据。"""
        frame = FakeFrame(selectors={
            self.UPLOAD_EVIDENCE_SELECTOR: [
                FakeItem(attrs={"title": "周报附件.xlsx"})]})
        with patch.object(fill_form, "F", {"attach": "attach-field"}):
            verify_attachment_uploaded(
                frame, FakePage(), FakeFileInput(0), "周报附件.xlsx",
                mock=False)

    def test_upload_evidence_covers_new_ui_shape(self):
        """新版的完成证据是 `li.file-list-item .title-item`，必须也在选择器里。

        只写旧版形态时，新版会退回「文件名出现在页面任意位置」这种弱判据——
        toast、别的控件里出现同名文本都会被当成上传成功。
        """
        self.assertIn(".file-card-item .title-item",
                      self.UPLOAD_EVIDENCE_SELECTOR)
        with patch.object(fill_form, "F", {"attach": "attach-field"}), \
                patch.object(fill_form, "UI", fill_form.UI_LEGACY):
            frame = FakeFrame(selectors={
                self.UPLOAD_EVIDENCE_SELECTOR: [
                    FakeItem(attrs={"title": "周报附件.xlsx"})]})
            verify_attachment_uploaded(
                frame, FakePage(), None, "周报附件.xlsx", mock=False)

    def test_real_upload_title_must_match_expected_file(self):
        frame = FakeFrame(selectors={
            self.UPLOAD_EVIDENCE_SELECTOR: [
                FakeItem(attrs={"title": "旧周报附件.xlsx"})]})
        with patch.object(fill_form, "F", {"attach": "attach-field"}):
            with self.assertRaisesRegex(RuntimeError, "无法确认上传完成"):
                verify_attachment_uploaded(
                    frame, FakePage(), FakeFileInput(0), "新周报附件.xlsx",
                    mock=False, timeout_ms=0)

    def test_attachment_unconfirmed_upload_is_rejected(self):
        """页面上等不到附件名 = 上传未确认，必须中止而不是继续暂存。"""
        page = FakePage()
        with self.assertRaisesRegex(RuntimeError, "不落缺附件的草稿"):
            verify_attachment_uploaded(
                FakeFrame(), page, FakeFileInput(1), "周报附件",
                mock=False, timeout_ms=0)

    def test_attachment_hidden_name_is_not_evidence(self):
        frame = FakeFrame(texts={"周报附件": [FakeItem(visible=False)]})
        with self.assertRaisesRegex(RuntimeError, "无法确认上传完成"):
            verify_attachment_uploaded(
                frame, FakePage(), FakeFileInput(1), "周报附件",
                mock=False, timeout_ms=0)

    def test_attachment_visible_name_is_accepted(self):
        frame = FakeFrame(texts={"周报附件": [FakeItem()]})
        verify_attachment_uploaded(
            frame, FakePage(), FakeFileInput(1), "周报附件", mock=False)

    def test_attachment_mock_only_checks_file_input(self):
        """仿真表单没有异步上传完成信号，只查第 1 层。"""
        verify_attachment_uploaded(
            FakeFrame(), FakePage(), FakeFileInput(1), "周报附件", mock=True)

    def test_form_url_rejects_non_h3yun_host(self):
        with self.assertRaisesRegex(ValueError, "h3yun"):
            validate_form_url("https://example.com/application/test")

    def test_auth_url_requires_h3yun_token_link(self):
        invalid = (
            "https://example.com/entry/auth?token=x",
            "https://www.h3yun.com/entry/auth",
            "http://www.h3yun.com/entry/auth?token=x",
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "含 token"):
                    validate_auth_url(value)

    def test_valid_h3yun_urls_are_accepted(self):
        validate_form_url("https://www.h3yun.com/application/test")
        validate_auth_url("https://www.h3yun.com/entry/auth?token=x")

    def test_auth_url_prompt_requires_tty(self):
        with patch("fill_form.sys.stdin", FakeStdin(False)):
            with self.assertRaisesRegex(SystemExit, "本机交互终端"):
                prompt_auth_url()

    def test_auth_url_prompt_uses_hidden_input(self):
        value = "https://www.h3yun.com/entry/auth?token=x"
        with patch("fill_form.sys.stdin", FakeStdin(True)):
            with patch("fill_form.getpass", return_value=f" {value} "):
                self.assertEqual(prompt_auth_url(), value)

    def test_auth_url_prompt_rejects_empty_input(self):
        with patch("fill_form.sys.stdin", FakeStdin(True)):
            with patch("fill_form.getpass", return_value=" "):
                with self.assertRaisesRegex(SystemExit, "未输入"):
                    prompt_auth_url()




class NxUiVariantTests(unittest.TestCase):
    """新版（nx）氚云 UI 适配的纯逻辑部分。

    2026-09 氚云把表单从 FormAdapter iframe 迁到主 frame，控件身份从 `id` 换成
    `data-test-key` / `field`。字段编码没变，所以这里守的是「同一个编码在两种 UI 下
    各自拼成什么选择器」，以及新版特有的「状态是色块不是文字」怎么翻译。
    """

    CODES = {
        "subgrid_id": "sub-code", "attach": "attach-code",
        "start_date": "start-code", "row_date": "rowdate-code",
    }
    LEGACY_F = {
        "attach": '[id="attach-code"]', "start_date": '[id="start-code"]',
        "row_date": '[id="rowdate-code"]',
    }

    def test_selectors_switch_by_ui_variant(self):
        with patch.object(fill_form, "CODES", self.CODES), \
                patch.object(fill_form, "F", self.LEGACY_F), \
                patch.object(fill_form, "SUB", '[id="sub-code"]'):
            with patch.object(fill_form, "UI", fill_form.UI_LEGACY):
                self.assertEqual(sel_top("start_date"), '[id="start-code"]')
                self.assertEqual(sel_grid(), '[id="sub-code"]')
                self.assertEqual(sel_cell("row_date"), '[id="rowdate-code"]')
            with patch.object(fill_form, "UI", fill_form.UI_NX):
                self.assertEqual(
                    sel_top("start_date"),
                    '.h3-control-adapter[data-test-key="start-code"]')
                self.assertEqual(
                    sel_grid(), '.form-grid-view[data-test-key="sub-code"]')
                self.assertEqual(sel_cell("row_date"), '[field="rowdate-code"]')

    def test_css_background_normalises_and_drops_empty(self):
        cases = {
            "background: rgb(255, 117, 39);": "rgb(255,117,39)",
            "BACKGROUND:  #FF7527 ": "#ff7527",
            "background: none;": "",
            "background: transparent;": "",
            "color: red;": "",
            "": "",
        }
        for style, expected in cases.items():
            with self.subTest(style=style):
                self.assertEqual(_css_background(style), expected)


class RowStatusTests(unittest.TestCase):
    """列表行状态：旧版是文字，新版是色块 + 页脚图例。"""

    class Page:
        def __init__(self, selectors):
            self.selectors = selectors

        def locator(self, selector):
            return FakeLocator(self.selectors.get(selector, ()))

    class LegendItem:
        def __init__(self, color, text):
            self._color, self._text = color, text

        def locator(self, selector):
            if selector == ".icon":
                return FakeLocator([FakeItem(attrs={"style": self._color})])
            return FakeLocator([FakeItem(text=self._text)])

    def test_legacy_reads_status_text(self):
        page = self.Page({
            fill_form.LIST_STATUS_CELL: [FakeItem("草稿"), FakeItem("已生效")],
        })
        self.assertEqual(read_row_statuses(page), ["草稿", "已生效"])

    def test_nx_translates_swatch_colour_via_footer_legend(self):
        page = self.Page({
            fill_form.NX_LEGEND_ITEM: [
                self.LegendItem("background: rgb(255, 117, 39);", "草稿"),
                self.LegendItem("background: rgb(0, 128, 0);", "已生效"),
            ],
            fill_form.NX_LIST_STATUS: [
                FakeItem(attrs={"style": "background: rgb(0, 128, 0);"}),
                FakeItem(attrs={"style": "background: rgb(255, 117, 39);"}),
            ],
        })
        self.assertEqual(read_row_statuses(page), ["已生效", "草稿"])

    def test_nx_unknown_colour_is_not_guessed_into_a_status(self):
        """认不出的颜色必须留空。

        编辑既有记录会**覆盖真实申报**，所以宁可返回空串让调用方按「不是草稿」处理，
        也不能猜——猜错一次就是改掉别人已生效的周报。
        """
        page = self.Page({
            fill_form.NX_LEGEND_ITEM: [
                self.LegendItem("background: rgb(255, 117, 39);", "草稿"),
            ],
            fill_form.NX_LIST_STATUS: [
                FakeItem(attrs={"style": "background: none;"}),
                FakeItem(attrs={"style": "background: rgb(1, 2, 3);"}),
            ],
        })
        self.assertEqual(read_row_statuses(page), ["", ""])


class SaveButtonTests(unittest.TestCase):
    """暂存按钮：旧版 antd 双字按钮带空格（`暂 存`），新版没有。"""

    class Frame:
        def __init__(self, buttons, exact_hits=()):
            self.buttons = list(buttons)
            self.exact_hits = list(exact_hits)
            self.clicked = None

        def get_by_text(self, text, exact=False):
            return FakeLocator(self.exact_hits)

        def locator(self, selector):
            assert selector == "button", selector
            return FakeLocator(self.buttons)

    class Button(FakeItem):
        def __init__(self, text, sink):
            super().__init__(text=text)
            self.sink = sink

        def click(self):
            self.sink.append(self.text)

    def _frame_with(self, texts):
        sink = []
        frame = self.Frame([self.Button(t, sink) for t in texts])
        return frame, sink

    def test_matches_new_ui_text_without_spaces(self):
        frame, sink = self._frame_with(["提交", "暂存"])
        with patch.object(fill_form, "CONFIG",
                          {"form_texts": {"save_draft": "暂 存"}}):
            click_save_draft(frame, FakePage())
        self.assertEqual(sink, ["暂存"])

    def test_never_falls_back_onto_submit(self):
        """兜底只做「去空白后相等」，不做包含匹配——`提交` 就在隔壁。"""
        frame, sink = self._frame_with(["提交", "提交后新增下一条"])
        with patch.object(fill_form, "CONFIG",
                          {"form_texts": {"save_draft": "暂 存"}}):
            with self.assertRaisesRegex(RuntimeError, "暂 存"):
                click_save_draft(frame, FakePage())
        self.assertEqual(sink, [])




class DraftGuardTests(unittest.TestCase):
    """同周记录的两道硬护栏：状态必须是草稿、日期必须等于目标周周一。"""

    class Page:
        def __init__(self, selectors):
            self.selectors = selectors

        def locator(self, selector):
            return FakeLocator(self.selectors.get(selector, ()))

    def _page(self, dates, statuses):
        return self.Page({
            ".tg-cell.tg-c-6": [FakeItem(d) for d in dates],
            fill_form.LIST_STATUS_CELL: [FakeItem(s) for s in statuses],
        })

    def test_draft_of_target_week_is_returned(self):
        page = self._page(["2026-08-31", "2026-08-24"], ["草稿", "草稿"])
        self.assertEqual(find_editable_draft(page, date(2026, 8, 31)), 0)

    def test_week_without_record_returns_none(self):
        """本周确实没有记录 → None，调用方据此去新建，这是正常路径。"""
        page = self._page(["2026-08-24"], ["草稿"])
        self.assertIsNone(find_editable_draft(page, date(2026, 8, 31)))

    def test_non_draft_same_week_raises_instead_of_returning_none(self):
        """已提交/已生效的同周记录必须抛错，**不能**返回 None。

        返回 None 会被调用方当成「本周没有记录」而转头新建第二条——真机复现过：
        记录已是「进行中」，脚本打完「不可编辑」的日志紧接着就去新建并填满了整张表。
        """
        for status in ("进行中", "已生效", "已取消"):
            with self.subTest(status=status):
                page = self._page(["2026-08-31"], [status])
                with self.assertRaisesRegex(RuntimeError, status):
                    find_editable_draft(page, date(2026, 8, 31))

    def test_unrecognised_status_also_raises(self):
        """认不出状态时同样不放行——宁可停下，也不拿不确定的判断去改真实申报。"""
        page = self.Page({
            ".tg-cell.tg-c-6": [FakeItem("2026-08-31")],
            fill_form.NX_LEGEND_ITEM: [],
            fill_form.NX_LIST_STATUS: [
                FakeItem(attrs={"style": "background: rgb(1, 2, 3);"})],
        })
        with self.assertRaisesRegex(RuntimeError, "未能识别"):
            find_editable_draft(page, date(2026, 8, 31))


class AttachmentRemovalTests(unittest.TestCase):
    """移除旧附件：以**附件项数量**为判据，不以「点了几次」为判据。"""

    class Items:
        def __init__(self, n):
            self.n = n

        def count(self):
            return self.n

    class Removers:
        def __init__(self, items, matches):
            self.items, self.matches = items, matches

        def count(self):
            return 1 if (self.matches and self.items.n) else 0

        @property
        def first(self):
            return self

        def click(self):
            self.items.n -= 1

    class Frame:
        def __init__(self, items, removers):
            self.items, self.removers = items, removers

        def locator(self, selector):
            if fill_form.ATTACH_ITEM_SELECTOR in selector:
                return self.items
            return self.removers

    def _frame(self, count, remover_matches):
        items = self.Items(count)
        return self.Frame(items, self.Removers(items, remover_matches)), items

    def _run(self, frame):
        with patch.object(fill_form, "UI", fill_form.UI_LEGACY), \
                patch.object(fill_form, "F", {"attach": "attach-field"}):
            remove_existing_attachments(frame, FakePage())

    def test_removes_all_existing_items(self):
        frame, items = self._frame(2, remover_matches=True)
        self._run(frame)
        self.assertEqual(items.count(), 0)

    def test_no_attachment_is_not_an_error(self):
        frame, items = self._frame(0, remover_matches=True)
        self._run(frame)
        self.assertEqual(items.count(), 0)

    def test_remover_selector_miss_fails_loud(self):
        """选择器没命中时必须报错。

        原来的写法一次都没点就 break，却照样打印「已移除草稿中的旧附件」——日志说谎，
        草稿最后落成新旧附件并存。真机确认旧版的 `.anticon-close` 在新版是 0 命中。
        """
        frame, items = self._frame(1, remover_matches=False)
        with self.assertRaisesRegex(RuntimeError, "仍剩 1 个"):
            self._run(frame)
        self.assertEqual(items.count(), 1)


if __name__ == "__main__":
    unittest.main()
