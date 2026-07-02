function highlightTerm(term) {
  if (!term) return;
  const content = document.getElementById('content');
  if (!content) return;
  const pattern = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
  const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue || !pattern.test(node.nodeValue)) return NodeFilter.FILTER_REJECT;
      pattern.lastIndex = 0;
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const span = document.createElement('span');
    span.innerHTML = node.nodeValue.replace(pattern, '<mark class="search-hit">$&</mark>');
    node.parentNode.replaceChild(span, node);
  }
  const target = location.hash ? document.querySelector(location.hash) : document.querySelector('mark.search-hit');
  if (target) setTimeout(() => target.scrollIntoView({ block: 'start' }), 120);
}

const params = new URLSearchParams(location.search);
highlightTerm(params.get('q'));
