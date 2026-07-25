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
- [ ] P3 氚云 OpenApi（缺 EngineSecret）

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
