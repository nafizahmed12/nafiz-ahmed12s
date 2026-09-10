(() => {
  const esc = (value) => String(value ?? '').replace(/[&<>\"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));

  const money = (value, currency = 'BDT') => {
    const prefix = currency === 'BDT' ? '৳' : `${currency} `;
    return `${prefix}${esc(value)}`;
  };

  function phoneDetailHref(p) {
    const category = String(p.category_slug || '').toLowerCase();
    const slug = String(p.slug || '').trim().toLowerCase();
    if (category !== 'mobile' || !slug) return `/product/${Number(p.id)}`;
    const brands = [
      ['samsung', 'samsung'], ['apple', 'apple'], ['iphone', 'apple'],
      ['google', 'google'], ['pixel', 'google'], ['oneplus', 'oneplus'],
      ['xiaomi', 'xiaomi'], ['redmi', 'xiaomi'], ['realme', 'realme'],
      ['vivo', 'vivo'], ['oppo', 'oppo'], ['honor', 'honor'], ['huawei', 'huawei'],
      ['motorola', 'motorola'], ['nothing', 'nothing'], ['sony', 'sony'],
      ['nokia', 'nokia'], ['asus', 'asus']
    ];
    const match = brands.find(([prefix]) => slug === prefix || slug.startsWith(`${prefix}-`));
    return match ? `/phones/${match[1]}/${encodeURIComponent(slug)}` : `/product/${Number(p.id)}`;
  }

  function loadMarketplaceStyles() {
    if (document.querySelector('link[data-marketplace-home]')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/static/marketplace-home.css';
    link.setAttribute('data-marketplace-home', 'true');
    document.head.appendChild(link);
  }

  function renderProducts(products) {
    const grid = document.querySelector('.products');
    if (!grid) return;

    if (!Array.isArray(products) || products.length === 0) {
      grid.innerHTML = '<p style="grid-column:1/-1;text-align:center;color:#64748b;padding:30px">No products available yet.</p>';
      return;
    }

    grid.innerHTML = products.slice(0, 10).map((p, index) => {
      const sale = p.compare_at_price && Number(p.compare_at_price) > Number(p.price);
      const badge = p.featured ? 'FEATURED' : (sale ? 'SALE' : (index < 2 ? 'NEW' : 'POPULAR'));
      const compare = sale ? `<s style="font-size:11px;color:#94a3b8;margin-right:6px">${money(p.compare_at_price, p.currency)}</s>` : '';
      const image = p.image_url ? `<img class="product-image" src="${esc(p.image_url)}" alt="${esc(p.name)}" loading="lazy" onerror="this.style.display='none'">` : '';
      const href = phoneDetailHref(p);

      return `<a class="product" href="${href}" aria-label="View details for ${esc(p.name)}">
        ${image}
        <div class="product-body">
          <small>${esc(p.category || 'New in')}</small>
          <h3>${esc(p.name)}</h3>
          <div class="stars">★★★★★</div>
          <div class="price-row">
            <strong class="price">${compare}${money(p.price, p.currency)}</strong>
            <button class="add" type="button" data-add-product="${Number(p.id)}" aria-label="Add ${esc(p.name)} to cart">+</button>
          </div>
        </div>
      </a>`;
    }).join('');

    grid.querySelectorAll('[data-add-product]').forEach((button) => {
      button.addEventListener('click', async (event) => {
        event.preventDefault();
        event.stopPropagation();
        button.disabled = true;
        try {
          const response = await fetch('/api/cart/items', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ product_id: Number(button.dataset.addProduct), quantity: 1 })
          });
          if (response.status === 401) {
            window.location.href = '/user-login';
            return;
          }
          const data = await response.json();
          if (!response.ok) {
            alert(data.error || 'Could not add this product.');
            return;
          }
          button.textContent = '✓';
          setTimeout(() => { button.textContent = '+'; }, 900);
        } catch (_) {
          alert('Could not add this product. Please try again.');
        } finally {
          button.disabled = false;
        }
      });
    });
  }

  function addTrustLinks() {
    const footerGrid = document.querySelector('.footer .footer-grid');
    if (!footerGrid || footerGrid.querySelector('[data-trust-links]')) return;

    const section = document.createElement('div');
    section.setAttribute('data-trust-links', 'true');
    section.innerHTML = `
      <b>INFORMATION</b>
      <a href="/about">About Us</a>
      <a href="/contact">Contact Us</a>
      <a href="/privacy-policy">Privacy Policy</a>
      <a href="/terms">Terms &amp; Conditions</a>
      <a href="/refund-policy">Refund &amp; Return Policy</a>
    `;
    footerGrid.appendChild(section);
  }

  async function loadProducts() {
    const grid = document.querySelector('.products');
    if (!grid) return;
    try {
      const url = new URL(window.location.href);
      const category = url.searchParams.get('category') || '';
      if (category && category !== 'mobile') {
        const response = await fetch(`/api/category-products?category=${encodeURIComponent(category)}&page=1&per_page=10`, { headers: { Accept: 'application/json' } });
        if (!response.ok) return;
        const data = await response.json();
        renderProducts((data.items || []).map((p) => ({ ...p, category: category.replace(/-/g, ' ') })));
        const heading = document.querySelector('.section-head h2');
        if (heading) heading.textContent = `${category.replace(/\b\w/g, (c) => c.toUpperCase())} products`;
        return;
      }
      const response = await fetch('/api/home', { headers: { Accept: 'application/json' } });
      if (!response.ok) return;
      const data = await response.json();
      renderProducts(data.products || []);
    } catch (_) {
      // Keep the existing fallback card if the API is temporarily unavailable.
    }
  }

  function bindCategoryNavigation() {
    document.querySelectorAll('a.cat[href*="/shop?category="]').forEach((link) => {
      link.addEventListener('click', (event) => {
        const url = new URL(link.href, window.location.origin);
        const category = url.searchParams.get('category');
        if (!category || category === 'mobile') return;
        event.preventDefault();
        const next = new URL(window.location.href);
        next.searchParams.set('category', category);
        history.pushState({ category }, '', next);
        loadProducts();
        const section = document.querySelector('.products')?.closest('.section');
        if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
    window.addEventListener('popstate', loadProducts);
  }

  document.addEventListener('DOMContentLoaded', () => {
    addTrustLinks();
    loadMarketplaceStyles();
    bindCategoryNavigation();
    const schedule = window.requestIdleCallback || ((callback) => setTimeout(callback, 1));
    schedule(loadProducts, { timeout: 1500 });
  });
})();
