# 维护者指南

面向克隆本仓库的维护者。用户安装与每周使用见 [../skills/dingtalk-weekly-report/USER_GUIDE.md](../skills/dingtalk-weekly-report/USER_GUIDE.md) 与根 [README.md](../README.md)。

文档分层：用户先看根 [README.md](../README.md)（价值 / 边界 / 工作流 / 快速开始）；
完整安装与操作在技能包 `USER_GUIDE.md`；本文件仅维护者。

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

### 独立核对「某周到底提交了没」

不要靠回忆或截图，用 `--dump-list` 读真实列表。列表是**列主序网格**，三列对上就够：

| 列 | 含义 |
|---|---|
| `.tg-cell.tg-c-6` | 报工开始日期 |
| `.tg-cell.tg-c-8` | 周总工时 |
| `.cell-status` | 状态（草稿 / 进行中 / 已生效） |

判据：**状态离开「草稿」即已提交**（进行中 = 在审批流里）。这也是
`find_editable_draft` 两道护栏的数据来源——它只认「状态=草稿 且 开始日期=目标周周一」，
所以已提交的记录不会被误改。

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
- [~] P3 氚云 OpenApi —— **暂不采用，不排期（决定于 2026-07-28）**。技术可行但收益不抵风险
      （`IsSubmit` 把存草稿与提交做成同一参数）；调研结论与**重估触发条件**见下节，
      触发前不要重开此话题
- [x] P4 配置引导与自动发现（首次缺项由 Agent 主动询问并可分阶段安全保存；真实 DOM
      8/10 自动定位、零错误）（把“自己改空模板 + 手抄十个字段 id”降为“回答基础问题 +
      确认十几个候选”）
