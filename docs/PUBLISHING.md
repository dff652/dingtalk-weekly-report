# skills.sh 分发与开源发布

## 分发模型

本项目采用 Apache License 2.0，仓库根与 Skill 安装目录均携带 `LICENSE`。skills CLI 只安装
`$SKILL`；`bootstrap.sh` / `bootstrap.ps1` 另行创建每用户私有 `$WORK`。

```text
公开仓库 / $SKILL              每用户私有 $WORK
---------------------------   --------------------------------
通用脚本、空白模板、文档       config.json、weeks/、output/、.venv/
Apache-2.0                     ~/.config/dtwr/ 保存指针和登录态
```

真实表单 URL、组件 ID、按钮文本、枚举、项目、周报、截图和登录态不得进入公开仓库、issue、
日志或发布附件。

## 许可证选择：Apache-2.0 vs MIT

**决定（2026-07-25）：维持 Apache-2.0，不换 MIT。** 理由按对本项目的实际权重排：

1. **§5 贡献条款 = 不需要 CLA（权重最高）**。Apache-2.0 明写"任何有意提交的贡献默认按本许可证
   授出"。本项目要挂到 skills hub 被陌生人安装，就会收到陌生人的 PR。MIT 无任何入站贡献条款，
   只能靠 GitHub ToS 的 inbound=outbound 兜底；Apache 把它写进许可证，省掉未来"要么建 CLA、
   要么心里没底"的两难。
2. **§3 专利授权 + 反诉终止**。本项目没有可专利的发明，此条**实质**价值不大，但**信号**价值不小：
   工具会被其他公司的员工装进公司机器去操作其 HR 系统，企业 OSPO 审"能不能装"时，显式专利授权
   是加分项，MIT 的专利地位靠默示推定。成本为零的保险。
3. **§4(b) 要求改动方标注"已修改"**。对本项目有真实意义：核心卖点是"只落草稿、永不提交、内容
   必人审"。有人 fork 后拆掉 `--draft` 闸门直接提交、还挂着本项目名分发——Apache 下属于违约，
   MIT 下无从追究。代人向 HR 填报的工具，"改了必须说"不是形式主义。
4. **§6 商标条款**明确不授予名称/标识使用权。技能名要在 hub 上被搜索发现，名字本身是资产；
   MIT 对商标只字不提。
5. **生态一致**。唯一运行时依赖 Playwright 本身即 Apache-2.0，skills / agent 工具链主流亦然，
   下游合规审查零摩擦。

MIT 的两个常见优势在此不成立：

- *简短*：`LICENSE` 11KB 比多数脚本都大，但技能包经 zip / `npx skills` 分发，多 11KB 无人感知。
  该理由只在单文件 gist 场景成立。
- *GPLv2 兼容*：Apache-2.0 与 GPLv2-only 不兼容（只兼容 GPLv3+）。但本项目是自包含独立技能包，
  被吸收进 GPLv2-only 项目的概率约等于零。

**重估触发**：若目标改为"让 `xlsxlite.py` 这类小组件被尽可能多的项目随手抄走"，MIT 的零摩擦
更优。当前目标是"整包被安装、被 fork 时行为约束可追溯"，Apache 更贴。

### 配套（2026-07-25 完成）

- [x] 版权主体写在 `README.md`（`Copyright 2026 dff652`）。`LICENSE` 附录保留 Apache 原文不动
      （那是给使用者抄的模板，不是待填空）。**刻意用 GitHub handle 而非真实姓名**——与提交身份
      统一用 noreply 是同一个决定，不把真实身份重新放回公开仓。
- [x] 全部分发脚本加 `# SPDX-License-Identifier: Apache-2.0`（16 个文件；shebang 仍在第一行）。
- [x] `tests/test_version.py` 断言分发脚本都带 SPDX 头，且 shebang 没被挤到第二行。

## 版本与发版

版本号**单一事实源** = `skills/dingtalk-weekly-report/VERSION`。
（刻意不放 `SKILL.md` frontmatter：本机 agent 入口是软链到仓库的，往 frontmatter 加非标准键
一旦被某个 loader 挑刺就会弄坏正在用的 skill。日后若要让 `npx skills` 显示版本，再提升到
frontmatter，并加测试守住两处一致。）

约束由 `tests/test_version.py` 强制：`VERSION` 必须是 semver，且 **CHANGELOG 最新的已发布条目
必须与之一致**——改了版本号就得写变更记录，否则「发了新行为却没人知道变了什么」。

git tag 一致性不在单测里断言（开发期先改 VERSION、发布时才打 tag，中间必然不一致），改由
`pack-skill.sh` 在发版时门禁：**未打 `v<VERSION>` tag 或工作区不干净，产物自动命名为
`-dev.<sha>`，不会冒充发行版**。

发版顺序：

1. 改 `VERSION` + 在 CHANGELOG 的 `## [Unreleased]` 下写好条目，改成 `## [x.y.z] - YYYY-MM-DD`；
2. 提交并推送，等 CI 三个 job 全绿；
3. `git tag -a vx.y.z -m "..." && git push origin vx.y.z`；
4. `bash pack-skill.sh` —— 产物名不带 `-dev.` 才算发行物；
5. 按下节「发布门禁」复验。

## skills.sh 发布方式

skills.sh 没有单独的上传命令。公开发布流程是：

