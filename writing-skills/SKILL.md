---
name: writing-style
description: Apply the measured writing patterns of highly cited Nature and Science papers, of Anthropic, OpenAI, Google, and DeepMind instructional writing, and of Harvard Business Review, MIT Sloan Management Review, McKinsey, Boston Consulting Group, and Bain documents when drafting or revising prose. The STEM sections govern by default; the business section governs business documents under its activation condition. Trigger when the user asks for scientific, instructional, business, or consulting writing, or for revision of such text for clarity, concision, accuracy, and readability.
---

# Writing style

This file is the core of a tiered package: this core plus condition-loaded reference files in `references/`. Evidence and provenance for every section are held in `references/evidence.md`, which is not loaded for writing. Rule numbers cite the core and its predecessor skills, which remain the documents of record for evidence, frequencies, and limits.

Use: this core governs all writing under the package. Reference files load only on their stated condition, and a loaded reference governs its stated scope: `references/business.md` under the business activation condition stated in that file; `references/equations.md` for a document with displayed equations, loaded jointly with `references/textbook.md` whenever a document or passage both carries a display and falls under the textbook gate, so a cross-reference between the two files always resolves inside the load; `references/textbook.md` for instructional or detailed explanatory, step-by-step phrases, sections, and sentences, under the activation stated in that file; `references/ai-check.md` at a revision or check pass. A reference that its condition does not call for is not loaded.

Frame-sentence clause: a closing or finding sentence that rests a claim or a decision on grounds stated before it is a frame sentence, and its inference is not marked with "thus", "therefore", "hence", "accordingly", or a causal "so".

## Register constraints

Journal-formal, unemotional register. Plain words. Each descriptive word is the most specific word that fits the observation: a change in a quantity is named by the word that matches what was observed (a reduction, where a procedure produced the change; a decrease, where a recorded value went down), not by a general or figurative word (a fall). Titles are short. Brevity by cutting words and clauses, not qualifications, ranges, or evidence. Define every symbol and every abbreviation before first use, with SI units where applicable. Definition is calibrated to the audience: STEM and textbook writing under this package addresses chemical engineers, and notation that a chemical engineer reads directly — element symbols (H, N, O), chemical formulae of common species (N2, NH3, H2O, CO2), and SI unit symbols — is used without definition; no clause states what such a symbol denotes, and no expansion stands at its first use. Headings are nominal and impersonal ("Computational Methods", not "How the numbers are computed"); no hype phrases or clickbait-style titles, no conversational fragments as headings, no anthropomorphizing, no second-person asides outside the instructional forms in rules 11–14. In STEM and instructional writing: explain, never persuade, with no argumentative framing and no rhetorical connectives. In business documents the persuasion switch in the business section governs in place of the preceding sentence. No fact, consequence, or causal link is stated that the source material for the document does not state; a derived figure is stated as derived, with its derivation.

## Sentences and paragraphs [shared]

1. Open the sentence with the noun the sentence is about. A participle frame ("Using …") is a minority method-first opening. "We" is used sparingly.
2. Keep explicit connectives sparse and spend them on contrast; "However" is the default marked transition. Addition and sequence stay unmarked unless the relation would otherwise be missed.
3. Carry continuity inside a paragraph by repeating the term. One object keeps one name; no synonym cycling, no signpost chains. A sentence that must stand on its own (a validity statement, a closing, the first sentence of a section or a paragraph) restates the object's name rather than carrying the object with a bare category noun: "Fick's law holds for a stagnant medium", not "The law holds for a stagnant medium"; the bare noun leaves the reader to re-identify the object. Where possible, "The" before a generic noun is replaced by a brief descriptive noun, a technical noun above all ("Fick's law" for "the law", the Antoine equation for "the equation" where the equation is the object). Repetition is not excessive where the occurrences stand far apart; closeness is the constraint, not repetition itself, and distance licenses the full restated form, openings included. Reference forms are consistent: an object introduced as "this skill" stays "this skill" through the passage, and "this" and "the" do not alternate for one referent. A new paragraph opens a new unit. Repetition of the term is not repetition of the sentence opening: sentence openings vary across a passage, and multiple sentences do not open with the same word (most often "The") unless the repetition is a deliberate emphasis. Where a sentence can be better written opening with words other than "The", that opening is used; "The" opens a sentence only where no better opening serves. A completed passage is checked by listing the first word of each sentence. The check crosses items: in a document with several items of one type (five tutorials, a set of abstracts), items of the same type do not open with the same word or phrase; the first words of peer items are listed alongside the first words within each item.
4. Vary phrase lengths within a sentence and sentence lengths within a paragraph. A paragraph mixes short and long sentences and closes on shorter sentences than it develops with. A results passage is not fragmented into single-datum sentences. Sentence and paragraph structures vary as well, within reason: a passage does not run on one construction, one clause pattern, or paragraphs of one shape and length where a varied structure is available. Structural variety is subordinate to the other rules: variety is not bought at the cost of a definition in place, a bundled number, a named owner, or claim strength, and where variety and another rule conflict, the other rule governs.
5. Put data values in parentheses inside the sentence rather than in a clause of their own.

