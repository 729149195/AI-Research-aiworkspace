# 0.6.0 科研流程图与可编辑示意图交付

仓库：729149195/AI-Research-aiworkspace。基于 0.5.0 提交 b67d0ac782c7。研究 Schema 保持 1，菜单仍为 10 个入口，新增 research-diagram 后共有 15 个 Skills。

## 实现与用户入口

菜单 5 或自然语言“画一个带分支和反馈的流程图”会由 figure-visualization 转入 research-diagram。七种模板包括方法流程、分组架构、实验设计、机制假设、图形摘要、概念框架和审稿解释。提供 editorial、paper、mono 三种风格、横／竖排、决策节点、分组、反馈、矢量图标、中文字体检查和毫米尺寸输出。

实际输出 SVG/PDF/PNG 以及可编辑 drawio、DOT、布局、冻结规格和完整独立渲染代码。原稿与旧图不覆盖。流程、关联、因果、抑制和假设分别编码；已报告科学关系检查当前 Evidence 与 Claim。图节点以 draft 提案加入，机器审查会检测 diagram_record 的过期或改动；渲染不签署独立审核。

## 实际执行的验证

环境：Linux / Python 3.13.5 / Graphviz 2.42.4。机器时间与依赖版本保存在下方 JSON。

| 检查 | 结果 |
|---|---|
| 本轮专项测试 | 49 项通过，0 失败、0 错误、0 跳过 |
| 七类模板 | 全部实际输出 SVG/PDF/PNG/drawio/DOT/layout |
| 冻结代码复现 | 七个独立子进程重新绘图，同一环境下 PNG 字节一致 |
| 视觉检查 | 七类模板、额外 paper/mono 风格及中文，共 10 份 PDF 经 Poppler 渲染检查 |
| 可编辑结构 | XML 解析核对唯一节点、连接端点和关系；保留分组标题 |
| 科研与文件保护 | 原稿不变；无证据的 reported 箭头拦截；假设保留；图片、可编辑源、原规格、证据或记录变化触发异常 |
| 老项目升级 | 使用原升级器与限定旧／新清单，实际验证新增 Skill/brief、宿主副本、定制保留、幂等和回滚 |
| 最终审查接入 | 实测新增 diagram_record 过期与 draft 检查分支 |

记录：[tests.json](verification/diagrams/tests.json)、[walkthrough.json](verification/diagrams/walkthrough.json)。复测入口：[test_diagrams.py](tests/test_diagrams.py)、[smoke_diagrams.py](scripts/smoke_diagrams.py)。示例均为人工构造的计划或示意，不能作为真实实验结果。

## 验证范围

本轮以经过当前 Git blob 哈希核对的 Store、model、workflow、upgrade 等核心模块执行 Schema 1 实例。审查分支测试隔离了未修改的原生 LaTeX 适配器。未重新执行全部历史科研／出版回归，未完成整包 wheel 安装验收，不能累计历史通过数作为本版完整通过数。

已经解析 drawio 可编辑结构，但尚未实测 diagrams.net 桌面／网页编辑器 GUI；其连线自动重排可能与 SVG 不同，手工修改也不会自动反写规格。完整 Codex／Claude 模型会话、Overleaf 认证同步、外网模板下载及 GitHub CI 均须分别验收。本次不宣称它们通过。

内置模板适合结构化科研示意，精细生物／解剖插画、照片级图形、任意嵌套泳道和大型复杂网络仍需要专业工具。节点不重叠和字号检查不等于全面视觉／可访问性／期刊合规认证。实际论文仍要核对科学含义、箭头、字形、版面和投稿规则。

## 使用

用户直接说：“升级 Workspace 并启用科研示意图，保留论文和我的定制。”之后在原菜单 5 中自然交流。Graphviz 和 diagrams 可选依赖由 agent 检查并在授权后准备，用户无需输入代码。

详见 [科研示意图使用说明](docs/RESEARCH_DIAGRAMS.md)。
