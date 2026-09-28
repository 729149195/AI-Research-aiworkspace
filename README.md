# AI Research Workspace

**和你自己的 agent 对话，就能维护一篇论文。**

新建论文、改稿、找文献、整理证据、制作图表、连接自建 Overleaf、转投和投稿检查，都可以从一张菜单开始。技术命令、目录和记录由具备对应权限的 agent 处理。

## 先这样开始

**Codex 和 Claude Code 都有对应入口：**

| 使用的 agent | 仓库中的入口 | 如何开始 |
|---|---|---|
| **Codex** | [AGENTS.md](AGENTS.md) ＋ [.agents/skills/workspace-guide](.agents/skills/workspace-guide/SKILL.md) | 打开本仓库并说“显示菜单”；[Codex 专门指引](aiworkspace/docs/CODEX.md) |
| **Claude Code** | [CLAUDE.md](CLAUDE.md) 导入同一份 AGENTS.md | 打开本仓库并说“显示菜单” |
| **其他文件型 agent** | 手动指定 [AGENTS.md](AGENTS.md) | 让 agent 读取入口，按其实际权限办理 |

首次交互没有具体任务时显示菜单，有明确任务则直接办理。Codex 的项目指令和 Skills 已放在标准位置；本仓库保留用户自己的模型、账号和权限配置。

宿主未自动读取，或你只提供了仓库链接时，说：

> 请阅读这个 AI Workspace，显示功能菜单，带我使用。操作由你完成，需要我确认的地方再问我。

**给 agent：** 先读根目录 [AGENTS.md](AGENTS.md)，再按需读取 [workspace-guide](aiworkspace/research_workspace/assets/skills/workspace-guide/SKILL.md)，显示下面的菜单；有具体需求时直接办理。技术执行细节见 [Agent 操作手册](aiworkspace/docs/AGENT_PLAYBOOK.md)。不要要求用户手动运行命令、填写 JSON 或替换路径占位符。

菜单在安装前就能显示。真正需要创建／修改本地文件时，agent 会检查环境，并集中说明需要你确认的安装或权限。阅读了仓库链接不代表它已经取得本地文件权限。

## 功能菜单

| 选择 | 我想做什么 |
|---|---|
| **1** | **新建论文**：找模板、整理当届投稿规则，准备写作目录 |
| **2** | **继续写／修改论文**：起草、润色、改摘要、处理导师意见 |
| **3** | **找文献／整理证据**：查原始来源、整理引用与反证 |
| **4** | **讨论想法／检查逻辑**：评估 Idea、比较方案、梳理贡献 |
| **5** | **方法、数据与图表**：研究设计、数据分析和可追溯图表 |
| **6** | **连接／同步 Overleaf**：配置自建服务器与本地稿件同步 |
| **7** | **转投期刊／会议**：保留旧稿，迁移到目标模板 |
| **8** | **审查论文／准备投稿**：检查证据、方法、规范与一致性 |
| **9** | **查看进度／待办**：查看上次做到哪里、还要修什么 |
| **0** | **项目与设置**：打开旧稿、切换论文、更新、环境与自动沉淀 |

回复“选 1”，或者直接说“帮我改摘要”“连接实验室 Overleaf”“保留论文并升级 Workspace”。不需要记编号。说“菜单”可以随时返回；明确任务直接进入工作，不必先经过菜单。

[第一次使用与对话示例](aiworkspace/docs/START_WITH_AGENT.md)

## 你说目标，agent 处理过程

“我想投某会议，帮我开始。” → 确认主题与目标 → 查当届官方模板和规则 → 在独立论文目录初始化。

“导师改了这一段，顺便检查摘要。” → 读取当前稿件 → 修改 → 保存差异和理由 → 检查关联论点与章节。

“把这篇论文转投到另一期刊。” → 找新模板与规范 → 比较差异 → 创建新版本 → 保留旧稿 → 编译和复核。

“更新 Workspace，别动我的论文。” → 预览上游变化 → 确认影响 → 三方增量更新 → 保留研究和本地定制。

以上是操作流程。模板适用性、来源真实性、连接状态和实际结果以真实工具回执及审核为准。

## 自动沉淀与少打断

`workspace-guide` 负责菜单、选择和必要的信息收集；`auto-route` 在实际改稿、研究讨论和反馈处理中保存变更并分派专业 Skills。共有 **14 个内置 Skills**。用户无需手工选择 Skill 或操作状态文件。

常规编辑在本轮授权范围内完成，重要研究判断、双向冲突、安装、外部传输、费用和远端写入集中确认。登录在本机网站／插件界面完成，密码、token 和 cookie 不放进聊天。菜单浏览不产生研究变更，也不授予无限期权限。

## 文件怎么放

本仓库只放框架。根目录 `AGENTS.md` / `CLAUDE.md` 给 agent 提供启动指引；`aiworkspace/` 放实现，`update_aiworkspace.py` 提供更新，本说明面向用户。隐藏的 `.agents/`、`.claude/` 只共享公开的宿主指引；`.github/workflows/` 保留自动测试配置，本地菜单使用不依赖云端 CI。

`.claude/settings.local.json`、个人记忆／会话、凭据与 `.rw` 运行状态保持本地，不提交、不打包。克隆文件不会自动安装、登录或启动监听。完整说明见 [仓库结构与共享范围](aiworkspace/docs/REPOSITORY_LAYOUT.md)。

每篇真实论文使用仓库之外的独立目录，里面 `workspace/` 管逻辑、文献、证据、规则与历史，`manuscript/` 管正式正文、LaTeX 和图表。研究目录与稿件目录并列。不会把真实论文上传到本公共仓库。

已有论文可以直接对 agent 说“打开这篇论文”或“接入旧稿”。框架升级保留已写内容、用户规则与本地定制，遇到冲突先停下，不重新初始化论文。

## 需要什么样的 agent

能读 Markdown 就能展示菜单；读写本地文件、执行命令、浏览网页、操作编辑器分别需要宿主提供实际工具与权限。普通网页聊天可以讨论和修改你提供的文字，持久保存和同步需要有文件权限的环境。首次可能需要确认安装器、选择目录或在本机登录，这些都由 agent 引导。

宿主是否自动发现入口取决于其实现。没有自动显示时，发送最上面的启动句即可。菜单是聊天中的文字选择，没有独立的图形客户端。它不会绕过研究核验、独立审查和账户授权。

## 使用资料

[自然语言入门](aiworkspace/docs/START_WITH_AGENT.md) · [模板与年度规则](aiworkspace/docs/PUBLICATION.md) · [Overleaf](aiworkspace/docs/OVERLEAF.md) · [转投](aiworkspace/docs/RESUBMISSION.md) · [自动沉淀](aiworkspace/docs/AUTO_ROUTE.md)

[开发者／Agent 执行手册](aiworkspace/docs/AGENT_PLAYBOOK.md) · [增量更新机制](aiworkspace/docs/UPDATING.md) · [实际验收与边界](aiworkspace/DELIVERY.md)

## 版本与验证

当前版本 **0.4.0**，研究数据 Schema 保持 1。新增菜单和自然语言引导，沿用既有科研、LaTeX、Overleaf 与增量更新机制。菜单选择和只读状态可用程序验证；任意宿主／模型是否完全遵循交互规范需要分别测试，不能用本地菜单测试替代。云端 CI 与本地测试分别记录。
