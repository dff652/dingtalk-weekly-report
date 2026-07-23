# dingtalk-weekly-report — 钉钉「报工周报」填写工具

基于 ts-platform 的 `docs/report/PROGRESS_REPORT.md` 生成钉钉「工作申请 → 报工周报」所需的
附件 xlsx 与表单粘贴内容，并可 Playwright 半自动填表。设计与调研见
`~/ilabel/ts-platform/docs/designs/design-dingtalk-weekly-report-tool.md`。

> **平台判定修正（2026-07-21）**：报工周报实为**氚云（H3yun, www.h3yun.com）**表单，
> 非最初判定的宜搭——「打印内部二维码」解出 h3yun 域名坐实；导出文件的 `F0000001` 字段编码
> 也是氚云约定。P3 全自动路线对应改为氚云 OpenApi（`POST /OpenApi/Invoke`，
> 需 EngineCode（已从 URL 拿到）+ EngineSecret（需管理员））。字段/枚举/DOM 事实源=`FIELDS.md`。

**依赖**：内容生成/附件 xlsx 为纯 stdlib（`xlsxlite.py`，适配 PEP 668）；半自动填表需
`playwright` + Chromium（`$WORK/.venv`）。独立个人项目，不进 ts-platform 团队仓库。

## 目录与职责

| 路径 | 职责 | 是否进 zip |
|---|---|---|
| `skills/dingtalk-weekly-report/` | **技能包**（`$SKILL`）：SKILL.md、install.sh、scripts、FIELDS、config 模板 | 是（平铺为 zip 根目录） |
| 仓库根 `config.json` / `weeks/` / `output/` / `.venv/` | 维护者本机 **`$WORK` 实例**（个人数据） | 否 |
| `~/.config/dtwr/` | 每用户指针 `root` + 登录态 `state.json`（0600） | 否 |
| `pack-skill.sh` / 根 `install.sh` | 维护仓打包入口 / 转调技能自安装 | 否（根 install 不进包） |
| `tests/` | 维护仓仿真 e2e | 否 |
| `dist/*.zip` | 分发物（gitignored） | — |

同事默认 `$WORK` = `~/weekly-report-data`（与仓库名刻意区分）；维护者可把本仓本身当作 `$WORK`。

## 推荐入口：Claude Code Skill `/dingtalk-weekly-report`

skill 正文 = `skills/dingtalk-weekly-report/SKILL.md`（本仓单一事实源）。每周在 Claude Code 里
一句 `/dingtalk-weekly-report`（或带周一日期）即触发 SOP 的 agent 版。三条铁律：只落草稿不提交 /
内容必须人审 / 落草稿前提醒删同周旧草稿。

**自包含与安全**（安装契约 2026-07-23 收口）：技能包无硬编码个人路径；`$SKILL` 只读、
`$WORK` 经 `~/.config/dtwr/root` 解析。属主安全闸：`$WORK` 与 `~/.config/dtwr/` 属主必须是
当前用户，否则拒绝运行（共享机禁止用他人目录/凭证填 HR 表）。工作目录建议 `chmod 700`。

### 安装与分发（单一契约）

| 角色 | 命令 | 效果 |
|---|---|---|
| **同事（推荐）** | `unzip dingtalk-weekly-report-skill-*.zip && bash dingtalk-weekly-report/install.sh` | 复制到 `~/.claude/skills/dingtalk-weekly-report/`；若有 `~/.codex` 则写桥接 prompt |
| **维护仓** | 仓库根目录 `bash install.sh --link` | 软链到仓内技能目录，改代码即时生效 |
| **升级 / 覆盖** | 同上加 `--force`（改软链：`--link --force`） | 覆盖已有安装；清理旧名 `weekly-report` 技能与 Codex prompt |
| **维护者打 zip** | `bash pack-skill.sh` | 产出 `dist/dingtalk-weekly-report-skill-YYYYMMDD.zip`（平铺技能包） |

- 触发：Claude Code `/dingtalk-weekly-report`；Codex 同名（仅手动斜杠，无自动路由）。
- 装完技能后**第一次**跑 skill：按 `SKILL.md`「首次安装」建 `$WORK`、uv 环境、config、登录。
- 脚本层与 agent 无绑定；也可在 `$WORK` 下按下方命令手动跑。
- 本仓私有 + 目录 700，同事**拿 zip 不拿仓库**；包内含公司表单结构，**仅限公司内部分发**。

