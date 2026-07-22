#!/usr/bin/env bash
# dingtalk-weekly-report 技能一键安装（在解压目录里运行: bash install.sh）
# 装到 Claude Code（~/.claude/skills/）；检测到 Codex CLI 则同时生成桥接 prompt。
set -euo pipefail
cd "$(dirname "$0")"
SRC="skills/dingtalk-weekly-report"
[ -d "$SRC" ] || { echo "❌ 找不到 $SRC —— 请在解压出来的目录里运行本脚本"; exit 1; }

DEST="$HOME/.claude/skills/dingtalk-weekly-report"
mkdir -p "$HOME/.claude/skills"
rm -rf "$DEST"
cp -r "$SRC" "$DEST"
chmod -R u+rwX,go-rwx "$DEST"
echo "✅ Claude Code 技能已安装: $DEST"

if [ -d "$HOME/.codex" ]; then
  mkdir -p "$HOME/.codex/prompts"
  cat > "$HOME/.codex/prompts/dingtalk-weekly-report.md" <<EOF
# 钉钉报工周报半自动流程（Codex 入口）

严格阅读并执行技能包指令文件：

$DEST/SKILL.md

要点提醒（详细以 SKILL.md 为准）：
- 三条铁律：只落草稿（--draft）永不提交；周报内容必须先给用户人审确认；落草稿前提醒用户删同周旧草稿。
- \$WORK 工作目录经 ~/.config/dtwr/root 解析；属主必须是当前用户，否则终止。
- 用户传入的第一个参数若是周一日期（YYYY-MM-DD），作为目标周。
EOF
  echo "✅ Codex CLI 已桥接: ~/.codex/prompts/dingtalk-weekly-report.md"
fi

echo ""
echo "下一步: 打开 Claude Code（新会话），输入 /dingtalk-weekly-report，按引导完成首次配置"
echo "（需要准备: 手机钉钉扫一次「打印内部二维码」；表单里你的项目下拉完整原文）"
