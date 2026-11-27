// HW Signing v2 service worker: tombstone (2.7.0).
//
// The page no longer uses Web Push or any service-worker feature.
// This worker exists only so a browser that still holds the old
// push worker replaces it: on activation it deletes every cache
// the old worker kept and unregisters itself. It has no fetch
// handler and intercepts nothing.

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map((k) => caches.delete(k)));
    await self.registration.unregister();
  })());
});
