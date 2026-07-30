---
name: dingtalk-weekly-report
description: 每周钉钉「报工周报」半自动流程——从个人工作日志生成内容草稿（人审）→ 附件 xlsx → 配置驱动的氚云表单落草稿 → 人工在钉钉核对提交。定稿本周或补交上周时使用；可带周一日期参数指定周。自包含技能包，首次使用自动引导安装与私有配置。
---

# 钉钉报工周报半自动流程

这是一个**自包含的多文件 Skill**，安装目录已携带脚本、bootstrap、模板、用户指南和 references，
无需 clone 仓库。安装、升级、纯 CLI 与 FAQ 见同目录 `USER_GUIDE.md`；输入输出契约见
`references/CONTRACT.md`，字段与 DOM 约束见 `references/FIELDS.md`。

两个路径变量贯穿流程，均在运行时解析，本文件不含具体用户路径：

- `$SKILL` = 本 SKILL.md 所在目录（只读技能代码；通常即 `~/.claude/skills/dingtalk-weekly-report`）。
- `$WORK` = 每用户私有工作目录（运行态：config.json / weeks/ / output/ / .venv/；登录态在 `~/.config/dtwr/`）。
  与 `$SKILL` 分离；默认建议 `~/weekly-report-data`，**不是**代码目录。

## AI 工具显式调用

- Claude Code：`/dingtalk-weekly-report`，可附周一日期。
- Codex：`$dingtalk-weekly-report`，可附周一日期；也可先运行 `/skills` 选择。

不要只依赖自然语言隐式匹配来判断 skill 已触发。

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
3. **防重复**：同周多条记录会撞「周报唯一性判定」。工具**默认改目标周的既有草稿**（`find_editable_draft` 两道护栏：状态必须是「草稿」、报工开始日期必须等于目标周周一），所以**不需要先删旧草稿**——某些租户的记录本来也删不掉，只能清空内容。确需另建一条时用 `--new-record`。

`--confirmed` 是操作清单声明，不是人审证据或安全授权机制；agent 仍必须真实展示摘要并获得用户确认。

## 流程

### 0.5) 先自检（推荐，秒出）

`.venv/bin/python "$SKILL/scripts/fill_form.py" --status`

读真实状态给出下一步：配置、登录态与保活日志新鲜度、本周 json 与附件。
遇到任何"不知道该做什么"或用户报错时，**先跑它再判断**，不要凭猜测执行后续步骤。

若输出「需要用户提供」，Agent 必须主动逐项询问列出的姓名、表单 URL、项目和
`form_texts.report_title`（用户看到的列表页周报标题）等信息，
不得只让用户自行编辑 `config.json`。也可先运行
`python3 "$SKILL/scripts/configure.py" --missing --json` 取得不含当前私有值的结构化清单；
用户明确回答后，用重复的 `--set KEY=VALUE` 配合 `--guided --yes` 分阶段保存。用户不愿在聊天
提供时，引导其本人在本机终端运行 `configure.py --guided`。字段 ID、枚举和按钮文字走真实表单
发现与逐项确认，不向用户索要猜测值；一次性 entry/auth 链接始终不得询问或接收。

### 1) 确定目标周

- 用户带参数（周一日期）→ 用参数；无参数：今天是周一 → 上一周；否则 → 当前周。
- 复述目标周区间（周一~周日）请用户确认。
- 若 `config.json` 的 `submission_reminder` 非空，一并复述；不得硬编码组织截止时间。

### 2) 前置检查：内容源

- 内容源 = `config.json` 的 `progress_report`：可指向个人工作日志文件，或项目目录。项目目录
  **只**解析 `<项目>/docs/report/PROGRESS_REPORT.md`，不得扫描仓库或读取 git log。解析后检查
  文档是否覆盖目标周；未覆盖则询问用户补齐缺失日期，不把已有证据扩写成未发生的事实。
- 该键为空（用户没有日志纪律）→ 退化为访谈式：按工作日逐天问用户做了什么，直接写 json。
  纯 CLI 可运行 `extract_week.py` 生成 TODO 骨架；TODO 未补齐时附件和填表都会被阻断。
