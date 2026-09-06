import datetime
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET

# 対象のRSSフィードURL
RSS_URL = "https://yamadashy.github.io/tech-blog-rss-feed/feeds/rss.xml"

# カテゴリ定義とキーワード一覧
CATEGORIES = {
    "AI・機械学習": {
        "icon": "🤖",
        "keywords": [
            "ai",
            "llm",
            "機械学習",
            "深層学習",
            "生成ai",
            "chatgpt",
            "gpt",
            "claude",
            "gemini",
            "openai",
            "langchain",
            "rag",
            "プロンプト",
            "データサイエンス",
            "推薦システム",
            "自然言語処理",
            "画像認識",
            "agent",
            "エージェント",
        ],
    },
    "フロントエンド": {
        "icon": "🎨",
        "keywords": [
            "react",
            "vue",
            "next.js",
            "nuxt",
            "typescript",
            "javascript",
            "css",
            "html",
            "tailwind",
            "astro",
            "svelte",
            "vite",
            "webpack",
            "ブラウザ",
            "ui",
            "ux",
            "アクセシビリティ",
            "webフロント",
            "フロントエンド",
        ],
    },
    "バックエンド・インフラ": {
        "icon": "⚙️",
        "keywords": [
            "go言語",
            "golang",
            "rust",
            "python",
            "java",
            "kotlin",
            "ruby",
            "rails",
            "aws",
            "gcp",
            "azure",
            "kubernetes",
            "k8s",
            "docker",
            "terraform",
            "マイクロサービス",
            "データベース",
            "mysql",
            "postgresql",
            "redis",
            "アーキテクチャ",
            "api",
            "graphql",
            "grpc",
            "サーバー",
            "バックエンド",
        ],
    },
    "モバイル": {
        "icon": "📱",
        "keywords": [
            "ios",
            "android",
            "swift",
            "swiftui",
            "flutter",
            "react native",
            "モバイル",
            "アプリ開発",
            "xcode",
        ],
    },
    "セキュリティ・SRE": {
        "icon": "🛡️",
        "keywords": [
            "セキュリティ",
            "脆弱性",
            "認証",
            "認可",
            "oauth",
            "sre",
            "オブザーバビリティ",
            "監視",
            "datadog",
            "prometheus",
            "インシデント",
            "負荷テスト",
            "slo",
            "sla",
        ],
    },
    "組織・マネジメント": {
        "icon": "👥",
        "keywords": [
            "アジャイル",
            "スクラム",
            "チーム開発",
            "マネジメント",
            "採用",
            "キャリア",
            "育成",
            "研修",
            "オンボーディング",
            "開発合宿",
            "コードレビュー",
            "ポエム",
            "振り返り",
            "組織",
        ],
    },
}


def clean_text(text: str) -> str:
  if not text:
    return ""
  # HTMLタグを除去して小文字化
  text = re.sub(r"<[^>]+>", "", text)
  return html.unescape(text).strip()


def classify_article(title: str, description: str):
  title_lower = title.lower()
  desc_lower = clean_text(description).lower()

  scores = {}
  matched_tags = []

  for cat_name, cat_info in CATEGORIES.items():
    score = 0
    for kw in cat_info["keywords"]:
      # 単語境界や部分一致の重み付け
      pattern = r"(?:\b|_)" + re.escape(kw) + r"(?:\b|_)" if kw.isalnum() else re.escape(kw)
      t_count = len(re.findall(pattern, title_lower))
      d_count = len(re.findall(pattern, desc_lower))

      if t_count > 0 or d_count > 0:
        # タイトル一致は重み3倍、本文は1倍
        score += (t_count * 3) + d_count
        if kw not in matched_tags and (t_count > 0 or d_count >= 2):
          matched_tags.append(kw)

    if score > 0:
      scores[cat_name] = score

  # 最高スコアのカテゴリを選定（同点またはスコアが低すぎる場合は「その他」）
  if scores and max(scores.values()) >= 2:
    best_category = max(scores, key=scores.get)
  else:
    best_category = "その他"

  return best_category, matched_tags[:5]


def fetch_and_parse():
  req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
  with urllib.request.urlopen(req) as response:
    xml_data = response.read()

  root = ET.fromstring(xml_data)
  channel = root.find("channel")
  if channel is None:
    return []

  articles = []
  for item in channel.findall("item"):
    title = item.findtext("title", "")
    link = item.findtext("link", "")
    pub_date = item.findtext("pubDate", "")
    description = clean_text(item.findtext("description", ""))

    category, tags = classify_article(title, description)

    articles.append({
        "title": title,
        "link": link,
        "pubDate": pub_date,
        "description": description[:150] + "..."
        if len(description) > 150
        else description,
        "category": category,
        "tags": tags,
    })

  return articles


