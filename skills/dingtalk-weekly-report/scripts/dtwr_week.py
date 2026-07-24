"""目标周和无年份日志标题的纯日期逻辑。"""
from datetime import date, timedelta


def pick_monday(argv, today=None) -> date:
    if len(argv) > 1:
        try:
            monday = date.fromisoformat(argv[1])
        except ValueError as exc:
            raise ValueError(f"日期格式错误: {argv[1]!r}；请传 YYYY-MM-DD") from exc
    else:
        today = today or date.today()
        offset = 7 if today.weekday() == 0 else today.weekday()
        monday = today - timedelta(days=offset)
    if monday.weekday() != 0:
        raise ValueError(f"{monday} 不是周一；请传周一日期")
    return monday


def date_near_week(month, day, monday):
    candidates = []
    for year in (monday.year - 1, monday.year, monday.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            continue
    if not candidates:
        raise ValueError(f"无效月日: {month}月{day}日")
    return min(candidates, key=lambda value: abs((value - monday).days))
