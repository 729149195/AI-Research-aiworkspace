# Agent 操作手册（内部执行层，0.4.0）

面向有文件／命令权限的 agent。普通用户入口是 [自然语言指南](START_WITH_AGENT.md)，默认不向用户展示本文件的命令、JSON 或占位字段。所有 `STUDY`、`PYTHON`、ID 和路径由实际检查结果替换，用参数数组或宿主安全转义；不要把用户自由文本拼进 shell。

## 入口和状态

首先读取 workspace-guide。无具体任务才显示菜单；明确任务直接交 auto-route。菜单来自 `workspace/templates/workspace-menu.md`（论文）或 `aiworkspace/MENU.md`（框架）。Python 尚未安装时直接读 Markdown，不为展示菜单创建环境。

可选只读助手：从已安装包运行 `PYTHON -m research_workspace.menu --project STUDY`。尚未安装时可直接运行框架中的 `aiworkspace/research_workspace/menu.py`。`--json` 返回本地状态与功能清单；`--select 2 --menu-reply` 解析刚显示过的菜单回复。此解析器只识别精确控制词与别名；任意自然语言由宿主理解。选择结果不会执行操作。默认仅向上查找当前目录所属论文，显式指定的路径不会被换成另一个项目。损坏的状态不能显示为“没有问题”。

读取当前论文 `workspace/state.json` 和用户规则，必要时读取实际稿件。只依据真实返回值显示名称、待办与状态。菜单不自动运行 capture、review、联网、安装或升级；无需把一次 help 记进研究历史。

## 环境准备：由 agent 执行

确认宿主的读写、执行、浏览能力。先确认可用 Python 3.11+，不要从应用名称推断权限。检查框架 `aiworkspace/pyproject.toml`；框架与真实论文分开。已有正常虚拟环境优先使用其绝对解释器路径，避免依赖 shell 激活。

首次准备可使用 `PYTHON aiworkspace/scripts/prepare_agent.py` 预览，用户明确同意本地虚拟环境与可选联网下载构建工具后，执行同一脚本加 `--approve`；缺少构建工具需要额外 `--allow-download`。脚本只使用框架根目录 `.venv`，不会全局安装、修改系统执行策略、初始化论文或登录远端。失败后保留环境供检查，不删除用户文件。安装确认不包含上传论文授权。

需要现有宿主的运行工具而当前没有时，清楚说明缺少的具体能力；继续做可完成的阅读／草拟。让用户通过宿主界面打开文件夹或确认官方安装器，避免把一页终端命令交给用户作为默认路径。

## 项目选择与创建

从论文根目录进入时复用它；从框架进入时先确定新建或已有论文，多个显式可用项目必须选择。不要扫描 home。用户选择后固定 `STUDY` 绝对路径，所有命令都带 `--project STUDY`；切换项目需要用户指定。作者姓名和真实目标从当前资料复用，确实缺少才问。

新建：调用 `PYTHON -m research_workspace init STUDY --name NAME --author AUTHOR`。目标应在框架仓库外；拒绝非空目录。安装宿主 Skills：在新项目使用 `skills install --target .agents/skills` 或 `.claude/skills`。已有宿主副本禁止盲目 `--overwrite`，按升级流程保护定制。激活 Hooks 是单独的明确本地配置授权。

已有 Workspace：读取其状态；缺少新资产先升级。已有普通 LaTeX：新建独立研究项目，保留原稿，通过 PUBLICATION.md 的 adopt 流程接入副本。Word／PDF 仅在拥有合适转换工具时按能力边界处理，不宣称无损导入。

## 菜单到执行的映射

