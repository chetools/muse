# Prompt package (pkg: grade-distribution-pt1 v1)

Status: frozen. Approved by the teacher on 2026-11-08. Any change to this
package is a new version with a new pkg identifier.

## Homework description

Explain how the most probable distribution of scores on a test is set up
to be found, for a fictional test out of 50 points with an average score
of 40 points, a standard deviation of 8.5 points, and 20% of the students
scoring less than 25 points. This is Part 1: it covers the counting
argument, the logarithm and Stirling's approximation, and the reduction
to the form that a later numerical maximisation (Part 2) will use,
together with the given statistics written as equations to be imposed.
Finding the distribution itself is Part 2 and is not required here.

## Lecture transcript portions

A bell curve will not be the most probable distribution in this case,
because a bell curve would predict that some students got over 50
points, and that is not possible on a 50-point test.

Take a simpler case first: 10 students, a test out of three points with
scores 1, 2, and 3, and an average score of 2. One possible distribution
is 0 students scoring 1, 10 students scoring 2, and 0 students scoring
3. Another is 3 students scoring 1, 4 students scoring 2, and 3 students
scoring 3. The second distribution is far more likely, because there are
many more ways to allocate the students to it. Counting the allocations:
choose the students for one score, then the next, dividing by the
factorial of each group size because the order in which students are
chosen within a group does not matter. The number of ways to realise a
distribution of N students is N! divided by the product of the
factorials of the numbers of students at each score. Maximising that
number of ways gives the most likely distribution.

For large N the factorials are too large to work with directly, so take
natural logarithms: ln(N!) is the sum of ln(k) for k from 1 to N, and
that sum is approximated by the integral of ln(x) from 1 to N
(Stirling's approximation). Integration by parts gives x ln(x) − x, so
ln(N!) ≈ N ln(N) − N. Applying this to the number of ways and using
that the numbers of students at all scores sum to N, the logarithm of
the number of ways reduces to −N Σ pᵢ ln(pᵢ), where pᵢ = nᵢ/N is the
fraction of students scoring i. A natural log is continuous and
increasing, so maximising the logarithm of the number of ways maximises
the number of ways itself.

## Key-point checklist (frozen)

Key points:

- K1, weight 1: The problem data are stated: a test out of 50 points, an average score of 40 points, a standard deviation of 8.5 points, and 20% of the students scoring less than 25 points.
- K2, weight 1: A simpler worked case is used first — 10 students, scores 1 to 3, average 2 — with two contrasting distributions, such as (0, 10, 0) and (3, 4, 3), both consistent with the average.
- K3, weight 2: The number of ways to realise a distribution is the multinomial count N!/(n₁! n₂! n₃! ⋯), obtained by choosing the students for each score in turn and dividing by each group size's factorial because the order of choosing within a group does not matter.
- K4, weight 1: The count is generalised to scores 0 to 50: W = N! / Π nᵢ!, where nᵢ is the number of students scoring i and the nᵢ sum to N.
- K5, weight 2: Stirling's approximation is derived: ln(N!) is written as a sum of logarithms, the sum is approximated by the integral of ln(x) from 1 to N, and integration by parts gives ln(N!) ≈ N ln(N) − N.
- K6, weight 2: The logarithm of the number of ways is reduced, using Σ nᵢ = N to cancel terms, to ln W ≈ −N Σ pᵢ ln(pᵢ), with pᵢ = nᵢ/N defined as the fraction of students scoring i.
- K7, weight 1: The given statistics are written as equations to be imposed on the nᵢ: Σ nᵢ = N; Σ i·nᵢ = 40N; Σ (i − 40)² nᵢ = 8.5² N; Σ over i < 25 of nᵢ = 0.20N.

Connections:

- C1, weight 1: Connection — a bell curve is ruled out because the scores are bounded above by 50, while a bell curve assigns probability to scores over 50.
- C2, weight 1: Connection — the most probable distribution is the one with the largest number of ways of occurring, on the basis that each individual allocation of students to scores is equally likely.
- C3, weight 1: Connection — maximising ln W maximises W because the logarithm is increasing, and taking logarithms turns the factorials and products in W into sums that Stirling's approximation can handle.
