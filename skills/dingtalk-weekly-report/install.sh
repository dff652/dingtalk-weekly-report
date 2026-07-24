#!/usr/bin/env bash
# dingtalk-weekly-report 技能自安装（本脚本位于技能包根目录）
# 用法:
#   bash install.sh              # 复制安装到 Claude；若有 Codex/agents 目录则一并装
#   bash install.sh --link       # 软链到本目录（维护仓开发）
#   bash install.sh --force      # 覆盖已有安装
#   bash install.sh --claude-only | --codex-only | --agents-only
# 目标:
#   Claude  → ~/.claude/skills/dingtalk-weekly-report
#   Codex   → ~/.codex/skills/dingtalk-weekly-report  （正式 skills，非旧 prompts）
#   Agents  → ~/.agents/skills/dingtalk-weekly-report （若目录已存在）
set -euo pipefail

MODE=copy
FORCE=0
DO_CLAUDE=1
DO_CODEX=1
DO_AGENTS=1
for arg in "$@"; do
  case "$arg" in
    --link) MODE=link ;;
    --force) FORCE=1 ;;
    --claude-only) DO_CLAUDE=1; DO_CODEX=0; DO_AGENTS=0 ;;
    --codex-only)  DO_CLAUDE=0; DO_CODEX=1; DO_AGENTS=0 ;;
    --agents-only) DO_CLAUDE=0; DO_CODEX=0; DO_AGENTS=1 ;;
    -h|--help)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "未知参数: $arg（见 --help）" >&2
      exit 2
      ;;
  esac
done

SRC="$(cd "$(dirname "$0")" && pwd)"
NAME="dingtalk-weekly-report"
OLD_NAME="weekly-report"

[ -f "$SRC/SKILL.md" ] || {
  echo "❌ 找不到 $SRC/SKILL.md —— 请在技能包目录内运行本脚本" >&2
  exit 1
}

# 安装到单个目标目录；label 仅用于日志
install_to() {
  local dest="$1"
  local label="$2"
  local parent
  parent="$(dirname "$dest")"
  mkdir -p "$parent"

  # 已在安装位置自身再跑
  if [ "$SRC" = "$dest" ] && [ ! -L "$dest" ]; then
    echo "✅ [$label] 已在安装位置: $dest"
    return 0
  fi

  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ -L "$dest" ]; then
      local target
      target="$(readlink -f "$dest" 2>/dev/null || true)"
      [ -n "$target" ] || target="$(readlink "$dest")"
      if [ "$MODE" = "link" ] && [ "$target" = "$SRC" ]; then
        echo "✅ [$label] 软链已指向本目录: $dest -> $SRC"
        return 0
      elif [ "$FORCE" -eq 1 ]; then
        rm -rf "$dest"
      else
        echo "❌ [$label] 已存在: $dest（软链 -> $target）" >&2
        echo "   对齐软链: bash install.sh --link --force" >&2
        echo "   改复制装: bash install.sh --force" >&2
        return 1
      fi
    else
      if [ "$FORCE" -eq 1 ]; then
        rm -rf "$dest"
      else
        echo "❌ [$label] 已存在目录: $dest" >&2
        echo "   升级: bash install.sh --force" >&2
        echo "   软链: bash install.sh --link --force" >&2
        return 1
      fi
    fi
  fi

  if [ "$MODE" = "link" ]; then
    ln -sfn "$SRC" "$dest"
    echo "✅ [$label] 已软链: $dest -> $SRC"
  else
    cp -a "$SRC" "$dest"
    chmod -R u+rwX,go-rwx "$dest" 2>/dev/null || chmod -R u+rwX "$dest"
    echo "✅ [$label] 已安装: $dest"
  fi
}

# 清理改名前旧技能，避免双路由
remove_old() {
  local path="$1"
  if [ -e "$path" ] || [ -L "$path" ]; then
    echo "⚠ 移除旧技能名: $path"
    rm -rf "$path"
  fi
}

errs=0

if [ "$DO_CLAUDE" -eq 1 ]; then
  remove_old "$HOME/.claude/skills/$OLD_NAME"
  install_to "$HOME/.claude/skills/$NAME" "Claude" || errs=$((errs + 1))
fi

if [ "$DO_CODEX" -eq 1 ]; then
  # 仅当用户已有 ~/.codex 或强制全装时写入；无 .codex 则跳过并提示
  if [ -d "$HOME/.codex" ] || [ "$DO_CLAUDE" -eq 0 ]; then
    mkdir -p "$HOME/.codex/skills"
    remove_old "$HOME/.codex/skills/$OLD_NAME"
    # 清理旧 prompt 桥接（Codex 新版本以 skills 为准）
    if [ -f "$HOME/.codex/prompts/$OLD_NAME.md" ]; then
      echo "⚠ 移除旧 Codex prompt: $HOME/.codex/prompts/$OLD_NAME.md"
      rm -f "$HOME/.codex/prompts/$OLD_NAME.md"
    fi
    if [ -f "$HOME/.codex/prompts/$NAME.md" ]; then
      echo "⚠ 移除过时 Codex prompt 桥接: $HOME/.codex/prompts/$NAME.md（改用 skills/）"
      rm -f "$HOME/.codex/prompts/$NAME.md"
    fi
    install_to "$HOME/.codex/skills/$NAME" "Codex" || errs=$((errs + 1))
  else
    echo "ℹ 未检测到 ~/.codex，跳过 Codex skills（需要时: bash install.sh --codex-only --force）"
  fi
fi

if [ "$DO_AGENTS" -eq 1 ]; then
  if [ -d "$HOME/.agents" ] || [ -d "$HOME/.agents/skills" ]; then
    mkdir -p "$HOME/.agents/skills"
    remove_old "$HOME/.agents/skills/$OLD_NAME"
    install_to "$HOME/.agents/skills/$NAME" "Agents" || errs=$((errs + 1))
  fi
fi

if [ "$errs" -ne 0 ]; then
  exit 1
fi

echo ""
echo "下一步:"
echo "  1) 建运行环境: bash \"$SRC/bootstrap.sh\"   # Windows: .\\bootstrap.ps1"
echo "  2) 编辑 \$WORK/config.json（项目下拉完整原文等）"
echo "  3) 新会话 /dingtalk-weekly-report；首次登录首选 --login 扫码"
echo "     URL 兜底由用户本人在交互终端运行 --login-url（隐藏输入，勿发给 Agent）"
echo "  说明: $SRC/USER_GUIDE.md  |  仓库: https://github.com/dff652/dingtalk-weekly-report"
