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
# الإعدادات
# =========================================================

OUTPUT_FILE = "news.json"

MAX_PER_SOURCE = 20

MAX_TOTAL_NEWS = 1000

KEEP_DAYS = 3

REQUEST_TIMEOUT = 15


# =========================================================
# كلمات واضحة تدل على أن الخبر متعلق باليمن
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
# المصادر العامة التي نأخذ منها أخبار اليمن فقط
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
# Headers
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
    )

    text = (
        text
        .replace("ى", "ي")
        .replace("ئ", "ي")
    )

    text = text.replace(
        "ؤ",
        "و"
    )

    text = text.replace(
        "ـ",
        ""
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

        if " " in normalized_keyword:

            if normalized_keyword in text:
                return True

            continue

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

    return str(
        link
    ).strip()


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
# تحويل التاريخ إلى UTC
# =========================================================

def normalize_datetime(value):

    if not value:
        return ""

    try:

        value = str(
            value
        ).strip()

        if value.endswith("Z"):

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

        dt = dt.astimezone(
            timezone.utc
        )

        return dt.isoformat()

    except Exception:

        return ""


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
# استخراج التاريخ الحقيقي من RSS
# =========================================================

def parse_date(entry):

    possible_dates = (

        "published_parsed",
        "updated_parsed",

    )

    for attr in possible_dates:

        value = getattr(
            entry,
            attr,
            None
        )

        if value:

            try:

                dt = datetime(
                    *value[:6],
                    tzinfo=timezone.utc
                )

                return dt.isoformat()

            except Exception:

                pass

    # -----------------------------------------------------
    # نحاول النص الأصلي للتاريخ
    # -----------------------------------------------------

    for attr in (
        "published",
        "updated"
    ):

        value = getattr(
            entry,
            attr,
            None
        )

        if not value:
            continue

        try:

            parsed = feedparser._parse_date(
                value
            )

            if parsed:

                dt = datetime(
                    *parsed[:6],
                    tzinfo=timezone.utc
                )

                return dt.isoformat()

        except Exception:

            pass

    # -----------------------------------------------------
    # مهم:
    # لا نعطي الخبر الوقت الحالي
    # إذا لم نجد تاريخاً حقيقياً
    # -----------------------------------------------------

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
        f"المصدر: {name}"
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

        published_at = parse_date(
            entry
        )

        # -------------------------------------------------
        # إذا لم يقدم RSS تاريخاً حقيقياً
        # لا نخترع تاريخاً للخبر
        # -------------------------------------------------

        if not published_at:

            print(
                f"⚠️ لا يوجد تاريخ موثوق: {title}"
            )

            continue

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
                published_at,

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
        f"✅ تم استخراج {len(items)} خبراً من {name}"
    )

    return items


# =========================================================
# استخراج صورة من HTML
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
# البحث عن تاريخ النشر في JSON-LD
# =========================================================

def extract_json_ld_date(soup):

    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    def search_object(obj):

        if isinstance(
            obj,
            dict
        ):

            for key in (
                "datePublished",
                "dateCreated"
            ):

                if obj.get(key):

                    result = normalize_datetime(
                        obj.get(key)
                    )

                    if result:
                        return result

            for value in obj.values():

                result = search_object(
                    value
                )

                if result:
                    return result

        elif isinstance(
            obj,
            list
        ):

            for value in obj:

                result = search_object(
                    value
                )

                if result:
                    return result

        return ""

    for script in scripts:

        try:

            data = json.loads(
                script.string
                or
                script.get_text()
            )

            result = search_object(
                data
            )

            if result:
                return result

        except Exception:

            continue

    return ""


# =========================================================
# استخراج تاريخ النشر من صفحة الخبر
# =========================================================

