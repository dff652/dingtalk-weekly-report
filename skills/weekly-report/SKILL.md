---
name: weekly-report
description: 每周钉钉「报工周报」半自动流程——从 PROGRESS_REPORT.md 生成内容草稿（人审）→ 附件 xlsx → 氚云表单落草稿 → 人工在钉钉核对提交。周五定稿本周或周一 17:00 前补交上周时使用；可带周一日期参数指定周（如 /weekly-report 2026-07-20）。
---

# 钉钉报工周报半自动流程

工具项目根 = `/home/ym/ilabel/dingtalk-weekly-report`（下称 `$ROOT`；命令一律 `cd $ROOT` 后执行，
git 操作必须 `git -C $ROOT`，防止误提交进别的仓库）。
事实源：`$ROOT/README.md`（SOP/模式速查/维护指南）、`$ROOT/FIELDS.md`（表单字段/枚举/DOM 坑）。

## 三条铁律（任何步骤不得违反）

1. **只落草稿，永不提交**：只用 `--draft`，不用 `--submit`。提交由用户在钉钉里核对后亲手点。
2. **内容必须人审**：`weeks/week_report_*.json` 生成/修改后，先把逐日内容摘要展示给用户确认，再进入填表。
3. **防重复**：落草稿前提醒用户检查/删除同一周的旧草稿（同周多条记录会撞「周报唯一性判定」；删除动作由用户在钉钉做，工具不做删除）。

## 流程

### 0) 确定目标周

- 用户带参数（周一日期）→ 用参数。
- 无参数：今天是周一 → 上一周（补交场景，注意 17:00 截止）；否则 → 当前周（定稿场景）。
- 复述目标周区间（周一~周日）请用户确认。

### 1) 前置检查：上游内容源

- 检查 `/home/ym/ilabel/ts-platform/docs/report/PROGRESS_REPORT.md` 是否已覆盖目标周
  （对照 `git -C /home/ym/ilabel/ts-platform log --since/--until` 该周的 commit）。
- 未覆盖 → **先更新 PROGRESS_REPORT.md 再回来**（fail-loud，不拿 git log 凑数直接出周报）。

### 2) 生成/更新周报 json（人审锚点）

- `weeks/week_report_YYYYMMDD.json` 不存在 → `python3 extract_week.py <周一日期>` 生成草稿。
- 基于 PROGRESS_REPORT 每日详情润色逐日 `content`：
  - 每工作日两行起：会议行（周一=算法团队周例会 0.5h 内外部会议·公司和部门运营活动·项目留空；
    其余=产品研发站会 0.5h 内部会议·产品研发·带项目）+ 开发主行（算法开发 8h·带项目）。
  - **content ≤200 字**（表单硬上限）；写给 HR 看的措辞（讲清做了什么、量化结果），不堆内部代号。
  - 休假日：状态「休假」8h、项目类型「公司和部门运营活动」、无项目无内容；正常周末不报。
  - `summary`/`next_week`：定稿日填实（周任务/交付物/完成情况编号列表）；周中测试可标「进行中，周五定稿」。
- 枚举合法值/双项目字段（表单选 D-PD-26002 标注平台 ≠ 附件关联 D-DP-25002 工智酷博）见 `FIELDS.md`。
- **把逐日内容+工时合计摘要发给用户，得到确认再继续。**

### 3) 附件

`python3 gen_attachment.py weeks/week_report_YYYYMMDD.json` → `output/YYYYMMDD-YYYYMMDD本周工作总结与下周计划.xlsx`。

### 4) 登录态

- `.venv/bin/python fill_form.py --keepalive` 验会话（每日 9:30 有 cron 保活，通常直接过）。
- 报「会话已失效」→ 请用户：钉钉报工周报列表 →「打印二维码 → 打印内部二维码」→ 手机钉钉扫 →
  把浏览器里 `h3yun.com/entry/auth?token=…` 整条链接发来 → `.venv/bin/python fill_form.py --login-url '<链接>'`。
  （链接 48h 有效、等价临时登录凭证，用完提醒用户勿转发；勿写入任何文件/git。）

### 5) 落草稿

- 先提醒用户删同周旧草稿（如有），得到确认。
- `.venv/bin/python fill_form.py weeks/week_report_YYYYMMDD.json --draft`
- 把 `output/shots/20-filled-review.png`（填表核对）与 `30-saved.png`（落草稿后列表）展示给用户，
  指出关键核对点：行数、周总工时、附件已挂、项目/负责人带出。

### 6) 收尾

- 提醒用户：钉钉里打开草稿核对 → 点「提交」（周一 17:00 截止线）。
- `git -C $ROOT add weeks/ && git -C $ROOT commit && git -C $ROOT push`（json 入库留痕；
  commit 尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`）。

## 出错处理

- 填表失败：看 `output/shots/99-error.png` 现场截图，对照 `FIELDS.md`「P2 真机联调发现」修
  `fill_form.py` 选择器；改后必跑 `bash $ROOT/tests/run_mock_test.sh` 回归再重试。
- 表单结构疑变：`.venv/bin/python fill_form.py --dump` 拿新 DOM。
- 环境损坏（venv/chromium）：本机 PEP 668，只用 uv 重建——
  `~/.local/bin/uv venv .venv --clear && ~/.local/bin/uv pip install --python .venv/bin/python playwright && .venv/bin/playwright install chromium`。
