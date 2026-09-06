'use strict';

const STORAGE_KEYS = {
  theme: 'tech-blog-radar:theme',
  columns: 'tech-blog-radar:columns',
};

const state = {
  category: 'ALL',
  query: '',
  theme: localStorage.getItem(STORAGE_KEYS.theme) || 'auto',
  columns: Number(localStorage.getItem(STORAGE_KEYS.columns)) || 3,
};

const categoryMeta = {
  'AI・機械学習': ['🤖', 'ai'],
  'フロントエンド': ['🎨', 'frontend'],
  'バックエンド・インフラ': ['⚙️', 'backend'],
  'モバイル': ['📱', 'mobile'],
  'セキュリティ・SRE': ['🛡️', 'security'],
  '組織・マネジメント': ['👥', 'management'],
  'その他': ['📦', 'other'],
};

function getArticles() {
  const node = document.getElementById('articleData');
  if (!node) return [];
  try {
    const parsed = JSON.parse(node.textContent || '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.error('記事データの読み込みに失敗しました', error);
    return [];
  }
}

const articles = getArticles();

function applyTheme() {
  const isDark = state.theme === 'dark' || (
    state.theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches
  );
  document.documentElement.dataset.theme = isDark ? 'dark' : 'light';
  document.querySelectorAll('[data-theme-option]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.themeOption === state.theme));
  });
}

function applyColumns() {
  state.columns = Math.min(6, Math.max(1, Number(state.columns) || 3));
  document.documentElement.style.setProperty('--column-count', String(state.columns));
  const input = document.getElementById('columnInput');
  if (input) input.value = String(state.columns);
}

function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : '#';
  } catch {
    return '#';
  }
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || '';
  return new Intl.DateTimeFormat('ja-JP', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  }).format(date);
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function createCard(article) {
  const card = createElement('article', 'article-card');
  const top = createElement('div', 'card-topline');
  const meta = categoryMeta[article.category] || categoryMeta['その他'];
  const category = createElement('span', `category-badge category-${meta[1]}`, `${meta[0]} ${article.category || 'その他'}`);
  const date = createElement('time', 'article-date', formatDate(article.pubDate));
  top.append(category, date);

  const title = createElement('a', 'article-title', article.title || '無題');
  title.href = safeExternalUrl(article.link);
  title.target = '_blank';
  title.rel = 'noopener noreferrer';

  const description = createElement('p', 'article-description', article.description || '');

  const footer = createElement('div', 'card-footer');
  const source = createElement('span', 'source-label', article.source || '外部サイト');
  footer.appendChild(source);

  const tags = createElement('div', 'tag-list');
  (article.tags || []).slice(0, 5).forEach((tag) => {
    tags.appendChild(createElement('span', 'tag', `#${tag}`));
  });
  if (tags.children.length) footer.appendChild(tags);

  card.append(top, title, description, footer);
  return card;
}

function filteredArticles() {
  const query = state.query.trim().toLowerCase();
  return articles.filter((article) => {
    const matchesCategory = state.category === 'ALL' || article.category === state.category;
    if (!matchesCategory) return false;
    if (!query) return true;
    return [article.title, article.description, article.source, ...(article.tags || [])]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query));
  });
}

function updateCategoryButtons() {
  document.querySelectorAll('[data-category]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.category === state.category));
  });
}

function render() {
  const list = document.getElementById('articlesList');
  const empty = document.getElementById('emptyState');
  const count = document.getElementById('resultCount');
  const filtered = filteredArticles();

  list.replaceChildren(...filtered.map(createCard));
  empty.hidden = filtered.length !== 0;
  count.textContent = `${filtered.length.toLocaleString()} articles`;
  updateCategoryButtons();
}

function bindEvents() {
  document.getElementById('searchInput')?.addEventListener('input', (event) => {
    state.query = event.target.value;
    render();
  });

  document.querySelectorAll('[data-category]').forEach((button) => {
    button.addEventListener('click', () => {
      state.category = button.dataset.category;
      render();
    });
  });

  document.querySelectorAll('[data-theme-option]').forEach((button) => {
    button.addEventListener('click', () => {
      state.theme = button.dataset.themeOption;
      localStorage.setItem(STORAGE_KEYS.theme, state.theme);
      applyTheme();
    });
  });

  document.getElementById('columnInput')?.addEventListener('change', (event) => {
    state.columns = event.target.value;
    localStorage.setItem(STORAGE_KEYS.columns, String(state.columns));
    applyColumns();
  });

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (state.theme === 'auto') applyTheme();
  });
}

function init() {
  applyTheme();
  applyColumns();
  bindEvents();
  const total = document.getElementById('totalCount');
  if (total) total.textContent = articles.length.toLocaleString();
  render();
}

init();
