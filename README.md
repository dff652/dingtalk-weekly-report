# dingtalk-weekly-report — 钉钉「报工周报」填写工具

基于 ts-platform 的 `docs/report/PROGRESS_REPORT.md` 生成钉钉「工作申请 → 报工周报」所需的
附件 xlsx 与表单粘贴内容，并可 Playwright 半自动填表。设计与调研见
`~/ilabel/ts-platform/docs/designs/design-dingtalk-weekly-report-tool.md`。

> **平台判定修正（2026-07-21）**：报工周报实为**氚云（H3yun, www.h3yun.com）**表单，
> 非最初判定的宜搭——「打印内部二维码」解出 h3yun 域名坐实；导出文件的 `F0000001` 字段编码
> 也是氚云约定。P3 全自动路线对应改为氚云 OpenApi（`POST /OpenApi/Invoke`，
> 需 EngineCode（已从 URL 拿到）+ EngineSecret（需管理员））。字段/枚举/DOM 事实源=`FIELDS.md`。

**纯 stdlib，零第三方依赖**（本机 python 受 PEP 668 管制、无 python3-venv，xlsx 用自带的
`xlsxlite.py` 生成）。独立个人项目，不进 ts-platform 团队仓库。

## 推荐入口：Claude Code Skill `/dingtalk-weekly-report`

skill 正文 = `skills/dingtalk-weekly-report/SKILL.md`（本仓单一事实源），软链接装载到
`~/.claude/skills/dingtalk-weekly-report`。每周在 Claude Code 里一句 `/dingtalk-weekly-report`
（或带周一日期）即触发下方 SOP 的 agent 版。三条铁律内置：只落草稿不提交 /
内容必须人审 / 落草稿前提醒删同周旧草稿。

**自包含技能包与多用户安全**（2026-07-21 定稿）：`skills/dingtalk-weekly-report/` 按标准 Skill 结构
自带全部执行资源（`SKILL.md` + `scripts/` 五脚本 + `references/FIELDS.md` + `assets/config.example.json`），
**分发 = 只复制这一个目录**到对方 `~/.claude/skills/`，无需 clone 本仓库。skill 全文无硬编码
个人路径：只读技能包（`$SKILL`）与每用户运行态工作目录（`$WORK`，经 `~/.config/dtwr/root`
指针解析，缺省建议 `~/weekly-report-data`——刻意与仓库名区分，工作目录只存个人数据非代码）
彻底分离；脚本以 `DTWR_HOME`/cwd 定位工作目录。
首次使用自动引导安装（建 `$WORK`→uv 环境→config 访谈→登录→写指针）。**属主安全闸**：`$WORK`
与 `~/.config/dtwr/` 属主≠当前用户即拒绝运行——共享机上严禁用他人工作目录/凭证（等于以他人
身份向 HR 填报）；工作目录建议 `chmod 700`，登录态 `state.json` 恒 0600。
本仓库 = 维护仓 + 我自己的 `$WORK`（config.json/weeks/ 是我的实例数据，分发时不带）。

**安装方式（两种 agent CLI）**：

| CLI | 安装 | 触发 |
|---|---|---|
| Claude Code | 把 `skills/dingtalk-weekly-report/` 整目录复制（或软链接）到 `~/.claude/skills/dingtalk-weekly-report/` | 新会话里 `/dingtalk-weekly-report`，description 也参与自动路由 |
| Codex CLI | Codex 无原生 SKILL.md 机制，用自定义 prompt 桥接：建 `~/.codex/prompts/dingtalk-weekly-report.md`，内容一句话——「严格阅读并执行 <技能包绝对路径>/SKILL.md」+ 三铁律提醒 | Codex 里 `/dingtalk-weekly-report`（仅手动斜杠触发，无自动路由） |

脚本层（python3 + uv venv）与 agent 无绑定，任何终端也能按 README SOP 手动跑。

**分发**：`bash pack-skill.sh` → `dist/dingtalk-weekly-report-skill-YYYYMMDD.zip`
（只含技能包目录，零个人数据），通过钉钉/共享盘发给同事即可；本仓是私有仓+目录 700，
同事**拿 zip 不拿仓库**。包内含公司表单结构（FIELDS.md/form_url），仅限公司内部分发。

## 每周 SOP（周一 17:00 前；半自动闭环约 5 分钟人工）

