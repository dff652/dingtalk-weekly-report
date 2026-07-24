---
name: dingtalk-weekly-report
description: 每周钉钉「报工周报」半自动流程——从个人工作日志生成内容草稿（人审）→ 附件 xlsx → 氚云表单落草稿 → 人工在钉钉核对提交。周五定稿本周或周一 17:00 前补交上周时使用；可带周一日期参数指定周（如 /dingtalk-weekly-report 2026-07-20）。自包含技能包（脚本随包分发），首次使用自动引导安装。
---

# 钉钉报工周报半自动流程

**自包含技能包**：本目录携带全部执行资源，无需 clone 仓库——
`USER_GUIDE.md`（给人看的安装与每周使用说明）、
`install.sh` / `install.ps1`（装 Claude `~/.claude/skills/`、Codex `~/.codex/skills/`、可选 `~/.agents/skills/`；
`--link` / `--force`；清理旧名 `weekly-report` 与过时 Codex prompts 桥接）、
`bootstrap.sh` / `bootstrap.ps1`（建 `$WORK`、uv venv、playwright+Chromium、config、`~/.config/dtwr/root`）、
`requirements-runtime.txt`（锁定 Playwright 运行时版本）、
`scripts/`（extract_week / gen_attachment / print_form_rows / fill_form / xlsxlite）、
`references/FIELDS.md`（表单字段编码/枚举合法值/DOM 坑，事实源）、
`references/CONTRACT.md`（输入、缺失处理、输出与失败契约）、
`assets/config.example.json`（个人配置模板）。分发 zip 根目录即本目录（平铺）。

两个路径变量贯穿全文（**均在运行时解析，本文件不含任何具体用户的路径**）：

- `$SKILL` = 本 SKILL.md 所在目录（只读技能代码；通常即 `~/.claude/skills/dingtalk-weekly-report`）。
- `$WORK` = 每用户工作目录（运行态：config.json / weeks/ / output/ / .venv/；登录态在 `~/.config/dtwr/`）。
  与 `$SKILL` 分离；默认建议 `~/weekly-report-data`，**不是**代码目录。

## 第 0 步：解析 $WORK（严禁跳过，严禁硬编码）

1. 读 `~/.config/dtwr/root`（一行绝对路径）→ 目录存在且含 `config.json` 则为 `$WORK`；
2. 否则 → 走「首次安装」（见文末），装完回到这里。

**安全闸（共享机必查）**：`$WORK` 与 `~/.config/dtwr/` 的属主必须是当前用户
（`stat -c %U` == `whoami`），否则**立即终止并告知用户**——严禁使用他人的工作目录、
config、登录态；那等于以他人身份向 HR 填报。本 skill 全程只读写 `$SKILL`（只读）、
当前用户 `$HOME` 与 `$WORK` 之内的路径。

以下命令一律 `cd $WORK` 后执行，脚本用 `$WORK/.venv/bin/python "$SKILL/scripts/<脚本>"` 调用
（extract_week/gen_attachment/print_form_rows 无三方依赖，可直接 `python3`）；
git 操作（若 $WORK 配了仓库）必须 `git -C $WORK`。每用户差异（姓名/项目/负责人/内容源路径/
会议模式）全部来自 `$WORK/config.json`，skill 里不出现具体值。

## 三条铁律（任何步骤不得违反）

1. **只落草稿，永不提交**：只用 `--draft --confirmed`；脚本不提供提交能力。提交由用户在钉钉里核对后亲手点。
2. **内容必须人审**：week_report json 生成/修改后，先把逐日内容摘要展示给用户确认，再进入填表。
3. **防重复**：落草稿前提醒用户检查/删除同一周的旧草稿（同周多条记录会撞「周报唯一性判定」；删除由用户在钉钉做）。

`--confirmed` 是操作清单声明，不是人审证据或安全授权机制；agent 仍必须真实展示摘要并获得用户确认。

## 流程

### 1) 确定目标周

- 用户带参数（周一日期）→ 用参数；无参数：今天是周一 → 上一周（补交，注意 17:00 截止）；否则 → 当前周。
- 复述目标周区间（周一~周日）请用户确认。

### 2) 前置检查：内容源

- 内容源路径 = `config.json` 的 `progress_report`（个人工作日志）。存在 → 检查其是否已覆盖目标周
  （无覆盖则**先更新日志再回来**，fail-loud，不拿 git log 凑数）。
- 该键为空（用户没有日志纪律）→ 退化为访谈式：按工作日逐天问用户做了什么，直接写 json。
  纯 CLI 可运行 `extract_week.py` 生成 TODO 骨架；TODO 未补齐时附件和填表都会被阻断。
- 已配置路径但文件不存在 → 阻断并要求修正路径；不把配置错误静默当成“无日志”。

### 3) 生成/更新周报 json（人审锚点）

