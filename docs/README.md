# 文档索引

| 文档 | 读者 | 说明 |
|------|------|------|
| [../README.md](../README.md) | 所有人 | **短入口**：Install / 给 AI 的粘贴块 / Verify / Use |
| [../skills/dingtalk-weekly-report/USER_GUIDE.md](../skills/dingtalk-weekly-report/USER_GUIDE.md) | 同事 | 安装细节、CLI 周流程、FAQ（随 skill） |
| [../skills/dingtalk-weekly-report/SKILL.md](../skills/dingtalk-weekly-report/SKILL.md) | Agent | 周报 SOP |
| [../skills/dingtalk-weekly-report/references/FIELDS.md](../skills/dingtalk-weekly-report/references/FIELDS.md) | 维护者 | 表单字段 |
| [MAINTAINER.md](MAINTAINER.md) | 维护者 | 打包、测试、调试、路线图 |
| [PUBLISHING.md](PUBLISHING.md) | 维护者 | skills.sh 分发、公开发布与脱敏门槛 |
| [TESTING.md](TESTING.md) | 维护者/验收人 | 自动测试结果与真实人工验收边界 |
| [USER_GUIDE.md](USER_GUIDE.md) | — | 跳转到技能包内正文 |

## 分发

- **公开生态**：脱敏后使用 GitHub + `npx skills add`（见 `PUBLISHING.md`）
- **公司内部**：私有 Git URL / 内部 zip，不进入 skills.sh 公共索引
- **zip**：`bash pack-skill.sh` → 仅技能目录（含 USER_GUIDE），无个人数据
