#!/usr/bin/env bash
# 远端发行验收：GitHub 下载 → skills CLI 安装 → bootstrap → 配置夹具 → 仿真草稿 → 安全审计门禁。
# 不触达真实氚云。要求 Node >=22.20；可用 DTWR_TEST_BROWSERS_PATH 复用可信的同版本浏览器缓存。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SOURCE="${DTWR_RELEASE_SOURCE:-https://github.com/dff652/dingtalk-weekly-report}"
REMOTE="${DTWR_RELEASE_REMOTE:-origin}"
BRANCH="${DTWR_RELEASE_BRANCH:-main}"
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git ls-remote "$REMOTE" "refs/heads/$BRANCH" | awk '{print $1}')

[ -n "$REMOTE_SHA" ] || {
  echo "FAIL: 无法读取 $REMOTE/$BRANCH" >&2
  exit 1
}
if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
  echo "FAIL: 本地 HEAD $LOCAL_SHA != 远端 $REMOTE_SHA；先 push 再验收" >&2
  exit 1
fi
if [ "${DTWR_ALLOW_DIRTY:-0}" != "1" ] && {
    ! git diff --quiet || ! git diff --cached --quiet
  }; then
  echo "FAIL: 工作树有未提交改动；发行验收必须对应确定提交" >&2
  exit 1
fi

command -v node >/dev/null 2>&1 || {
  echo "FAIL: 未找到 Node.js；skills@1.5.20 需要 Node >=22.20.0" >&2
  exit 1
}
if ! node -e '
  const [major, minor] = process.versions.node.split(".").map(Number);
  process.exit(major > 22 || (major === 22 && minor >= 20) ? 0 : 1);
'; then
  echo "FAIL: Node $(node -v) 过旧；skills@1.5.20 需要 >=22.20.0" >&2
  exit 1
fi
command -v uv >/dev/null 2>&1 || {
  echo "FAIL: 未找到 uv；按 https://docs.astral.sh/uv/getting-started/installation/ 安装" >&2
  exit 1
}

TMP=$(mktemp -d)
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT
REAL_HOME="$HOME"
export HOME="$TMP/home"
export PLAYWRIGHT_BROWSERS_PATH="${DTWR_TEST_BROWSERS_PATH:-$REAL_HOME/.cache/ms-playwright}"
mkdir -p "$HOME/.codex" "$HOME/.agents"

echo "======== 1) remote identity ========"
echo "commit=$LOCAL_SHA source=$SOURCE"

echo "======== 2) GitHub download + skills CLI install ========"
INSTALL_LOG="$TMP/skills-add.log"
npx --yes skills add "$SOURCE" \
  --skill dingtalk-weekly-report \
  --agent claude-code \
  --agent codex \
  --global --yes --copy 2>&1 | tee "$INSTALL_LOG"
npx --yes skills list --global

SKILL="$HOME/.agents/skills/dingtalk-weekly-report"
test -f "$SKILL/SKILL.md"
diff -qr --exclude="__pycache__" \
  "$ROOT/skills/dingtalk-weekly-report" "$SKILL"
echo "OK remote skill matches commit $LOCAL_SHA"

AUDIT_LOG="$TMP/skills-audit.txt"
sed -E 's/\x1B\[[0-9;?]*[ -/]*[@-~]//g' "$INSTALL_LOG" > "$AUDIT_LOG"
AUDIT_STATUS=PASS
if grep -Eq 'Critical Risk|High Risk' "$AUDIT_LOG"; then
  AUDIT_STATUS=FAIL
elif ! grep -q 'Security Risk Assessments' "$AUDIT_LOG"; then
  AUDIT_STATUS=UNKNOWN
fi

echo "======== 3) bootstrap installed skill ========"
bash "$SKILL/bootstrap.sh" --work "$TMP/work"
PY="$TMP/work/.venv/bin/python"
test -x "$PY"
"$PY" -c "import playwright; print('playwright runtime OK')"
test "$(cat "$HOME/.config/dtwr/root")" = "$TMP/work"

echo "======== 4) configure + validate installed skill ========"
cp "$ROOT/tests/fixtures/config.json" "$TMP/work/config.json"
mkdir -p "$TMP/work/weeks"
cp "$ROOT/tests/fixtures/week_report_20260713.json" "$TMP/work/weeks/"
DTWR_HOME="$TMP/work" DTWR_SKILL="$SKILL" "$PY" "$ROOT/tests/test_core.py"
DTWR_SKILL="$SKILL" "$PY" "$ROOT/tests/test_fill_form_logic.py"

echo "======== 5) outputs + mock draft ========"
REPORT="$TMP/work/weeks/week_report_20260713.json"
DTWR_HOME="$TMP/work" "$PY" "$SKILL/scripts/gen_attachment.py" "$REPORT" \
  -o "$TMP/work/output"
test -f "$TMP/work/output/20260713-20260717本周工作总结与下周计划.xlsx"
DTWR_HOME="$TMP/work" "$PY" "$SKILL/scripts/print_form_rows.py" "$REPORT" \
  > "$TMP/form-rows.txt"
DTWR_HOME="$TMP/work" DTWR_PYTHON="$PY" DTWR_SKILL="$SKILL" \
  bash "$ROOT/tests/run_mock_test.sh"

echo "======== 6) skills.sh audit gate ========"
case "$AUDIT_STATUS" in
  PASS)
    echo "OK no Critical/High risk in install output"
    ;;
  FAIL)
    grep -E 'Security Risk Assessments|Critical Risk|High Risk|Details:' "$AUDIT_LOG" || true
    echo "FAIL: skills.sh 仍报告 Critical/High；等待重扫或处理告警" >&2
    exit 1
    ;;
  UNKNOWN)
    echo "FAIL: 安装输出没有 Security Risk Assessments，无法完成发行安全验收" >&2
    exit 1
    ;;
esac

echo "======== RELEASE ACCEPTANCE PASS ========"
echo "远端提交、下载、安装、运行时、配置、输出、仿真草稿与安全审计全部通过。"
