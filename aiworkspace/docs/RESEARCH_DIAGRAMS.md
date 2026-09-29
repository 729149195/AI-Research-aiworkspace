# 科研流程图与示意图（0.6.0）

## 用户怎么用

在自己的论文项目里，直接对 agent 说：

> 把方法画成一张清楚、好看的论文流程图，保留分支与反馈；图源也留好，之后我还要改。

也可以说“画系统架构”“画实验设计”“做一个图形摘要”“把假设关系画成虚线”“改成黑白，横向排版”。仍使用菜单 **5**，无需输入命令或配置文件。新增 `research-diagram` 负责示意图，原 `figure-visualization` 继续处理数据图并按需调用它。全框架共 15 个 Skills，菜单编号保持不变。

agent 先复用你的图表目标、实际内容、语言和投稿约束，给出一个简短结构方案，然后完成本地渲染、检查与保存。默认用克制的编辑风格；只有真正涉及科研含义、信息结构或授权的选择才询问。首次缺少依赖时集中确认安装，禁止全局安装或暗中上传到在线绘图网站。

## 已提供的七类可编辑模板

| 类型 | 适合表达 | 实现 |
|---|---|---|
| pipeline | 方法与分析流程 | 条件分支、决策菱形、并行步骤、反馈 |
| architecture | 系统与方法架构 | 一层分组、组件、数据流和职责边界 |
| experiment | 实验设计 | 样本、分配、对照／实验条件、共同测量与分析 |
| mechanism | 机制假设 | 关联、因果、抑制，以及显式假设／reported 状态 |
| graphical-abstract | 图形摘要 | 问题—方法—评估的分组矢量叙事 |
| conceptual | 理论与研究框架 | 概念、可观测指标及假设关系 |
| response | 审稿解释图 | 原意见—修改—复核—实际回复的关系 |

图形摘要模板是结构化矢量示意图。精细生物／解剖插画、照片级图像、任意嵌套泳道或特殊图标需要额外的专业编辑与验证，不能从这些模板推断已实现。示例只有计划或示意，不包含真实实验结果。

支持 2–40 个节点、1–80 条连线、最多 8 个单层分组，横排／竖排与同层对齐。过密图需要拆分；不靠缩成不可读的小字通过检查。提供 `editorial`、`paper`、`mono` 三种原创建议风格，配有矢量小图标、短标签、分组标题和留白。它们不代表任何期刊的官方风格认证。

## 科研含义和视觉编码

流程、数据流、关联、因果、抑制、反馈分别记录。关联线没有方向箭头，抑制使用终端横杠；假设使用虚线，并在关系旁注明 hypothesis。已报告的科学关系必须绑定本项目仍有效的已核验证据和相关 Claim；因果／抑制不能由相关性 Claim 直接升级。示意流程的实线只表示流程，不能当成已证实机制。

图的输入材料、视觉效果、目的和设计理由沿用 Idea Evaluation 的规划问题。源代码只检查结构、来源关联和完整性；科研解释、对照公平性和是否适用于实际论文仍需复核。

## 输出与后续修改

每个新版本同时生成：

- **SVG / PDF / PNG**：用于预览和论文排版。SVG 保留文字和矢量元素。
- **`.drawio` / DOT / layout.json**：可编辑的形状、连线与布局来源。
- **spec.json / reproduce.py / caption.md / alt-text.txt**：冻结说明、独立完整渲染器、图注和替代文字。

渲染图位于 `manuscript/figures/FIG-...-版本/`；可编辑源和复现材料位于 `workspace/results/diagrams/FIG-...-版本/`。登记记录在 `workspace/history/diagrams/`。文件系统中不会覆盖旧图，也不把源材料自动传到 Overleaf。

`.drawio` 可交给本机 diagrams.net／相关编辑器继续修改；需要安装的工具另行授权。XML 中形状和连接均可编辑，编辑器自身重排后的线条可能与 SVG 有差异。手工改动 drawio 不会自动反写 spec.json，agent 需要核对含义、更新图源并生成新的检查记录。

原规格、图片、可编辑文件、复现脚本或关联研究节点被改动后，原记录会显示过期。新增 Figure 提案始终从 draft 开始；正式机器审查会检查 diagram_record，未核对实际图形和含义的 draft 不能直接放行。探索图可以先生成，但无 Claim／Evidence 时保持 unlinked。

## Agent 内部执行

下面内容只供 agent／开发者使用。用户不用输入代码。

核心框架继续零第三方运行依赖。渲染需本机 Graphviz 的 `dot`；可选 `diagrams` extra 包含 CairoSVG 与 fontTools，用于 PDF/PNG 与字形核查。安装在专用虚拟环境；系统 Graphviz 和支持中文的字体由宿主检查并在获得授权后准备。仅生成 SVG 时可使用 `--svg-only`。缺少依赖会明确报错，不伪造输出。

```bash
python -m research_workspace.diagrams template pipeline
python -m research_workspace.diagrams --project PAPER render workspace/figures/diagram.json
python -m research_workspace.diagrams --project PAPER render workspace/figures/diagram.json --approve --actor ai:diagram
python -m research_workspace.diagrams --project PAPER check workspace/history/diagrams/DGR-ID.json
python -m research_workspace.diagrams --project PAPER propose workspace/history/diagrams/DGR-ID.json --actor ai:diagram
```

template 只打印示意规格；未加 approve 的 render 只预览研究关联与字段，不执行布局。agent 负责填入真实路径与内容。可在独立输出目录运行保存的 reproduce.py。保持 spec 中的节点 ID，按用户意图修改标签、分组、方向或关系，不插入任意 DOT 属性、SVG、外部 URL、可执行内容或在线素材。

本地图片检查需要看实际 PDF/PNG，不能只看代码。输出指定毫米宽度并保留纵横比；主标签过小时会拒绝生成。fontconfig/fontTools 可用时会检查所选字体的字形覆盖；其他环境须明确执行目视检查。中文示例实际使用本机已安装的 Noto Sans CJK SC，仓库与示例包均不分发字体文件。

## 旧项目升级

用户说“更新 Workspace，启用科研示意图，保留原稿和我改过的设置”即可。agent 使用原增量更新器。新增研究示意图 Skill 和空白 brief 都在既有受管路径范围内；稿件、既有图、已填写 brief 和本地定制保留，冲突按原机制处理。无需重新初始化论文，Schema 保持 1。

## 实现依据与验收边界

Graphviz 负责布局，生成的 SVG 经过受限组合；CairoSVG 负责输出；drawio 使用未压缩 mxGraph XML。实现独立编写，没有从第三方 Skill 整包安装脚本。

依据：[Graphviz 布局属性](https://graphviz.org/doc/info/attrs.html)、[SVG 输出](https://graphviz.org/docs/outputs/svg/)、[draw.io XML 格式](https://www.drawio.com/docs/manual/export/export-to-xml/)、[Nature 图形制作指南](https://research-figure-guide.nature.com/)。指南用于设计取舍，实际期刊规范仍需要查当前适用版本。

本轮执行范围与记录见 [交付报告](../DELIVERY.md)。图形编辑器 GUI、真实 Codex／Claude 会话和期刊最终合规需要各自验收；本地渲染测试不能替代这些环节。
