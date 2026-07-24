# 测试与验收状态

最近验证：2026-07-24，Linux / Python 3.12 / Playwright 1.61.0。

## 已通过

| 层级 | 命令 | 结果 |
|---|---|---|
| 核心边界 | `python3 tests/test_core.py` | 24 项通过 |
| 填表边界 | `.venv/bin/python tests/test_fill_form_logic.py` | 11 项通过 |
| 快速回归 | `bash tests/run_smoke.sh` | PASS |
| 完整自动验收 | `bash tests/run_full_acceptance.sh` | PASS |
| 远端发行验收 | `bash tests/run_release_acceptance.sh` | 功能链通过；旧审计缓存导致门禁 FAIL |
| 远程发现 | `npx skills add dff652/dingtalk-weekly-report --list` | 发现 1 个 skill |
| 本地 skills CLI 安装 | Node 22.23.1 / `skills@1.5.20` / 隔离 HOME | PASS |
| Claude 对话调用 | Claude Code 2.1.218 / `/dingtalk-weekly-report` | PASS |
| Codex 对话调用 | Codex CLI 0.145.0 / `$dingtalk-weekly-report` | PASS |

发行验收固定使用 `skills@1.5.20`，因为安全门禁解析该版本的英文安装输出；升级 CLI
时必须同步复验风险文案匹配。脚本优先使用 `~/.agents/skills`，缺失时回退
`~/.claude/skills`；两份同时存在则要求内容一致。

完整自动验收覆盖：

`打包 → 隔离 HOME 安装到 Claude/Codex/Agents → bootstrap → 独立 venv → 锁定 Playwright →
生成附件 → 生成粘贴块 → 浏览器仿真填表 → 只暂存并断言结果`。

同时验证了：

- CLI 不存在 `--submit`；
- `--draft` 未带 `--confirmed` 时阻断；
- 表单关闭或只有隐藏成功文案时，不得判定暂存成功；
- 非氚云表单 URL、无 token 登录 URL 均阻断；
- auth 链接只允许用户在 TTY 隐藏输入，非交互环境与空输入均阻断；
- `$WORK` 属主不匹配时阻断（POSIX）；
- 两个 CLI 的 help 不依赖工作目录；
- 未设置 `DTWR_HOME` 时可从 `~/.config/dtwr/root` 解析工作目录；
- `progress_report` 可解析直接文件或项目目录内固定的 `docs/report/PROGRESS_REPORT.md`；
  项目目录缺标准文档和不存在路径均阻断；
- 配置占位值、TODO、超长内容、错误周次、缺工作日、缺项目和单日超 24h 均阻断；
- 没有 `progress_report` 时生成 TODO 骨架，而不是编造内容；
- 打包产物包含运行脚本、契约、锁定依赖和跨平台安装脚本。

## AI 工具对话验收

2026-07-24 分别启动 Claude Code 与 Codex CLI 全新非持久会话，使用同一负例：
目标周为 2026-07-20，用户只提供“7 月 22 日工作 25 小时”，并要求其余日期从
git log 猜测。会话禁止读写文件、打开浏览器或访问真实表单。

初次负例证明 Codex 的自然语言提及不保证触发 skill；它错误询问是否授权读取 git log。
按 Codex 显式语法改用 `$dingtalk-weekly-report`，并把单日 `≤24h`、错误值必须询问修正
提升到主 `SKILL.md` 后，Claude 与 Codex 均能：

- 复述并要求确认目标周；
- 拒绝 25h，且不猜成 2.5h、不跨日拆分；
- 拒绝用 git log 编造报工；
- 主动询问缺失工作日、工时、项目/状态、总结与下周计划；
- 不生成文件、不登录、不触达真实表单。

因此用户文档固定写明：Claude 用 `/dingtalk-weekly-report`；Codex 用
`$dingtalk-weekly-report` 或先运行 `/skills` 选择。自然语言隐式匹配只能作为便利，
不能作为验收触发方式。

## 2026-07-24 本机安装→使用验收记录

本次从系统 Node 18.19.1、空隔离 HOME 开始，目标是验证当前维护仓能通过
Skills CLI 安装并运行，而不是复用已有 skill 链接。验收环境：

| 项 | 值 |
|---|---|
| 系统 | Linux x86_64 |
| Skills CLI | `skills@1.5.20` |
| 隔离 Node / npm | 22.23.1 / 10.9.8 |
| Python / Playwright | 3.12.3 / 1.61.0 |
| 安装源 | 当前维护仓本地路径，`--copy` |
| 隔离范围 | 独立 HOME、`$WORK`、venv、浏览器缓存 |

