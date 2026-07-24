# dingtalk-weekly-report

钉钉「报工周报」半自动：工作日志 → 内容草稿（**人审**）→ 附件 xlsx → 氚云表单**草稿** → 人在钉钉提交。

| | |
|---|---|
| **Skill** | `dingtalk-weekly-report` |
| **触发** | `/dingtalk-weekly-report`（可带周一日期） |
| **仓库** | https://github.com/dff652/dingtalk-weekly-report |
| **平台** | 氚云 H3yun（非宜搭） |
| **分发** | 公司内部；包内含表单结构，勿外传 |

---

## Install（skills.sh / skills CLI）

需要 [Node.js](https://nodejs.org/)（`npx`）与 [uv](https://docs.astral.sh/uv/)。
本次验收使用的 `skills@1.5.20` 要求 Node.js `>=22.20.0`；Node 18 会在
`node:util.styleText` 处启动失败。
这里使用的是官方开放生态的 `npx skills add` 安装方式；它只安装 skill 文件，
随后仍需运行本项目的 bootstrap 安装 Python/Chromium 运行时。

```bash
# 1) 装 skill → Claude Code + Codex（全局）
npx skills add https://github.com/dff652/dingtalk-weekly-report \
  --skill dingtalk-weekly-report \
  --agent claude-code \
  --agent codex \
  --global --yes --copy

# 2) Codex 若只扫 ~/.codex/skills，补链（npx 常只写到 ~/.agents + ~/.claude）
mkdir -p ~/.codex/skills
ln -sfn ~/.claude/skills/dingtalk-weekly-report \
        ~/.codex/skills/dingtalk-weekly-report

# 3) 运行时：$WORK + Playwright Chromium（装 skill 不会做这一步）
bash ~/.claude/skills/dingtalk-weekly-report/bootstrap.sh
```

等价简写：`npx skills add dff652/dingtalk-weekly-report -s dingtalk-weekly-report -a claude-code -a codex -g -y --copy`

| 回退 | 命令 |
|------|------|
| 无 Node / 仅 zip | 解压后 `bash install.sh` → `bash bootstrap.sh`（见 [USER_GUIDE](skills/dingtalk-weekly-report/USER_GUIDE.md)） |
| Windows | `npx skills add …` 同上；bootstrap 用 skill 目录内 `.\bootstrap.ps1` |
| 维护仓开发 | 克隆后 `bash install.sh --link` |

升级 skill：`npx skills update dingtalk-weekly-report -g -y`（或 `install.sh --force`）

> 分发边界：当前仓库可被公开 GitHub URL 克隆，但项目又声明“仅公司内部”，且包含内部表单结构。
> 在决定公开进入 skills.sh 前，请先阅读 [发布与脱敏要求](docs/PUBLISHING.md)。

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
4. 按 skills/dingtalk-weekly-report/USER_GUIDE.md 与 SKILL.md 引导我填写 config.json、完成扫码登录；不得让我把 auth 链接发到聊天或放进命令参数。
5. 之后用 /dingtalk-weekly-report 做周报；只允许 --draft --confirmed；脚本无提交能力；内容必须人审。

装完请运行自检（见 README「Verify」）并报告结果。
```

**说明：** AI 可完成装 skill + bootstrap；**不能**代替你：表单项目下拉原文、扫码、
一次性 auth 链接的隐藏输入、人审内容、钉钉点「提交」。

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
```

可选：`npx skills list -g` 应能看到 `dingtalk-weekly-report`。

---

## Use

1. 编辑 `~/weekly-report-data/config.json`（姓名、`form_project` 完整原文、`attach_project`、可选 `progress_report`）。
2. **新开** Claude / Codex 会话：

```text
/dingtalk-weekly-report
```

或指定周一：`/dingtalk-weekly-report 2026-07-20`

3. 首次登录首选 `fill_form.py --login` 后扫码；若使用内部二维码 auth 链接，
   由你本人在本机终端运行 `fill_form.py --login-url` 并按隐藏提示粘贴，勿交给 Agent。
4. 人审 json → 落**草稿** → **你**在钉钉点提交。

三条铁律：只 `--draft --confirmed`；内容必人审；落草稿前删同周旧草稿。补交上周：**周一 17:00 前**。
`--confirmed` 只是操作者完成检查清单的声明，不是人审记录或审计证明。

纯 CLI：见 [USER_GUIDE.md](skills/dingtalk-weekly-report/USER_GUIDE.md)。

---

## 文档

| 文档 | 内容 |
|------|------|
| [skills/…/USER_GUIDE.md](skills/dingtalk-weekly-report/USER_GUIDE.md) | 安装细节、每周 CLI、FAQ（随 skill / zip） |
| [skills/…/SKILL.md](skills/dingtalk-weekly-report/SKILL.md) | Agent 执行 SOP |
| [skills/…/references/CONTRACT.md](skills/dingtalk-weekly-report/references/CONTRACT.md) | 输入、缺失处理、输出与失败契约 |
| [skills/…/references/FIELDS.md](skills/dingtalk-weekly-report/references/FIELDS.md) | 表单字段事实源 |
| [docs/MAINTAINER.md](docs/MAINTAINER.md) | 维护仓：打包、测试、调试、路线图 |
| [docs/PUBLISHING.md](docs/PUBLISHING.md) | skills.sh 安装、公开发布与内部私有分发 |
| [docs/TESTING.md](docs/TESTING.md) | 自动测试覆盖、安装踩坑排查、最近结果与人工验收边界 |
| [docs/MANUAL_ACCEPTANCE.md](docs/MANUAL_ACCEPTANCE.md) | 真实配置、登录、预览、草稿与人工提交 SOP |
| [docs/](docs/) | 文档索引 |

维护者：`run_smoke.sh` 快速回归，`run_full_acceptance.sh` 验本地包，
`run_release_acceptance.sh` 验 GitHub 发行。更多见 [MAINTAINER.md](docs/MAINTAINER.md)。
