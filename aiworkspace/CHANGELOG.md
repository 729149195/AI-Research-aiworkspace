# Changelog

## 0.2.0 — Auto-route / 2026-09-24

- Add the tenth built-in Skill, auto-route, as the default paper-session entry.
- Capture actual manuscript/file/node changes transactionally; retain bounded diffs, hashes, attributed unconfirmed notes, impact and persistent grouped specialist tasks.
- Preserve pending route tasks across review cycles; require issue/sync reconciliation before completing a record.
- Add optional explicitly authorized local Claude lifecycle hooks with settings preservation, isolated Python invocation and nonblocking Stop/failure handling.
- Preserve user research and local customizations through the existing Schema 1 incremental updater; bootstrap old observed baselines lazily.
- Add route/hook/upgrade regression tests and a reproducible synthetic walkthrough. Live host/model quality is not certified by these software tests.


## 0.1.0 — initial public workspace delivery, 2026-09-23

- Packaged the framework as a standalone repository with aiworkspace/, update_aiworkspace.py and README.md; unrelated application files and history are excluded.
- Added nine evidence-governed research Skills and the supplied PPT's faithful Markdown transcription plus editable worksheet.
- Implemented versioned research nodes, proposals, approval, source/evidence integrity, dependency impact, local execution provenance, bidirectional Markdown sync, independent review declarations and gated export.
- Added a root Git updater with target-SHA locking, current/legacy layout support, three-way asset merges, explicit conflicts, backups and recovery.
- Fixed generated Python artifacts from an old package path blocking subsequent updates while preserving visibility of real local edits.
- Added beginner documentation, English quickstart, behavioral evaluation scenarios, local verification records and packaging helpers.

See DELIVERY.md for actual test scope and limitations. Schema remains version 1; unsupported schemas fail closed.
