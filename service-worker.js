/* =========================================================
   نبض اليمن - Service Worker
   ========================================================= */

const CACHE_NAME =
    "nabd-yemen-v1";

const APP_FILES = [
    "./",
    "./index.html",
    "./style.css",
    "./app.js",
    "./manifest.json"
];


/* =========================================================
   INSTALL
   ========================================================= */

self.addEventListener(
    "install",
    event => {

        event.waitUntil(

            caches
                .open(CACHE_NAME)
                .then(
                    cache => {

                        return cache.addAll(
                            APP_FILES
                        );

                    }
                )

        );

        /*
         * تفعيل النسخة الجديدة مباشرة.
         */
        self.skipWaiting();

    }
);


/* =========================================================
   ACTIVATE
   ========================================================= */

self.addEventListener(
    "activate",
    event => {

        event.waitUntil(

            caches
                .keys()
                .then(
                    keys => {

                        return Promise.all(

                            keys
                                .filter(
                                    key =>
                                        key !== CACHE_NAME
                                )
                                .map(
                                    key =>
                                        caches.delete(key)
                                )

                        );

                    }
                )

        );

        /*
         * التحكم بالصفحات المفتوحة مباشرة.
         */
        self.clients.claim();

    }
);


/* =========================================================
   FETCH
   ========================================================= */

self.addEventListener(
    "fetch",
    event => {

        const request =
            event.request;


        /*
         * نتعامل فقط مع GET.
         */
        if (
            request.method !== "GET"
        ) {
            return;
        }


        const url =
            new URL(request.url);


        /*
         * news.json يجب أن نحاول جلب أحدث
         * نسخة منه من الإنترنت أولاً.
         */
        if (
            url.pathname.endsWith(
                "/news.json"
            )
        ) {

            event.respondWith(

                fetch(request)
                    .then(
                        response => {

                            const copy =
                                response.clone();


                            caches
                                .open(CACHE_NAME)
                                .then(
                                    cache => {

                                        cache.put(
                                            request,
                                            copy
                                        );

                                    }
                                );


                            return response;

                        }
                    )
                    .catch(
                        () =>
                            caches.match(
                                request
                            )
                    )

            );

            return;

        }


        /*
         * ملفات التطبيق:
         * نعرض الكاش أولاً،
         * ثم الإنترنت عند الحاجة.
         */
        event.respondWith(

            caches
                .match(request)
                .then(
                    cachedResponse => {

                        if (
                            cachedResponse
                        ) {

                            return cachedResponse;

                        }


                        return fetch(
                            request
                        );

                    }
                )

        );

    }
);
