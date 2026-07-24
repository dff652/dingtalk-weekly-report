# skills.sh 分发与发布

## 结论

本项目已经采用 [skills CLI](https://github.com/vercel-labs/skills) / [skills.sh](https://skills.sh/)
兼容结构：`skills/dingtalk-weekly-report/SKILL.md`。用户执行
`npx skills add owner/repo --skill dingtalk-weekly-report` 时，CLI 从 Git 仓库发现并安装 skill。

skills.sh **没有单独的上传或 publish 命令**。公开发布的实际流程是：

1. 将含合法 `SKILL.md` 的仓库推送到公开 GitHub 仓库；
2. 用 `npx skills add owner/repo --list` 验证 CLI 可以发现 skill；
3. 用真实安装命令验证至少一个 Agent；
4. CLI 的匿名安装遥测驱动 skills.sh 的索引和排行榜，等待公开页面出现。

官方资料：

- [skills CLI README](https://github.com/vercel-labs/skills)
- [skills.sh 文档](https://skills.sh/docs)
- [skills.sh CLI 文档](https://skills.sh/docs/cli)

## 本项目当前状态

以下远程发现检查已通过：

```bash
git ls-remote https://github.com/dff652/dingtalk-weekly-report.git HEAD
npx skills add dff652/dingtalk-weekly-report --list
# Found 1 skill: dingtalk-weekly-report
```

安装分两层：

1. `npx skills add ...` 只安装 `$SKILL` 文件，属于 skills.sh 标准流程；
2. `bootstrap.sh` / `bootstrap.ps1` 创建 `$WORK`、Python venv 和 Chromium，是本项目特有的运行时初始化。

因此“能被 skills CLI 安装”已经成立，但“适合公开发布”目前不成立。

## 发布前必须选择分发策略

### A. 公司内部使用（当前描述）

推荐把 GitHub 仓库设为私有，通过有权限的 Git URL、内部 zip 或公司制品库分发。私有仓库不应追求
skills.sh 公共索引。

发布前还应把根目录维护者的 `config.json`、`weeks/` 与代码仓分离，并检查 Git 历史是否包含个人、
项目或表单信息。

### B. 脱敏后公开发布

必须先完成：

- 删除或参数化公司表单 URL、组件 ID、公司枚举和内部操作说明；
- 从当前版本及 Git 历史清除真实姓名、周报内容、内部项目名和路径；
- 将用户工作数据永久迁出仓库，只保留 `tests/fixtures/` 脱敏夹具；
- 确认许可证、安全说明和支持范围；
- 安装时检查 skills.sh 的 Gen、Socket、Snyk 审计；不得带 Critical/High 未解释风险；
- 重新运行 `tests/run_smoke.sh` 与 `tests/run_full_acceptance.sh`。

然后：

```bash
git push origin main
npx skills add dff652/dingtalk-weekly-report --list
npx skills add dff652/dingtalk-weekly-report \
  --skill dingtalk-weekly-report \
  --agent claude-code --agent codex \
  --global --yes --copy
```

预期页面路径为：
`https://skills.sh/dff652/dingtalk-weekly-report/dingtalk-weekly-report`。
索引由平台生成，不保证推送后立即出现。

可选 README 徽章：

```markdown
[![skills.sh](https://skills.sh/b/dff652/dingtalk-weekly-report)](https://skills.sh/dff652/dingtalk-weekly-report)
```

## 发布验收

先在待发布提交上运行本地门禁：

```bash
bash tests/run_smoke.sh
bash tests/run_full_acceptance.sh
```

两项通过并完成敏感信息检查后，push 候选提交；再运行远端门禁：

```bash
git push origin main
bash tests/run_release_acceptance.sh
```

正式发行验收不得设置 `DTWR_ALLOW_DIRTY=1` 或把 `DTWR_RELEASE_REMOTE` 指向本地仓库；
这两个变量只供候选脚本尚未 push 时做开发态自测。发行脚本固定使用
`skills@1.5.20`，并校验 `.agents` / `.claude` 中实际安装的副本。

只有三项都通过，且安装输出中的安全审计无未处理的 Critical/High，才可宣布该提交通过
公开发行验收。审计可能缓存旧提交；推送修复后需重新安装并等待平台重扫。

真实个人配置、登录、氚云草稿和钉钉提交不属于发行自动验收，按
[MANUAL_ACCEPTANCE.md](MANUAL_ACCEPTANCE.md) 单独执行并留存人工结论。
