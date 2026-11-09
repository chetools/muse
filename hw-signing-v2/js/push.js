// Web Push subscription helpers (SPEC, Webapp section). The Worker
// sends one push per graded job when a subscription is stored on the
// job; the payload carries no grade — clicking the notification opens
// the page, which retrieves with the stored name and code.

// VAPID public keys arrive base64url-encoded; PushManager.subscribe
// wants the raw bytes. Pure — Node-tested.
export function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const binary = typeof atob === 'function'
    ? atob(base64)
    : Buffer.from(base64, 'base64').toString('binary');
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

// Reverse of the above, for tests and diagnostics.
export function uint8ArrayToUrlBase64(bytes) {
  let binary = '';
  for (const b of bytes) binary += String.fromCharCode(b);
  const base64 = typeof btoa === 'function'
    ? btoa(binary)
    : Buffer.from(binary, 'binary').toString('base64');
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// Register the service worker and subscribe. Browser only.
// Returns the subscription JSON for the job payload, or null when
// push is unavailable, permission is refused, or no VAPID key is
// configured — push is optional and never blocks a submission.
export async function subscribeToPush(vapidPublicKey) {
  if (!vapidPublicKey) return null;
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return null;
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') return null;
  const registration = await navigator.serviceWorker.register('./sw.js');
  // Let the service worker learn the configured page URL, so a
  // notification click can reopen this exact configured link even
  // after the worker restarts (it reads the Cache Storage entry).
  try {
    const cache = await caches.open('hw-signing-v2-config');
    await cache.put('page-url', new Response(window.location.href));
  } catch { /* the SW falls back to its scope URL */ }
  const existing = await registration.pushManager.getSubscription();
  const subscription = existing || await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  });
  return subscription.toJSON();
}
