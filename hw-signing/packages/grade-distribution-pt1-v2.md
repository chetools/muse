# Prompt package (pkg: grade-distribution-pt1 v2)

Status: This package supersedes grade-distribution-pt1 v1 at the teacher's
direction on 2026-11-08. It contains no checklist. Any change to this
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

## Grading basis

There is no checklist for this homework: no key points, no connections
list, and no weights are given. Grading is a judgment made from the
homework description and the lecture transcript portions above only —
how fully the student's explanation covers what they call for, and how
correct what the student states is, including whether the reasoning
links ideas correctly.
