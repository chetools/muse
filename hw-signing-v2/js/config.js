// Configuration link handling. Pure functions.
//
// The teacher's link carries the webapp configuration as query parameters:
//   w      grading Worker base address
//   pkg    prompt package identifier and version ("<name> v<version>")
//   ph     prompt package CONTENT SHA-256: the page passes it to the
//          Worker as pkg_content_sha256 on job creation, and the
//          Worker grades only when it matches the stored package
//   course course label shown to the student
//   asg    assignment label shown to the student
// setup=1 opens the teacher setup mode. Students type no addresses.
//
// v2 difference from v1: the prompt package is never published and
// the page never fetches it, so v1's pkgurl parameter is gone; ph
// takes its place as the link's binding to the exact package text.

export function parseConfig(search) {
  const q = new URLSearchParams(search || '');
  const get = (k) => {
    const v = q.get(k);
    return v && v.trim() ? v.trim() : null;
  };
  return {
    worker: normaliseWorkerBase(get('w')),
    pkg: get('pkg'),
    ph: get('ph'),
    course: get('course'),
    asg: get('asg'),
    setup: q.get('setup') === '1',
  };
}

export function normaliseWorkerBase(w) {
  if (!w) return null;
  return String(w).replace(/\/+$/, '');
}

export function buildConfigLink(baseUrl, cfg) {
  const u = new URL(baseUrl);
  u.search = '';
  u.hash = '';
  if (cfg.worker) u.searchParams.set('w', cfg.worker);
  if (cfg.pkg) u.searchParams.set('pkg', cfg.pkg);
  if (cfg.ph) u.searchParams.set('ph', cfg.ph);
  if (cfg.course) u.searchParams.set('course', cfg.course);
  if (cfg.asg) u.searchParams.set('asg', cfg.asg);
  return u.href;
}
