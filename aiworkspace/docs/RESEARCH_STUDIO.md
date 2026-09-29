# 科研写作与绘图工作台 · 0.5.0

## 用户仍然只说目标

打开自己的论文项目，用原来的菜单 **5** 做数据与科研图，用 **2** 改稿，用 **8** 审查或处理审稿意见，用 **9** 接续进度。编号未改变，也没有新增一组必须学习的设置。

例如：“根据这些配对数据画一张论文图，保留每个样本。”“检查摘要和正文里的数字、结论有没有说过头。”“逐条处理审稿意见，回复里标出实际改在哪里。”“继续上次的任务，只问我现在必须决定的事情。”

agent 负责读数据、选图、填写参数、执行、看预览、保留代码及改动记录。首次缺少绘图库时集中申请一次本地环境安装授权；账号、收费模型和外部上传不自动启用。下面的命令和结构专供 agent／开发者阅读，普通用户无需输入。

## 一、可直接生成的七种科研图

| 类型 | 科学任务 | 重要约束 |
|---|---|---|
| scatter | 两个定量变量与分组 | 不凭散点自动声称相关性或因果性 |
| line | 有序变化／时间轨迹 | 数值排序；缺测 y 保留断点；重复 x 需先确定估计方法 |
| distribution | 分布、组间差异 | 箱线摘要＋全部原始点、各组 n；固定的横向抖动不改 y |
| paired | 同一观测单位前后比较 | 要求唯一配对 ID，保留每对轨迹 |
| interval | 已算好的点估计与区间 | 必须说明区间定义；不自动发明 CI、标准误或显著性 |
| heatmap | 方法×任务等矩阵 | 重复单元拒绝；缺失单元标记 NA；保留原始数据 |
| workflow | 2–6 步顺序流程 | 明确 planned／implemented，不能伪装成因果机制或实验结果 |

每次生成三个版本：SVG（保留文字）、PDF、PNG。尺寸以毫米指定，导出时不使用会改变页面物理尺寸的自动裁切。默认排版是通用起点，投稿尺寸与字体须查具体期刊当届要求。复杂机制图、交互设计、多面板、特殊归一化和大型图网络交给 agent 发现适用的专门工具；当前七类实现不会假装涵盖全部科研视觉表达。

