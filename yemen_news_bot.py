# -*- coding: utf-8 -*-

import json
import re
import time
from datetime import datetime, timezone, timedelta
from html import unescape
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup


# =========================================================
# نبض اليمن - الإعدادات
# =========================================================

OUTPUT_FILE = "news.json"

# أقصى عدد نأخذه من المصدر في كل تشغيل
MAX_PER_SOURCE = 20

# أقصى عدد إجمالي للأخبار
MAX_TOTAL_NEWS = 1000

# مدة الاحتفاظ بالأخبار داخل نبض اليمن
KEEP_DAYS = 3

REQUEST_TIMEOUT = 15


# =========================================================
# كلمات تدل على أن الخبر متعلق باليمن
# =========================================================

YEMEN_KEYWORDS = [

    "اليمن",
    "اليمني",
    "اليمنية",
    "اليمنيون",
    "اليمنيين",

    "صنعاء",
    "عدن",
    "مأرب",
    "الحديدة",
    "تعز",
    "شبوة",
    "حضرموت",
    "المكلا",
    "المهرة",
    "سقطرى",
    "أبين",
    "ابين",
    "لحج",
    "الضالع",
    "الجوف",
    "صعدة",
    "ذمار",
    "إب",
    "اب",
    "البيضاء",
    "ريمة",
    "حجة",
    "عمران",
    "المخا",

    "باب المندب",
    "مضيق باب المندب",

    "الحوثي",
    "الحوثيين",
    "الحوثيون",
    "الحوثية",

    "أنصار الله",
    "انصار الله",

    "مجلس القيادة الرئاسي",
    "المجلس الرئاسي اليمني",
    "الحكومة اليمنية",

    "المجلس الانتقالي الجنوبي",
    "الانتقالي الجنوبي",

    "القوات اليمنية",
    "الجيش اليمني",
]


# =========================================================
# المصادر العامة التي نريد منها أخبار اليمن فقط
# =========================================================

YEMEN_ONLY_SOURCES = {

    "BBC عربي",
    "الجزيرة",
    "الإخبارية السورية",

}


# =========================================================
# مصادر RSS
# =========================================================

SOURCES = [

    {
        "name": "المشهد اليمني",
        "rss": "https://www.almashhad.news/feed",
        "yemen_only": False,
    },

    {
        "name": "عدن الغد",
        "rss": "https://www.adngad.net/feed",
        "yemen_only": False,
    },

    {
        "name": "الصحوة نت",
        "rss": "https://www.alsahwa-yemen.net/rss",
        "yemen_only": False,
    },

    {
        "name": "قناة بلقيس",
        "rss": "https://belqees.net/rss",
        "yemen_only": False,
    },

    {
        "name": "وكالة سبأ",
        "rss": "https://www.sabanew.net/rss.php?lang=ar",
        "yemen_only": False,
    },

    {
        "name": "BBC عربي",
        "rss": "https://feeds.bbci.co.uk/arabic/rss.xml",
        "yemen_only": True,
    },

]


# =========================================================
# المواقع المباشرة
# =========================================================

WEB_SOURCES = [

    {
        "name": "الجزيرة",
        "url": "https://www.aljazeera.net/",
        "domain": "aljazeera.net",
        "yemen_only": True,
    },

    {
        "name": "الإخبارية السورية",
        "url": "https://alikhbariah.com/",
        "domain": "alikhbariah.com",
        "yemen_only": True,
    },

]


# =========================================================
# إعدادات الاتصال
# =========================================================

HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140 Safari/537.36"
    ),

    "Accept": (
        "text/html,"
        "application/xhtml+xml,"
        "application/xml;q=0.9,"
        "*/*;q=0.8"
    ),

    "Accept-Language":
        "ar,en-US;q=0.8,en;q=0.6",
}


# =========================================================
# وقت دخول الخبر إلى نبض اليمن
#
# مهم:
# هذا ليس تاريخ المصدر.
# هذا هو الوقت الذي اكتشف فيه البوت الخبر لأول مرة.
# =========================================================

def current_app_time():

    return datetime.now(
        timezone.utc
    ).isoformat()


# =========================================================
# تنظيف النص
# =========================================================

