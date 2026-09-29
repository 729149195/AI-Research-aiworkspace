# AI Research Workspace

**用自己的 agent，以自然语言维护整篇论文。**

从研究问题、证据、写作和图表，到 LaTeX 模板、Overleaf、转投和投稿检查，都可以从一张菜单开始。agent 处理技术操作；研究选择、必要授权和独立审核由实际责任人完成。

## 开始使用

在 Codex、Claude Code 或其他有文件权限的 agent 中打开完整仓库，然后说：

> 请阅读这个 AI Workspace，显示功能菜单，带我使用。操作由你完成，需要我确认的地方再问我。

Codex 使用根目录 [AGENTS.md](AGENTS.md) 和 [.agents/skills/workspace-guide](.agents/skills/workspace-guide/SKILL.md)；Claude Code 通过 [CLAUDE.md](CLAUDE.md) 导入统一指引。[Codex 专门说明](aiworkspace/docs/CODEX.md)。菜单在安装前就能阅读，实际读写、执行、浏览和编辑器操作需要宿主提供权限。

**给 agent：** 读取 AGENTS.md 和 [workspace-guide](aiworkspace/research_workspace/assets/skills/workspace-guide/SKILL.md)，技术细节按需读 [执行手册](aiworkspace/docs/AGENT_PLAYBOOK.md)。明确任务直接办理；不要要求用户输入命令、填写 JSON 或替换路径占位符。

## 功能菜单

| 选择 | 我想做什么 |
|---|---|
| **1** | **新建论文**：寻找模板，整理对应届次与稿件类型的投稿规则 |
| **2** | **继续写／改论文**：论证、段落职责、数字、术语与自然学术语言 |
| **3** | **找文献／整理证据**：原始来源、引用、支持与反证 |
| **4** | **讨论想法／检查逻辑**：Idea Evaluation、贡献和可比较方案 |
| **5** | **方法、数据与科研绘图**：数据图、方法图版、编码解释、交互叙事与图形摘要 |
| **6** | **连接／同步 Overleaf**：自建服务器、本地稿件和同步冲突 |
| **7** | **转投期刊／会议**：保留旧稿，迁移到新的模板 |
| **8** | **审查／准备投稿**：完整性检查、独立审核与逐条审稿回复 |
| **9** | **查看进度／待办**：接续真实未完成的工作 |
| **0** | **项目与设置**：打开旧稿、切换论文、升级和自动沉淀 |

说“选 5”，也可以直接说“用同一个例子把这段方法画清楚”“帮我改摘要”“继续上次的修改”。说“菜单”返回入口；不会每轮重复显示菜单。

## 0.6.1：VIS / HCI 图优先解释方法

保留 **15 个 Skills、10 个菜单入口、Schema 1**（原 14 个科研／引导 Skills，加上 research-diagram）。本次纠正此前默认流程图偏模块框和箭头的问题：VIS/HCI 的方法总览优先展示实际对象、数据到编码的映射、中间表示、交互动作和反馈。先查看相关论文的实际图与图注，再为当前研究编排有具体内容的分图。

新增自由 SVG 图版路线 `paper-composite`，支持 agent 按论文内容组合矢量图元、表格、局部编码示例和文字注释，不必将它们压成节点图。保存可编辑 SVG、PDF/PNG、原始图源、分图说明与独立复现代码；源图或关联证据变化会被检测。当前安全子集不嵌入位图，截图密集的界面图需要单独审查的真实截图排版路线。

[VIS/HCI 配图说明与原创样例](aiworkspace/docs/VIS_HCI_FIGURES.md) · [方法解释图](aiworkspace/examples/vis-hci/method-detail.svg) · [交互叙事图](aiworkspace/examples/vis-hci/interaction-storyboard.svg)

两个样例使用同一批明确标注的人工数据，用来检查表示、选择与反馈的一致性；不宣称研究创新、真实界面或用户实验结果。之前的 Graphviz 模板继续用于适合节点—连接表达的简单流程和工程结构；它们的程序测试不代表已达到论文表达要求。

[旧节点图能力及限制](aiworkspace/docs/RESEARCH_DIAGRAMS.md) · [数据绘图与写作工作台](aiworkspace/docs/RESEARCH_STUDIO.md) · [本轮验证范围](aiworkspace/verification/paper-composition/README.md)

## 用户不需要维护内部状态

workspace-guide 处理菜单与信息收集；auto-route 在实际改稿前后捕获变更，将证据、规则、理由与未完成工作沉淀到对应位置。写作偏好和术语可以复用，原始资料、AI 建议与已核验证据保持区别。常规操作在当前授权范围内执行，安装、上传、付费、冲突和重要科学判断集中确认。

账号、密码、token、cookie 只在本机提供方／插件登录界面处理，不发给 AI、不进公开仓库。克隆文件不会自行启动模型、登录或后台监听。宿主未自动发现入口时，说“读取根目录 AGENTS.md，显示菜单”即可。

## 框架与论文分开放

仓库只存框架代码、公共指引、菜单和测试。每篇真实论文放在仓库外的独立目录，内部 `workspace/` 与 `manuscript/` 并列。前者保存研究逻辑、来源、证据、方法、规则与历史；后者保存正式稿件和图表。公共仓库不存真实论文和个人凭据。

[仓库结构与共享范围](aiworkspace/docs/REPOSITORY_LAYOUT.md) 解释 AGENTS.md、.agents、.claude 和 .github/workflows。个人设置和运行记录保持本地，公共入口随版本分发。

已有论文直接对 agent 说：

> 请增量升级 Workspace，启用新的学术配图流程，保留论文、原图、已填写内容和本地定制；需要我确认的地方集中问我。

原增量更新器继续保护用户文件与三方合并冲突。Schema 保持 1，无需重新初始化论文。图形依赖为可选项，未经授权不自动安装或上传数据。

## 使用说明与验证

[自然语言入门](aiworkspace/docs/START_WITH_AGENT.md) · [模板与年度规则](aiworkspace/docs/PUBLICATION.md) · [Overleaf](aiworkspace/docs/OVERLEAF.md) · [转投](aiworkspace/docs/RESUBMISSION.md) · [自动沉淀](aiworkspace/docs/AUTO_ROUTE.md)

[Agent 执行手册](aiworkspace/docs/AGENT_PLAYBOOK.md) · [增量更新](aiworkspace/docs/UPDATING.md) · [历史交付记录](aiworkspace/DELIVERY.md) · [0.6.1 验证](aiworkspace/verification/paper-composition/README.md)

程序测试、实际模型会话、图形编辑器、远端同步和投稿合规分别验收。能渲染、能编译或能显示菜单，不等于研究已经核验或云端连接已经成功。
