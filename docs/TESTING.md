# 测试与验收状态

最近验证：2026-07-25，Linux / Python 3.12 / Playwright 1.61.0。

## 已通过

| 层级 | 命令 | 结果 |
|---|---|---|
| 核心边界 | `python3 tests/test_core.py` | 33 项通过 |
| 公开树脱敏 | `python3 tests/test_public_tree.py` | 4 项通过 |
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
- `$WORK` 指向源码仓库时阻断，防止个人数据再次混入公开代码；
- 两个 CLI 的 help 不依赖工作目录；
- 未设置 `DTWR_HOME` 时可从 `~/.config/dtwr/root` 解析工作目录；
- `progress_report` 可解析直接文件或项目目录内固定的 `docs/report/PROGRESS_REPORT.md`；
  项目目录缺标准文档和不存在路径均阻断；
- 配置占位值、TODO、超长内容、错误周次、缺工作日、缺项目和单日超 24h 均阻断；
- 重新配置通过完整校验后才原子写入并保留备份；非法工时和 entry/auth URL 不修改原配置；
- config/report schema v2、配置驱动字段/枚举一致性及“提交按钮不得冒充暂存”均有负例；
- 没有 `progress_report` 时生成 TODO 骨架，而不是编造内容；
- 打包产物包含 Apache-2.0、运行脚本、契约、锁定依赖和跨平台安装脚本。

## 2026-07-25 开源隔离验收

- 根 `config.json`、`weeks/`、`output/` 已迁出源码仓库；
- `$WORK` 指针改为仓库外私有目录，配置权限 0600，登录态保持独立；
- 表单字段 ID、按钮文本、枚举和组织规则改为 config schema v2；
- 公开模板的 URL、字段和词表均为空，测试只使用合成值；
- 根与 Skill 分发目录携带完全相同的 Apache-2.0；
- `tests/test_public_tree.py` 检查运行数据、许可证副本和常见敏感值形态。

这只清理当前树；旧 Git 历史仍需单独审批后重写，详见 `PUBLISHING.md`。

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

解决：补齐解析顺序（提交见历史重建前版本）：

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

2026-07-24 从 GitHub 远端安装当时的 main 时，安装与逻辑测试通过，但 Skills CLI 展示：

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

该批修复 push 后已运行远端发行脚本：GitHub 下载、Skills CLI 安装、安装副本比对、
bootstrap、核心 18 项、填表逻辑 11 项、附件和 mock draft 全部通过；最后因平台仍返回
02:34/02:35 的旧 Snyk/Socket 报告而按设计失败。旧报告仍描述已经删除的管道安装和 argv
传 token，故当前阻塞是等待重扫，不是功能测试失败。

同日对加固后的发行脚本再次做开发态复验：固定调用 `skills@1.5.20`，成功发现
`~/.agents/skills` 与 `~/.claude/skills`，并确认两份安装内容一致。其后的 bootstrap、
核心 18 项、填表逻辑 11 项、附件和 mock draft 均通过，最后仍由旧 `Critical Risk`
报告 fail-closed。由于候选提交尚未 push，本次使用 `DTWR_RELEASE_REMOTE=.` 与
`DTWR_ALLOW_DIRTY=1` 只验证脚本改动；它不构成正式 `RELEASE ACCEPTANCE PASS`。
push 后必须不带这两个开发覆盖变量重新运行。

## 2026-07-26/27 会话：工具链与门禁踩坑

本轮把评审缺陷 ①②③⑧⑨⑭⑮ 收口、引入版本号机制、处置历史泄露与安全告警。过程中踩到的坑
按"下次还会踩"的标准记录如下。

### 踩坑 5：`npx skills` 确认不写 `~/.codex/skills`

README「复制给 AI」那段的第 2 步（补链）曾被怀疑多余。在隔离 HOME 里逐条执行验证：
`--agent codex` 装完后 `~/.codex/skills/dingtalk-weekly-report` **不存在**，只写了
`~/.claude` 与 `~/.agents`。**该步骤必须保留**，不是历史包袱。

### 踩坑 6：`skills@1.5.20` 要 Node ≥22.20，且 `nvm install` 会偷改 default

本机只有 Node 18（system）与 20（nvm），跑 `run_release_acceptance.sh` 直接 fail-fast。
装 22 解决，但 **`nvm install 22` 在没有显式 default 别名时会自动创建 `default -> 22`**，
把项目默认 Node 顶掉。装完必须复查：

