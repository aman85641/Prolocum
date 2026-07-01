var staticCacheName = 'prolocum-pwa-v1';
var filesToCache = [
  '/',
  '/manifest.json'
];

// Cache on install
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(staticCacheName).then(function(cache) {
      return cache.addAll(filesToCache);
    })
  );
});

// Clear cache on activate
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.filter(function(cacheName) {
          return cacheName.startsWith('prolocum-pwa-') && cacheName !== staticCacheName;
        }).map(function(cacheName) {
          return caches.delete(cacheName);
        })
      );
    })
  );
});

// Serve from cache
self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      return response || fetch(event.request);
    }).catch(function() {
      // Offline fallback
      return caches.match('/');
    })
  );
});
