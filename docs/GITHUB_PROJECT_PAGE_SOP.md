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
