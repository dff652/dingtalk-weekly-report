---
name: weekly-report
description: 每周钉钉「报工周报」半自动流程——从个人工作日志生成内容草稿（人审）→ 附件 xlsx → 氚云表单落草稿 → 人工在钉钉核对提交。周五定稿本周或周一 17:00 前补交上周时使用；可带周一日期参数指定周（如 /weekly-report 2026-07-20）。首次使用自动引导安装。
---

# 钉钉报工周报半自动流程

本 skill 是 dingtalk-weekly-report 工具的 agent 入口，**多用户可复用：全文无任何硬编码的个人路径，
每用户的路径/身份/内容源一律运行时解析**。事实源：`$ROOT/README.md`（SOP/模式/维护）、
`$ROOT/FIELDS.md`（表单字段/枚举/DOM 坑）。

## 第 0 步：解析 $ROOT（严禁跳过，严禁硬编码）

1. 读 `~/.config/dtwr/root`（一行绝对路径）→ 目录存在则为 `$ROOT`；
2. 否则探测 `~/dingtalk-weekly-report`、`~/ilabel/dingtalk-weekly-report`，命中则用之并写回
   `~/.config/dtwr/root`；
3. 都没有 → 走「首次安装」（见文末），装完回到这里。

**安全闸（共享机必查）**：`$ROOT` 与 `~/.config/dtwr/` 的属主必须是当前用户
（`stat -c %U "$ROOT"` == `whoami`），否则**立即终止并告知用户**——严禁使用他人的
checkout、config、登录态；那等于以他人身份向 HR 填报。同理，本 skill 全程只读写
当前用户 `$HOME` 与 `$ROOT` 之内的路径。

以下所有命令 `cd $ROOT` 执行；git 操作必须 `git -C $ROOT`（防误提交进别的仓库）。
每用户差异（姓名/项目/负责人/内容源路径）全部来自 `$ROOT/config.json`，skill 里不出现具体值。

## 三条铁律（任何步骤不得违反）

1. **只落草稿，永不提交**：只用 `--draft`，不用 `--submit`。提交由用户在钉钉里核对后亲手点。
2. **内容必须人审**：`weeks/week_report_*.json` 生成/修改后，先把逐日内容摘要展示给用户确认，再进入填表。
3. **防重复**：落草稿前提醒用户检查/删除同一周的旧草稿（同周多条记录会撞「周报唯一性判定」；删除由用户在钉钉做）。

## 流程

### 1) 确定目标周

- 用户带参数（周一日期）→ 用参数；无参数：今天是周一 → 上一周（补交，注意 17:00 截止）；否则 → 当前周。
- 复述目标周区间（周一~周日）请用户确认。

### 2) 前置检查：内容源

- 内容源路径 = `config.json` 的 `progress_report`（个人工作日志）。存在 → 检查其是否已覆盖目标周
  （无覆盖则**先更新日志再回来**，fail-loud，不拿 git log 凑数）。
- 该键为空或文件不存在（用户没有日志纪律）→ 退化为访谈式：按工作日逐天问用户做了什么，直接写 json。

### 3) 生成/更新周报 json（人审锚点）

- `weeks/week_report_YYYYMMDD.json` 不存在 → `python3 extract_week.py <周一日期>` 生成草稿。
- 润色逐日 `content`：
  - 每工作日两行起：会议行（周一=周例会 0.5h 内外部会议·公司和部门运营活动·项目留空；
    其余=站会 0.5h 内部会议·产品研发·带项目）+ 开发主行（算法开发 8h·带项目）——具体会议
    名称/工时模式以 `config.json` 的 `standup`/`monday_meeting` 为准。
  - **content ≤200 字**（表单硬上限）；写给 HR 看的措辞，量化结果，不堆内部代号。
  - 休假日：状态「休假」8h、项目类型「公司和部门运营活动」、无项目无内容；正常周末不报。
  - `summary`/`next_week`：定稿日填实；周中测试可标「进行中，周五定稿」。
- 枚举合法值/双项目字段（表单下拉项 ≠ 附件关联项目，两处编号不同）见 `FIELDS.md` 与 `config.json`。
- **把逐日内容+工时合计摘要发给用户，得到确认再继续。**

### 4) 附件

`python3 gen_attachment.py weeks/week_report_YYYYMMDD.json`

### 5) 登录态

- `.venv/bin/python fill_form.py --keepalive` 验会话（若装了每日 cron 保活通常直接过）。
- 报「会话已失效」→ 请用户：钉钉报工周报列表 →「打印二维码 → 打印内部二维码」→ 手机钉钉扫 →
  把浏览器里 `h3yun.com/entry/auth?token=…` 整条链接发来 → `.venv/bin/python fill_form.py --login-url '<链接>'`。
  链接 48h 有效、等价临时登录凭证：用完提醒勿转发；**勿写入任何文件/git/命令历史之外的地方**。

### 6) 落草稿

- 先提醒用户删同周旧草稿（如有），得到确认。
- `.venv/bin/python fill_form.py weeks/week_report_YYYYMMDD.json --draft`
- 展示 `output/shots/20-filled-review.png` 与 `30-saved.png`，指出核对点：行数、周总工时、附件已挂、项目/负责人带出。

### 7) 收尾

- 提醒用户：钉钉里打开草稿核对 → 点「提交」（周一 17:00 截止线）。
- `git -C $ROOT add weeks/ && git -C $ROOT commit && git -C $ROOT push`（若该 checkout 配了远端；
  commit 尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`）。

## 首次安装（$ROOT 不存在时）

1. 问用户装哪（默认 `~/dingtalk-weekly-report`）；从仓库获取代码
   （有权限则 `git clone`，否则请持有者给压缩包/加协作者）。
2. 环境（机器若受 PEP 668 管制用 uv）：
   `uv venv .venv && uv pip install --python .venv/bin/python playwright && .venv/bin/playwright install chromium`
3. `cp config.example.json config.json`，逐项访谈填写：姓名、表单下拉项目值（form_project，
   从历史周报导出或下拉里抄**完整原文**）、附件关联项目（attach_project）、默认工时/会议模式、
   内容源路径 progress_report（没有则留空走访谈式）。
4. 登录：走上面第 5 步的「会话已失效」分支建立登录态；可选装每日保活 cron：
   `30 9 * * * cd <ROOT> && .venv/bin/python fill_form.py --keepalive >> output/keepalive.log 2>&1`
5. 写 `~/.config/dtwr/root`（内容=ROOT 绝对路径，目录 0700）；跑 `bash tests/run_mock_test.sh` 验环境。

## 出错处理

- 填表失败：看 `output/shots/99-error.png`，对照 `FIELDS.md`「P2 真机联调发现」修 `fill_form.py`
  选择器；改后必跑 `bash tests/run_mock_test.sh` 回归再重试。
- 表单结构疑变：`.venv/bin/python fill_form.py --dump` 拿新 DOM。
- 环境损坏：按「首次安装」第 2 步用 uv 重建。
