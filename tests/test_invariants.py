#!/usr/bin/env python3
"""不变量守卫：保护「设计承诺」，不是实现细节。

存在理由：`SECURITY.md`、`SKILL.md`、`CONTRACT.md` 都对外承诺**工具没有提交能力**。
这条承诺今天靠的是「代码里根本没有那条路径」——结构性保证，很强，但也脆：
任何一次"顺手加个提交按钮"的改动都能不声不响抹掉它，而 diff 看上去完全合理。
本文件把它变成一条会 FAIL 的断言。

尤其针对 **P3（改用氚云 OpenApi）**：换成 API 之后，"不能提交"会从
「不存在这条路径」退化成「我们选择不调那个接口」。届时本文件必须继续通过——
把断言目标改成「代码里不出现提交端点常量」，**不是删掉本文件**。
详见 docs/MAINTAINER.md 的 P3 条目。
"""
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path(os.environ.get(
    "DTWR_SKILL", ROOT / "skills" / "dingtalk-weekly-report"))
sys.path.insert(0, str(SKILL / "scripts"))

import dtwr_fields

SCRIPTS = SKILL / "scripts"
FILL_FORM = (SCRIPTS / "fill_form.py").read_text(encoding="utf-8")

# 提交类词汇。注意 "submit" 只在这里当"要拦的词"用；不要放宽成正则通配，
# 否则会把 "submitted"（LICENSE 措辞）之类无关文本也算进来。
SUBMIT_WORDS = ("提交", "submit", "审批", "approve")

# fill_form.py 允许读的 form_texts 键。**新增前先想清楚它会不会驱动点击**：
# 只有 add_row / save_draft 真的会 .click()，另两个是判据文本。
ALLOWED_TEXT_KEYS = {"add_row", "save_draft", "start_date_label",
                     "success_messages"}


class SubmitCapabilityAbsent(unittest.TestCase):
    def test_only_allowlisted_form_text_keys_are_read(self):
        """fill_form 读的 form_texts 键必须在白名单内——新增键会撞这条，逼人复核点击语义。"""
        used = set(re.findall(r'form_texts"\]\["([a-z_]+)"\]', FILL_FORM))
        self.assertEqual(used, ALLOWED_TEXT_KEYS,
                         f"form_texts 读取集变化：多出 {used - ALLOWED_TEXT_KEYS}，"
                         f"少了 {ALLOWED_TEXT_KEYS - used}")

    def test_no_config_key_is_submit_shaped(self):
        """配置里不得出现提交类键——有的话说明提交能力被产品化成了配置项。"""
        for key in dtwr_fields.FORM_TEXT_KEYS:
            for word in SUBMIT_WORDS:
                self.assertNotIn(word, key.casefold(),
                                 f"配置键 {key} 含提交类词汇 {word}")

    def test_no_click_is_driven_by_a_submit_literal(self):
        """代码里不得出现「点击提交类字面量」。

        只看 .click() 所在行：注释与提示文案里出现「提交」是**对的**（我们要告诉
        用户自己去提交），不能一并禁掉，否则测试会逼人删掉正确的文档字符串。
        """
        offenders = []
        for lineno, line in enumerate(FILL_FORM.splitlines(), 1):
            if ".click()" not in line:
                continue
            low = line.casefold()
            for word in SUBMIT_WORDS:
                if word in low:
                    offenders.append(f"{lineno}: {line.strip()}")
                    break
        self.assertEqual(offenders, [], f"疑似提交点击：{offenders}")

    # 第二道闸——「即使有人把 save_draft 配成提交按钮，校验层也要拦下」——
    # 已由 test_core.py::test_config_rejects_submit_button_as_draft_action 守住。
    # 这里不重复实现：上面三条守**代码**，那一条守**配置**，两者合起来才完整。


if __name__ == "__main__":
    unittest.main()
