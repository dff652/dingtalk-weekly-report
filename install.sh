#!/usr/bin/env bash
# 维护仓入口：转调技能包自安装脚本（同事请用 zip 内 dingtalk-weekly-report/install.sh）
set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/skills/dingtalk-weekly-report/install.sh" "$@"