- `$WORK/weeks/week_report_YYYYMMDD.json` 不存在 → `python3 "$SKILL/scripts/extract_week.py" <周一日期>`。
- 润色逐日 `content`：
  - 每工作日两行起：会议行 + 开发主行，具体会议名称/工时/状态取 `config.json` 的
    `standup`/`monday_meeting` 与默认值键。
  - **content ≤200 字**（表单硬上限）；写给 HR 看的措辞，量化结果，不堆内部代号。
  - 休假日：状态「休假」8h、项目类型「公司和部门运营活动」、无项目无内容；正常周末不报。
  - `summary`/`next_week`：定稿日填实；周中测试可标「进行中，周五定稿」。
- 枚举合法值/双项目字段（表单下拉项 ≠ 附件关联项目）见 `$SKILL/references/FIELDS.md` 与 config。
- **把逐日内容+工时合计摘要发给用户，得到确认再继续。**

### 4) 附件

`python3 "$SKILL/scripts/gen_attachment.py" weeks/week_report_YYYYMMDD.json`

### 5) 登录态

- `.venv/bin/python "$SKILL/scripts/fill_form.py" --keepalive` 验会话（若装了 cron 保活通常直接过）。
- 报「会话已失效」→ 请用户：钉钉报工周报列表 →「打印二维码 → 打印内部二维码」→ 手机钉钉扫 →
  把浏览器里 `h3yun.com/entry/auth?token=…` 整条链接发来 →
  `.venv/bin/python "$SKILL/scripts/fill_form.py" --login-url '<链接>'`。
  链接 48h 有效、等价临时登录凭证：用完提醒勿转发；**勿写入任何文件/git**。

### 6) 落草稿

- 先提醒用户删同周旧草稿（如有），得到确认。
- `.venv/bin/python "$SKILL/scripts/fill_form.py" weeks/week_report_YYYYMMDD.json --draft --confirmed`
- 展示 `$WORK/output/shots/20-filled-review.png` 与 `30-saved.png`，指出核对点：行数、周总工时、
  附件已挂、项目/负责人带出。

### 7) 收尾

- 提醒用户：钉钉里打开草稿核对 → 点「提交」（周一 17:00 截止线）。
- 若 `$WORK` 是 git 仓库：`git -C $WORK add weeks/ && git -C $WORK commit && git -C $WORK push`。
  除非用户明确要求，不添加模型专属 `Co-Authored-By`。

## 首次安装（$WORK 不存在时）

**前提**：技能已装到 agent 目录，故 `$SKILL` 可读。常见装法（仓库 README）：
`npx skills add https://github.com/dff652/dingtalk-weekly-report -s dingtalk-weekly-report -a claude-code -a codex -g -y`，
或 zip/`install.sh`，或维护仓 `--link`。若用户**只给了仓库 URL** 且本机尚无 skill，先按 README
「只给仓库 URL 时：复制给 AI」完成安装，再继续本步。

本步只建运行态（`$WORK`），不改技能包。

1. **推荐一键 bootstrap**（优先于逐步手敲；完整安装说明见同目录 `USER_GUIDE.md`）：
   - Linux/macOS / WSL: `bash "$SKILL/bootstrap.sh"`（或 `--work ~/weekly-report-data`）
   - Windows: `powershell -File "$SKILL/bootstrap.ps1"`
   会建 `$WORK`、`.venv`、playwright+Chromium、`config.json` 模板、`~/.config/dtwr/root`。
2. 若未跑 bootstrap：问用户工作目录（默认 `~/weekly-report-data`，只存个人数据，**不是代码目录**），
   再按旧步骤 mkdir + `uv venv` + playwright + 拷 config + 写 dtwr root。
3. 访谈补全 `config.json`：姓名、form_project（表单下拉**完整原文**）、attach_project、
   progress_report（没有则留空走访谈式）、会议/工时默认值。
4. 登录：走第 5 步「会话已失效」分支；可选保活：
   - Linux/mac: cron `30 9 * * * cd <WORK> && .venv/bin/python <SKILL>/scripts/fill_form.py --keepalive >> output/keepalive.log 2>&1`
   - Windows: 计划任务调用同一命令（路径用 `Scripts\python.exe`）。

**技能升级**（保留 `$WORK`/config/登录态）：
- 生态：`npx skills update dingtalk-weekly-report -g -y`（必要时重做 Codex 补链）
- zip / 本地：`bash install.sh --force`（Win: `.\install.ps1 -Force`）
环境损坏：`bash bootstrap.sh --force-venv`。

## 出错处理

- 填表失败：看 `$WORK/output/shots/99-error.png`，对照 `$SKILL/references/FIELDS.md`
  「P2 真机联调发现」修 `scripts/fill_form.py` 选择器（技能包持有者改后应跑维护仓的仿真回归）。
- 表单结构疑变：`.venv/bin/python "$SKILL/scripts/fill_form.py" --dump` 拿新 DOM。
- 环境损坏：按「首次安装」第 2 步用 uv 重建。