| 菜单 | Skills 与执行要点 |
|---|---|
| 1 新建 | 先确认名称／作者，目标未定可先通用初始化。指定 venue 时由 venue-setup 检索官方当届原文，填写 profile，调用 venue discover/init，必要时 latex adopt。JSON 由 agent 生成。 |
| 2 改稿 | auto-route → writing-language / manuscript-sync；用实际节点和文件哈希构造提案。读取 propose 返回的真实 ID，再 show/apply；不要让用户处理 ID。 |
| 3 文献 | researcher / knowledge-evidence；浏览需明确查询范围和隐私。默认只导入未核验候选。已有原文、反证和定位保留。 |
| 4 想法 | idea-evaluation / logic-methodology；读取已填工作表，比较方案并保留未知；不编造结果。 |
| 5 分析图表 | logic-methodology / figure-visualization；先查数据和实际方法，审查代码并取得执行许可，再 run。图表必须来自真实结果。 |
| 6 Overleaf | overleaf-sync；复用已确认服务器与目录，询问必要项目链接；插件安装、登录和上传分别确定。账号仅在本机登录；不要求聊天粘贴 token。 |
| 7 转投 | venue-setup → venue-transfer；先取得新模板与规则，预览到新目录的迁移，保留旧稿，编译／检查后再切换活跃稿件。不沿用旧项目上传授权。 |
| 8 审查 | reviewer / rules-compliance；先执行 review，再独立检查真实材料。只给实际范围内的结论；有问题先列修复。打包不等于直接提交到投稿网站。 |
| 9 进度 | 读取 status、route status 与已有 history/report；默认不创建新的任务，不把历史审核当成当前有效审查。 |
| 0 设置 | 根据用户用语区分打开／切换、更新、环境、Hooks、技术说明。先读现有配置，只改明确选中的事项。 |

研究操作在有实际编辑目标和权限后，用 `route --actor ai:HOST` 前后捕获。导航层只做选择和信息收集，不复制 auto-route 的队列。仅对已明确授权的常规编辑使用 agent 自身身份申请／应用提案；未授权的科学变化仍保留等待确认。不能伪装用户执行人工声明，不能清空问题来通过质量门。

## 更新：一句自然语言触发，后台细节由 agent 处理

定位当前框架仓库及实际虚拟环境，保存本地修改；先执行根目录 `update_aiworkspace.py --project STUDY --check`。向用户说明新功能、冲突和影响后，获准再 apply；从预览回执取完整目标 SHA 加 `--expected-commit SHA`，避免预览后上游改变。禁止 hard reset、自动 stash、强推或重新 init。源码引擎有本地修改时按 UPDATING.md 保留，不绕过保护。

新菜单与 Skill 通过受管清单三方更新，已填写研究、原稿、数据、用户规则不会被覆盖。宿主 Skills 已登记则随更新进入；未登记时由 agent 选择合适宿主目录安装一次。更新后实际检查 guide/menu 文件、版本及 Skill 数，不因命令返回成功就宣称全套宿主已测试。

## 回复、错误与确认

用户看到编辑结果／文件位置／关键风险；成功记录和内部命令可以安静完成。涉及新安装、联网传输、付费、远端写入、删除、冲突、研究强度变化时，以具体动作和范围集中确认。工具许可框保留，不能为了无感使用而绕过。

失败时保留文件、报告已完成和未完成的部分，给一个实际可执行的恢复动作。禁止把异常堆栈直接当使用说明，禁止杜撰工具、后台任务、登录状态或审核通过。普通对话里的“确认”只对应最近那个明确计划，不建立无限期授权。

## 维护入口的官方依据

入口按宿主实际能力读取，不能保证任意 agent 自动加载。Codex 的项目指令与 Skills 机制：[AGENTS.md](https://developers.openai.com/codex/guides/agents-md/)、[Skills](https://developers.openai.com/codex/skills/)。Claude 的项目说明读取：[项目记忆](https://code.claude.com/docs/en/memory)。检查日期 2026-09-27。通用兼容入口始终是 README 中的自然语言启动指令；没有安装特定模型账号。

如果框架来自 ZIP、没有 Git 历史，更新时先说明这一情况。经允许在新目录建立官方仓库的干净 Git 克隆，保留原 ZIP 目录与本地改动，核对差异再连接既有论文基线。不要在原文件上强行初始化、覆盖或伪造远程历史。
