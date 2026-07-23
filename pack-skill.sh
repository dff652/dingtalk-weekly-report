#!/usr/bin/env bash
# 打包技能分发物：平铺自安装目录 dingtalk-weekly-report/（含 install.sh），不含个人数据。
# 产物: dist/dingtalk-weekly-report-skill-YYYYMMDD.zip
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dist
OUT="dist/dingtalk-weekly-report-skill-$(date +%Y%m%d).zip"
rm -f "$OUT"
# zip 根目录即为技能包名，解压后 bash dingtalk-weekly-report/install.sh
(cd skills && zip -rq "../$OUT" dingtalk-weekly-report \
  -x '*__pycache__*' -x '*.pyc')
echo "分发物: $OUT"
unzip -l "$OUT" | head -20
echo "..."
unzip -l "$OUT" | tail -3
cat <<'EOF'
给同事的两行安装说明:
  unzip dingtalk-weekly-report-skill-*.zip && bash dingtalk-weekly-report/install.sh
  然后打开 Claude Code 输 /dingtalk-weekly-report 按引导走。
维护仓软链装载:
  bash install.sh --link
注意: 包内含公司表单结构信息(FIELDS.md/form_url), 仅限公司内部分发。
EOF
