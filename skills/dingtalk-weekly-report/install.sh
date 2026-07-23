#!/usr/bin/env bash
# dingtalk-weekly-report 技能自安装（本脚本位于技能包根目录）
# 用法:
#   bash install.sh           # 复制到 ~/.claude/skills/（同事 zip 默认）
#   bash install.sh --link    # 软链到本目录（维护仓开发）
#   bash install.sh --force   # 覆盖已有安装（含软链）
# 检测到 ~/.codex 时同时写 Codex 桥接 prompt。
set -euo pipefail

MODE=copy
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --link) MODE=link ;;
    --force) FORCE=1 ;;
    -h|--help)
      sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "未知参数: $arg（支持 --link / --force / --help）" >&2
      exit 2
      ;;
  esac
done

SRC="$(cd "$(dirname "$0")" && pwd)"
NAME="dingtalk-weekly-report"
DEST="$HOME/.claude/skills/$NAME"
OLD_DEST="$HOME/.claude/skills/weekly-report"
OLD_CODEX="$HOME/.codex/prompts/weekly-report.md"
CODEX_PROMPT="$HOME/.codex/prompts/$NAME.md"

[ -f "$SRC/SKILL.md" ] || {
  echo "❌ 找不到 $SRC/SKILL.md —— 请在技能包目录内运行本脚本" >&2
  exit 1
}

# 已在安装位置自身再跑（真实目录，非软链源）
if [ "$SRC" = "$DEST" ] && [ ! -L "$DEST" ]; then
  echo "✅ 已在安装位置: $DEST"
  # 仍可刷新 Codex 桥接
else
  mkdir -p "$HOME/.claude/skills"

  # 清理改名前的旧技能，避免 Claude 双路由
  if [ -e "$OLD_DEST" ] || [ -L "$OLD_DEST" ]; then
    echo "⚠ 移除旧技能名: $OLD_DEST"
    rm -rf "$OLD_DEST"
  fi
  if [ -f "$OLD_CODEX" ]; then
    echo "⚠ 移除旧 Codex 桥接: $OLD_CODEX"
    rm -f "$OLD_CODEX"
  fi

  need_install=1
  if [ -e "$DEST" ] || [ -L "$DEST" ]; then
    if [ -L "$DEST" ]; then
      target="$(readlink -f "$DEST" 2>/dev/null || true)"
      [ -n "$target" ] || target="$(readlink "$DEST")"
      if [ "$MODE" = "link" ] && [ "$target" = "$SRC" ]; then
        echo "✅ 软链已指向本目录: $DEST -> $SRC"
        need_install=0
      elif [ "$FORCE" -eq 1 ]; then
        rm -rf "$DEST"
      else
        echo "❌ 已存在: $DEST（软链 -> $target）" >&2
        echo "   对齐软链: bash install.sh --link --force" >&2
        echo "   改复制装: bash install.sh --force" >&2
        exit 1
      fi
    else
      # 真实目录
      if [ "$FORCE" -eq 1 ]; then
        rm -rf "$DEST"
      else
        echo "❌ 已存在目录安装: $DEST" >&2
        echo "   升级复制: bash install.sh --force" >&2
        echo "   改软链:   bash install.sh --link --force" >&2
        exit 1
      fi
    fi
  fi

  if [ "$need_install" -eq 1 ]; then
    if [ "$MODE" = "link" ]; then
      ln -sfn "$SRC" "$DEST"
      echo "✅ Claude Code 技能已软链: $DEST -> $SRC"
    else
      cp -a "$SRC" "$DEST"
      chmod -R u+rwX,go-rwx "$DEST"
      echo "✅ Claude Code 技能已安装: $DEST"
    fi
  fi
fi

# Codex 桥接：指向已装位置的 SKILL.md
if [ -d "$HOME/.codex" ]; then
  mkdir -p "$HOME/.codex/prompts"
  cat > "$CODEX_PROMPT" <<EOF
# 钉钉报工周报半自动流程（Codex 入口）

严格阅读并执行技能包指令文件：

$DEST/SKILL.md

要点提醒（详细以 SKILL.md 为准）：
- 三条铁律：只落草稿（--draft）永不提交；周报内容必须先给用户人审确认；落草稿前提醒用户删同周旧草稿。
- \$WORK 工作目录经 ~/.config/dtwr/root 解析；属主必须是当前用户，否则终止。
- 用户传入的第一个参数若是周一日期（YYYY-MM-DD），作为目标周。
EOF
  echo "✅ Codex 已桥接: $CODEX_PROMPT"
fi

echo ""
echo "下一步: 打开 Claude Code（新会话），输入 /dingtalk-weekly-report，按引导完成首次配置"
echo "（需要准备: 手机钉钉扫一次「打印内部二维码」；表单里你的项目下拉完整原文）"
