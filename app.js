/* =========================================================
   نبض اليمن - app.js
   ========================================================= */


/* =========================================================
   Firebase
   ========================================================= */

import { initializeApp }
    from "https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js";

import {
    getDatabase,
    ref,
    runTransaction,
    onValue
}
    from "https://www.gstatic.com/firebasejs/12.19.0/firebase-database.js";


const firebaseConfig = {
    apiKey: "AIzaSyBgEsIfIPj10BRXYwvJRkxgvmDRsPXnqkM",
    authDomain: "nabd-yemen.firebaseapp.com",
    databaseURL: "https://nabd-yemen-default-rtdb.europe-west1.firebasedatabase.app",
    projectId: "nabd-yemen",
    storageBucket: "nabd-yemen.firebasestorage.app",
    messagingSenderId: "178851320724",
    appId: "1:178851320724:web:3c1b9c17be1c518b127581"
};


const firebaseApp =
    initializeApp(firebaseConfig);

const database =
    getDatabase(firebaseApp);


/* =========================================================
   عناصر الصفحة
   ========================================================= */

const newsList =
    document.getElementById("newsList");

const statusBox =
    document.getElementById("statusBox");

const emptyState =
    document.getElementById("emptyState");

const refreshButton =
    document.getElementById("refreshButton");

const sortNewestButton =
    document.getElementById("sortNewestButton");

const sortPopularButton =
    document.getElementById("sortPopularButton");

const visitsCount =
    document.getElementById("visitsCount");

const viewsCount =
    document.getElementById("viewsCount");

const readsCount =
    document.getElementById("readsCount");


/* =========================================================
   الإعدادات
   ========================================================= */

const NEWS_FILE =
    "./news.json";

const STORAGE_KEY =
    "nabd-yemen-news";

const SORT_KEY =
    "nabd-yemen-sort";

const VISITOR_KEY =
    "nabd-yemen-visitor-counted";

/*
 * الأخبار التي شاهدها هذا المتصفح.
 *
 * نستخدم localStorage وليس sessionStorage،
 * حتى لا تزيد مشاهدة الخبر عند إغلاق التطبيق
 * وفتحه مرة أخرى من الجهاز نفسه.
 */
const ARTICLE_VIEW_KEY =
    "nabd-yemen-viewed-articles";

/*
 * الأخبار التي سبق لهذا الجهاز قراءتها.
 */
const ARTICLE_READ_KEY =
    "nabd-yemen-read-articles";


/* =========================================================
   المتغيرات
   ========================================================= */

let allNews = [];

let currentSort =
    localStorage.getItem(SORT_KEY)
    || "newest";

let isLoading = false;

let articleStats = {};

/*
 * مراقب ظهور الأخبار على الشاشة.
 */
let articleObserver = null;


/* =========================================================
   تنظيف النص
   ========================================================= */

