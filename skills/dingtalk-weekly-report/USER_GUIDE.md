# 用户指南：安装与使用

**本文件随技能 zip 分发**（与 `install.sh` 同目录）。  
维护仓另见仓库根 `README.md`；Agent 流程见 `SKILL.md`；表单字段见 `references/FIELDS.md`。

## 1. 你需要什么

| 必备 | 说明 |
|------|------|
| AI 工具之一 | Claude Code 和/或 Codex CLI（也可纯命令行） |
| [uv](https://docs.astral.sh/uv/) | bootstrap 创建 Python 虚拟环境用 |
| 手机钉钉 | 首次登录扫「打印内部二维码」 |
| 表单项目原文 | 氚云下拉「项目/产品名称」**完整字符串**（空格一致） |
| 可选 | 个人工作日志路径（没有则每周访谈式填内容） |

- **不要** clone 私有维护仓；**要**公司内部分发的 skill zip。  
- 包内含公司表单结构，**仅限公司内部分发**。

## 2. 安装（一次）

### 2.1 Linux / macOS / WSL

```bash
unzip dingtalk-weekly-report-skill-YYYYMMDD.zip
cd dingtalk-weekly-report   # zip 根目录即本技能包

bash install.sh             # ① 技能 → Claude / Codex / Agents
bash bootstrap.sh           # ② $WORK + uv + Playwright Chromium
# 默认 $WORK=~/weekly-report-data
# 自定义: bash bootstrap.sh --work ~/my-weekly-data
```

### 2.2 Windows（PowerShell）

```powershell
# 解压后进入技能目录 dingtalk-weekly-report\
.\install.ps1
.\bootstrap.ps1
# .\bootstrap.ps1 -Work "$env:USERPROFILE\weekly-report-data"
```

### 2.3 装到哪里、怎么触发

| 工具 | 技能路径 | 触发 |
|------|----------|------|
| Claude Code | `~/.claude/skills/dingtalk-weekly-report/` | 新会话 `/dingtalk-weekly-report` |
| Codex CLI | `~/.codex/skills/dingtalk-weekly-report/` | 同名 skill（**skills 目录**，不是旧 `prompts`） |
| 其他 Agents | `~/.agents/skills/…`（本机已有 `~/.agents` 时） | 视工具而定 |

| 操作 | Linux/mac/WSL | Windows |
|------|---------------|---------|
| 升级技能（保留 config/登录） | `bash install.sh --force` | `.\install.ps1 -Force` |
| 重建 venv | `bash bootstrap.sh --force-venv` | `.\bootstrap.ps1 -ForceVenv` |
| 维护仓软链 | 仓库根 `bash install.sh --link` | 建议 WSL |

### 2.4 安装是否成功（自检）

```bash
# 技能文件
test -f ~/.claude/skills/dingtalk-weekly-report/SKILL.md && echo Claude OK
test -f ~/.codex/skills/dingtalk-weekly-report/SKILL.md && echo Codex OK   # 若装了 Codex

# 工作目录与指针
test -f ~/weekly-report-data/config.json && echo config OK
cat ~/.config/dtwr/root    # 应为一行 $WORK 绝对路径
~/weekly-report-data/.venv/bin/python -c "import playwright; print('playwright OK')"
```

### 2.5 首次配置清单

1. 编辑 `$WORK/config.json`（bootstrap 已从 `assets/config.example.json` 拷出）：
   - `name`：姓名  
   - `form_project`：表单下拉**完整原文**  
   - `attach_project`：附件关联项目  
   - `progress_report`：工作日志绝对路径，没有则 `""`  
   - `form_url`：一般用模板中的公司表单链接  
2. 登录（二选一）：
   - **推荐**：AI 会话 `/dingtalk-weekly-report`，失效时粘贴 `h3yun.com/entry/auth?token=…`  
   - 命令行：

```bash
cd "${DTWR_HOME:-$HOME/weekly-report-data}"
SKILL="$HOME/.claude/skills/dingtalk-weekly-report"
.venv/bin/python "$SKILL/scripts/fill_form.py" --login-url 'https://www.h3yun.com/entry/auth?token=…'
```

3. （可选）每日保活  
   - Linux/mac：`30 9 * * * cd $WORK && .venv/bin/python $SKILL/scripts/fill_form.py --keepalive >> output/keepalive.log 2>&1`  
   - Windows：计划任务，python 用 `.venv\Scripts\python.exe`

登录态：`~/.config/dtwr/state.json`（0600），**勿转发、勿入 git**。

## 3. 每周使用

### 3.1 推荐：AI Skill（约 5 分钟人工）

1. 更新工作日志覆盖目标周（若配置了 `progress_report`）。  
2. 新会话：

```text
/dingtalk-weekly-report
```

或指定周一：`/dingtalk-weekly-report 2026-07-20`

3. Agent：定周 → 生成/更新 `weeks/week_report_*.json` → **人审** → 附件 → `--draft`。  
4. **你**在钉钉打开草稿核对后点「提交」。工具**永不自动提交**。

**三条铁律**：只 `--draft`；内容必人审；落草稿前删同周旧草稿。  
**截止**：补交上周须 **周一 17:00 前**。

### 3.2 纯命令行

```bash
export WORK="${DTWR_HOME:-$HOME/weekly-report-data}"
export SKILL="$HOME/.claude/skills/dingtalk-weekly-report"
cd "$WORK"

python3 "$SKILL/scripts/extract_week.py"              # 默认上一周周一；已存在则拒绝覆盖
# python3 "$SKILL/scripts/extract_week.py" 2026-07-20

# 人审 weeks/week_report_YYYYMMDD.json 后：
python3 "$SKILL/scripts/gen_attachment.py" weeks/week_report_YYYYMMDD.json
.venv/bin/python "$SKILL/scripts/fill_form.py" --keepalive
.venv/bin/python "$SKILL/scripts/fill_form.py" weeks/week_report_YYYYMMDD.json --draft

# 回退粘贴块
python3 "$SKILL/scripts/print_form_rows.py" weeks/week_report_YYYYMMDD.json
```

维护仓把仓库当 `$WORK` 时，脚本路径用 `skills/dingtalk-weekly-report/scripts/…`。

### 3.3 fill_form 模式

| 命令 | 作用 |
|------|------|
| `… json` | 只填不存，截图预览 |
| `… json --draft` | **每周正式**：暂存草稿 |
| `… json --submit` | 直接提交（政策上不用） |
| `--login-url '…'` | token 链接登录 |
| `--keepalive` | 续 cookie |
| `--dump` | DOM 诊断 |

## 4. 维护者（仅维护仓）

```bash
bash pack-skill.sh              # → dist/dingtalk-weekly-report-skill-YYYYMMDD.zip
bash install.sh --link          # 软链开发
bash tests/run_mock_test.sh     # 仿真表单 e2e（改 fill_form 必跑）
bash tests/run_smoke.sh         # pack + 隔离 install + 附件 + 仿真
.venv/bin/python skills/dingtalk-weekly-report/scripts/fill_form.py --keepalive  # 真机会话探测
```

冒烟**不**自动对真机 `--draft`（避免产生公司草稿）；真机落草稿需人工确认后执行。

## 5. 常见问题

| 现象 | 处理 |
|------|------|
| Codex 找不到 skill | 确认 `~/.codex/skills/dingtalk-weekly-report/SKILL.md`；`install.sh --force` |
| `extract_week` 拒绝写 | json 已存在；备份后删除再生成 |
| 会话已失效 | 内部二维码 → `--login-url` |
| 填表失败 | `$WORK/output/shots/99-error.png` + `references/FIELDS.md` |
| 共享机拒跑 | `$WORK` / `~/.config/dtwr` 属主须为当前用户 |
| Windows | 优先 `install.ps1` / `bootstrap.ps1`，或 WSL |

## 6. 安全与合规

- zip **仅限公司内部**。  
- 只落草稿，**人在钉钉提交**。  
- 禁止使用他人 `$WORK` 或登录态。  
- `state.json`、auth 链接视为凭证。