### 踩坑 1：npm 提示安装后，CLI 仍立即崩溃

症状：

```text
npm WARN EBADENGINE ... skills@1.5.20 required: node >=22.20.0
SyntaxError: node:util does not provide an export named styleText
Node.js v18.19.1
```

判断：`EBADENGINE` 不是可忽略警告；包虽已下载，CLI 尚未执行安装逻辑，因此
`find .../dingtalk-weekly-report/SKILL.md` 没有结果是正确现象。

解决：保留系统 Node，在隔离验收目录安装 Node 22，并校验官方 SHA-256。以下记录适用于
Linux x86_64；其他架构须选择对应压缩包：

```bash
ACCEPT=/path/to/dtwr-acceptance
NODE_DIR="$ACCEPT/runtime/node22"
NODE_BASE=https://nodejs.org/download/release/latest-v22.x
mkdir -p "$NODE_DIR"
cd "$NODE_DIR"
curl -fsSL "$NODE_BASE/SHASUMS256.txt" -o SHASUMS256.txt
NODE_FILE=$(awk '/linux-x64.tar.xz$/ {print $2; exit}' SHASUMS256.txt)
curl -fsSLO "$NODE_BASE/$NODE_FILE"
grep " $NODE_FILE$" SHASUMS256.txt | sha256sum -c -
tar -xJf "$NODE_FILE"
export PATH="$NODE_DIR/${NODE_FILE%.tar.xz}/bin:$PATH"
node -v
```

成功判据：校验和 `OK`，且 `node -v` 不低于 22.20.0；随后重新运行 `npx skills add`。

### 踩坑 2：指定 Codex 后没有独立 `~/.codex/skills` 副本

`skills@1.5.20` 的本次输出把共享副本放到 `~/.agents/skills`，同时写入 Claude
入口，并标记 Agents 为 `Claude Code, Codex`。因此只用 `find ~/.codex` 会误判失败。

先用 CLI 自检：

```bash
HOME="$ACCEPT/home" npx --yes skills@1.5.20 list --global
find "$ACCEPT/home" -path '*/dingtalk-weekly-report/SKILL.md' -print
```

成功判据：列表存在 `dingtalk-weekly-report`，Agents 包含 Codex，且
`~/.agents/skills/dingtalk-weekly-report/SKILL.md` 存在。若当前 Codex 版本只扫描
`~/.codex/skills`，再按 README 补链；不能仅凭目录缺失断言安装失败。

### 踩坑 3：Chromium 输出停在 0%，误以为 bootstrap 已完成

首次下载约 177 MiB Chromium 时，命令输出曾停在 0%，但下载进程和临时文件仍在增长；
此时 `.venv` 已存在，`~/.config/dtwr/root` 尚不存在。后者说明 bootstrap 还没走到结尾，
不能把“Python 包已安装”当作完成。

排查：

```bash
pgrep -af 'bootstrap.sh|playwright install chromium'
find /tmp -path '/tmp/playwright-download-*/*' -type f -printf '%s %p\n'
test -f "$HOME/.config/dtwr/root" && cat "$HOME/.config/dtwr/root"
```

标准解决方案：等待下载完成；若进程已失败，原命令可幂等重跑。只有看到
`bootstrap 完成`、root 指针写入且 Chromium 能启动，才算通过。

在已有完全相同 Playwright revision 的可信 dev 机上，可临时设置
`PLAYWRIGHT_BROWSERS_PATH` 复用本用户缓存以加速复验；新机器和普通用户不要依赖此捷径。
无论是否复用，最终都要在目标 HOME 下、不带临时缓存变量启动一次浏览器：

```bash
HOME="$ACCEPT/home" "$ACCEPT/work/.venv/bin/python" - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    browser.close()
print("isolated_chromium_launch=PASS")
PY
```

### 踩坑 4：bootstrap 写了 root，CLI 却仍把 cwd 当 `$WORK`

症状：root 指针正确，但从 `/tmp` 调用 `fill_form.py --keepalive` 报
`工作目录 /tmp 缺 config.json`。

定位：旧 `dtwr_common.workdir()` 只实现了 `DTWR_HOME → cwd`，没有实现 SKILL 与
bootstrap 承诺的 `~/.config/dtwr/root`。这不是使用者漏做 `cd`，而是代码契约缺口。

解决：提交 `20a6796` 补齐解析顺序：

1. 显式 `DTWR_HOME`；
2. 当前用户 `~/.config/dtwr/root`；
3. 指针不存在时兼容 cwd。

