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
HOME="$ACCEPT/home" npx --yes skills list --global
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

结果：核心 18 项、填表逻辑 8 项、`SMOKE PASS`、`FULL ACCEPTANCE PASS`，并额外完成
隔离 Skills CLI 安装、root 指针跨 cwd 解析和隔离 Chromium 实际启动。

## 尚未完成

| 项目 | 状态 | 原因 |
|---|---|---|
| Windows PowerShell 实机 | 未验证 | 当前环境无 PowerShell |
| 真实氚云暂存验收 | 等待人工 | 当前周报缺 2026-07-22 至 2026-07-24 内容，且需用户确认旧草稿 |
| 钉钉最终提交 | 不自动测试 | 设计上只能由用户人工执行 |

所以准确结论是：**完整自动测试已通过；真实生产表单的本轮人工验收尚未完成。**
