/* Cache only the public application shell. Audio, credentials and APIs are never cached. */
const CACHE='lingolive-web-1.8.0';
const ASSETS=['/','/assets/style.css','/assets/app.js','/assets/tutorial.js','/assets/google-signin.js','/assets/core.mjs','/assets/context.mjs','/assets/learners.mjs','/assets/personal-memory.mjs','/assets/places.mjs','/assets/signals.mjs','/assets/memory.js','/assets/microphone.js','/assets/pcm-worklet.js','/assets/languages.json','/assets/example.json','/assets/example-kn.json','/assets/icon.svg'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('lingolive-web-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==self.location.origin||!ASSETS.includes(url.pathname))return;
 // Network first allows new releases to update immediately; the cached shell keeps saved lessons usable offline.
 event.respondWith(fetch(event.request).then(response=>{if(response.ok){const copy=response.clone();event.waitUntil(caches.open(CACHE).then(cache=>cache.put(event.request,copy)));}return response;}).catch(()=>caches.match(event.request)));
});
