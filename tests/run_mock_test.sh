#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# 本地仿真表单 e2e：只落草稿，断言各字段真的填进去了。
#
# 氚云有**两套并存的前端**（旧版 FormAdapter iframe / 2026-09 起的新版 nx 主 frame），
# 两套的控件形态完全不同，所以两份仿真页都要跑——只回归其中一套，另一套碎了不会变红。
# 用法: run_mock_test.sh [mock_form.html ...]   # 省略=两套都跑
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MOCKS=("$@")
if [ ${#MOCKS[@]} -eq 0 ]; then
  MOCKS=("tests/mock_form.html" "tests/mock_form_nx.html")
fi

# 每份仿真页**必须**跑到它对应的 UI 分支。只断言字段值是不够的：新版仿真页若因探测
# 失误回落到旧版分支，字段照样填得出来、测试照样绿——那就成了「门还在响但已经不看
# 新版了」的假绿。所以按文件名钉死期望形态。
expected_ui() {
  case "$1" in
    *_nx.html) echo "nx" ;;
    *) echo "legacy" ;;
  esac
}

PY="${DTWR_PYTHON:-$ROOT/.venv/bin/python}"
SKILL="${DTWR_SKILL:-$ROOT/skills/dingtalk-weekly-report}"

for MOCK in "${MOCKS[@]}"; do
  [ -f "$MOCK" ] || { echo "仿真页不存在: $MOCK" >&2; exit 1; }
  echo "=== 仿真 e2e: $MOCK ==="

  TMP=$(mktemp -d)
  mkdir -p "$TMP/work/weeks"
  cp tests/fixtures/config.json "$TMP/work/config.json"
  # 用 12 行分页 fixture（>10 行触发子表分页）：覆盖面是 5 行 fixture 的超集，
  # 额外回归「第 11 行新增即翻页」的真机坑；5 行 fixture 仍由 test_core/smoke 使用。
  cp tests/fixtures/week_report_20260713_paged.json \
    "$TMP/work/weeks/week_report_20260713.json"

  REPORT="$TMP/work/weeks/week_report_20260713.json"
  DTWR_HOME="$TMP/work" python3 "$SKILL/scripts/gen_attachment.py" "$REPORT" \
    -o "$TMP/work/output"

  OUT=$(DTWR_HOME="$TMP/work" "$PY" "$SKILL/scripts/fill_form.py" "$REPORT" \
        --url "file://$ROOT/$MOCK" --draft --confirmed 2>&1) \
        || { echo "$OUT"; rm -rf "$TMP"; exit 1; }
  echo "$OUT" | grep -v MOCK_RESULT | tail -3
  WANT_UI="$(expected_ui "$MOCK")"
  if ! echo "$OUT" | grep -q "表单形态: $WANT_UI"; then
    echo "$OUT"
    echo "❌ $MOCK 没有跑到期望的 UI 分支（期望 $WANT_UI）" >&2
    rm -rf "$TMP"; exit 1
  fi
  RESULT=$(echo "$OUT" | grep "^MOCK_RESULT:" | sed 's/^MOCK_RESULT: //')

  "$PY" - "$RESULT" "$REPORT" "$MOCK" <<'EOF'
import json, sys
r = json.loads(sys.argv[1])
report = json.load(open(sys.argv[2], encoding="utf-8"))
mock = sys.argv[3]
assert r["kind"] == "draft", f"动作错: {r['kind']}"
assert r["start"] == report["week"]["start"], f"开始日期错: {r['start']}"
assert r["attach"].endswith("本周工作总结与下周计划.xlsx"), f"附件错: {r['attach']}"
assert len(r["rows"]) == len(report["days"]), f"行数错: {len(r['rows'])} != {len(report['days'])}"
for got, want in zip(r["rows"], report["days"]):
    f = got.split("|")
    assert f[0] == want["date"], f"日期错: {f[0]}"
    assert f[1] == want["project_type"], f"项目类型错: {f[1]}"
    if want.get("project"):
        assert f[2] == want["project"], f"项目错: {f[2]}"
    assert f[3] == want["status"], f"状态错: {f[3]}"
    assert f[4] == str(want["hours"]), f"工时错: {f[4]}"
    assert f[5] == want["content"][:24], f"内容错: {f[5]}"
print(f"MOCK e2e PASS ({mock}): {len(r['rows'])} 行全部字段断言通过")
EOF
  rm -rf "$TMP"
done