function escapeHtml(value) {

    if (
        value === null
        ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/* =========================================================
   تحويل التاريخ إلى رقم
   ========================================================= */

function getTimeValue(item) {

    const possibleDates = [
        item.published_at,
        item.published,
        item.date,
        item.datetime,
        item.timestamp,
        item.created_at
    ];


    for (const value of possibleDates) {

        if (!value) {
            continue;
        }


        if (
            typeof value === "number"
        ) {

            if (
                value <
                1000000000000
            ) {

                return value * 1000;
            }

            return value;
        }


        const parsed =
            Date.parse(value);


        if (
            !Number.isNaN(parsed)
        ) {

            return parsed;
        }
    }


    return 0;
}


/* =========================================================
   المصدر
   ========================================================= */

function getSource(item) {

    return (
        item.source
        ||
        item.source_name
        ||
        item.publisher
        ||
        item.site
        ||
        "مصدر إخباري"
    );
}


/* =========================================================
   العنوان
   ========================================================= */

function getTitle(item) {

    return (
        item.title
        ||
        item.headline
        ||
        "خبر بدون عنوان"
    );
}


/* =========================================================
   الرابط
   ========================================================= */

function getLink(item) {

    return (
        item.link
        ||
        item.url
        ||
        item.article_url
        ||
        "#"
    );
}


/* =========================================================
   الصورة
   ========================================================= */

function getImage(item) {

    return (
        item.image
        ||
        item.image_url
        ||
        item.thumbnail
        ||
        item.photo
        ||
        ""
    );
}


/* =========================================================
   الوصف
   ========================================================= */

function getDescription(item) {

    return (
        item.description
        ||
        item.summary
        ||
        item.excerpt
        ||
        ""
    );
}


/* =========================================================
   رقم ثابت لكل خبر
   ========================================================= */

function getArticleId(item) {

    const link =
        getLink(item);

    const title =
        getTitle(item);

    const text =
        (
            link
            &&
            link !== "#"
        )
            ? link
            : title;


    let hash =
        2166136261;


    for (
        let i = 0;
        i < text.length;
        i++
    ) {

        hash ^=
            text.charCodeAt(i);

        hash =
            Math.imul(
                hash,
                16777619
            );
    }


    return (
        "a_"
        +
        (hash >>> 0).toString(36)
    );
}


/* =========================================================
   عدد مشاهدات الخبر
   ========================================================= */

function getArticleViews(item) {

    const articleId =
        getArticleId(item);


    const value =
        articleStats[
            articleId
        ]?.views;


    const number =
        Number(
            value
            ??
            0
        );


    if (
        Number.isNaN(number)
    ) {

        return 0;
    }


    return number;
}


/* =========================================================
   عدد قراءات الخبر
   ========================================================= */

function getArticleReads(item) {

    const articleId =
        getArticleId(item);


    const firebaseValue =
        articleStats[
            articleId
        ]?.reads;


    const fallback =
        item.reads
        ??
        item.view_count
        ??
        item.clicks
        ??
        0;


    const number =
        Number(
            firebaseValue
            ??
            fallback
        );


    if (
        Number.isNaN(number)
    ) {

        return 0;
    }


    return number;
}


/* =========================================================
   تنسيق التاريخ
   ========================================================= */

function formatDate(item) {

    const timestamp =
        getTimeValue(item);


    if (!timestamp) {

        return (
            item.date_text
            ||
            item.time
            ||
            ""
        );
    }


    try {

        const date =
            new Date(timestamp);


        return new Intl.DateTimeFormat(
            "ar",
            {
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit"
            }
        ).format(date);

    }

    catch {

        return "";
    }
}


/* =========================================================
   زيادة عداد Firebase
   ========================================================= */

async function incrementCounter(path) {

    try {

        await runTransaction(
            ref(
                database,
                path
            ),

            currentValue => {

                return (
                    Number(currentValue)
                    ||
                    0
                ) + 1;
            }
        );

    }

    catch (error) {

        console.error(
            "Firebase counter error:",
            path,
            error
        );
    }
}


/* =========================================================
   تسجيل فتح التطبيق
   ========================================================= */

async function registerAppVisit() {

    /*
     * نحتفظ بهذا العداد في Firebase
     * حتى لو لم يعد ظاهراً في أعلى الصفحة.
     */
    await incrementCounter(
        "stats/views"
    );


    /*
     * الزائر يحسب مرة واحدة لكل متصفح/جهاز.
     */
    if (
        !localStorage.getItem(
            VISITOR_KEY
        )
    ) {

        await incrementCounter(
            "stats/visits"
        );


        localStorage.setItem(
            VISITOR_KEY,
            "1"
        );
    }
}


/* =========================================================
   الإحصائيات العامة
   ========================================================= */

function listenToGlobalStats() {

    onValue(
        ref(
            database,
            "stats"
        ),

        snapshot => {

            const stats =
                snapshot.val()
                ||
                {};


            if (visitsCount) {

                visitsCount.textContent =
                    Number(
                        stats.visits
                        ||
                        0
                    ).toLocaleString("ar");
            }


            if (viewsCount) {

                viewsCount.textContent =
                    Number(
                        stats.views
                        ||
                        0
                    ).toLocaleString("ar");
            }


            if (readsCount) {

                readsCount.textContent =
                    Number(
                        stats.reads
                        ||
                        0
                    ).toLocaleString("ar");
            }
        },

        error => {

            console.error(
                "تعذر قراءة الإحصائيات:",
                error
            );
        }
    );
}


/* =========================================================
   متابعة إحصائيات الأخبار
   ========================================================= */

function listenToArticleStats() {

    onValue(
        ref(
            database,
            "articles"
        ),

        snapshot => {

            articleStats =
                snapshot.val()
                ||
                {};


            renderNews();
        },

        error => {

            console.error(
                "تعذر قراءة إحصائيات الأخبار:",
                error
            );
        }
    );
}


/* =========================================================
   الأخبار التي سبق لهذا الجهاز مشاهدتها
   ========================================================= */

function getViewedArticles() {

    try {

        const value =
            localStorage.getItem(
                ARTICLE_VIEW_KEY
            );


        if (!value) {

            return new Set();
        }


        const parsed =
            JSON.parse(value);


        if (
            !Array.isArray(parsed)
        ) {

            return new Set();
        }


        return new Set(
            parsed
        );

    }

    catch {

        return new Set();
    }
}


/* =========================================================
   حفظ الأخبار التي شاهدها الجهاز
   ========================================================= */

function saveViewedArticles(set) {

    try {

        localStorage.setItem(
            ARTICLE_VIEW_KEY,
            JSON.stringify(
                [...set]
            )
        );

    }

    catch (error) {

        console.warn(
            "تعذر حفظ المشاهدات:",
            error
        );
    }
}


/* =========================================================
   تسجيل مشاهدة خبر واحد
   ========================================================= */

async function registerArticleView(item) {

    const articleId =
        getArticleId(item);


    const viewedArticles =
        getViewedArticles();


    /*
     * إذا سبق لهذا المتصفح مشاهدة الخبر،
     * فلا نزيد العداد مرة أخرى.
     */
    if (
        viewedArticles.has(
            articleId
        )
    ) {

        return;
    }


    /*
     * نسجله محلياً أولاً لمنع التكرار.
     */
    viewedArticles.add(
        articleId
    );


    saveViewedArticles(
        viewedArticles
    );


    await incrementCounter(
        `articles/${articleId}/views`
    );
}


/* =========================================================
   إنشاء مراقب ظهور الأخبار
   ========================================================= */

function createArticleObserver() {

    /*
     * إيقاف المراقب القديم عند إعادة رسم الأخبار.
     */
    if (articleObserver) {

        articleObserver.disconnect();
    }


    articleObserver =
        new IntersectionObserver(

            entries => {

                for (const entry of entries) {

                    /*
                     * لا نحسب المشاهدة إلا إذا ظهر
                     * 50% على الأقل من بطاقة الخبر.
                     */
                    if (
                        !entry.isIntersecting
                        ||
                        entry.intersectionRatio < 0.5
                    ) {

                        continue;
                    }


                    const article =
                        entry.target;


                    const item =
                        article._newsItem;


                    if (!item) {

                        articleObserver.unobserve(
                            article
                        );

                        continue;
                    }


                    /*
                     * بعد ظهور الخبر نحاول تسجيل
                     * المشاهدة مرة واحدة.
                     */
                    registerArticleView(
                        item
                    );


                    /*
                     * لا حاجة إلى مراقبة هذه البطاقة
                     * مرة أخرى خلال هذا العرض.
                     */
                    articleObserver.unobserve(
                        article
                    );
                }
            },

            {
                threshold: 0.5
            }
        );
}


/* =========================================================
   مراقبة البطاقات الموجودة حالياً
   ========================================================= */

function observeNewsCards() {

    createArticleObserver();


    const cards =
        newsList.querySelectorAll(
            ".news-card"
        );


    for (const card of cards) {

        articleObserver.observe(
            card
        );
    }
}


/* =========================================================
   الأخبار التي سبق لهذا الجهاز قراءتها
   ========================================================= */

function getReadArticles() {

    try {

        const value =
            localStorage.getItem(
                ARTICLE_READ_KEY
            );


        if (!value) {

            return new Set();
        }


        const parsed =
            JSON.parse(value);


        if (
            !Array.isArray(parsed)
        ) {

            return new Set();
        }


        return new Set(
            parsed
        );

    }

    catch {

        return new Set();
    }
}


/* =========================================================
   حفظ الأخبار المقروءة
   ========================================================= */

function saveReadArticles(set) {

    try {

        localStorage.setItem(
            ARTICLE_READ_KEY,
            JSON.stringify(
                [...set]
            )
        );

    }

    catch (error) {

        console.warn(
            "تعذر حفظ الأخبار المقروءة:",
            error
        );
    }
}


/* =========================================================
   تسجيل قراءة خبر
   مرة واحدة فقط لكل جهاز/متصفح
   ========================================================= */

async function registerArticleRead(item) {

    const articleId =
        getArticleId(item);


    const readArticles =
        getReadArticles();


    if (
        readArticles.has(
            articleId
        )
    ) {

        return;
    }


    readArticles.add(
        articleId
    );


    saveReadArticles(
        readArticles
    );


    await Promise.all([

        incrementCounter(
            "stats/reads"
        ),

        incrementCounter(
            `articles/${articleId}/reads`
        )

    ]);
}


/* =========================================================
   ترتيب الأخبار
   ========================================================= */

function sortNews(news) {

    const copy =
        [...news];


    if (
        currentSort ===
        "popular"
    ) {

        copy.sort(
            (a, b) => {

                const readsDifference =
                    getArticleReads(b)
                    -
                    getArticleReads(a);


                if (
                    readsDifference !== 0
                ) {

                    return readsDifference;
                }


                return (
                    getTimeValue(b)
                    -
                    getTimeValue(a)
                );
            }
        );


        return copy;
    }


    copy.sort(
        (a, b) =>
            getTimeValue(b)
            -
            getTimeValue(a)
    );


    return copy;
}


/* =========================================================
   إنشاء بطاقة الخبر
   ========================================================= */

function createNewsCard(item) {

    const title =
        escapeHtml(
            getTitle(item)
        );


    const source =
        escapeHtml(
            getSource(item)
        );


    const description =
        escapeHtml(
            getDescription(item)
        );


    const link =
        escapeHtml(
            getLink(item)
        );


    const image =
        escapeHtml(
            getImage(item)
        );


    const date =
        escapeHtml(
            formatDate(item)
        );


    const articleViews =
        getArticleViews(item);


    const articleReads =
        getArticleReads(item);


    const article =
        document.createElement(
            "article"
        );


    article.className =
        "news-card";


    /*
     * نربط الخبر ببطاقته حتى يعرف
     * IntersectionObserver أي خبر ظهر.
     */
    article._newsItem =
        item;


    let imageHtml = "";


    if (image) {

        imageHtml = `
            <img
                class="news-image"
                src="${image}"
                alt="${title}"
                loading="lazy"
                referrerpolicy="no-referrer"
            >
        `;
    }


    let descriptionHtml = "";


    if (description) {

        descriptionHtml = `
            <p class="news-description">
                ${description}
            </p>
        `;
    }


    let dateHtml = "";


    if (date) {

        dateHtml = `
            <span class="news-date">
                🕒 ${date}
            </span>
        `;
    }


    article.innerHTML = `

        ${imageHtml}

        <div class="news-content">

            <span class="news-source">
                ${source}
            </span>


            <h2 class="news-title">

                <a
                    class="news-title-link"
                    href="${link}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    ${title}
                </a>

            </h2>


            ${descriptionHtml}


            <div class="news-meta">

                ${dateHtml}


                <span class="news-views">

                    👁️ المشاهدات:
                    <strong>
                        ${articleViews.toLocaleString("ar")}
                    </strong>

                </span>


                <span class="news-reads">

                    📖 القراءات:
                    <strong>
                        ${articleReads.toLocaleString("ar")}
                    </strong>

                </span>

            </div>


            <a
                class="read-more"
                href="${link}"
                target="_blank"
                rel="noopener noreferrer"
            >
                قراءة الخبر
            </a>

        </div>
    `;


    /* =====================================================
       حذف الصورة إذا فشل تحميلها
       ===================================================== */

    const imageElement =
        article.querySelector(
            ".news-image"
        );


    if (imageElement) {

        imageElement.addEventListener(
            "error",
            () => {

                imageElement.remove();

            }
        );
    }


    /* =====================================================
       تسجيل القراءة
       ===================================================== */

    const titleLink =
        article.querySelector(
            ".news-title-link"
        );


    const readMoreLink =
        article.querySelector(
            ".read-more"
        );


    const handleRead =
        () => {

            registerArticleRead(
                item
            );
        };


    if (titleLink) {

        titleLink.addEventListener(
            "click",
            handleRead
        );
    }


    if (readMoreLink) {

        readMoreLink.addEventListener(
            "click",
            handleRead
        );
    }


    return article;
}


/* =========================================================
   عرض الأخبار
   ========================================================= */

function renderNews() {

    /*
     * إيقاف المراقب قبل إزالة البطاقات القديمة.
     */
    if (articleObserver) {

        articleObserver.disconnect();
    }


    newsList.innerHTML = "";


    const sortedNews =
        sortNews(
            allNews
        );


    if (
        sortedNews.length === 0
    ) {

        emptyState.hidden =
            false;

        updateSortButtons();

        return;
    }


    emptyState.hidden =
        true;


    const fragment =
        document.createDocumentFragment();


    for (
        const item
        of sortedNews
    ) {

        fragment.appendChild(
            createNewsCard(item)
        );
    }


    newsList.appendChild(
        fragment
    );


    updateSortButtons();


    /*
     * بعد وضع البطاقات في الصفحة
     * نبدأ مراقبة ما يظهر فعلياً للمستخدم.
     */
    observeNewsCards();
}


/* =========================================================
   تحديث أزرار الترتيب
   ========================================================= */

function updateSortButtons() {

    if (sortNewestButton) {

        sortNewestButton
            .classList
            .toggle(
                "active",
                currentSort ===
                "newest"
            );
    }


    if (sortPopularButton) {

        sortPopularButton
            .classList
            .toggle(
                "active",
                currentSort ===
                "popular"
            );
    }
}


/* =========================================================
   حالة التحميل
   ========================================================= */

function setLoading(
    loading,
    message =
        "جاري تحميل الأخبار..."
) {

    isLoading =
        loading;


    if (statusBox) {

        statusBox.hidden =
            !loading;


        statusBox.textContent =
            message;
    }


    if (refreshButton) {

        refreshButton
            .classList
            .toggle(
                "loading",
                loading
            );


        refreshButton.disabled =
            loading;
    }
}


/* =========================================================
   قراءة الأخبار المحفوظة
   ========================================================= */

function loadCachedNews() {

    try {

        const stored =
            localStorage.getItem(
                STORAGE_KEY
            );


        if (!stored) {

            return false;
        }


        const data =
            JSON.parse(
                stored
            );


        if (
            !Array.isArray(data)
        ) {

            return false;
        }


        allNews =
            data;


        renderNews();


        return true;

    }

    catch (error) {

        console.error(
            "خطأ في قراءة الأخبار المحفوظة:",
            error
        );


        return false;
    }
}


/* =========================================================
   حفظ الأخبار محلياً
   ========================================================= */

function saveNewsToCache(news) {

    try {

        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify(news)
        );

    }

    catch (error) {

        console.warn(
            "تعذر حفظ الأخبار محلياً:",
            error
        );
    }
}


/* =========================================================
   استخراج الأخبار
   ========================================================= */

function extractNews(data) {

    if (
        Array.isArray(data)
    ) {

        return data;
    }


    if (
        data
        &&
        Array.isArray(
            data.news
        )
    ) {

        return data.news;
    }


    if (
        data
        &&
        Array.isArray(
            data.articles
        )
    ) {

        return data.articles;
    }


    if (
        data
        &&
        Array.isArray(
            data.items
        )
    ) {

        return data.items;
    }


    return [];
}


/* =========================================================
   إزالة الأخبار المكررة
   ========================================================= */

function removeDuplicates(news) {

    const result = [];

    const seen =
        new Set();


    for (const item of news) {

        const key =
            getLink(item)
            ||
            getTitle(item);


        if (
            !key
            ||
            seen.has(key)
        ) {

            continue;
        }


        seen.add(
            key
        );


        result.push(
            item
        );
    }


    return result;
}


/* =========================================================
   تحميل الأخبار
   ========================================================= */

async function loadNews(
    forceRefresh = false
) {

    if (isLoading) {

        return;
    }


    setLoading(
        true,
        "جاري تحميل الأخبار..."
    );


    try {

        const separator =
            NEWS_FILE.includes("?")
                ? "&"
                : "?";


        const url =
            forceRefresh

                ? (
                    NEWS_FILE
                    +
                    separator
                    +
                    "t="
                    +
                    Date.now()
                )

                : NEWS_FILE;


        const response =
            await fetch(
                url,
                {
                    cache:
                        forceRefresh
                            ? "no-store"
                            : "default"
                }
            );


        if (
            !response.ok
        ) {

            throw new Error(
                "HTTP "
                +
                response.status
            );
        }


        const data =
            await response.json();


        let news =
            extractNews(
                data
            );


        news =
            removeDuplicates(
                news
            );


        if (
            news.length === 0
        ) {

            throw new Error(
                "ملف الأخبار فارغ"
            );
        }


        allNews =
            news;


        saveNewsToCache(
            allNews
        );


        /*
         * فقط نعرض الأخبار.
         *
         * لم نعد نستدعي registerArticleViews(allNews)
         * لأن ذلك كان يحسب جميع الأخبار كمشاهدة.
         */
        renderNews();

    }

    catch (error) {

        console.error(
            "تعذر تحميل الأخبار:",
            error
        );


        if (
            allNews.length === 0
        ) {

            const cached =
                loadCachedNews();


            if (!cached) {

                emptyState.hidden =
                    false;


                emptyState.textContent =
                    "لم يتم تحميل الأخبار بعد.";
            }
        }
    }

    finally {

        setLoading(
            false
        );
    }
}


/* =========================================================
   زر تحديث الأخبار
   ========================================================= */

if (refreshButton) {

    refreshButton.addEventListener(
        "click",
        async () => {

            await loadNews(
                true
            );
        }
    );
}


/* =========================================================
   زر الأحدث
   ========================================================= */

if (sortNewestButton) {

    sortNewestButton.addEventListener(
        "click",
        () => {

            currentSort =
                "newest";


            localStorage.setItem(
                SORT_KEY,
                currentSort
            );


            renderNews();
        }
    );
}


/* =========================================================
   زر الأكثر قراءة
   ========================================================= */

if (sortPopularButton) {

    sortPopularButton.addEventListener(
        "click",
        () => {

            currentSort =
                "popular";


            localStorage.setItem(
                SORT_KEY,
                currentSort
            );


            renderNews();
        }
    );
}


/* =========================================================
   بدء التطبيق
   ========================================================= */

async function startApp() {

    updateSortButtons();


    listenToGlobalStats();


    listenToArticleStats();


    await registerAppVisit();


    loadCachedNews();


    await loadNews(
        false
    );
}


/* =========================================================
   تشغيل التطبيق
   ========================================================= */

startApp();