- 已配置路径不存在，或项目目录缺标准文档 → 阻断并要求修正路径；不把配置错误静默当成“无日志”。

### 3) 生成/更新周报 json（人审锚点）

- `$WORK/weeks/week_report_YYYYMMDD.json` 不存在 → `python3 "$SKILL/scripts/extract_week.py" <周一日期>`。
- **生成前先问用户「本周有没有加班」**；没有就按默认口径走，不要自作主张多报或少报。
- **会议工时含在每日总工时内**：配了 `daily_hours` 时开发行 = `daily_hours − 会议工时`
  （如 8 − 0.5 = 7.5），一天合计正好 `daily_hours`。`weekly_hours_cap` 是每周硬上限。
  超限时校验会阻断——确有加班要用户显式确认并调整配置，不能默默多报。
- 每行工时必须 `>0` 且 `≤24`，同一天所有行合计不得超过 24h。用户给出 25h、缺日期、
  非法枚举或含糊信息时，必须停止并指出具体问题，询问用户修正；不得把 25h 猜成 2.5h、
  拆到其他日期或静默改值，也不得用 git log 补写。
- 润色逐日 `content`：
  - 每工作日两行起：会议行 + 开发主行，具体会议名称/工时/状态取 `config.json` 的
    `standup`/`monday_meeting` 与默认值键。
  - **content ≤200 字**（表单硬上限）；写给 HR 看的措辞，量化结果，不堆内部代号。
  - 休假日：使用 `vocabulary.leave_status`、`leave_hours` 与
    `vocabulary.operations_project_type`；正常周末不报。
  - `summary`/`next_week`：定稿日填实；周中测试可标「进行中，周五定稿」。
- 枚举合法值/双项目字段（表单下拉项 ≠ 附件关联项目）见 `$SKILL/references/FIELDS.md` 与 config。
- 修正后重新运行共享校验，并**把逐日内容+工时合计摘要发给用户，得到确认再继续。**

### 4) 附件

`python3 "$SKILL/scripts/gen_attachment.py" weeks/week_report_YYYYMMDD.json`

附件是否必需由 `config.json` 的 `form_fields.attach` 推导：填了则必须生成并成功上传
（`fill_form.py` 会等到页面出现附件名才继续，等不到就中止，不落缺附件的草稿）；
留空表示本表单没有附件项，本步跳过。**不存在"这周不传附件"的选项**——
表单要求附件时跳过就是交了不合规的周报。

### 5) 登录态

- `.venv/bin/python "$SKILL/scripts/fill_form.py" --keepalive` 验会话（若装了 cron 保活通常直接过）。
- 报「会话已失效」→ 有本地浏览器或 VS Code 端口转发时首选运行
  `.venv/bin/python "$SKILL/scripts/fill_form.py" --login-web`，打开终端给出的
  `http://127.0.0.1:8765` 扫码；只能看文件时改用 `--login`，扫描
  `$WORK/output/shots/login.png`。回环网页只展示二维码/状态，登录态进入生成二维码的
  Playwright context，不把 Cookie 交给网页。
- 若必须使用一次性 auth 链接：请用户**本人在本机交互终端**运行
  `.venv/bin/python "$SKILL/scripts/fill_form.py" --login-url`，再按隐藏提示粘贴。
  Agent 不得索要、接收、回显或代输链接，也不得把链接放入命令参数、聊天、文件或 git。
  该链接 48h 有效，等价临时登录凭证。

### 6) 落草稿

- 先让用户检查同周记录；**不要先删草稿**。命令默认只编辑「状态=草稿 且 报工开始日期=
  目标周周一」的既有记录，找不到可编辑草稿时才新建。若同周已有非草稿记录或多条记录，
  停止并由用户先在钉钉确认真实状态；不要用 `--new-record` 绕过唯一性判定。
- `.venv/bin/python "$SKILL/scripts/fill_form.py" weeks/week_report_YYYYMMDD.json --draft --confirmed`
- 展示 `$WORK/output/shots/20-filled-review.png` 与 `30-saved.png`，指出核对点：行数、周总工时、
  附件已挂、项目/负责人带出。

