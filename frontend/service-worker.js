// Name of the cache
const CACHE_NAME = "cache";
// Caching duration of the items, one week here
const CACHING_DURATION = 300000;
// Verbose logging or not
const DEBUG = true;

self.addEventListener('install', function(event) {
    event.waitUntil(self.skipWaiting()); // Activate worker immediately
});

self.addEventListener('activate', function(event) {
    event.waitUntil(self.clients.claim()); // Become available to all pages
});


self.addEventListener('fetch', (event) => {
    const { request } = event;

    console.log("Trying to fetch in cache" + event + request);

    event.respondWith(self.caches.open(`${CACHE_NAME}-tiles`).then(
        cache => cache.match(request).then(
            (response) => {
                // If there is a match from the cache
                if (response) {
                    DEBUG && console.log(`SW: serving ${request.url} from cache.`);
                    const expirationDate = Date.parse(response.headers.get('sw-cache-expires'));
                    const now = new Date();
                    // Check it is not already expired and return from the
                    // cache
                    if (expirationDate > now) {
                        return response;
                    }
                }

                // Otherwise, let's fetch it from the network
                DEBUG && console.log(`SW: no match in cache for ${request.url}, using network.`);
                // Note: We HAVE to use fetch(request.url) here to ensure we
                // have a CORS-compliant request. Otherwise, we could get back
                // an opaque response which we cannot inspect
                // (https://developer.mozilla.org/en-US/docs/Web/API/Response/type).
                return fetch(request.url).then((liveResponse) => {
                    // Compute expires date from caching duration
                    const expires = new Date();
                    expires.setSeconds(
                        expires.getSeconds() + CACHING_DURATION,
                    );
                    // Recreate a Response object from scratch to put
                    // it in the cache, with the extra header for
                    // managing cache expiration.
                    const cachedResponseFields = {
                        status: liveResponse.status,
                        statusText: liveResponse.statusText,
                        headers: { 'SW-Cache-Expires': expires.toUTCString() },
                    };
                    liveResponse.headers.forEach((v, k) => {
                        cachedResponseFields.headers[k] = v;
                    });
                    // We will consume body of the live response, so
                    // clone it before to be able to return it
                    // afterwards.
                    const returnedResponse = liveResponse.clone();
                    return liveResponse.blob().then((body) => {
                        DEBUG && console.log(
                            `SW: caching tiles ${request.url} until ${expires.toUTCString()}.`,
                        );
                        // Put the duplicated Response in the cache
                        cache.put(request, new Response(body, cachedResponseFields));
                        // Return the live response from the network
                        return returnedResponse;
                    });
                });
            })
        )
    );
});

self.addEventListener('message', (event) => {
    console.log(`SW: received message ${event.data}.`);

    const eventData = JSON.parse(event.data);

    // Clean tiles cache when we receive the message asking to do so
    if (eventData.action === 'PURGE_EXPIRED_TILES') {
        DEBUG && console.log('SW: purging expired tiles from cache.');
        self.caches.open(`${CACHE_NAME}-tiles`).then(
            cache => cache.keys().then(
                keys => keys.forEach(
                    // Loop over all requests stored in the cache and get the
                    // matching cached response.
                    key => cache.match(key).then((cachedResponse) => {
                        // Check expiration and eventually delete the cached
                        // item
                        const expirationDate = Date.parse(cachedResponse.headers.get('sw-cache-expires'));
                        const now = new Date();
                        if (expirationDate < now) {
                            DEBUG && console.log(`SW: purging (expired) tile ${key.url} from cache.`);
                            cache.delete(key);
                        }
                    }),
                ),
            ),
        );
    }
});

// Get duration (in s) before (cache) expiration from headers of a fetch
// request.
function getExpiresFromHeaders(headers) {
    // Try to use the Cache-Control header (and max-age)
    if (headers.get('cache-control')) {
        const maxAge = headers.get('cache-control').match(/max-age=(\d+)/);
        return parseInt(maxAge ? maxAge[1] : 0, 10);
    }

    // Otherwise try to get expiration duration from the Expires header
    if (headers.get('expires')) {
        return (
            parseInt(
                (new Date(headers.get('expires'))).getTime() / 1000,
                10,
            )
            - (new Date()).getTime()
        );
    }
    return null;
}
