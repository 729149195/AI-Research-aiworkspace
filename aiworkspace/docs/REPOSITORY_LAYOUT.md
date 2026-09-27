# 仓库入口、自动发现与哪些文件应共享

## 打开后怎么开始

在你的 agent 中打开完整的 `AI-Research-aiworkspace` 仓库文件夹。宿主支持并允许加载项目指令时，会读取根目录入口；首次交互没有具体任务时显示菜单，明确提出“帮我改摘要”则直接办理。用户无需先安装 Python 或执行命令才能看到菜单。

拉取文件本身不会启动模型、执行脚本、登录账号或持续监听。自动发现依赖宿主、当前打开目录和信任设置。已开启会话可能需要重新打开项目或新建会话；宿主没有读取时，只需说：“请读根目录 AGENTS.md，显示菜单。”单独提供网页链接也不会授予本地文件权限。

规范入口使用大写、复数的 **`AGENTS.md`**。普通 `agent.md` 可以被手工读取，但本项目不依赖它被默认发现，也不另存一份重复指令。

## 两层入口

```text
AI-Research-aiworkspace/            # 公共框架仓库
├── AGENTS.md                       # agent 的统一启动与分流规则
├── CLAUDE.md                       # Claude Code 导入 AGENTS.md
├── README.md                       # 给用户看的说明
├── aiworkspace/                    # 实现、菜单、Skills、模板和文档
├── update_aiworkspace.py           # 由 agent 操作的增量更新入口
├── .agents/skills/workspace-guide/ # 共享 Skill 发现入口
├── .claude/CLAUDE.md               # 原入口的兼容桥接
├── .github/workflows/              # GitHub 云端自动测试配置
└── .gitignore                      # 排除个人运行数据

my-paper/                          # 另一个目录，位于框架仓库之外
├── AGENTS.md / CLAUDE.md            # 初始化时生成的论文专属指令
├── START_HERE.md
├── workspace/                      # 本论文的逻辑、证据、规则与历史
└── manuscript/                     # 正文、LaTeX、图表
```

根目录 `AGENTS.md` 先帮助 agent 判断用户要使用论文助手还是开发框架，然后读取菜单和对应说明。进入论文目录后，读取该论文自己的入口、状态与规则。框架里的 `research_workspace/assets/AGENTS.md` 是生成论文入口的模板；它不代表框架根目录已经存在一篇论文。

## 哪些应放在 GitHub

| 文件或目录 | 本项目的处理 | 原因 |
|---|---|---|
| 根目录 AGENTS.md、CLAUDE.md、README.md | 提交 | 每个人拉取后获得一致的入口 |
| .agents/skills/ 中的公开 Skill | 提交 | 给支持该约定的宿主发现和使用 |
| .claude/ 中的共享指令或经审查的 Skill | 按文件提交 | 方便团队使用；当前只分发公开的兼容入口 |
| .claude/settings.json | 可选，审查后再提交 | 仅适合无秘密、无私人绝对路径的团队配置；本项目没有为了显示菜单添加自动执行 Hook 或放宽权限 |
| .github/workflows/*.yml | 保留并提交 | GitHub Actions 从仓库根目录的这个路径发现构建／测试工作流；本地使用菜单不依赖云端 CI |
| .claude/settings.local.json、CLAUDE.local.md | 忽略 | 个人配置、机器路径或本机权限选择 |
| 账号凭据、token、cookie、.env、会话日志 | 不提交、不打包 | 由本机安全登录或凭据管理机制保管 |
| 真实论文、数据与 .rw 运行状态 | 不进入公共框架仓库 | 论文另存；需要协作时使用自己的受控项目仓库 |

隐藏目录本身不意味着缓存或秘密。共享指令值得版本管理，机器运行数据应隔离。不要把整个 `.claude/` 或 `.agents/` 一概忽略，否则公共入口无法随仓库分发。

`.gitignore` 仅减少误提交，不会移除已经进入 Git 历史的内容，也不能识别任意文件中的秘密。提交前仍需检查差异；已经泄露的凭据需要作废并更换。源码打包显式包含根入口和已知公开宿主文件，不递归打包用户根目录的 `.claude`。

## 后续更新

新 clone 和发布用源码包都包含根目录入口。已有 clone 通过正常框架更新获得这些文件；`workspace/` 与 `manuscript/` 不作为框架更新目标。已有论文自己的入口继续使用原三方资产更新。本次补齐根入口不改研究 Schema，也不要求重建论文或重新授权全部功能。

## 依据与验证边界

核查日期：2026-09-27。不同宿主的规则分别以其官方文档为准：

- [Codex 的 AGENTS.md 发现规则](https://developers.openai.com/codex/guides/agents-md)：从项目根目录到当前目录读取指令。
- [Claude Code 的项目记忆](https://code.claude.com/docs/en/memory)：支持用 CLAUDE.md 的 `@AGENTS.md` 导入共享指令，导入路径相对于所在文件。
- [Claude Code 的配置作用域](https://code.claude.com/docs/en/settings)：区分共享项目设置与 settings.local.json。
- [Codex Skills](https://developers.openai.com/codex/skills)：说明仓库中的 .agents/skills 发现范围。
- [GitHub Actions 工作流](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows)：要求根目录 .github/workflows 中的 YAML。

自动发现规则与入口文件可以检查；完整宿主会话、账户认证和云端 CI 必须分别实测。克隆仓库不等于这些外部步骤已经完成。

本轮实际通过 24 项专项测试（12 项新入口／分发测试、12 项原发布器回归），包含真实本地 Git 忽略规则和 ZIP 字节检查。没有重跑全套科研测试或实际宿主会话；具体范围见 [测试记录](../verification/entry/tests.json)。