1. 将含合法 `SKILL.md` 的仓库推送到公开 GitHub；
2. `npx skills add owner/repo --list` 验证发现；
3. 用隔离 HOME 完成安装、bootstrap 和仿真验收；
4. 等待 skills.sh 根据安装遥测建立或更新索引。

安装示例：

```bash
npx skills add dff652/dingtalk-weekly-report \
  --skill dingtalk-weekly-report \
  --agent claude-code --agent codex \
  --global --yes --copy
```

## 历史泄露处置（已发生）

当前工作树已把运行数据迁出仓库并参数化表单元数据，但旧 Git 历史包含真实个人配置、周报、
组织项目与表单标识。普通删除提交不能清除历史对象。

**2026-07-25 核实：仓库已是 PUBLIC，上述历史对象公网可直取（实测 HTTP 200）。** 这不再是
"发布前阻断"，而是**已发生的泄露**。暴露窗口约 4 天（仓库创建于 2026-07-21），fork / star /
watcher 均为 0。**无凭证泄露**：token、`state.json`、cookie、截图从未入库，没有需要立即轮换
的凭证。泄露内容清单见 [REVIEW.md](REVIEW.md#四历史泄露已经发生不是待办)。

### 执行记录（2026-07-25）

| 步骤 | 状态 |
|---|---|
| 离线备份（`git bundle --all` + `--mirror` 克隆，已校验"完整历史"） | ✅ 完成 |
| 文档内敏感 commit 标识清除（GC 前等同取回路径） | ✅ 完成 |
| 历史重建为单一 orphan 提交（原 36 提交中 35 个命中，部分重写不可靠） | ✅ 完成 |
| 提交身份统一为 GitHub noreply（公司邮箱不再出现在公开仓） | ✅ 完成 |
| `git push --force` | ✅ 完成 |
| 公网 fresh clone 复验：1 提交、身份正确、脱敏扫描 0 命中 | ✅ 完成 |
| **回收弃置对象** —— 实测旧 commit 与旧文件**仍可按 hash 取回（HTTP 200）** | ❌ **未完成** |
| 防复发门禁（CI 扫历史，不只扫工作树） | ❌ 未完成 |

**未完成项是关键项**：force push 只改变了默认分支指向，GitHub 仍保留弃置对象且公开可寻址。
在完成回收前，本次重写的实际效果仅限于"新克隆者拿不到"。

两条回收路径：

- **删库重建**（本仓推荐）：删除仓库后同名重建再推送，弃置对象立即随仓库一并消失，可自行验证、
  无需等待。适用前提是仓库无可损失的附属物——本仓 fork / star / watcher / tag / release /
  issue / PR 均为 0，wiki 未建，**删除不损失任何东西**，且 URL 与安装命令不变。
- **联系 GitHub Support**：以仓库所有者身份请求清除 force push 后的弃置对象与缓存视图。
  不删仓，但需等待人工处理，且完成时点不由自己掌握。

原始处置顺序（每一步都需要单独批准，历史重写前必须先建离线备份）：

1. **止血决策**：转回 private，或接受暴露继续公开。转 private 只阻断新增抓取，不撤回已发生的
   暴露，也不影响已有克隆与第三方镜像。
2. **离线备份**整个仓库（含全部 ref 与 reflog），重写前不可跳过。
3. **历史重写**：36 个提交，规模很小，`git filter-repo` 一次可完成——删除历史 `config.json`、
   `weeks/`、含真实值的 `FIELDS.md` / `README.md` 版本。
4. **force push** 并通知任何已有克隆作废。
5. **请求 GitHub 清除弃置对象**：force push 后，被弃置的 commit 在 GitHub 上**仍可按 hash 直接
   访问**，必须另行联系 GitHub Support 请求 GC，否则第 3、4 步等于没做。这一步最常被漏。
6. **组织侧知会**：表单标识与内部项目/周报内容曾公开，按所在组织的安全合规要求判断是否上报。
7. **复跑全部发布门禁**，不得带 `DTWR_ALLOW_DIRTY=1` 或本地 `DTWR_RELEASE_REMOTE`。

历史重写是破坏性操作，不属于普通发布命令。

## 后续发布阻断

在完成以下动作前，不得宣布公开发行完成：

- 上节「历史泄露处置」7 步全部完成，且确认远端安装只包含脱敏版本；
- 确认有权以 Apache-2.0 发布全部剩余代码和文档。

## 发布门禁

本地候选：

```bash
bash tests/run_smoke.sh
bash tests/run_full_acceptance.sh
```

push 后：

```bash
bash tests/run_release_acceptance.sh
```

必须同时满足：

- 当前树脱敏扫描通过，未跟踪根 `config.json`、`weeks/` 或 `output/`；
- 根 `LICENSE` 与 Skill 内 `LICENSE` 完全一致；
- 单元、打包、隔离安装、附件、浏览器仿真草稿全部通过；
- skills CLI 安装输出无未处理的 Critical/High；
- 真实个人配置、登录和草稿按 `MANUAL_ACCEPTANCE.md` 单独人工验收。

正式发行验收不得设置 `DTWR_ALLOW_DIRTY=1`，也不得把 `DTWR_RELEASE_REMOTE` 指向本地仓库。
审计平台可能缓存旧提交；推送修复后需等待重扫并重新安装验证。
