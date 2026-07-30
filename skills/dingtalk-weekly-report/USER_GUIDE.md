# 用户指南：安装与使用

随 skill 分发（`npx skills` / zip / `install.sh` 安装后本文件在技能目录内）。  
仓库价值、边界与最短安装入口：根
[README.md](https://github.com/dff652/dingtalk-weekly-report#readme)。本文件保留完整安装、
「复制给 AI」、验证与每周操作说明。
Agent 流程见同目录 `SKILL.md`；字段见 `references/FIELDS.md`。

## 1. 你需要什么

| 必备 | 说明 |
|------|------|
| Claude Code 和/或 Codex | 或纯 CLI |
| [Node.js](https://nodejs.org/)（`npx`） | **推荐**生态安装；`skills@1.5.20` 需 `>=22.20.0`；无 Node 用 zip/`install.sh` |
| [uv](https://docs.astral.sh/uv/) | bootstrap 用 |
| 手机钉钉 | 扫码登录 |
| 表单项目原文 | 下拉「项目/产品名称」**完整字符串** |
| 表单元数据 | 本人或管理员确认的字段 DOM id、按钮文本与合法下拉值 |
| 可选 | 工作日志文件或项目目录（无则访谈式） |

本项目采用 [Apache-2.0](LICENSE)。公开 Skill 不含任何组织的表单 ID、枚举、项目或个人周报；
这些值只保存在每用户私有 `$WORK/config.json`。

## 2. 安装（一次）

### 2.1 推荐：skills hub / `npx skills`（GitHub）

```bash
npx skills add https://github.com/dff652/dingtalk-weekly-report \
  --skill dingtalk-weekly-report \
  --agent claude-code \
  --agent codex \
  --global --yes --copy

# Codex 专用目录补链（npx 常只装到 ~/.claude 与 ~/.agents）
mkdir -p ~/.codex/skills
ln -sfn ~/.claude/skills/dingtalk-weekly-report \
        ~/.codex/skills/dingtalk-weekly-report

bash ~/.claude/skills/dingtalk-weekly-report/bootstrap.sh
```

简写：`npx skills add dff652/dingtalk-weekly-report -s dingtalk-weekly-report -a claude-code -a codex -g -y --copy`

升级：`npx skills update dingtalk-weekly-report -g -y`

### 2.2 只给仓库 URL：复制给 AI

```text
请根据 https://github.com/dff652/dingtalk-weekly-report 安装 skill dingtalk-weekly-report：
1) npx skills add https://github.com/dff652/dingtalk-weekly-report --skill dingtalk-weekly-report --agent claude-code --agent codex --global --yes --copy
2) 若无 ~/.codex/skills/dingtalk-weekly-report：ln -sfn ~/.claude/skills/dingtalk-weekly-report ~/.codex/skills/dingtalk-weekly-report（先 mkdir -p ~/.codex/skills）
3) bash ~/.claude/skills/dingtalk-weekly-report/bootstrap.sh
4) 通过 configure.py 引导填写本人有权使用的表单 URL、字段 ID、按钮文本、枚举与项目并完成钉钉登录；Claude 用 /dingtalk-weekly-report、Codex 用 $dingtalk-weekly-report（或 /skills 选择）做周报；只 --draft --confirmed；脚本无提交能力；内容人审；不得猜测组织字段，不得保存或接收 entry/auth 链接。
5) 按本指南 2.5 Verify 自检并汇报。
```

AI **不能**代替：项目下拉原文、扫码、人审、钉钉提交。

### 2.3 回退：zip / 本地 install

```bash
# 解压 pack-skill 产物后
bash install.sh && bash bootstrap.sh
```

Windows：`.\install.ps1` → `.\bootstrap.ps1`  
维护仓：`bash install.sh --link`（仓库根）

### 2.4 装到哪里、怎么触发

| 工具 | 路径 | 触发 |
|------|------|------|
| Claude Code | `~/.claude/skills/dingtalk-weekly-report/` | `/dingtalk-weekly-report` |
| Codex | `~/.codex/skills/…`（建议显式补链）及/或 `~/.agents/skills/…` | `$dingtalk-weekly-report` 或 `/skills` 选择 |
| Agents | `~/.agents/skills/…` | 视工具 |

### 2.5 Verify（自检）

```bash
[ -f ~/.claude/skills/dingtalk-weekly-report/SKILL.md ] && echo "Claude skill OK" || echo "Claude skill MISSING"
if [ -f ~/.codex/skills/dingtalk-weekly-report/SKILL.md ]; then
  echo "Codex skill OK"
elif [ -f ~/.agents/skills/dingtalk-weekly-report/SKILL.md ]; then
  echo "Agents skill OK（建议补链到 ~/.codex/skills）"
else
  echo "Codex/Agents skill MISSING"
fi
[ -f ~/weekly-report-data/config.json ] && echo "config OK" || echo "config MISSING"
[ -f ~/.config/dtwr/root ] && echo "dtwr: $(cat ~/.config/dtwr/root)" || echo "dtwr MISSING"
~/weekly-report-data/.venv/bin/python -c "import playwright; print('playwright OK')" 2>/dev/null \
  || echo "playwright MISSING"
~/weekly-report-data/.venv/bin/python \
  ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py --check
```

### 2.6 首次配置

1. 先查看缺项。AI 调用 Skill 时会读取同一份清单并主动询问；不会要求你自己寻找并编辑
   `config.json`：

```bash
cd ~/weekly-report-data
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py --missing
```

   用户本人在本机交互填写缺少的姓名、表单 URL、表单项目和附件项目：

```bash
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py --guided
```

   `--guided` 允许先安全保存基础信息，字段 ID 尚未发现并不阻断保存；但最终填表仍必须通过
   完整 `--check`。每次保存都会备份旧配置为 `$WORK/config.json.bak`。一次性 entry/auth
   登录链接会被拒绝，不得保存为 `form_url`。

2. 登录首选扫码：会话里跟 Agent，或在终端运行：

```bash
cd ~/weekly-report-data
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/fill_form.py --login
```

若必须使用一次性 auth 链接，由你本人在本机交互终端运行以下命令，再按隐藏提示粘贴：

```bash
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/fill_form.py --login-url
```

不要把 auth 链接发给 Agent，也不要放进命令参数、聊天、文件或 git。

3. 按 `references/FIELDS.md` 用 `--dump-record N` 自动发现字段候选，再逐项确认写入：

```bash
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/fill_form.py --dump-record 2
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py --from-discovery
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py --check
```

   `progress_report` 可填工作日志文件，或含 `docs/report/PROGRESS_REPORT.md` 的项目目录；
   工具不会扫描项目或读取 git log。第三条命令用于补齐尚未发现的枚举和按钮文字；已有值直接
   回车保留。字段、枚举和按钮文字必须来自本人或管理员确认。
   Skill 和 `$WORK` 必须分离，不要把 `$WORK` 放进 Skill 或源码仓库。

4. 可选保活：cron / 计划任务跑 `fill_form.py --keepalive`。
登录态：`~/.config/dtwr/state.json`（0600）。

### 2.7 后续查看与重新配置

首次配置会保存在 `$WORK/config.json`，以后每周不需要重复填写。项目、表单地址、工作日志路径、
默认工时或会议发生变化时，重新运行配置向导即可，不要重跑 bootstrap：

```bash
# 查看 / 校验，不修改
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py --show
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py --missing
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py --check

# 交互更新；回车保留，- 清空可选项
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py

# 首次配置只询问当前缺少的用户必填项
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py --guided
```

Windows 将 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`，技能路径使用实际安装目录。
登录态失效只需重新扫码，不需要重新配置。

从旧版 config v1 升级时运行同一向导，补齐 `vocabulary`、`form_fields`、`form_texts`；
向导会升级为 `config_version=2`。旧周报需要在私有 `$WORK` 中重新生成，或补入
`schema_version=2` 与当前 `vocabulary`。

## 2.5 不知道下一步做什么？先跑自检

```bash
~/weekly-report-data/.venv/bin/python \
  ~/.claude/skills/dingtalk-weekly-report/scripts/fill_form.py --status
```

秒出，不联网。它读**当前真实状态**并直接给下一步：配置是否就绪、登录态与保活日志的新鲜度、
本周 json 是否存在／有没有 TODO、附件是否已生成。**卡在哪一步都可以先跑它**，
不用回来翻文档。

（保活日志那一项专门防一类坑：cron 写错路径会**每天静默失败**，而"没有日志"很容易被误读成
"没到点"。自检直接告诉你日志多久没更新了。）

## 3. 每周使用

### 3.1 AI（推荐）

```text
# Claude Code
/dingtalk-weekly-report
/dingtalk-weekly-report 2026-07-20

# Codex
$dingtalk-weekly-report
$dingtalk-weekly-report 2026-07-20
```

Codex 也可先运行 `/skills` 再选择；不要只靠自然语言提及来判断 skill 已触发。

人审 → `--draft --confirmed` → **你**在钉钉提交。铁律：不自动提交；检查同周记录。
工具默认编辑「状态=草稿 且 开始日期=目标周周一」的既有记录，找不到才新建，**不需要先删草稿**；
同周已有非草稿记录或多条记录时先停止并人工确认。
提交截止时间以 `submission_reminder` 和所在组织规则为准。
`--confirmed` 仅表示操作者完成了检查清单，不构成人审记录或审计证明。

### 3.2 CLI

```bash
export WORK=~/weekly-report-data
export SKILL=~/.claude/skills/dingtalk-weekly-report
cd "$WORK"

python3 "$SKILL/scripts/extract_week.py"    # 已存在 json 会拒绝覆盖
python3 "$SKILL/scripts/gen_attachment.py" weeks/week_report_YYYYMMDD.json
.venv/bin/python "$SKILL/scripts/fill_form.py" --keepalive
.venv/bin/python "$SKILL/scripts/fill_form.py" weeks/week_report_YYYYMMDD.json --draft --confirmed
python3 "$SKILL/scripts/print_form_rows.py" weeks/week_report_YYYYMMDD.json   # 回退
```

### 3.3 fill_form 速查

| 命令 | 作用 |
|------|------|
| `json` | 只填不存 |
| `json --draft --confirmed` | 人审并检查旧草稿后，正式落草稿 |
| `--login` | 首选扫码登录 |
| `--login-url` | 用户本人在交互终端隐藏输入 auth 链接；不接受 URL 参数 |
| `--keepalive` / `--dump` | 续期 / 诊断 |

## 4. FAQ

| 现象 | 处理 |
|------|------|
| npx 只写了 `~/.agents/skills` | 先用 `npx skills list -g` 确认 Agents 含 Codex；仅当 Codex 确实无法发现时做 §2.1 补链 |
| Codex 无 skill | 做 §2.1 补链；或 `install.sh --force` |
| `node:util` 缺 `styleText` / `EBADENGINE` | Node 过旧；`skills@1.5.20` 升到 Node `>=22.20.0` |
| Chromium 下载处长时间无新输出 | 检查下载进程是否仍在运行；看到 `bootstrap 完成` 且 `~/.config/dtwr/root` 已写入才算成功，失败可原命令重跑 |
| 已 bootstrap，换目录运行却报 cwd 缺 config | 先升级 skill；临时可 `cd $WORK` 或显式设置 `DTWR_HOME=$WORK` |
| `npx skills` 找不到 skill | 确认仓库 public 且含 `skills/dingtalk-weekly-report/SKILL.md` |
| extract 拒绝写 | json 已存在 |
| 会话失效 | 首选 `--login` 扫码；URL 兜底由用户本人运行 `--login-url` 后隐藏输入 |
| 填表失败 | `output/shots/99-error.png` + `references/FIELDS.md` |

## 5. 换设备 / 分发给同事

**登录态不要拷贝。** `~/.config/dtwr/state.json` 是活凭证（一份已登录会话）。新设备自己登录，
别拷这个文件，也别把它放进同步盘。

**多端登录可能互踢。** 临近提交截止时别在另一台设备上重新登录，否则可能在最需要时被踢下线。

**只在一台设备上落草稿。** 同一周多份草稿会撞表单的「周报唯一性判定」。在新设备上验证时
跑到预览为止——不加 `--draft`，工具默认就是只填不存：

```bash
~/weekly-report-data/.venv/bin/python \
  ~/.claude/skills/dingtalk-weekly-report/scripts/fill_form.py weeks/week_report_YYYYMMDD.json
```

**搬配置：拷文件或重填，都别经过聊天。** `~/weekly-report-data/config.json` 里是你所在组织的
表单标识和枚举，用 U 盘 / scp 拷过去，或在新设备重跑 `configure.py` 照着填。**不要**把这些值
粘贴进 AI 会话、聊天窗口或 issue。

**扫码还是打印链接？** 两条都行，看设备：

| 设备情况 | 用哪条 |
|---|---|
| **远程开发 / 不想翻文件** | **`--login-web`** —— 本地网页显示二维码 + 实时状态，浏览器打开扫一下（只绑 127.0.0.1，VSCode 会自动转发端口） |
| 不想找图、能收短信 | `--login-sms` —— **可能被滑块验证码拦下**（本维护者租户实测即如此），届时会 fail-loud 提示改用扫码 |
| 能打开 `output/shots/login.png` | `--login` 扫码，不产生可复制的秘密 |
| 无图形界面 / 远程机器 | `--login-url`，你本人在该机终端隐藏输入 |

**注意**：二维码必须扫**工具生成的那一张**。把图下载到手机、投屏、拍屏幕都行；
但**在你自己浏览器里打开登录页去扫是无效的**——会话会落到你的浏览器，工具拿不到。

**别把同一条 auth 链接在设备间转发**——它 48 小时内等效登录凭证，转发会让它留在剪贴板、
命令历史和传输通道里。换设备就重新获取一条。

## 6. 安全

输入、缺失处理和输出契约见 `references/CONTRACT.md`。只草稿、人提交；勿用他人
`$WORK`/登录态；auth 链接与 `state.json` 当凭证。auth 链接不得交给 Agent，不得进入参数、
聊天、文件或 git。属主自动检查目前仅在 POSIX 系统启用；Windows 依赖独立用户目录和
系统 ACL 隔离。
