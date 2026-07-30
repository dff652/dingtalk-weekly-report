#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# 首次建 $WORK 运行环境（不装技能；技能用 install.sh）
# 用法:
#   bash bootstrap.sh
#   bash bootstrap.sh --work ~/weekly-report-data
#   bash bootstrap.sh --work /path/to/work --force-venv   # 重建 .venv
#   bash bootstrap.sh --diagnose                           # 无安装体检
set -euo pipefail

SKILL="$(cd "$(dirname "$0")" && pwd)"
DTWR_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/dtwr"
if [ -n "${DTWR_HOME:-}" ]; then
  WORK="$DTWR_HOME"
elif [ -s "$DTWR_DIR/root" ]; then
  IFS= read -r WORK < "$DTWR_DIR/root"
else
  WORK="$HOME/weekly-report-data"
fi
FORCE_VENV=0
DIAGNOSE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --work)
      WORK="${2:?--work 需要路径}"
      shift 2
      ;;
    --force-venv)
      FORCE_VENV=1
      shift
      ;;
    --diagnose)
      DIAGNOSE=1
      shift
      ;;
    -h|--help)
      sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      exit 2
      ;;
  esac
done

# 展开 ~；诊断模式不创建不存在的工作目录。
case "$WORK" in
  "~/"*) WORK="$HOME/${WORK#~/}" ;;
  "~") WORK="$HOME" ;;
esac
if [ "$DIAGNOSE" -eq 1 ]; then
  [ -d "$WORK" ] || {
    echo "❌ 工作目录不存在: $WORK（首次安装请运行 bootstrap.sh）" >&2
    exit 1
  }
  WORK="$(cd "$WORK" && pwd)"
else
  WORK="$(mkdir -p "$WORK" && cd "$WORK" && pwd)"
fi

case "$WORK/" in
  "$SKILL/"*)
    echo "❌ \$WORK 不能位于技能代码目录内: $WORK" >&2
    exit 1
    ;;
esac
case "$SKILL/" in
  "$WORK/"*)
    echo "❌ \$WORK 不能包含技能/源码目录: $WORK" >&2
    exit 1
    ;;
esac

mkdir -p "$WORK/output"
BOOTSTRAP_LOG="$WORK/output/bootstrap.log"
touch "$BOOTSTRAP_LOG"
chmod 600 "$BOOTSTRAP_LOG" 2>/dev/null || true
STARTED_AT="$(date +%s)"
CURRENT_STAGE="启动"
exec > >(tee -a "$BOOTSTRAP_LOG") 2>&1

finish() {
  local code=$?
  local elapsed=$(( $(date +%s) - STARTED_AT ))
  if [ "$code" -eq 0 ]; then
    echo "[$(date '+%F %T')] bootstrap_result=PASS elapsed=${elapsed}s log=$BOOTSTRAP_LOG"
  else
    echo "[$(date '+%F %T')] bootstrap_result=FAIL stage=$CURRENT_STAGE exit=$code elapsed=${elapsed}s"
    echo "排查日志: $BOOTSTRAP_LOG"
  fi
}
trap finish EXIT

stage() {
  CURRENT_STAGE="$1"
  echo "[$(date '+%F %T')] ==> $CURRENT_STAGE"
}

echo ""
echo "[$(date '+%F %T')] bootstrap_start diagnose=$DIAGNOSE force_venv=$FORCE_VENV"
echo "==> \$WORK = $WORK"
echo "==> \$SKILL = $SKILL"
echo "==> 日志 = $BOOTSTRAP_LOG"

PY="$WORK/.venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="$WORK/.venv/Scripts/python.exe"
fi

runtime_check() {
  "$PY" "$SKILL/scripts/runtime_check.py" "$SKILL/requirements-runtime.txt"
}

if [ "$DIAGNOSE" -eq 1 ]; then
  stage "检查现有运行环境（不安装、不改配置/登录态）"
  [ -x "$PY" ] || {
    echo "❌ 找不到 venv python: $WORK/.venv"
    echo "修复: bash \"$SKILL/bootstrap.sh\" --work \"$WORK\""
    exit 1
  }
  runtime_check || {
    echo "修复: bash \"$SKILL/bootstrap.sh\" --work \"$WORK\""
    exit 1
  }
  echo "✅ 环境可复用；更新 Skill 不需要重装或重跑 bootstrap"
  exit 0
