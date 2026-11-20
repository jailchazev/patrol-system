const CACHE_NAME = 'patrol-static-v3';
const STATIC_ASSETS = ['/static/css/style.css', '/static/js/app.js', '/manifest.webmanifest', '/static/icon-192.png', '/static/icon-512.png'];
self.addEventListener('install', event => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
    event.waitUntil(caches.keys().then(names => Promise.all(names.filter(name => name.startsWith('patrol-') && name !== CACHE_NAME).map(name => caches.delete(name)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
    const request = event.request;
    if (request.method !== 'GET') return;
    const url = new URL(request.url);
    if (url.origin !== self.location.origin) return;
    if (!(url.pathname.startsWith('/static/') || url.pathname === '/manifest.webmanifest')) return;
    event.respondWith(caches.open(CACHE_NAME).then(async cache => {
        const cached = await cache.match(request);
        if (cached) return cached;
        const response = await fetch(request);
        if (response.ok && response.type === 'basic') await cache.put(request, response.clone());
        return response;
    }));
});
