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