def clean_text(text):

    if not text:
        return ""

    text = unescape(
        str(text)
    )

    soup = BeautifulSoup(
        text,
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# توحيد النص العربي
# =========================================================

def normalize_arabic_text(text):

    if not text:
        return ""

    text = clean_text(text)

    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )

    text = (
        text
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
        .replace("ئ", "ي")
        .replace("ؤ", "و")
        .replace("ـ", "")
    )

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# هل الخبر متعلق باليمن؟
# =========================================================

def is_yemen_related(
    title,
    description=""
):

    text = normalize_arabic_text(
        f"{title} {description}"
    )

    if not text:
        return False

    for keyword in YEMEN_KEYWORDS:

        normalized_keyword = (
            normalize_arabic_text(
                keyword
            )
        )

        if not normalized_keyword:
            continue

        # الكلمات المركبة
        if " " in normalized_keyword:

            if normalized_keyword in text:
                return True

            continue

        # كلمة عربية مستقلة
        pattern = (
            r"(?<![\u0600-\u06FF])"
            +
            re.escape(
                normalized_keyword
            )
            +
            r"(?![\u0600-\u06FF])"
        )

        if re.search(
            pattern,
            text
        ):

            return True

    return False


# =========================================================
# تنظيف الرابط
# =========================================================

def normalize_link(link):

    if not link:
        return ""

    link = str(
        link
    ).strip()

    # إزالة الجزء الذي يأتي بعد #
    link = link.split(
        "#",
        1
    )[0]

    return link


# =========================================================
# التحقق من النطاق
# =========================================================

def same_domain(
    link,
    domain
):

    try:

        host = urlparse(
            link
        ).netloc.lower()

    except Exception:

        return False

    domain = domain.lower()

    return (
        host == domain
        or
        host.endswith(
            "." + domain
        )
    )


# =========================================================
# استخراج صورة RSS
# =========================================================

def extract_image(entry):

    candidates = []

    if hasattr(
        entry,
        "media_content"
    ):

        for item in entry.media_content:

            url = item.get(
                "url"
            )

            if url:

                candidates.append(
                    url
                )

    if hasattr(
        entry,
        "media_thumbnail"
    ):

        for item in entry.media_thumbnail:

            url = item.get(
                "url"
            )

            if url:

                candidates.append(
                    url
                )

    if hasattr(
        entry,
        "links"
    ):

        for item in entry.links:

            href = item.get(
                "href"
            )

            typ = item.get(
                "type",
                ""
            )

            if (
                href
                and
                typ.startswith(
                    "image/"
                )
            ):

                candidates.append(
                    href
                )

    if candidates:

        return candidates[0]

    summary = getattr(
        entry,
        "summary",
        ""
    )

    if summary:

        soup = BeautifulSoup(
            summary,
            "html.parser"
        )

        img = soup.find(
            "img"
        )

        if (
            img
            and
            img.get("src")
        ):

            return img["src"]

    return ""


# =========================================================
# قراءة مصدر RSS
# =========================================================

