# SPDX-License-Identifier: Apache-2.0
"""配置驱动的表单字段与词表结构。"""

FORM_FIELD_KEYS = (
    "subgrid_id",
    "start_date",
    "attach",
    "note",
    "row_date",
    "row_type",
    "row_project",
    "row_status",
    "row_hours",
    "row_content",
)

# 留空 = 本表单没有这个字段。附件字段是**组织事实**（该表单有没有附件项），
# 不是每周的执行选择，所以由配置一次性决定，不提供 CLI 开关——那会变成
# 「生成失败就加参数绕过」的逃生口。其余字段一律必填。
OPTIONAL_FORM_FIELD_KEYS = ("attach",)

FORM_TEXT_KEYS = (
    "report_title",
    "add_row",
    "start_date_label",
    "save_draft",
)

VOCABULARY_LIST_KEYS = (
    "project_types",
    "statuses",
    "attachment_task_types",
)

VOCABULARY_VALUE_KEYS = (
    "operations_project_type",
    "leave_status",
)

# 假期与调休：均为可选的 YYYY-MM-DD 列表，留空即沿用「周一至周五」。
# 不内置年度节假日表（过期的表比没有表更危险），也不联网获取。
CALENDAR_LIST_KEYS = ("holidays", "extra_workdays")

# 工时口径：daily_hours 是**每天合计上限（会议含在内）**，weekly_hours_cap 是每周上限。
# 二者都可选；留空即沿用旧行为（开发行取 hours、不设周上限）。
HOURS_POLICY_KEYS = ("daily_hours", "weekly_hours_cap")
