# 文档索引

| 文档 | 读者 | 说明 |
|------|------|------|
| [../README.md](../README.md) | 所有人 | **短入口**：Install / 给 AI 的粘贴块 / Verify / Use |
| [../skills/dingtalk-weekly-report/USER_GUIDE.md](../skills/dingtalk-weekly-report/USER_GUIDE.md) | 同事 | 安装细节、CLI 周流程、FAQ（随 skill） |
| [../skills/dingtalk-weekly-report/SKILL.md](../skills/dingtalk-weekly-report/SKILL.md) | Agent | 周报 SOP |
| [../skills/dingtalk-weekly-report/references/FIELDS.md](../skills/dingtalk-weekly-report/references/FIELDS.md) | 维护者 | 表单字段 |
| [MAINTAINER.md](MAINTAINER.md) | 维护者 | 打包、测试、调试、路线图 |
| [USER_GUIDE.md](USER_GUIDE.md) | — | 跳转到技能包内正文 |

## 分发

- **推荐**：GitHub + `npx skills add`（见根 README）
- **zip**：`bash pack-skill.sh` → 仅技能目录（含 USER_GUIDE），无个人数据
