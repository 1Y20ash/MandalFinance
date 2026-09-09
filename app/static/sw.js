const CACHE_NAME = 'ashtavinayak-mandal-public-v2';

// Only public, non-sensitive application-shell resources belong in the
// offline cache. In particular, /donate is excluded because its HTML contains
// a server-generated CSRF token and must never be persisted in Cache Storage.
const PUBLIC_SHELL_ASSETS = [
  '/transparency',
  '/static/css/styles.css',
  '/static/manifest.json',
  '/static/img/icon-192.svg',
  '/static/img/icon-512.svg'
];

const PUBLIC_FALLBACK = '/transparency';
const isGetRequest = (request) => request.method === 'GET';
const isSameOrigin = (request) => new URL(request.url).origin === self.location.origin;
const isStaticAsset = (request) => new URL(request.url).pathname.startsWith('/static/');

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PUBLIC_SHELL_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.map((key) => key === CACHE_NAME ? undefined : caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Never interfere with form submissions, payment requests, uploads,
  // downloads, or other non-GET operations.
  if (!isGetRequest(request) || !isSameOrigin(request)) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match(PUBLIC_FALLBACK))
    );
    return;
  }

  // Cache-first is restricted to static assets. Other application responses
  // are network-only so authenticated/private data cannot enter Cache Storage.
  if (isStaticAsset(request)) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => cachedResponse || fetch(request))
    );
  }
});
