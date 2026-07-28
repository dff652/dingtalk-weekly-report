# 维护者指南

面向克隆本仓库的维护者。用户安装与每周使用见 [../skills/dingtalk-weekly-report/USER_GUIDE.md](../skills/dingtalk-weekly-report/USER_GUIDE.md) 与根 [README.md](../README.md)。

文档分层：用户看根 [README.md](../README.md)（Install / 给 AI / Verify / Use）；细节在技能包
`USER_GUIDE.md`；本文件仅维护者。

## 仓库角色

| 路径 | 职责 | 进 zip？ |
|------|------|----------|
| `skills/dingtalk-weekly-report/` | 技能包（`$SKILL`） | 是（平铺为 zip 根） |
| `~/weekly-report-data`（示例） | 维护者自己的私有 `$WORK`，必须在仓库外 | 否 |
| 根 `.venv/` | 可选开发测试环境，不含个人业务数据 | 否 |
| `~/.config/dtwr/` | 指针 + 登录态 | 否 |
| `pack-skill.sh` / 根 `install.sh` | 打包 / 转调技能 install | 否 |
| `tests/` | 仿真 e2e / 冒烟 | 否 |

源码仓库不得兼作 `$WORK`。维护者与普通用户都使用仓库外目录，例如
`~/weekly-report-data`；根 `.gitignore` 只作为误提交的第二道防线。

## 本机开发

流程骨架与决策表（改动类型→必跑验证、发版检查单、回滚路径）见 [SOP.md](SOP.md)；
外部贡献者规则见 [CONTRIBUTING.md](../CONTRIBUTING.md)。

克隆后**第一件事**是装 pre-push 钩子——CI 在 push 之后才跑，防泄露必须在本地拦：

```bash
ln -sf ../../hooks/pre-push .git/hooks/pre-push
```

```bash
bash install.sh --link              # ~/.claude + ~/.codex skills 软链到仓内
# 改代码即时生效；勿对软链误跑无 --force 的 copy 安装
bash tests/run_mock_test.sh         # 改 fill_form 后必跑
bash tests/run_smoke.sh             # pack + 隔离 install + 附件 + 仿真
bash tests/run_full_acceptance.sh   # 隔离 HOME：安装 + bootstrap + 完整仿真使用
bash tests/run_release_acceptance.sh # GitHub 下载 + 远端安装 + 审计门禁
bash pack-skill.sh                  # dist/dingtalk-weekly-report-skill-YYYYMMDD.zip
```

生态安装自测（隔离 HOME 更安全；公开发布与脱敏门槛见 [PUBLISHING.md](PUBLISHING.md)）：

```bash
npx skills add dff652/dingtalk-weekly-report -l -y
npx skills add dff652/dingtalk-weekly-report -s dingtalk-weekly-report -a claude-code -a codex -g -y --copy
```

注意：`npx skills -a codex` 常装到 `~/.agents/skills`，不一定写 `~/.codex/skills`（README 补链步骤）。

## fill_form 模式

| 命令 | 作用 | 何时用 |
|------|------|--------|
| `… json` | 只填不存 | 预览 |
| `… json --draft --confirmed` | 人审并检查旧草稿后暂存 | **每周正式** |
| `--login` | 扫码 | 会话失效时首选 |
| `--login-url` | 用户在交互终端隐藏输入 auth 链接 | 扫码不可用时兜底 |
| `--keepalive` | 续 cookie | cron / 计划任务 |
| `--dump` | DOM 诊断 | 联调 |

`--confirmed` 是操作清单声明，不是审计证据。属主自动检查仅覆盖 POSIX；Windows 验收需检查用户目录 ACL。

## 维护触发表

| 触发 | 动作 |
|------|------|
| 每周例行 | 在私有 `$WORK` 更新内容源与 `weeks/week_report_*.json` |
| 会话失效 | 首选 `--login` 扫码；auth URL 兜底由用户本人在交互终端隐藏输入 |
| 换项目/默认值 | `scripts/configure.py`（校验后写入并备份旧配置） |
| 组织改字段/枚举 | 只更新私有 `config.json` 的 `form_fields` / `form_texts` / `vocabulary` |
| DOM 变化 | `--dump` → 改选择器 → `run_mock_test.sh` |
| 分发同事 | `run_smoke.sh` → `pack-skill.sh` 或推 GitHub 用 `npx skills` |
| 环境坏 | `bootstrap.sh --force-venv` + 重登 |

## 调试

