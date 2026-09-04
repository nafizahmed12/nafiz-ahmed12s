(() => {
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));

  const money = (value, currency = 'BDT') => {
    const prefix = currency === 'BDT' ? '৳' : `${currency} `;
    return `${prefix}${esc(value)}`;
  };

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
      const image = p.image_url
        ? `<img src="${esc(p.image_url)}" alt="${esc(p.name)}" loading="lazy" decoding="async">`
        : '<span style="font-size:48px">🛍️</span>';
      const sale = p.compare_at_price && Number(p.compare_at_price) > Number(p.price);
      const badge = p.featured ? 'FEATURED' : (sale ? 'SALE' : (index < 2 ? 'NEW' : 'POPULAR'));
      const compare = sale ? `<s style="font-size:11px;color:#94a3b8;margin-right:6px">${money(p.compare_at_price, p.currency)}</s>` : '';

      return `<a class="product" href="/shop">
        <div class="product-img">
          <span class="badge">${badge}</span>${image}
        </div>
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
      const response = await fetch('/api/home', { headers: { Accept: 'application/json' } });
      if (!response.ok) return;
      const data = await response.json();
      renderProducts(data.products || []);
    } catch (_) {
      // Keep the existing fallback card if the API is temporarily unavailable.
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    addTrustLinks();
    const schedule = window.requestIdleCallback || ((callback) => setTimeout(callback, 1));
    schedule(loadProducts, { timeout: 1500 });
  });
})();
