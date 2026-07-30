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

## 值长什么样

公开仓不含任何真实值，但**形状是通用的**——知道形状才能判断管理员给的东西对不对、
`dump.html` 里该找什么。下表用掩码示意，`#` 代表数字、`x` 代表十六进制字符：

| 键 | 形状 | 从哪看 |
|---|---|---|
| `form_url` | `https://<租户>.h3yun.com/...`，通常带租户与表单标识的查询参数 | 浏览器打开周报列表页的地址栏 |
| `subgrid_id` | 32 位小写十六进制串，形如 `xxxxxxxx…`（共 32 字符） | 子表容器的 DOM `id` |
| `start_date` / `note` / `row_*` | 大写 `F` + 7 位数字，形如 `F#######` | 各字段控件的 DOM `id` |
| `form_texts.*` | 界面上的**可见原文**，注意按钮文字可能带空格（如「暂 存」） | 照抄屏幕 |
| `vocabulary.*` | 下拉选项的**完整原文**，不能简写 | 展开下拉逐条抄 |
| `form_project` / `attach_project` | 项目下拉的完整原文，两者**可能不同** | 表单下拉 / 附件模板 |
| `holidays` / `extra_workdays` | `YYYY-MM-DD` 列表，可留空 | 当年国务院放假安排；同一天不能同时出现在两个列表里 |

自查：`form_fields` 的十个值只允许字母、数字、下划线、连字符（`configure.py` 会拒绝其它字符）；
子表 id 与字段 id 形状不同，拿到一堆同形状的值说明抄错了地方。

## 向表单管理员索取（可直接复制）

> 你好，我要用脚本把周报填成草稿（只暂存、不提交，最终仍由我本人在钉钉核对后提交）。
> 麻烦提供报工周报表单的以下信息：
> 1. 表单列表页地址；
> 2. 「工作详情」子表容器的 DOM id，以及子表内日期/项目类型/项目名称/工作状态/工时/
>    主要工作内容六个字段的 DOM id；
> 3. 主表「报工开始日期」「附件」「特殊情况说明」三个字段的 DOM id；
> 4. 「新增」「暂存」按钮的可见文字原文，列表页标题文字，暂存成功的提示文案；
> 5. 「项目类型」「工作状态」两个下拉的全部合法选项原文；
> 6. 附件模板里「任务类型」的全部合法值。
> 只需要字段标识和选项文字，不需要任何账号或权限。

拿不到人也没关系，下节的 `--dump` 能自己扒。

## 获取配置（推荐：自动发现）

1. 运行 `configure.py --missing`；用 `configure.py --guided` 先填 `form_url`、姓名和项目原文。
   `--guided` 允许分阶段保存，`form_fields` 十个 id **此时全部留空**。
2. `fill_form.py --login`（或 `--login-url`）建立登录态。
3. `fill_form.py --dump-record 2` —— 打开第 2 条历史记录（避开可能是草稿的第 1 条），
   自动推断字段并把候选写到 `$WORK/output/field-proposal.json`。只读，不保存。
4. `configure.py --from-discovery` —— 逐项确认后写入，**绝不自动采纳候选**；即使其他配置
   尚未补齐，已确认字段也能安全分阶段保存。
5. `configure.py --check` 直到通过。

自动发现靠三重信号叠加：主表看控件类型类名（`control-adapter-Form*`）、子表看取值形状
（日期/数字/长短混杂）、形状分不开的再看取值是否属于已配的枚举。真机实测 10 项中自动定位
8 项、零错误，另 2 项给出候选由人二选一。

**枚举（`vocabulary`）仍需人工确认**：`--dump-record` 会列出该记录里观察到的取值，但那只是
**你用过的值**，不等于全集（没休过假就学不到休假状态）。多跑几条记录取并集能提高覆盖。
`--harvest-enums` 本想展开下拉取全集，但实测本表单**孤立点开取不到选项**（与下节「关联下拉
孤立探测无数据」是同一现象），现降级为诊断工具。

## 获取配置（手动兜底）

1. 运行 `configure.py --guided`，**先填能直接回答的** `form_url`、姓名和项目原文；按钮文字、
   下拉枚举随后由真实表单或管理员确认。
   `form_fields` 里的十个字段 id **此时可以全部留空**。
2. `fill_form.py --login`（或 `--login-url`）建立登录态。
3. `fill_form.py --dump` → 产出 `$WORK/output/shots/dump.html` 与 `dump.png`。
   **该模式只要求 `form_url` 与 `form_texts.add_row` / `start_date_label`**，不校验字段 id——
   找出字段 id 正是它的用途。
4. 在 `dump.html` 里按上表形状定位各控件 id，回填 `config.json`。
5. `scripts/configure.py --check` 直到通过。
6. 之后 `fill_form.py` 报字段未命中时，只改当前用户配置；**不要把真实值提交到公开仓库**。

一次性 `entry/auth` 链接不是 `form_url`，不得进入配置、聊天、命令参数、文件或 Git。

## 通用 DOM 约束

- 表单通常在 URL 含 `FormAdapter` 的 iframe 内渲染。
- 子表行使用 `[id="<subgrid_id>"] .ant-spin-container > .subgrid-sheet__row`，避免命中行内
  同名滚动容器。
- 日期控件通过 readonly input 打开日历，再向 `.ant-calendar-input` 输入日期并回车。
- 下拉按精确文本从后往前查找可见项，避免命中先前行残留的隐藏菜单。
- 附件通过 `input[type=file]` 上传。
- 草稿成功必须观察到可见成功 selector 或配置的 `success_messages`；表单关闭本身不算成功。
- 列表页**列优先渲染**：每列一个容器、内含各行单元格，所以按「行」切分取不到值；
  要按列下标对齐读（如 `tg-c-6` = 报工开始日期、`.cell-status` = 状态）。
- 附件是**受控上传组件**：上传成功后原生 `input[type=file]` 会被清空（`files.length==0` 属正常）。
  完成证据用 `.h3-upload-list__item.is-success` 的 `title`；已挂文件的移除按钮是 `anticon-close`。
- 编辑既有记录时：日期控件**已有值则点 input 不弹面板**（改点 `.ant-calendar-picker-icon`），
  且页面存在多个 `.ant-calendar-input`，只有可见的那个能用；写入后应回读校验。
- 点「暂存」后 FormAdapter frame 会 **detach**，遍历 `page.frames` 查询它会抛错——需跳过。
- 列表页是自有网格：行 `.tg-row`、单元格 `.tg-cell.tg-c-<N>`（列序编号，与表头一一对应）、
  记录标题 `span.tg-link`。标题**不是 `<a href>`**，打开记录只能点击，无法用 URL 直取。
