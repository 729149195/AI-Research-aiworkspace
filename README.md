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
| **5** | **方法、数据与科研绘图**：数据图、流程图、架构、机制假设与图形摘要 |
| **6** | **连接／同步 Overleaf**：自建服务器、本地稿件和同步冲突 |
| **7** | **转投期刊／会议**：保留旧稿，迁移到新的模板 |
| **8** | **审查／准备投稿**：完整性检查、独立审核与逐条审稿回复 |
| **9** | **查看进度／待办**：接续真实未完成的工作 |
| **0** | **项目与设置**：打开旧稿、切换论文、升级和自动沉淀 |

说“选 5”，也可以直接说“把这段方法画成分支流程图”“帮我改摘要”“继续上次的修改”。说“菜单”返回入口；不会每轮重复显示菜单。

## 新增：可编辑的科研示意图

0.6.0 在原 **14 个** Skills 的基础上新增 `research-diagram`，共 **15 个**；菜单仍为原 10 个入口。

七类模板覆盖方法 pipeline、分组系统架构、实验设计、机制假设、图形摘要、概念框架及审稿解释。支持分支、反馈、一层分组、横／竖排，提供 editorial、paper、mono 三种原创建议风格和小型矢量图标。当前图形摘要为结构化矢量叙事；精细生物插画、照片级效果和任意嵌套泳道需要另外的专业工具与检查。

用户给出图的目的和实际内容，agent 选择结构与风格、生成预览并继续修改。每版保存 SVG/PDF/PNG、可编辑 drawio/DOT、冻结规格和独立重绘源码。假设用虚线，关联和因果区分；图源或证据变化会使旧记录过期。未完成图形／科学复核的 draft 不直接通过质量门。

[科研示意图说明](aiworkspace/docs/RESEARCH_DIAGRAMS.md) · [已有数据绘图与写作工作台](aiworkspace/docs/RESEARCH_STUDIO.md)

## 用户不需要维护内部状态

workspace-guide 处理菜单与信息收集；auto-route 在实际改稿前后捕获变更，将证据、规则、理由与未完成工作沉淀到对应位置。写作偏好和术语可以复用，原始资料、AI 建议与已核验证据保持区别。常规操作在当前授权范围内执行，安装、上传、付费、冲突和重要科学判断集中确认。

账号、密码、token、cookie 只在本机提供方／插件登录界面处理，不发给 AI、不进公开仓库。克隆文件不会自行启动模型、登录或后台监听。宿主未自动发现入口时，说“读取根目录 AGENTS.md，显示菜单”即可。

## 框架与论文分开放

仓库只存框架代码、公共指引、菜单和测试。每篇真实论文放在仓库外的独立目录，内部 `workspace/` 与 `manuscript/` 并列。前者保存研究逻辑、来源、证据、方法、规则与历史；后者保存正式稿件和图表。公共仓库不存真实论文和个人凭据。

[仓库结构与共享范围](aiworkspace/docs/REPOSITORY_LAYOUT.md) 解释 AGENTS.md、.agents、.claude 和 .github/workflows。个人设置和运行记录保持本地，公共入口随版本分发。

已有论文直接对 agent 说：

> 请增量升级 Workspace，启用科研示意图，保留论文、原图、已填写内容和本地定制；需要我确认的地方集中问我。

原增量更新器继续保护用户文件与三方合并冲突。Schema 保持 1，无需重新初始化论文。图形依赖为可选项，未经授权不自动安装或上传数据。

## 使用说明与验证

[自然语言入门](aiworkspace/docs/START_WITH_AGENT.md) · [模板与年度规则](aiworkspace/docs/PUBLICATION.md) · [Overleaf](aiworkspace/docs/OVERLEAF.md) · [转投](aiworkspace/docs/RESUBMISSION.md) · [自动沉淀](aiworkspace/docs/AUTO_ROUTE.md)

[Agent 执行手册](aiworkspace/docs/AGENT_PLAYBOOK.md) · [增量更新](aiworkspace/docs/UPDATING.md) · [本次验收与限制](aiworkspace/DELIVERY.md)

程序测试、实际模型会话、图形编辑器、远端同步和投稿合规分别验收。能渲染、能编译或能显示菜单，不等于研究已经核验或云端连接已经成功。