```bash
cd ~/ilabel/dingtalk-weekly-report

# 0) 前提：PROGRESS_REPORT.md 已更新覆盖上周（没更新先去更新，工具不凑数）
# 1) 生成草稿（缺省=上一个周一）→ 人工审改 json（逐日 content/休假行/summary/next_week）
python3 skills/dingtalk-weekly-report/scripts/extract_week.py
# 2) 生成附件
python3 skills/dingtalk-weekly-report/scripts/gen_attachment.py weeks/week_report_YYYYMMDD.json
# 3) 登录态：每日 9:30 cron 自动 keepalive 滚动续命（crontab -l 可见；output/keepalive.log 看记录）。
#    仅当 keepalive 报「会话已失效」时才需人工续期：重新「打印内部二维码」→ 手机钉钉扫 →
.venv/bin/python skills/dingtalk-weekly-report/scripts/fill_form.py --login-url '<h3yun entry/auth 链接>'   # 链接本身 48h 有效
# 4) 半自动填表落草稿（填完自动截图 20-filled-review.png 可先核对）
.venv/bin/python skills/dingtalk-weekly-report/scripts/fill_form.py weeks/week_report_YYYYMMDD.json --draft
# 5) 钉钉里打开该草稿 → 人工核对 → 点「提交」（提交动作永远留给人）

# 回退路径（半自动不可用时）：print_form_rows.py 出粘贴块，手工填
python3 skills/dingtalk-weekly-report/scripts/print_form_rows.py weeks/week_report_YYYYMMDD.json
```

## 文件

| 文件 | 作用 |
|---|---|
| `skills/dingtalk-weekly-report/SKILL.md` | 技能指令（Claude Code 入口，`$SKILL`/`$WORK` 双路径模型） |
| `skills/dingtalk-weekly-report/scripts/extract_week.py` | ① 工作日志 → `weeks/week_report_*.json` 草稿（拒绝覆盖已有文件） |
| `skills/dingtalk-weekly-report/scripts/gen_attachment.py` | ② json → `output/YYYYMMDD-YYYYMMDD本周工作总结与下周计划.xlsx` |
| `skills/dingtalk-weekly-report/scripts/print_form_rows.py` | ② json → 表单粘贴块（回退路径） |
| `skills/dingtalk-weekly-report/scripts/fill_form.py` | ③ Playwright 半自动填表（模式速查见下表） |
| `skills/dingtalk-weekly-report/scripts/xlsxlite.py` | 极简 xlsx 写入器（stdlib 手写 OOXML，零依赖） |
| `skills/dingtalk-weekly-report/scripts/dtwr_common.py` | 工作目录解析（`DTWR_HOME`/cwd，缺 config.json 即 fail-loud） |
| `skills/dingtalk-weekly-report/references/FIELDS.md` | **表单字段事实源**：氚云字段编码 + 合法枚举值 + DOM 坑 |
| `skills/dingtalk-weekly-report/assets/config.example.json` | 个人配置模板 |
| `config.json` / `weeks/` | 我的实例数据（每用户各有一份，工作目录内） |
| `tests/mock_form.html` + `tests/run_mock_test.sh` | 维护仓的仿真表单 e2e（改 fill_form 后必跑回归） |
| `output/` | 生成的附件与截图（gitignored） |

## fill_form.py 模式速查

| 命令 | 作用 | 何时用 |
|---|---|---|
| `fill_form.py weeks/xx.json` | **只填不存**：填完全页截图退出，表单零痕迹 | 测试/预览 |
| `fill_form.py weeks/xx.json --draft` | 填完点「暂存」落**草稿** | 每周正式流程（提交由人在钉钉执行） |
| `fill_form.py weeks/xx.json --submit` | 填完直接提交 | **政策上不用**（提交永远留给人） |
| `fill_form.py --login-url '<链接>'` | 用「打印内部二维码」解出的 entry/auth 链接建登录态（免扫码，链接 48h 有效） | 会话失效时首选 |
| `fill_form.py --login` | 扫码登录（二维码持续截图到 `output/shots/login.png`，手机钉钉扫） | 拿不到链接时兜底 |
| `fill_form.py --keepalive` | 访问列表页续会话并回存 cookie | 每日 9:30 cron 自动跑（`crontab -l`；日志 `output/keepalive.log`） |
| `fill_form.py --dump` | 存表单页 HTML/截图/字段命中数 | DOM 变化时联调 |

## 维护指南（按触发条件）

