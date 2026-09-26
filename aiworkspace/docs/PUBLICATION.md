# 期刊／会议初始化与年度投稿规则（0.3.0）

在框架之外创建论文项目，`workspace/` 维护研究，`manuscript/` 维护正文。模板与正文均使用相对于论文根目录的路径；请勿把真实论文写入公共框架仓库。

## 自然语言入口

在有文件与浏览权限的 AI 宿主中打开论文根目录，让它读取 AGENTS.md 和 auto-route Skill，然后直接说：

> 按我指定的期刊／会议、届次、稿件类型和投稿阶段初始化论文。查阅今年实际适用的官方要求，找到官方推荐的 Overleaf 模板和完整源码 ZIP，保存规则、截止时间和来源，再建立可以直接编写的本地 LaTeX 项目。未知信息单独列出。

`auto-route` 会分派 `venue-setup`。浏览、模板选择和语义解释由宿主完成；CLI 负责有边界的获取、归档、校验和初始化。CLI 自带少量注明年份的发现入口，其他期刊／会议由宿主搜索官方网页后传入 `--official-url`，不会从旧年份猜一个下载地址。

先明确：期刊／会议、会议届次、实际投稿年份、track／article type、review／camera-ready／preprint、匿名要求。仅有通用出版社模板不足以确定会议的页数、截止时间或匿名模式。比如 VGTC 的 TVCG 特刊模板与常规 TVCG 投稿、会议短文模板适用范围不同，详见 [官方说明](https://tc.computer.org/vgtc/publications/journal/)。

## 可复制的命令流程

以下从框架仓库根目录、已激活虚拟环境执行。尖括号字段须由真实查阅结果替换；终端中不要保留尖括号。

```bash
rw init ../my-paper --name "我的论文" --author "作者姓名"
rw --project ../my-paper venue discover --name "目标会议" --year 2027 --track "full papers" --official-url "https://真实官方网站/对应届次/投稿指南" --online --actor ai:venue
```

结果打印 discovery 记录和候选链接。让 `venue-setup` 打开官方投稿说明、官方推荐的 Overleaf Gallery 页面、下载按钮或出版社源码链接，填写 [profile 示例](../examples/venue-profile.example.json)。Gallery 页面自身返回 HTML，不能当成 ZIP。优先使用官方明确推荐的模板；需要登录时由用户在本机合法下载，使用离线参数导入。不要传入含 cookie/token 的 URL，不执行模板中附带的安装脚本。

```bash
rw --project ../my-paper venue init --profile /本地/venue-profile.json --online --approve --actor ai:venue
```

命令下载完整归档并记录 SHA256。重定向目标需要精确加入 profile 的 `allowed_hosts`；例如官方 GitHub 归档可能重定向至 codeload.github.com。下载前检查许可；模板保留其原有版权。危险路径、符号链接、压缩炸弹、重名文件、HTML 登录页被拒绝；隐藏执行配置和无法识别的文件不装入工作目录，跳过清单与原 ZIP 保留。已有目录拒绝覆盖。

离线方式：将原始规则的 UTF-8 提取分别命名为 `<source-id>.txt`，放在同一个目录。每份提取必须保留定位与上下文，PDF 需要先合法提取并核对，不能把 PDF 二进制改名为 txt。

```bash
rw --project ../my-paper venue init --profile /本地/venue-profile.json --archive /本地/template.zip --sources-dir /本地/原文提取目录 --approve --actor ai:venue
```

离线材料明确标记为用户提供，不能宣称已实时访问原网站。可选 `template.sha256` 锁定已审阅归档。多主文件模板必须指定准确 `template.main`。模板内的示例作者、结果、引用和伦理声明保留为模板示例，必须替换或清除，不能登记为本文事实。

## 生成的目录

```text
my-paper/
├── workspace/venues/<venue-id>/template/       # 原 ZIP、许可证、全部可接受源文件、来源哈希
├── workspace/venues/index.json                 # 安装版本与路径
├── workspace/rules/venues/<venue-id>/revision-001/
│   ├── SUBMISSION_RULES.md                     # 13 类规则主题、候选原文和缺口
│   ├── dossier.json                           # 结构化规则、日期、来源及待核查状态
│   ├── deadlines.ics                          # 有准确时间及时区的候选截止日期
│   └── sources/<source-id>.txt                 # 可回查的原始文本提取
└── manuscript/latex/<venue-id>/                 # 实际可编写的完整模板工作副本
```

规则主题包括范围与稿件类型、格式／篇幅、匿名、截止时间、投稿系统、补充材料、伦理与同意、AI 使用、原创性／转投、版权许可、费用注册、审稿／终稿、引用与可访问性。关键词匹配生成候选片段，不能证明完整合规；`unknown` 项由 Skill 查阅官方来源继续补齐。结构化条目必须绑定真实 source id 和逐字原文。时间明确到时区才生成日历事件，事件状态为 tentative；未知时分不补午夜，历史日期显示 past。

刷新规则会读取同一组原始来源、显示差异、创建新版本并产生全局复核任务：

```bash
rw --project ../my-paper venue refresh <venue-id> --online
rw --project ../my-paper venue refresh <venue-id> --online --approve --actor ai:venue
```

原文发生变化后，已经不匹配的旧截止日期／规则失效并进入 `invalidated_structured_entries`，不会继续作为新规则使用；原版本仍保留。更换届次、track 或模板使用新 id/profile。新版本的确切时间与规则需重新提取；修改 profile 后以新 id 安装，当前刷新命令不暗中更改适用范围。

## 接入研究图与正常改稿

```bash
rw --project ../my-paper latex adopt --directory manuscript/latex/<venue-id> --main main.tex
rw --project ../my-paper latex adopt --directory manuscript/latex/<venue-id> --main main.tex --approve --actor ai:venue
rw --project ../my-paper latex build --allow-exec
rw --project ../my-paper route --actor ai:session
```

adopt 先预览章节，再建立 `% rw:section SEC-...` 标记和 `rw-content.tex`。原工作稿主文件在研究历史中保留，旧 Markdown 工作稿不被删除。绑定后以活跃 LaTeX 正文进行任务包、auto-route 和双向同步，原有 `rw sync status/propose` 继续使用。模板样例进入 draft；不要为消除警告而把示例节点设成 confirmed。

编译需要本机 TeX Live／MiKTeX 和相关 class/packages。支持 pdflatex、xelatex、lualatex，自动运行必要的 BibTeX；Biber、复杂构建链需单独审查。执行禁用 shell escape，不读取 .latexmkrc，但这仍是本地代码执行，无法替代操作系统隔离。编译目录位于 `.rw/builds/`；返回 PDF 路径、源文件哈希和未解析引用状态。之后修改源文件会使编译记录过期。必须实际打开 PDF 检查版面。

原生适配接受 UTF-8、字面量 input/include 和可平衡的结构。动态 TeX、外部导入、特殊宏环境需专门适配；不承诺任意历史论文的无损解析。失败保留原稿，说明无法处理的结构。

下一步：[Overleaf 配置与同步](OVERLEAF.md)；[转投迁移](RESUBMISSION.md)。
