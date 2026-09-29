---
name: research-diagram
description: Create and revise readable, editable research diagrams: branching pipelines, grouped system architectures, experimental designs, conceptual/mechanism models, graphical abstracts and reviewer explanations. Use when the user asks for a flowchart, framework, pipeline, mechanism, diagram or graphical abstract, including natural-language revisions. Keep relation semantics and evidence distinct from visual styling.
compatibility: Research Workspace 0.6.0; local authorized host. Graphviz dot for layout; optional diagrams extra for PDF/PNG and glyph checks. No network or model account needed for the renderer.
metadata:
  version: "0.6.0"
---

# research-diagram

## Inputs

Read the chosen paper's entry and project rules, current manuscript/Claims, figure brief and the user's request. Use menu 5 and auto-route; no extra menu or user-written JSON. Determine what the figure must explain, to whom, and at what final physical size. Reuse known language, fonts and venue constraints. A diagram is not a numerical result unless its represented results and relations actually have evidence.

## Workflow

1. **Form a short visual brief.** State the question the image answers, intended takeaway, required components, relation meanings and planned/implemented/mixed/illustrative status. Keep source data, intended visual effect and purpose separate, as in Idea Evaluation. Ask only for missing scientific choices. Do not ask users to choose Graphviz attributes or enter code.
2. **Choose a storyboard, not a wall of boxes.** Use pipeline for branches, decisions and feedback; architecture for grouped responsibilities/interfaces; experiment for conditions, assignment and measurements; mechanism for explicitly hypothetical or source-bound relations; graphical-abstract for problem, approach and evaluation; conceptual for constructs and measures; response for a review explanation. Start from the corresponding template and replace all example content. No invented results, sample counts or author decisions.
3. **Budget the information.** Prefer a few meaningful stages and short action/object labels. Group by scientific role, preserve the logic and do not add arrows merely for symmetry. Use a decision diamond only for a real decision; label branch outcomes. Split a dense graph rather than shrinking unreadable text. The bounded renderer accepts 2–40 nodes, 1–80 edges, one-level groups and optional same-rank constraints; it is not a complete biological illustration system.
4. **Encode scientific meaning explicitly.** Specify flow/data/association/causal/inhibition/feedback independently of certainty. Association has no directed arrow; inhibition has a terminal bar; hypotheses use dashed links with visible labels. Source-bound reported edges require evidence IDs supporting linked Claims; causal relationships require suitable causal Claims and actual scientific review. A planned method can have solid schematic flow arrows without claiming a proven mechanism. Do not turn a hypothesis solid to make a figure look more convincing.
5. **Apply a restrained style without another questionnaire.** Default to editorial for clear coloured modules; paper for a restrained technical figure; mono for grayscale. Reuse confirmed project preferences. These are original style presets, not official Nature/IEEE templates or a compliance certificate. Use colour redundantly with labels, shape, line style and small original vector icons. Respect the actual intended width and installed fonts; select a CJK-capable font for Chinese. Do not distribute font files.
6. **Render locally after scoped permission.** The agent writes the validated spec under workspace/figures/, previews via diagrams, then renders a new version. Graphviz performs layout; CairoSVG exports PDF/PNG; SVG keeps text and vectors. Inspect the actual PDF/PNG at the final width for clipping, glyphs, crossings, ambiguous arrows and excessive whitespace. Revise the same intended science, render a new version, and do not promise a universal aesthetic score. Missing dependencies require a single scoped installation request, never a global install or hidden paid service.
7. **Deliver editable and reproducible work.** Return SVG/PDF/PNG with diagram.drawio, DOT, layout JSON, frozen spec, the full independent renderer, caption and alt text. Editable sources and provenance stay in workspace/results/diagrams; only rendered images go under manuscript/figures. drawio editing may reroute edges and is not automatically parsed back to the spec. If it changes, reconcile the scientific meaning, update the source and regenerate/check; do not call old receipts current.
8. **Integrate with research.** Use diagram check, then a draft Figure proposal when real Claims/evidence are linked. Unlinked exploration stays unlinked. Review the caption, update affected text through the usual proposal/sync flow, and let auto-route retain the actual modifications. Reported evidence becoming stale, modified editable sources, or changed images invalidates the receipt. The final reviewer checks this record and actual visual output; the agent cannot sign independent human approval.

## Outputs

A diagram answering the agreed research question, editable sources, complete local reproduction bundle, versioned provenance and explicit review gaps. Offer the finished preview first and ask only one meaningful decision where needed. User requests such as “把这两个模块分组，补一个反馈箭头，改成黑白” should result in a scoped revised version with unchanged unsupported scientific claims.

## Boundaries

No invented effect sizes, mechanisms, significance, original data or evidence. No automatic uploads to diagrams.net, Overleaf or image-generation services. No arbitrary SVG/HTML, external assets, URLs or unreviewed code in the graph spec. Biological/anatomical drawings, compound multilevel swimlanes, arbitrary custom icons and dense network visualization may require an explicitly chosen specialist editor or authorized image tool; describe and verify that separate work. Graphical abstracts here are structured vector storyboards, not photorealistic experiment images. Data charts remain with figure-visualization/studio.

## Evaluation

A natural-language request selects the workflow without terminal homework. Branches and feedback are editable; grouped modules keep their labels; Chinese glyphs render with an available font. Hypotheses remain dashed, associations undirected, and unsupported reported causality is blocked. XML-like labels remain escaped text. A new diagram never overwrites an older one. Reproduction preserves semantic node/edge inventories. Changed spec, source, output or linked evidence is detected. Old-project upgrades add this Skill while preserving actual research and local customizations.
