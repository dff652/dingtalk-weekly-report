# 开发 / 测试 / 发版 / 部署 SOP

本文件是**流程骨架与决策表**。具体命令、踩坑和记录一律链回原文档，不在此复制——
四个阶段各写一份 SOP 会重叠漂移，违反本项目自己的单一事实源原则。

| 阶段 | 一句话 | 详情 |
|---|---|---|
| 开发 | 软链装 skill → 改代码即时生效 → 按改动类型选验证 | [MAINTAINER.md](MAINTAINER.md)、[CONTRIBUTING.md](../CONTRIBUTING.md) |
| 测试 | 本地钩子拦 → 提交 → CI 三 job → 人工验收 | [TESTING.md](TESTING.md) |
| 发版 | 改 VERSION + CHANGELOG → CI 绿 → 打 tag → 打包 | [PUBLISHING.md](PUBLISHING.md#版本与发版) |
| 部署 | 用户装 skill → bootstrap → configure → 登录 → keepalive | [../README.md](../README.md)、技能包 `USER_GUIDE.md` |

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
| 文档 | pre-push（脱敏）；判断 [docs/README.md](README.md) 索引是否要更新 |

三个验收层级**不得互相顶替**，判据见 [TESTING.md](TESTING.md) 末尾。

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
| 落了内容错误的草稿 | 用户在钉钉删掉草稿。工具无提交能力，错误不会变成已提交的申报 |

**已知缺口（⑪）**：`npx skills` 没有版本 pin，用户装到坏版本时无法自助退回。这是上游生态限制，
本项目补不了，只能降低影响：

- 每个版本的 zip 都按版本号命名且可归档，用户手里若留有上一版 zip 即可自救；
- 把版本化 zip 挂到 GitHub Release 作为可下载的历史归档，是最直接的补法——**尚未做**，
  待定；
- 回滚永远不影响 `$WORK`：代码与运行数据分离，退版本不会丢配置、周报或登录态。

## 与运行期的边界

本文件只覆盖**工程流程**。每周实际填报的执行流程是另一条线，见技能包 `SKILL.md`（Agent SOP）
与 `references/CONTRACT.md`（输入、缺失处理、输出与失败契约）。