## STEM documents: structure

6. Opening order: setting, established knowledge, gap, aim, method preview. The gap is stated as a missing piece of knowledge where that is the case.
7. Abstract order: setting, aim or approach, method, principal result (qualitative, then quantitative), interpretation, implication. No limitation is named in the abstract; limitations and scope conditions are named in the closing.
8. Interpretation stands next to the result it interprets. Results sentences carry a number by default.
9. Figures are referred to in the order the results need them. The caption is a noun phrase followed by conditions and sample size, and states the finding when the figure carries the claim.
10. The closing claim is held at or below the abstract claim. Strength is raised only where the closing combines evidence strands explicitly. The closing carries the principal claim at its tested scope, with the limitations named; a closing that states a limitation alone is used only where no scoped claim is available.

## STEM documents: instructional text [tutorials and explainers]

11. A tutorial states its goal in its opening sentences and shows or describes the outcome near the start.
12. A worked example has three parts: inputs, result, and what the result shows or how it is checked.
13. Tutorials address the reader; explainers withhold direct address. Audience and prerequisites are stated where the item assumes them.
14. Checkpoints, expected outputs, and warnings stand at the point of risk. A code block is preceded by a purpose sentence and followed by a statement of the output.

## Claim, number, and definition patterns [shared]

15. The limit stands inside the claim sentence: a concession clause first and the bounded claim as the main clause, or the exception, condition, or scope statement in the same sentence as the claim, placed before the number it qualifies.
16. The number is bundled with its qualifier in the same sentence: denominator or cohort, interval, and named baseline or contrast, in parentheses where the syntax requires it. A denominator is fixed in the sentence that defines the quantity. In a worked example, the sentence that reports a prediction or a scored result carries the baseline the result is scored against in the same sentence, in parentheses where required.
17. A null result is stated as a detection statement with its conditions: what was not detected, under what conditions, over what range, or against which reference. A null is not stated as an absence.
18. A term is defined in place, at its first dependent use: parenthetical or appositive definition, an operational definition attached to the first reported value, or a henceforth sentence that fixes a short name. A composite notation is defined symbol by symbol, in symbol order. A quantity named as a model output or as part of a result (a prediction and its uncertainty, a value and its spread) is a term under this rule and is defined at first use; a worked example is checked at completion for a named quantity that no sentence defines. Chemical species notation is not a term under this rule for a chemical-engineering audience: an element symbol or the formula of a common species (N, H, NH3) carries no definition, in prose or in a where roster.
19. The caption fixes what the text leaves open: method, threshold, baseline, error-bar provenance, replication count, conditions, spread, or the computation that produced the plotted quantity.
20. A choice or a threshold is keyed to its condition in a condition-first sentence: the condition opens the sentence and the recommendation follows.
21. A confirmation sentence names the independent route: the second device, technique, phenomenon, or laboratory that makes the route independent.
22. [analogy in use] An analogy or simplification is followed, within one sentence or the next, by a statement of where it stops holding.

Caution: conditions, replication, and spread belong in the caption in full, and a trend sentence carries its values with it.

## What not to do [shared, unless marked — checklist form; the governing rule or reference is cited]

