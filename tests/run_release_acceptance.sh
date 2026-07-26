#!/usr/bin/env bash
# 远端发行验收：GitHub 下载 → skills CLI 安装 → bootstrap → 配置夹具 → 仿真草稿 → 安全审计门禁。
# 不触达真实氚云。要求 Node >=22.20；可用 DTWR_TEST_BROWSERS_PATH 复用可信的同版本浏览器缓存。
# 安全审计门禁依赖 skills@1.5.20 的英文输出结构；升级版本时必须同步复验下方解析规则。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SOURCE="${DTWR_RELEASE_SOURCE:-https://github.com/dff652/dingtalk-weekly-report}"
REMOTE="${DTWR_RELEASE_REMOTE:-origin}"
BRANCH="${DTWR_RELEASE_BRANCH:-main}"
SKILLS_CLI_PACKAGE="skills@1.5.20"
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
npx --yes "$SKILLS_CLI_PACKAGE" add "$SOURCE" \
  --skill dingtalk-weekly-report \
  --agent claude-code \
  --agent codex \
  --global --yes --copy 2>&1 | tee "$INSTALL_LOG"
npx --yes "$SKILLS_CLI_PACKAGE" list --global

AGENTS_SKILL="$HOME/.agents/skills/dingtalk-weekly-report"
CLAUDE_SKILL="$HOME/.claude/skills/dingtalk-weekly-report"
if [ -f "$AGENTS_SKILL/SKILL.md" ]; then
  SKILL="$AGENTS_SKILL"
elif [ -f "$CLAUDE_SKILL/SKILL.md" ]; then
  SKILL="$CLAUDE_SKILL"
else
  echo "FAIL: .agents 与 .claude 均未发现已安装的 dingtalk-weekly-report" >&2
  exit 1
fi
test -f "$SKILL/LICENSE"
cmp "$ROOT/LICENSE" "$SKILL/LICENSE"
if [ -f "$AGENTS_SKILL/SKILL.md" ] && [ -f "$CLAUDE_SKILL/SKILL.md" ]; then
  diff -qr --exclude="__pycache__" "$AGENTS_SKILL" "$CLAUDE_SKILL"
  echo "OK .agents and .claude skill copies match"
fi
diff -qr --exclude="__pycache__" \
  "$ROOT/skills/dingtalk-weekly-report" "$SKILL"
echo "OK remote skill at $SKILL matches commit $LOCAL_SHA"

AUDIT_LOG="$TMP/skills-audit.txt"
sed -E 's/\x1B\[[0-9;?]*[ -/]*[@-~]//g' "$INSTALL_LOG" > "$AUDIT_LOG"

# 门禁语义 = 「本 skill 的评级相对已复审基线有没有变」，不是「评级干不干净」。
# 本 skill 的告警来自固有能力（浏览器自动化 + 登录态 + 安装期拉依赖），追求 PASS 不现实；
# 恒红的门禁等于没有门禁，只会逼人加 override。
# 旧实现是整日志 grep 'Critical Risk|High Risk'，两个毛病：
#   1) 不限定本 skill 那一行——同批安装的其它 skill 的评级会让我们的验收失败；
#   2) CLI 那一列印的字样与平台页面的实际 RISK LEVEL 不一致（CLI 写 Critical Risk，
#      页面写 MEDIUM），拿它当严重度判据本身就不可靠。
AUDIT_BASELINE="$ROOT/tests/fixtures/expected-audit-row.txt"
AUDIT_ROW=$(grep -F 'dingtalk-weekly-report' "$AUDIT_LOG" | grep -F '│' \
  | grep -E 'Safe|Risk|alert|Warn|Critical|High|Medium|Low' | tail -1 \
  | tr -d '│' | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//')
AUDIT_EXPECTED=$(grep -vE '^[[:space:]]*#|^[[:space:]]*$' "$AUDIT_BASELINE" | head -1)

AUDIT_STATUS=PASS
if ! grep -q 'Security Risk Assessments' "$AUDIT_LOG" || [ -z "$AUDIT_ROW" ]; then
  AUDIT_STATUS=UNKNOWN
elif [ "$AUDIT_ROW" != "$AUDIT_EXPECTED" ]; then
  AUDIT_STATUS=FAIL
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
    echo "OK 评级与已复审基线一致: $AUDIT_ROW"
    ;;
  FAIL)
    echo "实际: $AUDIT_ROW" >&2
    echo "基线: $AUDIT_EXPECTED" >&2
    grep -E 'Security Risk Assessments|Details:' "$AUDIT_LOG" || true
    echo "FAIL: skills.sh 评级与基线不符；去 Details 链接看告警原文，人工复审后再更新" >&2
    echo "      $AUDIT_BASELINE（含复审结论，勿盲目覆盖）" >&2
    exit 1
    ;;
  UNKNOWN)
    echo "FAIL: 安装输出缺 Security Risk Assessments 或取不到本 skill 的评级行，无法完成发行安全验收" >&2
    exit 1
    ;;
esac

echo "======== RELEASE ACCEPTANCE PASS ========"
echo "远端提交、下载、安装、运行时、配置、输出、仿真草稿与安全审计全部通过。"