def extract_article_date(
    article_url
):

    try:

        response = requests.get(
            article_url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except Exception as e:

        print(
            f"⚠️ تعذر فتح صفحة الخبر لمعرفة التاريخ: {e}"
        )

        return ""

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # -----------------------------------------------------
    # 1. meta article:published_time
    # -----------------------------------------------------

    selectors = [

        (
            "meta",
            {
                "property":
                    "article:published_time"
            },
            "content"
        ),

        (
            "meta",
            {
                "name":
                    "article:published_time"
            },
            "content"
        ),

        (
            "meta",
            {
                "itemprop":
                    "datePublished"
            },
            "content"
        ),

        (
            "meta",
            {
                "name":
                    "date"
            },
            "content"
        ),

        (
            "meta",
            {
                "name":
                    "pubdate"
            },
            "content"
        ),

    ]

    for (
        tag_name,
        attrs,
        attribute
    ) in selectors:

        tag = soup.find(
            tag_name,
            attrs=attrs
        )

        if (
            tag
            and
            tag.get(attribute)
        ):

            result = normalize_datetime(
                tag.get(attribute)
            )

            if result:
                return result

    # -----------------------------------------------------
    # 2. عنصر time
    # -----------------------------------------------------

    time_tag = soup.find(
        "time"
    )

    if time_tag:

        value = (
            time_tag.get(
                "datetime"
            )
            or
            time_tag.get_text(
                " ",
                strip=True
            )
        )

        result = normalize_datetime(
            value
        )

        if result:
            return result

    # -----------------------------------------------------
    # 3. JSON-LD
    # -----------------------------------------------------

    result = extract_json_ld_date(
        soup
    )

    if result:
        return result

    return ""


# =========================================================
# قراءة موقع إخباري مباشر
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
        f"المصدر: {name}"
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

        link = urljoin(
            url,
            href
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
        # استخراج تاريخ النشر الحقيقي من صفحة الخبر
        # -------------------------------------------------

        published_at = extract_article_date(
            link
        )

        if not published_at:

            print(
                f"⚠️ تم تجاهل خبر لعدم العثور على تاريخ نشر موثوق:"
            )

            print(
                f"   {title}"
            )

            continue

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
                published_at,

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

        time.sleep(
            0.2
        )

    print(
        f"✅ تم استخراج {len(items)} خبراً من {name}"
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

        if source not in YEMEN_ONLY_SOURCES:

            result.append(
                item
            )

            continue

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
                f"🗑️ استبعاد خبر غير يمني من {source}: {title}"
            )

    print()

    print(
        f"🧹 تم حذف {removed} خبراً غير متعلق باليمن"
    )

    return result


# =========================================================
# قراءة الأخبار القديمة من news.json
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
                f"📚 تم تحميل {len(data)} خبراً محفوظاً"
            )

            return data

    except FileNotFoundError:

        print(
            "📚 لا يوجد ملف أخبار سابق"
        )

    except Exception as e:

        print(
            f"⚠️ تعذر قراءة الأخبار السابقة: {e}"
        )

    return []


# =========================================================
# إزالة التكرار مع الحفاظ على النسخة القديمة
#
# إذا كان الخبر موجوداً من قبل:
# نحافظ على بياناته القديمة وخاصة تاريخ النشر.
# =========================================================

def merge_news(
    old_news,
    new_news
):

    result = []

    links = set()

    titles = set()

    # -----------------------------------------------------
    # الأخبار القديمة أولاً
    # -----------------------------------------------------

    for item in old_news:

        link = normalize_link(
            item.get(
                "link",
                ""
            )
        )

        title = normalize_arabic_text(
            item.get(
                "title",
                ""
            )
        )

        if (
            link
            and
            link in links
        ):

            continue

        if (
            title
            and
            title in titles
        ):

            continue

        if link:
            links.add(link)

        if title:
            titles.add(title)

        result.append(
            item
        )

    # -----------------------------------------------------
    # إضافة الأخبار الجديدة فقط
    # -----------------------------------------------------

    added = 0

    for item in new_news:

        link = normalize_link(
            item.get(
                "link",
                ""
            )
        )

        title = normalize_arabic_text(
            item.get(
                "title",
                ""
            )
        )

        if (
            link
            and
            link in links
        ):

            continue

        if (
            title
            and
            title in titles
        ):

            continue

        if link:
            links.add(link)

        if title:
            titles.add(title)

        result.append(
            item
        )

        added += 1

    print(
        f"🆕 تمت إضافة {added} أخبار جديدة"
    )

    return result


# =========================================================
# تحويل published_at إلى datetime
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
        ).replace(
            "Z",
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
# حذف الأخبار الأقدم من ثلاثة أيام
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

        # -------------------------------------------------
        # لا نحتفظ بخبر بلا تاريخ موثوق
        # -------------------------------------------------

        if dt is None:

            removed += 1

            continue

        if dt < cutoff:

            removed += 1

            continue

        # -------------------------------------------------
        # حماية من تاريخ مستقبلي غير منطقي
        # -------------------------------------------------

        if dt > (
            now
            +
            timedelta(
                hours=6
            )
        ):

            removed += 1

            continue

        result.append(
            item
        )

    print(
        f"🗑️ تم حذف {removed} خبراً أقدم من {KEEP_DAYS} أيام أو بتاريخ غير صالح"
    )

    return result


# =========================================================
# ترتيب الأخبار حسب تاريخ النشر الحقيقي
# =========================================================

def sort_news(news):

    def key(item):

        dt = get_news_datetime(
            item
        )

        if dt is None:

            return datetime.min.replace(
                tzinfo=timezone.utc
            )

        return dt

    news.sort(
        key=key,
        reverse=True
    )

    return news


# =========================================================
# تحديد الحد الأقصى 1000 خبر
# =========================================================

def limit_news(news):

    if (
        len(news)
        <=
        MAX_TOTAL_NEWS
    ):

        return news

    print(
        f"✂️ تجاوز العدد {MAX_TOTAL_NEWS} خبر، سيتم الاحتفاظ بالأحدث فقط"
    )

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
        f"✅ تم حفظ {len(news)} خبراً في {OUTPUT_FILE}"
    )

    print("=" * 70)