- [x] P5 GitHub Issue 安全辅助 —— 新 Issue 只自动发送固定安全回执；Claude API 方案已评估但
      因独立 Key / 计费与治理成本暂不启用。Issue 由维护者明确发起本地 Codex 排查与实施，
      commit / push / 回复 / 关闭分别授权。2026-07-30 已用一次性 Issue #2 完成远端验收：
      workflow 成功且仅回复预设文本，主分支 / 分支集合 / 开放 PR 无变化，测试 Issue 由维护者
      手动关闭；证据见 [GitHub 项目页 SOP](GITHUB_PROJECT_PAGE_SOP.md#当前决定只自动回执ai-处理由维护者启动)
- [x] README visual refresh —— 静态 Hero、工作流图与内容重排已在本地落地并通过宽/窄屏预览
- [~] GitHub 项目页元数据 —— About、Topics、skills.sh Homepage 与 v0.3.0 Release 已完成；
      Social preview 首版已上传，跨平台字体修正版待替换

### GitHub 项目页 / README 优化决定（2026-07-30）

长期执行流程已固化到
[GitHub 项目页与 README 维护 SOP](GITHUB_PROJECT_PAGE_SOP.md)；本节只保留本项目的决定、
视觉事实源与实施状态。

> **决定：可行，采用；先做本地预览，不直接发布。** 使用
> [`oil-oil/beautify-github-readme`](https://github.com/oil-oil/beautify-github-readme)
> 的整份 README 模式做 **visual refresh**，不做全量品牌重构。本次评估基于上游
> `main@55bdb1c05414cd7a0cf911d02e55ece79777206e`；实施时先复核并固定实际使用的 commit，
> 不经审查地跟随移动的 `main`。

**实施状态（2026-07-30）：** 已按该固定 commit 的规则完成 `assets/readme/hero.svg`、
`assets/readme/workflow.svg` 和 README 阅读顺序重排。本地 Chromium 预览覆盖 900px 与
360px 内容宽度；窄屏流程图同时由紧邻的纯文本序列兜底。用户已授权提交并推送；
此前另行授权后已更新 GitHub About、Topics、skills.sh Homepage，并补建 v0.3.0 Release。
验收结果：上游 README audit、公开树 4 项、历史扫描、Skill 校验、116 项单测及完整 smoke
（含隔离安装与 mock 草稿 e2e）全部通过。

#### 为什么值得做

当前 README 的事实、安装路径和安全说明已经完整，但首屏从维护者信息表很快进入 Node、uv、
bootstrap、补链和验证命令。新访客尚未建立「它解决什么问题、为什么安全、第一次成功是什么」
的认识，就先承担了实现细节。优化的目标是**调整阅读顺序并增加两张有沟通任务的静态图**，
不是把 README 装饰成不可搜索、不可复制的长图。

采用后的建议顺序：

1. 项目原生 SVG Hero：一句话价值 + 「只落草稿、内容人审、用户最终提交」；
2. 一张工作流图：工作日志 → JSON 人审锚点 → XLSX → 氚云草稿 → 人工提交；
3. 三个核心差异：无提交能力、私有 `$WORK` 隔离、失败必须有正向证据；
4. 最短安装与第一次调用；
5. CI / mock e2e / release acceptance 等真实验证证据；
6. 确定性安装、配置、Verify、维护者入口和完整文档索引。

#### 视觉与内容边界

- 采用**纯静态 SVG**，计划只做一张 Hero 和一张工作流图；不做 GIF、ImageGen、人物或电影化素材。
- 不使用真实氚云截图：截图可能包含租户、字段 ID、姓名、周报内容和登录上下文。
- 不引入远程字体、脚本、`foreignObject` 或依赖第三方动态徽章服务的关键证据；正文、命令、
  链接和限制继续留在可搜索、可复制的 Markdown。
- 不编造采用量、兼容性、性能或跨租户稳定性。当前「仅一个租户真机验证」「Windows 尚未实机」
  等边界不得被视觉文案弱化。
- 保留安装、隐私、安全、回滚和完整文档入口；允许折叠或后移，不允许为了首屏简洁删除。
- 上游 `audit_readme.py` 只检查本地图片引用、SVG 基础兼容和 alt text，不能替代内容正确性、
  脱敏和真实安装验收。

#### README 视觉资产规范

| 资产 | 画布 | 作用 |
|---|---:|---|
| `assets/readme/hero.svg` | 1200×400 | GitHub README 首屏价值与安全边界 |
| `assets/readme/workflow.svg` | 1200×520 | 五步 fail-closed 流程 |
| `assets/readme/social-preview.svg` / `.png` | 1280×640 | GitHub 分享预览的可编辑源与上传成品 |

- 中文字体栈统一为 `Noto Sans CJK SC → PingFang SC → Microsoft YaHei → sans-serif`；
  纯英文项目名用 `Noto Sans → Segoe UI → Arial`，元数据用系统等宽字体。
- 只使用真实存在的 `400` / `700` 字重，禁止 `600` / `650` / `750` 等依赖浏览器合成的中间值。
- 主色板固定为 navy `#0B1220`、ink `#111B2D`、blue `#246BDE`、amber `#F4B740`、
  warm white `#F7F4EC`、muted `#607086` / `#9FB0C7`；新增颜色必须说明语义并复验对比度。
- README 全宽资产保留至少 48–64 SVG 单位安全边距；Social preview 保留至少 72 单位，
  其成品必须是 1280×640、纯色底、PNG 小于 1MB。
- SVG 必须有 `title` / `desc` / `role=img` / `aria-labelledby`，不得使用脚本、
  `foreignObject`、远程字体、远程图片、内嵌位图或依赖动画。
- 自动门禁见 `tests/test_readme_assets.py`；合入前另用 Chromium 检查实际字体、文本边界及
  README 900px / 360px 渲染。360px 下非关键说明允许缩小，但核心标题、阶段名称和相邻
  Markdown 必须独立表达完整流程。

#### README / SKILL / docs 信息分层决定（2026-07-30）

> **决定：需要继续拆分，但按分发边界拆，不按文件长度机械拆。** 根 README 是 GitHub
> 落地页；skills.sh 页面主体和 Agent 运行上下文来自 `SKILL.md`；只有
> `skills/dingtalk-weekly-report/` 会随 Skill 安装。把运行必需信息只移到根 `docs/`
> 会让安装副本丢失依赖，禁止这样做。

| 层 | 主要读者 / 作用 | 是否随 Skill 安装 | 应保留什么 |
|---|---|---:|---|
| 根 `README.md` | GitHub 新访客 | 否 | 价值、证据、安全边界、流程、最短安装、限制、文档入口 |
| `skills/.../SKILL.md` | Agent；skills.sh 详情页 | 是 | 触发条件、`$SKILL/$WORK`、三条铁律、运行步骤、失败停止条件 |
| `skills/.../USER_GUIDE.md` | 安装和操作用户 | 是 | 完整安装矩阵、配置、登录、CLI、自检、升级、多设备、FAQ |
| `skills/.../references/` | Agent 按需读取 / 维护者 | 是 | 输入输出契约、字段与 DOM 约束 |
| 根 `docs/` | 维护者、验收人、贡献者 | 否 | 测试证据、发布、评审、历史事件和长期决策 |

安全拆分原则：

- 精简根 README **不影响** `npx skills add`；它不是安装输入。
- 只精简根 README **不会改变** skills.sh 截图里的长正文；该页面展示的是 `SKILL.md`。
- `SKILL.md` 首屏可移除逐文件“包内清单”，改为一句“自包含、多文件 Skill”并链接同目录
  `USER_GUIDE.md`；但运行步骤和安全闸不得只留链接。
- 需要复制、搜索、翻译或频繁更新的命令与说明继续用 Markdown，不塞进 SVG。
- 移动前后必须保证安装目录仍自包含；不得新增对根 `docs/`、根 README 或仓库 checkout 的
  运行时依赖。

本轮实施结果：

- [x] 根 README 从 245 行 / 668 词收短为 101 行 / 262 词；完整安装、配置、CLI 和维护者说明
      改由随包 `USER_GUIDE.md` 与根 `docs/` 承担；
- [x] `SKILL.md` 从 203 行 / 644 词收短为 163 行 / 487 词；首屏逐文件清单和重复升级说明已移除，
      三条铁律、`$WORK` 属主检查、内容人审、登录凭证、同周草稿和完整周流程仍在正文；
- [x] 900px / 360px 本地预览、README audit、Skill validate、116 项单测、公开树、历史扫描
      和完整 smoke 全部通过；隔离安装仍包含 scripts、bootstrap、references 与用户指南；
- [x] 本轮 README / SKILL / docs 改动已完成提交并推送；
- [x] 远端刷新后制作 1280×640 Social preview PNG；
- [~] GitHub Settings 已上传首版 Social preview；字体修正版待替换；
- [ ] skills-hub.ai 仅做多文件安装 PoC，未通过前不公开发布。

#### GitHub 页面元数据是另一项工作

`beautify-github-readme` 优化的是 README，不会自动补齐 GitHub 仓库设置。实施时另行处理：

- [x] About description：一句话说明「工作日志 → 人审 → 氚云草稿 → 人工提交」；
- [x] Topics：`dingtalk`、`h3yun`、`agent-skill`、`claude-code`、`codex-skill`、
  `weekly-report`；
- [~] Social preview：已从验收过的静态视觉系统导出 SVG 源文件与 1280×640 PNG，
  不含真实业务数据；首版已上传，跨平台字体修正版待替换；
- [x] Releases：`v0.3.0` 已挂从 tag 直接导出并逐文件对账的版本化 zip。

这些是 GitHub 外部状态变更；README 预览获批不等于授权修改设置、创建 Release 或推送。

#### 实施与验收门禁

1. 先只读审查 README，再产本地 SVG、渲染预览和 README diff；
2. 预览同时检查 GitHub 宽屏、窄屏、明暗背景、SVG 文字裁切和 alt text；
3. 用户批准视觉方案与阅读顺序后才嵌入 README；提交、推送、Release 和仓库设置分别授权；
4. 合入前至少运行：
   - `python3 <beautify-skill>/scripts/audit_readme.py README.md`
   - `.venv/bin/python tests/test_public_tree.py`
   - `.venv/bin/python tests/scan_history.py`
   - `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
5. 验收标准：首屏无需内部背景即可理解用途与安全边界；最短安装命令仍可复制；图片失效时标题、
   alt text、命令和链接仍能独立表达；仓库中不存在真实组织或个人数据。

### P3 决定：暂不采用氚云 OpenApi（2026-07-28）

> **决定：不采用，不排期。** 保持现有 Playwright 浏览器路径。
> 本节保留完整调研过程，**目的是让将来的人不必重做这次调研**——结论有明确的重估触发
> 条件（见本节末），触发前不要重开这个话题。

**这不是"阻塞在凭据上"，是评估后主动放弃。** 调研（不需要任何凭据）已经把技术面查清：
接口能力齐全、原先记的两个未知都是好消息，但 `IsSubmit` 的形状与本项目最核心的安全承诺
正面冲突，而它要消除的痛点（登录）当天已被 `--login-web` 解决。**换来的不值。**

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
「氚**专** OpenApi 文档」。**这一条至今未验证**——因为按下方决定，现在连问都不该问
（版本若不支持，`EngineSecret` 根本不存在）。重估时这是第一个要确认的前置条件，
排在要密钥之前。

#### 结论（三层分开答，因为答案不同）

| 层 | 技术可行？ | 决定 |
|---|---|---|
| **读**（查记录状态、字段发现） | ✅ 可行，纯收益零风险 | **暂不做**（见下方"为什么连读也不做"） |
| **写**（存草稿） | ⚠️ 技术可行 | **不做**，收益不抵 `IsSubmit` 风险 |
| **附件** | ✅ 有 `UploadAttachment` | 跟着写走，不做 |

**一句话：拦路的不是技术，是 `IsSubmit` 把"存草稿"和"提交"做成了同一个调用的同一个参数——
而这恰好是本项目唯一不能出错的地方。**

不整体迁移的理由不是"做不到"，是**换来的东西不值**：

- 迁移消掉的是**已经解决了的痛**：登录（`--login-web` 已解）、iframe 时序（已修并真机验过）、
  选择器脆（今天能跑）；
- 迁移引入的是**新的、不可逆的风险**：漏传或传错 `IsSubmit` → 周报直接生效提交 →
  记录只能清空不能删。

拿"已经不疼的地方"去换"一个每次写入都要踩准的悬崖"，方向是错的。

**为什么连"只做读"也暂不做**：读路径（`LoadBizObjects`）本身确实是纯收益，但它需要
同一套 `EngineCode` + `EngineSecret`，而**同一套凭据同时具备写和提交能力**。为了给
`--status` 省一次开浏览器，把一份能提交周报的凭据引进 `$WORK`，性价比不成立。
读路径的价值要等到**有别的理由必须引入凭据时**才顺带兑现。

#### 重估触发条件（满足任一条再重开此话题，否则不要重开）

1. **浏览器路径因氚云前端改版反复碎** —— 一个季度内两次以上因选择器/DOM 变更修复，
   说明"选择器脆"从理论风险变成实际维护负担；
2. **`--login-web` 失效或体验退化** —— 登录重新变成主要痛点（当前它是不迁移的核心理由）；
3. **官方文档明确 `IsSubmit` 的类型与默认值，且提供只能写草稿的受限凭据**（或独立的
   只读凭据）—— 那时风险模型才真正变了；
4. **需要无人值守运行**（例如挪到没有图形环境的服务器上跑）—— 届时 Chromium 依赖
   会从"安装大一点"变成硬阻塞。

**触发前的正确动作是什么都不做**，包括不要"先问一下管理员"——问了就会有人想推进。

#### 已保留的资产（重估时直接复用，不必重查）

本节上方的端点、鉴权头、接口清单、`UploadAttachment` 契约、`Status` / `WorkflowInstanceId`
字段可见性、`IsSubmit` 语义与三个风险细节、专业版版本闸——**都是这次查证的结果**，
重估时从这里接着走。

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
