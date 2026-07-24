# 测试与验收状态

最近验证：2026-07-24，Linux / Python 3.12 / Playwright 1.61.0。

## 已通过

| 层级 | 命令 | 结果 |
|---|---|---|
| 核心边界 | `python3 tests/test_core.py` | 18 项通过 |
| 填表边界 | `.venv/bin/python tests/test_fill_form_logic.py` | 8 项通过 |
| 快速回归 | `bash tests/run_smoke.sh` | PASS |
| 完整自动验收 | `bash tests/run_full_acceptance.sh` | PASS |
| 远程发现 | `npx skills add dff652/dingtalk-weekly-report --list` | 发现 1 个 skill |
| 本地 skills CLI 安装 | Node 22.23.1 / `skills@1.5.20` / 隔离 HOME | PASS |

完整自动验收覆盖：

`打包 → 隔离 HOME 安装到 Claude/Codex/Agents → bootstrap → 独立 venv → 锁定 Playwright →
生成附件 → 生成粘贴块 → 浏览器仿真填表 → 只暂存并断言结果`。

同时验证了：

- CLI 不存在 `--submit`；
- `--draft` 未带 `--confirmed` 时阻断；
- 表单关闭或只有隐藏成功文案时，不得判定暂存成功；
- 非氚云表单 URL、无 token 登录 URL 均阻断；
- `$WORK` 属主不匹配时阻断（POSIX）；
- 两个 CLI 的 help 不依赖工作目录；
- 未设置 `DTWR_HOME` 时可从 `~/.config/dtwr/root` 解析工作目录；
- 配置占位值、TODO、超长内容、错误周次、缺工作日、缺项目和单日超 24h 均阻断；
- 没有 `progress_report` 时生成 TODO 骨架，而不是编造内容；
- 打包产物包含运行脚本、契约、锁定依赖和跨平台安装脚本。

## 尚未完成

| 项目 | 状态 | 原因 |
|---|---|---|
| Windows PowerShell 实机 | 未验证 | 当前环境无 PowerShell |
| 真实氚云暂存验收 | 等待人工 | 当前周报缺 2026-07-22 至 2026-07-24 内容，且需用户确认旧草稿 |
| 钉钉最终提交 | 不自动测试 | 设计上只能由用户人工执行 |

所以准确结论是：**完整自动测试已通过；真实生产表单的本轮人工验收尚未完成。**

手工安装补充：系统 Node 18.19.1 无法启动 `skills@1.5.20`（其要求
Node `>=22.20.0`）；改用隔离 Node 22.23.1 后安装成功。
