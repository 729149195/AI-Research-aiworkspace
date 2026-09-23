# Auto-route：自然改论文，持续沉淀研究

从 0.2.0 起，`auto-route` 是第 10 个内置 Skill，也是论文会话的默认入口。用户直接说“润色讨论”“导师改了这一段”“补这篇文献”“统一术语”，AI 根据项目入口自动捕获和分派工作。平时无需选择 Skill 或操作状态文件。

## 1. 第一次接入

先按仓库 README 安装，在框架之外创建论文项目，并把 Skills 安装给你的文件型 AI 宿主：

```bash
rw init ../my-paper --name "我的论文" --author "作者姓名"
rw --project ../my-paper skills install --target .agents/skills
# Claude Code 使用 --target .claude/skills
```

在 **my-paper 根目录**打开已授权宿主，让它读 `AGENTS.md` 与 `START_HERE.md`。可直接使用这段开场指令：

> 请读项目入口，以 auto-route 作为默认入口。以后我直接改稿、讨论想法和提供反馈时，你负责捕获实际改动、保存必要的上下文并调用对应 Skills 完成维护。常规整理尽量少打断；研究结论、证据强度、双向冲突或超出我授权范围的操作统一向我确认。不要把捕获记录当成核验完成。

用户已经明确授权的本轮编辑可由宿主在该范围内执行；重要研究判断和独立核验仍保留原权限。AI 使用真实的 `ai:...` 操作身份，不能伪装为作者、核验人或独立审核者。普通网页聊天没有本地文件监听或操作能力。

## 2. 一次正常改稿会发生什么

用户：“把讨论里的‘导致’改成‘相关’，摘要也检查一下。”

宿主先运行一次本地捕获，阅读现有状态；用 Writing 和 Sync 处理实际稿件；在修改后再次捕获，保留逐节 Diff；将相关 Claim、Evidence、Methods、摘要、讨论、结论和图注交给相应 Skills。确有推断强度变化时，提出一次组合式研究确认。完成修复和复核后，关闭对应待办，下一位作者或 AI 会话可以接续。

捕获程序不会仅凭关键词断言“只改了措辞”。它保守地把可能有研究含义的改动留待复核。CLI 不会自行调用模型或执行分析；实际语义工作由宿主执行的 Skills 完成。

| 观察到的变化 | 默认路由 |
|---|---|
| 正文、章节、Claim | Sync → Logic / Evidence → Writing / Figure → Reviewer |
| 新来源、引用、证据材料 | Researcher → Evidence → Logic / Writing → Reviewer |
| 方法、数据、结果 | Logic / Method → Evidence / Figure / Writing → Reviewer |
| 图表 | Figure → Evidence / Writing → Reviewer |
| 期刊规则、项目规则 | Rules → Writing → Reviewer，重新检查全局影响 |
| Idea 工作表、研究方向 | Idea Evaluation → Researcher / Logic → Reviewer |
| 讨论、措辞偏好、可能决策 | 保存为未确认上下文，按类型分派；不自动形成事实 |

这些是有顺序的工作建议。路由队列不自行运行付费模型、联网、执行代码或签署审核。

## 3. 数据保存在哪里

```text
my-paper/
├── workspace/state.json                    # 规范研究节点、问题，以及按 Skill 合并的持久待办
├── workspace/sync/auto-route.json           # 上次观察到的文件哈希、节点指纹与 Markdown 快照
├── workspace/history/auto-route/CHANGE-*.json # 不覆盖既有记录：差异、归属、影响、备注与待办 ID
├── workspace/research/idea-evaluation.md    # 作者自己的工作表
├── workspace/rules/project-policy.md       # 已确认的项目规则
└── manuscript/main.md                      # 正式工作稿，与 Workspace 并列
```

事件记录绑定 change record 哈希；完成命令会核对记录完整性。捕获记录是观察和上下文，规范研究状态仍在 `state.json`。外部数据/代码/图像只保留哈希和来源引用；不会把所有二进制复制进记忆。

相同状态重复扫描不新增记录。连续多次编辑保留各次 change record，同时把同一 Skill 的未完成工作合并到一个待办，避免任务刷屏。`cycle` 不会丢掉旧的未完成路由任务。自动生成的捕获文件不参与再次触发或科研指纹；实际研究文件和问题仍会使旧审核失效。

## 4. 讨论也要沉淀

宿主仅记录与研究相关、必要且获授权的简短归纳，保留说话人及不确定性。例如：

```bash
rw route --actor ai:session --note "作者提出：下一轮比较两种编码，当前尚未选择。" --note-kind decision-candidate
rw route --actor ai:session --note "作者偏好：全文统一使用该术语，语义适用范围待核对。" --note-kind preference
```

