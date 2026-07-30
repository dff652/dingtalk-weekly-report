#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""只读检查 Skill 运行环境；不安装、不下载、不修改配置或登录态。"""
import importlib.metadata
import re
import sys
from pathlib import Path


EXACT_REQUIREMENT = re.compile(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)$")


def parse_exact_requirements(path):
    pins = []
    for lineno, raw in enumerate(
            Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        match = EXACT_REQUIREMENT.fullmatch(line)
        if not match:
            raise ValueError(
                f"requirements-runtime.txt 第 {lineno} 行不是精确版本: {line}")
        pins.append(match.groups())
    if not pins:
        raise ValueError("requirements-runtime.txt 没有运行依赖")
    return pins


def check_runtime(requirements_path):
    pins = parse_exact_requirements(requirements_path)
    installed = []
    for package, expected in pins:
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            raise RuntimeError(f"缺少 Python 包 {package}=={expected}") from None
        if actual != expected:
            raise RuntimeError(
                f"{package} 版本不匹配：需要 {expected}，当前 {actual}")
        installed.append(f"{package}=={actual}")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            executable = Path(playwright.chromium.executable_path)
            if not executable.is_file():
                raise RuntimeError("Playwright Chromium 缓存不存在")
            browser = playwright.chromium.launch(headless=True)
            browser.close()
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Playwright Chromium 无法启动：{type(exc).__name__}: {exc}") from None
    return installed


def main():
    if len(sys.argv) != 2:
        sys.exit(f"用法: {Path(sys.argv[0]).name} requirements-runtime.txt")
    print(f"runtime_python={sys.executable}")
    try:
        installed = check_runtime(sys.argv[1])
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"runtime_diagnose=FAIL reason={exc}")
        return 1
    print(f"runtime_requirements=PASS {' '.join(installed)}")
    print("runtime_chromium=PASS headless launch")
    print("runtime_diagnose=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
