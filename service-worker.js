/* =========================================================
   نبض اليوم - Service Worker
   ========================================================= */

const CACHE_NAME =
    "nabd-yemen-v2";


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
            new URL(
                request.url
            );


        /* =================================================
           news.json
           دائماً الإنترنت أولاً
           ================================================= */

        if (
            url.pathname.endsWith(
                "/news.json"
            )
        ) {

            event.respondWith(

                fetch(
                    request,
                    {
                        cache: "no-store"
                    }
                )

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


        /* =================================================
           app.js و style.css و index.html
           الإنترنت أولاً
           حتى تصل التحديثات مباشرة
           ================================================= */

        if (
            url.pathname.endsWith("/app.js")
            ||
            url.pathname.endsWith("/style.css")
            ||
            url.pathname.endsWith("/index.html")
            ||
            url.pathname.endsWith("/")
        ) {

            event.respondWith(

                fetch(
                    request,
                    {
                        cache: "no-store"
                    }
                )

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


        /* =================================================
           باقي الملفات
           الكاش أولاً
           ================================================= */

        event.respondWith(

            caches
                .match(
                    request
                )
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