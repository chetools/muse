// Mishearing corrections, taken unchanged from the Bernoulli explanation
// app (v21), where they were built from attested mishearings in real takes.
// Only non-terms are corrected, so a genuine word is never rewritten.
export const MISHEAR = [
  [/burn\s?newl[yi]/gi, 'Bernoulli'],
  [/bernou+l[yi]/gi, 'Bernoulli'],
  [/in\s?tell\s?p(?:ea|y)/gi, 'enthalpy'],
  [/friction\s?all heating/gi, 'frictional heating'],
  [/fictional heating/gi, 'frictional heating'],
  [/friction heating/gi, 'frictional heating'],
  [/study floor/gi, 'steady flow'],
  [/steady floor/gi, 'steady flow'],
  [/death value/gi, 'rho value'],
];

export function correctText(t) {
  let out = t;
  for (const [pattern, replacement] of MISHEAR) out = out.replace(pattern, replacement);
  return out;
}
