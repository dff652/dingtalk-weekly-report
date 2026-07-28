---
name: dingtalk-weekly-report
description: 每周钉钉「报工周报」半自动流程——从个人工作日志生成内容草稿（人审）→ 附件 xlsx → 配置驱动的氚云表单落草稿 → 人工在钉钉核对提交。定稿本周或补交上周时使用；可带周一日期参数指定周。自包含技能包，首次使用自动引导安装与私有配置。
---

# 钉钉报工周报半自动流程

**自包含技能包**：本目录携带全部执行资源，无需 clone 仓库——
`USER_GUIDE.md`（给人看的安装与每周使用说明）、
`install.sh` / `install.ps1`（装 Claude `~/.claude/skills/`、Codex `~/.codex/skills/`、可选 `~/.agents/skills/`；
`--link` / `--force`；清理旧名 `weekly-report` 与过时 Codex prompts 桥接）、
`bootstrap.sh` / `bootstrap.ps1`（建 `$WORK`、uv venv、playwright+Chromium、config、`~/.config/dtwr/root`）、
`requirements-runtime.txt`（锁定 Playwright 运行时版本）、
`scripts/`（configure / extract_week / gen_attachment / print_form_rows / fill_form / xlsxlite）、
`references/FIELDS.md`（私有配置键、字段获取方法与通用 DOM 约束）、
`references/CONTRACT.md`（输入、缺失处理、输出与失败契约）、
`assets/config.example.json`（无组织数据的个人配置模板）、`LICENSE`（Apache-2.0）。
分发 zip 根目录即本目录（平铺）。

两个路径变量贯穿全文（**均在运行时解析，本文件不含任何具体用户的路径**）：

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
- 报「会话已失效」→ 首选运行 `.venv/bin/python "$SKILL/scripts/fill_form.py" --login`，
  请用户用手机钉钉扫描 `$WORK/output/shots/login.png`。
- 若必须使用一次性 auth 链接：请用户**本人在本机交互终端**运行
  `.venv/bin/python "$SKILL/scripts/fill_form.py" --login-url`，再按隐藏提示粘贴。
  Agent 不得索要、接收、回显或代输链接，也不得把链接放入命令参数、聊天、文件或 git。
  该链接 48h 有效，等价临时登录凭证。

### 6) 落草稿

- 先提醒用户删同周旧草稿（如有），得到确认。
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
3. 访谈取得姓名、form_project（表单下拉**完整原文**）、attach_project、
   progress_report（没有则留空走访谈式）、会议/工时默认值，以及用户或表单管理员确认的
   `vocabulary`、`form_fields`、`form_texts`；不得从公开仓库猜测任何组织字段。再运行
   `python3 "$SKILL/scripts/configure.py"` 交互填写；Agent 已取得明确值时可使用重复的
   `--set KEY=VALUE --yes`。脚本在完整校验通过后才原子写入，并将旧配置保存为
   `$WORK/config.json.bak`；一次性 entry/auth 登录链接不得作为 `form_url`。
4. 登录：走第 5 步「会话已失效」分支；一次性 auth 链接只能由用户本人在交互终端隐藏输入；
   可选保活：
   - Linux/mac: cron `30 9 * * * cd <WORK> && .venv/bin/python <SKILL>/scripts/fill_form.py --keepalive >> output/keepalive.log 2>&1`
   - Windows: 计划任务调用同一命令（路径用 `Scripts\python.exe`）。

**技能升级**（保留 `$WORK`/config/登录态）：
- 生态：`npx skills update dingtalk-weekly-report -g -y`（必要时重做 Codex 补链）
- zip / 本地：`bash install.sh --force`（Win: `.\install.ps1 -Force`）
环境损坏：`bash bootstrap.sh --force-venv`。
从 config v1 升级时重新运行配置向导，补齐组织私有的 `vocabulary`、`form_fields`、
`form_texts`；向导会写入 `config_version=2`。旧周报需重新生成或由用户在私有 `$WORK`
中补入 `schema_version=2` 与当前 `vocabulary`，不得把真实值提交到技能仓库。

**查看/重新配置**（不需重跑 bootstrap）：
- `python3 "$SKILL/scripts/configure.py" --show`：查看；
- `python3 "$SKILL/scripts/configure.py" --check`：校验；
- `python3 "$SKILL/scripts/configure.py"`：交互更新。回车保留原值，`-` 清空可选项。

## 多设备 / 多人

同一个人在多台设备上使用，或把技能分发给同事时，以下四条必须遵守：

1. **登录态不跨设备复制。** `~/.config/dtwr/state.json` 是**活凭证**，等同于一份已登录会话。
   每台设备各自登录，不要拷贝该文件，也不要把它放进任何同步盘或仓库。
2. **多端登录可能互相踢下线。** 临近提交截止时，不要在别的设备上重新登录主力设备的账号，
   否则可能在最需要时把自己锁在门外。
3. **只在一台设备上落草稿。** 同一周落多份草稿会撞表单的「周报唯一性判定」。非主力设备做
   验证时**跑到预览为止**（不加 `--draft`），或事后由用户在钉钉删掉多余草稿。
4. **配置搬运不经过聊天。** `$WORK/config.json` 含组织私有值，搬到新设备靠拷文件或重跑
   `configure.py`；**不得**把这些值粘贴进 AI 会话、聊天或 issue。

`--login`（扫码）与 `--login-url`（打印链接）**两条都可用，按设备条件选**：

- 设备能看到 `output/shots/login.png` → 扫码更省事，且不产生可复制的秘密；
- 无图形界面 / 远程机器 → 用 `--login-url`，由用户本人在该机交互终端隐藏输入。

**唯一硬规矩：不要把同一条 auth 链接在设备之间转发。** 它 48h 内等效登录凭证，转发会让它
留在剪贴板、shell history 和传输通道里；换设备就重新获取一条。

## 出错处理

- 填表失败：看 `$WORK/output/shots/99-error.png`，对照 `$SKILL/references/FIELDS.md`
  检查私有字段配置与通用 DOM 约束；确认表单结构确已变化后再修 `scripts/fill_form.py`
  选择器（技能包持有者改后应跑维护仓的仿真回归）。
- 表单结构疑变：`.venv/bin/python "$SKILL/scripts/fill_form.py" --dump` 拿新 DOM。
- 环境损坏：按「首次安装」第 2 步用 uv 重建。
