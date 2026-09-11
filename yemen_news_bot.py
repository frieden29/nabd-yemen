# -*- coding: utf-8 -*-

import json
import re
import time
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin

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
# مصادر RSS
# =========================================================

SOURCES = [

    # 🇾🇪 اليمن

    {
        "name": "المشهد اليمني",
        "rss": "https://www.almashhad.news/feed",
    },

    {
        "name": "عدن الغد",
        "rss": "https://www.adngad.net/feed",
    },

    {
        "name": "الصحوة نت",
        "rss": "https://www.alsahwa-yemen.net/rss",
    },

    {
        "name": "قناة بلقيس",
        "rss": "https://belqees.net/rss",
    },

    {
        "name": "وكالة سبأ",
        "rss": "https://www.sabanew.net/rss.php?lang=ar",
    },


    # 🌍 مصادر عربية ودولية

    {
        "name": "BBC عربي",
        "rss": "https://feeds.bbci.co.uk/arabic/rss.xml",
    },

]


# =========================================================
# المصادر التي سنقرأها مباشرة من الموقع
# =========================================================

WEB_SOURCES = [

    {
        "name": "الجزيرة",
        "url": "https://www.aljazeera.net/",
        "domain": "aljazeera.net",
    },

    {
        "name": "الإخبارية السورية",
        "url": "https://alikhbariah.com/",
        "domain": "alikhbariah.com",
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
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,"
        "image/webp,*/*;q=0.8"
    ),

    "Accept-Language":
        "ar,en-US;q=0.8,en;q=0.6",

}


# =========================================================
# أدوات مساعدة
# =========================================================

def clean_text(text):

    if not text:
        return ""

    text = unescape(text)

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
# استخراج صورة RSS
# =========================================================

def extract_image(entry):

    candidates = []


    if hasattr(
        entry,
        "media_content"
    ):

        for item in entry.media_content:

            url = item.get("url")

            if url:
                candidates.append(url)


    if hasattr(
        entry,
        "media_thumbnail"
    ):

        for item in entry.media_thumbnail:

            url = item.get("url")

            if url:
                candidates.append(url)


    if hasattr(
        entry,
        "links"
    ):

        for item in entry.links:

            href =
                item.get("href")

            typ =
                item.get("type", "")

            if (
                href
                and
                typ.startswith("image/")
            ):

                candidates.append(
                    href
                )


    if candidates:

        return candidates[0]


    summary =
        getattr(
            entry,
            "summary",
            ""
        )


    if summary:

        soup =
            BeautifulSoup(
                summary,
                "html.parser"
            )

        img =
            soup.find("img")

        if (
            img
            and
            img.get("src")
        ):

            return img["src"]


    return ""


# =========================================================
# التاريخ
# =========================================================

def parse_date(entry):

    possible = [

        "published_parsed",

        "updated_parsed",

    ]


    for attr in possible:

        value =
            getattr(
                entry,
                attr,
                None
            )

        if value:

            try:

                dt =
                    datetime(
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
# تنظيف الرابط
# =========================================================

def normalize_link(link):

    if not link:
        return ""

    return link.strip()


# =========================================================
# قراءة مصدر RSS
# =========================================================

def fetch_source(source):

    name =
        source["name"]

    rss =
        source["rss"]


    print("=" * 70)

    print(
        f"المصدر: {name}"
    )

    print(
        f"RSS: {rss}"
    )

    print("=" * 70)


    try:

        response =
            requests.get(
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


    feed =
        feedparser.parse(
            response.content
        )


    items = []


    for entry in feed.entries[
        :MAX_PER_SOURCE
    ]:

        title =
            clean_text(
                getattr(
                    entry,
                    "title",
                    ""
                )
            )


        link =
            normalize_link(
                getattr(
                    entry,
                    "link",
                    ""
                )
            )


        description =
            clean_text(
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


        image =
            extract_image(
                entry
            )


        published_at =
            parse_date(
                entry
            )


        if (
            not title
            or
            not link
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
                published_at,

            "views":
                0,

        }


        items.append(
            item
        )


    print(
        f"✅ تم استخراج {len(items)} خبراً"
    )


    return items


# =========================================================
# استخراج صورة من عنصر HTML
# =========================================================

def extract_html_image(
    element,
    base_url
):

    img =
        element.find("img")


    if not img:

        parent =
            element.parent

        if parent:

            img =
                parent.find(
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

        srcset =
            img.get("srcset", "")

        if srcset:

            image =
                srcset.split(",")[0]
                .strip()
                .split(" ")[0]


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

    name =
        source["name"]

    url =
        source["url"]

    domain =
        source["domain"]


    print("=" * 70)

    print(
        f"المصدر: {name}"
    )

    print(
        f"WEB: {url}"
    )

    print("=" * 70)


    try:

        response =
            requests.get(
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


    soup =
        BeautifulSoup(
            response.text,
            "html.parser"
        )


    items = []

    seen = set()


    # -----------------------------------------
    # البحث عن عناوين الأخبار وروابطها
    # -----------------------------------------

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

        title =
            clean_text(
                anchor.get_text(
                    " ",
                    strip=True
                )
            )


        href =
            anchor.get(
                "href",
                ""
            )


        if (
            not title
            or
            not href
        ):

            continue


        # نتجاهل النصوص القصيرة جدًا

        if len(title) < 15:

            continue


        link =
            urljoin(
                url,
                href
            )


        # يجب أن يكون الرابط من نفس الموقع

        if domain not in link:

            continue


        # منع التكرار

        if link in seen:

            continue


        seen.add(
            link
        )


        # -------------------------------------
        # محاولة استخراج الصورة
        # -------------------------------------

        container =
            anchor.find_parent(
                [
                    "article",
                    "div",
                    "li"
                ]
            )


        image = ""


        if container:

            image =
                extract_html_image(
                    container,
                    url
                )


        # -------------------------------------
        # الوصف
        # -------------------------------------

        description = ""


        if container:

            paragraph =
                container.find("p")

            if paragraph:

                description =
                    clean_text(
                        paragraph.get_text(
                            " ",
                            strip=True
                        )
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


    print(
        f"✅ تم استخراج {len(items)} خبراً"
    )


    return items


# =========================================================
# إزالة التكرار
# =========================================================

def remove_duplicates(news):

    result = []

    seen_links = set()

    seen_titles = set()


    for item in news:

        link =
            item.get(
                "link",
                ""
            ).strip()


        title =
            item.get(
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

        value =
            item.get(
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
# حفظ الملف
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
        "🇾🇪 نبض اليمن - جلب الأخبار"
    )

    print()


    # -----------------------------------------
    # RSS
    # -----------------------------------------

    for source in SOURCES:

        items =
            fetch_source(
                source
            )

        all_news.extend(
            items
        )

        time.sleep(
            0.5
        )


    # -----------------------------------------
    # المواقع المباشرة
    # -----------------------------------------

    for source in WEB_SOURCES:

        items =
            fetch_web_source(
                source
            )

        all_news.extend(
            items
        )

        time.sleep(
            0.5
        )


    # -----------------------------------------
    # إزالة التكرار
    # -----------------------------------------

    all_news =
        remove_duplicates(
            all_news
        )


    # -----------------------------------------
    # الترتيب
    # -----------------------------------------

    all_news =
        sort_news(
            all_news
        )


    # -----------------------------------------
    # الحفظ
    # -----------------------------------------

    save_news(
        all_news
    )


if __name__ == "__main__":

    main()