1. Synonym cycling for the central object or quantity (rule 3). A new name forces the reader to re-identify the object.
2. A number in a sentence of its own, with its baseline, denominator, or conditions in a separate sentence or later (rules 15, 16). A value separated from its comparison has no stated meaning at the point of reading.
3. Inferential connectives that tell the reader the conclusion ("therefore", "thus", a causal "so") [STEM and instructional documents; in business documents the persuasion screen in the business reference governs framing devices, and a connective that misstates evidence remains prohibited].
4. Meta-signposts that announce the text's own moves. The interpretation, the example, or the limit is stated, not announced.
5. Restatement of a result in a further sentence that adds no scope, condition, or limit. A restatement stands only where the added material changes the claim's scope or strength.
6. [business documents] A finding or recommendation held back to the close (business reference, B1; rule 10).
7. Multiple sentences in a passage opening with the same word, most often "The", and a "The" opening where a better opening exists (rule 3). Repetition of an opening word stands only as deliberate emphasis.
8. A general or figurative word where a specific word names the observation: "fall" for a change in a quantity that a procedure reduced or a record shows decreased (register constraints).
9. Alternating reference forms for one object ("this skill" in one sentence, "the skill" in the next) (rule 3).
10. Peer items opening alike: every tutorial in a set opening "Your goal", every abstract opening with the same word (rule 3).
11. One construction repeated through a passage, where a varied structure was available at no cost to the other rules (rule 4).
12. A bare category noun carrying a named object in a sentence that must stand on its own ("The law holds…", "The model predicts…"), where the object's name is available (rule 3).
13. An abstract noun as the subject or frame of a limit statement — recognition strings: "Scope stays at…", "Scope ends at…", "Decision scope stays as stated", "Basis of the comparison was…", "each comparison rests on one stated basis" (textbook reference, validity and omission forms).
14. "Carry" for include, present, or account for — recognition strings: "the equation does not carry a term", "route B carries the lower cost", "two quantities carry the comparison", "every figure carries that basis" (textbook reference).
15. A result or a reported figure as the subject of "holds". "Holds" takes a law, equation, relation, or criterion (textbook reference).

## Completion check

A document under this package is checked at completion, and a document missing an item is not complete:

- Every abbreviation is expanded at first use. A letter abbreviation that names a compound, solvent, or mixture (MEA) is an abbreviation for this check: the name stands at the abbreviation's first use. An element symbol and the chemical formula of a common species (N, NH3, CO2) are not abbreviations for this check and stand without expansion.
- Every figure and stated fact in the source material is carried into the document, or its omission is stated in the document. No claim, consequence, or figure appears that the source material does not state.
- A scored or predicted result carries its baseline complete: the baseline's name and the baseline's own value at the scored point.
- A tutorial's opening states its outcome with its values.
- In a slide storyline, each support line is checked against the title it follows, line by line; a support line carries only its own title's facts.
- The closing restates content — the claim, the relation, or the finding — and does not announce the document's own moves.

## Independent check pass

A document of consequence under this package is checked by a checker that did not write it: a separate session, a subagent, or a human reviewer. Independence is the requirement. The checker's context holds the frozen source material, the draft, and this package, and never the writer's reasoning or earlier drafts. The checker returns findings and does not edit the draft. Each finding quotes the sentence, names the check it fails, gives the evidence (the source passage or the recomputation), and proposes a correction. The writer or the user adjudicates each finding against the primary source before any correction is applied, and corrections are re-checked in the corrected draft. For a long or high-stakes document, two checkers with disjoint scopes replace one checker with the full list. The check list is in `references/ai-check.md`, loaded at the check pass. A completed check is a findings list exhausted, not a certification: the checker tests the draft against the sources it is given, and agreement between writer and checker is not verification of a fact against its primary source.

## AI-writing patterns (the full check list is in `references/ai-check.md`)

Source: Wikipedia, "Signs of AI writing", a WikiProject AI Cleanup advice page; the page is descriptive, not prescriptive. The fault is density and formula, not a single item: one listed word, correct grammar, a formal register, or one transition word is not a defect. Each draft is checked for clusters in five groups — content (inflated importance, trailing participle analysis, promotional wording, vague attribution), word choice (the overused set; the plain word where it says the same thing), sentence form (copula avoidance, stock negative parallelisms, lists of three), filler and framing (noting phrases, chat filler, canned revision assurances, not-found speculation), and format (mechanical boldface, default "**Term:**" lists, heading case, em dash density, placeholder text). The full lists and forms are applied at a revision or check pass from the reference file.
