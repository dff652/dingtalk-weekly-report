# 变更记录

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循
[语义化版本](https://semver.org/lang/zh-CN/)。1.0.0 之前，次版本号的变化即可能带来
不兼容的行为改变。

版本号的**单一事实源**是 `skills/dingtalk-weekly-report/VERSION`；本文件最新的已发布条目
必须与它一致（`tests/test_version.py` 守住这一点）。

## [Unreleased]

## [0.4.1] - 2026-08-03

### 修复

- **修复子表超过 10 行时填表失败**：氚云子表默认每页 10 行，第 11 行一点「新增」就翻到
  第 2 页，可见行数反而变少，被误判成「新增没生效」而中止（真机 12 行周报踩中：
  5 工作日 × 会议/开发 2 行 + 周末加班 2 行）。现在填行前先把子表每页条数调大到能装下
  本周所有行（编辑既有草稿时以分页「共N条」为准），无分页控件的表单保持 no-op；
  调整不生效或行数超过最大每页选项时 fail-loud。mock 表单同步仿真分页与每页条数切换
  （新增后跳到最后一页，复刻真机行为），`run_mock_test.sh` 改用 12 行 fixture 常态回归
  （5 行 fixture 仍由 test_core/smoke 使用）；负例已复现与真机一致的报错后修复转绿。
- **修复 `--login-web` 扫码成功后仍停在“等待扫码”（Issue #3）**：首次引导现在会先询问
  `form_texts.report_title`，缺少正向标识时在打开二维码前 fail-loud，不再无效等待 300 秒；
  扫码页与独立目标页共用同一 Playwright context，后者主动访问 `form_url`，即使 OAuth
  落到工作台也能确认登录。只有目标页出现用户确认过的可见标题才保存 `state.json`；
  不使用 URL 或 Cookie 变化猜测成功。`127.0.0.1` 状态页仍只展示二维码和状态，不接收凭证。
  2026-07-30 已完成真实扫码验收：页面显示成功、`state.json` 以 `0600` 保存，随后
  `--keepalive` 返回会话有效。

### 改进

- **Skill 升级不再被误解为重装运行环境**：安装提示和用户指南明确区分 Skill 代码更新与
  `$WORK/.venv`；正常升级无需重跑 bootstrap。bootstrap 新增 `--diagnose` / `-Diagnose`
  无安装体检，健康环境直接复用现有 venv 与 Chromium，只有依赖版本不符、浏览器缓存缺失或
  显式 `--force-venv` 时才进入同步/重建。阶段、耗时、失败阶段及安装器原始输出统一追加到
  私有 `$WORK/output/bootstrap.log`，方便判断慢在 Python 包还是 Chromium。

## [0.4.0] - 2026-07-30

### 新增

- **安全的 GitHub Issue 回执**：新增 `issue-assistance.yml`，只在新 Issue 创建时用短期
  `GITHUB_TOKEN` 回复维护策略；不 checkout、不读取模型 Secret、不响应外部提及，也不改代码、
  建 PR 或关单。Claude API 自动排查方案因独立 Key / 计费和治理成本暂不启用；项目页 SOP
  补充维护者人工启动本地 Codex 的 Issue 排查、实现、验证与外部动作授权流程，并明确
  `查看/评估` 只读、`同意方案/执行` 才授权本地改动，commit / push / 回复 / 关闭分别授权。
- **首次配置主动引导（Issue #1）**：`configure.py --missing [--json]` 将缺项分成“需要用户
  提供”和“需要真实表单发现”，且结构化输出不包含当前私有值；`--guided` 只询问缺失的姓名、
  表单 URL 与项目等基础信息，并允许在字段 ID 尚未发现时分阶段原子保存。
  `fill_form.py --status` 复用同一计划，明确要求 Agent 主动提问；`--from-discovery` 也可先保存
  已由用户确认的候选。完整 `--check` 与正式填表仍严格拒绝不完整配置。
- **`--status` 自检**：秒出、不联网，读当前真实状态回答「我现在该做什么」——配置是否就绪、
  登录态与保活日志的新鲜度、目标周 json 是否存在／有无 TODO、附件是否已生成，最后给出
  编号的下一步清单。**比再写一份文档有用**：文档会漂，自检读的是实际状态。
  保活日志那项专门防「cron 静默失败」复发。
- **不变量测试 `tests/test_invariants.py`**：把「工具没有提交能力」这条对外承诺变成会 FAIL
  的断言（点击不得由提交类字面量驱动、`form_texts` 读取集白名单、配置键不得含提交类词汇）。
  此前这条承诺只靠"代码里恰好没有那条路径"，一次顺手的改动就能不声不响抹掉它。
  已用注入假提交点击的方式验证守卫真的会红，不是空转。

### 文档

- **完成 Issue 固定安全回执的远端验收**：一次性
  [Issue #2](https://github.com/dff652/dingtalk-weekly-report/issues/2) 只收到一条
  `github-actions` 预设评论；对应
  [Actions run](https://github.com/dff652/dingtalk-weekly-report/actions/runs/30521947460)
  成功，自动化未关闭 Issue，且主分支 SHA、分支集合和开放 PR 均无变化。验收结论由维护者
  另行回复后手动关单。
- **记录 `@claude` 未触发原因与安全启用门槛**：本仓只有 CI workflow，未配置
  `issue_comment` 触发器、Claude Action 或 `ANTHROPIC_API_KEY`，文字提及不会连接到本机 AI
  会话。项目页 SOP 补充 GitHub App、Secret、workflow、权限和验证要求；公开仓建议仅维护者或
  `ai-approved` 门控触发。本项目进一步确定“回复与修改分离”：AI 至多在维护者门控后回复
  Issue，不直接修改代码；文档建议经第二次人工批准后由本地固化或创建仅含文档的待审 PR。
- **固化 GitHub 项目页与 README 维护 SOP**：新增端到端流程，覆盖 README / SKILL / docs
  信息分层、SVG 与 Social preview 生产验收、About/Topics/Homepage/Release 的独立授权边界、
  skills.sh 与其他 Hub 的发现/安装核验，以及提交后 CI annotations、外部状态和回滚检查。
  `docs/SOP.md` 与文档索引补入口，避免长期规则继续散落在会话记录中。
- **统一 README 视觉资产规范与回归门禁**：三张 SVG 显式使用跨平台中文/英文/等宽字体栈，
  字重只保留真实存在的 400/700；收深蓝色与 muted 灰，使关键文本对比度不低于 4.5:1。
  新增 `tests/test_readme_assets.py` 固定画布、ARIA、安全特性、许可色板、字体、对比度及
  Social preview PNG 尺寸/体积；维护文档补充长期视觉规范。
- **补齐 GitHub Social preview 交付物**：新增可编辑的
  `assets/readme/social-preview.svg` 与 1280×640 最终上传文件
  `assets/readme/social-preview.png`，沿用 README 的静态视觉系统，展示“工作日志 → 内容人审
  → XLSX → 氚云草稿 → 用户提交”，不含真实租户或个人数据。
- **完成 GitHub README visual refresh**：基于固定的
  `oil-oil/beautify-github-readme@55bdb1c05414cd7a0cf911d02e55ece79777206e`，
  新增纯静态 SVG Hero 与工作流图，并按「价值与边界 → 工作流 → 快速开始 → 完整操作」
  重排内容；保留安装、登录、隐私、历史重写与维护入口。明确不使用真实氚云截图、GIF、
  ImageGen 或未经审查的动态素材。`MAINTAINER.md` 记录实施/验收门禁，以及需独立处理的
  About、Topics、Social preview、Releases，避免把 README 美化误当成完整 GitHub 项目页优化。
- **实施 README / SKILL / docs 分层并确定双 Hub 策略**：根 README 从 245 行收短为
  101 行，只做 GitHub 落地页；`SKILL.md` 从 203 行收短为 163 行，保留 Agent 运行闭包，
  详细操作下沉到随包 `USER_GUIDE.md` / `references/`，维护证据进入根 `docs/`。禁止把安装
  必需信息移出 Skill 目录。分发继续以 GitHub + skills.sh + Releases 为主；skills-hub.ai
  在多文件安装、元数据兼容和隔离 smoke 通过前不公开发布。
- **统一同周旧草稿契约**：Skill 流程、用户指南、输入输出契约、人工验收和回滚说明全部改为
  「默认只编辑状态=草稿且开始日期=目标周周一的既有记录，找不到才新建；不需要先删草稿」。
  同周已有非草稿记录或多条记录时必须停止人工确认，不得用 `--new-record` 绕过唯一性判定；
  `tests/test_invariants.py` 新增防漂移守卫，禁止现行操作文档恢复旧的“先删”说明。
- **`MAINTAINER.md` 新增 P3（氚云 OpenApi）完整评估 + 文档调研结论**，取代原路线图里
  那行光秃秃的待办。调研不需要凭据即可完成，结果直接改变了结论：
  - 原记的两个待验未知**都已解答且是好消息**：`UploadAttachment` 存在（须先建数据再传附件）、
    业务数据带 `Status` / `WorkflowInstanceId`（护栏可在 API 侧复现）；
  - 但挖出 **`CreateBizObject.IsSubmit`**——存草稿与提交是**同一调用的同一参数**，
    `true` 即生效提交；且疑似默认 `true`（fail-open）、文档中类型不一致（Bool vs string）、
    误提交不可逆（记录只能清空不能删）。安全性质会从"结构性不可能"退化为"每次调用都在悬崖边"；
  - 另发现**比密钥更前置的闸**：OpenApi 疑为专业版付费能力，须先确认租户版本；
  - **决定：暂不采用，不排期。** 技术可行，但迁移消掉的是**已经解决了的痛**
    （登录已由 `--login-web` 解、iframe 时序已修并真机验过），引入的是**新的不可逆风险**。
    连"只做读"也暂不做：读路径需要同一套凭据，而那套凭据同时具备提交能力——
    为省一次开浏览器就把它引进 `$WORK`，性价比不成立；
  - 记了**四条重估触发条件**（前端反复碎 / `--login-web` 失效 / 官方明确 `IsSubmit` 语义或
    提供受限凭据 / 需要无人值守）。触发前的正确动作是什么都不做，**包括不要先去问管理员**。
    调研结果全部保留在文档里，重估时不必重查。

- 记录 2026-07-28 首次 `RELEASE ACCEPTANCE PASS`（六步全过）与审计评级
  Critical→Med 的复审结论；并写明「装得上 ≠ 用得起来」的两道坎
  （枚举仍需人工补、DOM 选择器只在一个租户验证过）。
- `PUBLISHING.md` 的「后续发布阻断」两条均已清，改记为现状。
- `TESTING.md` 新增踩坑 19–22（本轮没写功能代码，坑集中在"怎么确认测试真有用"）：
  重复实现已有断言并第三次撞脱敏门禁（**根因是加测试前没先 grep**）、
  裸 `python3` 跑测试静默少跑 27 项且红得像环境问题（**判读要先看 `Ran N` 再看 OK/FAILED**）、
  守"不会发生的事"的测试必须先让它红一次否则可能是空转、
  单一来源 API 文档不足以定契约（`IsSubmit` 类型与默认值跨来源冲突）。
  并记下踩坑 18（cron 静默失败）的修复当天即由新增冗余时段自证。
- `MAINTAINER.md` 调试节新增「独立核对某周到底提交了没」：`--dump-list` 读列主序网格，
  三列（开始日期 / 周总工时 / 状态）对上即可，**状态离开「草稿」即已提交**。
- `SOP.md` 明确 canonical 测试命令走 `$WORK/.venv/bin/python`。

### 修复

- **消除 GitHub Actions Node 20 弃用警告**：CI 中 `actions/checkout` 与
  `actions/setup-python` 升级到官方当前 `v7`，并显式限制默认 token 权限为
  `contents: read`；测试矩阵与 Python 3.12 运行口径不变。
- **正式包版本门禁**：`pack-skill.sh` 现在除检查版本 tag 与工作区外，还要求
  `HEAD == v<VERSION>^{}`；避免旧 tag 仍存在时，较新的干净 HEAD 被错误命名成无 `-dev`
  的正式包。新增临时 Git 仓库回归测试，真实复现「tag 后继续提交」场景。
- `bootstrap.sh` 打印的 keepalive cron 模板把日志路径改为**绝对路径**，并加 15:30 冗余时段。
  相对路径在 cron 里跟着 cwd 走，cwd 一错重定向就失败，而 cron 的 stderr 无人看
  → 保活每天静默失败（本项目已踩，见 TESTING 踩坑 18）。

## [0.3.0] - 2026-07-28

### 文档

- `docs/TESTING.md` 新增踩坑 11–17（登录判据、二维码入口、ticket 绑定、滑块验证码、
  受控上传组件、编辑态日期控件与 detached frame、字段发现要用已生效记录）与本轮真机验收结论。
- `docs/SOP.md` 新增「零真机里程的分支必然带 bug」：一天内七个 bug、六个同一毛病
  （只做动作不做正向确认），并给出两条可迁移规则。
- `references/FIELDS.md` 沉淀四条真机 DOM 事实（列优先渲染、受控上传组件、编辑态日期控件、
  暂存后 frame detach）。

### 新增

- **工时口径 `daily_hours` / `weekly_hours_cap`**（均可选）：`daily_hours` 是**每天合计上限、
  会议含在内**，`extract_week` 据此算开发行 = `daily_hours − 会议工时`（8 − 0.5 = 7.5），
  一天正好 8h、一周 40h。校验按报告自带的 `hours_policy` 快照判上限，超了**阻断**——
  加班要显式确认并调整配置，不能默默多报。SKILL.md 要求生成前先问用户本周有没有加班。
  旧报告没有该快照时不受影响，向后兼容。

- **默认改目标周的既有草稿，不再需要先删旧草稿**。此前 `do_fill` 只会点「新增」，同周再建
  一条就撞「周报唯一性判定」；而实测有的租户**记录删不掉、只能清空内容**，等于把用户堵死。
  现在先找目标周草稿（两道护栏：状态必须「草稿」、开始日期必须等于目标周周一），找到就改它。
  编辑态会先移除已挂附件再上传（避免赌重复上传是替换还是追加）；既有行多于本周行数时
  fail-loud（删行路径未真机验证，不猜）。`--new-record` 可强制新建。

- 「编辑既有草稿」的定位与护栏（`find_editable_draft` / `open_existing_draft`）：同一周重复
  落草稿会撞表单的「周报唯一性判定」，此前只能先人工删旧草稿再新建——那是绕过工具限制的
  权宜之计，不是表单要求。现可直接改草稿。**两道硬护栏缺一不可**：状态必须是「草稿」
  （已生效/进行中/已取消一律不碰），且报工开始日期必须等于目标周周一。
  真机三种情况均验证正确：目标周草稿命中、已生效被拒、不存在的周返回未找到。

- `--login-web`：扫码登录，但二维码显示在**本地网页**（`http://127.0.0.1:8765`）而不是让你去
  翻 `login.png` 文件；页面自动刷新二维码并显示「等待扫码 / 登录成功」实时状态。
  远程开发经 VSCode 端口转发直接打开。**只绑回环地址**；页面只是**显示**工具生成的二维码，
  不收集任何凭证——收集式登录界面等同凭证拦截，本项目不做。

- `--login-sms`：短信验证码登录，**不用扫码、不存任何长期凭证**。扫码要求你能看到无头浏览器
  生成的那张图，而**在自己浏览器打开登录页扫码是无效的**——二维码是钉钉 OAuth 的 ticket，
  绑定在生成并轮询它的那个浏览器实例上。验证码走隐藏输入、非交互终端直接拒绝，
  与 auth 链接同款约束；同样只在正向确认登录后才落盘。
  **注意**：实测维护者租户点「发送验证码」会触发阿里云滑块拼图，短信不会送达；
  本工具**不绕过验证码**，检测到即 fail-loud 提示改用 `--login` 扫码。

### 修复

- **`--login` 生成的 `login.png` 里从来没有二维码**：氚云登录页默认是「密码登录」，扫码入口
  藏在「或」下面那排图标后面，而 `--login` 从不点它。现改为先点开扫码入口
  （`--qr-entry N` 指定第几个图标，默认 1；实跑确认第 1 个即「钉钉扫码登录」）。

- **`--login` 会在用户还没扫码时就报告「登录态已保存」**：判据是「URL 里没有 `login`」，
  而氚云登录页 URL 恰恰不含该字样，于是打开登录页即判定成功，存下一份**未登录**的
  `state.json`。`--login-url` 同源。现改为正向确认——必须看见 `form_texts.report_title`
  才落盘，看不见宁可超时也不写。

- `--dump-list` / `--dump-record` 在登录态过期时**静默产出无效 dump**：它们只用 URL 含不含
  `login`/`entry/auth` 判断，而氚云过期后落到的登录页 URL 不含这两个字样。现抽出
  `assert_logged_in()`，判据改为正向确认页面出现 `form_texts.report_title`，
  与 `--keepalive` 同款，四处共用。

## [0.2.0] - 2026-07-27

### 变更

- **行为变更**：`$WORK` 是 git 仓库时，技能不再自动 `git push`，只 `commit` 并提示你自行推送。
  推送是把周报数据发往远端的外发动作，与「提交由用户亲手点」是同一条原则；这也是外部安全
  审计（Socket）对本技能的扣分项之一。

### 新增
- `fill_form.py` 运行日志落盘到 `$WORK/output/fill_form.log`（逐行时间戳 + 每次运行起始标记，
  失败也入日志）。**URL 落盘前脱敏**（只留 scheme+host），运行头只记文件名不记绝对路径——
  日志会被附到 issue 或发给协助排查的人，表单 URL 带组织租户标识、绝对路径会带出用户名。
- `SKILL.md`「多设备 / 多人」与 `USER_GUIDE.md` 第 5 节：登录态不跨设备拷贝、多端登录可能
  互踢、只在一台设备落草稿、配置搬运不经过聊天，以及扫码与打印链接的真实判据（有没有
  图形界面），取代原先一律「首选扫码」的说法。
- **配置自动发现闭环**：`--dump-record N` 现直接推断 `form_fields` 候选并写出
  `$WORK/output/field-proposal.json`；`configure.py --from-discovery` 逐项确认后写入，
  **绝不自动落盘**。真机实测 10 项中自动定位 8 项、零错误，另 2 项给候选由人二选一。
  原来要手抄十个 DOM id，现在是确认十几个候选。
- `--harvest-enums`：本想展开下拉取枚举全集，实测本表单**孤立点开取不到选项**
  （与 `FIELDS.md` 早已记录的「关联下拉孤立探测无数据」是同一现象），故降级为诊断工具。
  枚举的实用来源改为跨多条历史记录取并集——但那只是**用过的值**，不等于全集，仍需人工补。
- `--dump-record N`：打开列表第 N 条**历史记录**并 dump（只读，不保存）。空白新增表单只有
  控件 id 没有值，按值形状认字段必须看已填记录。氚云列表页标题是 `span.tg-link` 而非
  `<a href>`，无法用 URL 直取，只能点开。
- `--dump-list`：只读 dump **列表页**并列出打开历史记录的候选入口。`--dump` 打的是「新增」
  空白表单，只有控件 id、没有值；要按值形状认字段（日期/工时/长文本各有形态）必须打开
  一条**已填历史记录**，而「怎么点开一条记录」的选择器目前未知——本模式为取证而设。
  不需要任何字段配置，只需登录态。
- `--dump` / `--login` 不再要求完整配置通过校验：`--dump` 只需 `form_texts.add_row` 与
  `start_date_label`。此前它要求字段 id 已配好才肯运行，而找出字段 id 正是它的用途，
  新用户被死锁在门外。
- `references/FIELDS.md` 新增「值长什么样」掩码形状表、可直接复制的**向表单管理员索取**
  模板，以及基于修好的 `--dump` 重写的获取流程。脱敏移除真实值时把形状信息也一并带走了，
  新用户无从判断拿到的值对不对。
- **假期与调休支持**：新增可选配置 `holidays` / `extra_workdays`，应报工作日 =
  (周一~周五 − holidays) ∪ extra_workdays。此前硬编码周一到周五，**国庆/春节周会强迫
  为放假日填工时，调休周六上班则根本不生成该行、直接漏报**。周报 json 增加 `workdays`
  快照供校验使用；旧 json 无该字段时回落周一~周五，向后兼容。不内置年度节假日表、不联网。
- `CONTRIBUTING.md`：装钩子、提交身份必须 noreply、三条硬规则与不接受的改动类型。
- `docs/SOP.md`：开发 / 测试 / 发版 / 部署的流程骨架与三张决策表（改动类型→必跑验证、
  发版检查单、回滚路径），并记录 `npx skills` 无版本 pin 这一已知回滚缺口。
- `SECURITY.md`：信任模型与两条扫描器告警（Snyk W012 MEDIUM / Socket LOW Anomaly）的处置说明，
  含数据边界表与「你不该装它的情况」。
- 发行审计门禁改为与已复审基线比对（`tests/fixtures/expected-audit-row.txt`），
  取代原先在整个安装日志里 grep `Critical Risk` 的做法。
- `references/CONTRACT.md` 新增「工作日志的格式契约」：`PROGRESS_REPORT.md` 的标题形态此前
  只存在于 `extract_week.py` 的正则里，格式写不对不会报错、只会得到一整周 TODO。现补上
  最小示例与三条硬约束（日期标题形态、工作日必须全覆盖、拒绝覆盖已有 json）。

## [0.1.0] - 2026-07-26

首个带版本号的发行。此前的安装没有版本标识，因此本条同时说明**从无版本号的旧安装升级上来时
会遇到的行为变化**。

### 新增

- 附件上传完成校验：上传后必须拿到证据才继续——文件控件真的持有文件，且页面上出现附件名
  （与人工在 `20-filled-review.png` 上核对「附件已挂」是同一判据）。
- `hooks/pre-push` 本地门禁与 GitHub Actions CI（单元测试 / 仿真表单 e2e / 历史脱敏扫描）。
- `tests/scan_history.py`：扫描整个 Git 历史（而不只是工作树）里的敏感形状与提交身份，
  脱敏模式复用 `tests/test_public_tree.py` 作单一事实源。
- 全部分发脚本加 `SPDX-License-Identifier` 标识。

### 变更

- **`form_fields.attach` 成为唯一可留空的配置项**：留空表示本表单没有附件项，填表时整步跳过。
  此前它是必填项，等于让没有附件字段的组织无法使用本工具。放宽不影响既有配置。
- **⚠️ 行为变化**：附件上传后若在 30 秒内无法确认完成，现在会**中止并报错**，而不再像过去那样
  固定等待 4 秒就继续。过去在网络慢时可能存下缺附件的草稿；现在宁可中止也不落不完整的草稿。
  失败时看 `output/shots/99-error.png`。
- 附件是否必需**由配置推导**，不提供 `--no-attach` 之类的命令行开关——那会成为
  「附件生成失败就加参数绕过」的逃生口。表单要求附件时跳过附件就是提交了不合规的周报。

### 修复

- `extract_week.py` 在配置缺少可选项 `dept_goal` 时抛出裸 `KeyError`，而不是本项目统一的
  fail-loud 提示。
- 登录态路径不再无视 `XDG_CONFIG_HOME`：此前 `workdir()` 与 `bootstrap.sh` 都尊重该变量，
  而 `fill_form.py` 硬编码 `~/.config`，在设置了该变量的系统上会把工作目录指针和登录态
  分散到两个目录。两者现在共用 `dtwr_common.dtwr_config_dir()`。

### 安全

- **Git 历史已于 2026-07-25 重建为单一提交。** 早期提交包含真实个人配置、周报内容与组织表单
  标识，36 个提交中 35 个命中，无法通过部分重写可靠清除。此日期之前的克隆全部作废，请重新
  克隆。未发现凭证泄露：登录 token、`state.json`、cookie 与截图从未进入版本库。
  处置全过程见 [docs/PUBLISHING.md](docs/PUBLISHING.md)。
- 提交身份统一为 GitHub noreply 地址，真实邮箱不再出现在公开历史中。

[Unreleased]: https://github.com/dff652/dingtalk-weekly-report/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/dff652/dingtalk-weekly-report/releases/tag/v0.3.0
[0.2.0]: https://github.com/dff652/dingtalk-weekly-report/releases/tag/v0.2.0
[0.1.0]: https://github.com/dff652/dingtalk-weekly-report/releases/tag/v0.1.0
