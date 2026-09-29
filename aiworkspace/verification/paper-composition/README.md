# 0.6.1 内容驱动的 VIS/HCI 图版：专项验证

本轮基于 06c6444c07bb0dbe8dada1b7285b0c73d3a0d4f3。研究 Schema 仍为 1，15 个 Skills、10 个菜单入口不变。修改研究示意图默认流程，新增 paper-composite 矢量图版路线，保留原节点图操作。

## 实际执行

**37 项专项测试通过，0 失败、0 错误、0 跳过。** 覆盖分图描述与 SVG 对应、安全矢量子集、物理尺寸与文字尺寸、只读预览、源码／产物／记录变化检测、原稿与旧版本保护、不伪造证据或研究批准、独立重绘进程，以及限定范围的旧／新资产升级、宿主副本与回滚。

两份原创人工数据示例实际生成 SVG/PDF/PNG；通过原 diagrams 操作注册记录，并用冻结 artwork.svg 和完整 reproduce.py 在独立子进程中重新生成。同一环境下 PNG 字节一致。两份最终 PDF 已渲染查看，已修正透明背景、文字遮挡和第三状态缺少联动结果的问题。数据表、刷选集合和分组计数在测试中核对。阅读来源原图与原创示例分别处理，没有将参考论文图版复制入仓库。

另外用 0.6.0 已发布示例包里的七个 graph spec 经本轮修改后的 diagrams 入口实际生成旧路线输出，检查了记录和 drawio 产物，以确认新增路线没有替换原路线。这个有限的兼容演练不代表重跑了全部旧测试。

核心 model、Store、workflow、upgrade、原 diagram_render 从已有分发材料恢复，并与当前仓库 Git blob SHA 核对后用于测试；没有以行为 stub 替代它们。具体机器时间、依赖范围和源码 SHA 见 [tests.json](tests.json)。机器记录使用 UTC；文档按本次会话日期 2026-09-30 标注。

## 范围边界

没有重跑全部历史科研／出版测试，没有构建并安装完整新 wheel，没有执行完整 Codex/Claude 模型会话、专业 SVG 编辑器 GUI、真实 Overleaf 登录或云端 CI 验收。当前测试验证软件路径、文件保护和示例一致性，不能证明“任何论文图都美观”、科学有效性、真实系统已实现或期刊合规。

当前 SVG 子集不嵌入真实位图截图，也不支持任意第三方 SVG 的 CSS、transform 和资源引用。方法细节、截图真实状态、自由绘制箭头的研究意义、颜色和图注都需要实际审核。示例属于熟悉交互的解释性人工例子，无创新或用户实验结果主张。

## 复测入口

在已安装当前源码的本地环境中，agent／开发者可以执行 `python -m unittest discover -s aiworkspace/tests -p test_paper_composition.py -v`。执行 `python aiworkspace/scripts/smoke_paper_composition.py --destination 新目录` 会生成两份人工示例及机器记录。普通用户无需输入命令，仍向自己的 agent 描述研究与图形任务。
