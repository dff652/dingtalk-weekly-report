"""工作目录解析（技能包脚本共用）。

脚本随技能包分发（只读），运行态数据（config.json/weeks/output/.venv/登录态）
全部放在**每用户的工作目录**里，二者彻底分离：
  工作目录 = $DTWR_HOME 环境变量；否则读 ~/.config/dtwr/root；
  指针不存在时兼容当前目录（cwd）。
  判定标准 = 目录里有 config.json；没有则 fail-loud 指向首次安装。
"""
import os
import sys
from pathlib import Path

PROJECT_PROGRESS_REPORT = Path("docs/report/PROGRESS_REPORT.md")


def require_owned(path: Path, label: str) -> None:
    """共享机安全闸：已有路径必须属于当前用户。"""
    if not path.exists() or not hasattr(os, "geteuid"):
        return
    if path.stat().st_uid != os.geteuid():
        sys.exit(f"安全检查失败：{label} {path} 不属于当前用户，拒绝继续")


def resolve_progress_report(source) -> Path | None:
    """解析工作日志文件；项目目录只认固定的标准相对路径。"""
    if source is None or source == "":
        return None
    if not isinstance(source, str):
        raise ValueError("progress_report 必须是文件路径、项目目录或空字符串")
    value = source.strip()
    if not value:
        return None
    path = Path(value).expanduser()
    if path.is_file():
        return path
    if path.is_dir():
        candidate = path / PROJECT_PROGRESS_REPORT
        if candidate.is_file():
            return candidate
        raise ValueError(
            f"progress_report 项目目录缺 {PROJECT_PROGRESS_REPORT}: {path}")
    raise ValueError(f"progress_report 不存在或不是文件/项目目录: {path}")


def workdir() -> Path:
    configured = os.environ.get("DTWR_HOME")
    if configured:
        d = Path(configured).expanduser().resolve()
    else:
        config_home = Path(
            os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        pointer = config_home / "dtwr" / "root"
        if pointer.exists():
            require_owned(pointer.parent, "登录态目录")
            require_owned(pointer, "工作目录指针")
            configured = pointer.read_text(encoding="utf-8").strip()
            if not configured:
                sys.exit(f"工作目录指针 {pointer} 为空——请重新运行 bootstrap")
            d = Path(configured).expanduser().resolve()
        else:
            d = Path.cwd().resolve()
    if not (d / "config.json").exists():
        sys.exit(
            f"工作目录 {d} 缺 config.json——请 cd 到工作目录（或设 DTWR_HOME）；"
            "首次使用按 skill『首次安装』流程初始化")
    require_owned(d, "工作目录")
    require_owned(d / "config.json", "配置文件")
    return d
