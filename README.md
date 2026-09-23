# AI Research Workspace

维护整篇论文的研究状态、论证、证据、方法和稿件，并在修改后检查全局影响。

**Workspace 管研究；Skills 管过程；Manuscript 管表达；Sync 管双向变更；Reviewer 管质量门。**

**0.2.0：新增默认入口 `auto-route`。** 在论文项目中启动有文件权限的 AI 宿主后，用户直接改稿、讨论研究或提供反馈。AI 自动捕获实际改动、保留必要上下文并分派对应 Skills；重要研究判断、冲突和授权事项集中确认。框架提供 10 个可修改的 Skills，默认不联网、不调用付费模型、不上传论文。

## 仓库与论文项目

本项目独立维护于 [729149195/AI-Research-aiworkspace](https://github.com/729149195/AI-Research-aiworkspace)。

```text
AI-Research-aiworkspace/
├── aiworkspace/              # 框架、Skills、模板、测试及详细文档
├── update_aiworkspace.py     # 已使用项目的增量更新脚本
├── README.md                 # 使用说明
├── .github/                  # 隐藏的 CI 配置
└── .gitignore
```

框架仓库只放通用程序。真实论文创建在仓库外，一个框架可以维护多篇论文：

```text
my-paper/
├── START_HERE.md / AGENTS.md / CLAUDE.md
├── workspace/
│   ├── state.json            # 规范研究节点、依赖、提案、问题和持久待办
│   ├── research/             # 已填写 Idea Evaluation
│   ├── sources/ / evidence/  # 原始来源与证据材料
│   ├── methods/ / data/ / results/
│   ├── rules/ / figures/ / history/ / sync/
│   ├── skills/ / templates/  # 可增量更新的默认资产
│   └── memory.md / reports/
├── manuscript/              # Markdown 工作稿、图表和 Supplementary
└── .rw/                     # 更新基线、事务和本地备份
```

`workspace/` 和 `manuscript/` 始终并列。Memory、讨论和决策只提供上下文，不能充当事实证据。不要把未发表论文或私人数据推送到这个公共框架仓库。

## 1. 安装并体验演示

需要 Python 3.11+、Git；核心无第三方运行时依赖，安装需要 pip/setuptools/wheel。AI 宿主和模型账号由使用者自行授权。

macOS / Linux：

```bash
git clone https://github.com/729149195/AI-Research-aiworkspace.git
cd AI-Research-aiworkspace
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-deps --no-build-isolation -e ./aiworkspace
rw doctor
rw demo ../research-demo
```

Windows PowerShell：

```powershell
git clone https://github.com/729149195/AI-Research-aiworkspace.git
cd AI-Research-aiworkspace
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .\aiworkspace
.\.venv\Scripts\python.exe -m research_workspace doctor
.\.venv\Scripts\python.exe -m research_workspace demo ..\research-demo
```

Windows 后续的 `rw` 可替换为 `.\.venv\Scripts\python.exe -m research_workspace`，无需调整系统执行策略。`doctor` 应显示 0.2.0 和 10 个 Skill 契约通过。

演示真实执行合成数据计算、生成 SVG、建立证据链、双向同步、更新/回滚及质量门检查。打开 `../research-demo/workspace/reports/dashboard.html` 查看离线只读看板；同目录 `walkthrough.json` 记录步骤。数据与人工审核声明均明确为模拟，不能用于真实投稿。demo/init 拒绝覆盖非空目录，重跑请使用新目录。

## 2. 创建论文并接入 AI

以下在框架仓库根目录、专用虚拟环境执行：

```bash
rw init ../my-paper --name "我的论文项目" --author "你的姓名"
rw --project ../my-paper skills install --target .agents/skills
# Claude Code 用户改用 --target .claude/skills
```

然后在 **my-paper 根目录**打开已授权的 AI 宿主，让它读 `START_HERE.md` 与 `AGENTS.md`。先填写 `workspace/research/idea-evaluation.md` 及 `workspace/rules/project-policy.md`；不要把研究内容填进后续会更新的空模板目录。

Idea Evaluation 已由用户提供的十页 PPT 转为 [逐页原文](aiworkspace/research_workspace/assets/templates/idea-evaluation.original.md) 和 [可填写工作表](aiworkspace/research_workspace/assets/templates/idea-evaluation.md)，保留可视化编码、任务、设计理由、替代方案、已有与预期结果等问题。PPT 二进制不随仓库发布，原文权利保留。

## 3. 日常使用：直接说你要改什么

> 请以 auto-route 作为默认入口。以后我直接改稿、讨论想法和提供反馈时，你维护研究状态、保存必要上下文并调用对应 Skills。常规整理尽量少打断；研究结论、证据强度、双向冲突或超出我授权的操作统一向我确认。

之后直接提出“润色讨论”“导师把导致改成相关”“补入这篇文献”“统一术语”等请求。入口指令要求 AI 在改稿前后自动运行本地捕获，读取差异和依赖关系，并用对应 Skill 完成研究维护。相同状态不重复记录；连续编辑按 Skill 合并未完成待办，跨会话保留。

捕获记录位于 `workspace/history/auto-route/`，观察基线位于 `workspace/sync/auto-route.json`，正式研究状态仍在 `state.json`。简短讨论笔记保留说话人和不确定性，保持未确认上下文，不能自动升级成证据或决定。

**捕获、提案、应用、核验和审核分别记录。** AI 可以在本轮明确授权的编辑范围内操作，使用自己的真实操作身份。新的科学含义、证据确认、同步冲突和独立审核保留相应确认；不会因一次“帮我改稿”而签署人类核验。

完整操作见 [Auto-route 指南](aiworkspace/docs/AUTO_ROUTE.md)。所有这些命令由文件型 AI 宿主执行；普通网页聊天没有本地文件操作或监听能力。

### 可选：Claude Code 自动捕获 Hooks

在论文项目根目录预览配置，授权后安装：

```bash
rw route install-hooks
rw route install-hooks --approve
```

安装仅合并本程序的本地 Hook，保留其他设置。重启宿主并确认 Hook 生效。它在宿主会话事件上执行本地捕获，无新改动时静默；Stop 不循环启动新回复。没有宿主运行时，手工改动在下一次捕获发现。卸载使用 `rw route remove-hooks --approve`。完整宿主/Windows 效果尚未验证，本地处理器及独立 Python 调用链已测试。

## 4. 需要检查时

日常可以让 AI 代为操作；作者也可随时查看：

```bash
rw --project ../my-paper route status
rw --project ../my-paper sync status
rw --project ../my-paper review
rw --project ../my-paper dashboard
```

新项目显示 blocked 属正常情况，缺失问题、证据、正文和审核不能用虚构内容填补。`rw --help` 与各子命令 `--help` 给出准确参数。CLI 退出码 0 表示命令完成，1 表示质量/预检阻塞，2 表示输入无效或操作被拒绝。

详细的来源核验、提案批准、方法执行、图表、Reviewer、导出、可选 API 和人工任务包分别见 [从零开始](aiworkspace/docs/GETTING_STARTED.md)、[Skills](aiworkspace/docs/SKILLS.md)、[数据协议](aiworkspace/docs/SCHEMA.md)。自动来源发现仅提供候选元数据；原文和真实核验仍是 Evidence 的前提。分析代码执行需要单独许可，当前本地执行器不提供安全沙箱。

## 5. 已使用项目的增量更新

关闭正在写论文的 AI/编辑器任务，备份完整论文；在**框架仓库根目录**使用专用虚拟环境：

```bash
python update_aiworkspace.py --project ../my-paper --check
python update_aiworkspace.py --project ../my-paper --apply --actor "你的姓名"
```

应用时可加 `--expected-commit 完整SHA` 锁定刚预览的版本。脚本只快进更新框架；受管默认资产按旧默认/本地/新默认三方比较。局部定制保留，不重叠修改合并，重叠冲突暂停并明确选择。数据、稿件、证据、方法、用户规则和已填写工作表不作为默认资产覆盖目标。

```bash
rw --project ../my-paper upgrade history
rw --project ../my-paper upgrade rollback UPDATE-ID
```

0.1.0 项目会增量补入 auto-route、入口指令和已注册宿主的 Skill 副本；研究 Schema 仍为 1。第一次捕获安全建立观察基线，不虚构旧编辑历史。Hook 不会随升级擅自启用。保留 `.rw/framework.json`；资产备份不替代真实研究备份。详见 [更新/冲突/恢复](aiworkspace/docs/UPDATING.md) 和 [从旧框架接续](aiworkspace/docs/NEW_REPOSITORY.md)。

## 6. 开发、测试与范围

新增 Skill、适配器和研究字段的约定见 [贡献说明](aiworkspace/CONTRIBUTING.md) 与 [整体架构](aiworkspace/docs/ARCHITECTURE.md)。通用默认改在框架源码，个人研究/偏好改在论文项目；用私有 Git 管理真实论文。

```bash
python aiworkspace/scripts/run_tests.py
python aiworkspace/scripts/check_docs.py
python aiworkspace/scripts/smoke_root_update.py
python aiworkspace/scripts/smoke_auto_route.py
```

本地测试、干净安装和合成演练结果见 [验收记录](aiworkspace/DELIVERY.md)。确定性软件测试与真实模型/完整宿主效果分别记录；不能用测试通过宣称科学有效性或投稿保证。原生稿件同步支持带稳定标记的 Markdown；Word/LaTeX/Overleaf 无损往返、身份认证、实时多人数据库和常驻自主研究不在当前实现范围。

[Auto-route](aiworkspace/docs/AUTO_ROUTE.md) · [English quickstart](aiworkspace/docs/QUICKSTART_EN.md) · [安全说明](aiworkspace/SECURITY.md) · [版本记录](aiworkspace/CHANGELOG.md)
