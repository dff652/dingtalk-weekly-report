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

## 每周 SOP（周一 17:00 前；半自动闭环约 5 分钟人工）

```bash
cd ~/ilabel/dingtalk-weekly-report

# 0) 前提：PROGRESS_REPORT.md 已更新覆盖上周（没更新先去更新，工具不凑数）
# 1) 生成草稿（缺省=上一个周一）→ 人工审改 json（逐日 content/休假行/summary/next_week）
python3 extract_week.py
# 2) 生成附件
python3 gen_attachment.py weeks/week_report_YYYYMMDD.json
# 3) 登录态检查：过期则重新「打印内部二维码」→ 手机钉钉扫 → 复制跳转链接 →
.venv/bin/python fill_form.py --login-url '<h3yun entry/auth 链接>'   # token 48h 有效
# 4) 半自动填表落草稿（填完自动截图 20-filled-review.png 可先核对）
.venv/bin/python fill_form.py weeks/week_report_YYYYMMDD.json --draft
# 5) 钉钉里打开该草稿 → 人工核对 → 点「提交」（提交动作永远留给人）

# 回退路径（半自动不可用时）：print_form_rows.py 出粘贴块，手工填
python3 print_form_rows.py weeks/week_report_YYYYMMDD.json
```

## 文件

| 文件 | 作用 |
|---|---|
| `config.json` | 姓名/项目/默认工时/PROGRESS_REPORT 路径等常量 |
| `extract_week.py` | ① PROGRESS_REPORT.md → `weeks/week_report_*.json` 草稿（拒绝覆盖已有文件） |
| `gen_attachment.py` | ② json → `output/YYYYMMDD-YYYYMMDD本周工作总结与下周计划.xlsx` |
| `print_form_rows.py` | ② json → 表单粘贴块（content 有 TODO 会拒绝出块） |
| `xlsxlite.py` | 极简 xlsx 写入器（stdlib zipfile + 手写 OOXML） |
| `FIELDS.md` | **表单字段事实源**：宜搭组件 ID + 合法枚举值 + 真实填报风格（逆向自数据管理页导出文件） |
| `fill_form.py` | ③ P2：Playwright 半自动填表（`--login` 扫码 / `--dump` 诊断 / 填表+截图确认提交） |
| `tests/mock_form.html` + `tests/run_mock_test.sh` | 本地仿真宜搭表单 e2e（改 fill_form 后跑它回归） |
| `weeks/` | 每周 json（入库留痕） |
| `output/` | 生成的附件与截图（gitignored） |

## 表单硬规则（工具自查清单已内置）

- 晚于**周一 17:00** 提交上周报 = 报工不合格
- 法定节假日/休假当天需报 8h，状态选「休假」；正常周末与调休放假**不报工**
- 任务类型枚举：产品研发 / 交付项目 / 售前活动 / 知识产权 / 其他
- 附件 ≤10MB，命名 `YYYYMMDD-YYYYMMDD本周工作总结与下周计划.xlsx`（周一-周五）
- 工作详情**一天可多行**（站会 0.5h + 开发主行 + 临时会议），字段合法取值见 `FIELDS.md`；
  表单「项目/产品名称」选 D-PD-26002 标注平台（≠附件里的 D-DP-25002 工智酷博，两处编号不同是常态）

## 路线图

- [x] **P1（路径 C）**：内容生成 + 附件 xlsx + 人工粘贴（当前形态）
- [x] **P2（路径 B）**：`fill_form.py` Playwright 半自动，**真机联调已通**（2026-07-21：token 免扫码登录、
      新增、开始日期、附件上传、10 行子表含关联项目选择与负责人联动全走通；坑与选择器事实源见
      `FIELDS.md`「P2 真机联调发现」）。默认只填不存，`--draft` 落草稿（推荐）、`--submit` 直接提交。
      环境：`uv venv .venv && uv pip install playwright && .venv/bin/playwright install chromium`（已装好）。
      无显示器服务器工作流：
      1. `config.json` 填 `form_url`（钉钉里复制「报工周报-新增」链接）
      2. `.venv/bin/python fill_form.py --login` → VSCode 打开 `output/shots/login.png` 手机钉钉扫码
         → 登录态存 `~/.config/dtwr/state.json`（0600，勿入 git）
      3. `.venv/bin/python fill_form.py weeks/week_report_*.json` → 自动填表+传附件 → 截图核对
         → 终端输 `yes` 才提交（`--submit` 跳过确认）；失败自动截图 `output/shots/99-error.png` 供联调
      填表逻辑已过本地仿真 e2e（`bash tests/run_mock_test.sh`，10 行全字段断言）；子表单元格按
      「列头文本→列号」定位不猜 DOM 顺序。真实页面首轮先跑 `fill_form.py --dump` 拿
      HTML/截图/字段清单，再按差异微调选择器（仿真≠真实 DOM，联调 1-2 轮预期内）。
- [ ] **P3（路径 A，可选）**：宜搭 OpenAPI 直提（`POST /v1.0/yida/formInstances`）。
      组件 ID 已从导出文件拿到（见 `FIELDS.md`），仅剩企业应用凭证 + 宜搭 systemToken 两个卡点；
      验证步骤见设计文档 §3.1。
# dingtalk-weekly-report
