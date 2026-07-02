const input = document.getElementById('searchInput');
const results = document.getElementById('searchResults');
const meta = document.getElementById('searchMeta');
const clearButton = document.getElementById('clearSearch');

function normalize(value) {
  return (value || '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }[char]));
}

function snippet(text, terms) {
  const lower = text.toLowerCase();
  const first = terms.map(term => lower.indexOf(term)).filter(index => index >= 0).sort((a, b) => a - b)[0] || 0;
  const start = Math.max(0, first - 52);
  const raw = text.slice(start, start + 150);
  let escaped = escapeHtml((start > 0 ? '...' : '') + raw + (start + 150 < text.length ? '...' : ''));
  for (const term of terms) {
    if (!term) continue;
    escaped = escaped.replace(new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'ig'), '<strong>$1</strong>');
  }
  return escaped;
}

function render() {
  const query = normalize(input.value);
  const terms = query.split(' ').filter(Boolean);
  results.innerHTML = '';
  if (!terms.length) {
    meta.textContent = 'キーワードを入れると、該当する説明書と章が表示されます。';
    return;
  }
  const matches = window.SEARCH_INDEX
    .map(item => ({ item, haystack: normalize(`${item.manual} ${item.section} ${item.text}`) }))
    .filter(({ haystack }) => terms.every(term => haystack.includes(term)))
    .slice(0, 30);

  meta.textContent = `${matches.length}件見つかりました`;
  if (!matches.length) {
    results.innerHTML = '<p class="search-meta">別の言葉で検索してください。</p>';
    return;
  }
  results.innerHTML = matches.map(({ item }) => {
    const url = `${item.url}?q=${encodeURIComponent(query)}#${item.anchor}`;
    return `<a class="result-card" href="${url}">
      <span class="eyebrow">${escapeHtml(item.category)}</span>
      <h3>${escapeHtml(item.manual)} / ${escapeHtml(item.section)}</h3>
      <p>${snippet(item.text, terms)}</p>
    </a>`;
  }).join('');
}

input.addEventListener('input', render);
clearButton.addEventListener('click', () => {
  input.value = '';
  input.focus();
  render();
});
render();
