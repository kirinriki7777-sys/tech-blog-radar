import datetime
import email.utils
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

FEEDS = [
    {
        "name": "Tech Blogs",
        "url": "https://yamadashy.github.io/tech-blog-rss-feed/feeds/rss.xml",
        "kind": "tech_blog",
    },
    {
        "name": "Zenn Trend",
        "url": "https://zenn.dev/feed",
        "kind": "trend",
    },
    {
        "name": "Qiita Popular",
        "url": "https://qiita.com/popular-items/feed",
        "kind": "trend",
    },
]

CATEGORIES = {
    "AI・機械学習": {"icon": "🤖", "keywords": [
        "ai", "llm", "機械学習", "深層学習", "生成ai", "chatgpt", "gpt", "claude",
        "gemini", "openai", "langchain", "rag", "プロンプト", "データサイエンス",
        "推薦システム", "自然言語処理", "画像認識", "agent", "エージェント",
    ]},
    "フロントエンド": {"icon": "🎨", "keywords": [
        "react", "vue", "next.js", "nuxt", "typescript", "javascript", "css", "html",
        "tailwind", "astro", "svelte", "vite", "webpack", "ブラウザ", "ui", "ux",
        "アクセシビリティ", "webフロント", "フロントエンド",
    ]},
    "バックエンド・インフラ": {"icon": "⚙️", "keywords": [
        "go言語", "golang", "rust", "python", "java", "kotlin", "ruby", "rails", "aws",
        "gcp", "azure", "kubernetes", "k8s", "docker", "terraform", "マイクロサービス",
        "データベース", "mysql", "postgresql", "redis", "アーキテクチャ", "api",
        "graphql", "grpc", "サーバー", "バックエンド",
    ]},
    "モバイル": {"icon": "📱", "keywords": [
        "ios", "android", "swift", "swiftui", "flutter", "react native", "モバイル",
        "アプリ開発", "xcode",
    ]},
    "セキュリティ・SRE": {"icon": "🛡️", "keywords": [
        "セキュリティ", "脆弱性", "認証", "認可", "oauth", "sre", "オブザーバビリティ",
        "監視", "datadog", "prometheus", "インシデント", "負荷テスト", "slo", "sla",
    ]},
    "組織・マネジメント": {"icon": "👥", "keywords": [
        "アジャイル", "スクラム", "チーム開発", "マネジメント", "採用", "キャリア", "育成",
        "研修", "オンボーディング", "開発合宿", "コードレビュー", "ポエム", "振り返り", "組織",
    ]},
}

TRACKING_QUERY_PREFIXES = ("utm_",)
USER_AGENT = "TechBlogRadar/1.1 (+https://github.com/kirinriki7777-sys/tech-blog-radar)"


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def clean_text(text: str) -> str:
    if not text:
        return ""
    parser = _TextExtractor()
    parser.feed(text)
    parser.close()
    return " ".join("".join(parser.parts).split())


def _keyword_pattern(keyword: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_+-]+", keyword):
        return rf"(?<![A-Za-z0-9_]){re.escape(keyword)}(?![A-Za-z0-9_])"
    return re.escape(keyword)


def classify_article(title: str, description: str):
    title_lower = title.lower()
    desc_lower = clean_text(description).lower()
    scores = {}
    matched_tags = []

    for cat_name, cat_info in CATEGORIES.items():
        score = 0
        for keyword in cat_info["keywords"]:
            pattern = _keyword_pattern(keyword.lower())
            title_count = len(re.findall(pattern, title_lower))
            desc_count = len(re.findall(pattern, desc_lower))
            if title_count or desc_count:
                score += title_count * 3 + desc_count
                if keyword not in matched_tags and (title_count > 0 or desc_count >= 2):
                    matched_tags.append(keyword)
        if score:
            scores[cat_name] = score

    if not scores:
        return "その他", matched_tags[:5]

    best_score = max(scores.values())
    winners = [name for name, score in scores.items() if score == best_score]
    best_category = winners[0] if best_score >= 2 and len(winners) == 1 else "その他"
    return best_category, matched_tags[:5]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _element_text(element) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _first_child_text(parent, names) -> str:
    wanted = set(names)
    for child in list(parent):
        if _local_name(child.tag) in wanted:
            return _element_text(child)
    return ""


