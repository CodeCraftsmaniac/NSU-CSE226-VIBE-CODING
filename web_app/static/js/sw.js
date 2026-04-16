/**
 * NSU Degree Audit - Service Worker
 * ==================================
 * Provides offline support and caching for the web application.
 * 
 * Caching Strategy:
 * - Static assets: Cache-first (CSS, JS, images)
 * - API responses: Network-first with cache fallback
 * - User history: Cache with background sync
 */

const CACHE_NAME = 'nsu-audit-v1';
const STATIC_CACHE_NAME = 'nsu-audit-static-v1';
const DYNAMIC_CACHE_NAME = 'nsu-audit-dynamic-v1';

// Static assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/auth.js',
    '/static/favicon.svg',
    '/static/logo.svg',
];

// API endpoints to cache (for offline access)
const CACHEABLE_API_PATTERNS = [
    /\/health$/,
    /\/auth\/config$/,
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[SW] Static assets cached');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[SW] Failed to cache static assets:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => {
                            // Delete old cache versions
                            return name.startsWith('nsu-audit-') && 
                                   name !== STATIC_CACHE_NAME && 
                                   name !== DYNAMIC_CACHE_NAME;
                        })
                        .map((name) => {
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[SW] Activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - handle requests with caching strategy
self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip Chrome extension requests
    if (url.protocol === 'chrome-extension:') {
        return;
    }
    
    // Static assets: Cache-first strategy
    if (isStaticAsset(url)) {
        event.respondWith(cacheFirst(request));
        return;
    }
    
    // API requests: Network-first with cache fallback
    if (isAPIRequest(url)) {
        event.respondWith(networkFirst(request));
        return;
    }
    
    // HTML pages: Network-first with offline fallback
    if (request.headers.get('Accept')?.includes('text/html')) {
        event.respondWith(networkFirstWithOfflineFallback(request));
        return;
    }
    
    // Default: Network-first
    event.respondWith(networkFirst(request));
});

// Check if URL is a static asset
function isStaticAsset(url) {
    const staticExtensions = ['.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.ico', '.woff', '.woff2'];
    return staticExtensions.some(ext => url.pathname.endsWith(ext));
}

// Check if URL is an API request
function isAPIRequest(url) {
    return url.pathname.startsWith('/api') || 
           url.pathname.startsWith('/auth') ||
           url.pathname.startsWith('/health') ||
           url.pathname.startsWith('/upload') ||
           url.pathname.startsWith('/history');
}

// Cache-first strategy: Try cache, then network
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.log('[SW] Network failed for:', request.url);
        // Return a fallback response for images
        if (request.url.match(/\.(png|jpg|jpeg|svg)$/)) {
            return caches.match('/static/logo.svg');
        }
        throw error;
    }
}

// Network-first strategy: Try network, then cache
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            // Cache successful API responses
            const url = new URL(request.url);
            if (isCacheableAPI(url)) {
                const cache = await caches.open(DYNAMIC_CACHE_NAME);
                cache.put(request, networkResponse.clone());
            }
        }
        return networkResponse;
    } catch (error) {
        console.log('[SW] Network failed, trying cache for:', request.url);
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline JSON response for API requests
        if (isAPIRequest(new URL(request.url))) {
            return new Response(
                JSON.stringify({
                    error: 'You are offline',
                    offline: true
                }),
                {
                    status: 503,
                    headers: { 'Content-Type': 'application/json' }
                }
            );
        }
        
        throw error;
    }
}

// Network-first with offline fallback for HTML
async function networkFirstWithOfflineFallback(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.log('[SW] Network failed for HTML, trying cache');
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline page
        return new Response(
            `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NSU Degree Audit - Offline</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            text-align: center;
        }
        .container {
            padding: 2rem;
            max-width: 400px;
        }
        h1 { font-size: 1.5rem; margin-bottom: 1rem; }
        p { color: #a0aec0; margin-bottom: 2rem; }
        button {
            background: #4f46e5;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-size: 1rem;
        }
        button:hover { background: #4338ca; }
        .icon { font-size: 3rem; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📡</div>
        <h1>You're Offline</h1>
        <p>The NSU Degree Audit requires an internet connection for OCR processing and analysis.</p>
        <button onclick="window.location.reload()">Try Again</button>
    </div>
</body>
</html>`,
            {
                status: 200,
                headers: { 'Content-Type': 'text/html' }
            }
        );
    }
}

// Check if API response should be cached
function isCacheableAPI(url) {
    return CACHEABLE_API_PATTERNS.some(pattern => pattern.test(url.pathname));
}

// Handle background sync for history
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync:', event.tag);
    
    if (event.tag === 'sync-history') {
        event.waitUntil(syncHistory());
    }
});

// Sync cached history data when back online
async function syncHistory() {
    console.log('[SW] Syncing history...');
    // Implementation depends on IndexedDB storage of pending uploads
    // This is a placeholder for future implementation
}

// Handle push notifications (if implemented)
self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received');
    
    const options = {
        body: event.data?.text() || 'New notification',
        icon: '/static/favicon.svg',
        badge: '/static/favicon.svg',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
        },
    };
    
    event.waitUntil(
        self.registration.showNotification('NSU Degree Audit', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(
        clients.openWindow('/')
    );
});

console.log('[SW] Service Worker loaded');
