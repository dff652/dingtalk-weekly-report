#!/usr/bin/env python3
"""在线入口离线验证：下载失败不覆盖，重复执行能更新 Codex 安装。"""
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "install-online.sh"
SKILL = ROOT / "skills" / "dingtalk-weekly-report"


class InstallOnlineTests(unittest.TestCase):
    def test_codex_install_update_and_failed_download(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "home"
            home.mkdir()
            archive = base / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                bundle.add(ROOT / "install.sh", "repo/install.sh")
                bundle.add(SKILL, "repo/skills/dingtalk-weekly-report")

            fake_bin = base / "bin"
            fake_bin.mkdir()
            fake_curl = fake_bin / "curl"
            fake_curl.write_text(
                "#!/bin/sh\n"
                "while [ \"$#\" -gt 0 ]; do\n"
                "  if [ \"$1\" = --output ]; then output=$2; shift 2; else shift; fi\n"
                "done\n"
                "cp \"$DTWR_TEST_ARCHIVE\" \"$output\"\n"
            )
            fake_curl.chmod(0o755)
            env = os.environ | {
                "HOME": str(home),
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
                "DTWR_TEST_ARCHIVE": str(archive),
            }

            def run(*args, test_env=env):
                return subprocess.run(
                    ["bash", str(SCRIPT), "--codex-only", "--skill-only", *args],
                    env=test_env, capture_output=True, text=True,
                )

            installed = home / ".codex/skills/dingtalk-weekly-report/VERSION"
            first = run()
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(installed.read_text(), (SKILL / "VERSION").read_text())

            installed.write_text("locally stale\n")
            update = run()
            self.assertEqual(update.returncode, 0, update.stdout + update.stderr)
            self.assertEqual(installed.read_text(), (SKILL / "VERSION").read_text())

            failed = run(test_env=env | {"DTWR_TEST_ARCHIVE": str(base / "missing")})
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(installed.read_text(), (SKILL / "VERSION").read_text())

    def test_rejects_invalid_ref_before_install(self):
        result = subprocess.run(
            ["bash", str(SCRIPT), "--ref", "bad;command", "--skill-only"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("非法 ref", result.stderr)


if __name__ == "__main__":
    unittest.main()
