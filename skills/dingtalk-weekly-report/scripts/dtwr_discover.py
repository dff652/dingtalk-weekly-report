# SPDX-License-Identifier: Apache-2.0
"""从一条**已填**历史记录的 DOM 推断 `form_fields` 候选映射。

空白新增表单只有控件 id、没有值，而「哪个是工时、哪个是状态」在空白表单上没有可靠信号——
实测已否掉按标签认字段（控件附近无标签文本、`title` 属性 15 个候选只命中 1 个、无表头结构）。
已填记录里每个控件装着值，值的形态才是强信号。

记录页里**两个区域用两套信号**（这是实测结论，不能只用一套）：

- **主表**字段带 `control-adapter-Form<类型>` 类，类型是**显式**的：
  `FormAttachment` → `attach`、`FormTextArea` → `note`、`FormDateTime` → 日期字段。
- **子表行**字段在查看态是网格渲染、**没有**这些类，只能靠取值：同一 id 在每行重复出现，
  聚合后判形状——日期 → `row_date`、数字 → `row_hours`、长短混杂 → `row_content`。
- 形状分不开的 `row_type` / `row_status` / `row_project` 再叠**枚举归属**：
  取值 ∈ `project_types` / ∈ `statuses` / == `form_project`。枚举来自展开下拉，是独立来源。

**产物永远是候选，绝不自动写入配置。** 组织私有面必须由人确认——这是本项目的不变量之一。
"""
import re
from collections import Counter

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NUMBER_RE = re.compile(r"^\d+(\.\d+)?$")
_ID_RE = re.compile(r'id="([^"]+)"')
_KIND_RE = re.compile(r"control-adapter-(Form\w+)")
_VALUE_RE = re.compile(r'value="([^"]*)"')
# 窗口从开标签的 ">" 之后开始，所以直属文本在窗口**开头**；
# 若先匹配 ">"，取到的会是下一个元素的文本（off-by-one，简单标记下立刻暴露）。
_DIRECT_TEXT_RE = re.compile(r"^\s*([^<>]{1,200})<")
_NESTED_TEXT_RE = re.compile(r">([^<]{1,200})<")
_TAG_RE = re.compile(r"<\w+([^>]*)>")
_SUBGRID_ID_RE = re.compile(r"^[0-9a-f]{32}$")
# 字段 id 的通用形状：字母开头的标识符。刻意**不**写死某个厂商的具体形态
# （如"大写字母 + 7 位数字"），换个租户就会失效。
_FIELD_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{3,}$")

LONG_TEXT_MIN = 40


