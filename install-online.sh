#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# 首次安装和后续更新共用入口。可用 curl 下载本脚本，再按指定 ref 下载仓库归档。
set -euo pipefail

REF=main
SCOPE=
SKILL_ONLY=0

usage() {
  cat <<'EOF'
用法: bash install-online.sh [--ref <tag|branch|commit>] [--codex-only|--claude-only|--agents-only] [--skill-only]
默认更新 Claude、Codex 与 Agents 的已有安装目录；首次安装还会建立私有运行环境。
--skill-only 只安装技能代码，不检查或安装 Python/Chromium 运行环境。
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --ref)
      [ "$#" -ge 2 ] || { echo "--ref 需要值" >&2; exit 2; }
      REF=$2
      shift 2
      ;;
    --codex-only|--claude-only|--agents-only)
      [ -z "$SCOPE" ] || { echo "只能选一个安装范围" >&2; exit 2; }
      SCOPE=$1
      shift
      ;;
    --skill-only)
      SKILL_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$REF" in
  ''|*[!a-zA-Z0-9._/-]*)
    echo "非法 ref: $REF" >&2
    exit 2
    ;;
esac

for command_name in curl tar mktemp; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "缺少命令: $command_name" >&2
    exit 1
  }
done

owner_uid() {
  stat -c %u "$1" 2>/dev/null || stat -f %u "$1"
}

# 运行态含私有配置和登录态。共享机器上先检查属主，再允许安装器或 bootstrap 触碰它。
dtwr_dir="${XDG_CONFIG_HOME:-$HOME/.config}/dtwr"
work_dir="$HOME/weekly-report-data"
if [ -d "$dtwr_dir" ] && [ "$(owner_uid "$dtwr_dir")" != "$(id -u)" ]; then
  echo "私有状态目录属主不是当前用户: $dtwr_dir" >&2
  exit 1
fi
if [ -s "$dtwr_dir/root" ]; then
  IFS= read -r work_dir < "$dtwr_dir/root"
  case "$work_dir" in
    /*) ;;
    *) echo "私有工作目录不是绝对路径: $work_dir" >&2; exit 1 ;;
  esac
fi
if [ -d "$work_dir" ] && [ "$(owner_uid "$work_dir")" != "$(id -u)" ]; then
  echo "私有工作目录属主不是当前用户: $work_dir" >&2
  exit 1
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
archive="$tmp_dir/source.tar.gz"
source_dir="$tmp_dir/source"
mkdir -p "$source_dir"
archive_url="https://codeload.github.com/dff652/dingtalk-weekly-report/tar.gz/$REF"
echo "下载 dingtalk-weekly-report: $REF"
curl --fail --location --silent --show-error --retry 3 \
  --connect-timeout 15 --max-time 180 --output "$archive" "$archive_url"
tar -xzf "$archive" -C "$source_dir" --strip-components=1
[ -f "$source_dir/skills/dingtalk-weekly-report/SKILL.md" ] || {
  echo "下载的归档不含技能包" >&2
  exit 1
}

# 已有安装由维护仓的安装器原子范围内覆盖；$WORK 不属于技能包，不会被覆盖。
install_log="$tmp_dir/install.log"
if [ -z "$SCOPE" ]; then
  mkdir -p "$HOME/.codex"
  if ! bash "$source_dir/install.sh" --force >"$install_log" 2>&1; then
    cat "$install_log" >&2
    exit 1
  fi
else
  if ! bash "$source_dir/install.sh" "$SCOPE" --force >"$install_log" 2>&1; then
    cat "$install_log" >&2
    exit 1
  fi
fi
echo "技能已安装到当前用户目录（来源 ref: $REF）。"

if [ "$SKILL_ONLY" -eq 1 ]; then
  echo "按需运行已安装技能的 bootstrap.sh --diagnose；私有运行环境未改动。"
  exit 0
fi

case "$SCOPE" in
  --codex-only) bootstrap="$HOME/.codex/skills/dingtalk-weekly-report/bootstrap.sh" ;;
  --agents-only) bootstrap="$HOME/.agents/skills/dingtalk-weekly-report/bootstrap.sh" ;;
  *) bootstrap="$HOME/.claude/skills/dingtalk-weekly-report/bootstrap.sh" ;;
esac

if [ -f "$work_dir/config.json" ] && [ -d "$work_dir/.venv" ]; then
  if bash "$bootstrap" --diagnose; then
    echo "技能已更新，私有运行环境可复用。"
    exit 0
  fi
  echo "运行环境体检失败，按 bootstrap.sh 修复依赖。"
fi
bash "$bootstrap"
echo "技能已安装；首次使用请按 USER_GUIDE.md 完成私有配置和登录。"