def fetch_source(source):

    name = source["name"]

    rss = source["rss"]

    yemen_only = source.get(
        "yemen_only",
        False
    )

    print("=" * 70)

    print(
        f"🇾🇪 المصدر: {name}"
    )

    print(
        f"RSS: {rss}"
    )

    print(
        f"فلترة اليمن فقط: {'نعم' if yemen_only else 'لا'}"
    )

    print("=" * 70)

    try:

        response = requests.get(
            rss,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except Exception as e:

        print(
            f"❌ فشل الاتصال: {e}"
        )

        return []

    feed = feedparser.parse(
        response.content
    )

    items = []

    # المصادر العامة:
    # نقرأ عدداً أكبر حتى نجد أخبار اليمن.
    if yemen_only:

        entries = feed.entries[
            :100
        ]

    else:

        entries = feed.entries[
            :MAX_PER_SOURCE
        ]

    for entry in entries:

        title = clean_text(
            getattr(
                entry,
                "title",
                ""
            )
        )

        link = normalize_link(
            getattr(
                entry,
                "link",
                ""
            )
        )

        description = clean_text(
            getattr(
                entry,
                "summary",
                getattr(
                    entry,
                    "description",
                    ""
                )
            )
        )

        if (
            not title
            or
            not link
        ):

            continue

        if yemen_only:

            if not is_yemen_related(
                title,
                description
            ):

                continue

        image = extract_image(
            entry
        )

        # -------------------------------------------------
        # وقت نشر الخبر في نبض اليمن
        #
        # هذا الوقت لن يُعتمد إلا إذا كان الخبر جديداً.
        # عند الدمج لاحقاً، الخبر القديم يحتفظ بوقته.
        # -------------------------------------------------

        item = {

            "title":
                title,

            "source":
                name,

            "link":
                link,

            "image":
                image,

            "description":
                description,

            "published_at":
                current_app_time(),

            "views":
                0,
        }

        items.append(
            item
        )

        if (
            len(items)
            >=
            MAX_PER_SOURCE
        ):

            break

    print(
        f"✅ تم العثور على {len(items)} خبراً من {name}"
    )

    return items


# =========================================================
# استخراج الصورة من HTML
# =========================================================

def extract_html_image(
    element,
    base_url
):

    img = element.find(
        "img"
    )

    if (
        not img
        and
        element.parent
    ):

        img = element.parent.find(
            "img"
        )

    if not img:
        return ""

    image = (
        img.get("src")
        or
        img.get("data-src")
        or
        img.get("data-lazy-src")
        or
        ""
    )

    if not image:

        srcset = img.get(
            "srcset",
            ""
        )

        if srcset:

            image = (
                srcset
                .split(",")[0]
                .strip()
                .split(" ")[0]
            )

    if image:

        return urljoin(
            base_url,
            image
        )

    return ""


# =========================================================
# قراءة موقع مباشر
# =========================================================

def fetch_web_source(source):

    name = source["name"]

    url = source["url"]

    domain = source["domain"]

    yemen_only = source.get(
        "yemen_only",
        False
    )

    print("=" * 70)

    print(
        f"🇾🇪 المصدر: {name}"
    )

    print(
        f"WEB: {url}"
    )

    print(
        f"فلترة اليمن فقط: {'نعم' if yemen_only else 'لا'}"
    )

    print("=" * 70)

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except Exception as e:

        print(
            f"❌ فشل الاتصال: {e}"
        )

        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    items = []

    seen = set()

    selectors = [

        "h1 a",
        "h2 a",
        "h3 a",
        "h4 a",
        "article a",

    ]

    links = []

    for selector in selectors:

        links.extend(
            soup.select(
                selector
            )
        )

    for anchor in links:

        title = clean_text(
            anchor.get_text(
                " ",
                strip=True
            )
        )

        href = anchor.get(
            "href",
            ""
        )

        if (
            not title
            or
            not href
        ):

            continue

        if len(title) < 15:
            continue

        link = normalize_link(
            urljoin(
                url,
                href
            )
        )

        if not same_domain(
            link,
            domain
        ):

            continue

        if link in seen:
            continue

        seen.add(
            link
        )

        container = anchor.find_parent(
            [
                "article",
                "div",
                "li"
            ]
        )

        image = ""

        description = ""

        if container:

            image = extract_html_image(
                container,
                url
            )

            paragraph = container.find(
                "p"
            )

            if paragraph:

                description = clean_text(
                    paragraph.get_text(
                        " ",
                        strip=True
                    )
                )

        if yemen_only:

            if not is_yemen_related(
                title,
                description
            ):

                continue

        # -------------------------------------------------
        # لا نفتح صفحة الخبر لمعرفة تاريخ المصدر.
        #
        # ما يهمنا هو وقت دخوله إلى نبض اليمن.
        # -------------------------------------------------

        item = {

            "title":
                title,

            "source":
                name,

            "link":
                link,

            "image":
                image,

            "description":
                description,

            "published_at":
                current_app_time(),

            "views":
                0,
        }

        items.append(
            item
        )

        if (
            len(items)
            >=
            MAX_PER_SOURCE
        ):

            break

    print(
        f"✅ تم العثور على {len(items)} خبراً من {name}"
    )

    return items


# =========================================================
# فلترة نهائية لأخبار اليمن
# =========================================================

def final_yemen_filter(news):

    result = []

    removed = 0

    for item in news:

        source = item.get(
            "source",
            ""
        )

        title = item.get(
            "title",
            ""
        )

        description = item.get(
            "description",
            ""
        )

        # المصادر اليمنية المتخصصة
        # نحتفظ بأخبارها كما هي.
        if source not in YEMEN_ONLY_SOURCES:

            result.append(
                item
            )

            continue

        # المصادر العامة
        # يجب أن يكون الخبر متعلقاً باليمن.
        if is_yemen_related(
            title,
            description
        ):

            result.append(
                item
            )

        else:

            removed += 1

            print(
                f"🗑️ استبعاد خبر غير متعلق باليمن من {source}: {title}"
            )

    print(
        f"🧹 تم استبعاد {removed} خبراً غير متعلق باليمن"
    )

    return result


# =========================================================
# تحميل news.json الحالي
# =========================================================

def load_existing_news():

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(
                f
            )

        if isinstance(
            data,
            list
        ):

            print(
                f"📚 الأخبار الموجودة حالياً: {len(data)}"
            )

            return data

        if (
            isinstance(data, dict)
            and
            isinstance(
                data.get("news"),
                list
            )
        ):

            data = data["news"]

            print(
                f"📚 الأخبار الموجودة حالياً: {len(data)}"
            )

            return data

    except FileNotFoundError:

        print(
            "📚 لا يوجد news.json سابق"
        )

    except Exception as e:

        print(
            f"⚠️ تعذر قراءة news.json: {e}"
        )

    return []


# =========================================================
# إنشاء مفتاح للخبر
# =========================================================

def news_key(item):

    link = normalize_link(
        item.get(
            "link",
            ""
        )
    )

    if link:

        return (
            "link:",
            link
        )

    title = normalize_arabic_text(
        item.get(
            "title",
            ""
        )
    )

    return (
        "title:",
        title
    )


# =========================================================
# دمج الأخبار القديمة والجديدة
#
# النقطة الأهم:
#
# إذا كان الخبر موجوداً من قبل، نحتفظ بالنسخة القديمة
# وبالتالي يبقى published_at كما كان عند دخوله لأول مرة.
#
# لا يتغير الوقت مع كل تشغيل.
# =========================================================

def merge_news(
    old_news,
    fetched_news
):

    result = []

    existing_keys = set()

    existing_titles = set()

    # -----------------------------------------------------
    # أولاً: الأخبار الموجودة في التطبيق
    # -----------------------------------------------------

    for item in old_news:

        key = news_key(
            item
        )

        title = normalize_arabic_text(
            item.get(
                "title",
                ""
            )
        )

        if key in existing_keys:
            continue

        if (
            title
            and
            title in existing_titles
        ):
            continue

        existing_keys.add(
            key
        )

        if title:

            existing_titles.add(
                title
            )

        result.append(
            item
        )

    # -----------------------------------------------------
    # ثانياً: الأخبار التي وجدناها الآن
    # -----------------------------------------------------

    added = 0

    repeated = 0

    for item in fetched_news:

        key = news_key(
            item
        )

        title = normalize_arabic_text(
            item.get(
                "title",
                ""
            )
        )

        # الخبر موجود من قبل
        if key in existing_keys:

            repeated += 1
            continue

        # حماية إضافية إذا تغيّر الرابط وبقي العنوان نفسه
        if (
            title
            and
            title in existing_titles
        ):

            repeated += 1
            continue

        existing_keys.add(
            key
        )

        if title:

            existing_titles.add(
                title
            )

        # published_at هنا هو وقت اكتشاف الخبر
        # لأول مرة في نبض اليمن.
        result.append(
            item
        )

        added += 1

    print(
        f"🆕 أخبار جديدة أضيفت إلى نبض اليمن: {added}"
    )

    print(
        f"🔁 أخبار مكررة لم تتم إضافتها: {repeated}"
    )

    return result


# =========================================================
# قراءة وقت الخبر داخل نبض اليمن
# =========================================================

def get_news_datetime(item):

    value = item.get(
        "published_at",
        ""
    )

    if not value:
        return None

    try:

        value = str(
            value
        ).strip()

        if value.endswith(
            "Z"
        ):

            value = (
                value[:-1]
                +
                "+00:00"
            )

        dt = datetime.fromisoformat(
            value
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    except Exception:

        return None


# =========================================================
# حذف الأخبار التي تجاوزت 3 أيام
#
# الثلاثة أيام تحسب من وقت دخول الخبر إلى نبض اليمن،
# وليس من تاريخ نشره في المصدر.
# =========================================================

def remove_old_news(news):

    now = datetime.now(
        timezone.utc
    )

    cutoff = (
        now
        -
        timedelta(
            days=KEEP_DAYS
        )
    )

    result = []

    removed = 0

    for item in news:

        dt = get_news_datetime(
            item
        )

        # خبر قديم لا يحتوي وقتاً صالحاً:
        # نحذفه حتى لا يبقى إلى الأبد.
        if dt is None:

            removed += 1
            continue

        if dt < cutoff:

            removed += 1
            continue

        result.append(
            item
        )

    print(
        f"🗑️ أخبار حُذفت لتجاوزها {KEEP_DAYS} أيام: {removed}"
    )

    return result


# =========================================================
# ترتيب الأخبار
#
# الأحدث في نبض اليمن أولاً
# =========================================================

def sort_news(news):

    minimum_date = datetime.min.replace(
        tzinfo=timezone.utc
    )

    news.sort(

        key=lambda item:
            (
                get_news_datetime(
                    item
                )
                or
                minimum_date
            ),

        reverse=True

    )

    return news


# =========================================================
# الحد الأقصى 1000 خبر
# =========================================================

def limit_news(news):

    if (
        len(news)
        <=
        MAX_TOTAL_NEWS
    ):

        return news

    removed = (
        len(news)
        -
        MAX_TOTAL_NEWS
    )

    print(
        f"✂️ تم حذف {removed} خبراً لتطبيق حد {MAX_TOTAL_NEWS} خبر"
    )

    # الأخبار مرتبة مسبقاً من الأحدث إلى الأقدم.
    return news[
        :MAX_TOTAL_NEWS
    ]


# =========================================================
# حفظ news.json
# =========================================================

def save_news(news):

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            news,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()

    print("=" * 70)

    print(
        f"💾 تم حفظ {len(news)} خبراً في {OUTPUT_FILE}"
    )

    print("=" * 70)


# =========================================================
# البرنامج الرئيسي
# =========================================================

def main():

    print()

    print("=" * 70)

    print(
        "🇾🇪 نبض اليمن - جلب أخبار اليمن"
    )

    print("=" * 70)

    print()

    # -----------------------------------------------------
    # 1. قراءة الأخبار الموجودة
    # -----------------------------------------------------

    old_news = load_existing_news()

    # -----------------------------------------------------
    # 2. جمع الأخبار الموجودة حالياً في المصادر
    # -----------------------------------------------------

    fetched_news = []

    for source in SOURCES:

        items = fetch_source(
            source
        )

        fetched_news.extend(
            items
        )

        time.sleep(
            0.4
        )

    for source in WEB_SOURCES:

        items = fetch_web_source(
            source
        )

        fetched_news.extend(
            items
        )

        time.sleep(
            0.4
        )

    print()

    print(
        f"📥 الأخبار التي عُثر عليها في هذه الدورة: {len(fetched_news)}"
    )

    # -----------------------------------------------------
    # 3. فلترة اليمن
    # -----------------------------------------------------

    fetched_news = final_yemen_filter(
        fetched_news
    )

    print(
        f"🇾🇪 بعد فلترة اليمن: {len(fetched_news)}"
    )

    # -----------------------------------------------------
    # 4. دمج الجديد مع الموجود
    #
    # هنا يتم تثبيت وقت الخبر.
    # الخبر الموجود لا يحصل على وقت جديد.
    # -----------------------------------------------------

    all_news = merge_news(
        old_news,
        fetched_news
    )

    # -----------------------------------------------------
    # 5. حذف الأخبار التي تجاوزت 3 أيام
    # -----------------------------------------------------

    all_news = remove_old_news(
        all_news
    )

    # -----------------------------------------------------
    # 6. ترتيبها حسب وقت دخولها إلى نبض اليمن
    # -----------------------------------------------------

    all_news = sort_news(
        all_news
    )

    # -----------------------------------------------------
    # 7. عدم تجاوز 1000 خبر
    # -----------------------------------------------------

    all_news = limit_news(
        all_news
    )

    # -----------------------------------------------------
    # 8. الحفظ
    # -----------------------------------------------------

    save_news(
        all_news
    )

    print()

    print(
        "✅ انتهى تحديث نبض اليمن بنجاح"
    )

    print()


# =========================================================
# التشغيل
# =========================================================

if __name__ == "__main__":

    main()