#!/usr/bin/env python3
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "dingtalk-weekly-report"

EXCLUDED_PARTS = {".git", ".venv", "dist", "__pycache__"}
SENSITIVE_PATTERNS = {
    "absolute Linux home path": re.compile(r"/home/[A-Za-z0-9._-]+/"),
    "H3yun field-like ID": re.compile(r"\bF\d{7}\b"),
    "32-char internal component ID": re.compile(r"\b[0-9a-f]{32}\b"),
    "H3yun tenant query": re.compile(
        r"(?:enginecode|shardkey2|corpid)=", re.IGNORECASE),
    "organization project code": re.compile(r"\bD-(?:PD|DP)-\d{4,}\b"),
}


def public_text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or EXCLUDED_PARTS.intersection(path.parts):
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


class PublicTreeTests(unittest.TestCase):
    def test_runtime_data_is_not_in_repository_root(self):
        self.assertFalse((ROOT / "config.json").exists())
        self.assertFalse((ROOT / "weeks").exists())
        self.assertFalse((ROOT / "output").exists())

    def test_license_is_shipped_with_skill(self):
        self.assertEqual(
            (ROOT / "LICENSE").read_bytes(),
            (SKILL / "LICENSE").read_bytes(),
        )

    def test_public_template_contains_no_organization_metadata(self):
        config = json.loads(
            (SKILL / "assets/config.example.json").read_text(encoding="utf-8"))
        self.assertEqual(config["form_url"], "")
        self.assertTrue(all(not value for value in config["form_fields"].values()))
        self.assertTrue(all(
            not value for value in config["vocabulary"].values()))

    def test_public_tree_contains_no_known_sensitive_shapes(self):
        findings = []
        for path, text in public_text_files():
            for label, pattern in SENSITIVE_PATTERNS.items():
                if pattern.search(text):
                    findings.append(f"{path.relative_to(ROOT)}: {label}")
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
