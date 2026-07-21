#!/usr/bin/env bash
# 本地仿真表单 e2e：跑 fill_form.py 全流程（含提交），断言各字段真的填进去了。
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=$(.venv/bin/python fill_form.py weeks/week_report_20260713.json \
      --url "file://$PWD/tests/mock_form.html" --submit 2>&1) || { echo "$OUT"; exit 1; }
echo "$OUT" | grep -v MOCK_RESULT | tail -3
RESULT=$(echo "$OUT" | grep "^MOCK_RESULT:" | sed 's/^MOCK_RESULT: //')

.venv/bin/python - "$RESULT" <<'EOF'
import json, sys
r = json.loads(sys.argv[1])
report = json.load(open("weeks/week_report_20260713.json", encoding="utf-8"))
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