def _entry_link(entry) -> str:
    for child in list(entry):
        if _local_name(child.tag) != "link":
            continue
        href = (child.attrib.get("href") or "").strip()
        rel = (child.attrib.get("rel") or "alternate").strip()
        if href and rel in {"", "alternate"}:
            return href
        text = _element_text(child)
        if text:
            return text
    return ""


def canonicalize_url(value: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(value.strip())
    except ValueError:
        return value.strip()

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return value.strip()

    query = [
        (key, val)
        for key, val in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    ]
    path = parsed.path or "/"
    return urllib.parse.urlunsplit((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        urllib.parse.urlencode(query, doseq=True),
        "",
    ))


def source_name(link: str) -> str:
    try:
        host = urllib.parse.urlparse(link).hostname or ""
        return host.removeprefix("www.") or "外部サイト"
    except ValueError:
        return "外部サイト"


def _parse_datetime(value: str):
    if not value:
        return None

    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=datetime.timezone.utc)
            return parsed
    except (TypeError, ValueError, OverflowError):
        pass

    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed
    except ValueError:
        return None


def _fetch_xml(url: str, attempts: int = 3) -> bytes:
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except Exception as error:
            last_error = error
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"Failed to fetch {url} after {attempts} attempts") from last_error


def _parse_rss(root, feed):
    channel = next((child for child in list(root) if _local_name(child.tag) == "channel"), None)
    if channel is None:
        raise ValueError(f"{feed['name']}: RSS channel not found")

    articles = []
    for item in list(channel):
        if _local_name(item.tag) != "item":
            continue
        title = clean_text(_first_child_text(item, {"title"}))
        link = canonicalize_url(_first_child_text(item, {"link"}))
        pub_date = _first_child_text(item, {"pubDate", "date", "updated", "published"})
        description = clean_text(_first_child_text(item, {"description", "encoded", "content", "summary"}))
        articles.append(_make_article(title, link, pub_date, description, feed))
    return articles


def _parse_atom(root, feed):
    articles = []
    for entry in list(root):
        if _local_name(entry.tag) != "entry":
            continue
        title = clean_text(_first_child_text(entry, {"title"}))
        link = canonicalize_url(_entry_link(entry))
        pub_date = _first_child_text(entry, {"published", "updated", "date"})
        description = clean_text(_first_child_text(entry, {"content", "summary", "description"}))
        articles.append(_make_article(title, link, pub_date, description, feed))
    return articles


def _make_article(title: str, link: str, pub_date: str, description: str, feed):
    category, tags = classify_article(title, description)
    return {
        "title": title,
        "link": link,
        "pubDate": pub_date,
        "description": description[:150] + "..." if len(description) > 150 else description,
        "category": category,
        "tags": tags,
        "source": source_name(link),
        "feedSources": [feed["name"]],
        "trendSources": [feed["name"]] if feed["kind"] == "trend" else [],
    }


def parse_feed(xml_data: bytes, feed):
    root = ET.fromstring(xml_data)
    root_name = _local_name(root.tag).lower()
    if root_name == "rss":
        return _parse_rss(root, feed)
    if root_name == "feed":
        return _parse_atom(root, feed)
    raise ValueError(f"{feed['name']}: unsupported feed root <{root_name}>")


def _merge_article(existing, incoming):
    for key in ("feedSources", "trendSources"):
        existing[key] = list(dict.fromkeys(existing.get(key, []) + incoming.get(key, [])))

    if len(incoming.get("description", "")) > len(existing.get("description", "")):
        existing["description"] = incoming["description"]

    existing_dt = _parse_datetime(existing.get("pubDate", ""))
    incoming_dt = _parse_datetime(incoming.get("pubDate", ""))
    if incoming_dt and (not existing_dt or incoming_dt > existing_dt):
        existing["pubDate"] = incoming["pubDate"]

    category, tags = classify_article(existing.get("title", ""), existing.get("description", ""))
    existing["category"] = category
    existing["tags"] = list(dict.fromkeys(existing.get("tags", []) + tags))[:5]


