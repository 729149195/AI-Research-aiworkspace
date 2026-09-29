# AI Research Workspace

**和你自己的 agent 对话，维护一篇有证据、有逻辑、可追溯的论文。**

新建论文、查文献、改稿、科研绘图、连接自建 Overleaf、转投和投稿检查，都从同一张菜单开始。用户说目标，agent 处理有权限执行的技术步骤。

## 先这样开始

在你已登录的文件型 agent 中打开本仓库，说：

> 请阅读这个 AI Workspace，显示功能菜单，带我使用。操作由你完成，需要我确认的地方再问我。

| 使用的 agent | 入口 |
|---|---|
| **Codex** | [AGENTS.md](AGENTS.md) ＋ [.agents/skills/workspace-guide](.agents/skills/workspace-guide/SKILL.md)；[专门指引](aiworkspace/docs/CODEX.md) |
| **Claude Code** | [CLAUDE.md](CLAUDE.md) 导入同一份启动规则 |
| **其他文件型 agent** | 指定读取 [AGENTS.md](AGENTS.md)，按实际工具与权限办理 |

菜单无需先安装 Python。真正需要操作文件时，agent 再检查环境并集中请求必要授权。打开链接或拉取文件不会自动获得本机文件权限、启动监听、登录账户或安装依赖。

**给 agent：** 先读根入口与 workspace-guide。用户已有具体需求时直接办理；技术细节由你查 [Agent 手册](aiworkspace/docs/AGENT_PLAYBOOK.md) 和 [科研工作台](aiworkspace/docs/RESEARCH_STUDIO.md)，不要让用户填写 JSON、替换路径或复制命令。

## 功能菜单

| 选择 | 我想做什么 |
|---|---|
| **1** | **新建论文**：官方模板、当届投稿规则、独立写作目录 |
| **2** | **继续写／修改论文**：梳理论证、起草、润色、统一术语与数字 |
| **3** | **找文献／整理证据**：原始来源、引用、支持与反证 |
| **4** | **讨论想法／检查逻辑**：Idea Evaluation、方案比较、贡献与验证计划 |
| **5** | **方法、数据与科研图**：读数据、选合适图形、生成可复现的 SVG／PDF／PNG |
| **6** | **连接／同步 Overleaf**：自建服务器、账号本机登录、稿件同步 |
| **7** | **转投期刊／会议**：保留原稿，迁移目标模板并检查 |
| **8** | **审查／审稿回复／投稿**：证据与规范检查、逐条意见、实际修改位置 |
| **9** | **查看进度／继续任务**：读取真实待办，优先处理关键问题 |
| **0** | **项目与设置**：打开旧稿、切换论文、增量更新、环境与自动沉淀 |

可以回复编号，也可以直接说“根据这组配对数据画一张论文图”“检查摘要与正文的数字”“逐条处理审稿意见”。说“菜单”返回入口；目标明确时不必先选择菜单。

## 0.5.0：更好写，也更好用

**可直接执行的科研绘图。** 七种本地配方覆盖散点、折线、分布、配对、区间、热图和小型流程图。agent 读取真实数据，确认必要的单位和观测结构，再生成图、图注与替代文字。数据、配方、完整渲染代码、环境及输出哈希一起保留；原始 CSV 和代码留在研究目录，不自动进入 Overleaf 稿件上传范围。图必须经过实际视觉与科学复核，不能只看生成成功。

**先论证，后润色。** 写作流程先检查研究问题、章节职责、Claim 和证据，再处理数字、段落与自然学术表达。新的检查报告提供带位置的数字清单、段落检查表和证据缺口。程序标出的文字是复核线索，不会自行改结论或把不同队列的数字改成一样。

**不用反复解释偏好。** agent 可以维护你已确认的写作简报和术语表，复用读者、文风、修改范围与不能擅改的内容。简报提供写作背景，不作为研究证据；独立审查仍保留上下文边界。

**审稿回复对应真实修改。** 每条原意见关联修改方案、当前文件中的原文位置和回复草稿。声称“已经补了实验”但找不到实际修改时，会保持待处理；定位成功也不代表科学问题已解决。

[工作台说明、完整配方和使用边界](aiworkspace/docs/RESEARCH_STUDIO.md)

## 自动沉淀与少打断

保留 **14 个内置 Skills**，菜单仍为原来的 10 个入口。workspace-guide 负责引导，auto-route 负责改稿与研究讨论的变更沉淀；本轮强化已有绘图、写作和 Reviewer Skill，没有给用户增加另一套操作系统。

常规修改在本轮授权范围内完成，重要研究判断、双向冲突、安装、外部传输、费用和远端写入集中确认。密码、token、cookie 在本机登录或凭据工具处理，不放进聊天。原文核验、独立审核和作者责任不能由 AI 冒名完成。

## 文件与更新

本公共仓库只放框架：根目录 AGENTS.md／CLAUDE.md 是启动入口，aiworkspace/ 包含实现和资料，update_aiworkspace.py 提供原有增量更新。共享宿主指令可版本管理，个人设置、会话、凭据与 .rw 运行数据保持本地。

真实论文放在仓库之外，各自有并列的 workspace/ 和 manuscript/。已填写工作表、研究、数据、代码、稿件及本地规则不受框架默认资产更新覆盖。

旧用户直接说：

> 帮我升级 Workspace，启用新的科研绘图和写作检查，保留我的论文、规则与定制；需要确认的地方集中问我。

agent 先预览，再按授权增量更新。遇到冲突保留双方，不重新初始化已有论文。绘图库是可选依赖，只在确实需要且获准时安装。

## 使用资料与验证

[自然语言入门](aiworkspace/docs/START_WITH_AGENT.md) · [Codex](aiworkspace/docs/CODEX.md) · [科研工作台](aiworkspace/docs/RESEARCH_STUDIO.md) · [模板与规则](aiworkspace/docs/PUBLICATION.md) · [Overleaf](aiworkspace/docs/OVERLEAF.md) · [转投](aiworkspace/docs/RESUBMISSION.md) · [自动沉淀](aiworkspace/docs/AUTO_ROUTE.md)

[Agent 操作手册](aiworkspace/docs/AGENT_PLAYBOOK.md) · [增量更新](aiworkspace/docs/UPDATING.md) · [仓库共享范围](aiworkspace/docs/REPOSITORY_LAYOUT.md) · [本次验收](aiworkspace/DELIVERY.md)

版本 **0.5.0**，研究 Schema 保持 **1**。本轮验证范围和历史报告分别记录；实际绘图与本地检查不能代替完整宿主／模型效果、期刊合规、远端 Overleaf 联调或 GitHub CI。当前菜单是对话中的文字选择，执行能力由所用 agent 提供。