- 失败截图：`$WORK/output/shots/99-error.png`
- `--dump` → dump.html / dump.png
- 登录态：`~/.config/dtwr/state.json`（0600，勿入 git）
- 一次性 auth 链接：Agent 不得接收；不得进入 argv、聊天、文件或 git

## 表单硬规则（工具侧）

- 工具只落草稿，不提交；
- `form_texts.save_draft` 不得指向提交按钮；
- 截止提醒、休假状态/工时、枚举和字段 ID 均来自私有配置；
- 附件命名 `YYYYMMDD-YYYYMMDD本周工作总结与下周计划.xlsx`；content ≤200 字。

## 测试覆盖

最近一次结果、真实安装踩坑与解决过程、尚未完成的人工边界见
[TESTING.md](TESTING.md)。

```bash
bash tests/run_smoke.sh
bash tests/run_mock_test.sh
bash tests/run_full_acceptance.sh
.venv/bin/python skills/dingtalk-weekly-report/scripts/fill_form.py --keepalive  # 可选真机
```

| 项 | 自动？ |
|----|--------|
| 历史脱敏扫描（`tests/scan_history.py`） | ✅ pre-push 钩子 + CI |
| 单测 / 仿真 e2e | ✅ CI（`.github/workflows/ci.yml`） |
| pack / 隔离 install / 附件 / 仿真 e2e | ✅ |
| bootstrap + 独立 venv + 安装后仿真使用 | ✅ `run_full_acceptance.sh` |
| GitHub 下载 + skills CLI + 安全审计 | ✅ `run_release_acceptance.sh` |
| 真机 keepalive | 可选 |
| 真机 `--draft --confirmed` / 钉钉提交 | ❌ 人工 |

真实生产验收必须逐项执行 [MANUAL_ACCEPTANCE.md](MANUAL_ACCEPTANCE.md)，不能用
`FULL ACCEPTANCE PASS` 或 `RELEASE ACCEPTANCE PASS` 代替。

