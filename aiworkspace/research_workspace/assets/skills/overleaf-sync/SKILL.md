---
name: overleaf-sync
description: Handle natural-language requests to connect, sync, compile, inspect or repair a self-hosted Overleaf paper using the built-in Overleaf CE transport (zero third-party editor plugin required) or an existing Overleaf-Workshop / Git Bridge binding. Require observed results before saying connected.
compatibility: An authorized local file-capable agent. Built-in Overleaf CE mode (`mode=ce`) needs `websocket-client` inside the framework venv; optional Workshop mode needs VS Code/Cursor plus `iamhyc.overleaf-workshop`.
metadata:
  version: "0.6.2-ce-builtin.1"
---

# overleaf-sync

## Inputs

Read the actual user request, current selected paper, non-secret connection metadata (`.rw/overleaf.json`), main-file identity and pending edits. Prefer the explicit project link and existing binding over defaults. Default suggested server is https://nankaivisoverleaf.asia/. A project URL is not a credential or authorization to overwrite a paper. Read docs/OVERLEAF_AGENT.md for internal operations; docs/OVERLEAF.md is the user-facing conversational guide.

## Workflow

1. **Accept the task, not a configuration form.** “Connect this paper and check sync” is sufficient to start. Parse the usual HTTPS project URL; infer server and project ID. Reuse the current root and real existing binding. Only ask for a missing project, genuinely ambiguous main file, a conflicting target or necessary permission. The agent handles every command, JSON, exact path and returned ID. Never hand those to the user as required setup steps.
2. **Choose the right transport honestly.**
   - **Built-in Overleaf CE mode (`mode=ce`, default for new self-hosted CE connections; zero editor/plugin dependency):** Uses `aiworkspace`'s own HTTPS + Socket.IO 0.9 / OT client (`overleaf_ce.py`). Supports authentication (storing only the session cookie in `.rw/overleaf/ce-session.json` with 0600 permissions, never raw passwords), full pull/push with three-way merge and conflict stop, real-time OT document updates, binary uploads, remote compilation (`output.pdf`/`output.log` into `.rw/builds/`), and live connectivity verification (`read` or `roundtrip`). Requires `websocket-client` inside the isolated framework `.venv`.
   - **Overleaf-Workshop mode (`mode=workshop`):** Compatibility path only when the user explicitly retains or requests editor-managed Local Replica. Preserve existing working bindings and pending changes; never install Workshop for a new CE connection by default.
   - **Git Bridge mode (`mode=git`):** Only when the Overleaf server exposes Server Pro Git Bridge (`/git/<project_id>`). Never silently fall back across modes without confirmation.
3. **Set up and protect credentials and manuscripts.** Follow docs/OVERLEAF_AGENT.md section 0: prepare the isolated runtime, authenticate locally, list accessible projects or preview/approve remote blank project creation with `overleaf create`, configure an existing manuscript subdirectory, and preview then apply synchronization. First pull into an empty subdirectory when possible; never reinitialize an existing study or flatten an original to satisfy an older semantic-binding interface. By default sync runs per invocation. Foreground `watch` requires explicit scoped approval and stops with the process/conflict. Never write passwords, cookies, or tokens into `manuscript/`, `workspace/`, Git history, or command arguments. For CAPTCHA/SSO servers, never attempt to bypass CAPTCHA; let the user supply a session cookie via process environment (`RW_OVERLEAF_COOKIE`) or log in via Workshop. Synchronize only the explicitly selected `manuscript/<subdir>` subtree—never upload `workspace/`, history, or `.rw/`. Preserve original filenames, subdirectories, figures, and `\input` structure; pause on conflicts and block deletions unless explicitly approved.
4. **Perform real acceptance checks.** Saved configuration or a login cookie alone does not establish live sync. Run `rw overleaf verify --online` (read-only live Socket.IO `joinProject` + `joinDoc` hash check) or, with scoped approval, `rw overleaf verify --online --roundtrip --approve` (disposable 1×1 PNG upload, read-back, overwrite, remote deletion cleanup, and unchanged local manuscript hashes). The CE probe verifies a binary upload/read-back/update/cleanup with unchanged local manuscript hashes; it does not independently establish collaborator text propagation to disk or long-term reliability. After a successful file sync, observe actual authorized text edits separately and remotely compile when requested. Never copy files manually to fake sync or hand-edit verification flags.
5. **Handle partial results honestly.** Distinguish awaiting_login, readable_via_ce / readable_via_plugin, roundtrip_verified, blocked, and stale/historical. Timeouts, expired sessions, conflicts, wrong projects, or incomplete cleanup stay unresolved. Preserve local edits and remote files; report exact phase and next recovery action.
6. **Continue naturally.** Report actual target, check time, tested scope, and any remaining issue in ordinary language. After authorized sync, run `auto-route` so changes to prose, claims, evidence, and figures are captured cleanly.

## Outputs

Actual built-in CE or Workshop synchronization results, time-scoped read or roundtrip verification records, optional remote compile PDF/log under `.rw/builds/`, preserved local manuscript, and concise next steps.

## Boundaries

No password persistence, no CAPTCHA bypass, no webpage computer-use scraping, no silent transport switching, no blind deletion, no whole-workspace upload, no force-push, no fake live checks or forged human approval.

## Evaluation

A plain project link leads to concise intake and agent operations, never terminal homework. Built-in CE mode operates independently of Cursor/VS Code. Wrong-host/ID bindings block writes. Read-only mode never reports verified writes. Conflicts pause and preserve both sides. On success show time and tested scope; on failure preserve work and give one clear recovery action.