| 触发 | 更新什么 |
|---|---|
| 每周例行 | ① 上游 `PROGRESS_REPORT.md` 更新到当周（内容源头）② `weeks/week_report_*.json` 内容与周五定稿 |
| keepalive 报「会话已失效」 | 重新「打印内部二维码」→ 手机扫 → 把 `entry/auth?token=…` 链接给 `--login-url`（30 秒） |
| 换项目/换负责人 | `config.json` 的 `form_project` / `attach_project` |
| HR 改表单字段 | `FIELDS.md` 编码表 + `fill_form.py` 顶部 `F` 映射与 `SUBGRID_ID` |
| 氚云前端升级致 DOM 变化 | 跑 `--dump` 拿新结构 → 调选择器 → `bash tests/run_mock_test.sh` 回归 |
| 附件模板要求变化 | `gen_attachment.py` 模板常量（表头/注/枚举） |
| 机器迁移 | `uv venv .venv && uv pip install playwright && .venv/bin/playwright install chromium`（本机 PEP 668，只用 uv）+ 重建登录态 + 重挂 cron |

## 调试指南

- 填表失败：自动截图 `output/shots/99-error.png`（现场）；每步过程截图也在 `output/shots/`。
- 结构疑变：`--dump` 产出 `dump.html`/`dump.png`/字段命中数。
- 把上述截图/文件发给 Claude 即可按真实 DOM 修选择器；改完必跑 `tests/run_mock_test.sh` 回归。
- 登录态文件 `~/.config/dtwr/state.json`（0600）= 敏感凭证，勿入 git、勿外发。

## 表单硬规则（工具自查清单已内置）

- 晚于**周一 17:00** 提交上周报 = 报工不合格
- 法定节假日/休假当天需报 8h，状态选「休假」；正常周末与调休放假**不报工**
- 任务类型枚举：产品研发 / 交付项目 / 售前活动 / 知识产权 / 其他
- 附件 ≤10MB，命名 `YYYYMMDD-YYYYMMDD本周工作总结与下周计划.xlsx`（周一-周五）
- 工作详情**一天可多行**（站会 0.5h + 开发主行 + 临时会议），字段合法取值见 `FIELDS.md`；
  表单「项目/产品名称」选 D-PD-26002 标注平台（≠附件里的 D-DP-25002 工智酷博，两处编号不同是常态）

## 路线图

- [x] **P1（路径 C）**：内容生成 + 附件 xlsx + 人工粘贴（当前形态）
- [x] **P-A（产品化）**：Claude Code Skill `/dingtalk-weekly-report`（skills/dingtalk-weekly-report/，用户级软链接装载）
- [x] **P2（路径 B）**：`fill_form.py` Playwright 半自动，**真机联调已通**（2026-07-21：token 免扫码登录、
      新增、开始日期、附件上传、10 行子表含关联项目选择与负责人联动全走通；坑与选择器事实源见
      `FIELDS.md`「P2 真机联调发现」）。默认只填不存，`--draft` 落草稿（推荐）、`--submit` 直接提交。
      环境：`uv venv .venv && uv pip install playwright && .venv/bin/playwright install chromium`（已装好）。
      无显示器服务器工作流：
      1. `config.json` 填 `form_url`（钉钉里复制「报工周报-新增」链接）
      2. `.venv/bin/python skills/dingtalk-weekly-report/scripts/fill_form.py --login` → VSCode 打开 `output/shots/login.png` 手机钉钉扫码
         → 登录态存 `~/.config/dtwr/state.json`（0600，勿入 git）
      3. `.venv/bin/python skills/dingtalk-weekly-report/scripts/fill_form.py weeks/week_report_*.json` → 自动填表+传附件 → 截图核对
         → 终端输 `yes` 才提交（`--submit` 跳过确认）；失败自动截图 `output/shots/99-error.png` 供联调
      填表逻辑已过本地仿真 e2e（`bash tests/run_mock_test.sh`，10 行全字段断言）；子表单元格按
      「列头文本→列号」定位不猜 DOM 顺序。真实页面首轮先跑 `fill_form.py --dump` 拿
      HTML/截图/字段清单，再按差异微调选择器（仿真≠真实 DOM，联调 1-2 轮预期内）。
- [ ] **P3（路径 A，可选）**：氚云 OpenApi 直提（`POST https://www.h3yun.com/OpenApi/Invoke`）。
      字段编码已从导出文件拿到（见 `skills/dingtalk-weekly-report/references/FIELDS.md`），EngineCode 已知，
      仅剩 EngineSecret（需氚云管理员）一个卡点。
# dingtalk-weekly-report
