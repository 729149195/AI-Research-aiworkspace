---
name: figure-visualization
description: Design, generate and audit research figures from actual data or explicitly labelled schematics. Use for paper charts, figure improvement, diagrams, graphical abstracts, reviewer requests or changed data. Users give scientific goals; the agent handles tools and previews.
compatibility: AI Workspace 0.6.0+. Numerical studio uses optional Matplotlib; research-diagram uses Graphviz and optional diagrams extra. Local execution requires permission.
metadata:
  version: "0.6.0"
---

# Scientific figure studio

## Inputs

Read the actual question, Figure purpose, bounded Claim, source/result IDs, intended venue/phase and current data. Reuse author-approved writing preferences and terminology. Retain Idea Evaluation's data, expected visual effect, purpose, encoding, analytical task, design rationale and alternative-design questions. Ask only for genuinely missing units, independent/paired structure or scientific intent; users do not fill plotting JSON.

## Workflow

1. Write a short internal brief: question → Claim → source material → encoding → legitimate interpretation → limitations. Distinguish measured evidence, exploratory plots, process diagrams and hypothetical mechanisms. Never design around a desired significant result.
2. **For non-numerical diagrams, delegate to research-diagram immediately.** Branching flowcharts, architectures, experiments, conceptual/mechanism models, graphical abstracts and review explanations use its dedicated renderer, source formats and scientific arrow semantics. Do not ask for a CSV or squeeze these tasks into the old 2–6 step workflow recipe. The basic workflow remains for backwards compatibility.
3. For data charts, inspect the authorized CSV with studio inspect-data: headers, units, sample/replicate IDs, orientation, missing and censored values. Convert other tables only with an actual available tool and retain originals and transformation records. Matching column lengths do not establish pairing.
4. Choose the quantitative recipe by task: scatter, line, distribution with all points, paired trajectories, interval with stated definition, or heatmap with visible missing cells. Use the local studio implementation and optional Matplotlib. The agent fills the spec, previews, and renders after local authorization. Missing dependencies prompt one scoped virtual-environment setup request; no global installation, mandatory paid image provider or terminal homework.
5. Default missing policy is error. Omission requires a reason and row inventory; missing line y remains a gap. Unknown x, duplicate x-per-series, duplicate pair IDs, matrix collisions, nonfinite values and reversed bounds require correction. No hidden smoothing, filtering, outlier removal, significance labels, invented intervals, interpolation or fabricated experimental images. State interval type, estimator, n and replication unit in the caption.
6. Reuse actual venue dimensions and typography. Export SVG with text, PDF and PNG, retaining physical dimensions; use redundant marker/line cues. Numerical Matplotlib defaults and diagram palettes are provisional, not accessibility or publisher certification. Dense networks, biological illustration, arbitrary nested layouts and complex multi-panel comparisons need an explicitly reviewed specialist tool.
7. Open the actual PNG and exported PDF at final size. Inspect axes, units, labels, arrows, pair identity, missingness, captions, glyphs, clipping, overlap and colour-independent interpretation. Fix failed layouts; no automatic check covers all visual or scientific errors. Hosts without image inspection must leave visual review pending.
8. Preserve versioned outputs and the full reproduction bundle. Numerical figures keep frozen inputs, recipe and renderer under workspace/results/figures; diagrams use workspace/results/diagrams with editable drawio/DOT. Original data and scripts stay outside the manuscript upload subtree. Checks validate input/output/source and linked-node hashes. Only a draft Figure proposal is produced; unlinked exploration never becomes supported evidence automatically.
9. Reconcile the reviewed figure with text through normal proposal/sync operations, then auto-route affected sections and references. Input, editable source or research changes require rechecking and usually a new figure version. Show the preview and relevant limitations first; routine bookkeeping stays quiet.

## Outputs

Actual SVG/PDF/PNG, complete caption and alt text, frozen local sources, independent regeneration code, execution provenance and a reviewable Figure node. Diagrams additionally retain editable shape/connector and layout sources. Scientific interpretation, visual review and final independent approval remain distinct states.

## Boundaries

The numerical studio retains seven bounded recipes including its legacy sequential workflow. Advanced structured diagrams use research-diagram. Byte identity across different software/fonts is not promised. External downloads, installation, data transmission and execution preserve scoped permissions. No scientific image fabrication, credential access, self-verification or compliance claims based solely on export format/DPI.

## Evaluation

Retain each real pair and missing-time gap. Reject duplicate headers, reversed intervals and unexplained omissions. Changed data or output makes the receipt stale. A source-free schematic stays labelled and unlinked. Re-run saved code; inspect output files. A request for a branching pipeline delegates to research-diagram, preserving hypotheses and relations rather than creating a decorative numerical chart.

## References

See docs/RESEARCH_STUDIO.md for the existing chart implementation and docs/RESEARCH_DIAGRAMS.md for diagram formats, examples, dependencies and limits. Consult current official renderer documentation and the target venue's actual rules. The local implementations are original code; external Skill scripts are not automatically installed.
