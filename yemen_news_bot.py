# -*- coding: utf-8 -*-

import json
import re
import time
from datetime import datetime, timezone
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

REQUEST_TIMEOUT = 15


# =========================================================
# كلمات واضحة تدل على أن الخبر متعلق باليمن
# ملاحظة:
# لا نستخدم الكلمة العامة "يمن"
# حتى لا نحصل على تطابقات خاطئة
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
    "الحوثيين",

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
# المصادر العامة التي لا نريد منها إلا أخبار اليمن
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

    # -----------------------------------------------------
    # 🇾🇪 مصادر يمنية
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # 🌍 مصادر عربية ودولية
    # لا نأخذ منها إلا الأخبار المتعلقة باليمن
    # -----------------------------------------------------

    {
        "name": "BBC عربي",
        "rss": "https://feeds.bbci.co.uk/arabic/rss.xml",
        "yemen_only": True,
    },

]


# =========================================================
# المصادر التي نقرأها مباشرة من الموقع
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
        "image/avif,"
        "image/webp,"
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
# توحيد الحروف العربية
# يساعد على مطابقة الكلمات بصورة أفضل
# =========================================================

def normalize_arabic_text(text):

    if not text:

        return ""


    text = clean_text(
        text
    )


    # إزالة التشكيل

    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )


    # توحيد أشكال الألف

    text = (
        text
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
    )


    # توحيد الياء والألف المقصورة

    text = (
        text
        .replace("ى", "ي")
        .replace("ئ", "ي")
    )


    # توحيد الواو بالهمزة

    text = text.replace(
        "ؤ",
        "و"
    )


    # إزالة التطويل

    text = text.replace(
        "ـ",
        ""
    )


    # تحويل للحروف الصغيرة

    text = text.lower()


    # توحيد المسافات

    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip()


# =========================================================
# فحص هل الخبر متعلق باليمن
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


        # -----------------------------------------------
        # الكلمات المركبة مثل:
        # باب المندب
        # مجلس القيادة الرئاسي
        # -----------------------------------------------

        if " " in normalized_keyword:

            if normalized_keyword in text:

                return True

            continue


        # -----------------------------------------------
        # الكلمات المفردة:
        # نبحث عنها ككلمة كاملة قدر الإمكان
        # -----------------------------------------------

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
# استخراج صورة RSS
# =========================================================

def extract_image(entry):

    candidates = []


    # -----------------------------------------------------
    # media_content
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # media_thumbnail
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # روابط من نوع صورة
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # محاولة استخراج صورة من الوصف
    # -----------------------------------------------------

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
# استخراج التاريخ
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


    return datetime.now(
        timezone.utc
    ).isoformat()


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


    # نقرأ عدداً أكبر قليلاً للمصادر العامة
    # لأن كثيراً من الأخبار سيتم استبعادها

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


        # -------------------------------------------------
        # المصادر العامة:
        # لا نقبل الخبر إلا إذا كان متعلقاً باليمن
        # -------------------------------------------------

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


    if yemen_only:

        print(
            f"✅ تم استخراج {len(items)} خبراً متعلقاً باليمن"
        )

    else:

        print(
            f"✅ تم استخراج {len(items)} خبراً"
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
# قراءة موقع إخباري مباشرة
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


        # تجاهل العناوين القصيرة

        if len(title) < 15:

            continue


        link = urljoin(
            url,
            href
        )


        # يجب أن يكون الرابط من نفس الموقع

        if not same_domain(
            link,
            domain
        ):

            continue


        # منع تكرار الرابط

        if link in seen:

            continue


        seen.add(
            link
        )


        # -------------------------------------------------
        # العنصر الحاوي للخبر
        # -------------------------------------------------

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


        # -------------------------------------------------
        # فلترة المصادر العامة
        # -------------------------------------------------

        if yemen_only:

            if not is_yemen_related(
                title,
                description
            ):

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
                datetime.now(
                    timezone.utc
                ).isoformat(),

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


    if yemen_only:

        print(
            f"✅ تم استخراج {len(items)} خبراً متعلقاً باليمن"
        )

    else:

        print(
            f"✅ تم استخراج {len(items)} خبراً"
        )


    return items


# =========================================================
# فلترة نهائية
#
# هذه أهم طبقة حماية:
# أي خبر قادم من مصدر عام
# يجب أن يكون متعلقاً باليمن
# حتى لو مر من مرحلة سابقة
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


        # -------------------------------------------------
        # المصدر اليمني:
        # نترك خبره كما هو
        # -------------------------------------------------

        if source not in YEMEN_ONLY_SOURCES:

            result.append(
                item
            )

            continue


        # -------------------------------------------------
        # المصدر العام:
        # لا بد أن يكون الخبر متعلقاً باليمن
        # -------------------------------------------------

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
        f"🧹 الفلترة النهائية: تم حذف {removed} خبراً غير متعلق باليمن"
    )


    return result


# =========================================================
# إزالة التكرار
# =========================================================

def remove_duplicates(news):

    result = []

    seen_links = set()

    seen_titles = set()


    for item in news:

        link = item.get(
            "link",
            ""
        ).strip()


        title = normalize_arabic_text(
            item.get(
                "title",
                ""
            )
        )


        if (
            link
            and
            link in seen_links
        ):

            continue


        if (
            title
            and
            title in seen_titles
        ):

            continue


        if link:

            seen_links.add(
                link
            )


        if title:

            seen_titles.add(
                title
            )


        result.append(
            item
        )


    return result


# =========================================================
# ترتيب الأخبار
# =========================================================

def sort_news(news):

    def key(item):

        value = item.get(
            "published_at",
            ""
        )


        try:

            return datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00"
                )
            )


        except Exception:

            return datetime.min.replace(
                tzinfo=timezone.utc
            )


    news.sort(
        key=key,
        reverse=True
    )


    return news


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

    all_news = []


    print()

    print("=" * 70)

    print(
        "🇾🇪 نبض اليوم - جلب أخبار اليمن"
    )

    print("=" * 70)

    print()


    # =====================================================
    # RSS
    # =====================================================

    for source in SOURCES:

        items = fetch_source(
            source
        )


        all_news.extend(
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


        all_news.extend(
            items
        )


        time.sleep(
            0.5
        )


    print()

    print(
        f"📥 العدد قبل الفلترة النهائية: {len(all_news)}"
    )


    # =====================================================
    # فلترة نهائية للمصادر العامة
    # =====================================================

    all_news = final_yemen_filter(
        all_news
    )


    print(
        f"🇾🇪 العدد بعد فلترة أخبار اليمن: {len(all_news)}"
    )


    # =====================================================
    # إزالة الأخبار المكررة
    # =====================================================

    all_news = remove_duplicates(
        all_news
    )


    print(
        f"🔁 العدد بعد إزالة التكرار: {len(all_news)}"
    )


    # =====================================================
    # ترتيب الأحدث أولاً
    # =====================================================

    all_news = sort_news(
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