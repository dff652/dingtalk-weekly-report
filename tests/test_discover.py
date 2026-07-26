#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""字段自动发现：三重信号叠加的匹配器。

夹具是**合成**的记录页，刻意不用真实字段 id 形状与 32 位十六进制——那两者都会被脱敏门禁拦。
真实租户上的验证结果记录在 docs/MAINTAINER.md「P4 方案」。
"""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path(os.environ.get("DTWR_SKILL", ROOT / "skills" / "dingtalk-weekly-report"))
sys.path.insert(0, str(SKILL / "scripts"))

import json as _json
import tempfile
from unittest.mock import patch

from configure import assignments_from_discovery
from dtwr_discover import propose_fields, value_shape


class DiscoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "tests/fixtures/record_view.html").read_text(encoding="utf-8")
        config = json.loads(
            (ROOT / "tests/fixtures/config.json").read_text(encoding="utf-8"))
        cls.proposal, cls.ambiguous = propose_fields(
            cls.html, config["vocabulary"], config["form_project"])

    def test_value_shapes(self):
        self.assertEqual(value_shape("2026-07-13"), "date")
        self.assertEqual(value_shape("0.5"), "number")
        self.assertEqual(value_shape("x" * 60), "long_text")
        self.assertEqual(value_shape("会议"), "short_text")
        self.assertEqual(value_shape("  "), "empty")

    def test_subgrid_container_is_identified(self):
        self.assertEqual(self.proposal["subgrid_id"]["id"], "Xsubgrid")

    def test_main_fields_use_control_type_signal(self):
        self.assertEqual(self.proposal["attach"]["id"], "Xmain03")
        self.assertEqual(self.proposal["note"]["id"], "Xmain04")

    def test_two_date_controls_resolved_by_earlier_value(self):
        """开始/结束日期同为 FormDateTime，靠"开始必早于结束"消歧。"""
        self.assertEqual(self.proposal["start_date"]["id"], "Xmain01")

    def test_row_fields_use_value_shape(self):
        self.assertEqual(self.proposal["row_date"]["id"], "Xrow01")
        self.assertEqual(self.proposal["row_hours"]["id"], "Xrow05")
        self.assertEqual(self.proposal["row_content"]["id"], "Xrow06")

    def test_lookalike_row_fields_use_vocabulary_membership(self):
        """三个短文本字段形状分不开，靠取值归属区分。"""
        self.assertEqual(self.proposal["row_type"]["id"], "Xrow02")
        self.assertEqual(self.proposal["row_status"]["id"], "Xrow04")
        self.assertEqual(self.proposal["row_project"]["id"], "Xrow03")

    def test_every_proposal_carries_evidence(self):
        for key, item in self.proposal.items():
            with self.subTest(key=key):
                self.assertTrue(item["why"], f"{key} 缺依据说明")
                self.assertIn(item["confidence"], ("high", "medium"))

    def test_without_vocabulary_lookalikes_become_ambiguous(self):
        """没有枚举这重信号时必须坦白说不确定，而不是瞎猜一个。"""
        proposal, ambiguous = propose_fields(self.html, {}, "")
        for key in ("row_type", "row_status", "row_project"):
            with self.subTest(key=key):
                self.assertNotIn(key, proposal)
                self.assertIn(key, ambiguous)


class ConfirmBeforeWriteTests(unittest.TestCase):
    """自动发现只把「手抄十个 id」降为「确认十几个候选」，不把人从回路里拿掉。"""

    PAYLOAD = {
        "proposal": {"row_hours": {"id": "Xrow05", "confidence": "high",
                                   "why": "每行取值均为数字"}},
        "ambiguous": {"row_project": ["Xa", "Xb"]},
        "observed": {"row_hours": ["8", "0.5"]},
    }

    def _run(self, answers):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proposal.json"
            path.write_text(_json.dumps(self.PAYLOAD), encoding="utf-8")
            with patch("builtins.input", side_effect=answers):
                return assignments_from_discovery({"form_fields": {}}, path)

    def test_nothing_is_written_without_explicit_yes(self):
        self.assertEqual(self._run(["", ""]), [])

    def test_accepted_proposal_becomes_assignment(self):
        self.assertIn("form_fields.row_hours=Xrow05", self._run(["y", ""]))

    def test_ambiguous_choice_is_by_number(self):
        self.assertIn("form_fields.row_project=Xb", self._run(["", "2"]))

    def test_out_of_range_choice_is_ignored(self):
        self.assertEqual(self._run(["", "9"]), [])


if __name__ == "__main__":
    unittest.main()
