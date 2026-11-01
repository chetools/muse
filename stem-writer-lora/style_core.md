---
name: local-stem-writing-style
description: Apply the measured writing patterns of highly cited Nature and Science papers and of Anthropic, OpenAI, Google, and DeepMind instructional writing when drafting or revising STEM prose (papers, reports, pages, explanations, tutorials). Trigger when the user asks for writing in the style of the best STEM writers, or when revising scientific or instructional text for clarity, concision, accuracy, and readability.
---

# STEM writing style (pilot-derived working rules) — DRAFT revision, not installed

Draft state: prepared 2026-11-01 from the full-vs-slim paired test (`~/workspace/nature-science-pilot/slim-test/`). Installation requires a user decision; the installed skill remains the full version until that decision. Amendments to the tested slim core are marked [test amendment] at the rule amended.

Loading: this core is the drafting text. Three reference files sit beside the installed skill and are loaded only as named: `references/equations.md` for a document that carries displayed equations; `references/angell.md` when a device named in that file is in use; `references/provenance.md` for audit only, never for drafting. Each rule carries a tier label: [general] corpus-wide in the pilot sets; [conditional] applies to the named document type or move; [single-case] one recorded instance. Frequencies, batch evidence, and limits for every rule are in `references/provenance.md` and in the full skill under the rule number cited.

## Register constraints

Journal-formal, unemotional register. Explain, never persuade: no argumentative framing, no rhetorical connectives. Plain words. Brevity by cutting words and clauses, not qualifications, ranges, or evidence. Define every symbol before first use, with SI units where applicable.

## Sentences and paragraphs [general; full skill rules 1–5]

1. Open the sentence with the noun the sentence is about. A participle frame ("Using …") is a minority method-first opening. "We" is used sparingly.
2. Keep explicit connectives sparse and spend them on contrast; "However" is the default marked transition. Addition and sequence stay unmarked unless the relation would otherwise be missed.
3. Carry continuity inside a paragraph by repeating the term. One object keeps one name; no synonym cycling, no signpost chains. A new paragraph opens a new unit.
4. Vary phrase lengths within a sentence and sentence lengths within a paragraph. A paragraph mixes short and long sentences and closes on shorter sentences than it develops with. A results passage is not fragmented into single-datum sentences.
5. Put data values in parentheses inside the sentence rather than in a clause of their own.

## Structure [general; full skill rules 6–10]

6. Opening order: setting, established knowledge, gap, aim, method preview. The gap is stated as a missing piece of knowledge where that is the case.
7. Abstract order: setting, aim or approach, method, principal result (qualitative, then quantitative), interpretation, implication. No limitation is named in the abstract; limitations and scope conditions are named in the closing.
8. Interpretation stands next to the result it interprets. Results sentences carry a number by default.
9. Figures are referred to in the order the results need them. The caption is a noun phrase followed by conditions and sample size, and states the finding when the figure carries the claim.
10. The closing claim is held at or below the abstract claim. Strength is raised only where the closing combines evidence strands explicitly. [test amendment, from slim-test pair S5] The closing carries the principal claim at its tested scope, with the limitations named; a closing that states a limitation alone is used only where no scoped claim is available.

## Instructional text [conditional: tutorials and explainers; full skill rules 11–14]

11. A tutorial states its goal in its opening sentences and shows or describes the outcome near the start.
12. A worked example has three parts: inputs, result, and what the result shows or how it is checked.
13. Tutorials address the reader; explainers withhold direct address. Audience and prerequisites are stated where the item assumes them.
14. Checkpoints, expected outputs, and warnings stand at the point of risk. A code block is preceded by a purpose sentence and followed by a statement of the output.

## Claim, number, and definition patterns [general; full skill patterns 15–21]

15. The limit stands inside the claim sentence: a concession clause first and the bounded claim as the main clause, or the exception, condition, or scope statement in the same sentence as the claim, placed before the number it qualifies.
16. The number is bundled with its qualifier in the same sentence: denominator or cohort, interval, and named baseline or contrast, in parentheses where the syntax requires it. A denominator is fixed in the sentence that defines the quantity.
17. A null result is stated as a detection statement with its conditions: what was not detected, under what conditions, over what range, or against which reference. A null is not stated as an absence.
18. A term is defined in place, at its first dependent use: parenthetical or appositive definition, an operational definition attached to the first reported value, or a henceforth sentence that fixes a short name. A composite notation is defined symbol by symbol, in symbol order. [test amendment, from slim-test pair S3] A quantity named as a model output or as part of a result (a prediction and its uncertainty, a value and its spread) is a term under this rule and is defined at first use; a worked example is checked at completion for a named quantity that no sentence defines.
19. The caption fixes what the text leaves open: method, threshold, baseline, error-bar provenance, replication count, conditions, spread, or the computation that produced the plotted quantity.
20. A choice or a threshold is keyed to its condition in a condition-first sentence: the condition opens the sentence and the recommendation follows.
21. A confirmation sentence names the independent route: the second device, technique, phenomenon, or laboratory that makes the route independent.
22. [conditional: analogy in use] An analogy or simplification is followed, within one sentence or the next, by a statement of where it stops holding.

## What not to do [general; full skill, anti-pattern section]

1. Synonym cycling for the central object or quantity. A new name forces the reader to re-identify the object.
2. A number in a sentence of its own, with its baseline, denominator, or conditions in a separate sentence or later. A value separated from its comparison has no stated meaning at the point of reading.
3. Inferential connectives that tell the reader the conclusion ("therefore", "thus", a causal "so"). The result and its evidence are stated; the inference is the reader's.
4. Meta-signposts that announce the text's own moves. The interpretation, the example, or the limit is stated, not announced.
5. [test amendment, from slim-test pair S5] Restatement of a result in a further sentence that adds no scope, condition, or limit. A result is stated once; a restatement stands only where the added material changes the claim's scope or strength.

Caution: conditions, replication, and spread belong in the caption in full, and a trend sentence carries its values with it (full skill, application caution from case S4).
