# Auto-route：自然改稿，持续沉淀

在有文件权限的 AI 宿主中打开论文根目录，让它先读 AGENTS.md 和 START_HERE.md。auto-route 在研究或论文请求前后默认触发，平时无需用户选择 Skill、手改状态 JSON 或重复提醒“记进 Workspace”。

## 一轮工作

开始时 `rw route --actor ai:session`，恢复会话时 `rw route status`；根据实际请求调用相关 Skill，按用户授权编辑，结束前再次捕获。程序记录观察到的 Diff、文件和节点哈希、共享 Claim 影响、带说话人的简短上下文，以及按 Skill 合并的持久待办。它不把观察自动提升为已核验事实。

例如“导师把导致改成相关”：捕获段落变化，分派 Sync、Logic、Evidence、Writing、Figure 和 Reviewer，检查摘要、讨论、结论、图注及共享论点。冲突或科学选择保留给责任人确认。同步后的文本相同不能证明推断成立。

0.3.0 增加 venue-setup、overleaf-sync、venue-transfer。用户说期刊初始化、配置自建 Overleaf、转投时自动分派这三项；已显式 adopt 的原生 LaTeX 进入同一条捕获／同步链，未绑定的附件改动仍保存为观察。

## 保存位置与状态

- `workspace/sync/auto-route.json`：上次观察到的文件／节点／稿件快照。
- `workspace/history/auto-route/CHANGE-*.json`：不覆盖旧记录的差异、影响、备注和待办关联。
- `workspace/state.json`：规范研究节点、问题和持久待办。

相同状态重复扫描不增加事件。多次修改保留各次记录，同一 Skill 未完成任务合并，跨会话和 review cycle 不丢弃。初始化旧项目只使用当前文件与已有同步基线，不能恢复此前未保存的编辑历史。二进制保留哈希引用，不整份塞入 Memory。捕获记录自身不再次触发，实际研究文件和问题变化仍使旧审核过期。

讨论只保存必要且授权的归纳：

```bash
rw route --actor ai:session --note "作者提出比较两种编码，尚未选择。" --note-kind decision-candidate
rw route --actor ai:session --note "作者偏好该术语，适用范围尚待核对。" --note-kind preference
```

默认 note-kind 是 discussion，全部保留为 unconfirmed-context。确认后的规则、选择和证据分别通过对应 Skill 的正式流程登记，不能把候选偏好直接写成官方规则，也不批量复制聊天或读取 transcript。

## 可选 Claude Hooks

```bash
rw route install-hooks
rw route install-hooks --approve
```

预览自己的固定命令，批准后合并 `.claude/settings.local.json`，保留已有权限、其他 Hook 和设置，备份在 `.rw/auto-route-hooks.json`。用当前 Python 的绝对路径和 `-I` 隔离方式执行本地捕获，不调用模型、联网或读取聊天记录。重启宿主并确认生效。

支持 SessionStart、UserPromptSubmit、PostToolUse（Write/Edit/MultiEdit/Bash）、Stop、PreCompact。无变化的 PostToolUse 静默；Stop 只落盘，不阻止停止或循环启动回复。失败显示短提示，改动保留为未处理，不能宣称维护已完成。宿主关闭期间不会运行 Hook，下次捕获再发现外部编辑。

```bash
rw route remove-hooks
rw route remove-hooks --approve
```

只移除本程序记录的处理器。Python 虚拟环境迁移后重新预览和安装；不要复制失效绝对路径。普通网页聊天没有本地监听能力。

## 完成和恢复

```bash
rw route --check
rw route status
rw route complete CHANGE-ID --actor ai:session --note "具体说明已经处理的关联改动、同步、问题修复与实际复核。"
```

完成命令核对原记录哈希、关联问题、最新捕获和同步状态；只有实际复核完成才关闭相应任务。捕获、提出、应用、核验、审核分别记录，AI 不冒充 --human，不能自签独立审核。写入使用项目锁和事务恢复；确认没有其他写入者后，按错误提示运行 `rw recover`，不要擅自清理锁或丢弃用户编辑。

框架更新继续使用根目录 update_aiworkspace.py。0.3.0 保持 Schema 1，已填写研究、稿件、用户规则和已下载 venue 模板保留。[更新](UPDATING.md)、[出版流程](PUBLICATION.md)、[Overleaf](OVERLEAF.md)、[转投](RESUBMISSION.md) 提供完整命令。
