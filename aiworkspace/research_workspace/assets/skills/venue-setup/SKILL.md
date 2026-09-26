---
name: venue-setup
description: Discover the current official venue and Overleaf/publisher LaTeX template, initialize a source-bound local project and preserve yearly submission requirements. Trigger on starting a journal/conference paper, selecting a venue/track or refreshing submission rules.
compatibility: Research Workspace 0.3.0 and an authorized file-capable host; explicit network and execution permissions.
metadata:
  version: "0.3.0"
---

# venue-setup

## Inputs

Read project rules, the user's venue name, edition year, actual submission year, article/track and review/camera-ready stage. Resolve ambiguous track/stage with the user only when official sources cannot resolve it. Current date matters: an edition's submission can fall in a prior year. Never infer a future deadline from an old edition.

## Workflow

1. Use the authorized host's web search to find the current official venue/track page, author instructions, publisher policy and any linked Overleaf gallery. Open primary sources. Search snippets and gallery labels alone cannot establish the right template. Preserve any official disagreements instead of silently choosing a date.
2. Run `rw venue discover --name "VENUE" --year YEAR --track "TRACK" --official-url "OFFICIAL_URL" --online`. This records retrieved pages and candidate links. Its CLI has a small dated seed list, not a universal web search engine; for other venues provide actual official URLs found by the host.
3. Follow the venue's template link and verify review versus final format, article type, class version, anonymization and license. Overleaf galleries may require browser login to download a complete ZIP. Use authorized Download Source, or the exact official publisher/repository ZIP of the same template. Never guess gallery-to-project IDs, bypass login or pretend an HTML page is a ZIP.
4. Build a profile JSON from inspected sources. Required fields: profile_version=1, unique id, name, edition year, submission_year if known, track, stage, sources with id/role/url, and template with the exact ZIP url, main, overleaf_url if available, license_note, explicit class_options and bibliography_style for transfer. Declare redirect hosts individually. See the example profile and publication guide.
5. Capture all submission topics: scope/track, format/length, anonymity, deadlines/timezones, submission portal, supplementary/artifacts, ethics/consent, AI use, originality/resubmission, copyright/license, fees/registration, review/camera-ready, references/accessibility. Requirements and exact deadlines need a matching quote/source. Missing topics remain unknown. A quote matches bytes; applicability remains a research judgment.
6. Use `rw venue init --profile PROFILE.json --online --approve --actor ai:venue-setup` only within actual user authorization. A local ZIP and reviewed UTF-8 extracts can be supplied with --archive and --sources-dir. The entire accepted template source is copied to a new relative manuscript directory; original ZIP/provenance and versioned rules live under Workspace. No template example authors/results become research facts.
7. Inspect the local main file and remove or replace sample content only through the user's authorized writing task. Run `rw latex adopt --directory RETURNED_DIRECTORY --main MAIN --approve --actor ai:venue-setup` to bind LaTeX sections to canonical research nodes. Compile only after permission; inspect the resulting PDF, citations and template settings. New imported sections remain draft.
8. On a policy refresh, run `rw venue refresh ID --online` before applying. Changed original pages create a new rules revision; old structured entries whose quotes vanished are invalidated. Preserve earlier versions, route global rule changes and never silently keep a stale deadline. Run auto-route after meaningful edits.

## Outputs

A real downloaded local template, immutable original/provenance, native LaTeX binding, current retrieved rule dossier and tentative calendar only for exact timezone-aware deadlines. Report gaps, source conflicts, old deadlines and inability to access a full template explicitly. The host performs web reasoning; the deterministic CLI validates and persists its results.

## Boundaries

No credentials in profiles, no remote code execution, no template sample facts or fake approvals. TeX compilation is explicitly authorized and is not a security sandbox. Do not overwrite a used manuscript, silently choose the wrong TVCG article type, or assert complete compliance from keyword coverage. Unknowns remain review issues.

## Evaluation

A stale year or camera-ready-only gallery must not become an unchecked review template. HTML pretending to be ZIP, path traversal and ambiguous mains must fail. Refresh must retain changed policies and invalidate vanished quotes. Old research remains unchanged on framework upgrade.