```bash
nvm alias default        # 确认仍指向项目需要的版本
nvm unalias default      # 若是 nvm 自己创建的，删掉恢复原状
node -v                  # 非登录 shell 应与安装前一致
```

注意 `stable` / `node` 这两个内置别名会跟着最新安装版本走，装了 22 就回不去——这是安装
本身的固有结果，不是别名设置问题。

### 踩坑 7：`test_fill_form_logic` 不是纯单元测试

CI 首次运行即失败：该文件 `import fill_form`，而 `fill_form.py` 顶层 `import playwright`，
缺包会在 unittest **loader 阶段**就 ImportError（报 `Ran 38 tests` 而非全量）。单测 job 必须
装 `requirements-runtime.txt`，但**不需要**下载 Chromium——浏览器只有仿真 e2e 用得到。

### 踩坑 8：git hook 里 `dirname "$0"` 会解析到 `.git`

`hooks/pre-push` 装成 `.git/hooks/pre-push` 软链后，`$(dirname "$0")/..` 得到的是 `.git`
而不是仓库根，脚本立刻找不到 `tests/`。hook 里一律用：

```bash
ROOT="$(git rev-parse --show-toplevel)"
```

### 踩坑 9：测试假数据撞脱敏门禁

新增附件测试时，假字段 id 用了「大写 F + 7 位数字」这个形状——正好命中 `SENSITIVE_PATTERNS`，
被 `test_public_tree` 当场拦下。**连测试夹具都要避开真实标识的形状**；这也反过来证明门禁有效。

后续写本条踩坑说明时**又中了一次**——正文里原样写出那个形状，`test_public_tree` 再次拦下。
结论：连"讨论敏感形状"的文档也不能把形状写出来，只能描述它（"大写 F + 7 位数字"）。

### 踩坑 10：提交身份忘带 noreply 被钩子拦

用默认 git 身份（公司邮箱）做了一次空提交，`scan_history.py` 的身份校验立刻拦住推送。
治本是设仓库级身份，别靠每次手打：

```bash
git config --local user.email "<GitHub 数字 ID>+<用户名>@users.noreply.github.com"
```

### README「复制给 AI」粘贴块验收（PASS）

在隔离 HOME 里逐条执行 README 那段自然语言指令（这是脚本化验收覆盖不到的部分——它验的是
**指令本身是否完整可执行**）：

| 步骤 | 结果 |
|---|---|
| `npx skills add` | ✅ |
| Codex 补链 | ✅ 且证实必要（见踩坑 5） |
| `bootstrap.sh` | ✅ 全新下载 Chromium 114MB、建 venv、写 `dtwr/root` |
| Verify 自检 5 条 | ✅ 全过 |
| `configure.py --check` | ✅ 正确 fail-loud 列出缺失项 |
| 安装物无维护者路径 | ✅ |
| 版本号随包分发 | ✅ `VERSION: 0.1.0` |

附带确认：`--check` 的缺失清单**跳过了 `attach`**，说明"附件字段可留空"在从 GitHub 全新安装
的产物里端到端生效，不只是本地测试通过。

## 2026-07-28 首次真机全流程：登录路径与编辑态踩坑

本轮第一次真机跑通「登录 → 编辑既有草稿 → 落草稿」。**一天之内在登录这一块连撞四个 bug、
在填表这一块连撞三个**，根因是同一个：

> **这些分支从来没有真机里程。** 维护者一直用 auth 链接登录、一直走「新增」路径，
> 扫码分支和编辑分支等于零覆盖。仿真表单测不出来——它没有登录、没有受控上传组件、
> 没有 iframe 生命周期。

七个 bug 里有 **六个是同一种毛病：只做了动作，没做正向确认**。这条教训值得单列：
**"点了"不等于"成了"，凡是跨进程/跨网络的动作都必须回读证据。**

### 踩坑 11：登录判据不能用「URL 里没有 login」

氚云登录页的 URL **不含** `login`，也不含 `entry/auth`。于是：

- `--login` 一打开登录页就判定成功，把**未登录**的会话存成 `state.json`（用户还没扫码）
- `--dump-list` / `--dump-record` 在登录过期时**静默产出登录页的 dump**，还照常写文件给统计

判据必须是**正向确认看见预期页面标识**（本项目用 `form_texts.report_title`）。
`--keepalive` 本来就是这么做的，是新加的模式漏了。

