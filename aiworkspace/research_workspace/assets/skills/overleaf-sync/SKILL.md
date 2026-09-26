---
name: overleaf-sync
description: Configure authorized self-hosted Overleaf and synchronize only the chosen LaTeX manuscript. Trigger when a user asks for Overleaf login, custom server, remote collaboration, local replica, sync conflict or switching remote project.
compatibility: Research Workspace 0.3.0 and an authorized file-capable host; explicit network and execution permissions.
metadata:
  version: "0.3.0"
---

# overleaf-sync

## Inputs

Read current native LaTeX binding, actual host URL and project ID, server Git capability, privacy/upload scope, and current pending sync state. Default server suggestion is https://nankaivisoverleaf.asia/. The framework does not hold the user's login. Never request secrets in chat or inspect browser/session databases.

## Workflow

1. Prefer the community Overleaf Workshop extension for interactive self-hosted local-replica editing when supported by the actual deployment. Explain that it is a third-party extension, distinct from the server's optional native Git Bridge. Check the current upstream interface before changing integration contracts.
2. `rw overleaf configure --server URL --project-id ID --directory manuscript/PAPER --mode workshop --approve` writes a local non-secret configuration and a step-by-step guide. `rw overleaf install-plugin` previews the exact extension command; --approve installs it only when authorized. Installation is not login or proof of live connectivity.
3. Have the user sign in through the extension's Add New Server and login UI. Email/password login or the documented cookie method for SSO/CAPTCHA belongs in that UI only. For Git Bridge use the Overleaf account's Git token with username git, via an OS-backed Git credential helper or process-local RW_OVERLEAF_TOKEN. Never embed it in a URL, argument, repository or rule file.
4. Package only the selected manuscript using `rw latex pack --output NEW.zip`. A Workspace, raw research data, history, credentials and previous submissions are not a remote upload scope. Only include data explicitly intended for this manuscript. Create/select the remote project via its ordinary UI.
5. For Workshop, Open Project Locally into a NEW empty parent: the extension may overwrite an existing replica path. Keep independent versioned backups. For an already marked, byte-identical paper run `rw overleaf bind-replica --directory manuscript/replicas/NAME --approve`; otherwise reconcile differences before rebinding. Keep the editor open; report the documented local-replica stability caveat. Do not run two sync engines on the same folder.
6. Use native mode git only when this server exposes a Git endpoint. `rw overleaf sync --online` previews a bounded three-way comparison. Explicit --approve applies it; --resolve path=local|remote chooses a conflict; deletion needs --allow-deletions. The Git adapter detects the branch, never force-pushes, and preserves remote entries outside the selected source-file scope.
7. For near-real-time Git sync use the explicitly started foreground `rw overleaf watch --online --approve --interval 5`. This is polling, not character-level collaboration. Conflicts stop it. No daemon is silently installed. A failed push outcome is uncertain; use overleaf recover only after fetching and confirming intended bytes, preserving intervening local edits.
8. After remote pulls, capture changes with auto-route and reconcile native LaTeX sections, Claims and evidence. A transfer to another template requires explicit remote rebinding so the old venue project is not overwritten. Surface only actual conflicts or required user decisions in routine editing.

## Outputs

A non-secret per-study configuration, exact plugin setup guide, manuscript-only ZIP, source-scoped sync previews/receipts, preserved conflict records and downstream research tasks. State precisely which transport, server and authentication were actually tested.

## Boundaries

No credential collection in chat, no force-push, no blind deletes, no whole-Workspace upload, no claim that Server Pro Git Bridge exists on Community Edition. Workshop UI and the actual self-hosted login require a real authenticated session. Local fake/temporary Git tests do not prove production synchronization.

## Evaluation

Custom server URLs work without invented settings keys. Password URLs, wrong-host Git endpoints, escaping paths and two-sided changes are rejected. Unknown remote push outcomes remain recoverable. Workspace secrets/history stay outside uploaded files. A new active template blocks sending it to an old remote binding.
