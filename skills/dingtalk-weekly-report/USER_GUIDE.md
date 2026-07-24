# 用户指南：安装与使用

随 skill 分发（`npx skills` / zip / `install.sh` 安装后本文件在技能目录内）。  
仓库短入口（含「复制给 AI」整段）：仓库根 [README.md](https://github.com/dff652/dingtalk-weekly-report#readme)。  
Agent 流程见同目录 `SKILL.md`；字段见 `references/FIELDS.md`。

## 1. 你需要什么

| 必备 | 说明 |
|------|------|
| Claude Code 和/或 Codex | 或纯 CLI |
| [Node.js](https://nodejs.org/)（`npx`） | **推荐**生态安装；`skills@1.5.20` 需 `>=22.20.0`；无 Node 用 zip/`install.sh` |
| [uv](https://docs.astral.sh/uv/) | bootstrap 用 |
| 手机钉钉 | 扫「打印内部二维码」 |
| 表单项目原文 | 下拉「项目/产品名称」**完整字符串** |
| 可选 | 工作日志文件或项目目录（无则访谈式） |

包内含公司表单结构，**仅限公司内部分发**。

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
4) 引导填写 config、钉钉登录；Claude 用 /dingtalk-weekly-report、Codex 用 $dingtalk-weekly-report（或 /skills 选择）做周报；只 --draft --confirmed；脚本无提交能力；内容人审。
5) 按 README Verify 自检并汇报。
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
```

### 2.6 首次配置

1. 编辑 `$WORK/config.json`：`name`、`form_project`、`attach_project`、`progress_report`（可空）、`form_url`。
   `progress_report` 可填工作日志文件，或含 `docs/report/PROGRESS_REPORT.md` 的项目目录；
   工具不会扫描项目或读取 git log。
2. 登录首选扫码：会话里跟 Agent，或在终端运行：

```bash
cd ~/weekly-report-data
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/fill_form.py --login
```

若必须使用内部二维码 auth 链接，由你本人在本机交互终端运行以下命令，再按隐藏提示粘贴：

```bash
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/fill_form.py --login-url
```

不要把 auth 链接发给 Agent，也不要放进命令参数、聊天、文件或 git。

3. 可选保活：cron / 计划任务跑 `fill_form.py --keepalive`。  
登录态：`~/.config/dtwr/state.json`（0600）。

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

人审 → `--draft --confirmed` → **你**在钉钉提交。铁律：不自动提交；删同周旧草稿。补交上周：**周一 17:00 前**。
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

## 5. 安全

输入、缺失处理和输出契约见 `references/CONTRACT.md`。只草稿、人提交；勿用他人
`$WORK`/登录态；auth 链接与 `state.json` 当凭证。auth 链接不得交给 Agent，不得进入参数、
聊天、文件或 git。属主自动检查目前仅在 POSIX 系统启用；Windows 依赖独立用户目录和
系统 ACL 隔离。