安装验收不要只看命令是否返回：必须分别确认 Skills CLI 列表、安装文件、bootstrap root
指针、独立 venv、Chromium 实际启动和最终测试退出码。Node/Skills CLI 版本不兼容、
`~/.agents` 与 `~/.codex` 的发现差异、浏览器下载中断和 root 指针解析的具体排查命令见
[TESTING.md「本机安装→使用验收记录」](TESTING.md#2026-07-24-本机安装使用验收记录)。

## 路线图

- [x] P1 内容 + 附件 + 粘贴
- [x] P-A Skill 包 + install/bootstrap + GitHub/`npx skills`
- [x] P2 Playwright 真机联调 + 仿真 e2e
- [ ] P3 氚云 OpenApi（**降级为"有条件可行"**；阻塞项按序：租户版本 → `EngineSecret`；
      推荐先只做**读**路径，写入不迁移。理由见下节 `IsSubmit`）
- [x] P4 配置自动发现（阶段 0/A/B/C/D 全部落地，真机 8/10 自动定位、零错误）（把"手抄十个字段 id + 三组枚举"降为"确认十几个候选"）

### P3 评估：改走氚云 OpenApi（未启动，2026-07-28）

**当前状态：阻塞在凭据上。** OpenApi 需要 `EngineSecret`，只能由租户管理员在氚云后台取，
本人拿不到。**拿到之前不要动代码**——浏览器路径 2026-07-28 才刚跑通并真机验证，
现在推翻等于把刚回本的投入扔掉。

#### 收益（真实，不是"更优雅"）

今天七个真机 bug 里有六个是**驱动网页的固有成本**：登录态、iframe 生命周期、
受控上传组件、异步渲染时序。走 API 这一类整体消失。附带：

- 去掉 790MB Chromium 与 `bootstrap.sh` 的下载环节（新用户安装最大的一块）
- 去掉扫码登录、`--login-web`、keepalive cron 整条线
- Snyk `W012 Unverifiable external dependency` 自动消失（它指的正是 `page.goto` 到远端页面）
- 选择器不再随氚云前端改版而碎

#### 文档调研已确认的事实（2026-07-28，不需要凭据就能查）

| 项 | 结论 | 来源 |
|---|---|---|
| 端点 / 鉴权 | `POST https://www.h3yun.com/OpenApi/Invoke`，JSON，请求头带 `EngineCode` + `EngineSecret` | help.h3yun.com/contents/1014/1640.html |
| 数据 CRUD | `LoadBizObject` / `LoadBizObjects` / `CreateBizObject(s)` / `UpdateBizObject` / `RemoveBizObject` 齐全 | 同上 |
| **附件上传** | **有 `UploadAttachment`**，但契约是「**先建数据、再传附件**，附件不得塞进表单数据」 | 氚专 OpenApi 文档 |
| **系统字段** | 业务数据里带 `WorkflowInstanceId` 与 `Status` | 氚专 OpenApi 文档 |

**原先记的两个"待验未知"到此都有答案了，而且都是好消息**：附件有官方接口（两步、有顺序约束
但可行）；`Status` 可读，意味着[编辑既有草稿]的「状态必须是草稿」护栏在 API 侧能复现。

#### ⚠️ 但调研挖出一件更要命的事：`IsSubmit`

`CreateBizObject` 有一个**必填**参数 `IsSubmit`：

> `true` = 创建**生效**数据（即提交）；`false` = 草稿数据。

也就是说——**存草稿和提交是同一个调用的同一个参数，差一个布尔值**。

这比本节初稿写的"只隔着一个函数名"**严重得多**，而且三个细节让它更糟：

1. **可能 fail-open**：一份第三方文档把该参数的默认值标为 `true`；官方镜像标"必填、
   默认值未指定"。**如果漏传就等于提交**，与本项目"缺配置就 fail-fast"的原则完全相反。
2. **类型在文档里不一致**：一处写 `Bool`，另一处写 `string` 且示例是 `"IsSubmit":"true"`
   带引号。那么 `false` / `"false"` / Python 的 `False` 哪个真能得到草稿，**不能只信文档**。
3. **错了不可逆**：周报记录**只能清空、不能删除**（本项目已踩过这条，见[编辑既有草稿]的由来）。
   误提交没有回退键。

对比一下今天：提交能力是**代码里不存在的路径**；换 API 后变成**每次写入都要正确地传一个
布尔值**。安全性质从"结构性不可能"退化成"每次调用都在悬崖边上"。

**若仍要做，配套要求（四条，缺一条不算数）：**

1. 禁止裸调 `CreateBizObject`——必须经**唯一一个**封装函数，`IsSubmit` 在函数体内**写死**
   为草稿值，不接受调用方传参；
2. **用真实调用验证**该值确实产出草稿（读回 `Status` 确认），**不接受"文档这么写"当证据**——
   这正是本项目"正向确认"原则的应用场景；
3. `tests/test_invariants.py` 继续通过，断言目标改为「`IsSubmit` 只在封装函数里出现一次，
   且不来自参数或配置」——**改断言，不是删文件**；
4. `SECURITY.md` 的措辞要改成 API 语境下**诚实**的表述，不能沿用"脚本里不存在提交路径"装作没变。

#### 还有一个比 secret 更前置的闸：版本

多份资料指向 **OpenApi / 自定义接口属于专业版（付费）能力**，官方文档站本身就叫
「氚**专** OpenApi 文档」。**先确认租户版本支不支持，再谈要密钥**——版本不支持的话，
`EngineSecret` 根本不存在，这封消息就白问了。

#### 结论：从"值得做"降级为"有条件可行"，且优先级下调

不是不可行，是**成本结构变了**：

- 收益没变（去掉 Chromium / 登录 / keepalive 整条线）；
- 但风险从"重构时可能被稀释"变成"每次写入都在悬崖边"；
- 而浏览器路径最大的痛点——登录——已经被 `--login-web` 解决了，**痛感显著下降**，
  换路的紧迫性随之下降。

**推荐的中间路线（真正的"并存"最优解）：只用 API 做读，写仍走浏览器。**

`LoadBizObjects` 是纯读接口，完全不碰 `IsSubmit`。只做读就能拿到：

- `--status` 直接读真实记录状态，不用开浏览器；
- 字段发现（P4）不再需要 dump 页面；
- [编辑既有草稿]的两道护栏用 `Status` 判据，比解析表格单元格可靠。

而**提交能力仍然是结构性不存在的**——因为写入路径压根没换。收益拿到大半，风险几乎为零。

**下一步（按顺序）：**

1. 问管理员：**本租户的氚云版本是否支持 OpenApi / 自定义接口**（不是先要密钥）；
2. 支持的话再要 `EngineCode` + `EngineSecret`（后台：系统管理 → 系统集成 → 企业开发信息）；
3. 拿到后**先只做读**（`LoadBizObjects` 查周报列表），验证鉴权与数据形状；
4. 写入路径**暂不迁移**，等读路径稳定运行一段时间再单独评估。

拿到密钥之前不写代码。

### P4 方案（已在真实 DOM 上取证）

对本人 2026-07-21 的真实表单 dump 做过结构分析，结论直接否掉了"按标签认字段"的直觉方案：

| 假设 | 实测 |
|---|---|
| 控件附近有中文标签文本 | ❌ 前 600 字符内无 |
| 标签挂在 `title` 属性 | ❌ 15 个候选里只有 1 个能关联 |
| 子表有 `<th>` 列头 | ❌ 无该结构 |
| `aria-label` / `placeholder` | ❌ 只有「图标: left」「年-月-日」这类 |

但两条结构规则很干净，可直接用：

- **32 位十六进制 id 全页仅 1 个**，class 含 `subgrid-control-adapter` → 子表容器零歧义确定
- **`F`+7 位数字共 15 个，其中 10 个位于子表容器之后** → 主表字段与行字段可自动切分

剩下"哪个是工时、哪个是状态"在**空白表单**上没有可靠信号，因此改走**已填历史记录 + 值形状匹配**
（日期格式→row_date、纯数字→row_hours、长文本→row_content、短枚举→row_type/row_status、
项目全名→row_project）。值形状比标签可靠得多。

数据来源按可靠度分级，前一级拿不到才降级，**任何一级都不自动写入 config**：

1. 用户/表单管理员直接提供
2. 展开下拉抓选项 —— 枚举的**唯一**正确来源（历史只含"用过的值"，拿不到没用过的休假状态）
3. 历史记录值形状匹配 —— 字段定位主力，**一条完整记录即可**；仅当该条残缺时才往前取，上限 4 条
4. 空白表单结构切分 —— 兜底，只能定到"子表容器 + 主表/行分组"

**阶段 0 已完成并真机取证（2026-07-27）**：新增 `--dump-list`（只读 dump 列表页）与
`--dump-record N`（打开第 N 条历史记录并 dump，只读不保存）。真机结果：

- 列表页是 h3yun 自有网格，**不是 `<table>`、标题不是 `<a href>`**（全页仅 8 个链接），
  所以无法用 URL 直取记录，必须点 `span.tg-link`。行容器 `.tg-row`，单元格 `.tg-cell.tg-c-<N>`，
  **列序带稳定编号**且表头文字与 `tg-c-N` 一一对应。
- 取一条 9 行的历史记录，按字段 id 分组统计取值形状，结果高度一致：
  日期×9 → `row_date`、数字×9 → `row_hours`、短文本×4+长文本×4 → `row_content`
  （长短混杂正是内容字段特征）。**这三个值形状即可唯一确定。**
- `row_type` / `row_project` / `row_status` 三者都是短文本，**形状分不开**——需第二重信号：
  取值 ∈ `vocabulary.project_types` → row_type；∈ `statuses` → row_status；
  == `form_project` → row_project。枚举来自展开下拉（独立来源），两信号叠加即可区分。
- 主表三项用**控件类型**区分：`input[type=file]` 全表单唯一 → `attach`；`textarea` → `note`；
  日期控件 → `start_date`。

**结论：值形状 + 枚举匹配 + 控件类型三者叠加，9 个字段 + 子表容器可全自动定位。**
剩余实现 = B 枚举抓取 → C 三信号匹配器 → D `configure.py` 逐项确认写入。

**阶段 0 原始说明**：`fill_form.py --dump-list` 只读 dump 列表页并统计候选入口，
只需登录态、不需要字段配置。**待真机跑一次**——把它输出的统计行（不是 html 本身，
html 含组织数据）拿回来，才能实现「打开一条历史记录」那步。

实施顺序：0 让 `--dump` 支持指向历史记录页取证（0.5h）→ B 枚举抓取（2h，独立且收益最大）
→ A 结构切分（2h，已验证）→ C 值形状匹配（半天，依赖阶段 0）→ D `configure.py` 逐项确认写入（2h）。

改代码前先读 [REVIEW.md](REVIEW.md)：第二节是**不变量清单**（改动不得破坏），第三节是代码缺陷
清单（①②③⑧⑨ 已修，④⑤⑥⑦ 待修），第三点五节是**工程流程缺口**（⑩ 无版本号、⑪ 无回滚路径、
⑫ 测试选择无矩阵、⑬ 开发流程未成文）及其处置取向 A/B/C。历史泄露的处置与状态见
[PUBLISHING.md](PUBLISHING.md#历史泄露处置已发生)。

## 跨平台运行时（不换 TS）

| 层 | 做法 |
|----|------|
| Skill | `npx skills` / install.sh → 标准 skills 目录 |
| Python | uv + `$WORK/.venv` |
| 浏览器 | `requirements-runtime.txt` 锁定的 Playwright + 自带 Chromium |
| 保活 | cron / Windows 计划任务 |
