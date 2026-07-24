#!/usr/bin/env bash
# 维护仓冒烟：打包 → 隔离安装 → 单元测试 → 附件/抽取 → 仿真草稿 e2e
# 不触达真实氚云登录/落草稿。用法: bash tests/run_smoke.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REAL_HOME="${HOME}"

echo "======== 1) pack-skill ========"
bash pack-skill.sh >/tmp/dtwr-pack.out
ZIP=$(ls -1t dist/dingtalk-weekly-report-skill-*.zip | sed -n '1p')
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

echo "======== 3) core tests ========"
cd "$ROOT"
python3 tests/test_core.py
.venv/bin/python tests/test_fill_form_logic.py
(
  cd /tmp
  python3 "$ROOT/skills/dingtalk-weekly-report/scripts/extract_week.py" --help \
    | grep -q "用法"
  "$ROOT/.venv/bin/python" \
    "$ROOT/skills/dingtalk-weekly-report/scripts/fill_form.py" --help \
    | grep -q "usage:"
)
echo "OK help works without workdir"
HELP=$(.venv/bin/python skills/dingtalk-weekly-report/scripts/fill_form.py --help)
if echo "$HELP" | grep -q -- "--submit"; then
  echo "FAIL: fill_form 仍暴露 --submit" >&2
  exit 1
fi
if DTWR_HOME="$ROOT/tests/fixtures" .venv/bin/python \
    skills/dingtalk-weekly-report/scripts/fill_form.py \
    tests/fixtures/week_report_20260713.json --draft \
    --url "file://$ROOT/tests/mock_form.html" >/tmp/dtwr-guard.out 2>&1; then
  echo "FAIL: --draft 未带 --confirmed 仍可执行" >&2
  exit 1
fi
grep -q -- "--draft 必须同时提供 --confirmed" /tmp/dtwr-guard.out
echo "OK no-submit + explicit-confirm guards"

echo "======== 4) gen_attachment + print_form_rows ========"
cd "$ROOT"
WEEK_JSON=tests/fixtures/week_report_20260713.json
test -f "$WEEK_JSON"
mkdir -p /tmp/dtwr-smoke-out
python3 skills/dingtalk-weekly-report/scripts/gen_attachment.py "$WEEK_JSON" -o /tmp/dtwr-smoke-out
ls /tmp/dtwr-smoke-out/*本周工作总结与下周计划.xlsx >/dev/null
python3 skills/dingtalk-weekly-report/scripts/print_form_rows.py "$WEEK_JSON" | sed -n '1,15p'
echo "OK attachment + print_form_rows"

echo "======== 5) extract_week blank-source scaffold ========"
EXTRACT_WORK="$TMP/extract-work"
mkdir -p "$EXTRACT_WORK"
cp tests/fixtures/config.json "$EXTRACT_WORK/config.json"
DTWR_HOME="$EXTRACT_WORK" python3 skills/dingtalk-weekly-report/scripts/extract_week.py 2026-07-13
grep -q "TODO" "$EXTRACT_WORK/weeks/week_report_20260713.json"
echo "OK blank progress_report -> TODO scaffold"

echo "======== 6) mock form draft e2e ========"
bash tests/run_mock_test.sh
echo "======== SMOKE PASS ========"
