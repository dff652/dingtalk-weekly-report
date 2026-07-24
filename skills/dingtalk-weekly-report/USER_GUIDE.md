# 用户指南：安装与使用

随 skill 分发（`npx skills` / zip / `install.sh` 安装后本文件在技能目录内）。  
仓库短入口（含「复制给 AI」整段）：仓库根 [README.md](https://github.com/dff652/dingtalk-weekly-report#readme)。  
Agent 流程见同目录 `SKILL.md`；字段见 `references/FIELDS.md`。

## 1. 你需要什么

| 必备 | 说明 |
|------|------|
| Claude Code 和/或 Codex | 或纯 CLI |
| [Node.js](https://nodejs.org/)（`npx`） | **推荐**生态安装；无 Node 用 zip/`install.sh` |
| [uv](https://docs.astral.sh/uv/) | bootstrap 用 |
| 手机钉钉 | 扫「打印内部二维码」 |
| 表单项目原文 | 下拉「项目/产品名称」**完整字符串** |
| 可选 | 工作日志路径（无则访谈式） |

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
4) 引导填写 config、钉钉登录；用 /dingtalk-weekly-report 做周报；只 --draft --confirmed；脚本无提交能力；内容人审。
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
| Codex | `~/.codex/skills/…`（建议显式补链）及/或 `~/.agents/skills/…` | 同名 skill |
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
2. 登录：会话里跟 agent，或  

```bash
cd ~/weekly-report-data
.venv/bin/python ~/.claude/skills/dingtalk-weekly-report/scripts/fill_form.py \
  --login-url 'https://www.h3yun.com/entry/auth?token=…'
```

3. 可选保活：cron / 计划任务跑 `fill_form.py --keepalive`。  
登录态：`~/.config/dtwr/state.json`（0600）。

## 3. 每周使用

### 3.1 AI（推荐）

```text
/dingtalk-weekly-report
/dingtalk-weekly-report 2026-07-20
```

人审 → `--draft --confirmed` → **你**在钉钉提交。铁律：不自动提交；删同周旧草稿。补交上周：**周一 17:00 前**。

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
| `--login-url` / `--keepalive` / `--dump` | 登录 / 续期 / 诊断 |

## 4. FAQ

| 现象 | 处理 |
|------|------|
| Codex 无 skill | 做 §2.1 补链；或 `install.sh --force` |
| `npx skills` 找不到 skill | 确认仓库 public 且含 `skills/dingtalk-weekly-report/SKILL.md` |
| extract 拒绝写 | json 已存在 |
| 会话失效 | 内部二维码 → `--login-url` |
| 填表失败 | `output/shots/99-error.png` + `references/FIELDS.md` |

## 5. 安全

输入、缺失处理和输出契约见 `references/CONTRACT.md`。只草稿、人提交；勿用他人
`$WORK`/登录态；auth 链接与 `state.json` 当凭证。
