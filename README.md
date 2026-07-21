# dingtalk-weekly-report — 钉钉「报工周报」填写工具

基于 ts-platform 的 `docs/report/PROGRESS_REPORT.md` 生成钉钉「工作申请 → 报工周报」所需的
附件 xlsx 与表单粘贴内容。设计与调研见
`~/ilabel/ts-platform/docs/designs/design-dingtalk-weekly-report-tool.md`。

**纯 stdlib，零第三方依赖**（本机 python 受 PEP 668 管制、无 python3-venv，xlsx 用自带的
`xlsxlite.py` 生成）。独立个人项目，不进 ts-platform 团队仓库。

## 每周 SOP（周一 17:00 前，约 10 分钟）

```bash
cd ~/ilabel/dingtalk-weekly-report

# 0) 前提：PROGRESS_REPORT.md 已更新覆盖上周（没更新先去更新，工具不凑数）
# 1) 生成草稿（缺省=上一个周一；也可显式传周一日期）
python3 extract_week.py 2026-07-13
# 2) 人工审改 weeks/week_report_20260713.json：
#    - 逐日 content 润色（可让 Claude Code 基于 PROGRESS_REPORT 代写后过目）
#    - 休假/调休日改 status 与说明；summary/next_week 填实
# 3) 生成附件 + 粘贴块
python3 gen_attachment.py weeks/week_report_20260713.json
python3 print_form_rows.py weeks/week_report_20260713.json
# 4) 打开钉钉「报工周报-新增」：传附件 → 按粘贴块逐行新增工作详情 → 自查 → 提交
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
| `weeks/` | 每周 json（入库留痕） |
| `output/` | 生成的附件（gitignored） |

## 表单硬规则（工具自查清单已内置）

- 晚于**周一 17:00** 提交上周报 = 报工不合格
- 法定节假日/休假当天需报 8h，状态选「休假」；正常周末与调休放假**不报工**
- 任务类型枚举：产品研发 / 交付项目 / 售前活动 / 知识产权 / 其他
- 附件 ≤10MB，命名 `YYYYMMDD-YYYYMMDD本周工作总结与下周计划.xlsx`（周一-周五）
- 工作详情**一天可多行**（站会 0.5h + 开发主行 + 临时会议），字段合法取值见 `FIELDS.md`；
  表单「项目/产品名称」选 D-PD-26002 标注平台（≠附件里的 D-DP-25002 工智酷博，两处编号不同是常态）

## 路线图

- [x] **P1（路径 C）**：内容生成 + 附件 xlsx + 人工粘贴（当前形态）
- [ ] **P2（路径 B）**：`fill_form.py` Playwright 半自动——扫码登录持久化、自动填表+传附件，
      **停在提交前人工点提交**（加 `--submit` 才自动提交）。前置：确认表单 URL（宜搭域名）。
- [ ] **P3（路径 A，可选）**：宜搭 OpenAPI 直提（`POST /v1.0/yida/formInstances`）。
      前置条件与验证步骤见设计文档 §3.1；需要企业应用凭证 + 宜搭 systemToken。
# dingtalk-weekly-report
