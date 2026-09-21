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

> 氚云有**两套并存的前端**：旧版（表单在 `FormAdapter` iframe 内）与 2026-09 起的新版
> （URL 前缀 `/nx/`，表单在主 frame）。**字段编码在两套里是同一个**，所以 `config.json`
> 不用改；变的只是「用哪个属性去找它」。`fill_form.py` 运行时以「哪里能找到开始日期标签」
> 探测变体——不靠 URL 猜，灰度期两套可能同时存在。下面先列旧版约束，新版差异见后一节。

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
- 子表**分页**：每页默认 10 行（`ul.ant-pagination`，含「共N条」与每页条数切换器
  `.ant-pagination-options-size-changer`，选项在 `li.ant-select-dropdown-menu-item`）。
  行计数与 nth 定位只看当前页；「新增」超出当前页容量会自动跳到最后一页。>10 行填表
  必须先把每页条数调大到同屏（`fit_subgrid_page_size` 已内置处理）。


## 新版（nx）DOM 差异

| 对象 | 旧版 | 新版 |
|---|---|---|
| 表单载体 | `FormAdapter` iframe | 主 frame |
| 顶层控件 | `[id="<code>"]` | `.h3-control-adapter[data-test-key="<code>"]` |
| 子表容器 | `[id="<subgrid_id>"]` | `.form-grid-view[data-test-key="<subgrid_id>"]` |
| 子表行 | `.ant-spin-container > .subgrid-sheet__row` | `.fixed-table__body .fixed-table__row`（虚拟滚动，`data-row-index` 从 1 起） |
| 子表列 | `[id="<code>"]` | `[field="<code>"]`（`.fixed-table__cell`，横向也是绝对定位虚拟化） |
| 日期 | `.ant-calendar-input` 输入 + 回车 | 只读 `ant-picker`：点开后在 `.ant-picker-dropdown` 里点 `td[title="YYYY-MM-DD"]`；目标月不同要按 `.ant-picker-header-prev-btn/-next-btn` 翻页 |
| 枚举下拉 | `h3-dropdown` 精确文本 | `.ant-select` → `.ant-select-dropdown .ant-select-item-option` |
| 项目/产品名称 | 同枚举下拉 | 关联选择：`.ant-dropdown` 内带 `.h3-dropdown-content__search input` 的 **radio 列表**，选项是 `label.ant-radio-wrapper` |
| 附件 | `input[type=file]` | 无原生 input，走 file chooser |
| 暂存按钮 | `暂 存`（antd 双字按钮插空格） | `暂存` |
| 行状态（列表页） | `.cell-status` 文字 | `span.sort-num-status` **色块**，文字只在页脚图例 `.grid-footer .status-info .status-item` |
| 已挂附件项 | `.h3-upload-list__item` | `.file-card-item`（新建态外包 `ul.file-list>li`、编辑态外包 `div.file-list>div`，文件名在 `.title-item` 的 `title`） |
| 移除附件按钮 | `.anticon-close` | `svg.action-item.delete-action`（同排还有 `.desc-action` / `.download-action`，别点错） |

新版特有的坑（每条都真机踩过）：

- **新手引导 `.guide-wrapper` 是全屏遮罩**，不关掉时每一次 click 都被它吃掉；报错是
  "intercepts pointer events" 而不是「找不到元素」，极易误判成选择器写错。
  关法：循环点 `.guide-skip, .guide-close` 直到消失（引导是分步的）。
- **收起浮层不要按 Escape**——实测会连整个新增弹窗一起关掉；改点子表标题等中性区域。
- **附件上传的点击处理器挂在 `.upload-trigger-click` 里面那个 `svg` 上**：点外层 div
  既不报错也不弹文件选择器。按「svg → click 容器 → trigger」由内到外逐个试。
- **关联选择按 `.content` 的 `title` 精确匹配**，不要用 `inner_text`：命中词会被包进
  `<span class="highlight">`，且原文里的连续空格在 `white-space: pre` 下不可靠。
  搜索框整串搜常搜不到，先用首个 token（如项目编号）再退回整串。
- **行状态是颜色**：运行时从页脚图例建「颜色 → 状态」映射再翻译，**不硬编码 RGB**
  （换主题即失效）。认不出的颜色一律留空、按「不是草稿」处理——编辑既有记录会覆盖真实
  申报，猜错一次就是改掉别人已生效的周报。
- **列表首屏比旧版慢**：固定 `sleep 3s` 时 `.tg-row` 仍是 0，会把「有草稿」误判成「没有」
  进而多建一条撞周报唯一性判定。必须按元素轮询等渲染。
- `span.tg-link` / `.tg-cell.tg-c-<N>` 这套列表网格两版**通用**，不用改。
- **点列表行标题打开的可能是只读详情**（附件控件带 `control-readonly`、只有下载动作）。
  判断能不能改要看控件本身的 class，不要因为"页面打开了"就假定是编辑态。
- **旧版的附件移除类名在新版是 0 命中**。只写旧版形态时，移除会一次都没点就结束，
  然后照常上传新文件——草稿落成新旧附件并存，而日志还说"已移除"。所以移除必须以
  **附件项数量**为判据并在移不掉时 fail-loud，不能以"点了几次"为判据。
