"""工作目录解析（技能包脚本共用）。

脚本随技能包分发（只读），运行态数据（config.json/weeks/output/.venv/登录态）
全部放在**每用户的工作目录**里，二者彻底分离：
  工作目录 = $DTWR_HOME 环境变量，缺省 = 当前目录（cwd）。
  判定标准 = 目录里有 config.json；没有则 fail-loud 指向首次安装。
"""
import os
import sys
from pathlib import Path


def workdir() -> Path:
    d = Path(os.environ.get("DTWR_HOME") or Path.cwd()).resolve()
    if not (d / "config.json").exists():
        sys.exit(
            f"工作目录 {d} 缺 config.json——请 cd 到工作目录（或设 DTWR_HOME）；"
            "首次使用按 skill『首次安装』流程初始化")
    return d