### 踩坑 12：登录页默认是密码登录，二维码要先点开

`login.png` 里从来没有二维码——扫码入口藏在「或」下面那排 40×40 图标后面（`<img>` 无
alt/title，从 DOM 分不出哪个是钉钉）。`--login` 从不点它，于是提示写着「等待扫码」而无码可扫。
实跑确认第 1 个图标即「钉钉扫码登录」。

### 踩坑 13：二维码是 ticket，绑定生成它的浏览器实例

二维码跑在 `login.dingtalk.com/login/qrcode.htm` 的 iframe 里，是钉钉 OAuth 的 ticket。
**在自己浏览器打开登录页扫码是无效的**——会话会落到那个浏览器。
但**把工具生成的那张图拿到任何地方扫都有效**（下载到手机、投屏、拍屏幕）。
区别不在"你在哪儿看"，而在"这张图是谁生成的"。

链接形态的凭证则相反：`entry/auth?token=` 是 bearer token，任何浏览器打开都能换到会话，
所以可以转交——这也是 `--login-url` 成立的原因。**注意「打印内部二维码」的链接编码在图里、
不在地址栏**；「打印外链二维码」给的是公开表单地址（无 token），登不了。

### 踩坑 14：短信验证码被阿里云滑块拦下

点「发送验证码」触发 `uhset9.captcha-open.aliyuncs.com` 的 PUZZLE 滑块（`VerifyCode: F001`
未通过），**短信根本不会送达**。`--login-sms` 因此在本租户不可用，已降级并在检测到弹层时
fail-loud。**本项目不绕过验证码**——那是反滥用控制，绕它既不合适也不稳定。

### 踩坑 15：受控上传组件消费文件后会清空原生 input

真实表单上传成功后 `input[type=file].files.length == 0` 是**正常**的，不是失败。
原先把"控件持有文件"当第 1 层证据，在真机上必然误判。改为以
`.h3-upload-list__item.is-success` 的 `title == 文件名` 为完成证据（更强的正向确认），
仿真态才查 `files.length`。

### 踩坑 16：编辑态的日期控件与 detached frame

- 字段**已有值**时点 input 不弹日期面板；且页面存在多个 `.ant-calendar-input`，
  只有可见的那个能用。改为：值已正确就跳过、重试并改点 picker 图标、只选可见面板、
  **写入后回读校验**。
- 点「暂存」后 FormAdapter frame 会 **detach**，遍历 `page.frames` 查询它会抛 `PWError`，
  把本来成功的暂存变成异常。改为跳过 detached frame 并对 `PWError` 二次确认。

### 踩坑 17：字段自动发现要用「已生效」记录，不要用草稿

同一套匹配器：对**已生效**记录是 8/10 自动定位、零错误；对**草稿**（编辑态）只有
3 确定 / 4 歧义，且歧义项列出十几个候选。原因是编辑态 DOM 结构不同（控件是可编辑组件，
不是只读网格）。`--dump-record N` 取证时**避开状态为草稿的那条**。

### 踩坑 18：keepalive cron 每天静默失败（会话过期的真因）

会话在 07-25 之后失效，一直以为是「那几天机器没开机」。实际查下来，crontab 里那条是：

```
30 9 * * * cd <源码仓> && .venv/bin/python skills/.../fill_form.py --keepalive >> output/keepalive.log 2>&1
```

**三重错误**：

1. `cd` 进的是**源码仓**而不是 `$WORK`——项目自己三令五申「源码仓不得兼作 `$WORK`」；
2. `>> output/keepalive.log` 是**相对 cwd** 的，而源码仓里根本没有 `output/` 目录
   → **重定向直接失败、命令压根没执行**（实跑复现：`bash: output/keepalive.log: 没有那个文件或目录`，退出码 1）；
3. 全程**无声**——cron 的 stderr 没人看，日志文件又建不出来，于是「没有日志」被误读成「没到点」。

`bootstrap.sh` 打印的模板本来是对的（`cd $WORK && $PY $SKILL/scripts/...`），是装进 crontab
的那份被手改过或来自旧目录布局。

修法：全绝对路径、cwd 指向 `$WORK`，并加 15:30 冗余时段（机器上午没开也能补上）。
**与本轮其余六个 bug 同源**：重定向失败属于「动作没做成却无人知晓」。定时任务尤其需要
**成功证据**（这里就是日志里那行 `keepalive OK`）——在 cron 场景下只看「有没有报错」等于什么都没看。

