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
    get,
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
   العناصر
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


/* =========================================================
   المتغيرات
   ========================================================= */

let allNews = [];

let currentSort =
    localStorage.getItem(SORT_KEY)
    || "newest";

let isLoading = false;

let articleReads = {};


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
   تحويل التاريخ
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

            if (value < 1000000000000) {
                return value * 1000;
            }

            return value;
        }

        const parsed =
            Date.parse(value);

        if (!Number.isNaN(parsed)) {
            return parsed;
        }

    }

    return 0;
}


/* =========================================================
   معرفة المصدر
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
   عنوان الخبر
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
   رابط الخبر
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
   صورة الخبر
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
   وصف الخبر
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
   إنشاء رقم ثابت لكل خبر
   ========================================================= */

function getArticleId(item) {

    const text =
        getLink(item)
        ||
        getTitle(item);

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
   عدد القراءات
   ========================================================= */

function getViews(item) {

    const articleId =
        getArticleId(item);

    const firebaseReads =
        articleReads[articleId]?.reads;

    if (
        firebaseReads !== undefined
        &&
        firebaseReads !== null
    ) {

        return (
            Number(firebaseReads)
            ||
            0
        );
    }


    const value =
        item.views
        ?? item.reads
        ?? item.view_count
        ?? item.clicks
        ?? 0;

    const number =
        Number(value);

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

async function incrementCounter(
    path
) {

    try {

        await runTransaction(
            ref(
                database,
                path
            ),
            currentValue => {

                return (
                    Number(
                        currentValue
                    )
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
   تسجيل الزيارة وفتح التطبيق
   ========================================================= */

async function registerAppVisit() {

    await incrementCounter(
        "stats/views"
    );


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
   متابعة قراءات الأخبار من Firebase
   ========================================================= */

function listenToArticleReads() {

    onValue(
        ref(
            database,
            "articles"
        ),
        snapshot => {

            articleReads =
                snapshot.val()
                ||
                {};

            renderNews();
        },
        error => {

            console.error(
                "تعذر قراءة عدادات الأخبار:",
                error
            );
        }
    );
}


/* =========================================================
   تسجيل قراءة خبر
   ========================================================= */

async function registerArticleRead(
    item
) {

    const articleId =
        getArticleId(item);

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


    /* -----------------------------------------
       الأكثر قراءة
       ----------------------------------------- */

    if (
        currentSort ===
        "popular"
    ) {

        copy.sort(
            (a, b) => {

                const viewsDifference =
                    getViews(b)
                    -
                    getViews(a);

                if (
                    viewsDifference !== 0
                ) {

                    return viewsDifference;
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


    /* -----------------------------------------
       الأحدث
       ----------------------------------------- */

    copy.sort(
        (a, b) =>
            getTimeValue(b)
            -
            getTimeValue(a)
    );

    return copy;
}


/* =========================================================
   بطاقة الخبر
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

    const views =
        getViews(item);


    const article =
        document.createElement(
            "article"
        );

    article.className =
        "news-card";


    /* -----------------------------------------
       الصورة
       ----------------------------------------- */

    let imageHtml = "";

    if (image) {

        imageHtml = `
            <img
                class="news-image"
                src="${image}"
                alt="${title}"
                loading="lazy"
                referrerpolicy="no-referrer"
                onerror="this.style.display='none'"
            >
        `;
    }


    /* -----------------------------------------
       الوصف
       ----------------------------------------- */

    let descriptionHtml = "";

    if (description) {

        descriptionHtml = `
            <p class="news-description">
                ${description}
            </p>
        `;
    }


    /* -----------------------------------------
       التاريخ
       ----------------------------------------- */

    let dateHtml = "";

    if (date) {

        dateHtml = `
            <span class="news-date">
                🕒 ${date}
            </span>
        `;
    }


    /* -----------------------------------------
       القراءات
       ----------------------------------------- */

    let viewsHtml = "";

    if (views > 0) {

        viewsHtml = `
            <span class="news-views">
                👁️ ${views.toLocaleString("ar")}
            </span>
        `;
    }


    /* -----------------------------------------
       HTML النهائي
       ----------------------------------------- */

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

                ${viewsHtml}

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

    newsList.innerHTML = "";


    const sortedNews =
        sortNews(allNews);


    if (
        sortedNews.length === 0
    ) {

        emptyState.hidden =
            false;

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
}


/* =========================================================
   تحديث شكل أزرار الترتيب
   ========================================================= */

function updateSortButtons() {

    sortNewestButton
        .classList
        .toggle(
            "active",
            currentSort ===
            "newest"
        );


    sortPopularButton
        .classList
        .toggle(
            "active",
            currentSort ===
            "popular"
        );
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


    statusBox.hidden =
        !loading;


    statusBox.textContent =
        message;


    refreshButton
        .classList
        .toggle(
            "loading",
            loading
        );


    refreshButton.disabled =
        loading;
}


/* =========================================================
   قراءة النسخة المحفوظة
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
            JSON.parse(stored);


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
   استخراج الأخبار من JSON
   ========================================================= */

function extractNews(data) {

    if (
        Array.isArray(data)
    ) {

        return data;
    }


    if (
        data &&
        Array.isArray(data.news)
    ) {

        return data.news;
    }


    if (
        data &&
        Array.isArray(data.articles)
    ) {

        return data.articles;
    }


    if (
        data &&
        Array.isArray(data.items)
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


    for (
        const item
        of news
    ) {

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


        seen.add(key);

        result.push(item);
    }


    return result;
}


/* =========================================================
   جلب الأخبار
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


        if (!response.ok) {

            throw new Error(
                "HTTP "
                +
                response.status
            );
        }


        const data =
            await response.json();


        let news =
            extractNews(data);


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

        setLoading(false);
    }
}


/* =========================================================
   زر التحديث
   ========================================================= */

refreshButton
    .addEventListener(
        "click",
        async () => {

            await loadNews(true);

        }
    );


/* =========================================================
   زر الأحدث
   ========================================================= */

sortNewestButton
    .addEventListener(
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


/* =========================================================
   زر الأكثر قراءة
   ========================================================= */

sortPopularButton
    .addEventListener(
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


/* =========================================================
   بدء التطبيق
   ========================================================= */

async function startApp() {

    updateSortButtons();


    /*
     * نسجل فتح التطبيق والزيارة
     */

    registerAppVisit();


    /*
     * نبدأ متابعة قراءات الأخبار.
     */

    listenToArticleReads();


    /*
     * نعرض النسخة المحفوظة فوراً
     * إن كانت موجودة.
     */

    loadCachedNews();


    /*
     * ثم نطلب النسخة الأحدث.
     */

    await loadNews(false);
}


/* =========================================================
   تشغيل التطبيق
   ========================================================= */

startApp();