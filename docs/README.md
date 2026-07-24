# 文档索引

| 文档 | 读者 | 说明 |
|------|------|------|
| [USER_GUIDE.md](USER_GUIDE.md) | 同事 / 维护者 | 跳转到技能包内安装与使用说明 |
| [../skills/dingtalk-weekly-report/USER_GUIDE.md](../skills/dingtalk-weekly-report/USER_GUIDE.md) | 同事（zip） | **安装 + 每周使用** 正文（随 zip） |
| [../README.md](../README.md) | 维护者 | 项目总览、打包、维护、调试 |
| [../skills/dingtalk-weekly-report/SKILL.md](../skills/dingtalk-weekly-report/SKILL.md) | AI Agent | 半自动周报 SOP |
| [../skills/dingtalk-weekly-report/references/FIELDS.md](../skills/dingtalk-weekly-report/references/FIELDS.md) | 维护者 | 表单字段事实源 |

## 分发物里有什么

`bash pack-skill.sh` 打出的 zip **只含** `dingtalk-weekly-report/` 技能目录（含 `USER_GUIDE.md`、`install*`、`bootstrap*`、`scripts/` 等），**不含** 个人 `config.json` / `weeks/` / 登录态。
