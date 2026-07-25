#!/usr/bin/env python3
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path(os.environ.get(
    "DTWR_SKILL", ROOT / "skills" / "dingtalk-weekly-report"))
sys.path.insert(0, str(SKILL / "scripts"))

from fill_form import (
    prompt_auth_url,
    validate_auth_url,
    validate_form_url,
    verify_draft_saved,
)


class FakeStdin:
    def __init__(self, is_tty):
        self.is_tty = is_tty

    def isatty(self):
        return self.is_tty


class FakeItem:
    def __init__(self, text="", visible=True):
        self.text = text
        self.visible = visible

    def is_visible(self):
        return self.visible

    def inner_text(self):
        return self.text


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
    def __init__(self, selectors=None, texts=None):
        self.selectors = selectors or {}
        self.texts = texts or {}

    def locator(self, selector):
        return FakeLocator(self.selectors.get(selector, ()))

    def get_by_text(self, text, exact=False):
        return FakeLocator(self.texts.get(text, ()))


class FakePage:
    def __init__(self, frames=()):
        self.frames = list(frames)


class FillFormLogicTests(unittest.TestCase):
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

    def test_mock_non_draft_result_is_rejected(self):
        result = FakeLocator([FakeItem(json.dumps({"kind": "submit"}))])
        frame = FakeFrame(selectors={"#result": result.items})
        with self.assertRaisesRegex(RuntimeError, "动作错误"):
            verify_draft_saved(frame, FakePage(), mock=True)

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
