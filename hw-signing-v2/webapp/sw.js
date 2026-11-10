// HW Signing v2 service worker: Web Push only.
//
// The Worker's push payload is {"title": "HW Signing", "body":
// "Your grade and critique are ready."} — it carries no grade and no
// transcript. Clicking the notification opens the configured page
// URL: the page stored its own full URL (with the configuration
// parameters) in the 'hw-signing-v2-config' cache at subscribe time,
// because a service worker cannot otherwise know the query string of
// the link the student used. Fallback is the worker's scope URL.

self.addEventListener('push', (event) => {
  let data = { title: 'HW Signing', body: 'Your grade and critique are ready.' };
  try {
    const parsed = event.data ? event.data.json() : null;
    if (parsed && typeof parsed === 'object') data = { ...data, ...parsed };
  } catch { /* keep the defaults */ }
  event.waitUntil(
    self.registration.showNotification(data.title, { body: data.body })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil((async () => {
    let target = self.registration.scope;
    try {
      const cache = await caches.open('hw-signing-v2-config');
      const stored = await cache.match('page-url');
      if (stored) target = await stored.text();
    } catch { /* fall back to the scope URL */ }
    const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of clients) {
      if (client.url === target && 'focus' in client) return client.focus();
    }
    return self.clients.openWindow(target);
  })());
});
