# 转投迁移：保留原稿，生成目标模板新版本

自然指令：

> 把当前论文转到指定的期刊／会议、届次、稿件类型和阶段。先取得官方模板与最新规范，保留全文、公式、图表和引用，比较规范差异，在新目录迁移。不要覆盖旧稿或自动推到旧 Overleaf 项目；无法自动处理的部分明确列出。

auto-route 将其分派到 venue-transfer，复用 venue-setup 的检索与初始化。目标 venue 必须先安装，流程见 [模板与规则](PUBLICATION.md)。同一出版商的模板也可能有不同 review/camera-ready、匿名、单／双栏和长度要求。

## 执行步骤

在论文项目根目录运行，实际路径和 id 由 `rw venue list` 给出：

```bash
rw venue transfer --source manuscript/latex/旧稿目录 --source-main main.tex --target 目标venue-id
rw venue transfer --source manuscript/latex/旧稿目录 --source-main main.tex --target 目标venue-id --approve --actor ai:transfer
```

预览检查源文件、目标文档类和需人工适配的内容；批准生成全新的 `manuscript/latex/<target>-transfer-<id>/`。源目录保持逐字节不变。报告保存在 `workspace/history/transfers/`，包含原主文件／导言区、前后文件哈希、引用键／标签／交叉引用／图引用清单及必做检查。

当前内置基础适配针对 article、acmart、IEEEtran、llncs、elsarticle、vgtc。五类前述常用格式已用本机安装的类包实际编译合成样例；vgtc 因本机缺少类包未做对应编译。它们提供可审查的目标草稿，任意出版社自定义宏、动态 TeX 或复杂历史模板需要追加适配与真实编译，不能自动认定完全合规。

迁移保留正文语义、可平衡的宏定义、公式、BibTeX、图／数据文件和标签。检查引用键存在及清单一致性；同路径不同内容的资产碰撞会停止。复杂布局包、作者信息、特殊环境不会无依据硬套。原导言区完整保留给后续核对；转换器会标记未移植部分。自定义环境、Biber/biblatex、复杂 package option 或动态 input 可能需要手动处理。

作者／机构信息使用待核查或匿名占位，不能编造。匿名审核还需检查致谢、自引措辞、图像及 PDF 元数据、补充材料。ACM 迁移草稿关闭默认示例 DOI／ISBN／出版引用块；终稿阶段只能按真实权利信息补齐。框架不凭模板默认值生成出版事实。

## 先检查，再切换活跃稿件

```bash
rw latex build --directory manuscript/latex/新迁移目录 --main main.tex --allow-exec
# 打开输出 PDF，核对全文、图表、跨页、参考文献、字号与留白；修改后再次编译。
rw latex adopt --directory manuscript/latex/新迁移目录 --main main.tex
rw latex adopt --directory manuscript/latex/新迁移目录 --main main.tex --approve --actor ai:transfer
rw route --actor ai:session
rw sync status
rw review
```

相对 TeX 输入从稿件编译根目录解析。超出稿件目录的依赖须先整理为自足项目；不能把整个 Workspace 加到 TeX 搜索或云端上传路径。adopt 建立目标稿件新的章节绑定，旧稿与原研究节点历史保留，相关 Claim 依赖须由 Logic/Sync 复核，不自动把 draft 升级为研究结论。

迁移报告的必做项包括目标届次／稿件类型／阶段、全部作者与匿名处理、篇幅、宏包兼容、实际编译、引用／交叉引用、科学内容复核。页数、词数、图数变化可以自动定位并提出改写建议；删除内容、改变结论或缩减实验范围需作者决定。编译成功只能说明当前构建成立，仍需规则与视觉核验。

## Overleaf 接续

迁移不会自动绑定新目录，也不会把新格式推送到旧投稿项目。为新稿创建独立远端项目，完成模板检查和保密授权后打包上传，或重新配置 Git Bridge。原稿的远端链接保持不动。详见 [Overleaf 配置](OVERLEAF.md)。

目录创建与状态登记之间出现故障时，保留新目录和原稿，检查返回错误及 state/index/history；部分新目录可能尚未注册。使用新版本 id 重试或人工恢复，禁止自动删除已有稿件目录来“修复”。增量框架升级也不会把新模板覆盖到已写论文上。
