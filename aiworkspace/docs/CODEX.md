# 用 Codex 使用 AI Workspace

Codex 使用根目录 **AGENTS.md** 和 **.agents/skills/** 作为项目指引及本地 Skill 入口。这两处已经随仓库提供。Claude 的入口另外保留为 CLAUDE.md；两种宿主共用同一份菜单和科研流程。

## 用户只需这样开始

在具有本地文件能力的 Codex 应用／IDE 中打开完整的 AI-Research-aiworkspace 文件夹，新建会话后说：

> 显示 AI Workspace 菜单，带我使用。操作由你完成，需要我确认的地方再问我。

之后可以回复“选 1，新建论文”“帮我改摘要”“连接实验室 Overleaf”或“更新 Workspace，保留我的论文”。使用 Codex CLI 的用户在其已打开的项目会话中使用同样的自然语言。无需自己填写 JSON、输入 Python 命令或记 Skill 名称。

这一步需要你已经能够使用 Codex 并在自己的客户端登录。读取菜单不依赖本框架的 Python 安装；创建文件、安装依赖、编译、联网和远端同步需要对应工具权限，Codex 应按实际范围请求授权。没有本地文件权限的云端任务不能直接修改你电脑上的论文，也不能操作本机 Overleaf 插件。

## 已提供的 Codex 接入

| 位置 | 作用 |
|---|---|
| [根目录 AGENTS.md](../../AGENTS.md) | Codex 的项目启动指引；区分使用论文助手与开发框架 |
| [.agents/skills/workspace-guide/SKILL.md](../../.agents/skills/workspace-guide/SKILL.md) | 菜单和自然语言需求的发现入口，转到统一的 workspace-guide 契约 |
| [.agents/skills/workspace-guide/agents/openai.yaml](../../.agents/skills/workspace-guide/agents/openai.yaml) | 可选的显示名、简短说明、默认提示和隐式调用策略 |
| [完整 workspace-guide](../research_workspace/assets/skills/workspace-guide/SKILL.md) | 共用菜单、项目选择、必要信息收集与授权流程 |
| 每篇论文自己的 AGENTS.md 和 .agents/skills/ | 由现有初始化／Skill 安装流程生成，提供论文专属状态入口和 14 个内置 Skills |

仓库里的轻量入口服务首次使用。真正改论文时，应打开或明确选择那篇论文的根目录；Codex 在授权范围内处理环境准备和项目 Skill 安装，保留已有定制。不要仅把工作目录切换到仓库内的框架实现目录，就当成打开了一篇论文。涉及仓库外目录时，使用 Codex 的正常目录选择／授权方式，不关闭沙箱来扩大范围。

本次新增 openai.yaml 位于框架仓库入口，随 Git 与源码 ZIP 分发。现有论文安装器仍分发 SKILL.md；它已支持 Codex 的本地 Skill 发现，显示元数据是可选项，本次不修改论文资产格式或研究 Schema。界面是否呈现显示名由当前客户端决定；允许隐式调用也不保证每个模型在每一轮都选中该 Skill。

## 自动沉淀在 Codex 中如何工作

明确改稿或研究讨论直接进入 auto-route。Codex 根据论文入口，在实际修改前后执行本地捕获、读取待办并调用专业 Skills；用户不用手动维护状态。菜单浏览不触发捕获，框架目录也不充当论文。

当前仓库的 `rw route install-hooks` 是 Claude 专用安装器。Codex 使用上述回合内调用路径；不要把 Claude 的 Hook 配置写进 Codex 或声称已完成 Codex 生命周期 Hook 接入。Codex 本身提供独立的 Hooks 机制，本仓库尚未实现和验证它的专用适配。宿主未运行期间的外部修改在下一次捕获时发现。

## 为什么不强制提供 .codex/config.toml

该文件用于可选的项目配置。显示菜单和发现本地 Skills 使用上面的入口即可。本项目保留用户自己的模型选择、登录、权限、沙箱和网络设置，不为自动显示菜单修改全局配置，也不自动启用 Hook、后台任务或全盘写入。

项目级 Codex 配置只在项目受信任时加载；信任由用户与宿主控制。账号、认证文件、会话、缓存及机器专属路径不要提交到公共仓库。仓库不提供 CODEX.md 作为另一份自动执行指令；本文是使用说明，统一启动规则仍在 AGENTS.md。

## 没有出现菜单时

先确认当前打开的是完整框架目录或实际论文目录；新增入口后重新开启该目录下的会话。然后说：

> 请读取当前项目根目录的 AGENTS.md，按它显示菜单；不要安装或修改文件。

仍有问题时，让 Codex 说明实际加载的项目指引，检查是否存在更近的 AGENTS.override.md、指令长度限制、被禁用的 Skill 或错误工作目录。不得要求用户贴出账号文件或完整私人会话。当前 CLI／IDE 支持显式 Skill 选择时，也可用 `$workspace-guide` 作可选的诊断入口；正常使用依旧以自然语言为主。

已有使用中的论文可以说：“请更新框架并检查这篇论文的 Codex 入口，保留正文、已填写内容和本地定制。”框架入口随正常 Git 更新；论文专属入口沿用三方资产升级，禁止重新初始化已有论文。

## 官方依据与验证范围

核查日期：2026-09-28。以下均为 OpenAI 官方文档入口，可能重定向到 ChatGPT Learn：

- [AGENTS.md 的发现与优先级](https://developers.openai.com/codex/guides/agents-md)
- [本地 Skills 与 openai.yaml 元数据](https://developers.openai.com/codex/skills)
- [项目配置、信任与作用域](https://developers.openai.com/codex/config-basic)
- [Codex 自身的 Hooks](https://developers.openai.com/codex/hooks)

本次变更仅涉及入口说明、可选菜单元数据和分发白名单；不增加科研 Skill，也不变更 0.4.0 引擎或 Schema 1。本地验证检查入口／元数据契约、真实 ZIP 内容及发布器保护；本轮未运行真实 Codex 客户端／模型会话或完整科研回归，不能声称所有客户端自动加载、远端同步或云端 CI 已通过。记录见 [Codex 入口验证](../verification/codex-entry/tests.json)。
