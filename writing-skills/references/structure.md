# Structure and order [load to reorganize existing text, or to plan the order of a new document of more than about 300 words]

Activation: a request to reorganize, reorder, or restructure an essay, report, section, or other existing text; or the outline step of a new document whose body exceeds about 300 words. This file orders the material that a type frame leaves open and sizes the opening and the closing. Where a type frame applies, the frame fixes what the opening and the closing contain and in what order: core rules 16, 17, and 20 for STEM text, core rule 21 for a tutorial, and B1, B2, and B5 in `business.md` for a business document. An essay with no assigned type takes the default frame in S7.

## Procedure

S1. Inventory. The text is split into units, each unit one claim with the sentences that support it, and each unit is tagged with its role: thesis, claim, evidence, definition, example, limit, or aside. Each unit keeps its source location (paragraph and sentence). The inventory is a working record and does not enter the document.
S2. Thesis. The principal claim is stated in one sentence, taken from the source. Where the source states no principal claim, or states two that compete, the finding is reported in the covering message and no thesis is invented (core rule 3).
S3. Rank. Each unit is ranked by importance to the reader, judged on three grounds in order: whether the thesis requires it, how many other units depend on it, and the weight of its evidence. The ranks are principal, supporting, and peripheral. Where two units tie on all three grounds, or the rank rests on judgement rather than on a dependency, the rank is marked as a judgement in the record.
S4. Dependencies. A unit requires another unit when it uses a term, symbol, premise, method, or result that the other unit introduces. Every requirement is listed as a pair in the record. Core rule 28 fixes the most frequent pair: a definition stands at or before its first dependent use.
S5. Order. The body order is a topological order of the dependency pairs, with rank as the tie-break: no unit stands before a unit it requires, and among units free to move, the higher rank stands first. Units on one topic stand together in one passage, unless a dependency splits them. Where two units each require the other, the shorter of the two is stated first in brief and in full at its ranked place; where no such statement resolves the cycle, the cycle is reported in the covering message. Core rule 6 fixes the last place: implementation detail stands after the content it implements.
S6. Peripheral and duplicate units. A peripheral unit is kept, moved to the end of its passage or into the closing limits, and listed in the record; a peripheral unit is cut only on request. Two units that state the same claim are merged into one, and the merged unit keeps every qualifier, number, and condition of both (core rules 3 and 26).
S7. Opening and closing size. The opening and the closing scale with the word count N of the body (the text between them):
    - Below about 300 words: the opening is one sentence that states the thesis; the closing is one sentence.
    - From about 300 to about 1500 words: the opening is one paragraph of two to five sentences, and the closing is one paragraph.
    - Above about 1500 words: the opening is up to three paragraphs, or a headed introduction; the closing is a headed section of one to three paragraphs.
    The opening and the closing each stay near 5–15 % of N. Default frame, for an essay with no type frame: the opening states the topic and the thesis, and, above about 300 words, the principal units in body order, each as a claim; the closing restates the thesis at its supported scope with its limits named (core rule 20). A preview states the claims themselves, never the document's moves ("This essay discusses …" is a meta-signpost under core rule 15). The closing adds no new claim and no new evidence.
S8. Paragraphs. Each principal unit opens its own paragraph with its claim, and its supporting units follow in that paragraph. A supporting unit that serves two principal units stands with the first of them and is referred to by name at the second (core rule 10).
S9. Wording. Body sentences keep their source wording. Edits are limited to the opening, the closing, the transitions, and the joins that a move breaks: a pronoun whose antecedent moved, a "the former", "as above", or "see below" whose referent changed place, and a definition that now stands after its first dependent use. A full rewrite is made only on request, and then under the rest of the package.
S10. Record. The covering message (core rule 36) states the thesis as found, the new outline (one line per paragraph), the move list (each moved unit, from where, to where, and the reason: a dependency pair or a rank), the peripheral and merged units, and each rank marked as a judgement. None of this enters the document (core rule 6).

## Pitfalls

- Order by rank alone, which places a result before the definition or method it needs.
- Composing a thesis from units the source does not join, which states a claim the source does not make (core rule 3).
- Merging two duplicate units and losing a qualifier or a number that only one of them stated.
- An opening sized to a fixed sentence count regardless of N, such as a three-paragraph introduction to a 200-word piece.
- Closing on the preview's list of points in place of the thesis and its limits.

## Completion check

Every source unit stands in the output or in the record as merged; no unit stands before a unit it requires; the opening and the closing fall in the size band for N; the thesis, or the reported absence of one, stands in the opening and in the closing; body sentences keep their wording except the joins named in S9; the fidelity diff of the revision pass (`ai-check.md`, item 9b) finds the same claims, numbers, and qualifiers before and after the move.
