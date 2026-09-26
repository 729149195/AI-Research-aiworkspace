---
name: venue-transfer
description: Move an existing LaTeX manuscript into a newly verified venue template while preserving content, citations and assets. Trigger when resubmitting, changing venue, switching publisher formats or generating a different submission version.
compatibility: Research Workspace 0.3.0 and an authorized file-capable host; explicit network and execution permissions.
metadata:
  version: "0.3.0"
---

# venue-transfer

## Inputs

Current manuscript directory/main, target venue edition/track/stage, source package dependencies and current rules. Read actual source files, target template provenance and user-authorized adaptation scope. Retain the original submission as a separate version.

## Workflow

1. Invoke venue-setup to find/download the current target template and rules. A generic publisher class is insufficient to establish the exact conference/journal's current requirements. Record submission-year versus edition-year and review anonymity.
2. Preview `rw venue transfer --source manuscript/SOURCE --source-main main.tex --target VENUE_ID`. The parser expands bounded literal input/include paths, detects cycles and rejects dynamic imports requiring a custom adapter. Preserve the original and compare all citation, label, reference and graphic inventories.
3. Review the transfer plan and then --approve within authorization. It creates a new target-version directory, retains source bibliography/figure/data bytes, and archives original front matter/preamble plus a mapping report under Workspace history. The active manuscript and remote binding do not switch automatically.
4. Check every recorded blocker: source-specific packages, custom environments, author metadata, target anonymity, class options, bibliography style, copyright/DOI/license, acknowledgments, image metadata, appendices and supplements. The standard wrapper supports article, acmart, IEEEtran, vgtc, llncs and elsarticle structurally; actual template variants require real compilation and inspection. Do not claim arbitrary TeX is automatically portable.
5. Preserve research text, math, tables, citations and graphics. Do not delete content merely to meet page limits. For shortening or restructuring, offer a concrete change plan and perform authorized edits, then recheck argument/evidence and all dependent sections. Missing bibliographic entries block migration; unusual class-specific commands require reviewed manual mapping.
6. Compile the new target with `rw latex build --directory NEW_DIRECTORY --main main.tex --allow-exec`, only after reviewing code and receiving execution permission. Inspect actual PDF, citations/references, page count, layout and original template requirements. A successful compile does not prove compliance or anonymity.
7. After the user chooses the migrated version, adopt it with native LaTeX, map new section roles to Claims, capture auto-route changes and rerun independent review. Keep previous template revisions. Reconfigure Overleaf to the intended remote project explicitly before synchronization.

## Outputs

New migrated draft, unchanged original, exact file/hash and citation/label/reference/graphic inventories, original metadata archive, required manual adaptation list, actual compile report and unresolved scientific/compliance review issues. Never label a transfer draft submission-ready without completing the original quality gate.

## Boundaries

No silent deletion of text, figures or citations; no old author/DOI/year carried as confirmed metadata; no whole-study overwrite. Dynamic or ambiguous TeX stops for a reviewed adapter. Local compilation needs a TeX installation and explicit permission. Do not upload a new venue draft to the old project without a new decision.

## Evaluation

Nested literal inputs and same-named assets must be preserved or rejected safely. Missing references, asset collisions and dynamic imports block. Source bytes remain unchanged. Class-specific metadata and page limits remain explicit review tasks even when a wrapper compiles.