绘图参考了 Matplotlib 的 [输出格式](https://matplotlib.org/stable/users/explain/figure/backends.html)、[savefig](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html)、[布局机制](https://matplotlib.org/stable/users/explain/axes/constrainedlayout_guide.html) 和 [Nature 研究图指南](https://research-figure-guide.nature.com/)。科研流程对照阅读了 K-Dense [scientific-visualization](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-visualization/SKILL.md) 前 135 行（核查 2026-09-29，blob 13f3ae9b115aefc2f15098bcfd460f0b96e047c2）。本项目实现独立编写，未自动安装上游脚本，未宣称完成全库许可／安全审计或全网最佳基准。

### 内部调用

绘图仅需可选 `figures` 依赖，核心研究引擎仍无第三方运行依赖。agent 检查专用虚拟环境和已有 Matplotlib；需要时经授权安装项目的 figures extra，不修改全局 Python。

```bash
python -m research_workspace.studio --project PAPER inspect-data workspace/data/observations.csv
python -m research_workspace.studio --project PAPER figure SPEC.json
python -m research_workspace.studio --project PAPER figure SPEC.json --approve --actor ai:figure
```

SPEC 由 agent 写到项目 `workspace/figures/`。公共字段：id、kind、input、title、purpose、caption、alt_text、claims、evidence、xlabel、ylabel、unit。可选 width_mm、height_mm、font_family、font_size、dpi。统计图读 CSV；Excel 等需要用实际可用工具转换并记录原表与转换方法。

映射字段：scatter/line 使用 x、y 和可选 group；distribution 使用 y、group；paired 使用 x、y、pair_id；interval 使用 x、lower、upper、label、interval_definition；heatmap 使用 row、column、value；workflow 使用 steps、workflow_status 且不提供 input。范例见 [figure-paired.json](../examples/figure-paired.json)。

默认 missing=error。明确选择 missing=omit 时需 omission_reason；程序记录涉及的 CSV 行号。折线的缺测 y 保留断点，缺失 x 无法可靠排序时停止。非数值、无穷、重复表头、重复配对、重复矩阵格等不会被默默修正。中文图需实际安装支持相应字形的字体，缺字会报错；仓库不分发字体文件。

### 生成位置与复现

```text
my-paper/
├── manuscript/figures/FIG-...-版本/
│   ├── figure.svg
│   ├── figure.pdf
│   └── figure.png
├── workspace/results/figures/FIG-...-版本/
│   ├── input.csv          # 冻结的本地图数据，不自动上传到 Overleaf
│   ├── spec.json
│   ├── reproduce.py       # 当时实际使用的完整渲染器源码
│   ├── caption.md
│   ├── alt-text.txt
│   └── README.md
└── workspace/history/figures/FGR-....json  # 源输入、输出、节点、代码与版本记录
```

每次用新目录，不覆盖旧图。渲染完成只表示实际产出了文件；原始研究、图意和视觉效果仍需核对。没有 Claim/Evidence 的探索图保持 unlinked，不能直接登记为有证据支持的研究图。图注自动补入实际 n、缺失处理或区间说明，仍要由作者／agent 根据上下文完善。

```bash
python -m research_workspace.studio --project PAPER figure-check workspace/history/figures/FGR-ID.json
python -m research_workspace.studio --project PAPER figure-propose workspace/history/figures/FGR-ID.json --actor ai:figure
```

第二行只生成 draft Figure 提案；之后沿用原有查看、批准、同步和独立审核。输入、输出、复现脚本或关联研究节点变化会被查出。失败发生在产物写入和登记之间时，新目录可能保留为未登记产物；应检查错误与记录，不能为了消除报错删除原稿。资产更新不碰这些用户文件。

## 二、先理清论证，再润色

writing-language 已改成分阶段流程：明确修改范围 → 整篇论证与段落职责 → 检查证据 → 起草 → 数字和结论一致性 → 自然学术语言 → 全篇复核。保留技术含义、限定条件与作者风格，减少机械套话和反复询问。

由 agent 从已知事实和授权对话维护 `workspace/research/writing-brief.md`：研究问题、拟贡献、读者、语言风格、术语表、不得擅改的内容及当前任务。已填写版本不受框架默认模板更新覆盖。偏好不变成科学证据；原 Idea Evaluation 十部分、可视化编码／任务／设计理由继续保留。写作任务包自动附带此 brief 和已有 glossary，独立 reviewer 默认不接收这个额外的作者偏好上下文。

```bash
python -m research_workspace.studio --project PAPER resume
python -m research_workspace.studio --project PAPER audit --save
```

审查报告包括 Claim–Evidence 支持状况、段落用途检查表、带位置的数字清单、待查夸大／因果措辞和图生成记录。它们是有位置的复核线索，不是自动科学评分。数字须按指标、分母、群体、单位与舍入对齐，不同队列的 n 可以不同；不要全局替换成同一值。常规审查默认只读，保存时仅新增报告，不改正文或核验状态。

## 三、审稿意见与实际修改相连

reviewer 增加逐条处理模式：原意见 → 问题含义 → 修改方案 → 实际执行 → 具体位置 → 回复草稿 → 复核。回复有道理的批评，保留有证据的不同意见；不把尚未做的实验写成完成。

agent 准备 comments 列表，每项有 id、reviewer、comment、action、response、locations。locations 含 path、quote 和当前 sha256，程序核查实际文件存在、哈希一致、原文可找到，返回行号。

```bash
python -m research_workspace.studio --project PAPER responses COMMENTS.json --save
```

状态区分 needs_work、response_draft、located_for_review。找到改动原文不代表审稿人已满意或科学问题已解决，不能自动进入“已完成审核”。报告存入 workspace/reports/studio，可由 agent 整理为正式回复文档；原评审材料与既有任务记录仍保留。

## 四、验证与适用范围

七类图真实生成并在相同环境用保存的脚本重新生成，PNG 字节一致；PDF 需独立渲染检查尺寸、文字和版面。Matplotlib 默认色彩、自动边界检查不构成完整可访问性或期刊合规认证。

本轮测试使用隔离的 Schema 1 软件实例与经过 Git blob 核对的现有核心模块，详情见 [专项验证](../verification/studio/tests.json)。没有将历史全部回归与本轮测试直接相加，没有声称完成真实 Codex／Claude 模型会话、远端 Overleaf 登录或云端 CI。当前 Markdown 审查与 LaTeX 文本检查分别测试，完整 LaTeX 接入继续复用既有引擎。

旧用户只需说：“帮我升级 Workspace，启用新的科研绘图和写作检查，保留我的论文、规则与定制。”agent 操作原增量更新器；研究 Schema 仍为 1，菜单保持原 10 个入口。
