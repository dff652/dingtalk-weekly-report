# GitHub 项目页与 README 维护 SOP

本文件固化 README 信息分层、视觉资产生产、GitHub 项目页发布和 Skills Hub 分发核验。
它记录可重复执行的流程与验收标准，不记录某次会话的操作流水。

相关事实源：

- 视觉规则与当前资产规格：[MAINTAINER.md](MAINTAINER.md#github-项目页--readme-优化决定2026-07-30)
- Skill 打包、版本与 Hub 决策：[PUBLISHING.md](PUBLISHING.md)
- 通用测试与发版骨架：[SOP.md](SOP.md)
- 用户可见的最终入口：[../README.md](../README.md)

## 适用范围与授权边界

以下四类工作必须分开判断，前一项获批不自动授权后一项：

| 工作 | 默认可做 | 需要单独授权 |
|---|---|---|
| 只读审查 README、SVG、仓库元数据 | 是 | — |
| 修改 README、SVG、PNG 和项目文档 | 用户要求优化或修复后 | — |
| commit / push | 否 | 每次明确授权 |
| 修改 About、Topics、Homepage、Social preview | 否 | 仓库设置授权 |
| 创建或修改 GitHub Release | 否 | 发布授权 |
| 在第三方 Hub 建账号、publish、下架 | 否 | 对应外部状态变更授权 |

真实表单截图、字段 ID、租户信息、人员信息、周报内容和登录上下文不得用于公开项目页素材。

## SOP 1：README 信息架构与文档分层

### 触发条件

- README 过长、首屏无法说明项目用途；
- `SKILL.md` 在 Hub 页面展示的信息过密；
- 安装、运行、维护说明出现重复或漂移；
- 新增能力后不知道应该写到哪个文档。

### 分层判定

| 内容 | 单一落点 |
|---|---|
| 价值、主要证据、安全边界、最短安装、限制、文档入口 | 根 `README.md` |
| Agent 触发条件、运行步骤、硬规则、失败停止条件 | `skills/.../SKILL.md` |
| 完整安装、配置、登录、CLI、升级、FAQ | `skills/.../USER_GUIDE.md` |
| Agent 按需读取的输入输出与字段契约 | `skills/.../references/` |
| 测试证据、评审、发版、长期决策和事故复盘 | 根 `docs/` |

根 README 不是 Skill 安装输入；根 `docs/` 也不会随 Skill 安装。运行必需信息不得只存在于
这两个位置。移动内容后，安装目录必须仍然自包含。

### 执行顺序

1. 只读盘点 README、`SKILL.md`、`USER_GUIDE.md` 和相关 `docs/`，列出重复与缺失内容。
2. 写清五个设计输入：受众、一句话价值、主要证据、第一次成功动作、视觉主题。
3. 先调整纯 Markdown 阅读顺序，再判断哪些关系确实需要 SVG；命令、链接和长说明不得图片化。
4. 保留可验证的限制与安全边界，不用视觉文案覆盖单租户验证、平台兼容等真实边界。
5. 检查所有下沉链接；图片加载失败时，标题、alt、正文和命令仍须独立表达完整含义。
6. 先展示本地预览与 diff，得到授权后再提交或推送。

### 验收

- 首屏无需项目背景即可回答“做什么、不会做什么、如何第一次使用”；
- 最短安装命令仍可复制；
- `SKILL.md` 本身保留运行闸门，不是只剩指向外部文档的链接；
- 根 README、Skill 包内文档和维护文档没有互相复制整段正文；
- 900px 与 360px 内容宽度均可阅读。

## SOP 2：README SVG 与 Social preview 生产

### 资产职责

| 资产 | 固定画布 | 发布形态 |
|---|---:|---|
| `assets/readme/hero.svg` | 1200×400 | README 内嵌 SVG |
| `assets/readme/workflow.svg` | 1200×520 | README 内嵌 SVG |
| `assets/readme/social-preview.svg` | 1280×640 | 可编辑源 |
| `assets/readme/social-preview.png` | 1280×640 | GitHub Settings 上传成品 |

字体、许可色板、字重、安全边距、ARIA 和禁用特性以
[MAINTAINER.md 的视觉资产规范](MAINTAINER.md#readme-视觉资产规范)为单一事实源。

### 执行顺序

1. 从仓库真实价值、流程或产物提取视觉信息，不使用通用装饰模板。
2. 默认使用纯静态 SVG；只有真实截图或复杂合成确实更能说明项目时，才另行评估位图。
3. 所有精确文案保留为 SVG 文本或 Markdown，不把文字烘焙进生成式图片。
4. 使用明确的中英文字体栈和真实存在的 `400` / `700` 字重，避免逐字 fallback 与合成字重。
5. 对每一组前景色/背景色复验对比度；正文和关键标签不低于 4.5:1。
6. 用浏览器读取实际字体和文本边界，确认没有越出 `viewBox`；不能只看源代码坐标。
7. 在 900px 和 360px 内容宽度目视检查。窄屏不可读的关键说明应拆图或移回相邻 Markdown。
8. SVG 定稿后再导出 Social preview PNG；PNG 必须小于 1MB，且与 SVG 源同一版本。
9. 更新或新增 `tests/test_readme_assets.py` 断言，防止尺寸、字体、色板、ARIA 和安全特性回退。

### 必跑门禁

```bash
python3 /path/to/beautify-github-readme/scripts/audit_readme.py README.md
.venv/bin/python -m unittest tests.test_readme_assets -v
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python tests/test_public_tree.py
.venv/bin/python tests/scan_history.py
git diff --check
```

涉及 README 信息架构、安装入口或 Skill 文档分层时，追加：

```bash
bash tests/run_smoke.sh
```

自动测试不能替代浏览器实际字体、文本边界和宽窄屏目视检查。

## SOP 3：GitHub 项目页元数据发布

README 合入不等于 GitHub 项目页已完成。按以下顺序分别处理：

1. **About description**：一句话说明输入、人工审核、输出草稿和最终人工提交。
2. **Topics**：只选真实、稳定、能帮助检索的技术与场景词。
3. **Homepage**：指向当前主分发页；本项目使用 skills.sh 页面。
4. **Social preview**：上传已验收的 1280×640 PNG，不直接上传未渲染验证的 SVG。
5. **Release**：只按 [PUBLISHING.md 的版本与发版流程](PUBLISHING.md#版本与发版)创建。

发布前后各保存一次只读快照：

```bash
gh repo view dff652/dingtalk-weekly-report --json description,homepageUrl,repositoryTopics,usesCustomOpenGraphImage,latestRelease
```

Social preview 目前必须在 GitHub 网页
`Settings → Social preview → Edit → Upload an image` 操作。上传后至少确认：

- 页面显示的是本次 PNG，而不是浏览器缓存的旧图；
- `usesCustomOpenGraphImage` 为 `true`；
- 分享预览无敏感数据，裁切后标题、价值句和核心流程仍完整。

若 SVG 或 PNG 后续修正，README 中的 SVG 会随 push 更新，但 GitHub 已上传的 Social preview
不会自动同步，必须重新上传 PNG。维护文档在替换完成前应明确写“修正版待替换”。

## SOP 4：Skills Hub 分发与可发现性核验

### skills.sh 主链

1. GitHub 仓库中的 Skill 目录是事实源，不存在单独上传动作。
2. 用 `npx skills add OWNER/REPO --list` 确认发现。
3. 运行 `bash tests/run_release_acceptance.sh`，验证远端下载、完整目录安装、bootstrap、依赖和
   mock 草稿链路。
4. 等索引刷新后检查技能页；页面正文来自 `SKILL.md`，不是根 README。
5. installs 包含维护者自己的发行验收，不得表述为独立用户数或增长证据。

### 其他 Hub

不同 Hub 是独立注册中心，搜索不到不等于 GitHub 或 skills.sh 发布失败。对多文件 Skill，
任何新 Hub 上架前必须先做隔离安装 PoC，并同时满足：

- `scripts/`、`references/`、bootstrap、模板、锁文件和许可证均被完整安装；
- 安装副本能通过配置校验、脚本 import 和 mock 草稿 smoke；
- 元数据不会破坏 Claude Code、Codex 或 skills.sh 的现有 loader；
- 更新、回滚、下架和 GitHub 同步语义明确。

任一项不满足时保持“不发布”，不要为了可搜索而把运行代码内联进 `SKILL.md`。

## GitHub Issue 中的 `@AI` 自动触发

Issue 或评论中的 `@claude` 只是文本提及，不会连接到维护者本机已经打开的 Claude Code、
Codex 或 IDE 会话。自动执行需要仓库另行安装服务端集成。

Issue #1 提交 `@claude` 时，本仓只有 `.github/workflows/ci.yml`，没有监听
`issue_comment` 的 AI workflow，因此没有产生 workflow run。后来增加的
`.github/workflows/issue-assistance.yml` 也只在新建 Issue 时发送固定回执，不监听评论、
不调用模型、不会自动改代码。

按 [Claude Code GitHub Actions 官方文档](https://code.claude.com/docs/en/github-actions)，
启用至少需要：

1. 仓库管理员安装 Claude GitHub App；
2. 将 `ANTHROPIC_API_KEY` 放入 GitHub Actions Secret，禁止写进仓库；
3. 在默认分支加入监听 `issue_comment: created` 的 workflow，并调用
   `anthropics/claude-code-action@v1`；
4. 授予所需的 Contents、Issues、Pull requests 权限；
5. 用真实 `@claude` 评论验证 workflow、回复、分支、PR 和 CI。

这是独立外部状态变更：会增加 GitHub App 写权限、Actions/API 成本和第三方 Issue 的
prompt-injection 面，必须单独授权。公开仓推荐只允许维护者触发，或先由维护者添加
`ai-approved` 标签；AI 只能提交 PR，禁止自动合并。外部用户的单独 `@claude` 不应直接取得
仓库写入和付费调用能力。

### 当前决定：只自动回执，AI 处理由维护者启动

本项目不允许外部用户通过 Issue、评论或 `@AI` 直接触发模型调用或代码修改。当前自动化只做：

- `issues: opened` 时用短期 `GITHUB_TOKEN` 发布固定安全回执；
- workflow 默认 `permissions: {}`，回执 job 只有 `issues: write`；
- 不 checkout 仓库，不读取 Secret，不监听 `issue_comment`，不创建分支 / PR，不自动关单。

Claude Issue 自动排查方案已经完成技术评估：可由仓库所有者添加 `ai-triage` 标签，以
`contents: read`、`issues: write` 运行无 tools 的 Messages API 文本分析，并更新一条机器人
评论；输出还应中和半角 `@`，防止意外提及用户。但该方案需要独立的 Anthropic Console
API Key 与计费，收益不足以覆盖当前低 Issue 量下的 Secret 管理、费用和 prompt-injection
治理成本，**当前不启用、不配置 `ANTHROPIC_API_KEY`、不保留模型 job**。仅当 Issue 量明显
增加、人工排查成为持续负担且有明确预算时重估。

“写项目文档”仍属于仓库内容变更。Issue 回复可以提出“建议固化内容”，但必须由维护者另行
批准后在本地更新；不允许回复 workflow 直接写文档。

### Codex 处理 Issue：当前采用的人工门控 SOP

OpenAI 官方的 GitHub `@codex` 集成目前面向 PR review 与 PR 分支修复；官方文档没有把公开
Issue 评论列为同等触发入口。`openai/codex-action@v1` 可以在自定义 GitHub Actions 中运行，
但 CI 仍需要 `OPENAI_API_KEY`；官方还明确不建议在公开开源仓中把个人 ChatGPT/Codex 登录态
作为 CI 凭据。因此 Codex 不是“免 API Key 的 Issue 自动机器人”替代品：

- [Codex code review in GitHub](https://learn.chatgpt.com/docs/third-party/github)
- [Codex GitHub Action](https://learn.chatgpt.com/docs/github-action)
- [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)

当前使用已有本地 Codex 会话和 GitHub CLI，按 Issue 逐项人工启动：

1. 用户要求“查看并处理 Issue #N”；Codex 运行
   `gh issue view N --repo dff652/dingtalk-weekly-report --comments`，只读取得原始事实。
2. Codex 先检查代码、文档、测试和当前工作区，给出根因、方案、风险与验收标准；此阶段不回复
   Issue、不改外部状态。
3. 用户批准后，Codex 在本地做最小实现、补测试并运行项目门禁；是否更新文档由结论决定。
4. Codex 汇报 diff 与验证结果；commit、push、Issue 回复和关闭分别按用户授权执行。
5. 回复只写已经完成且可验证的事实；修复尚未推送时必须注明，合并 / 推送完成后再关闭。

授权方式与当前日常使用 Codex 完全一致：

- “查看 / 评估 / 给方案”只授权只读检查，不授权修改文件或外部状态；
- “同意方案 / 按方案执行”授权本地完成该方案必要的代码、测试和文档改动，不需要逐文件确认；
- “提交”只授权创建本地 git commit，不自动包含 push；
- “push”授权推送已确认提交；
- “回复 / 关闭 Issue”属于 GitHub 外部状态变更，必须明确授权，且关闭前要确认修复已经推送；
- 用户中途变更方向时，以最新指令为准，未获批的后续动作立即停止。

该流程使用当前交互式 Codex 授权，不新增仓库 API Secret，也不会因外部 Issue 内容自动消耗
模型额度。若未来 Issue 量达到需要无人值守处理的程度，再单独评估
`openai/codex-action@v1` 的 `read-only` sandbox、维护者 allowlist 和 PR-only 写入分层。

## 提交、发布后验证与回滚

1. 提交前检查 `git diff --check`、完整 diff 和工作区范围，只暂存本任务文件。
2. 获得授权后 commit / push；不得绕过 pre-push 钩子。
3. 等 GitHub Actions 完成，逐 job 确认成功，并检查 annotations，而不只看总状态为绿色。
4. 确认本地 `HEAD`、远端分支和工作区状态一致。
5. README / SVG 回滚使用新的 revert 提交；不重写已公开历史。
6. About、Topics、Homepage 回滚为发布前快照；Social preview 重新上传上一个已验收 PNG。
7. Release 和第三方 Hub 属于独立外部状态；不要因代码回滚而擅自删除，按
   [PUBLISHING.md](PUBLISHING.md)和平台规则另行处置。

## 完成定义

一次 GitHub 项目页维护只有同时满足以下条件才算完成：

- 内容层级正确，Skill 安装闭包没有被 README 精简破坏；
- SVG 源、PNG 派生物、README 引用和维护规范一致；
- 自动测试、浏览器宽窄屏、实际字体与文本边界全部通过；
- 所有获批的 GitHub 元数据已验证，未获批的外部动作保持未执行；
- CI 全绿且无 annotations，远端提交与本地一致；
- 尚需人工执行的 Social preview 或 Hub 操作在文档中明确标记，而不是口头遗留。
