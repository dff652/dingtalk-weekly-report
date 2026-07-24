#!/usr/bin/env bash
# 首次建 $WORK 运行环境（不装技能；技能用 install.sh）
# 用法:
#   bash bootstrap.sh
#   bash bootstrap.sh --work ~/weekly-report-data
#   bash bootstrap.sh --work /path/to/work --force-venv   # 重建 .venv
set -euo pipefail

SKILL="$(cd "$(dirname "$0")" && pwd)"
WORK="${DTWR_HOME:-$HOME/weekly-report-data}"
FORCE_VENV=0

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

# 展开 ~
case "$WORK" in
  "~/"*) WORK="$HOME/${WORK#~/}" ;;
  "~") WORK="$HOME" ;;
esac
WORK="$(mkdir -p "$WORK" && cd "$WORK" && pwd)"

echo "==> \$WORK = $WORK"
echo "==> \$SKILL = $SKILL"

mkdir -p "$WORK/weeks" "$WORK/output/shots"
chmod 700 "$WORK" 2>/dev/null || true

# config
if [ ! -f "$WORK/config.json" ]; then
  cp "$SKILL/assets/config.example.json" "$WORK/config.json"
  echo "✅ 已写入 $WORK/config.json（请编辑 name / form_project / attach_project 等）"
else
  echo "ℹ 保留已有 config.json"
fi

# uv / venv / playwright
if ! command -v uv >/dev/null 2>&1; then
  echo "❌ 未找到 uv。安装: https://docs.astral.sh/uv/  或 curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

if [ "$FORCE_VENV" -eq 1 ] && [ -d "$WORK/.venv" ]; then
  echo "⚠ --force-venv: 删除 $WORK/.venv"
  rm -rf "$WORK/.venv"
fi

if [ ! -x "$WORK/.venv/bin/python" ] && [ ! -x "$WORK/.venv/Scripts/python.exe" ]; then
  echo "==> uv venv"
  (cd "$WORK" && uv venv .venv)
fi

PY="$WORK/.venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="$WORK/.venv/Scripts/python.exe"
fi
[ -x "$PY" ] || { echo "❌ 找不到 venv python: $WORK/.venv" >&2; exit 1; }

echo "==> 安装 playwright"
uv pip install --python "$PY" playwright
echo "==> 安装 Chromium（Playwright 自带）"
"$PY" -m playwright install chromium

# dtwr 指针
DTWR_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/dtwr"
mkdir -p -m 700 "$DTWR_DIR" 2>/dev/null || mkdir -p "$DTWR_DIR"
echo "$WORK" > "$DTWR_DIR/root"
chmod 600 "$DTWR_DIR/root" 2>/dev/null || true
echo "✅ 已写 $DTWR_DIR/root → $WORK"

echo ""
echo "bootstrap 完成。"
echo "  下一步: 编辑 $WORK/config.json"
echo "  登录:   $PY \"$SKILL/scripts/fill_form.py\" --login-url '<h3yun entry/auth 链接>'"
echo "  或打开 AI 工具运行 /dingtalk-weekly-report 完成访谈式配置与登录"
echo "  可选 cron(Linux/mac): 30 9 * * * cd $WORK && $PY $SKILL/scripts/fill_form.py --keepalive >> output/keepalive.log 2>&1"
echo "  Windows 计划任务可调用同一 keepalive 命令"