默认类型为 `discussion`。它们都保存为 `unconfirmed-context`；原始偏好不会自动改写 Rules，讨论中的想法不会自动变成 Evidence。已选择的决策、已确认的规则和已核验的证据由对应 Skill 通过原有提案/确认流程写入正式位置。不要自动复制整段聊天，更不要读取 transcript、环境密钥或无关私人文件。

## 5. 可选 Claude Code Hooks

在论文项目根目录，先预览，再明确授权安装：

```bash
rw route install-hooks
rw route install-hooks --approve
```

这会合并 `.claude/settings.local.json` 中自己的 Hook，保留其他 Hook、权限和设置。使用当前虚拟环境 Python 的绝对路径及固定项目路径；命令使用 `-I` 隔离当前目录/PYTHONPATH 的模块干扰。预览只展示自己的命令与事件，不回显其他设置中的环境内容。安装前的设置保存在 `.rw/auto-route-hooks.json`；修改后重启宿主并确认配置生效。手工恢复备份前核对是否有后续设置改动。

事件覆盖 `SessionStart`、`UserPromptSubmit`、`PostToolUse`（Write/Edit/MultiEdit/Bash）、`Stop`、`PreCompact`。PostToolUse 无新变化时静默；Stop 只落盘，不阻止停止或触发新一轮回复。捕获失败会留下简短提示，不改变来源核验或稿件审批状态。

```bash
rw route remove-hooks            # 预览移除
rw route remove-hooks --approve  # 只移除本程序记录的 Hook
```

Hook 依赖宿主运行和当前配置，关闭宿主后的编辑会在下一次捕获发现。它没有常驻文件监听进程。更换虚拟环境路径后重新安装 Hook。Windows 的 Hook 命令按 Claude 的 Git Bash 执行方式引用路径；实际完整 Windows/宿主运行尚未验证，需本机检查。Codex 等其他宿主通过项目入口驱动 Skills；不提供未经验证的通用 Hook 配置。

依据与访问日期（2026-09-24）：[Claude 官方 Hooks](https://code.claude.com/docs/en/hooks)、[Codex 官方 Skills](https://developers.openai.com/codex/skills/)、[AGENTS.md](https://developers.openai.com/codex/guides/agents-md/)。本地 Hook 输入/合并/幂等测试和完整宿主效果评估分别记录。

## 6. 排查与手动入口

以下命令主要由宿主在内部使用；作者随时可以检查：

```bash
rw route --check                 # 只读检查，项目文件不变
rw route --actor ai:session      # 保存实际观察与待办
rw route status                 # 尚未捕获的变化 + 已捕获但未完成的工作
rw sync status                  # 原生 Markdown 同步差异
rw review                       # 包含尚未解决的路由复核问题
rw route complete CHANGE-ID --actor ai:session --note "具体说明已经处理的改动、同步与对应复核结果。"
```

完成操作要求关联问题已解决、没有更新但尚未捕获的改动；涉及稿件时要求 Sync 一致。合并后的 Skill 待办要等所属 change records 都完成才结束。完成路由不签署人类审核，也不会绕开投稿质量门。

并发写锁、中断事务、未知快照版本、符号链接、损坏章节标记均不能被静默忽略。损坏标记会保留待处理记录；读写失败不推进捕获基线。事务恢复沿用 `rw recover`，确认旧写者退出后才使用 `--clear-lock`。

当前限制：主 Markdown 最多 512 KB；扫描最多 10,000 个被纳入的文件；单个生成的快照/记录最多 4 MiB；每个 Diff 超过 16,000 字符会明确标记截断。大稿件或更多文件需要分拆或扩展适配器。首次激活旧项目只知道已有 Sync 基线及当前文件，不虚构更早历史。完整历史请另用私有 Git/数据备份。

## 7. 已使用 0.1.0 的项目如何升级

关闭当前写者，在**框架仓库根目录**运行原来的更新入口：

```bash
python update_aiworkspace.py --project ../my-paper --check
python update_aiworkspace.py --project ../my-paper --apply --actor "你的姓名"
```

更新会增量补入第 10 个 Skill、默认入口指令，以及已注册宿主的 Skill 副本。你改过的入口/Skill 仍进行三方比较；有冲突时明确合并或选择，避免覆盖定制。源码引擎更新后，旧 Schema 1 项目无需迁移研究数据；第一次 `rw route` 安全建立观察基线。

Hook 属于用户本机设置，**不会通过框架升级擅自启用**；需要上面的单独授权安装。稿件、数据、已填写 Idea Evaluation、证据及用户规则均不作为框架资产覆盖目标。