同时校验指针目录、指针文件、`$WORK` 和 config 属主；空指针直接阻断。新增两个回归测试。
安装副本覆盖后，从 `/tmp` 调用得到“config 模板占位值未填写”，而不再报 `/tmp`
缺 config，证明 root 指针已生效。

### 最终复验

```bash
python3 tests/test_core.py
.venv/bin/python tests/test_fill_form_logic.py
bash tests/run_smoke.sh
DTWR_TEST_BROWSERS_PATH="$HOME/.cache/ms-playwright" \
  bash tests/run_full_acceptance.sh
```

结果：核心 18 项、填表逻辑 11 项、`SMOKE PASS`、`FULL ACCEPTANCE PASS`，并额外完成
隔离 Skills CLI 安装、root 指针跨 cwd 解析和隔离 Chromium 实际启动。

## Skills.sh 安全审计跟进

2026-07-24 从 GitHub 远端安装提交 `98a3326` 时，安装与逻辑测试通过，但 Skills CLI 展示：

- Gen：Safe；
- Socket：1 个 LOW anomaly，说明为安装脚本、依赖安装链和临时登录链接需要人工复核，
  同时明确未见第三方凭证中转或恶意外传；
- Snyk：Critical，包含 W007（auth 链接交给 Agent/进入 argv）和 E005
  （文档建议把远端 uv 安装脚本直接管道执行）。

对应报告：

- <https://www.skills.sh/dff652/dingtalk-weekly-report/dingtalk-weekly-report/security/socket>
- <https://www.skills.sh/dff652/dingtalk-weekly-report/dingtalk-weekly-report/security/snyk>

本次修复：

1. bootstrap 不再输出任何远端脚本管道执行命令，只链接 uv 官方安装文档；
2. `--login-url` 改为无参数开关，仅在真实 TTY 使用 `getpass` 隐藏输入；
3. 旧写法 `--login-url '<URL>'`、非 TTY、空输入均 fail-loud；
4. SKILL/用户指南要求首选扫码，Agent 不得索要、接收或回显 auth 链接；
5. 新增 3 项逻辑测试和 2 个 smoke CLI 门禁；实机 PTY 用假域名验证输入不回显、
   且在启动浏览器前被 URL 校验阻断。

本地修复后的核心 18 项、填表逻辑 11 项、smoke、full acceptance 均通过。
平台审计是远端快照且可能缓存；必须在本提交 push 后重新从 GitHub 安装并等待重扫，
才能判断告警是否解除。旧报告不能代表修复后版本。

提交 `8408995` push 后已运行远端发行脚本：GitHub 下载、Skills CLI 安装、安装副本比对、
bootstrap、核心 18 项、填表逻辑 11 项、附件和 mock draft 全部通过；最后因平台仍返回
02:34/02:35 的旧 Snyk/Socket 报告而按设计失败。旧报告仍描述已经删除的管道安装和 argv
传 token，故当前阻塞是等待重扫，不是功能测试失败。

同日对加固后的发行脚本再次做开发态复验：固定调用 `skills@1.5.20`，成功发现
`~/.agents/skills` 与 `~/.claude/skills`，并确认两份安装内容一致。其后的 bootstrap、
核心 18 项、填表逻辑 11 项、附件和 mock draft 均通过，最后仍由旧 `Critical Risk`
报告 fail-closed。由于候选提交尚未 push，本次使用 `DTWR_RELEASE_REMOTE=.` 与
`DTWR_ALLOW_DIRTY=1` 只验证脚本改动；它不构成正式 `RELEASE ACCEPTANCE PASS`。
push 后必须不带这两个开发覆盖变量重新运行。

## 尚未完成

| 项目 | 状态 | 原因 |
|---|---|---|
| Windows PowerShell 实机 | 未验证 | 当前环境无 PowerShell |
| Skills.sh 安全重扫 | 等待平台重扫与正式复验 | 当前公开报告仍对应 `98a3326` |
| 真实氚云暂存验收 | 等待人工 | 当前周报缺 2026-07-22 至 2026-07-24 内容，且需用户确认旧草稿 |
| 钉钉最终提交 | 不自动测试 | 设计上只能由用户人工执行 |

所以准确结论是：**完整自动测试已通过；真实生产表单的本轮人工验收尚未完成。**

三个验收层级不得混用：

1. `run_full_acceptance.sh`：本地技能包的自动仿真闭环；
2. `run_release_acceptance.sh`：远端提交、GitHub 下载、Skills CLI、运行态、仿真与审计门禁；
3. [MANUAL_ACCEPTANCE.md](MANUAL_ACCEPTANCE.md)：真实个人配置、登录、氚云草稿和钉钉提交。
