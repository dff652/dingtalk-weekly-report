# 维护者指南

面向克隆本仓库的维护者。用户安装与每周使用见 [../skills/dingtalk-weekly-report/USER_GUIDE.md](../skills/dingtalk-weekly-report/USER_GUIDE.md) 与根 [README.md](../README.md)。

## 仓库角色

| 路径 | 职责 | 进 zip？ |
|------|------|----------|
| `skills/dingtalk-weekly-report/` | 技能包（`$SKILL`） | 是（平铺为 zip 根） |
| 根 `config.json` / `weeks/` / `output/` / `.venv/` | 维护者本机 `$WORK` 实例 | 否 |
| `~/.config/dtwr/` | 指针 + 登录态 | 否 |
| `pack-skill.sh` / 根 `install.sh` | 打包 / 转调技能 install | 否 |
| `tests/` | 仿真 e2e / 冒烟 | 否 |

本仓可同时是维护仓 + 自己的 `$WORK`（`~/.config/dtwr/root` 指向仓库根）。同事默认 `$WORK=~/weekly-report-data`。

## 本机开发

```bash
bash install.sh --link              # ~/.claude + ~/.codex skills 软链到仓内
# 改代码即时生效；勿对软链误跑无 --force 的 copy 安装
bash tests/run_mock_test.sh         # 改 fill_form 后必跑
bash tests/run_smoke.sh             # pack + 隔离 install + 附件 + 仿真
bash pack-skill.sh                  # dist/dingtalk-weekly-report-skill-YYYYMMDD.zip
```

生态安装自测（隔离 HOME 更安全）：

```bash
npx skills add dff652/dingtalk-weekly-report -l -y
npx skills add dff652/dingtalk-weekly-report -s dingtalk-weekly-report -a claude-code -a codex -g -y --copy
```

注意：`npx skills -a codex` 常装到 `~/.agents/skills`，不一定写 `~/.codex/skills`（README 补链步骤）。

## fill_form 模式

| 命令 | 作用 | 何时用 |
|------|------|--------|
| `… json` | 只填不存 | 预览 |
| `… json --draft` | 暂存草稿 | **每周正式** |
| `… json --submit` | 直接提交 | 政策上不用 |
| `--login-url` | token 登录 | 会话失效 |
| `--login` | 扫码 | 兜底 |
| `--keepalive` | 续 cookie | cron / 计划任务 |
| `--dump` | DOM 诊断 | 联调 |

## 维护触发表

| 触发 | 动作 |
|------|------|
| 每周例行 | 更新内容源 + `weeks/week_report_*.json` |
| 会话失效 | 内部二维码 → `--login-url` |
| 换项目 | `config.json` 的 form/attach project |
| HR 改字段 | `FIELDS.md` + `fill_form.py` 映射 |
| DOM 变化 | `--dump` → 改选择器 → `run_mock_test.sh` |
| 分发同事 | `run_smoke.sh` → `pack-skill.sh` 或推 GitHub 用 `npx skills` |
| 环境坏 | `bootstrap.sh --force-venv` + 重登 |

## 调试

- 失败截图：`$WORK/output/shots/99-error.png`
- `--dump` → dump.html / dump.png
- 登录态：`~/.config/dtwr/state.json`（0600，勿入 git）

## 表单硬规则（工具侧）

- 补交上周：**周一 17:00** 前
- 休假日报 8h 状态「休假」；正常周末不报
- 附件命名 `YYYYMMDD-YYYYMMDD本周工作总结与下周计划.xlsx`；content ≤200 字
- 表单项目 ≠ 附件项目编号属常态（见 FIELDS.md）

## 测试覆盖

```bash
bash tests/run_smoke.sh
bash tests/run_mock_test.sh
.venv/bin/python skills/dingtalk-weekly-report/scripts/fill_form.py --keepalive  # 可选真机
```

| 项 | 自动？ |
|----|--------|
| pack / 隔离 install / 附件 / 仿真 e2e | ✅ |
| 真机 keepalive | 可选 |
| 真机 `--draft` / 钉钉提交 | ❌ 人工 |

## 路线图

- [x] P1 内容 + 附件 + 粘贴
- [x] P-A Skill 包 + install/bootstrap + GitHub/`npx skills`
- [x] P2 Playwright 真机联调 + 仿真 e2e
- [ ] P3 氚云 OpenApi（缺 EngineSecret）

设计背景：`~/ilabel/ts-platform/docs/designs/design-dingtalk-weekly-report-tool.md`（本机路径，非本仓）。

## 跨平台运行时（不换 TS）

| 层 | 做法 |
|----|------|
| Skill | `npx skills` / install.sh → 标准 skills 目录 |
| Python | uv + `$WORK/.venv` |
| 浏览器 | Playwright 自带 Chromium |
| 保活 | cron / Windows 计划任务 |
