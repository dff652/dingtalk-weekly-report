#!/usr/bin/env python3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "dingtalk-weekly-report" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from runtime_check import parse_exact_requirements


class RuntimeCheckTests(unittest.TestCase):
    def test_parse_exact_requirements_accepts_pins_and_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            requirements = Path(directory) / "requirements.txt"
            requirements.write_text(
                "# runtime\nplaywright==1.61.0\n"
                "typing-extensions==4.16.0  # compatibility\n",
                encoding="utf-8")
            self.assertEqual(
                parse_exact_requirements(requirements),
                [
                    ("playwright", "1.61.0"),
                    ("typing-extensions", "4.16.0"),
                ])

    def test_parse_exact_requirements_rejects_unpinned_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            requirements = Path(directory) / "requirements.txt"
            requirements.write_text("playwright>=1.61\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "不是精确版本"):
                parse_exact_requirements(requirements)


if __name__ == "__main__":
    unittest.main()
