# tech-blog-radar 作業手引き

RSS / Atom を集めて分類し、`index.html` を作るサイト。GitHub Actions（`.github/workflows/update.yml`）が1日9回 `python build.py` を回し、`index.html` を main に commit する。

## フィードを足す

`build.py` の `FEEDS` に1項目足す。

```python
{
    "name": "表示名",          # feedSources / trendSources に入る
    "url": "https://…/feed",   # RSS 2.0 か Atom
    "kind": "tech_blog",       # 企業ブログなど。人気・トレンド系は "trend"
},
```

- **1本でも取れないと全体の更新が止まる**（`_fetch_xml` が `RuntimeError`）。足す前に URL が XML を返すことを確かめる
- 同じ記事は URL を正規化して1件にまとめる（`canonicalize_url`）。重複を足しても件数は増えない

## カテゴリを足す・名前を変える

次の3か所を同じ名前でそろえる。

1. `build.py` の `CATEGORIES`（分類の言葉。どれにも当たらない記事は「その他」）
2. `build.py` の HTML の `category-button`（`data-category` がカテゴリ名）
3. `app.js` の `categoryMeta`（絵文字と CSS の名前）

## 壊してはいけないもの

Redmi Pad のランチャー（repo `redmi-pad-launcher` の `radar/`）が `index.html` を読んでいる。

- `<script id="articleData" type="application/json">` の中の JSON 配列（1件 = `title` `link` `pubDate` `description` `category` `tags` `source` `feedSources` `trendSources`）。id・キー名・配列であることを変えない
- `pubDate` は RFC 1123 か ISO 8601
- カテゴリはランチャーが記事から数えて作るので、カテゴリを足してもランチャーは変えなくてよい

## 確かめ方

```bash
python -m py_compile build.py
python build.py   # 各フィードの件数と "Generated index.html with N unique articles from M feeds." が出る
```

- 足したフィードの行に `fetched N articles`（N > 0）が出て、M がフィードの数と合えばよい
- 手元で作った `index.html` は commit しない（`git checkout index.html` で戻す）。`index.html` は Actions が作る
- `build.py` `app.js` `styles.css` を main に push すると Actions が回り、`index.html` が作り直される
