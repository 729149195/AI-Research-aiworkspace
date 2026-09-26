# 0.3.0 交付与实际验收

仓库：729149195/AI-Research-aiworkspace。验证日期 2026-09-26；Linux / Python 3.13.5；研究 Schema 1。

## 实现

新增 venue-setup、overleaf-sync、venue-transfer，内置 Skills 共 13 个。包括当前官方来源发现与整份模板 ZIP 归档、相对路径 LaTeX 项目、13 类投稿规则主题和有时区的候选日期、版本刷新、原生 LaTeX 研究节点绑定及三方同步、自建网址和插件／Git 两条同步通道、转投新版本和编译校验。更新沿用三方默认资产升级，不覆盖已写稿件或 venue 模板。

## 已实际运行

| 验证 | 结果 | 记录 |
|---|---|---|
| 完整回归 | 181 项，0 失败、0 错误、0 跳过；60 项新增出版相关用例 | [tests.json](verification/publication/tests.json) |
| 干净 wheel 安装 | 新虚拟环境安装 0.3.0，从源码目录外运行 doctor，13 个 Skill 契约通过 | [installed-doctor.json](verification/publication/installed-doctor.json) |
| 研究演示 | 实际合成分析、证据链、双向同步与演示质量门 | [installed-demo.json](verification/publication/installed-demo.json) |
| LaTeX 迁移与实际编译 | article、acmart、IEEEtran、llncs、elsarticle 五种已安装文档类的合成迁移样例编译成功，引用和交叉引用解析；保留原稿字节 | [walkthrough.json](verification/publication/walkthrough.json) |
| 更新／回滚 | 当前目录与旧目录两种布局实际 Git fetch、安装、冲突／回滚保护通过，研究哈希不变 | [root-update.json](verification/publication/root-update.json) |
| 文档／分发 | 21 项受管资产、18 个行为场景定义、相对链接与无 PPT 检查 | [docs.json](verification/publication/docs.json) |

Git 同步测试包含真实临时 bare repository 的 fetch／commit／push，以及带故障注入的双向合并、冲突、删除确认、推送结果不明恢复和新编辑保护。模板测试使用实际 ZIP 字节／文件系统和记录式 HTTPS transport，测试 HTML 登录页、错误引用原文、未知年份、时间与时区、归档越界等；没有把离线提取称为实时下载。

实际编译中发现并修复 ACM 重复数学宏包冲突，迁移草稿避免默认示例 DOI／ISBN。五份 PDF 已渲染，人工查看了 ACM 和 IEEEtran 样例；样例并非完整真实长论文的视觉验收。额外回归核对图像字节、图引用、表格文字、公式与 BibTeX 保留。

## 尚未验收的外部环节

没有用户自建 Overleaf 的登录凭据，未执行该站的认证登录／真实双向同步／完整 VS Code Replica 会话。默认网址和配置已实现，凭据通过用户本机插件或 token 提示输入，不在聊天收集。

交付运行环境未完成公开模板站点的实际下载；HTTPS 访问与下载接口通过隔离 transport 测试，浏览工具核查了官方界面／来源。实际模板 ZIP 可通过 --online 或用户合法取得的 --archive 导入。因本机缺少 vgtc 类包，该适配未做 vgtc 编译。其他五类的实际编译来自已安装 TeX 类包和合成文稿，不代表已经验证每个期刊当届模板和投稿合规。

18 个模型行为场景保持 not_run；没有真实模型效果、专家审稿或科学正确性保证。GitHub CI 需查看当前提交的 Actions，不能由本地通过推断云端通过。

## 复测

```bash
python aiworkspace/scripts/run_tests.py
python aiworkspace/scripts/check_docs.py
python aiworkspace/scripts/smoke_root_update.py
python aiworkspace/scripts/smoke_publication.py --destination ../new-publication-smoke
```

完整新操作见 [模板与规则](docs/PUBLICATION.md)、[Overleaf](docs/OVERLEAF.md)、[转投](docs/RESUBMISSION.md)。
