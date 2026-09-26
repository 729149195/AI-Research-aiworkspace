# AI Research Workspace

本地维护整篇论文的研究逻辑、证据、方法、规则与正式稿件。**Workspace 管研究，Manuscript 管表达，Skills 管过程，Sync 管双向变更，Reviewer 管最终质量。**

当前框架版本 **0.3.0**，研究 Schema 1。默认离线，无第三方 Python 运行时依赖；模型账号和工具由你选择的、已授权的 AI 宿主提供。自然改稿通过 auto-route 沉淀变化，不要求用户每次挑选 Skill 或编辑状态文件。

## 仓库入口

```text
AI-Research-aiworkspace/
├── aiworkspace/              # 框架、13 个 Skills、模板、测试、详细文档
├── update_aiworkspace.py     # 已使用论文的增量更新
└── README.md                 # 本说明
```

隐藏的 `.github/` 与 `.gitignore` 维护测试和版本管理。**论文项目放在本框架仓库外**，内部 `workspace/` 与 `manuscript/` 并列；一个框架可以维护多篇论文，不要将未发表研究放进公共仓库。

## 1. 安装并运行演示

需要 Python 3.11+ 和 Git。LaTeX 编译另需 TeX Live／MiKTeX；编辑器插件可选。首次安装构建工具需要网络，核心研究流程默认不联网。

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

后续 Windows 示例中的 `rw` 可替换为 `.\.venv\Scripts\python.exe -m research_workspace`，无需降低系统脚本策略。`doctor` 检查 13 个 Skill 契约。演示实际处理合成数据，所有人工核验／审核声明标记为模拟，不能用于真实投稿。打开 `../research-demo/workspace/reports/dashboard.html` 看离线状态。demo/init 均拒绝覆盖非空目录，重跑需新目录。

## 2. 建立论文，让 AI 正常工作

```bash
rw init ../my-paper --name "我的论文" --author "作者姓名"
rw --project ../my-paper skills install --target .agents/skills
# Claude Code 使用 --target .claude/skills
```

在 **my-paper 根目录**打开有文件操作权限的 AI 宿主。先填写 `workspace/research/idea-evaluation.md`，把实际导师／期刊／伦理／AI／术语要求放进 `workspace/rules/project-policy.md`。原 Idea Evaluation PPT 已转为逐页 Markdown 原文和十部分填写表；框架不发布 PPT 二进制。

对宿主说：

> 先读 START_HERE.md 和 AGENTS.md，以 auto-route 为默认入口。我正常改论文、提供导师意见或讨论方案时，你负责记录实际变化、更新相关研究状态并调用对应 Skills。常规整理少打断，证据、重要研究结论、双向冲突或超出授权的操作集中确认。

默认入口会在操作前后捕获 Diff、归档必要上下文、定位全局影响并合并待办。选择理由和 Memory 属于上下文，不能成为事实证据。Claude 可选生命周期 Hooks：在论文目录执行 `rw route install-hooks` 预览，然后 `rw route install-hooks --approve`，重启宿主核对。其他宿主按 AGENTS.md 主动调用。宿主关闭期间的改动在下一次捕获发现。

## 3. 新增：模板、年度规则、Overleaf 与转投

| 功能 | 默认 Skill | 完整操作 |
|---|---|---|
| 找到官方推荐 Overleaf／出版社模板，下载完整 LaTeX 项目，保存当前届次规则和日期 | venue-setup | [模板与投稿规则](aiworkspace/docs/PUBLICATION.md) |
| 自建网址、编辑器登录、Replica 配置，或原生 Git Bridge 同步 | overleaf-sync | [Overleaf 配置](aiworkspace/docs/OVERLEAF.md) |
| 保留旧稿，把全文、公式、引用与图表迁移到目标格式新版本 | venue-transfer | [转投说明](aiworkspace/docs/RESUBMISSION.md) |

用户可直接说：“按目标期刊／会议和届次初始化论文”“配置南开自建 Overleaf”“把这篇论文转投指定 venue”。AI 宿主负责检索与语义操作，CLI 负责下载、归档、校验、写入、同步和编译。通用 CLI 不内置全网搜索引擎，未收录 venue 由 Skill 查阅官方页面后生成 profile；遇到登录墙时使用用户在本机下载的 ZIP。

初始化出的论文模板位于 `manuscript/latex/<venue-id>/`；原始模板位于 `workspace/venues/`；规则、来源、时间、时区和版本位于 `workspace/rules/venues/`。未核查项保留 unknown，过期日期标记 past，不把旧届次或通用模板误用为当前要求。初稿示例内容不成为本文事实。

