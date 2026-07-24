# 用户指南：安装与使用

面向**同事**（拿 zip）与**维护者**（本仓库）。技术细节与字段事实源见仓库 `README.md`、`skills/.../SKILL.md`、`FIELDS.md`。

## 1. 你需要什么

| 必备 | 说明 |
|------|------|
| AI 工具之一 | Claude Code 和/或 Codex CLI（也可纯命令行） |
| Python 环境管理 | [uv](https://docs.astral.sh/uv/)（bootstrap 会用到） |
| 手机钉钉 | 首次登录：扫「打印内部二维码」 |
| 表单项目原文 | 氚云下拉「项目/产品名称」**完整字符串**（空格一致） |
| 可选 | 个人工作日志路径（没有则每周访谈式填内容） |

**不要** clone 私有维护仓；**要**拿到公司内部分发的 skill zip。

## 2. 安装（一次）

### 2.1 Linux / macOS / WSL

```bash
unzip dingtalk-weekly-report-skill-YYYYMMDD.zip
cd dingtalk-weekly-report   # 若 zip 解出该目录

# ① 安装技能 → Claude / Codex / Agents 目录
bash install.sh

# ② 建个人工作目录 + Playwright 浏览器
bash bootstrap.sh
# 默认 $WORK=~/weekly-report-data
# 自定义: bash bootstrap.sh --work ~/my-weekly-data
```

### 2.2 Windows（PowerShell）

```powershell
# 解压 zip 后进入技能目录
.\install.ps1
.\bootstrap.ps1
# 自定义工作目录: .\bootstrap.ps1 -Work "$env:USERPROFILE\weekly-report-data"
```

### 2.3 装到哪里、怎么触发

| 工具 | 技能路径 | 触发 |
|------|----------|------|
| Claude Code | `~/.claude/skills/dingtalk-weekly-report/` | 新会话 `/dingtalk-weekly-report` |
| Codex CLI | `~/.codex/skills/dingtalk-weekly-report/` | 同名 skill（skills，不是旧 prompts） |
| 其他 Agents | `~/.agents/skills/…`（若本机有该目录） | 视工具而定 |

升级技能（配置与登录态保留）：

```bash
bash install.sh --force          # Windows: .\install.ps1 -Force
```

环境损坏只重建 venv：

```bash
bash bootstrap.sh --force-venv   # Windows: .\bootstrap.ps1 -ForceVenv
```

### 2.4 首次配置清单

1. 编辑 `$WORK/config.json`（bootstrap 已从模板拷出）：
   - `name`：姓名  
   - `form_project`：表单下拉完整原文  
   - `attach_project`：附件关联项目  
   - `progress_report`：工作日志绝对路径，没有则 `""`  
   - `form_url`：一般用模板里的公司表单链接即可  
2. 登录（二选一）：
   - **推荐**：打开 AI 跑 `/dingtalk-weekly-report`，会话失效时按提示把 `h3yun.com/entry/auth?token=…` 链接发回；或  
   - 命令行：

```bash
cd "$WORK"   # 如 ~/weekly-report-data
SKILL="$HOME/.claude/skills/dingtalk-weekly-report"
.venv/bin/python "$SKILL/scripts/fill_form.py" --login-url 'https://www.h3yun.com/entry/auth?token=…'
```

3. （可选）每日保活  
   - Linux/mac cron：`30 9 * * * cd $WORK && .venv/bin/python $SKILL/scripts/fill_form.py --keepalive >> output/keepalive.log 2>&1`  
   - Windows：计划任务执行同一命令（python 用 `.venv\Scripts\python.exe`）

登录态在 `~/.config/dtwr/state.json`（0600），**勿转发、勿入 git**。

## 3. 每周使用

### 3.1 推荐：AI Skill（约 5 分钟人工）

1. 更新工作日志覆盖目标周（若配置了 `progress_report`）。  
2. 新会话：

```text
/dingtalk-weekly-report
```

或指定周一：

```text
/dingtalk-weekly-report 2026-07-20
```

3. Agent 会：定周 → 生成/更新 `weeks/week_report_*.json` → **给你人审** → 附件 xlsx → `--draft` 落草稿。  
4. **你**在钉钉打开草稿核对后点「提交」。工具**永不自动提交**。

三条铁律：只 `--draft`；内容必人审；落草稿前删同周旧草稿。

截止：补交上周须 **周一 17:00 前**。

### 3.2 纯命令行（同事 `$WORK` 独立）

```bash
export WORK="${DTWR_HOME:-$HOME/weekly-report-data}"
export SKILL="$HOME/.claude/skills/dingtalk-weekly-report"
cd "$WORK"

# 1) 草稿 json（已存在会拒绝覆盖，防冲掉人工改稿）
python3 "$SKILL/scripts/extract_week.py"           # 默认上一周周一
# python3 "$SKILL/scripts/extract_week.py" 2026-07-20

# 2) 人审编辑 weeks/week_report_YYYYMMDD.json 后：
python3 "$SKILL/scripts/gen_attachment.py" weeks/week_report_YYYYMMDD.json

# 3) 会话探测 / 续期
.venv/bin/python "$SKILL/scripts/fill_form.py" --keepalive

# 4) 落草稿（截图 output/shots/）
.venv/bin/python "$SKILL/scripts/fill_form.py" weeks/week_report_YYYYMMDD.json --draft

# 回退：打印粘贴块手工填
python3 "$SKILL/scripts/print_form_rows.py" weeks/week_report_YYYYMMDD.json
```

维护仓若把仓库当 `$WORK`，脚本路径写成 `skills/dingtalk-weekly-report/scripts/…` 即可。

### 3.3 fill_form 模式

| 命令 | 作用 |
|------|------|
| `… json` | 只填不存，截图预览 |
| `… json --draft` | **每周正式**：暂存草稿 |
| `… json --submit` | 直接提交（政策上不用） |
| `--login-url '…'` | token 链接登录 |
| `--keepalive` | 续 cookie |
| `--dump` | 导出 DOM 诊断 |

## 4. 维护者：打包与本机

```bash
# 在维护仓根目录
bash pack-skill.sh          # → dist/dingtalk-weekly-report-skill-YYYYMMDD.zip
bash install.sh --link      # 技能软链到仓内，改代码即时生效
bash tests/run_mock_test.sh # 仿真表单 e2e（改 fill_form 后必跑）
bash tests/run_smoke.sh     # 打包/安装/附件/仿真冒烟（可选）
```

## 5. 常见问题

| 现象 | 处理 |
|------|------|
| Codex 找不到 skill | 确认 `~/.codex/skills/dingtalk-weekly-report/SKILL.md`；重跑 `install.sh --force` |
| `extract_week` 拒绝写 | json 已存在；先备份再删或改文件名 |
| 会话已失效 | 重新内部二维码 → `--login-url` |
| 填表失败 | 看 `$WORK/output/shots/99-error.png`；对照 FIELDS.md |
| 共享机拒跑 | `$WORK` / `~/.config/dtwr` 属主必须是当前用户 |
| Windows 路径 | 优先 PowerShell 脚本；或 WSL 走 bash 路径 |

## 6. 安全与合规

- zip **仅限公司内部分发**（含表单结构）。  
- 只落草稿，**人在钉钉提交**。  
- 不使用他人 `$WORK` 或登录态。  
- `state.json`、auth 链接等同凭证。
