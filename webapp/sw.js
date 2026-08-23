/* sw.js — Service Worker，让PWA支持离线 */

const CACHE_NAME = 'njust-schedule-v4';
const PRECACHE = [
  './',
  './index.html',
  './css/style.css',
  './js/app.js',
  './js/schedule.js',
  './js/storage.js',
  './data/schedule.enc.json',
  './data/exams.enc.json',
  './manifest.json'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    // 逐个缓存：单个文件失败（如404）不影响整体安装
    caches.open(CACHE_NAME).then((cache) =>
      Promise.allSettled(PRECACHE.map((url) => cache.add(url)))
    )
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
  const url = new URL(e.request.url);
  const hasQuery = url.search.length > 0;
  e.respondWith(
    fetch(e.request).then((resp) => {
      if (!resp || resp.status !== 200 || resp.type !== 'basic') return resp;
      // 带查询参数（如 ?v=时间戳）的请求不写入缓存，避免缓存无限增长；
      // 预缓存的精确匹配不受影响
      if (!hasQuery) {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then((c) => c.put(e.request, clone));
      }
      return resp;
    }).catch(() => {
      // 离线时 fallback 到缓存
      // 对数据文件（带 ?v=... 时间戳），尝试不带查询参数的缓存匹配
      if (url.pathname.endsWith('/data/schedule.enc.json') || url.pathname.endsWith('/data/exams.enc.json')) {
        const cacheUrl = e.request.url.split('?')[0];
        return caches.match(cacheUrl);
      }
      // 其余请求忽略查询参数匹配（js/css 带 ?v=版本号 也能命中预缓存）
      return caches.match(e.request, { ignoreSearch: true });
    })
  );
});
