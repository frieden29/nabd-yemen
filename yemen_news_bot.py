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
# كلمات تدل على أن الخبر متعلق باليمن
# =========================================================

YEMEN_KEYWORDS = [

    "اليمن",
    "يمن",

    "اليمني",
    "اليمنية",
    "اليمنيين",
    "اليمنيون",

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
    "لحج",
    "الضالع",
    "الجوف",
    "صعدة",
    "ذمار",
    "إب",
    "البيضاء",
    "ريمة",
    "حجة",
    "عمران",
    "المخا",

    "باب المندب",
    "مضيق باب المندب",

    "البحر الأحمر",

    "الحوثي",
    "الحوثيين",
    "الحوثيون",
    "الحوثية",

    "أنصار الله",

    "مجلس القيادة الرئاسي",
    "الحكومة اليمنية",

    "الرئاسي اليمني",

    "القوات اليمنية",

    "الجيش اليمني",

    "السواحل اليمنية",

    "المياه اليمنية",

    "الموانئ اليمنية",

    "ميناء الحديدة",
    "ميناء عدن",
    "ميناء المخا",

]


# =========================================================
# المصادر التي يجب أن تكون أخبارها عن اليمن فقط
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

    # =====================================================
    # مصادر يمنية
    # =====================================================

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


    # =====================================================
    # مصادر عربية ودولية
    # لا نأخذ منها إلا الأخبار المتعلقة باليمن
    # =====================================================

    {
        "name": "BBC عربي",
        "rss": "https://feeds.bbci.co.uk/arabic/rss.xml",
        "yemen_only": True,
    },

]


# =========================================================
# المصادر التي نقرأها مباشرة من صفحات الموقع
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
# تنظيف الرابط
# =========================================================

def normalize_link(link):

    if not link:
        return ""

    return str(
        link
    ).strip()


# =========================================================
# فحص اسم النطاق
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
# توحيد النص العربي للمقارنة
# =========================================================

def normalize_arabic_text(text):

    text = clean_text(
        text
    ).lower()

    replacements = {

        "أ": "ا",
        "إ": "ا",
        "آ": "ا",

        "ى": "ي",

        "ؤ": "و",

        "ئ": "ي",

        "ة": "ه",

    }


    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )


    # حذف التشكيل

    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )


    return text


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


    for keyword in YEMEN_KEYWORDS:

        normalized_keyword = (
            normalize_arabic_text(
                keyword
            )
        )


        if normalized_keyword in text:

            return True


    return False


# =========================================================
# استخراج صورة من RSS
# =========================================================

def extract_image(entry):

    candidates = []


    # media_content

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


    # media_thumbnail

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


    # روابط الصور

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


    # صورة داخل الوصف

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
# قراءة التاريخ
# =========================================================

def parse_date(entry):

    for attr in (

        "published_parsed",

        "updated_parsed",

    ):

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

    checked = 0


    # نقرأ عدداً أكبر من العناصر للمصادر العامة
    # حتى نجد أخبار اليمن بينها

    entries = feed.entries


    if not yemen_only:

        entries = entries[
            :MAX_PER_SOURCE
        ]


    for entry in entries:

        checked += 1


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


        # =================================================
        # فلترة المصادر العامة
        # =================================================

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
            f"✅ تم استخراج {len(items)} خبراً يمنياً"
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
# استخراج الوصف من محيط الخبر
# =========================================================

def extract_html_description(
    anchor
):

    container = anchor.find_parent(
        [
            "article",
            "div",
            "li",
        ]
    )


    if not container:

        return ""


    paragraph = container.find(
        "p"
    )


    if not paragraph:

        return ""


    return clean_text(
        paragraph.get_text(
            " ",
            strip=True
        )
    )


# =========================================================
# قراءة مصدر ويب
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


        description = (
            extract_html_description(
                anchor
            )
        )


        # =================================================
        # فلترة الأخبار
        # =================================================

        if yemen_only:

            if not is_yemen_related(
                title,
                description
            ):

                continue


        container = anchor.find_parent(
            [
                "article",
                "div",
                "li",
            ]
        )


        image = ""


        if container:

            image = extract_html_image(
                container,
                url
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
            f"✅ تم استخراج {len(items)} خبراً يمنياً"
        )

    else:

        print(
            f"✅ تم استخراج {len(items)} خبراً"
        )


    return items


# =========================================================
# فلترة نهائية
# =========================================================

def final_yemen_filter(news):

    filtered_news = []

    removed_count = 0


    for item in news:

        source = item.get(
            "source",
            ""
        )


        # المصادر اليمنية تبقى كما هي

        if (
            source
            not in
            YEMEN_ONLY_SOURCES
        ):

            filtered_news.append(
                item
            )

            continue


        title = item.get(
            "title",
            ""
        )

        description = item.get(
            "description",
            ""
        )


        # BBC والجزيرة والإخبارية السورية
        # لا نسمح لها إلا بأخبار اليمن

        if is_yemen_related(
            title,
            description
        ):

            filtered_news.append(
                item
            )

        else:

            removed_count += 1

            print(
                "🗑️ تم حذف خبر غير متعلق باليمن:"
            )

            print(
                f"   المصدر: {source}"
            )

            print(
                f"   العنوان: {title}"
            )


    print("=" * 70)

    print(
        f"🇾🇪 الفلترة النهائية: حذف {removed_count} خبراً غير متعلق باليمن"
    )

    print("=" * 70)


    return filtered_news


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


        title = item.get(
            "title",
            ""
        ).strip().lower()


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
# التشغيل
# =========================================================

def main():

    all_news = []


    print()

    print(
        "🇾🇪 نبض اليوم - جلب أخبار اليمن"
    )

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


    # =====================================================
    # فلترة نهائية
    # =====================================================

    all_news = final_yemen_filter(
        all_news
    )


    # =====================================================
    # إزالة التكرار
    # =====================================================

    all_news = remove_duplicates(
        all_news
    )


    # =====================================================
    # ترتيب الأخبار
    # =====================================================

    all_news = sort_news(
        all_news
    )


    # =====================================================
    # حفظ الملف
    # =====================================================

    save_news(
        all_news
    )


if __name__ == "__main__":

    main()