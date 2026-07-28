# 设计与实现评审（2026-07-25）

评审范围：全仓约 3.9k 行（代码 1.5k / 文档 2.4k），含技能包脚本、安装与打包脚本、测试与文档。
许可证选择的决策与理由见 [PUBLISHING.md「许可证选择」](PUBLISHING.md#许可证选择apache-20-vs-mit)。

评审时实跑的验证：

| 验证 | 结果 |
|---|---|
| `python -m unittest discover -s tests` | 48 项全过 |
| `bash tests/run_mock_test.sh` | `MOCK e2e PASS: 5 行全部字段断言通过` |
| 历史脱敏扫描（全部提交对象） | **命中**，见下文「发布阻断」 |

## 一、结论

工程水平已达到可对外发行的产品级，不是个人自动化脚本的量级。最难的一步——把绑死在特定组织
HR 表单上的内部工具做成可开源的通用技能包——已经解决，且是在代码里强制的，不靠文档自觉。

**没有需要返工的架构错误。** 待办全部是可逐条修掉的具体缺陷，加一项与代码无关的发布阻断。

## 二、已确认成立的设计（后续改动不得破坏）

本节是不变量清单，不是评语。改动触碰到其中任何一条时，应先确认替代方案同样成立。

1. **`$SKILL`（只读代码）/ `$WORK`（每用户运行态）分离，代码强制**。`dtwr_common.py::workdir()`
   检测到目录含 `SKILL.md` 即判定源码仓并拒绝；`bootstrap.sh` 双向拒绝两者互相嵌套。
   这一条决定项目能否开源。
2. **组织私有面 100% 配置化**。表单 URL、10 个 DOM id、按钮文本、下拉枚举、项目原文全部外置到
   私有 `config.json`，公开仓只留键名（`dtwr_fields.py`）。
3. **脱敏是回归测试，不是发布前人肉 review**。`tests/test_public_tree.py` 用正则扫全树拦字段 id
   形状、内部组件 id、租户查询参数与绝对 home 路径。新增敏感形状时加进 `SENSITIVE_PATTERNS`。
4. **安全边界在确定性层，不在 prompt 里**。`--draft` 强制配 `--confirmed`（argparse 互斥校验）、
   脚本无提交能力、`form_texts.save_draft` 指向提交按钮会被 config 校验拒绝、暂存成功必须正向
   观测到可见提示（表单关闭不算成功）。跑飞的 agent 在这套约束下也提交不了。
5. **凭证处理**：一次性 auth 链接只接受 TTY 上的 `getpass` 隐藏输入，非 tty 退出，拒绝 argv，
   拒绝存成 `form_url`；`state.json` 0600；共享机上对 `$WORK` 与登录态做 uid 属主校验。
6. **校验单一事实源 + 一次性报全错**。`dtwr_validation.py` 被 4 个入口共用，错误汇总后一起抛。
7. **零依赖 xlsx 写入器**（`xlsxlite.py`，130 行）替掉 openpyxl，降低他人机器上的 bootstrap 成本。
8. **测试五层且明确拒绝互相顶替**：单测 → mock DOM e2e → 隔离 HOME 全量验收 → 远端发行验收 →
   人工真机验收。文档明写 `FULL ACCEPTANCE PASS` 不能代替 `MANUAL_ACCEPTANCE.md`。
9. **诚实的自我限定**：`--confirmed` 三处文档均注明"只是操作者声明，不是人审证据或审计凭证"；
   属主检查注明"仅 POSIX，Windows 需人工确认 ACL"。不吹能力边界。

## 三、待修缺陷

| # | 位置 | 问题 | 严重度 | 状态 |
|---|---|---|---|---|
| ① | `fill_form.py` 附件上传 | 无完成校验，可能存下缺附件的草稿 | 高 | ✅ 已修 |
| ② | `extract_week.py` `dept_goal` | 缺键时裸 KeyError | 中 | ✅ 已修 |
| ③ | `fill_form.py` `STATE` 常量 | 忽略 `XDG_CONFIG_HOME`，与其余两处不一致 | 中 | ✅ 已修 |
| ④ | `fill_form.py::verify_draft_saved` | 依赖 frame 顺序，后置 frame 的错误看不到 | 低 | ✅ 已修：改为两趟——先扫全 frame 找错误，再找成功 |
| ⑤ | `fill_form.py` 各处 | 定长 `wait_for_timeout` 而非条件等待 | 低 | ✅ 已修：暂存后轮询等结果（上限 20s）取代定长 4s；日历面板改重试等待 |
| ⑥ | `gen_attachment.py` | 产物走 cwd 相对 `output/`，与 `$WORK/output/` 两套解析 | 低 | ✅ 已修：`-o` 缺省时走 `workdir()/output`，与 fill_form 同源 |
| ⑦ | `xlsxlite.py::Sheet.to_xml` | 未过滤 XML 非法控制字符 | 低 | ✅ 已修：新增 `xml_text()` 过滤 XML 1.0 非法控制字符 |
| ⑧ | `extract_week.py` | 重复 import sys | 琐碎 | ✅ 已修 |
| ⑨ | 仓库根 | 无 CI，测试不在 push 时运行 | 中 | ✅ 已修 |

**②③⑧⑨ 的修复与验证（2026-07-25）**

- ② `config.get("dept_goal", "")`；实测删掉该键后 `extract_week.py` 正常产出、`dept_goal` 落空串。
- ③ 新增 `dtwr_common.dtwr_config_dir()` 作为指针与登录态目录的**唯一**解析口，
  `workdir()` 与 `fill_form.STATE` 共用；实测 `XDG_CONFIG_HOME=/tmp/...` 时两者同源，
  未设时仍为 `~/.config/dtwr`。
- ⑨ `.github/workflows/ci.yml` 三个 job（单测 / 仿真 e2e / **历史脱敏扫描**）
  + `hooks/pre-push` 本地闸门。**CI 在 push 之后才跑，对防泄露已经晚了**——
  本地钩子才是唯一能在暴露前拦住的一道，两者都要。
- 历史扫描器 `tests/scan_history.py` 复用 `test_public_tree.SENSITIVE_PATTERNS`
  作单一事实源，扫全部 blob / commit / tag 对象（含提交信息），并校验提交身份必须是
  GitHub noreply。有效性已反向验证：对尚未 gc 的悬空旧对象能正确命中。

**① 与附件可选化的落地（2026-07-25）**

- `verify_attachment_uploaded` 两层证据：① 文件控件真的持有文件（`set_input_files`
  静默没生效会在这层暴露，两种模式都查）；② 页面出现附件名——与人工在
  `20-filled-review.png` 上核对「附件已挂」**同一判据**。等不到就中止，不落缺附件的草稿。
  仿真表单是同步的、没有异步完成信号，只做第 1 层。原先的 `wait_for_timeout(4000)` 已删。
- `form_fields.attach` 成为**唯一可留空**的字段，留空即整步跳过。
- 新增 8 项测试（配置推导 / 控件未持有 / 等不到附件名 / 名字不可见不算证据 /
  可见即通过 / 仿真只查第 1 层 / 空 attach 合法 / 其余字段仍必填）。
- 两条路径都跑了仿真 e2e：有附件字段 → 5 行断言全过；无附件字段 → 跳过上传、
  `attach` 为空、草稿照常落。
- 门禁自证有效：本批测试的第一版用了字段 id 形状的假值，被脱敏扫描当场拦下。

### 附件必选/可选（设计依据）

结论：**该由配置决定，但不能做成 CLI 开关。** 要分清两个问题——

- **表单有没有附件字段** = 组织事实，与字段 id、枚举同类，应当可配。现在
  `form_fields.attach` 是必填非空键，等于**让没有附件字段的组织根本配不出来**，
  违反第二节第 2 条不变量。
- **某一周要不要传附件** = 执行选择。表单要求附件时跳过就是交了不合规的周报，不该给选择。

实现取向：`form_fields.attach` 允许留空（语义 = 本表单无附件字段），由它**推导**必选性；
`do_fill` 配了则附件必须存在且必须校验上传完成，没配则整步跳过。**不新增 `--no-attach`
之类的开关**——那会成为 agent 的逃生口（生成失败 → 加参数绕过 → 交出缺附件的草稿），
正是本项目在别处都堵死的失败模式。放宽"必填非空"为"可空"向后兼容，**不需要升
`config_version`**。

### ① 附件上传没有完成校验 —— 唯一的"静默成功"缺口

`set_input_files()` 之后固定等待 4000ms 就继续。网络慢时草稿可能在附件未传完的情况下被暂存。
项目其他所有地方都要求正向确认，只有这里靠定长 sleep 加人看截图兜底。

修法：上传后等附件控件出现文件名节点（或上传完成标记），超时 fail-loud，与 `verify_draft_saved`
同款语义。字段配置侧可能需要在 `form_fields` 增加一个"附件已上传"判据键，届时同步
`dtwr_fields.py`、`configure.py::FIELD_SPECS`、`FIELDS.md` 与 `config.example.json`。

### ② `config["dept_goal"]` 会 KeyError

`dept_goal` 不在 `dtwr_validation.py::validate_config` 的 `required` 元组里，但
`extract_week.py` 直接下标取值。删掉该键后复现为裸 traceback，而不是项目自有的"缺什么列什么"
fail-loud 信息。修法二选一：加进 `required`，或改 `.get("dept_goal", "")`。

### ③ `XDG_CONFIG_HOME` 两套解析

`dtwr_common.py::workdir()` 与 `bootstrap.sh` 都尊重 `$XDG_CONFIG_HOME`，但 `fill_form.py` 的
`STATE` 常量硬编码 `~/.config/dtwr/state.json`。设了该变量的系统上，root 指针与登录态会落在
两个目录。同一事实两个源，正是本项目其他地方最避免的形态。修法：`STATE` 复用
`dtwr_common` 里的 config home 解析。

### ④ `verify_draft_saved` 依赖 frame 顺序

逐 frame 先查错再查成功，命中成功即 return。若成功提示在前一个 frame、错误在后一个 frame，
错误不会被看到。应有语义是"全 frame 无可见错误 ∧ 存在可见成功"，当前是"任一 frame 先出现
成功即通过"。风险低，但与这套代码的严谨度不匹配。

### ⑤ 定长等待遍布

加行与下拉这两个高风险点已写重试循环（`rows.count()` 真涨了才继续，做法正确），日期面板、
上传、暂存后仍是裸 sleep。失败是 fail-loud 加截图，可接受；既然重试模式已在这套 DOM 上验证
可行，剩余点位可以拉齐。

### ⑥ 附件路径两套解析

`gen_attachment.py` 默认写 cwd 相对 `output/`，`fill_form.py::attach_path` 读 `$WORK/output/`。
靠 SKILL.md「一律 `cd $WORK` 后执行」约束；跑错目录会得到"附件不存在"，失败是响的，但这是
全项目唯一没走 `workdir()` 的路径。

### ⑦ xlsx 未过滤控制字符

`escape()` 只处理 `&<>`。内容混入 `\x0b` 之类会产出 Excel 打不开的文件。加字符过滤即可。

### ⑧ 琐碎

`extract_week.py` 重复 import sys（`import sys` 与 `import sys as _sys`）；5 个脚本各自
`sys.path.insert(0, scripts_dir)` 而非做成包——今天无问题，但日后往 `scripts/` 添加与 stdlib
重名的模块会全线失败。

### ⑨ 无 CI

仓库无 `.github/`。测试写得齐整却没有任何机制在 push 时运行。公开仓最便宜的下一步是把单测与
mock e2e 挂上 Actions，与 `PUBLISHING.md` 的发布门禁对齐。

## 三点五、工程流程（开发 / 测试 / 发版 / 部署）现状与缺口

### 现状承载

| 阶段 | 现有承载 | 覆盖 |
|---|---|---|
| 开发 | [MAINTAINER.md](MAINTAINER.md)「本机开发」+ 本文件第二节不变量清单 | 部分 |
| 测试 | MAINTAINER.md 命令表 + [TESTING.md](TESTING.md) + CI 三 job + `hooks/pre-push` | 机制齐，选择规则未成矩阵 |
| 发版 | [PUBLISHING.md](PUBLISHING.md)（分发 / 许可 / 泄露处置 / 门禁）+ `pack-skill.sh` | 有硬缺口，见 ⑩ |
| 部署 | [../README.md](../README.md) + 技能包 `USER_GUIDE.md`（安装 / bootstrap / 配置 / 登录 / keepalive / 升级） | 较好，缺回滚 |
| 运行期 | `SKILL.md` + `references/CONTRACT.md` + [MANUAL_ACCEPTANCE.md](MANUAL_ACCEPTANCE.md) | 好 |

### 缺口（是机制不存在，不是文档没写）

| # | 缺口 | 后果 | 状态 |
|---|---|---|---|
| ⑩ | **完全没有版本概念**：无 CHANGELOG、0 个 git tag、无版本载体、zip 用日期戳 | 见下 | ✅ 已修（A） |
| ⑪ | **无回滚路径** | 发出坏版本后用户无法退回 | ✅ 已成文（C）；`npx skills` 无版本 pin 是上游缺口，已在 [SOP.md](SOP.md#部署用户侧与回滚) 记录并给出降低影响的做法 |
| ⑫ | **测试选择无矩阵** | "改了什么必须跑什么"无处可查 | ✅ 已修（C）：[SOP.md「改动类型→必跑验证」](SOP.md#改动类型--必跑验证) |
| ⑭ | **工作日志格式是隐性契约** | 全仓只说路径 `docs/report/PROGRESS_REPORT.md`，从未说明文件该长什么样；解析要求全埋在 `extract_week.py` 的两个正则里。维护者自己的文件符合是因为工具和它一起长出来的——**换个人配好 progress_report 却写不对格式，只会得到一整周 TODO 且不知道为什么** | ✅ 已修：`references/CONTRACT.md` 新增「工作日志的格式契约」（含最小示例、工作日必须全覆盖、拒绝覆盖已有 json 的行为） |
| ⑮ | **发行审计门禁不可用** | 整日志 grep `Critical Risk\|High Risk`：① 不限定本 skill 那一行，同批安装的**其它 skill** 的评级会让我们的验收失败；② CLI 那列的字样与平台页面实际 RISK LEVEL 不一致（CLI 写 Critical Risk、页面写 MEDIUM），拿它当严重度判据不可靠；③ 本 skill 的告警源自固有能力，恒红的门禁等于没有门禁 | ✅ 已修：改为**与已复审基线比对**（`tests/fixtures/expected-audit-row.txt`），语义从「干不干净」变成「有没有变」，评级一变即要求人工复审 |
| ⑯ | **多设备 / 多人场景无任何文档** | 「不要拷贝 state.json」「多设备」「另一台」在全仓出现 **0 次**；而路线图上有 P-B「同事复用包」，分发出去必然撞上：登录态被当普通文件拷贝、多端互踢、同周落两份草稿撞唯一性判定 | ✅ 已修：`SKILL.md`「多设备 / 多人」+ `USER_GUIDE.md` 第 5 节 |
| ⑰ | **运行日志不落文件** | 12 处 `[fill_form]` 逐步日志只到 stdout，全项目只有 cron keepalive 重定向到文件。**会话一关日志就没了，失败后回溯只剩截图**——截图能看最终状态，看不到「第几行开始不对、等了多久超时」 | ✅ 已修：写 `$WORK/output/fill_form.log`，URL 落盘前脱敏 |
| ⑱ | **`--dump` 被完整配置校验挡住** | `--dump` 的用途就是**找出字段 id**，却要求字段 id 已配好才能跑——新用户拿空模板运行只会得到「字段不能为空」。这是别人用不起来的**具体机制**，不是抽象的「门槛高」 | ✅ 已修：`--dump` 只校验 `form_texts.add_row` / `start_date_label`，`--login` 只校验 form_url，填表与保活仍走完整校验 |
| ⑲ | **脱敏把「值长什么样」也删了** | 公开模板里全是空串，新用户不知道该向管理员要什么、拿到的对不对、`dump.html` 里该找什么形状 | ✅ 已修：`FIELDS.md` 加掩码形状表（`F#######` / 32 位十六进制）、可复制的索取模板、以及修正后的获取流程 |
| ⑳ | **工作日硬编码周一~周五，无视节假日与调休** | `extract_week` 只生成 `range(5)` 五天、`validate_report` 缺任一周一~周五即阻断。国庆/春节周会**强迫为放假日填工时**；调休周六上班则**根本不生成该行 → 漏报**。中国假期制度下两头都错 | ✅ 已修：配置项 `holidays` + `extra_workdays`，工作日集合 = (周一~周五 − holidays) ∪ extra_workdays；报告写入 `workdays` 快照供校验，旧报告回落周一~周五 |
| ㉑ | **登录态过期时静默产出无效 dump** | `--dump-list` / `--dump-record` 只用 URL 含不含 `login`/`entry/auth` 判登录态，而实测氚云过期后落到的登录页 URL **不含**这两个字样——于是照常写文件、给统计、无任何报错。拿登录页去推断字段只会得到垃圾，且是本项目最忌讳的静默成功 | ✅ 已修：抽 `assert_logged_in()`，判据改为**正向确认看见 `form_texts.report_title`**（keepalive 本就这么做，新加的两个模式漏了），四处共用 |
| ㉒ | **`--login` 在用户还没扫码时就报告成功** | 判据是「URL 里没有 `login` 且含 `h3yun`」，而氚云登录页 URL 恰恰不含 `login`——于是一打开登录页就判定成功，把**未登录**的会话存成 `state.json` 并打印「登录态已保存」。后续所有步骤都会拿这份废登录态去跑。与 ㉑ 同源，我修 ㉑ 时漏了登录这条路径 | ✅ 已修：新增 `looks_logged_in()` 正向判据（必须看见 `report_title`），`--login` 轮询到确认才落盘、`--login-url` 同样；无正向标识时宁可超时也不认 |
| ⑬ | **开发流程未成文** | 公开仓无 `CONTRIBUTING.md`，而选 Apache-2.0 的首要理由正是"会收到陌生人 PR" | ✅ 已修（B）：[CONTRIBUTING.md](../CONTRIBUTING.md) + [SOP.md](SOP.md) |

⑩ 的后果很具体：`npx skills update` 的用户不知道更新到了什么、变了什么；出问题说不清哪版引入；
**2026-07-25 的附件行为变更（等不到附件名即中止）就是活例——装了旧版的人升级后会撞上新的中止
行为，而没有任何地方告知**；同一天打两次包还会互相覆盖。

另：`PUBLISHING.md` 的手工门禁清单与新 CI 有重叠，两套并存会漂移。

### 处置取向：补机制优先于写文档

文档已 9 个文件千余行、taxonomy 清楚。再新增「开发 / 测试 / 发版 / 部署」四份 SOP 会造成重叠与
漂移——那恰恰违反本项目自己的单一事实源原则。取向是**只新增两个文件**：

- **A. 引入版本号（唯一真正缺失的机制）**：`SKILL.md` frontmatter 加 `version` 作单一事实源
  → `CHANGELOG.md` → git tag → `pack-skill.sh` 改用版本号命名 → **加测试守住 tag /
  frontmatter / CHANGELOG 三者一致**（沿用本项目"用测试守约定"的既有套路）。
- **B. `CONTRIBUTING.md`**（约 20 行）：装 pre-push 钩子、提交身份必须 noreply、
  禁止提交任何真实表单数据、PR 必过 CI 三 job。
- **C. `docs/SOP.md`**（唯一新增的 SOP 文件）：四阶段流程骨架 + 三张表——改动类型→必跑验证矩阵、
  发版检查单（标明哪些 CI 自动 / 哪些人工）、回滚路径。具体命令一律链回现有文档，**不复制**。

顺序 A → B → C，机制先于文档。Apache-2.0 的三项配套（版权主体、SPDX 头、SPDX 断言）并入 A。

**A 已于 2026-07-26 完成**：`VERSION`（单一事实源，刻意不入 frontmatter，理由见
[PUBLISHING.md](PUBLISHING.md#版本与发版)）+ `CHANGELOG.md` + tag `v0.1.0` +
`pack-skill.sh` 按版本号命名并把未打 tag / 脏工作区标成 `-dev.<sha>` +
`tests/test_version.py`（semver / CHANGELOG 一致 / SPDX 头 / shebang 未被挤走）+
Apache 三项配套。⑪ 回滚路径归入 C 一起写。

## 四、历史泄露：已经发生，不是待办

**2026-07-25 核实：仓库已是 PUBLIC，历史敏感对象公网可直取。** 这不是"发布前要处理的阻断"，
是**已生效的泄露**。

核实方式与结果：

| 检查 | 结果 |
|---|---|
| GitHub 仓库可见性 | `"private": false` / `visibility: PUBLIC` |
| 含敏感内容的提交 | 重建前 36 个提交中 **35 个命中** |
| 公网可达性 | 实测可直取历史版本文件（HTTP 200） |
| 暴露窗口 | 仓库创建于 2026-07-21，约 4 天 |
| fork / star / watcher / tag / release / issue | 均为 0，wiki 未建，无下游副本 |

（具体提交标识不在本文件记录：在 GitHub 回收弃置对象之前，公开这些标识等于附送取回路径。）

### 已排除：无凭证泄露

逐项验证，以下**从未**进入过版本库：一次性 `entry/auth` token 值、`state.json` 登录态、
cookie、`output/shots/` 截图。因此不构成账号接管风险，**没有需要立即轮换的凭证**。

### 实际泄露内容（按对组织的实质影响排）

1. **3 份真实周报 JSON**（`weeks/week_report_20260706` / `_20260713` / `_20260720`）——
   逐日真实工作内容、工时、项目名与进度。对公司而言这是最实质的一项：内部项目进展流水。
2. **表单 URL（200 字符）** —— 含组织氚云租户与表单标识，可定位到具体实例（未登录仍打不开，
   但便于社工与钓鱼）。
3. **10 个真实表单字段 DOM id**（历史 `FIELDS.md`）与**组织项目编码**（历史 `README.md`）。
4. **真实姓名**、内部项目/活动全名、内部会议名与工作状态枚举。
5. **本机绝对路径**（含系统用户名与内部项目目录结构）。

### 处置

见 [PUBLISHING.md「历史泄露处置」](PUBLISHING.md#历史泄露处置已发生)。要点：转 private 只止
新增抓取的血，不撤回已发生的暴露；历史重写后被弃置的 commit 在 GitHub 上仍可按 hash 访问，
需另行请求 GitHub Support 清除。

选许可证只在公开时才有意义——本项目已经公开，所以许可证已经生效，反倒是**脱敏没跟上公开**。
