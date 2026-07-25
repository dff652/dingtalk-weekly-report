#!/usr/bin/env python3
"""扫描 **整个 Git 历史**（而不只是工作树）里的敏感形状与提交身份。

`test_public_tree.py` 只看当前工作树；2026-07-25 的教训是工作树干净、历史仍在公网可取。
本脚本扫全部 blob / commit / tag 对象内容（含提交信息），并校验提交身份。

脱敏模式复用 `test_public_tree.SENSITIVE_PATTERNS`，**不在此另写一套**。

用法:
  python3 tests/scan_history.py          # 扫全部 ref 可达对象
  python3 tests/scan_history.py --all-objects   # 连未被 ref 引用的悬空对象一起扫
退出码: 0=干净, 1=命中, 2=执行失败
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_public_tree import SENSITIVE_PATTERNS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# 公开仓的提交身份必须是 GitHub noreply，避免真实邮箱（尤其公司域名）进入公开历史。
ALLOWED_EMAIL_SUFFIX = "@users.noreply.github.com"
SCANNED_TYPES = {"blob", "commit", "tag"}  # tree 是二进制目录项，扫它只会产生噪音


def git(*args: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(ROOT)) + args,
        capture_output=True, text=True, check=True)
    return result.stdout


def iter_objects(all_objects: bool):
    """流式读出对象内容：`git cat-file --batch` 一次进程读完，不逐个 fork。"""
    if all_objects:
        listing = git("cat-file", "--batch-all-objects", "--unordered",
                      "--batch-check=%(objectname) %(objecttype)")
        shas = [parts[0] for parts in (line.split() for line in listing.splitlines())
                if len(parts) == 2 and parts[1] in SCANNED_TYPES]
    else:
        listing = git("rev-list", "--objects", "--all")
        shas = [line.split()[0] for line in listing.splitlines() if line.strip()]
    if not shas:
        return
    proc = subprocess.run(
        ("git", "-C", str(ROOT), "cat-file", "--batch"),
        input=("\n".join(shas) + "\n").encode(), capture_output=True, check=True)
    stream, pos = proc.stdout, 0
    while pos < len(stream):
        end = stream.find(b"\n", pos)
        if end == -1:
            break
        header = stream[pos:end].decode("utf-8", "replace").split()
        pos = end + 1
        if len(header) < 3:  # "<sha> missing"
            continue
        sha, otype, size = header[0], header[1], int(header[2])
        body, pos = stream[pos:pos + size], pos + size + 1
        if otype in SCANNED_TYPES:
            yield sha, otype, body.decode("utf-8", "ignore")


def scan_contents(all_objects: bool) -> list[str]:
    findings = []
    for sha, otype, text in iter_objects(all_objects):
        for label, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{otype} {sha[:12]}: {label}")
    return findings


def scan_identities() -> list[str]:
    findings = []
    seen = set()
    for line in git("log", "--all", "--pretty=%ae%n%ce").splitlines():
        email = line.strip()
        if not email or email in seen:
            continue
        seen.add(email)
        if not email.endswith(ALLOWED_EMAIL_SUFFIX):
            findings.append(
                f"提交身份 {email} 不是 {ALLOWED_EMAIL_SUFFIX}——真实邮箱不得进入公开历史")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描 Git 历史中的敏感形状与提交身份")
    parser.add_argument("--all-objects", action="store_true",
                        help="连未被 ref 引用的悬空对象一起扫（本地 gc 前的残留）")
    args = parser.parse_args()

    try:
        findings = scan_contents(args.all_objects) + scan_identities()
    except subprocess.CalledProcessError as exc:
        print(f"git 调用失败: {exc.stderr or exc}", file=sys.stderr)
        return 2

    if findings:
        print("历史扫描命中：", file=sys.stderr)
        for item in findings:
            print(f"- {item}", file=sys.stderr)
        print("\n工作树干净不代表历史干净；处置见 docs/PUBLISHING.md。", file=sys.stderr)
        return 1
    print("历史扫描通过：0 命中")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