def value_shape(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "empty"
    if _DATE_RE.fullmatch(value):
        return "date"
    if _NUMBER_RE.fullmatch(value):
        return "number"
    if len(value) > LONG_TEXT_MIN:
        return "long_text"
    return "short_text"


class Candidate:
    """一个候选字段。同一 id 在子表每行重复出现，取值聚合后才好判形状。"""

    def __init__(self, element_id, control_kind, in_subgrid):
        self.element_id = element_id
        self.control_kind = control_kind      # FormDateTime / FormAttachment / … 或 None
        self.in_subgrid = in_subgrid
        self.values = []

    @property
    def shapes(self):
        return Counter(value_shape(v) for v in self.values)

    def dominant(self, shape, ratio=0.8):
        profile = self.shapes
        total = sum(profile.values())
        return bool(total) and profile.get(shape, 0) / total >= ratio

    def texts(self):
        return {v.strip() for v in self.values if v.strip()}


def analyse(html: str):
    """返回 (子表容器 id, {id: Candidate})。

    取值提取用「标签属性 + 紧随窗口」而不是建 DOM 树：记录页里 `<input>` 与承载 id 的容器
    隔了很深的层级，按子树取值几乎什么都拿不到（实测树遍历只捞到 2 个控件）。
    """
    # 先找「class 含 subgrid 且 id 是 32 位十六进制」的强匹配；找不到再放宽到任意 id。
    # 不把十六进制当硬条件——那是某个租户的形态，换一家就失效。
    subgrid_id = None
    for require_hex in (True, False):
        for match in _TAG_RE.finditer(html):
            attrs = match.group(1)
            if "subgrid" not in attrs:
                continue
            found = _ID_RE.search(attrs)
            if not found:
                continue
            if require_hex and not _SUBGRID_ID_RE.fullmatch(found.group(1)):
                continue
            subgrid_id = found.group(1)
            break
        if subgrid_id:
            break

    subgrid_pos = html.find(f'id="{subgrid_id}"') if subgrid_id else len(html)
    candidates = {}
    for match in _TAG_RE.finditer(html):
        attrs = match.group(1)
        found = _ID_RE.search(attrs)
        if not found:
            continue
        element_id = found.group(1)
        if element_id == subgrid_id or not _FIELD_ID_RE.fullmatch(element_id):
            continue
        kind = _KIND_RE.search(attrs)
        candidate = candidates.get(element_id)
        if candidate is None:
            candidate = Candidate(element_id, kind.group(1) if kind else None,
                                  match.start() > subgrid_pos)
            candidates[element_id] = candidate
        elif kind and not candidate.control_kind:
            candidate.control_kind = kind.group(1)
        window = html[match.end():match.end() + 900]
        value = _VALUE_RE.search(attrs) or _VALUE_RE.search(window[:300])
        text = _DIRECT_TEXT_RE.search(window) or _NESTED_TEXT_RE.search(window)
        raw = value.group(1) if value else (text.group(1) if text else "")
        if raw.strip():
            candidate.values.append(raw.strip())
    return subgrid_id, candidates


def _only(candidates, predicate):
    """恰好一个命中才算数——多个命中说明这重信号不足以区分，留给下一重或人。"""
    hits = [c for c in candidates if predicate(c)]
    return hits[0] if len(hits) == 1 else None


def propose_fields(html: str, vocabulary=None, form_project=""):
    """产出候选映射与歧义清单。

    返回 `(proposal, ambiguous)`：
    `proposal = {配置键: {"id": ..., "confidence": ..., "why": 证据}}`，
    `ambiguous = {配置键: [候选 id, ...]}`。**调用方必须逐项让用户确认后才写入配置。**
    """
    vocabulary = vocabulary or {}
    project_types = set(vocabulary.get("project_types") or ())
    statuses = set(vocabulary.get("statuses") or ())
    subgrid_id, candidates = analyse(html)

    proposal, ambiguous = {}, {}
    if subgrid_id:
        proposal["subgrid_id"] = {"id": subgrid_id, "confidence": "high",
                                  "why": "class 含 subgrid 且 id 为 32 位十六进制，全表单唯一"}

    mains = [c for c in candidates.values() if not c.in_subgrid]
    rows = [c for c in candidates.values() if c.in_subgrid]

    def claim(key, candidate, confidence, why):
        if candidate is not None and key not in proposal:
            proposal[key] = {"id": candidate.element_id,
                             "confidence": confidence, "why": why}
            return True
        return False

    def taken():
        return {v["id"] for v in proposal.values()}

    def by_kind(pool, kind):
        return [c for c in pool if c.control_kind == kind]

    # ---- 主表：控件类型是显式信号 ----
    for key, kind, why in (
        ("attach", "FormAttachment", "控件类型 FormAttachment，全表单唯一"),
        ("note", "FormTextArea", "控件类型 FormTextArea"),
    ):
        hits = by_kind(mains, kind)
        if len(hits) == 1:
            claim(key, hits[0], "high", why)
        elif len(hits) > 1:
            ambiguous[key] = [c.element_id for c in hits]

    dates = by_kind(mains, "FormDateTime")
    if len(dates) == 1:
        claim("start_date", dates[0], "high", "主表唯一的 FormDateTime")
    elif len(dates) > 1:
        # 开始/结束日期同为 FormDateTime，类型信号分不开——但**开始日期一定早于结束日期**，
        # 用取值本身消歧；取值缺失或并列时才交给人。
        dated = [(min(c.texts()), c) for c in dates
                 if c.texts() and all(_DATE_RE.fullmatch(v) for v in c.texts())]
        earliest = sorted(dated, key=lambda pair: pair[0])
        if len(earliest) >= 2 and earliest[0][0] < earliest[1][0]:
            claim("start_date", earliest[0][1], "high",
                  "两个日期控件中取值较早的那个（开始日期必早于结束日期）")
        else:
            ambiguous["start_date"] = [c.element_id for c in dates]

    # ---- 子表：值形状 ----
    claim("row_date", _only(rows, lambda c: c.dominant("date")),
          "high", "每行取值均为日期")
    claim("row_hours", _only(rows, lambda c: c.dominant("number")),
          "high", "每行取值均为数字")
    claim("row_content", _only(rows, lambda c: c.shapes.get("long_text", 0) > 0),
          "high", "存在超长取值——内容字段长短混杂是其特征")

    # ---- 子表：枚举归属（形状分不开的三个）----
    for key, allowed, why in (
        ("row_type", project_types, "取值全部属于 vocabulary.project_types"),
        ("row_status", statuses, "取值全部属于 vocabulary.statuses"),
    ):
        if not allowed:
            continue
        pool = [c for c in rows if c.element_id not in taken()]
        hits = [c for c in pool if c.texts() and c.texts() <= allowed]
        if len(hits) == 1:
            claim(key, hits[0], "high", why)
        elif len(hits) > 1:
            ambiguous[key] = [c.element_id for c in hits]

    if form_project:
        pool = [c for c in rows if c.element_id not in taken()]
        hits = [c for c in pool if c.texts() == {form_project}]
        if len(hits) == 1:
            claim("row_project", hits[0], "high", "取值恒等于 form_project")
        elif len(hits) > 1:
            ambiguous["row_project"] = [c.element_id for c in hits]

    for key in ("row_type", "row_status", "row_project"):
        if key not in proposal and key not in ambiguous:
            rest = [c.element_id for c in rows if c.element_id not in taken()]
            if rest:
                ambiguous[key] = rest
    return proposal, ambiguous