### 本轮真机验收结论

| 环节 | 状态 |
|---|---|
| 登录（`--login-web` 本地网页扫码） | ✅ 通过 |
| 定位并打开目标周既有草稿（两道护栏） | ✅ 通过 |
| 移除旧附件 → 上传 → 完成校验 | ✅ 通过（修完踩坑 15 后） |
| 10 行子表填充（含补行） | ✅ 通过（修完踩坑 16 后） |
| **点「暂存」→ `verify_draft_saved` 正向确认** | ❌ **仍未真机验证**——该次暂存是在脚本外单独完成的，日志无「草稿暂存成功」行 |
| 钉钉最终提交 | ❌ 设计上只能人工 |

独立核对（不采信工具自述，直接查列表）：`2026-07-20 / 42.50 / 草稿`，原值 17.00 → 确已写入。

**三次失败全部 fail-loud、无一留下半截草稿**——这是前几轮做「正向确认」与「宁可中止」的直接回报。

## 2026-07-28 首次 `RELEASE ACCEPTANCE PASS`

`run_release_acceptance.sh` **第一次跑到全绿**（此前每次都卡在第 6 步审计门禁）：

| 步骤 | 结果 |
|---|---|
| 1 本地 HEAD == 远端 | ✅ |
| 2 GitHub 下载 + Skills CLI 安装 | ✅ 安装副本与提交逐字节一致——**装到的是最新代码，不是平台缓存** |
| 3 bootstrap（venv + Chromium） | ✅ |
| 4 在安装副本上跑测试 | ✅ 46 + 29 项 |
| 5 附件 + 仿真草稿 | ✅ `MOCK e2e PASS` |
| 6 skills.sh 审计门禁 | ✅ 评级与已复审基线一致 |

**门禁这次干了正事**：评级从 `Critical Risk` 变为 `Med Risk`，门禁立刻 FAIL 并要求人工复审，
没有默默放行。复审结论——**这不是我们改好了什么，是 skills.sh 的渲染口径对齐了**：
此前 CLI 说 `Critical`、平台页面说 `MEDIUM`，两处矛盾；现在 CLI 也显示 `Med`。
**告警内容本身没变**（Snyk W012 + Socket LOW Anomaly），处置说明仍在 `SECURITY.md`。

这正是把门禁从「grep Critical 就失败」改成「与已复审基线比对」的价值：恒红的门禁等于没门禁，
基线比对才能在评级真变化时叫住人。基线文件里附了本次复审结论。

### 「装得上」≠「用得起来」

链路通了，别人 `npx skills add dff652/dingtalk-weekly-report` 确实能装上并拿到最新代码。
但对新用户还有两道坎，分发时必须说清：

| 坎 | 现状 |
|---|---|
| 取表单元数据（10 个字段 id + 枚举） | 已从「手抄」降到「确认候选」（真机 8/10 自动定位），但**枚举仍需人工补全** |
| DOM 选择器的通用性 | `FormAdapter` / `subgrid-sheet__row` / `tg-row` / `h3-upload-list` 是氚云通用形态，但**只在维护者一个租户验证过**；别家表单若有差异会在 `--dump` 阶段暴露 |

当前定位：**同为氚云用户、且技术上配得动的人可以装来用**；第一个同事最好是能当面帮着调的那个。

另：skills.sh 显示的 install 计数**基本都是自己的验收**（每跑一次发行验收就 +1），别读成采用量。

## 2026-07-28 晚：不变量测试与 P3 调研踩坑

这一轮**没写功能代码**，产出是一个不变量测试 + 一份 P3 决定。踩的坑集中在
「怎么确认自己写的测试真的有用」和「怎么在没有凭据的前提下判定一个方案」。

### 踩坑 19：重复实现了已有断言，顺带第三次撞脱敏门禁

给「无提交能力」补测试时写了四条断言，其中第四条（把 `save_draft` 配成提交按钮必须被拦）
`test_core.py` 里**早就有了**（`test_config_rejects_submit_button_as_draft_action`）。
为了造一份合法 config 夹具，又需要一批假字段 id——于是用了那个形状（大写 F + 7 位数字），
`test_public_tree` **第三次**当场拦下（前两次见踩坑 9）。

两个教训，第二个才是根因：

