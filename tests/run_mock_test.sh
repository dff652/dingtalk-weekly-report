#!/usr/bin/env bash
# 本地仿真表单 e2e：只落草稿，断言各字段真的填进去了。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TMP=$(mktemp -d)
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT
mkdir -p "$TMP/work/weeks"
cp tests/fixtures/config.json "$TMP/work/config.json"
cp tests/fixtures/week_report_20260713.json "$TMP/work/weeks/"

PY="${DTWR_PYTHON:-$ROOT/.venv/bin/python}"
SKILL="${DTWR_SKILL:-$ROOT/skills/dingtalk-weekly-report}"
REPORT="$TMP/work/weeks/week_report_20260713.json"
DTWR_HOME="$TMP/work" python3 "$SKILL/scripts/gen_attachment.py" "$REPORT" \
  -o "$TMP/work/output"

OUT=$(DTWR_HOME="$TMP/work" "$PY" "$SKILL/scripts/fill_form.py" "$REPORT" \
      --url "file://$ROOT/tests/mock_form.html" --draft --confirmed 2>&1) \
      || { echo "$OUT"; exit 1; }
echo "$OUT" | grep -v MOCK_RESULT | tail -3
RESULT=$(echo "$OUT" | grep "^MOCK_RESULT:" | sed 's/^MOCK_RESULT: //')

"$PY" - "$RESULT" "$REPORT" <<'EOF'
import json, sys
r = json.loads(sys.argv[1])
report = json.load(open(sys.argv[2], encoding="utf-8"))
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
print(f"MOCK e2e PASS: {len(r['rows'])} 行全部字段断言通过")
EOF
