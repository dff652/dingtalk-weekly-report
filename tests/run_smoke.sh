#!/usr/bin/env bash
# 维护仓冒烟：打包 → 隔离安装 → 附件生成 → 粘贴块 → 仿真 e2e
# 不触达真实氚云登录/落草稿。用法: bash tests/run_smoke.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REAL_HOME="${HOME}"

echo "======== 1) pack-skill ========"
bash pack-skill.sh >/tmp/dtwr-pack.out
ZIP=$(ls -1t dist/dingtalk-weekly-report-skill-*.zip | head -1)
test -f "$ZIP"
echo "OK zip=$ZIP"

echo "======== 2) isolated install ========"
TMP=$(mktemp -d)
cleanup() { rm -rf "$TMP" /tmp/dtwr-smoke-out 2>/dev/null || true; }
trap cleanup EXIT
unzip -q "$ZIP" -d "$TMP"
export HOME="$TMP/home"
mkdir -p "$HOME/.codex" "$HOME/.agents"
bash "$TMP/dingtalk-weekly-report/install.sh"
test -f "$HOME/.claude/skills/dingtalk-weekly-report/SKILL.md"
test -f "$HOME/.codex/skills/dingtalk-weekly-report/SKILL.md"
test -f "$HOME/.agents/skills/dingtalk-weekly-report/SKILL.md"
echo "OK install Claude+Codex+Agents"
export HOME="$REAL_HOME"

echo "======== 3) gen_attachment + print_form_rows ========"
cd "$ROOT"
WEEK_JSON=weeks/week_report_20260713.json
test -f "$WEEK_JSON"
mkdir -p /tmp/dtwr-smoke-out
python3 skills/dingtalk-weekly-report/scripts/gen_attachment.py "$WEEK_JSON" -o /tmp/dtwr-smoke-out
ls /tmp/dtwr-smoke-out/*本周工作总结与下周计划.xlsx >/dev/null
python3 skills/dingtalk-weekly-report/scripts/print_form_rows.py "$WEEK_JSON" | head -15
echo "OK attachment + print_form_rows"

echo "======== 4) extract_week refuse-overwrite ========"
set +e
OUT=$(python3 skills/dingtalk-weekly-report/scripts/extract_week.py 2026-07-13 2>&1)
RC=$?
set -e
echo "$OUT" | head -3
if [ "$RC" -ne 0 ] && echo "$OUT" | grep -q "拒绝覆盖\|已存在"; then
  echo "OK extract_week 拒绝覆盖 (exit=$RC)"
else
  echo "FAIL: 期望拒绝覆盖已存在 json, exit=$RC" >&2
  echo "$OUT" >&2
  exit 1
fi

echo "======== 5) mock form e2e ========"
bash tests/run_mock_test.sh
echo "======== SMOKE PASS ========"
