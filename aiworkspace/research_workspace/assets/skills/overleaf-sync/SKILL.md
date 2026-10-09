---
name: overleaf-sync
description: Handle natural-language requests to connect, reuse, inspect or repair a self-hosted Overleaf paper using the real Overleaf-Workshop editor extension. The agent performs technical setup and scoped connectivity checks; users do not type commands or configuration. Require observed results before saying connected.
compatibility: An authorized local file-capable agent plus an actual editor/Workshop session. The optional local verification assistant needs VS Code 1.85+; no universal headless plugin setup API is assumed.
metadata:
  version: "0.6.1-onboarding.1"
---

# overleaf-sync

## Inputs

Read the actual user request, current selected paper, non-secret connection/Replica metadata, main-file identity and pending edits. Prefer the explicit project link and existing server/login over defaults. Default suggested server is https://nankaivisoverleaf.asia/. A project URL is not a credential or authorization to overwrite a paper. Read docs/OVERLEAF_AGENT.md for internal operations; docs/OVERLEAF.md is the user-facing conversational guide.

## Workflow

1. **Accept the task, not a configuration form.** “Connect this paper and check sync” is sufficient to start. Parse the usual HTTPS project URL; infer server and project ID. Reuse the current root and real existing binding. Only ask for a missing project, genuinely ambiguous main file, a conflicting target or necessary permission. The agent handles every command, JSON, exact path and returned ID. Never hand those to the user as required setup steps.
2. **Check actual capabilities.** Detect the editor and installed iamhyc.overleaf-workshop version through the real host interface. Reuse an available working installation; ask before installing/changing a version or the local optional verifier. Do not silently pin/downgrade to 0.15.10. A shell alone does not grant editor control, and a cloud agent cannot reach the user's local plugin. Keep unavailable operations pending with one concrete explanation.
3. **Use Workshop exclusively for the requested connection.** Invoke its real server/project/Replica entry points using available editor tools. Some upstream commands open native input boxes or need actual tree objects; do not invent a headless API or fabricate a project item. Fill non-secret values when supported; otherwise guide the minimal native prompt. Users log in locally. Do not read a private plugin/browser credential store or request password, token or cookie in chat. No computer-use webpage download, authenticated ZIP HTTP downloader, Git Bridge fallback or second sync engine.
4. **Preserve the manuscript.** Use the intended manuscript root when that layout is actually supported. Keep an existing bound path until an explicitly reviewed migration. Check version-specific Replica path rules before creating folders; never overwrite an existing nonempty paper. Preserve original file names, bytes and input/include organization during setup. Do not run a flattening/marker-inserting adoption operation merely to claim the connection is ready. Metadata must be produced by the real extension and must match the chosen host/project.
5. **Perform real acceptance checks.** First read the actual project/main through Workshop and compare with local. Cached document reads, a successful installer, saved config, localhost status, or .overleaf/settings.json alone do not establish live sync. With scoped approval, use a host-provided measured checker or the repository's one-shot Overleaf assistant: observe local-to-remote propagation, a remote-side change returning locally, successful cleanup and unchanged original files. See the runbook for the binary probe's limited scope. Never copy data on both sides yourself and count that as synchronization. Never set a verified flag by hand.
6. **Handle partial results honestly.** Distinguish awaiting_plugin, awaiting_login, awaiting_replica, readable_via_plugin, roundtrip_verified, blocked and stale/historical. Read-only consent cannot yield write approval. Timeouts, wrong projects, concurrent edits, expired login, incomplete cleanup or unavailable editor tools stay unresolved. Preserve partial test files and user edits, explain the exact phase, and repair only within the approved scope. Do not keep trying indefinitely or replace a failed transport with webpage automation.
7. **Continue naturally.** Show actual target, check time, tested scope and any remaining issue in ordinary language. A successful one-shot file check is not a guarantee of all text/OT operations or continuous connectivity. During authorized real writing, check actual save/sync results; auto-route preserves research meaning, related evidence, figures and pending work. Do not capture private plugin metadata as research evidence. Closing the editor stops editor-owned activity.

## Outputs

Actual configuration/Replica results produced via Workshop, time-scoped read or roundtrip observations, preserved local manuscript and concise next steps. The optional verifier stores request/report files in .rw/overleaf-agent on the currently released layout; it does not create another research workspace. Technical details are for the agent, while the user sees progress and meaningful permissions.

## Boundaries

No secret collection, no webpage/computer-use download, no invented plugin API, no automatic Git fallback, no blind deletion, no whole-workspace upload, no force-push, no fake live checks or forged human approval. Existing legacy Git code is compatibility support, not a fallback to this user request. The current repository's broader single-workspace migration and live server authentication remain separately verifiable tasks.

## Evaluation

A plain project link leads to concise intake and agent operations, never terminal homework. Existing metadata is reused and an already-installed working plugin is retained. Wrong-host/ID metadata blocks writes. Read-only mode remains unverified for writes. No upload, download or cleanup observation means no success. A generated request or mocked plugin test cannot be presented as a real user connection. On success show time and tested scope; on failure preserve work and give one necessary recovery action.
