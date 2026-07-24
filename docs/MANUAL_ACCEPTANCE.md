# 真实钉钉人工验收 SOP

本 SOP 只验收真实个人配置、登录态、氚云草稿与钉钉人工提交。自动测试和远端发行验收通过，
不能替代本流程；本流程也不能由 Agent 自动点击最终提交。

## 0. 准入条件

- `bash tests/run_release_acceptance.sh` 已对待发布提交打印 `RELEASE ACCEPTANCE PASS`；
- 当前用户独占 `$WORK` 与 `~/.config/dtwr/`，属主检查通过；
- 不使用测试 fixture、他人 config 或他人登录态；
- 一次性 auth 链接不进入聊天、命令参数、shell 历史、文件或 git；
- 已确定目标周，且用户明确确认周一至周日区间。

任一条件不满足即停止，不得用“先落草稿再看”绕过。

## 1. 验收记录

开始前填写：

| 项 | 记录 |
|---|---|
| 日期 / 验收人 | |
| Git commit | |
| 安装来源 | GitHub / 内部 zip |
| Agent / 操作系统 | |
| `$SKILL` | |
| `$WORK` | |
| 目标周 | |
| Skills.sh 审计 | |

## 2. 安装与运行态

```bash
export WORK="$(cat ~/.config/dtwr/root)"
AGENTS_SKILL="$HOME/.agents/skills/dingtalk-weekly-report"
CLAUDE_SKILL="$HOME/.claude/skills/dingtalk-weekly-report"
if [ -f "$AGENTS_SKILL/SKILL.md" ]; then
  export SKILL="$AGENTS_SKILL"
elif [ -f "$CLAUDE_SKILL/SKILL.md" ]; then
  export SKILL="$CLAUDE_SKILL"
else
  echo "未发现已安装的 dingtalk-weekly-report" >&2
  return 1 2>/dev/null || exit 1
fi
npx --yes skills@1.5.20 list --global
test -f "$SKILL/SKILL.md"
if [ -f "$AGENTS_SKILL/SKILL.md" ] && [ -f "$CLAUDE_SKILL/SKILL.md" ]; then
  diff -qr --exclude="__pycache__" "$AGENTS_SKILL" "$CLAUDE_SKILL"
fi
stat -c '%U %a %n' "$WORK" ~/.config/dtwr ~/.config/dtwr/root
"$WORK/.venv/bin/python" -c "import playwright; print('playwright OK')"
```

通过标准：

- 列表中有 `dingtalk-weekly-report`，目标 Agent 可发现；
- `$SKILL` 指向实际安装副本；
- `.agents` 与 `.claude` 同时存在时，两份安装内容一致；
- root 指向当前用户的真实 `$WORK`；
- `$WORK` 与登录态目录属于当前用户；
- venv 与 Playwright 可加载。

Windows 不提供 POSIX uid 闸，须人工确认当前 Windows 账户与目录 ACL。

## 3. 真实配置

人工检查 `$WORK/config.json`：

- `name` 是本人姓名；
- `form_project` 是氚云下拉完整原文；
- `attach_project` 是附件使用的项目；
- `form_url` 是 `https://*.h3yun.com`；
- `progress_report` 为空，或指向当前用户确实维护的工作日志文件/项目目录；项目目录内须有
  `docs/report/PROGRESS_REPORT.md`；
- 不含模板占位值、他人姓名、他人项目或凭证。

已配置但不存在的 `progress_report`，或项目目录缺标准文档，都是配置错误，必须修正；
不得静默转成访谈模式。

## 4. 内容源与目标周

1. 复述目标周 `周一 ～ 周日`，取得用户明确确认；
2. 检查工作日志覆盖目标周所有工作日；
3. 缺失日期由用户补日志或逐日口述，不得用 git log 猜测；
4. 运行：

```bash
cd "$WORK"
python3 "$SKILL/scripts/extract_week.py" YYYY-MM-DD
```

若 JSON 已存在，脚本拒绝覆盖；先人工判断是继续编辑旧文件还是另行备份，禁止直接删除。

## 5. 周报内容人审

对 `$WORK/weeks/week_report_YYYYMMDD.json` 展示并逐项确认：

- 每个工作日的日期、项目类型、项目、状态、工时和主要工作内容；
- 每日合计不超过 24h，正常周末不报；
- 休假日规则正确；
- 单条内容不超过 200 字；
- 本周总结与下周计划已定稿；
- 周总工时符合实际；
- 不含 `TODO`、内部敏感代号或编造内容。

记录用户确认时间。未取得确认，不得生成真实填表预览。

## 6. 附件

```bash
cd "$WORK"
python3 "$SKILL/scripts/gen_attachment.py" weeks/week_report_YYYYMMDD.json
python3 "$SKILL/scripts/print_form_rows.py" weeks/week_report_YYYYMMDD.json
```

人工打开 xlsx，核对日期、每日行、工时、总结、计划和附件项目。附件与粘贴块必须和已确认
JSON 一致。

## 7. 登录

先检查已有会话：

```bash
cd "$WORK"
.venv/bin/python "$SKILL/scripts/fill_form.py" --keepalive
```

失效时首选扫码：

```bash
.venv/bin/python "$SKILL/scripts/fill_form.py" --login
```

用户扫描 `$WORK/output/shots/login.png`。若扫码不可用，用户本人在本机交互终端运行：

```bash
.venv/bin/python "$SKILL/scripts/fill_form.py" --login-url
```

再按隐藏提示粘贴 auth 链接。Agent 不得索要、接收、回显或代输该链接。

## 8. 真实表单预览：只填不存

```bash
cd "$WORK"
.venv/bin/python "$SKILL/scripts/fill_form.py" \
  weeks/week_report_YYYYMMDD.json
```

检查 `$WORK/output/shots/20-filled-review.png`：

- 周开始日期及自动结束日期；
- 子表行数与 JSON 一致；
- 项目类型、项目、状态、工时、内容均正确；
- 附件已挂载；
- 负责人等关联字段正确带出。

此步骤不得加 `--draft`。

## 9. 防重复与落草稿

用户在钉钉中检查目标周是否已有草稿；有则由用户判断并删除旧草稿。Agent 不自动删除。

用户再次明确确认“内容已审、旧草稿已检查”后，才运行：

```bash
cd "$WORK"
.venv/bin/python "$SKILL/scripts/fill_form.py" \
  weeks/week_report_YYYYMMDD.json --draft --confirmed
```

通过标准：

- 命令明确检测到可见成功提示；
- `$WORK/output/shots/30-saved.png` 存在；
- 钉钉草稿列表出现且只有一条目标周记录；
- 打开草稿后内容、工时、附件、项目和负责人均正确。

表单关闭、导航变化或没有可见成功提示都不算成功。

## 10. 最终提交与结果

最终提交只能由用户在钉钉打开草稿、再次核对后亲手点击。

| 检查项 | 通过/失败 | 证据或备注 |
|---|---|---|
| 下载与安装 | | |
| 运行态与属主 | | |
| 真实配置 | | |
| 内容源覆盖 | | |
| JSON 人审 | | |
| 附件 | | |
| 登录 | | |
| 真实预览 | | |
| 防重复 | | |
| 草稿保存 | | |
| 钉钉最终提交 | | |

最终结论只能是以下之一：

- `PASS`：全部项目通过；
- `CONDITIONAL PASS`：仅钉钉最终提交按设计留给用户，其他全部通过；
- `FAIL`：任一配置、内容、登录、预览或草稿步骤失败。

失败时保留 `output/shots/99-error.png` 和不含凭证的错误摘要；不得保存 auth 链接。
