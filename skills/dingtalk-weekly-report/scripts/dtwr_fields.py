"""表单枚举的运行时唯一事实源。"""

PROJECT_TYPES = (
    "产品研发",
    "交付项目",
    "售前活动",
    "知识产权",
    "公司和部门运营活动",
    "其他",
)

ATTACHMENT_TASK_TYPES = tuple(
    value for value in PROJECT_TYPES if value != "公司和部门运营活动"
)

STATUSES = (
    "算法开发",
    "内部会议",
    "内外部会议",
    "休假",
    "其它",
)