fi

mkdir -p "$WORK/weeks" "$WORK/output/shots"
chmod 700 "$WORK" 2>/dev/null || true

# config
stage "检查私有配置"
if [ ! -f "$WORK/config.json" ]; then
  cp "$SKILL/assets/config.example.json" "$WORK/config.json"
  echo "✅ 已写入 $WORK/config.json（AI 首次调用会主动引导；本机可运行 --guided）"
else
  echo "ℹ 保留已有 config.json"
fi
chmod 600 "$WORK/config.json" 2>/dev/null || true

if [ "$FORCE_VENV" -eq 1 ] && [ -d "$WORK/.venv" ]; then
  echo "⚠ --force-venv: 删除 $WORK/.venv"
  rm -rf "$WORK/.venv"
  PY="$WORK/.venv/bin/python"
fi

stage "检查 Python 与浏览器运行环境"
if [ "$FORCE_VENV" -eq 0 ] && [ -x "$PY" ] && runtime_check; then
  echo "✅ 复用现有 .venv 与 Chromium；Skill 更新不会重复安装环境"
  RUNTIME_READY=1
else
  RUNTIME_READY=0
fi

if [ "$RUNTIME_READY" -eq 0 ] && ! command -v uv >/dev/null 2>&1; then
  echo "❌ 运行环境需要创建/修复，但未找到 uv。" >&2
  echo "请按官方文档安装: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

if [ ! -x "$WORK/.venv/bin/python" ] && [ ! -x "$WORK/.venv/Scripts/python.exe" ]; then
  stage "创建 Python venv"
  (cd "$WORK" && uv venv .venv)
fi

PY="$WORK/.venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="$WORK/.venv/Scripts/python.exe"
fi
[ -x "$PY" ] || { echo "❌ 找不到 venv python: $WORK/.venv" >&2; exit 1; }

if [ "$RUNTIME_READY" -eq 0 ]; then
  stage "同步 Python 运行依赖"
  uv pip install --python "$PY" -r "$SKILL/requirements-runtime.txt"
  stage "校验/补齐 Chromium（缓存命中时不会重复下载）"
  "$PY" -m playwright install chromium
  stage "复验修复后的运行环境"
  runtime_check
fi

# dtwr 指针
stage "写入工作目录指针"
mkdir -p -m 700 "$DTWR_DIR" 2>/dev/null || mkdir -p "$DTWR_DIR"
echo "$WORK" > "$DTWR_DIR/root"
chmod 600 "$DTWR_DIR/root" 2>/dev/null || true
echo "✅ 已写 $DTWR_DIR/root → $WORK"

echo ""
echo "bootstrap 完成。"
echo "  更新 Skill: 不要重跑 bootstrap；先用 --diagnose 无安装体检"
echo "  排查日志: $BOOTSTRAP_LOG"
echo "  查看日志: tail -n 80 \"$BOOTSTRAP_LOG\""
echo "  缺项:   $PY \"$SKILL/scripts/configure.py\" --missing"
echo "  配置:   $PY \"$SKILL/scripts/configure.py\" --guided"
echo "  登录:   $PY \"$SKILL/scripts/fill_form.py\" --login-web  # 127.0.0.1；远程使用端口转发"
echo "  截图兜底: $PY \"$SKILL/scripts/fill_form.py\" --login"
echo "  URL兜底: 用户本人在交互终端运行 $PY \"$SKILL/scripts/fill_form.py\" --login-url（隐藏输入）"
echo "  AI: Claude 用 /dingtalk-weekly-report；Codex 用 \$dingtalk-weekly-report 或 /skills 选择"
# 日志路径必须写绝对：相对路径在 cron 里跟着 cwd 走，cwd 一错重定向就失败，
# 而 cron 的 stderr 无人看 → 保活每天静默失败（本项目 2026-07-28 踩过，见 TESTING 踩坑 18）。
echo "  可选 cron(Linux/mac)，日志路径务必写绝对："
echo "    30 9,15 * * * cd $WORK && $PY $SKILL/scripts/fill_form.py --keepalive >> $WORK/output/keepalive.log 2>&1"
echo "  装好后第二天务必确认 $WORK/output/keepalive.log 真的有新行——没有就是没跑成"
echo "  Windows 计划任务可调用同一 keepalive 命令"
