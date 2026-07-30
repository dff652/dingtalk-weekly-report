#!/usr/bin/env python3
"""README 视觉资产的结构、安全与跨平台渲染门禁。"""
import re
import struct
import unittest
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "readme"
SVG_NS = {"svg": "http://www.w3.org/2000/svg"}
SVG_SPECS = {
    "hero.svg": (1200, 400),
    "workflow.svg": (1200, 520),
    "social-preview.svg": (1280, 640),
}
CJK_FONT_STACK = (
    "'Noto Sans CJK SC', 'PingFang SC', 'Microsoft YaHei', sans-serif")
ALLOWED_COLORS = {
    "#0B1220", "#111B2D", "#246BDE", "#26354C", "#607086",
    "#9FB0C7", "#A56A00", "#D7DDE6", "#F4B740", "#F7F4EC", "#FFFFFF",
}


def contrast_ratio(first, second):
    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255
                    for index in (1, 3, 5)]
        linear = [
            value / 12.92 if value <= 0.04045
            else ((value + 0.055) / 1.055) ** 2.4
            for value in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class ReadmeAssetTests(unittest.TestCase):
    def test_svg_structure_fonts_and_palette(self):
        for filename, (width, height) in SVG_SPECS.items():
            with self.subTest(filename=filename):
                path = ASSETS / filename
                source = path.read_text(encoding="utf-8")
                root = ElementTree.fromstring(source)
                self.assertEqual(root.attrib["width"], str(width))
                self.assertEqual(root.attrib["height"], str(height))
                self.assertEqual(
                    root.attrib["viewBox"], f"0 0 {width} {height}")
                self.assertEqual(root.attrib["role"], "img")
                self.assertEqual(root.attrib["aria-labelledby"], "title desc")
                self.assertIsNotNone(root.find("svg:title", SVG_NS))
                self.assertIsNotNone(root.find("svg:desc", SVG_NS))
                self.assertIn(CJK_FONT_STACK, source)

                weights = {
                    element.attrib["font-weight"]
                    for element in root.iter()
                    if "font-weight" in element.attrib
                }
                self.assertLessEqual(weights, {"400", "700"})

                colors = set(re.findall(r"#[0-9A-Fa-f]{6}", source))
                self.assertLessEqual(colors, ALLOWED_COLORS)

    def test_svg_has_no_fragile_or_remote_features(self):
        forbidden_tags = {"script", "foreignObject", "style", "image"}
        for filename in SVG_SPECS:
            with self.subTest(filename=filename):
                root = ElementTree.parse(ASSETS / filename).getroot()
                for element in root.iter():
                    local_name = element.tag.rsplit("}", 1)[-1]
                    self.assertNotIn(local_name, forbidden_tags)
                    for name, value in element.attrib.items():
                        if name.rsplit("}", 1)[-1] == "href":
                            self.assertFalse(value.startswith(("http:", "https:")))

    def test_key_text_contrast_is_at_least_4_5_to_1(self):
        pairs = {
            "warm white on navy": ("#F7F4EC", "#0B1220"),
            "light muted on navy": ("#9FB0C7", "#0B1220"),
            "ink on warm white": ("#111B2D", "#F7F4EC"),
            "muted on warm white": ("#607086", "#F7F4EC"),
            "warm white on blue": ("#F7F4EC", "#246BDE"),
            "navy on amber": ("#0B1220", "#F4B740"),
        }
        for label, colors in pairs.items():
            with self.subTest(label=label):
                self.assertGreaterEqual(contrast_ratio(*colors), 4.5)

    def test_social_preview_png_dimensions_and_size(self):
        path = ASSETS / "social-preview.png"
        data = path.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", data[16:24]), (1280, 640))
        self.assertLess(len(data), 1_000_000)


if __name__ == "__main__":
    unittest.main()
