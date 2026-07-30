#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""版本号与许可证标识的一致性门禁。

`skills/dingtalk-weekly-report/VERSION` 是版本号的**单一事实源**；CHANGELOG 最新的
已发布条目必须与它一致，否则「发了新行为却没人知道变了什么」（本项目 2026-07-25
的附件行为变更就是活例）。

git tag 一致性**不在这里断言**：开发期先改 VERSION、发布时才打 tag，两者必然有一段
不一致的窗口。tag 是发布时门禁，由 `pack-skill.sh` 负责——未打 tag 的产物会被标成
dev 构建，不会冒充发行版。
"""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "dingtalk-weekly-report"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
RELEASED_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", re.M)
SPDX = "SPDX-License-Identifier: Apache-2.0"

# 随技能包分发或参与安装的脚本，必须带 SPDX 标识。
def distributed_scripts():
    yield from sorted(SKILL.glob("scripts/*.py"))
    yield from sorted(SKILL.glob("*.sh"))
    yield from sorted(SKILL.glob("*.ps1"))
    yield ROOT / "install.sh"
    yield ROOT / "pack-skill.sh"


class VersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.version = (SKILL / "VERSION").read_text(encoding="utf-8").strip()
        cls.changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    def test_version_is_semver(self):
        self.assertRegex(self.version, SEMVER)

    def test_changelog_latest_release_matches_version(self):
        releases = RELEASED_HEADING.findall(self.changelog)
        self.assertTrue(releases, "CHANGELOG 里没有任何已发布条目")
        self.assertEqual(
            releases[0][0], self.version,
            "CHANGELOG 最新条目与 VERSION 不一致——改了版本号就要写变更记录")

    def test_changelog_keeps_unreleased_section(self):
        self.assertIn("## [Unreleased]", self.changelog)

    def test_distributed_scripts_carry_spdx_identifier(self):
        missing = [
            str(path.relative_to(ROOT))
            for path in distributed_scripts()
            if SPDX not in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(missing, [])

    def test_shebang_stays_on_first_line(self):
        """SPDX 头不得插到 shebang 前面，否则脚本直接执行会失效。"""
        broken = []
        for path in distributed_scripts():
            lines = path.read_text(encoding="utf-8").split("\n")
            if any(line.startswith("#!") for line in lines[:3]) and not lines[0].startswith("#!"):
                broken.append(str(path.relative_to(ROOT)))
        self.assertEqual(broken, [])

    @unittest.skipUnless(shutil.which("git") and shutil.which("zip"),
                         "需要 git 与 zip")
    def test_pack_marks_clean_head_ahead_of_tag_as_dev(self):
        """旧版本 tag 仍存在时，较新的干净 HEAD 也不得冒充该正式版本。"""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            skill = repo / "skills" / "dingtalk-weekly-report"
            skill.mkdir(parents=True)
            shutil.copy2(ROOT / "pack-skill.sh", repo / "pack-skill.sh")
            (skill / "VERSION").write_text("0.3.0\n", encoding="utf-8")
            (skill / "SKILL.md").write_text("---\nname: test\n---\n", encoding="utf-8")

            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=repo, check=True,
                    text=True, capture_output=True).stdout.strip()

            git("init", "-q")
            git("config", "user.name", "test")
            git("config", "user.email", "test@example.invalid")
            git("add", ".")
            git("commit", "-qm", "tagged release")
            git("tag", "v0.3.0")
            (repo / "AFTER_TAG").write_text("new head\n", encoding="utf-8")
            git("add", "AFTER_TAG")
            git("commit", "-qm", "head moved")

            subprocess.run(
                ["bash", "pack-skill.sh"], cwd=repo, check=True,
                text=True, capture_output=True)
            short_head = git("rev-parse", "--short", "HEAD")
            self.assertTrue(
                (repo / "dist" /
                 f"dingtalk-weekly-report-skill-v0.3.0-dev.{short_head}.zip").is_file())
            self.assertFalse(
                (repo / "dist" / "dingtalk-weekly-report-skill-v0.3.0.zip").exists())


if __name__ == "__main__":
    unittest.main()