1. 表面：连测试夹具都要避开真实标识形状（踩坑 9 已记，本次是复发）；
2. **根因：加测试前先 `grep` 现有断言。** 这条重复的断言不仅白写，还顺带把自己送进了门禁——
   如果先查一下，两个问题都不会发生。删掉后改成一行注释指向 `test_core.py`，
   并写明分工：新文件守**代码**，那条守**配置**。

### 踩坑 20：`Ran 72 tests` 不是 99，而报的是 `FAILED` 不是「环境不全」

用裸 `python3 -m unittest discover` 跑测试，结果 `Ran 72 tests`，比预期少 27 项。
真因是踩坑 7 的复发面貌：`test_fill_form_logic` 需要 playwright，缺包在 **loader 阶段**
就 ERROR，那一整个文件的测试**根本没被计数**。

危险的地方不在于它红了，而在于**它红的理由看起来像"环境问题"**——很容易被当成已知的
预存失败跳过，从而以为覆盖跑全了。canonical 命令是：

```bash
~/weekly-report-data/.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

**判读规则：先看 `Ran N tests` 的 N 对不对，再看 OK/FAILED。** 测试数量下降是静默的
覆盖损失，本项目其它地方（附件校验、暂存确认）反复吃过"没看到失败 ≠ 成功"的亏，
测试自己这一层不能例外。

### 踩坑 21：新增"守承诺"的测试，必须先证明它会红

`test_invariants.py` 守的是「工具没有提交能力」。这类测试有个特有的失效模式：
**它可能永远是绿的**——正则写错、白名单集合恒等、扫错文件，都会让断言变成空转，
而空转的测试比没有测试更坏（它提供虚假的安全感）。

所以写完立刻做了反向验证：往 `fill_form.py` 注入一行假的提交点击 → 确认测试 FAIL 并
打印出注入的那一行 → 还原 → 确认回到 OK。

**规则：凡是"守住某条不会发生的事"的测试，必须先让它红一次。** 只验证"改对了会绿"
是不够的，那是所有空断言都能通过的检验。

### 踩坑 22：单一来源的 API 文档不足以定契约

判定 P3 时要查氚云 OpenApi 的行为，过程中两件事值得记：

- **抓文档本身不可靠**：`qliang.cloud` 证书 SAN 不匹配、另一站直接 socket closed。
  同一份文档在镜像站（`qeasy.cloud`）能取到——**换镜像比放弃便宜**。
- **跨来源对拍后发现口径冲突**：`IsSubmit` 参数在一处标类型 `Bool`、另一处标 `string`
  且示例写成带引号的字符串；默认值一处标 `true`、官方镜像标「必填、默认值未指定」。

结论不是"挑一个信"，而是：**冲突处只能由真实调用裁决**。而这条恰好成了 P3 被否的
证据之一——一个"传错就不可逆提交"的参数，其类型和默认值居然查不到确定答案。
详见 [MAINTAINER.md 的 P3 决定](MAINTAINER.md#p3-决定暂不采用氚云-openapi2026-07-28)。

### 顺带自证：踩坑 18（cron 静默失败）的修复当天生效

不必等次日——`keepalive.log` 在 15:30 出现新行，正是那次修复**新加的冗余时段**写的。
绝对路径 + 冗余时段两处改动同时得到验证。

## 尚未完成

| 项目 | 状态 | 原因 |
|---|---|---|
| Windows PowerShell 实机 | 未验证 | 当前环境无 PowerShell |
| Skills.sh 安全重扫 | ✅ 已完成 | 2026-07-28 `RELEASE ACCEPTANCE PASS`；评级 Critical→Med 已人工复审并更新基线 |
| 真实氚云暂存验收（`verify_draft_saved` 那一段） | 部分完成 | 填表与附件已真机通过；**点「暂存」后的正向确认那一小段仍未跑到**——07-28 那次暂存是在脚本外完成的。下次报工自然覆盖 |
| 钉钉最终提交 | 不自动测试 | 设计上只能由用户人工执行 |

所以准确结论是：**完整自动测试与远端发行验收均已通过；真机只剩「暂存后正向确认」这一小段没跑到。**

三个验收层级不得混用：

1. `run_full_acceptance.sh`：本地技能包的自动仿真闭环；
2. `run_release_acceptance.sh`：远端提交、GitHub 下载、Skills CLI、运行态、仿真与审计门禁；
3. [MANUAL_ACCEPTANCE.md](MANUAL_ACCEPTANCE.md)：真实个人配置、登录、氚云草稿和钉钉提交。
