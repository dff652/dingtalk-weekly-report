# 开发 / 测试 / 发版 / 部署 SOP

本文件是**流程骨架与决策表**。具体命令、踩坑和记录一律链回原文档，不在此复制——
四个阶段各写一份 SOP 会重叠漂移，违反本项目自己的单一事实源原则。

| 阶段 | 一句话 | 详情 |
|---|---|---|
| 开发 | 软链装 skill → 改代码即时生效 → 按改动类型选验证 | [MAINTAINER.md](MAINTAINER.md)、[CONTRIBUTING.md](../CONTRIBUTING.md) |
| 测试 | 本地钩子拦 → 提交 → CI 三 job → 人工验收 | [TESTING.md](TESTING.md) |
| 发版 | 改 VERSION + CHANGELOG → CI 绿 → 打 tag → 打包 | [PUBLISHING.md](PUBLISHING.md#版本与发版) |
| 部署 | 用户装 skill → bootstrap → configure → 登录 → keepalive | [../README.md](../README.md)、技能包 `USER_GUIDE.md` |
| GitHub 项目页 | README 分层 → SVG 验收 → 元数据发布 → Hub 核验 | [GITHUB_PROJECT_PAGE_SOP.md](GITHUB_PROJECT_PAGE_SOP.md) |

## 开发

1. 克隆后装 pre-push 钩子（`ln -sf ../../hooks/pre-push .git/hooks/pre-push`）并设 noreply 提交身份。
2. `bash install.sh --link` 把 skill 软链进 agent 目录，改代码即时生效。
3. 动手前读 [REVIEW.md](REVIEW.md) 第二节**不变量清单**与第三节缺陷清单。
4. 分支：目前单人维护，直接推 `main`；外部贡献走 PR。改动大或想要独立评审时开分支。

## 测试

### 改动类型 → 必跑验证

| 改了什么 | 必跑 |
|---|---|
| **任何改动** | pre-push 钩子（历史脱敏 + 工作树断言）+ CI 三 job |
| `fill_form.py` 的 DOM / 选择器 | `bash tests/run_mock_test.sh` **必跑**；再对真实表单跑 `--dump` 或不带 `--draft` 的预览 |
| 校验逻辑（`dtwr_validation.py` / `dtwr_fields.py`） | 单元测试 + `run_mock_test.sh` |
| **增删配置键** | 单元测试 + `configure.py --check`，并同步四处：`dtwr_fields.py`、`configure.py::FIELD_SPECS`、`references/FIELDS.md`、`assets/config.example.json` |
| 附件 / xlsx 生成 | 单元测试 + 实跑 `gen_attachment.py` + **打开产物目视**（结构对不对测试断不出来） |
| 安装 / bootstrap 脚本 | `bash tests/run_full_acceptance.sh`（隔离 HOME） |
| 打包 / 发布链路 | `run_smoke.sh` + `pack-skill.sh` + push 后 `run_release_acceptance.sh` |
| 版本号 / CHANGELOG | 单元测试（`test_version.py` 守一致性） |
| README / SVG / Social preview | `tests/test_readme_assets.py` + README audit + 900px / 360px 浏览器预览；完整流程见 [GITHUB_PROJECT_PAGE_SOP.md](GITHUB_PROJECT_PAGE_SOP.md) |
| GitHub Issue / `@AI` 自动化 | 外部 `@AI` 不触发代码修改；如启用辅助，仅由维护者门控后在 Issue 回复，文档固化另行批准。权限与两阶段流程见 [GITHUB_PROJECT_PAGE_SOP.md](GITHUB_PROJECT_PAGE_SOP.md#github-issue-中的-ai-自动触发) |
| **点击 / 端点 / 配置键**（碰到"这个动作能不能做"的边界） | `tests/test_invariants.py` 守「无提交能力」。它红了别急着改测试——**先确认承诺是不是真的被削弱了** |
| 文档 | pre-push（脱敏）；判断 [docs/README.md](README.md) 索引是否要更新 |

三个验收层级**不得互相顶替**，判据见 [TESTING.md](TESTING.md) 末尾。

跑测试用 `$WORK/.venv/bin/python`，**不要用裸 `python3`**——后者缺 playwright，
`test_fill_form_logic` 会在 loader 阶段整文件不被计数，且红得像"环境问题"容易被跳过。
**判读时先看 `Ran N tests` 的 N 对不对，再看 OK/FAILED**（TESTING 踩坑 20）。

### 零真机里程的分支必然带 bug

2026-07-28 首次真机跑登录与编辑既有草稿，**一天内连撞七个 bug**，其中六个是同一种毛病：
**只做了动作、没做正向确认**（点了登录就当登录成功、传了文件就当上传完成、点了暂存就当保存成功）。

根因不是水平问题，是**覆盖问题**：维护者一直用 auth 链接登录、一直走「新增」路径，
扫码分支和编辑分支零里程。仿真表单测不到这些——它没有登录、没有受控上传组件、
没有 iframe 生命周期。

两条可迁移的规则：

1. **"点了"不等于"成了"**：凡跨进程/跨网络的动作，都要回读一个**正向证据**再往下走；
   拿不到证据宁可中止，不要靠"没看到失败"推断成功。
2. **没跑过真机的分支要当成未实现**，不要因为"代码看着对"就写进文档当能力宣传。

### 什么测不出来

仿真表单是同步的，测不出真实表单的异步行为（上传完成、下拉渲染时序）。附件上传校验的第二层
证据（等页面出现附件名）**只能在真实氚云上验证**，仿真只覆盖第一层。真机相关项一律走
[MANUAL_ACCEPTANCE.md](MANUAL_ACCEPTANCE.md)。

## 发版

顺序与门禁见 [PUBLISHING.md](PUBLISHING.md#版本与发版)。检查单：

| # | 项 | 自动？ |
|---|---|---|
| 1 | 单元测试 | ✅ CI |
| 2 | 仿真表单 e2e | ✅ CI |
| 3 | 历史脱敏扫描 | ✅ pre-push + CI |
| 4 | VERSION 与 CHANGELOG 条目一致 | ✅ 测试守一致性，**条目内容人工写** |
| 5 | tag `v<VERSION>` 已打且工作区干净 | ✅ `pack-skill.sh` 门禁（不满足则产物标 `-dev.<sha>`） |
| 6 | 隔离 HOME 全量验收 `run_full_acceptance.sh` | ❌ 人工本地跑 |
| 7 | 远端发行验收 `run_release_acceptance.sh` | ❌ 人工，push 后跑 |
| 8 | 真实氚云人工验收 | ❌ 只能人工，见 [MANUAL_ACCEPTANCE.md](MANUAL_ACCEPTANCE.md) |

**行为变更必须写进 CHANGELOG。** 判据：升级后用户的操作结果会不会变。例如 0.1.0 把附件上传从
「等 4 秒就继续」改成「等不到证据即中止」——不写清楚，用户升级后会莫名其妙被卡住。

## 部署（用户侧）与回滚

安装、bootstrap、配置、登录、keepalive、升级见 [../README.md](../README.md) 与技能包
`USER_GUIDE.md`。回滚按症状分流：

| 症状 | 回滚动作 |
|---|---|
| 维护者本机（软链安装）新代码坏了 | `git checkout v<上一版>` 或 `git revert`；软链即时生效，无需重装 |
| 用户经 zip 安装的版本坏了 | 解压上一版 zip → `bash install.sh --force`；`$WORK` 与登录态不受影响 |
| 用户经 `npx skills` 安装的版本坏了 | **见下方缺口**；当前只能等维护者发 patch 版，或改用 zip 装历史版本 |
| 运行态坏了（venv / Chromium / 登录态） | 不是代码问题：`bash bootstrap.sh --force-venv` + 重新登录 |
| 配置被改坏 | `configure.py` 每次写入都留 `config.json.bak`，覆盖回去即可 |
| 落了内容错误的草稿 | 修正周报后重跑，工具默认更新目标周草稿；必要时由用户按钉钉实际权限手工编辑或清空。不要假设记录可以删除；工具无提交能力，错误不会变成已提交的申报 |

**已知缺口（⑪）**：`npx skills` 没有版本 pin，用户装到坏版本时无法自助退回。这是上游生态限制，
本项目补不了，只能降低影响：

- 每个版本的 zip 都按版本号命名且可归档，用户手里若留有上一版 zip 即可自救；
- 把版本化 zip 挂到 GitHub Release 作为可下载的历史归档，是最直接的补法——**尚未做**，
  待定；
- 回滚永远不影响 `$WORK`：代码与运行数据分离，退版本不会丢配置、周报或登录态。

## 用户旅程 SOP（安装 → 使用 → 登录 → 确认）

工程流程见上；这一节是**用户侧**的一条线。每一步都标明「谁做」和「卡住时怎么办」。

| # | 步骤 | 谁做 | 卡住时 |
|---|---|---|---|
| 1 | `npx skills add dff652/dingtalk-weekly-report` | 用户/AI | 无 Node 走 zip + `install.sh` |
| 2 | 调用 `/dingtalk-weekly-report`，首次会引导 bootstrap | AI | 或手动 `bash bootstrap.sh` |
| 3 | **取表单元数据**（十个字段 id + 枚举） | 用户 | `--dump-record N` 自动发现 → `configure.py --from-discovery` 确认写入 |
| 4 | **登录** | **只能用户** | 见下方登录决策表 |
| 5 | 装 keepalive cron（可选但强烈建议） | 用户 | 日志路径**必须绝对**；装完次日务必确认日志真有新行 |
| 6 | 每周：内容 → 人审 → 附件 → 预览 → 落草稿 | AI 带做 | 先跑 `--status` |
| 7 | **钉钉里核对并提交** | **只能用户** | 工具无提交能力，这是设计 |

**任何一步不知道该干什么，先跑 `--status`** —— 它读真实状态直接给下一步，不用回来翻文档。

### 登录方式决策

| 情况 | 用哪个 | 说明 |
|---|---|---|
| 有浏览器可开本地端口（含 VSCode 远程） | **`--login-web`** | 网页显示二维码 + 实时状态，最省事 |
| 只能看文件 | `--login` | 扫 `$WORK/output/shots/login.png`，图每 2.5 秒刷新 |
| 无图形界面 | `--login-url` | 「打印**内部**二维码」解出链接，本人在终端隐藏输入 |
| 想用短信 | `--login-sms` | **可能被滑块验证码拦下**，届时会 fail-loud 提示改扫码 |

三条硬规矩：

1. **二维码必须扫工具生成的那一张**。图可以下载到手机、投屏、拍屏幕；但**在自己浏览器打开
   登录页扫码无效**——那是 OAuth ticket，绑定生成它的浏览器实例，会话会落到你的浏览器。
2. **auth 链接（`entry/auth?token=`）48 小时内等同账号**，只贴进 `--login-url` 的隐藏提示，
   不发聊天、不进命令行参数。「打印**外链**二维码」给的是公开表单地址，登不了。
3. **登录态不跨设备复制**，每台设备各自登录。

### 给用户的提示（工具已内建，不必背）

- `--status`：不知道下一步时先跑
- 落草稿前**先跑一次不带 `--draft` 的预览**，核对 `20-filled-review.png`
- 同周**不需要先删旧草稿**：工具默认改目标周的既有草稿（两道护栏：状态必须「草稿」、
  开始日期必须等于目标周周一）
- 工时口径：配了 `daily_hours` 后**会议含在每日总工时内**，超日/周上限会被拦；
  确有加班要显式确认并调整配置
- 失败时看 `output/shots/99-error.png` **和** `output/fill_form.log`（后者才有"第几行开始不对"）

## 与运行期的边界

本文件只覆盖**工程流程**。每周实际填报的执行流程是另一条线，见技能包 `SKILL.md`（Agent SOP）
与 `references/CONTRACT.md`（输入、缺失处理、输出与失败契约）。
