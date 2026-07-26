# dingtalk-weekly-report

钉钉「报工周报」半自动：工作日志 → 内容草稿（**人审**）→ 附件 xlsx → 氚云表单**草稿** → 人在钉钉提交。

| | |
|---|---|
| **Skill** | `dingtalk-weekly-report` |
| **触发** | Claude：`/dingtalk-weekly-report`；Codex：`$dingtalk-weekly-report` 或 `/skills` 选择 |
| **仓库** | https://github.com/dff652/dingtalk-weekly-report |
| **平台** | 氚云 H3yun（非宜搭） |
| **许可** | [Apache-2.0](LICENSE)，Copyright 2026 dff652 |
| **版本** | 见 [`skills/dingtalk-weekly-report/VERSION`](skills/dingtalk-weekly-report/VERSION)（单一事实源）与 [CHANGELOG](CHANGELOG.md) |
| **隐私边界** | 仓库仅含通用代码；表单 ID、枚举、个人周报和登录态只存每用户私有 `$WORK` |

---

## Install（skills.sh / skills CLI）

需要 [Node.js](https://nodejs.org/)（`npx`）与 [uv](https://docs.astral.sh/uv/)。
本次验收使用的 `skills@1.5.20` 要求 Node.js `>=22.20.0`；Node 18 会在
`node:util.styleText` 处启动失败。
这里使用的是官方开放生态的 `npx skills add` 安装方式；它只安装 skill 文件，
随后仍需运行本项目的 bootstrap 安装 Python/Chromium 运行时。

**最短路径**——装完直接调用，skill 自己会建运行环境：

```bash
npx skills add dff652/dingtalk-weekly-report
```

```text
/dingtalk-weekly-report        # Claude；Codex 用 $dingtalk-weekly-report
```

首次调用时 `SKILL.md` 第 0 步发现 `$WORK` 不存在，会引导跑 bootstrap（建 `$WORK`、venv、
Chromium、config）。

**确定性装法**（非交互、或想一次装到位不依赖 agent 行为）：

```bash
# 1) 装 skill → Claude Code + Codex（全局）
npx skills add https://github.com/dff652/dingtalk-weekly-report \
  --skill dingtalk-weekly-report --agent claude-code --agent codex --global --yes --copy

# 2) Codex 补链（实测 npx 只写 ~/.agents + ~/.claude，不写 ~/.codex/skills）
mkdir -p ~/.codex/skills
ln -sfn ~/.claude/skills/dingtalk-weekly-report ~/.codex/skills/dingtalk-weekly-report

# 3) 运行时：$WORK + Playwright Chromium
bash ~/.claude/skills/dingtalk-weekly-report/bootstrap.sh
```

| 回退 | 命令 |
|------|------|
| 无 Node / 仅 zip | 解压后 `bash install.sh` → `bash bootstrap.sh`（见 [USER_GUIDE](skills/dingtalk-weekly-report/USER_GUIDE.md)） |
| Windows | `npx skills add …` 同上；bootstrap 用 skill 目录内 `.\bootstrap.ps1` |
| 维护仓开发 | 克隆后 `bash install.sh --link` |

升级 skill：`npx skills update dingtalk-weekly-report -g -y`（或 `install.sh --force`）

Skill 代码与每用户运行数据严格分离：安装目录只读，默认私有工作目录为
`~/weekly-report-data`。不要把 `$WORK/config.json`、`weeks/`、`output/` 或
`~/.config/dtwr/state.json` 提交到本仓库。Git 历史已于 2026-07-25 重建为单一提交并回收旧对象，
该日期之前的克隆请重新克隆；处置全过程见 [PUBLISHING.md](docs/PUBLISHING.md)。

---

## 只给仓库 URL 时：复制给 AI

把下面整段贴进 **Claude Code / Codex**（有终端权限的会话）：

```text
请根据 https://github.com/dff652/dingtalk-weekly-report 在本机安装 skill「dingtalk-weekly-report」并完成首次运行环境：

1. 执行：
   npx skills add https://github.com/dff652/dingtalk-weekly-report --skill dingtalk-weekly-report --agent claude-code --agent codex --global --yes --copy
2. 若 ~/.codex/skills/dingtalk-weekly-report 不存在，则：
   mkdir -p ~/.codex/skills && ln -sfn ~/.claude/skills/dingtalk-weekly-report ~/.codex/skills/dingtalk-weekly-report
3. 执行：bash ~/.claude/skills/dingtalk-weekly-report/bootstrap.sh
4. 按 skills/dingtalk-weekly-report/USER_GUIDE.md 与 SKILL.md，通过 configure.py 引导我填写本人有权使用的表单 URL、字段 ID、按钮文本、枚举和项目，再完成扫码登录；不得猜测组织字段，不得让我把 auth 链接发到聊天、保存为 form_url 或放进命令参数。
5. 之后 Claude 用 /dingtalk-weekly-report、Codex 用 $dingtalk-weekly-report（或 /skills 选择）做周报；只允许 --draft --confirmed；脚本无提交能力；内容必须人审。

装完请运行自检（见 README「Verify」）并报告结果。
```

**说明：** AI 可完成装 skill + bootstrap；**不能**代替你：本人或管理员确认的表单字段 ID、
下拉枚举和项目原文、扫码、一次性 auth 链接的隐藏输入、人审内容、钉钉点「提交」。

---

## Verify（装完自检）

```bash
[ -f ~/.claude/skills/dingtalk-weekly-report/SKILL.md ] && echo "Claude skill OK" || echo "Claude skill MISSING"
if [ -f ~/.codex/skills/dingtalk-weekly-report/SKILL.md ]; then
  echo "Codex skill OK (~/.codex/skills)"
elif [ -f ~/.agents/skills/dingtalk-weekly-report/SKILL.md ]; then
  echo "Agents skill OK (~/.agents/skills；Codex 可能读这里，建议仍补链到 ~/.codex/skills)"
else
  echo "Codex/Agents skill MISSING"
fi
[ -f ~/weekly-report-data/config.json ] && echo "config OK" || echo "config MISSING（先 bootstrap）"
[ -f ~/.config/dtwr/root ] && echo "dtwr root: $(cat ~/.config/dtwr/root)" || echo "dtwr root MISSING"
~/weekly-report-data/.venv/bin/python -c "import playwright; print('playwright OK')" 2>/dev/null \
  || echo "playwright MISSING（先 bootstrap）"
~/weekly-report-data/.venv/bin/python \
  ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py --check
```

可选：`npx skills list -g` 应能看到 `dingtalk-weekly-report`。

---

## Use

1. 运行配置向导（首次和以后换项目均可使用）：

```bash
~/weekly-report-data/.venv/bin/python \
  ~/.claude/skills/dingtalk-weekly-report/scripts/configure.py
```

   填写姓名、`form_project` 完整原文、`attach_project`、可选 `progress_report`，以及由本人
   或表单管理员确认的 `vocabulary`、`form_fields`、`form_texts`。工作日志项目目录只读取
   `docs/report/PROGRESS_REPORT.md`，留空则由 AI 逐日访谈。校验通过后才写入；旧配置保留为
   `config.json.bak`。查看用 `--show`，校验用 `--check`。首次保存后，后续每周不需重复配置，
   只有项目、表单、内容源或默认值变化时再运行。
2. **新开** AI 会话并显式调用（自然语言提及不作为可靠触发方式）：

```text
# Claude Code
/dingtalk-weekly-report

# Codex
$dingtalk-weekly-report
```

指定周一：Claude 用 `/dingtalk-weekly-report 2026-07-20`；Codex 用
`$dingtalk-weekly-report 2026-07-20`，也可先运行 `/skills` 选择。

3. 首次登录首选 `fill_form.py --login` 后扫码；若使用一次性 auth 链接，
   由你本人在本机终端运行 `fill_form.py --login-url` 并按隐藏提示粘贴，勿交给 Agent。
4. 人审 json → 落**草稿** → **你**在钉钉点提交。

三条铁律：只 `--draft --confirmed`；内容必人审；落草稿前检查同周旧草稿。提交时间以用户私有
配置中的 `submission_reminder` 和所在组织规则为准。
`--confirmed` 只是操作者完成检查清单的声明，不是人审记录或审计证明。

纯 CLI：见 [USER_GUIDE.md](skills/dingtalk-weekly-report/USER_GUIDE.md)。

---

## 文档

| 文档 | 内容 |
|------|------|
| [skills/…/USER_GUIDE.md](skills/dingtalk-weekly-report/USER_GUIDE.md) | 安装细节、每周 CLI、FAQ（随 skill / zip） |
| [skills/…/SKILL.md](skills/dingtalk-weekly-report/SKILL.md) | Agent 执行 SOP |
| [skills/…/references/CONTRACT.md](skills/dingtalk-weekly-report/references/CONTRACT.md) | 输入、缺失处理、输出与失败契约 |
| [skills/…/references/FIELDS.md](skills/dingtalk-weekly-report/references/FIELDS.md) | 私有配置键、字段获取方法与通用 DOM 约束 |
| [SECURITY.md](SECURITY.md) | 信任模型、扫描器告警处置、数据边界 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献规则：钩子、提交身份、不接受的改动 |
| [docs/SOP.md](docs/SOP.md) | 开发/测试/发版/部署流程骨架与决策表 |
| [docs/REVIEW.md](docs/REVIEW.md) | 设计评审：不变量清单与缺陷台账 |
| [docs/MAINTAINER.md](docs/MAINTAINER.md) | 维护仓：打包、测试、调试、路线图 |
| [docs/PUBLISHING.md](docs/PUBLISHING.md) | 开源发布、发行门禁与历史清理 |
| [docs/TESTING.md](docs/TESTING.md) | 自动测试覆盖、安装踩坑排查、最近结果与人工验收边界 |
| [docs/MANUAL_ACCEPTANCE.md](docs/MANUAL_ACCEPTANCE.md) | 真实配置、登录、预览、草稿与人工提交 SOP |
| [LICENSE](LICENSE) | Apache License 2.0 |
| [docs/](docs/) | 文档索引 |

维护者：`run_smoke.sh` 快速回归，`run_full_acceptance.sh` 验本地包，
`run_release_acceptance.sh` 验 GitHub 发行。更多见 [MAINTAINER.md](docs/MAINTAINER.md)。
