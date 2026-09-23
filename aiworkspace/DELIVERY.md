# 0.2.0 Auto-route 交付与验收

发布目标：[729149195/AI-Research-aiworkspace](https://github.com/729149195/AI-Research-aiworkspace)。版本 0.2.0，研究 Schema 仍为 1。验证日期：2026-09-24（Asia/Singapore）；机器记录时间为 UTC。

## 已完成

新增第 10 个 Skill auto-route，设为自然改稿和研究讨论的默认入口。实现本地差异捕获、节点含义前后记录、跨章节影响分析、未确认讨论笔记、按 Skill 合并的持久待办，以及经过问题/同步检查的完成操作。捕获本身不修改稿件或科研节点，不签署核验与独立审核。

AGENTS.md、CLAUDE.md、START_HERE.md 和受管资产清单已更新。可选 Claude 生命周期 Hook 需单独授权；配置合并保留已有设置，Stop 不循环触发新回复。现有论文通过原增量更新入口接入，研究数据无需 Schema 迁移。

## 实际本地验收

环境：Linux / Python 3.13.5。软件执行与真实模型/宿主效果分别记录。

| 检查 | 实际结果 | 记录 |
|---|---|---|
| 单元与回归测试 | 121 项通过，0 失败、0 错误、0 跳过；含 44 项新增路由、Hook、升级测试 | [tests.json](verification/auto-route/tests.json) |
| 干净 wheel 安装与自动沉淀调用链 | 全新虚拟环境安装 0.2.0；实际执行隔离 Python Hook 进程、改稿捕获、重复静默、显式同步、任务收尾及 Stop | [walkthrough.json](verification/auto-route/walkthrough.json) |
| 真实 0.1.0 → 0.2.0 本地升级 | 从旧分发包创建已用论文；实际 Git fetch、快进和安装；稿件、研究、用户规则及本地 Skill 定制哈希不变；新 Skill 进入已注册宿主 | [old-to-new-upgrade.json](verification/auto-route/old-to-new-upgrade.json) |
| 当前/旧目录更新与回滚 | 两种布局的 Git 更新、冲突、回滚保护通过 | [root-update.json](verification/auto-route/root-update.json) |
| 文档/分发检查 | 本地链接、18 项受管资产及 15 个行为场景定义检查 | [docs.json](verification/auto-route/docs.json) |

合成示例实际计算 12 组人工数据，均值 22.5 和 18.0，配对均差 -4.5。示例中的作者与审核声明明确标注为模拟。它们不能用于真实研究或投稿。历史 0.1.0 报告保留在 verification/ 根目录，仅描述历史版本。

## 尚未验证与边界

未运行完整 Claude/Codex/Windows 宿主会话或真实付费模型效果评测；15 个 Skill 行为场景保持 not_run。本地 Hook 输入和真实命令链测试不能替代完整宿主验证。论文语义检查由宿主调用 Skills 执行，CLI 不会自行调用模型、自动开展研究或替人签字。

没有常驻文件监听进程；宿主关闭时的编辑在下一次捕获发现。原生正文同步仍为带稳定章节标记的 Markdown，Word/LaTeX/Overleaf 无损往返尚未实现。GitHub CI 以对应提交的 Actions 为准，不能由本地测试推断为通过。

## 复测

在框架仓库根目录、专用虚拟环境安装当前版本后：

```bash
python aiworkspace/scripts/run_tests.py
python aiworkspace/scripts/check_docs.py
python aiworkspace/scripts/smoke_root_update.py
python aiworkspace/scripts/smoke_auto_route.py
```

使用方式、首次 Hook 授权、冲突处理和旧论文升级见 [AUTO_ROUTE](docs/AUTO_ROUTE.md)。