LaTeX 原生绑定后，正常 `rw sync`、auto-route、任务包和质量检查使用活跃 `.tex` 稿件。转投先创建新目录和迁移报告，再实际编译检查，不自动替换旧稿或推送到旧 Overleaf 项目。

自建站默认 `https://nankaivisoverleaf.asia/`，可修改。Workshop 是社区插件，账号／cookie 在本机插件中配置；原生 Git Bridge 需 Server Pro 已启用该能力，使用 Git 专用 token。框架提供不回显的 `--token-prompt`，不保存密码。插件实时协作和 Git 前台轮询分别说明，不同时写同一目录。

## 4. 研究闭环

13 个 Skills：auto-route、researcher、knowledge-evidence、logic-methodology、writing-language、figure-visualization、manuscript-sync、reviewer、rules-compliance、idea-evaluation、venue-setup、overleaf-sync、venue-transfer。

来源发现 → 原文核验 → Evidence 与 Claim → 方法／实际结果 → 写作／图表 → 双向同步 → 独立审核 → 下一轮。每个节点有稳定 ID 和依赖；新证据、规则或稿件改动产生可追踪影响。证据区分支持、反驳、条件限定，保留反证与不确定性。

```bash
rw --project ../my-paper status
rw --project ../my-paper route status
rw --project ../my-paper sync status
rw --project ../my-paper review
rw --project ../my-paper packet logic-methodology --task "检查整个论证链和方法边界"
```

新项目显示 blocked 正常。退出码 1 表示质量／检查阻塞，2 表示输入或安全边界错误。AI 可以按用户已授予的编辑权限操作提案，重要科学选择和 `--human` 核验／最终审核由真实责任人完成。所有引用与方法结果都需原文或真实执行支撑。审核声明绑定内容指纹，改动后过期；未完成独立审核不能作为真实投稿放行。

详细示例见 [从零使用](aiworkspace/docs/GETTING_STARTED.md)、[自动沉淀](aiworkspace/docs/AUTO_ROUTE.md)、[数据结构](aiworkspace/docs/SCHEMA.md)。旧文档中 Markdown 是默认模式，0.3.0 的原生 LaTeX 扩展以 [PUBLICATION](aiworkspace/docs/PUBLICATION.md) 为准。手动聊天任务包与可选 API 见 [Skills](aiworkspace/docs/SKILLS.md)，付费服务和外部传输均需授权。

## 5. 已用项目的增量更新

在框架仓库根目录、专用虚拟环境执行：

```bash
python update_aiworkspace.py --project ../my-paper --check
python update_aiworkspace.py --project ../my-paper --apply --actor "作者姓名"
```

先读预览，可用 `--expected-commit 完整SHA` 锁定预览版本。三方比较旧默认／本地／新默认，保留非冲突定制，冲突要求显式选择；不使用 hard reset、自动 stash 或 force-push。**已填写工作表、论文、数据、方法、证据、项目规则和已下载的 venue 模板均不被框架默认更新覆盖。**

保留 `.rw/framework.json` 更新基线并独立备份研究。资产备份／回滚：

```bash
rw --project ../my-paper upgrade history
rw --project ../my-paper upgrade rollback UPDATE-ID
```

回滚检查期间新增编辑；引擎恢复与资产回滚分别处理。[更新说明](aiworkspace/docs/UPDATING.md)；[旧论文切换框架仓库](aiworkspace/docs/NEW_REPOSITORY.md)。0.3.0 保持 Schema 1，新增 Skills 通过已有注册的宿主路径更新；安装编辑器插件、配置远端和执行同步仍须单独授权。

## 6. 验收与维护

[本次真实验收记录](aiworkspace/DELIVERY.md) 区分软件测试、实际 TeX 编译、真实本地 Git 收发、模拟网络接口，以及尚未执行的自建服务器认证／完整编辑器会话。无法从配置成功推断登录成功，无法从本地测试推断 GitHub Actions 通过。

```bash
python aiworkspace/scripts/run_tests.py
python aiworkspace/scripts/check_docs.py
python aiworkspace/scripts/smoke_root_update.py
python aiworkspace/scripts/smoke_publication.py --destination ../publication-demo-new
```

原生迁移是有边界的 LaTeX 适配，特殊宏／复杂构建可能需要人工补充；机器检查不能认证科学有效性、完整合规、匿名性或期刊接收。参见 [架构](aiworkspace/docs/ARCHITECTURE.md)、[贡献规范](aiworkspace/CONTRIBUTING.md)、[安全边界](aiworkspace/SECURITY.md)。只把已授权公开的框架改动提交到本仓库。
