# 从这里开始 / Start here

这是论文项目，框架程序在另一个 Git checkout。`workspace/` 保存研究状态和证据，`manuscript/` 保存正式表达。需要 Python 3.11+ 和已安装的 rw；框架首页有 Windows／macOS／Linux 安装命令。

## 第一次

执行 `rw status`、`rw sync status`、`rw review`。新项目 blocked 正常。填写 `workspace/research/idea-evaluation.md`；实际导师、机构、期刊、伦理、AI、引用与术语规则写到 `workspace/rules/project-policy.md`。不要把研究写进可更新的 `workspace/templates/` 空表。

使用有文件能力的 AI 宿主时让它读 AGENTS.md，并以 auto-route 默认接手。安装宿主 Skills：`rw skills install --target .agents/skills`，Claude 使用 `.claude/skills`。以后正常提出改稿、文献、方法或导师反馈，宿主负责捕获和维护；论文科学判断、外部传输和冲突按实际授权确认。可选 Claude Hooks 先 `rw route install-hooks` 预览，再加 `--approve` 并重启验证。

## 期刊／会议与 LaTeX

直接告诉 AI 目标 venue、届次、稿件类型和投稿阶段，调用 venue-setup 找官方 Overleaf／出版社模板，保留完整 ZIP 和年度规则。工作副本在 `manuscript/latex/`，规则在 `workspace/rules/venues/`，不猜截止时分或时区。

已有模板可用 `rw latex adopt --directory manuscript/latex/实际目录 --main main.tex` 预览，核对后加 `--approve --actor ai:session` 绑定原生 LaTeX。此后 rw sync 与 auto-route 使用活跃 .tex。构建 `rw latex build --allow-exec` 需要本地 TeX，禁用 shell escape 仍需可信源码。模板内示例事实不属于本文。

Overleaf 默认自建网址 https://nankaivisoverleaf.asia/，由 overleaf-sync 引导本机插件登录或原生 Git token。不要给 AI 密码／cookie，不要把整个研究目录上传。转投由 venue-transfer 创建新版本并保留旧稿；旧远端绑定不会自动换成新格式。完整说明在框架 docs/PUBLICATION.md、OVERLEAF.md、RESUBMISSION.md。

## 日常循环

研究 → 原始证据 → 逻辑／方法 → 写作／图表 → 同步 → 独立复审 → 下一轮。`rw route` 捕获，`rw route status` 查看待办，`rw sync propose --actor ai:sync` 提出同步。提案先 show，再按授权 apply；双向冲突不能静默选边，含义变化须复核证据与所有受影响章节。

`rw packet SKILL --task "具体任务"` 生成任务包；只交给获得授权的模型。`rw review` 保存报告，`rw dashboard` 生成离线看板。捕获、提出、应用、核验、审核分别记录；模型不能替人签署 --human 或把建议当事实。

## 更新与交接

结束前捕获真实改动，保存简短且必要的交接说明，保留未完成任务。框架根目录用 `python update_aiworkspace.py --project 论文路径 --check` 预览，再按需要 --apply。保留 .rw/framework.json；查看备份 `rw upgrade history`，资产回滚 `rw upgrade rollback UPDATE-ID`。更新不覆盖稿件、数据、已写工作表、用户规则或已下载 venue 模板。

真实论文需要原文核验、独立领域审查和作者责任声明，示例和机器检查不代表科研有效性或投稿合规。
