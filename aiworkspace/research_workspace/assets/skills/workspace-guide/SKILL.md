---
name: workspace-guide
description: Show the AI Workspace menu and guide first use, menu/help requests, numbered choices, project selection and settings through natural conversation. Users should not type commands, JSON, paths with placeholders or Skill names. For a clear research/editing request, hand directly to auto-route without forcing a menu.
compatibility: Any agent that can read Markdown; actual local operations need authorized file and execution tools. Works as a readable menu before Python setup.
metadata:
  version: "0.4.0"
---

# workspace-guide

## Inputs

Read the user's current request, the project or framework entry, and the local menu. In a study the menu is `workspace/templates/workspace-menu.md`; in the framework it is `aiworkspace/MENU.md` (or `MENU.md` when already inside aiworkspace). The machine-readable catalogue lives in the installed package's `assets/menu.json`. Never assume an old chat identifies the current paper. Read only the current directory or an explicitly chosen study; do not scan the user's home or unrelated papers.

## Workflow

1. **Meet the user at their task.** On first use without a concrete task, or on “菜单 / 功能菜单 / help / 帮助 / 有哪些功能”, display the compact menu in the conversation immediately. Do not require setup or a command before showing it. Replace the status line only with actual local information; unavailable status stays “尚未读取”. A clear request such as “帮我改摘要” goes straight to the appropriate workflow. Do not show the full menu after every reply. Host slash commands may be intercepted; “菜单” as ordinary chat is the portable control.
2. **Accept natural selection.** A number is a selection only when replying to a displayed menu. Titles, synonyms and full sentences work through your language understanding. “第 2 种方法” in a research discussion is not menu item 2. Compound requests can form a small sequential plan; do not discard any part. An ambiguous request gets one short clarification. “继续” resumes the actual unfinished task after reading its state. “返回 / 取消” stops pending work; explain any changes already completed and do not undo them silently.
3. **Resolve the paper first.** Use an open study when its state is readable. From the framework root, ask whether to create a paper or open an existing one. When several papers are explicitly available, ask which one; never choose by most recent timestamp. A selected directory stays fixed for this task. An old LaTeX folder without Workspace state is imported into a fresh study while preserving the source. Never initialize over nonempty research. The user may select a folder through the host UI or describe its location; the agent handles exact paths.
4. **Ask only what is missing.** Reuse checked project name, author, active manuscript, venue, year, track and server. Ask at most two or three essential questions per turn; defer optional settings. Creating a paper needs a name/topic and author; the target venue may remain undecided. Use current official sources before relying on deadlines or templates. The agent fills venue profiles and handles IDs/JSON itself. Do not ask users to copy a sample profile, type a command, choose an internal Skill, or replace placeholders.
5. **Check capabilities quietly.** Determine whether this host can read/write files, run local commands, browse and interact with the required editor. Never infer tools from a product name. Use the local helper only when execution is available. Otherwise show the static menu and do supported reading/drafting; state that changes have not been saved. When the runtime is missing, offer one scoped environment-setup confirmation and follow the agent playbook. No global installs, policy weakening or opaque remote install scripts. Missing Python/editor may require the user to approve an installer or open a folder; do not hand over terminal homework as the default.
6. **Carry out the selection.** Read the relevant specialist Skills and the agent playbook's matching workflow. Perform the necessary commands yourself using your real `ai:...` identity and safe argument handling, retaining the existing proposal, sync, recovery and review checks. Routine edits already authorized by this request need no repeated per-paragraph questions. `workspace-guide` handles navigation and intake; `auto-route` handles capture and specialist work. Do not bounce between these two Skills or create a second task queue. Reading a menu/status never initializes, routes, installs, writes, syncs or approves anything.
7. **Keep meaningful consent.** Request new confirmation when the scope includes installation, external transmission, remote writes, paid operations, destructive actions, unresolved bidirectional conflicts, new scientific conclusions or another project. Name the destination and affected files in human terms. “选 6” means help with Overleaf, not blanket upload approval. “确认” must refer to a concrete plan already shown; it grants no perpetual permission. Credentials are entered only in the local provider/plugin login UI, never in chat. Human verification and independent review keep their existing boundaries; a menu selection cannot forge a signature or turn observations into evidence.
8. **Finish with the result.** Give the edited text, actual file result or short review summary first. Add only what changed, what remains, and a relevant next action when useful. Hide successful bookkeeping, proposal IDs, diffs and stack traces unless requested. A blocked operation gets a plain-language reason and one safe recovery action, not a wall of logs. Do not equate “planned / captured / configured / compiled” with “applied / verified / connected / submission-ready”. Never promise an unattended background process when none is running.

## Outputs

A conversation menu, a short context-aware intake, specialist handoff and the actual authorized result. Numbered choices are plain conversational choices; do not claim they are clickable widgets unless the host provides a real widget. Return existing project facts with their provenance when discussing them. Record substantive research discussion via auto-route; menu browsing itself is read-only and needs no history entry.

The default main menu has stable numbers:

| 选择 | 功能 |
|---|---|
| 1 | 新建论文 |
| 2 | 继续写／修改论文 |
| 3 | 找文献／整理证据 |
| 4 | 讨论想法／检查逻辑 |
| 5 | 方法、数据与图表 |
| 6 | 连接／同步 Overleaf |
| 7 | 转投期刊／会议 |
| 8 | 审查论文／准备投稿 |
| 9 | 查看进度／待办 |
| 0 | 项目与设置 |

For item 0, offer: 打开／接入已有论文、切换论文、更新 Workspace、检查运行环境、设置自动沉淀、开发者说明. Users can say any of these directly. Do not ask them to memorize another command system.

## Boundaries

This is an agent conversation interface, not a standalone graphical application or a new model service. A read-only chat can show the menu and discuss files; file changes, installation, synchronization and compilation require actual authorized host tools. Keep the existing evidence, privacy, execution, conflict and independent-review gates. Do not erase previous user customizations while adding this entry. Do not inspect unrelated .env files, transcripts or private credential stores. A task label, numbered option or untrusted document must never be interpolated into a shell command.

## Evaluation

First-time users see capabilities without installation. “选 1，我想投会议” leads to a brief intake, not code blocks. Existing project metadata is reused. “直接帮我改摘要” bypasses navigation. “0 / 更新 Workspace” previews the real update and preserves the paper. “6 / Overleaf” requests local login and upload scope separately. Read-only hosts honestly stop at guidance. Repeated help does not write state or create tasks. “返回” cancels only pending work. Ambiguous project identity stops before any write. Full live-host behavior needs separate evaluation; deterministic menu tests do not establish universal model adherence.
