#!/usr/bin/env bash
# 打包技能分发物：只含 skills/dingtalk-weekly-report/（代码+模板+事实源），不含任何个人数据。
# 产物: dist/dingtalk-weekly-report-skill-YYYYMMDD.zip
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dist
OUT="dist/dingtalk-weekly-report-skill-$(date +%Y%m%d).zip"
rm -f "$OUT"
zip -rq "$OUT" skills/dingtalk-weekly-report install.sh \
  -x '*__pycache__*' -x '*.pyc'
echo "分发物: $OUT"
unzip -l "$OUT" | tail -3
cat <<'EOF'
给同事的两行安装说明:
  unzip dingtalk-weekly-report-skill-*.zip -d dtwr && bash dtwr/install.sh
  然后打开 Claude Code 输 /dingtalk-weekly-report 按引导走。
注意: 包内含公司表单结构信息(FIELDS.md/form_url), 仅限公司内部分发。
EOF
