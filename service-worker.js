const CACHE_NAME = "yunjianan-v4-4";
const CORE = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async cache => {
      await cache.addAll(CORE);
      try {
        const feed = await fetch("./weekly_feed.json", {cache:"no-store"});
        if (feed.ok) await cache.put("./weekly_feed.json", feed.clone());
      } catch (_) {}
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

async function networkFirst(request, fallbackUrl) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const response = await fetch(request);
    if (response && response.ok) cache.put(request, response.clone());
    return response;
  } catch (_) {
    return (await cache.match(request)) || (fallbackUrl ? await cache.match(fallbackUrl) : undefined);
  }
}

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request, "./index.html"));
    return;
  }

  if (url.pathname.endsWith("/weekly_feed.json")) {
    event.respondWith(networkFirst(request, "./weekly_feed.json"));
    return;
  }

  event.respondWith(
    caches.match(request).then(cached => {
      if (cached) {
        fetch(request).then(response => {
          if (response && response.ok) {
            caches.open(CACHE_NAME).then(cache => cache.put(request, response.clone()));
          }
        }).catch(() => {});
        return cached;
      }

      return fetch(request).then(response => {
        if (response && response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
        }
        return response;
      });
    })
  );
});
