const CACHE_NAME = 'infinity-ai-v1';
const ASSETS = [
  '/',
  '/login',
  '/manifest.json',
  '/css/tokens.css',
  '/css/components.css',
  '/css/letterhead.css',
  '/css/forms.css',
  '/css/table.css',
  '/css/layout.css',
  '/css/responsive.css',
  '/css/login.css',
  '/js/api.js',
  '/js/logger.js',
  '/js/history.js',
  '/js/translations.js',
  '/js/ui.js',
  '/js/auth.js',
  '/js/main.js',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  // Only intercept GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  const url = new URL(event.request.url);
  
  // Bypass API requests to prevent polling and dynamic state corruption
  if (url.pathname.startsWith('/api/')) {
    return;
  }
  
  // Bypass navigation requests to allow server-side redirects to work correctly
  if (event.request.mode === 'navigate') {
    return;
  }

  
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request);
    })
  );
});
