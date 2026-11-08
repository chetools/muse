// Configuration link handling (plan step 2). Pure functions.
//
// The teacher's link carries the webapp configuration as query parameters:
//   w      signing Worker base address
//   pkg    prompt package identifier and version
//   course course label shown to the student
//   asg    assignment label shown to the student
// setup=1 opens the teacher setup mode. Students type no addresses.

export function parseConfig(search) {
  const q = new URLSearchParams(search || '');
  const get = (k) => {
    const v = q.get(k);
    return v && v.trim() ? v.trim() : null;
  };
  return {
    worker: normaliseWorkerBase(get('w')),
    pkg: get('pkg'),
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
  if (cfg.course) u.searchParams.set('course', cfg.course);
  if (cfg.asg) u.searchParams.set('asg', cfg.asg);
  return u.href;
}