def fetch_and_parse():
    deduped = {}

    for feed in FEEDS:
        xml_data = _fetch_xml(feed["url"])
        articles = parse_feed(xml_data, feed)
        print(f"{feed['name']}: fetched {len(articles)} articles")

        for article in articles:
            key = canonicalize_url(article["link"])
            if not key:
                key = f"{feed['name']}::{article['title']}::{article['pubDate']}"

            if key in deduped:
                _merge_article(deduped[key], article)
            else:
                deduped[key] = article

    articles = list(deduped.values())
    articles.sort(
        key=lambda article: _parse_datetime(article.get("pubDate", ""))
        or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        reverse=True,
    )
    return articles


def generate_html(articles):
    article_json = json.dumps(articles, ensure_ascii=False).replace("</", "<\\/")
    html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="description" content="テックブログ、Zennトレンド、Qiita人気記事を自動収集・分類して一覧できる軽量リーダー">
  <title>Tech Blog Radar</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="site-header">
    <div class="shell">
      <div class="header-main">
        <div class="brand">
          <div class="brand-mark" aria-hidden="true">📡</div>
          <div class="brand-copy">
            <h1>Tech Blog Radar</h1>
            <p>Engineering signals, filtered for humans.</p>
          </div>
        </div>

        <label class="search-wrap">
          <span class="sr-only">記事を検索</span>
          <input id="searchInput" class="search-input" type="search" placeholder="タイトル・本文・タグ・配信元を検索" autocomplete="off">
        </label>

        <div class="theme-switcher" aria-label="表示テーマ">
          <button class="icon-button" type="button" data-theme-option="light" aria-label="ライトテーマ">☀️</button>
          <button class="icon-button" type="button" data-theme-option="auto" aria-label="システム設定に合わせる">◐</button>
          <button class="icon-button" type="button" data-theme-option="dark" aria-label="ダークテーマ">🌙</button>
        </div>
      </div>

      <div class="toolbar">
        <nav class="category-scroll" aria-label="カテゴリ">
          <div class="category-list">
            <button class="category-button" type="button" data-category="ALL">すべて</button>
            <button class="category-button" type="button" data-category="AI・機械学習">🤖 AI・機械学習</button>
            <button class="category-button" type="button" data-category="フロントエンド">🎨 フロントエンド</button>
            <button class="category-button" type="button" data-category="バックエンド・インフラ">⚙️ バックエンド・インフラ</button>
            <button class="category-button" type="button" data-category="モバイル">📱 モバイル</button>
            <button class="category-button" type="button" data-category="セキュリティ・SRE">🛡️ セキュリティ・SRE</button>
            <button class="category-button" type="button" data-category="組織・マネジメント">👥 組織・マネジメント</button>
            <button class="category-button" type="button" data-category="その他">📦 その他</button>
          </div>
        </nav>

        <label class="column-control">
          <span class="column-label">列数</span>
          <input id="columnInput" class="column-input" type="number" min="1" max="6" inputmode="numeric" aria-label="記事の列数">
        </label>
      </div>
    </div>
  </header>

  <main class="shell">
    <section class="hero">
      <div class="hero-panel">
        <div>
          <div class="eyebrow">Signal dashboard</div>
          <h2>技術の流れを、<br>ノイズ少なめで眺める。</h2>
          <p>国内テックブログ、Zennトレンド、Qiita人気記事を自動収集して分類。検索と表示密度を自分の読み方に合わせて調整できます。</p>
        </div>
        <div class="radar-stat">
          <strong id="totalCount">0</strong>
          <span>signals indexed</span>
        </div>
      </div>
    </section>

    <div class="content-head">
      <h2>Latest signals</h2>
      <div id="resultCount" class="result-count">0 articles</div>
    </div>

    <section id="articlesList" class="article-grid" aria-live="polite"></section>
    <div id="emptyState" class="empty-state" hidden>条件に合う記事が見つかりませんでした。</div>
  </main>

  <script id="articleData" type="application/json">{article_json}</script>
  <script src="app.js" defer></script>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as file:
        file.write(html_template)


if __name__ == "__main__":
    articles = fetch_and_parse()
    generate_html(articles)
    print(f"Generated index.html with {len(articles)} unique articles from {len(FEEDS)} feeds.")
