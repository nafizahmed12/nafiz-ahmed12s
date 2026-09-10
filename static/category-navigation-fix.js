(() => {
  function esc(value) {
    return String(value ?? '').replace(/[&<>\"']/g, (c) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
  }
  function money(value, currency='BDT') {
    return `${currency === 'BDT' ? '৳' : `${currency} `}${esc(value)}`;
  }
  function categoryLinks() {
    return Array.from(document.querySelectorAll('a.cat[href*="/shop?category="]'));
  }
  async function showCategory(category, title) {
    const grid = document.querySelector('.products');
    const heading = document.querySelector('.section-head h2');
    if (!grid) return;
    grid.innerHTML = '<p style="grid-column:1/-1;text-align:center;color:#64748b;padding:30px">Loading products...</p>';
    try {
      const r = await fetch(`/api/category-products?category=${encodeURIComponent(category)}&page=1&per_page=10`, { headers: { Accept: 'application/json' } });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || 'Could not load products.');
      if (heading) heading.textContent = `${title} products`;
      grid.innerHTML = d.items.length ? d.items.map(p => {
        const image = p.image_url ? `<img class="product-image" src="${esc(p.image_url)}" alt="${esc(p.name)}" loading="lazy">` : '';
        return `<a class="product" href="/product/${Number(p.id)}" aria-label="View details for ${esc(p.name)}">${image}<div class="product-body"><small>${esc(title)}</small><h3>${esc(p.name)}</h3><div class="stars">★★★★★</div><div class="price-row"><strong class="price">${money(p.price,p.currency)}</strong><button class="add" type="button" data-add-product="${Number(p.id)}">+</button></div></div></a>`;
      }).join('') : '<p style="grid-column:1/-1;text-align:center;color:#64748b;padding:30px">No products found in this category.</p>';
      history.pushState({ category }, '', `/?category=${encodeURIComponent(category)}`);
      const section = grid.closest('.section');
      if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (_) {
      window.location.href = `/shop?category=${encodeURIComponent(category)}`;
    }
  }
  document.addEventListener('DOMContentLoaded', () => {
    categoryLinks().forEach(link => link.addEventListener('click', event => {
      event.preventDefault();
      const url = new URL(link.href, window.location.origin);
      const category = url.searchParams.get('category');
      if (!category) return;
      showCategory(category, link.querySelector('b')?.textContent?.trim() || category);
    }));
  });
})();