def generate_html(articles):
  now_jst = datetime.datetime.now(
      datetime.timezone(datetime.timedelta(hours=9))
  ).strftime("%Y/%m/%d %H:%M")
  articles_json = json.dumps(articles, ensure_ascii=False)

  html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tech Blog Radar</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">
  <header class="bg-white border-b sticky top-0 z-20 shadow-sm">
    <div class="max-w-5xl mx-auto px-4 py-3 flex flex-col sm:flex-row justify-between items-center gap-3">
      <div>
        <h1 class="text-xl font-bold text-slate-800 flex items-center gap-2">
          <span>📡</span> Tech Blog Radar
        </h1>
        <p class="text-xs text-slate-500">最終更新: {now_jst}</p>
      </div>
      <div class="w-full sm:w-72">
        <input type="text" id="searchInput" placeholder="タイトルやタグで検索..." 
          class="w-full px-3 py-1.5 text-sm bg-slate-100 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
      </div>
    </div>

    <!-- カテゴリタブ -->
    <div class="max-w-5xl mx-auto px-4 overflow-x-auto">
      <div class="flex space-x-2 py-2 text-sm whitespace-nowrap" id="categoryTabs">
        <button onclick="setCategory('ALL')" class="cat-btn px-3 py-1 rounded-full font-medium bg-indigo-600 text-white" data-cat="ALL">すべて</button>
        <button onclick="setCategory('AI・機械学習')" class="cat-btn px-3 py-1 rounded-full font-medium bg-slate-200 text-slate-700 hover:bg-slate-300" data-cat="AI・機械学習">🤖 AI・機械学習</button>
        <button onclick="setCategory('フロントエンド')" class="cat-btn px-3 py-1 rounded-full font-medium bg-slate-200 text-slate-700 hover:bg-slate-300" data-cat="フロントエンド">🎨 フロントエンド</button>
        <button onclick="setCategory('バックエンド・インフラ')" class="cat-btn px-3 py-1 rounded-full font-medium bg-slate-200 text-slate-700 hover:bg-slate-300" data-cat="バックエンド・インフラ">⚙️ バックエンド・インフラ</button>
        <button onclick="setCategory('モバイル')" class="cat-btn px-3 py-1 rounded-full font-medium bg-slate-200 text-slate-700 hover:bg-slate-300" data-cat="モバイル">📱 モバイル</button>
        <button onclick="setCategory('セキュリティ・SRE')" class="cat-btn px-3 py-1 rounded-full font-medium bg-slate-200 text-slate-700 hover:bg-slate-300" data-cat="セキュリティ・SRE">🛡️ セキュリティ・SRE</button>
        <button onclick="setCategory('組織・マネジメント')" class="cat-btn px-3 py-1 rounded-full font-medium bg-slate-200 text-slate-700 hover:bg-slate-300" data-cat="組織・マネジメント">👥 組織・マネジメント</button>
        <button onclick="setCategory('その他')" class="cat-btn px-3 py-1 rounded-full font-medium bg-slate-200 text-slate-700 hover:bg-slate-300" data-cat="その他">📦 その他</button>
      </div>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-6">
    <div id="articlesList" class="grid gap-4 sm:grid-cols-1 md:grid-cols-2"></div>
    <div id="noResults" class="hidden text-center py-12 text-slate-400">該当する記事が見つかりませんでした</div>
  </main>

  <script>
    const articles = {articles_json};
    let currentCategory = 'ALL';
    let searchQuery = '';

    function render() {{
      const list = document.getElementById('articlesList');
      const noResults = document.getElementById('noResults');
      list.innerHTML = '';

      const filtered = articles.filter(a => {{
        const matchCat = (currentCategory === 'ALL' || a.category === currentCategory);
        const q = searchQuery.toLowerCase();
        const matchSearch = !q || a.title.toLowerCase().includes(q) || a.description.toLowerCase().includes(q) || a.tags.some(t => t.toLowerCase().includes(q));
        return matchCat && matchSearch;
      }});

      if (filtered.length === 0) {{
        noResults.classList.remove('hidden');
      }} else {{
        noResults.classList.add('hidden');
        filtered.forEach(a => {{
          const card = document.createElement('div');
          card.className = 'bg-white p-4 rounded-xl border border-slate-200 hover:shadow-md transition flex flex-col justify-between';
          
          const tagsHtml = a.tags.map(t => `<span class="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">#${{t}}</span>`).join(' ');

          card.innerHTML = `
            <div>
              <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
                <span class="font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">${{a.category}}</span>
                <span>${{a.pubDate.split(' ').slice(0, 4).join(' ')}}</span>
              </div>
              <a href="${{a.link}}" target="_blank" rel="noopener noreferrer" class="font-semibold text-slate-900 hover:text-indigo-600 text-base line-clamp-2">
                ${{a.title}}
              </a>
              <p class="text-xs text-slate-600 mt-2 line-clamp-3 leading-relaxed">
                ${{a.description}}
              </p>
            </div>
            <div class="mt-3 pt-2 border-t border-slate-100 flex flex-wrap gap-1">
              ${{tagsHtml}}
            </div>
          `;
          list.appendChild(card);
        }});
      }}
    }}

    function setCategory(cat) {{
      currentCategory = cat;
      document.querySelectorAll('.cat-btn').forEach(btn => {{
        if (btn.dataset.cat === cat) {{
          btn.className = 'cat-btn px-3 py-1 rounded-full font-medium bg-indigo-600 text-white';
        }} else {{
          btn.className = 'cat-btn px-3 py-1 rounded-full font-medium bg-slate-200 text-slate-700 hover:bg-slate-300';
        }}
      }});
      render();
    }}

    document.getElementById('searchInput').addEventListener('input', (e) => {{
      searchQuery = e.target.value;
      render();
    }});

    render();
  </script>
</body>
</html>"""

  with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)


if __name__ == "__main__":
  articles = fetch_and_parse()
  generate_html(articles)
  print(f"Generated index.html with {len(articles)} articles.")
