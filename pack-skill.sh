#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# 打包技能分发物：平铺自安装目录 dingtalk-weekly-report/（含 install.sh），不含个人数据。
# 产物: dist/dingtalk-weekly-report-skill-v<VERSION>.zip
#       未打 tag 或工作区有改动时命名为 …-v<VERSION>-dev.<sha>.zip
# 版本号单一事实源: skills/dingtalk-weekly-report/VERSION
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dist

VERSION="$(tr -d '[:space:]' < skills/dingtalk-weekly-report/VERSION)"
[ -n "$VERSION" ] || { echo "❌ VERSION 文件为空" >&2; exit 1; }

# 发行物必须能追溯到 tag 和干净工作区；否则显式标成 dev 构建，别让它冒充发行版。
SUFFIX=""
if ! git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null; then
  echo "⚠ 未找到 tag v$VERSION —— 标记为 dev 构建"
  SUFFIX="-dev.$(git rev-parse --short HEAD)"
elif [ -n "$(git status --porcelain)" ]; then
  echo "⚠ 工作区有未提交改动 —— 标记为 dev 构建"
  SUFFIX="-dev.$(git rev-parse --short HEAD)"
fi

OUT="dist/dingtalk-weekly-report-skill-v${VERSION}${SUFFIX}.zip"
rm -f "$OUT"
# zip 根目录即为技能包名，解压后 bash dingtalk-weekly-report/install.sh
(cd skills && zip -rq "../$OUT" dingtalk-weekly-report \
  -x '*__pycache__*' -x '*.pyc')
echo "分发物: $OUT"
unzip -l "$OUT" | sed -n '1,20p'
echo "..."
unzip -l "$OUT" | tail -3
cat <<'EOF'
推荐（有 Node）— skills hub 风格:
  npx skills add https://github.com/dff652/dingtalk-weekly-report \
    -s dingtalk-weekly-report -a claude-code -a codex -g -y --copy
  bash ~/.claude/skills/dingtalk-weekly-report/bootstrap.sh
  # 说明: 仓库 README「Install / 复制给 AI / Verify」
zip 回退:
  unzip … && bash dingtalk-weekly-report/install.sh && bash dingtalk-weekly-report/bootstrap.sh
许可证: Apache-2.0。包内只有通用代码和空白模板；真实表单元数据只存每用户私有 $WORK。
EOF
