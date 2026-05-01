/* sw.js — Service Worker，让PWA支持离线 */

const CACHE_NAME = 'njust-schedule-v2';
const PRECACHE = [
  './',
  './index.html',
  './css/style.css',
  './js/app.js',
  './js/schedule.js',
  './js/storage.js',
  './data/schedule.json',
  './data/exams.json',
  './manifest.json'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // 开发模式：网络优先，有网络就用最新版本
  e.respondWith(
    fetch(e.request).then((resp) => {
      if (!resp || resp.status !== 200 || resp.type !== 'basic') return resp;
      const clone = resp.clone();
      caches.open(CACHE_NAME).then((c) => c.put(e.request, clone));
      return resp;
    }).catch(() => {
      // 离线时 fallback 到缓存
      return caches.match(e.request);
    })
  );
});
