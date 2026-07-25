# 氚云周报表单配置

本项目不分发任何组织的真实表单 URL、组件 ID、项目名称或下拉枚举。运行时唯一事实源是每位用户
私有 `$WORK/config.json`；`scripts/dtwr_fields.py` 只定义通用配置键。

## `form_fields`

值填写对应控件的 DOM `id`，不要带 `#`。只允许字母、数字、下划线和连字符。

| 配置键 | 含义 |
|---|---|
| `subgrid_id` | 工作详情子表容器 |
| `start_date` | 周报开始日期 |
| `attach` | 附件上传。**唯一可留空的字段**：留空 = 本表单没有附件项，填表时整步跳过；填了则附件必须存在，且上传后必须出现附件名才继续 |
| `note` | 特殊情况说明 |
| `row_date` | 子表行日期 |
| `row_type` | 子表行项目类型 |
| `row_project` | 子表行项目/产品 |
| `row_status` | 子表行工作状态 |
| `row_hours` | 子表行工时 |
| `row_content` | 子表行主要工作内容 |

## `form_texts`

按钮和标签文本必须与当前表单可见文本一致。

| 配置键 | 含义 |
|---|---|
| `report_title` | 列表页用于确认会话有效的周报标题 |
| `add_row` | 子表新增行按钮 |
| `start_date_label` | 新增表单中的开始日期标签 |
| `save_draft` | 暂存/保存草稿按钮；不得配置成提交按钮 |
| `success_messages` | 暂存成功时可能出现的可见提示列表 |

## `vocabulary`

所有枚举都从当前组织的表单下拉或附件模板抄录，不得由 Agent 猜测。

| 配置键 | 含义 |
|---|---|
| `project_types` | 表单允许的项目类型 |
| `statuses` | 表单允许的工作状态 |
| `attachment_task_types` | 附件允许的任务类型，必须是 `project_types` 子集 |
| `operations_project_type` | 允许项目名称为空的组织运营类型 |
| `leave_status` | 允许主要工作内容为空的休假状态 |

`form_project` 是表单项目下拉的完整可见原文；`attach_project` 是附件中的关联项目/活动。两者可能
不同，必须分别由用户或表单管理员确认。

## 获取配置

1. 向表单管理员索取字段 ID、可见按钮文本和合法下拉值；或在有权访问的浏览器中检查 DOM。
2. 先完成 `$WORK/config.json`，再运行 `scripts/configure.py --check`。
3. 已登录后可运行 `fill_form.py --dump`，检查 `$WORK/output/shots/dump.html` 与 `dump.png`。
4. `fill_form.py` 报字段未命中时，仅修改当前用户配置；不要把真实值提交到公开仓库。

一次性 `entry/auth` 链接不是 `form_url`，不得进入配置、聊天、命令参数、文件或 Git。

## 通用 DOM 约束

- 表单通常在 URL 含 `FormAdapter` 的 iframe 内渲染。
- 子表行使用 `[id="<subgrid_id>"] .ant-spin-container > .subgrid-sheet__row`，避免命中行内
  同名滚动容器。
- 日期控件通过 readonly input 打开日历，再向 `.ant-calendar-input` 输入日期并回车。
- 下拉按精确文本从后往前查找可见项，避免命中先前行残留的隐藏菜单。
- 附件通过 `input[type=file]` 上传。
- 草稿成功必须观察到可见成功 selector 或配置的 `success_messages`；表单关闭本身不算成功。
