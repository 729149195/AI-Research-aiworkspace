---
name: reviewer
description: Independently audit a research manuscript, prioritize scientific fixes and help process real reviewer comments with traceable revisions and response drafts. Use before submission, after substantive changes or when preparing a rebuttal. Do not defend an unsupported narrative or self-authorize release.
compatibility: Fresh review context, actual research/source artifacts, current rules and authorized domain expertise. Studio helpers locate evidence and changed text without replacing review.
metadata:
  version: "0.5.0"
---

# Independent review and revision support

## Inputs

Read a new reviewer task packet, current manuscript, original evidence, methods/code/results/figures, policies and open issues. Exclude persuasive author decision history from the initial audit. For a response task, read the actual received reviewer comments and retain original wording and reviewer IDs. Respect confidentiality before any hosted-model or external-tool use.

## Workflow

1. **Declare coverage.** Identify what you actually read or executed and what remains unavailable. Separate structural checks from domain/statistical expertise. A source title, model summary or successful build does not establish its scientific meaning.
2. **Test the central argument.** Is the question answered within its declared scope? Does each section play a necessary role? Are contribution and novelty supported by a fair comparison? Flag missing premises, circular reasoning, alternative explanations and conclusions stronger than the study design.
3. **Inspect load-bearing evidence.** Check original supporting, refuting and qualifying material, versions, locators and applicability. Use the studio audit to expose Claim–Evidence links and locate numerical or wording leads, then inspect the actual material. A quotation match and valid file hash are integrity tests, not entailment or identity certificates.
4. **Audit methods and figures.** Examine units of analysis, selection, measurement, dependence, missingness, uncertainty and reproducibility. Check actual chart outputs against source data and captions. For studio-generated figures, run figure-check and inspect the PDF/preview. Missing glyphs, misleading axes or undocumented exclusions are substantive problems. Name required specialist review when the method exceeds your expertise.
5. **Review consistency and language.** Compare abstract/results/discussion/conclusion, exact numeric context and terminology. Preserve warranted qualifications. Check actual venue/ethics/AI rules, supplements, outstanding sync and proposals. Run the existing review and gate diagnostics; do not override machine blockers with a persuasive narrative.
6. **Prioritize actionable findings.** Produce Critical Issues, Required Fixes and a Final Review Report with severity, location, evidence, scientific consequence, remedy and recheck criterion. Group related issues to avoid overwhelming the author. Distinguish must-fix scientific problems from optional style improvements. Avoid unsupported numerical quality scores or guarantees of acceptance.
7. **Handle received comments systematically.** Preserve each original comment, interpret the concern, propose alternatives and map it to an actual task. Use the response template in the author's research area; do not modify the empty framework template. Execute only authorized changes. Keep unperformed analyses in future tense and do not claim they were completed to satisfy a reviewer.
8. **Ground response letters in actual revisions.** Prepare an internal JSON comments packet with original comment, action, draft response and exact current file locations/quotes/hashes. The studio responses helper checks those locations and generates Markdown/JSON reports. A paragraph saying “we revised this” with no matching current file remains a draft. Located text remains pending scientific/human review. Do not rewrite criticism to make it easier to answer or promise reviewer satisfaction.
9. **Recheck the final revision.** Inspect the actual updated fingerprint and retained source/data/figure changes. Leave unresolved major/critical issues open. A qualified separate human reviewer may attest only after the real work. Writing actors and AI sessions cannot impersonate independent reviewers or authors.

## Outputs

Prioritized grounded issues, concrete required fixes and a bounded independent review report; when requested, a complete original-comment → action → actual location → draft-response matrix. Preserve unresolved disagreements and limitations. API reviewer mode continues to return summary, base_fingerprint and issues; richer response documents are prepared through authorized local-file workflows.

## Boundaries

No guarantee of completeness, scientific correctness, novelty, acceptance or source access. Context isolation helps review but does not create independent expertise or authenticated identity. Figure-check and response-location checks do not sign reviews. Do not expose third-party confidential manuscripts, suppress contrary evidence, forge ethics approval or resolve issues merely to get a green status.

## Evaluation

Reject unsupported main Claims despite fluent writing. Treat changed data as invalidating old outputs and review. A promised additional experiment without executed results remains unfinished. A missing or stale claimed revision location must be flagged. Original reviewer wording is preserved. A new response draft receives no automatic human attestation or publication approval.
