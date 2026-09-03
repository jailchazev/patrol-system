const CACHE_NAME = 'patrol-system-v2';

const urlsToCache = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/manifest.webmanifest',
    '/static/icon-192.png',
    '/static/icon-512.png'
];

// INSTALACIÓN
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
            .then(() => self.skipWaiting())
            .catch(err => console.error('Error cacheando:', err))
    );
});

// ACTIVACIÓN
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(cacheName => cacheName !== CACHE_NAME)
                    .map(cacheName => caches.delete(cacheName))
            );
        }).then(() => self.clients.claim())
    );
});

// PETICIONES
self.addEventListener('fetch', event => {

    // Solo manejar solicitudes GET
    if (event.request.method !== 'GET') {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then(response => {

                // Guardar una copia de recursos válidos
                if (response && response.status === 200) {
                    const responseClone = response.clone();

                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseClone);
                    });
                }

                return response;
            })
            .catch(() => {
                return caches.match(event.request);
            })
    );
});