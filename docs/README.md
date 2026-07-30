# 文档索引

| 文档 | 读者 | 说明 |
|------|------|------|
| [../README.md](../README.md) | 所有人 | **短入口**：价值、安全边界、工作流、快速开始和文档入口 |
| [../skills/dingtalk-weekly-report/USER_GUIDE.md](../skills/dingtalk-weekly-report/USER_GUIDE.md) | 同事 | 安装细节、CLI 周流程、FAQ（随 skill） |
| [../skills/dingtalk-weekly-report/SKILL.md](../skills/dingtalk-weekly-report/SKILL.md) | Agent | 周报 SOP |
| [../skills/dingtalk-weekly-report/references/FIELDS.md](../skills/dingtalk-weekly-report/references/FIELDS.md) | 维护者 | 表单字段 |
| [SOP.md](SOP.md) | 维护者/贡献者/用户 | **流程骨架与决策表**：改动类型→必跑验证、发版检查单、回滚路径、**用户旅程 SOP（安装→登录→使用→确认）** |
| [GITHUB_PROJECT_PAGE_SOP.md](GITHUB_PROJECT_PAGE_SOP.md) | 维护者 | README 信息分层、SVG/Social preview、GitHub 元数据与 Skills Hub 分发 SOP |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | 贡献者 | 钩子、提交身份、三条硬规则、不接受的改动 |
| [MAINTAINER.md](MAINTAINER.md) | 维护者 | 打包、测试、调试、路线图 |
| [REVIEW.md](REVIEW.md) | 维护者 | 设计与实现评审：不变量清单、待修缺陷、发布阻断复核 |
| [PUBLISHING.md](PUBLISHING.md) | 维护者 | skills.sh 分发、许可证选择、公开发布与脱敏门槛 |
| [TESTING.md](TESTING.md) | 维护者/验收人 | 自动测试结果、安装踩坑排查与真实人工验收边界 |
| [MANUAL_ACCEPTANCE.md](MANUAL_ACCEPTANCE.md) | 验收人 | 真实配置、登录、预览、草稿与人工提交 SOP |
| [USER_GUIDE.md](USER_GUIDE.md) | — | 跳转到技能包内正文 |

## 分发

- **公开代码**：Apache-2.0；GitHub + `npx skills add`（见 `PUBLISHING.md`）
- **私有运行数据**：每用户 `$WORK` 与登录态，禁止进入仓库和发布产物
- **zip**：`bash pack-skill.sh` → 仅技能目录（含 USER_GUIDE），无个人数据
