---
name: manuscript-sync
description: Reconcile Workspace and Manuscript after author, supervisor, collaborator or reviewer edits. Use for changed text, research records, rules or conflicting versions. Preserve semantic meaning and explicit three-way conflict resolution.
compatibility: Markdown or explicitly adopted native LaTeX section markers with rw sync (0.3.0+).
metadata:
  version: "0.3.0"
---

# manuscript-sync

## Inputs

Current workspace/state.json, manuscript/main.md, last synchronized section baselines, pending proposals, open issues and the reason for edits. Keep both directories as siblings. Use actual file hashes and stable section IDs rather than memory of the previous draft.

## Workflow

1. Run `rw sync status`. Inspect base, Workspace and Manuscript versions. The native adapter uses `<!-- rw:section SEC-ID -->` blocks. Missing/duplicate/mismatched markers require structural reconciliation, not guessed recovery.
2. Classify changes: only Workspace changed; only Manuscript changed; both changed; unmapped text changed. Identify research implications separately from copyediting.
3. For one-sided changes, create a synchronization proposal with `rw sync propose --actor sync-agent`. For conflicts, present both variants and their implications; require explicit `--resolve SEC-ID=workspace` or `=manuscript`, or manually merge before rechecking. No last-writer-wins behavior.
4. Inspect text outside section blocks. Only after real inspection use `--acknowledge-outside`; preserve the change and open a semantic-review issue. Identical independent edits to both sides also need their new baseline reviewed.
5. Every Manuscript-to-Workspace change must trigger semantic review. Check causality/association, scope/population, units/numbers, negation, comparator, terminology, uncertainty and citation changes. Do not assume the sentence alone captures its scientific implications.
6. Route meaningful changes to Logic and Evidence. Update canonical Claims and requirements, then all affected abstract/results/discussion/conclusion, figures/captions, supplementary material and related rules. Use the dependency graph and explicitly note undeclared relationships.
7. Present proposal operations, impact and unresolved conflicts. A real author reviews and applies the proposal. Run sync status and review again; convergence of text is a necessary structural check, not proof of scientific consistency.

## Outputs

Base/local/remote differences, explicit conflict choices, synchronization proposal, affected section/Figure/Claim list and semantic-review issues. Keep provenance for external edits and reasons. Never mint evidence verification or review approvals.

## Boundaries

Native Markdown and adopted UTF-8 LaTeX use explicit section markers and three-way synchronization. Separate the research-state sync from the configured Overleaf transport. Word Track Changes and arbitrary dynamic TeX are not supported. Do not remove section markers to hide conflicts, automatically discard reviewer edits, or mark semantic issues solved without actual evaluation.

## Evaluation

Changing “X causes Y” to “X is associated with Y” must open global scientific review. Divergent edits must pause rather than overwrite. An edit outside markers must remain visible. Synchronized paragraphs with an unchanged stronger Claim must not pass final semantic review.

## Native LaTeX publication flow

Use venue-setup to install the correct source template, then preview/approve rw latex adopt. Read the active project.latex directory instead of stale manuscript/main.md. Preserve percent-comment section IDs. Preamble, bibliography and asset changes require explicit outside acknowledgment and semantic review. Overleaf transport only moves selected manuscript files; after incoming edits run auto-route and native sync. Transfer to a new venue never silently changes remote bindings. Compile the actual selected source and inspect the resulting PDF before release.
