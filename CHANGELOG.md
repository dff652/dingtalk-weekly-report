# 变更记录

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循
[语义化版本](https://semver.org/lang/zh-CN/)。1.0.0 之前，次版本号的变化即可能带来
不兼容的行为改变。

版本号的**单一事实源**是 `skills/dingtalk-weekly-report/VERSION`；本文件最新的已发布条目
必须与它一致（`tests/test_version.py` 守住这一点）。

## [Unreleased]

## [0.1.0] - 2026-07-25

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
