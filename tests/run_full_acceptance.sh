#!/usr/bin/env bash
# 隔离 HOME 的完整自动验收：打包 → 安装 → bootstrap → 配置 → 生成附件 → 仿真暂存。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TMP=$(mktemp -d)
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT
REAL_HOME="$HOME"
export HOME="$TMP/home"
export PLAYWRIGHT_BROWSERS_PATH="${DTWR_TEST_BROWSERS_PATH:-$REAL_HOME/.cache/ms-playwright}"
mkdir -p "$HOME/.codex" "$HOME/.agents"

echo "======== 1) package + install ========"
bash pack-skill.sh >/tmp/dtwr-full-pack.out
ZIP=$(ls -1t dist/dingtalk-weekly-report-skill-*.zip | sed -n '1p')
unzip -q "$ZIP" -d "$TMP/package"
bash "$TMP/package/dingtalk-weekly-report/install.sh"
SKILL="$HOME/.claude/skills/dingtalk-weekly-report"
test -f "$SKILL/SKILL.md"
test -f "$SKILL/LICENSE"
cmp "$ROOT/LICENSE" "$SKILL/LICENSE"

echo "======== 2) bootstrap runtime ========"
bash "$SKILL/bootstrap.sh" --work "$TMP/work"
PY="$TMP/work/.venv/bin/python"
test -x "$PY"
"$PY" -c "import playwright; print('playwright runtime OK')"
DIAGNOSE_OUT="$TMP/bootstrap-diagnose.out"
bash "$SKILL/bootstrap.sh" --diagnose | tee "$DIAGNOSE_OUT"
grep -q 'runtime_diagnose=PASS' "$DIAGNOSE_OUT"
grep -q '更新 Skill 不需要重装' "$DIAGNOSE_OUT"
WARM_OUT="$TMP/bootstrap-warm.out"
bash "$SKILL/bootstrap.sh" | tee "$WARM_OUT"
grep -q '复用现有 .venv 与 Chromium' "$WARM_OUT"
if grep -q '同步 Python 运行依赖' "$WARM_OUT"; then
  echo "FAIL: 健康环境重跑 bootstrap 仍进入依赖安装阶段" >&2
  exit 1
fi
grep -q 'bootstrap_result=PASS' "$TMP/work/output/bootstrap.log"
mkdir -p "$TMP/broken-work"
if bash "$SKILL/bootstrap.sh" --work "$TMP/broken-work" --diagnose; then
  echo "FAIL: 缺 venv 的诊断不应通过" >&2
  exit 1
fi
grep -q 'bootstrap_result=FAIL stage=检查现有运行环境' \
  "$TMP/broken-work/output/bootstrap.log"

echo "======== 3) configure + validate ========"
cp "$ROOT/tests/fixtures/config.json" "$TMP/work/config.json"
mkdir -p "$TMP/work/weeks"
cp "$ROOT/tests/fixtures/week_report_20260713.json" "$TMP/work/weeks/"
DTWR_HOME="$TMP/work" "$PY" "$SKILL/scripts/configure.py" --check
DTWR_HOME="$TMP/work" DTWR_SKILL="$SKILL" "$PY" "$ROOT/tests/test_core.py"
DTWR_SKILL="$SKILL" "$PY" "$ROOT/tests/test_fill_form_logic.py"

echo "======== 4) generate outputs ========"
REPORT="$TMP/work/weeks/week_report_20260713.json"
DTWR_HOME="$TMP/work" "$PY" "$SKILL/scripts/gen_attachment.py" "$REPORT" \
  -o "$TMP/work/output"
test -f "$TMP/work/output/20260713-20260717本周工作总结与下周计划.xlsx"
DTWR_HOME="$TMP/work" "$PY" "$SKILL/scripts/print_form_rows.py" "$REPORT" >/tmp/dtwr-full-rows.out

echo "======== 5) mock draft ========"
DTWR_HOME="$TMP/work" DTWR_PYTHON="$PY" DTWR_SKILL="$SKILL" \
  bash "$ROOT/tests/run_mock_test.sh"

echo "======== FULL ACCEPTANCE PASS ========"
echo "安装、运行时、配置校验、附件、粘贴块、仿真草稿全部通过；真实钉钉由人工验收单独确认。"