### 7) 收尾

- 提醒用户：钉钉里打开草稿核对 → 点「提交」；若配置了 `submission_reminder`，同时展示。
- 若 `$WORK` 是 git 仓库：`git -C $WORK add weeks/ && git -C $WORK commit`，然后**告诉用户可以
  自行 push**。**不得代替用户执行 `git push`**——推送是把用户的周报数据发往远端，属于外发动作，
  与"提交由用户亲手点"是同一条原则；自动 push 也是外部安全审计对本技能的扣分项之一。
  除非用户明确要求，不添加模型专属 `Co-Authored-By`。

## 首次安装（$WORK 不存在时）

**前提**：Skill 已装到 Agent 目录，`$SKILL` 可读。本节只建立当前用户的运行态 `$WORK`，
不修改技能包；完整安装方式见同目录 `USER_GUIDE.md`。

1. **推荐一键 bootstrap**（优先于逐步手敲；完整安装说明见同目录 `USER_GUIDE.md`）：
   - Linux/macOS / WSL: `bash "$SKILL/bootstrap.sh"`（或 `--work ~/weekly-report-data`）
   - Windows: `powershell -File "$SKILL/bootstrap.ps1"`
   会建 `$WORK`、`.venv`、playwright+Chromium、`config.json` 模板、`~/.config/dtwr/root`。
   失败时展示原始错误并查 `USER_GUIDE.md`，不得自行拼一套简化环境。
2. 运行 `configure.py --missing --json`。对 `needs_user` 主动访谈，至少取得姓名、form_url、
   form_project（表单下拉**完整原文**）、attach_project 与
   `form_texts.report_title`（列表页周报标题准确原文）；已取得明确值时用
   `configure.py --guided --set KEY=VALUE ... --yes` 分阶段原子保存，旧配置备份为
   `$WORK/config.json.bak`。用户希望本地私密输入时改由其运行 `configure.py --guided`。
3. 登录：走第 5 步「会话已失效」分支；一次性 auth 链接只能由用户本人在交互终端隐藏输入。
4. 登录后按 `references/FIELDS.md` 运行 `--dump-record N`，再用
   `configure.py --from-discovery` 逐项确认字段候选；枚举与按钮文字也必须来自本人或管理员
   确认，不得从公开仓库猜；Agent 可继续用 `configure.py --guided --set KEY=VALUE ... --yes`
   分阶段保存这些已确认值。最后运行 `configure.py --check`，完整校验通过前不得生成或填写周报。
   保活、升级、环境重建和重新配置命令见 `USER_GUIDE.md`，不要在未核对私有路径时凭记忆拼命令。

## 多设备 / 多人

- 登录态不跨设备复制：`~/.config/dtwr/state.json` 是活凭证，每台设备各自登录。
- 只在一台设备落草稿；其他设备最多跑到预览，避免撞同周唯一性判定。
- `$WORK/config.json` 含组织私有值，只能拷文件或重跑向导，不得粘贴到聊天或 issue。
- 能开本地页面或端口转发时用 `--login-web`；只能看截图时用 `--login`；两者都不可用时，
  远程机器由用户本人运行 `--login-url` 并隐藏输入。
- auth 链接不得跨设备转发；换设备就重新获取。多端登录和迁移细节见 `USER_GUIDE.md`。

## 出错处理

- 填表失败：看 `$WORK/output/shots/99-error.png`，对照 `$SKILL/references/FIELDS.md`
  检查私有字段配置与通用 DOM 约束；确认表单结构确已变化后再修 `scripts/fill_form.py`
  选择器（技能包持有者改后应跑维护仓的仿真回归）。
- 表单结构疑变：`.venv/bin/python "$SKILL/scripts/fill_form.py" --dump` 拿新 DOM。
- 环境损坏：按 `USER_GUIDE.md` 用对应平台的 bootstrap 强制重建 venv
  （Linux/macOS/WSL：`bash "$SKILL/bootstrap.sh" --force-venv`；
  Windows：`powershell -File "$SKILL/bootstrap.ps1" -ForceVenv`）。