# =========================================================
# التشغيل الرئيسي
# =========================================================

def main():

    print()

    print("=" * 70)

    print(
        "🇾🇪 نبض اليمن - جلب أخبار اليمن"
    )

    print("=" * 70)

    print()

    # =====================================================
    # قراءة الأخبار المحفوظة أولاً
    # =====================================================

    old_news = load_existing_news()

    new_news = []

    # =====================================================
    # RSS
    # =====================================================

    for source in SOURCES:

        items = fetch_source(
            source
        )

        new_news.extend(
            items
        )

        time.sleep(
            0.5
        )

    # =====================================================
    # المواقع المباشرة
    # =====================================================

    for source in WEB_SOURCES:

        items = fetch_web_source(
            source
        )

        new_news.extend(
            items
        )

        time.sleep(
            0.5
        )

    print()

    print(
        f"📥 تم جلب {len(new_news)} خبراً في هذه الدورة"
    )

    # =====================================================
    # فلترة أخبار اليمن
    # =====================================================

    new_news = final_yemen_filter(
        new_news
    )

    print(
        f"🇾🇪 بعد الفلترة: {len(new_news)} خبراً"
    )

    # =====================================================
    # دمج القديم مع الجديد ومنع التكرار
    # =====================================================

    all_news = merge_news(
        old_news,
        new_news
    )

    print(
        f"🔁 العدد بعد الدمج ومنع التكرار: {len(all_news)}"
    )

    # =====================================================
    # حذف ما تجاوز ثلاثة أيام
    # =====================================================

    all_news = remove_old_news(
        all_news
    )

    # =====================================================
    # ترتيب حسب تاريخ النشر الحقيقي
    # =====================================================

    all_news = sort_news(
        all_news
    )

    # =====================================================
    # الحد الأقصى 1000 خبر
    # =====================================================

    all_news = limit_news(
        all_news
    )

    # =====================================================
    # الحفظ
    # =====================================================

    save_news(
        all_news
    )


# =========================================================
# بدء البرنامج
# =========================================================

if __name__ == "__main__":

    main()