## 每周 SOP（周一 17:00 前；半自动闭环约 5 分钟人工）

下列命令以**维护仓即 `$WORK`** 为例（路径含 `skills/…`）。同事在独立 `$WORK` 下应使用
`"$SKILL/scripts/…"`（由 skill/agent 解析；或 `~/.claude/skills/dingtalk-weekly-report/scripts/…`）。

```bash
cd ~/ilabel/dingtalk-weekly-report   # 或 cd $WORK

# 0) 前提：PROGRESS_REPORT.md 已更新覆盖目标周（没更新先去更新，工具不凑数）
# 1) 生成草稿（缺省=上一个周一）→ 人工审改 json（逐日 content/休假行/summary/next_week）
python3 skills/dingtalk-weekly-report/scripts/extract_week.py
# 2) 生成附件
python3 skills/dingtalk-weekly-report/scripts/gen_attachment.py weeks/week_report_YYYYMMDD.json
# 3) 登录态：每日 9:30 cron keepalive 滚动续命（crontab -l；output/keepalive.log）。
#    仅当报「会话已失效」：钉钉「打印内部二维码」→ 手机扫 →
.venv/bin/python skills/dingtalk-weekly-report/scripts/fill_form.py --login-url '<h3yun entry/auth 链接>'   # 链接 48h 有效
# 4) 半自动填表落草稿（截图 20-filled-review.png / 30-saved.png 可先核对）
.venv/bin/python skills/dingtalk-weekly-report/scripts/fill_form.py weeks/week_report_YYYYMMDD.json --draft
# 5) 钉钉打开该草稿 → 人工核对 → 点「提交」（提交永远留给人）

# 回退：print_form_rows.py 出粘贴块，手工填
python3 skills/dingtalk-weekly-report/scripts/print_form_rows.py weeks/week_report_YYYYMMDD.json
```
## 文件

| 文件 | 作用 |
|---|---|
| `skills/dingtalk-weekly-report/SKILL.md` | 技能指令（Claude Code 入口，`$SKILL`/`$WORK` 双路径模型） |
| `skills/dingtalk-weekly-report/install.sh` | 技能自安装（copy / `--link` / `--force`；清理旧名；Codex 桥接） |
| `skills/dingtalk-weekly-report/scripts/extract_week.py` | ① 工作日志 → `weeks/week_report_*.json` 草稿（拒绝覆盖已有文件） |
| `skills/dingtalk-weekly-report/scripts/gen_attachment.py` | ② json → `output/YYYYMMDD-YYYYMMDD本周工作总结与下周计划.xlsx` |
| `skills/dingtalk-weekly-report/scripts/print_form_rows.py` | ② json → 表单粘贴块（回退路径） |
| `skills/dingtalk-weekly-report/scripts/fill_form.py` | ③ Playwright 半自动填表（模式速查见下表） |
| `skills/dingtalk-weekly-report/scripts/xlsxlite.py` | 极简 xlsx 写入器（stdlib 手写 OOXML，零依赖） |
| `skills/dingtalk-weekly-report/scripts/dtwr_common.py` | 工作目录解析（`DTWR_HOME`/cwd，缺 config.json 即 fail-loud） |
| `skills/dingtalk-weekly-report/references/FIELDS.md` | **表单字段事实源**：氚云字段编码 + 合法枚举值 + DOM 坑 |
| `skills/dingtalk-weekly-report/assets/config.example.json` | 个人配置模板 |
| `install.sh` | 维护仓入口，转调技能包 `install.sh` |
| `pack-skill.sh` | 打平铺 zip 到 `dist/`（分发用） |
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
| 改技能脚本后分发给同事 | `bash tests/run_mock_test.sh`（若动 fill_form）→ `bash pack-skill.sh` → 发 zip；对方 `install.sh --force` |
| 本机重挂技能（维护仓） | `bash install.sh --link`（已对齐则无需再跑；换模式加 `--force`） |
| 机器迁移 | `uv venv .venv && uv pip install playwright && .venv/bin/playwright install chromium`（PEP 668 用 uv）+ 重建登录态 + 重挂 cron + 重跑 `install.sh` |

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
- [x] **P-A（产品化）**：Claude Code Skill `/dingtalk-weekly-report`（自安装技能包 + 维护仓 `--link`）
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
