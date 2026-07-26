# 变更记录

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循
[语义化版本](https://semver.org/lang/zh-CN/)。1.0.0 之前，次版本号的变化即可能带来
不兼容的行为改变。

版本号的**单一事实源**是 `skills/dingtalk-weekly-report/VERSION`；本文件最新的已发布条目
必须与它一致（`tests/test_version.py` 守住这一点）。

## [Unreleased]

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
- `--dump` / `--login` 不再要求完整配置通过校验：`--dump` 只需 `form_texts.add_row` 与
  `start_date_label`。此前它要求字段 id 已配好才肯运行，而找出字段 id 正是它的用途，
  新用户被死锁在门外。
- `references/FIELDS.md` 新增「值长什么样」掩码形状表、可直接复制的**向表单管理员索取**
  模板，以及基于修好的 `--dump` 重写的获取流程。脱敏移除真实值时把形状信息也一并带走了，
  新用户无从判断拿到的值对不对。
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

[Unreleased]: https://github.com/dff652/dingtalk-weekly-report/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dff652/dingtalk-weekly-report/releases/tag/v0.1.0
