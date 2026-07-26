# SPDX-License-Identifier: Apache-2.0
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


def parse_dates(values, label):
    """把 ISO 日期字符串列表解析成 date 集合。"""
    result = set()
    for item in values or ():
        if not isinstance(item, str):
            raise ValueError(f"{label} 必须是 YYYY-MM-DD 字符串列表")
        try:
            result.add(date.fromisoformat(item.strip()))
        except ValueError as exc:
            raise ValueError(f"{label} 含非法日期 {item!r}") from exc
    return result


def workdays_for(monday, holidays=(), extra_workdays=()):
    """目标周的应报工作日。

    默认周一至周五，但中国的假期制度两头都会偏离：法定假日不上班、**调休时周六周日要上班**。
    硬编码 range(5) 会在国庆/春节周强迫为放假日填工时，在调休周漏掉周末那天。

    工作日集合 = (周一~周五 − holidays) ∪ (落在本周内的 extra_workdays)。
    两个列表都由用户配置，本项目**不内置年度节假日表**——过期的表比没有表更危险——
    也不联网获取。
    """
    holidays = set(holidays)
    extra = set(extra_workdays)
    week = {monday + timedelta(days=i) for i in range(7)}
    base = {monday + timedelta(days=i) for i in range(5)}
    return sorted((base - holidays) | (extra & week))
