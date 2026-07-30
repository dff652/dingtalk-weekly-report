#!/usr/bin/env python3
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path(os.environ.get(
    "DTWR_SKILL", ROOT / "skills" / "dingtalk-weekly-report"))
sys.path.insert(0, str(SKILL / "scripts"))

import fill_form
from fill_form import (
    attachment_enabled,
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

    def test_real_controlled_input_may_clear_after_consuming_file(self):
        """真实受控组件会清空 input；可见附件名才是上传完成证据。"""
        selector = (
            'attach-field .h3-upload-list__item.is-success '
            '.h3-upload-list__item-name')
        frame = FakeFrame(selectors={
            selector: [FakeItem(attrs={"title": "周报附件.xlsx"})]})
        with patch.object(fill_form, "F", {"attach": "attach-field"}):
            verify_attachment_uploaded(
                frame, FakePage(), FakeFileInput(0), "周报附件.xlsx",
                mock=False)

    def test_real_upload_title_must_match_expected_file(self):
        selector = (
            'attach-field .h3-upload-list__item.is-success '
            '.h3-upload-list__item-name')
        frame = FakeFrame(selectors={
            selector: [FakeItem(attrs={"title": "旧周报附件.xlsx"})]})
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


if __name__ == "__main__":
    unittest.main()
