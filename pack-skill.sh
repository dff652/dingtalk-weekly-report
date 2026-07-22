#!/usr/bin/env bash
# 打包技能分发物：只含 skills/dingtalk-weekly-report/（代码+模板+事实源），不含任何个人数据。
# 产物: dist/dingtalk-weekly-report-skill-YYYYMMDD.zip
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dist
OUT="dist/dingtalk-weekly-report-skill-$(date +%Y%m%d).zip"
rm -f "$OUT"
zip -rq "$OUT" skills/dingtalk-weekly-report \
  -x '*__pycache__*' -x '*.pyc'
echo "分发物: $OUT"
unzip -l "$OUT" | tail -3
cat <<'EOF'
给同事的一句话安装说明:
  解压后把 skills/dingtalk-weekly-report/ 放到 ~/.claude/skills/ 下,
  在 Claude Code 里输 /dingtalk-weekly-report, 按引导完成首次安装即可。
注意: 包内含公司表单结构信息(FIELDS.md/form_url), 仅限公司内部分发。
EOF
