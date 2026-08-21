(() => {
  const $ = (s) => document.querySelector(s);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money = (v, currency = 'BDT') => `${currency === 'BDT' ? '৳' : currency + ' '}${esc(v)}`;

  function setCartCount(n) {
    const badge = $('#cartCount');
    if (badge) badge.textContent = String(n ?? 0);
  }

  function renderFeatured(product) {
    const frame = $('#featuredProduct');
    if (!frame) return;
    if (!product) {
      frame.dataset.state = 'empty';
      $('#featuredName').textContent = 'No featured product yet';
      $('#featuredStars').textContent = '';
      $('#featuredPrice').innerHTML = '';
      $('#featuredSale').hidden = true;
      return;
    }
    frame.dataset.state = 'ready';

    const visual = $('#featuredVisual');
    if (product.image_url) {
      visual.innerHTML = `<img src="${esc(product.image_url)}" alt="${esc(product.name)}" style="width:100%;height:100%;object-fit:cover;border-radius:17px">`;
    }
    // If there's no image, the existing CSS placeholder shape stays visible — this is
    // an intentional fallback, not the bug: it only shows when a product truly has no image.

    $('#featuredName').textContent = product.name;
    // /api/home does not currently return a rating — leave this blank rather than
    // fabricating stars. See note to Nafiz: rating data needs to be added server-side.
    $('#featuredStars').textContent = '';

    const priceEl = $('#featuredPrice');
    const compareHtml = product.compare_at_price
      ? `<s>${money(product.compare_at_price, product.currency)}</s>` : '';
    priceEl.innerHTML = `${compareHtml}${money(product.price, product.currency)}`;

    const saleEl = $('#featuredSale');
    if (product.compare_at_price && Number(product.compare_at_price) > Number(product.price)) {
      const pct = Math.round((1 - Number(product.price) / Number(product.compare_at_price)) * 100);
      saleEl.textContent = `UP TO ${pct}% OFF`;
      saleEl.hidden = false;
    } else {
      saleEl.hidden = true;
    }
  }

  function renderTrending(products) {
    const grid = $('#trendingGrid');
    if (!grid) return;

    if (!products || products.length === 0) {
      grid.dataset.state = 'empty';
      grid.innerHTML = '<p class="trendingEmpty">No trending products yet — check back soon.</p>';
      return;
    }

    grid.dataset.state = 'ready';
    grid.innerHTML = products.slice(0, 4).map((p, i) => {
      const image = p.image_url
        ? `<img src="${esc(p.image_url)}" alt="${esc(p.name)}" loading="lazy" style="width:100%;height:100%;object-fit:cover">`
        : '<div class="shape"></div>';
      const compare = p.compare_at_price && Number(p.compare_at_price) > Number(p.price)
        ? `<s>${money(p.compare_at_price, p.currency)}</s>` : '';
      const badge = p.featured || i < 2
        ? '<span class="badge hot">TRENDING</span>'
        : '<span class="badge">NEW</span>';
      // No rating field from /api/home yet, so the rating row is omitted rather than faked.
      return `<a class="card" href="/shop"><div class="pic">${badge}<button class="heart" onclick="event.preventDefault()" aria-label="Save">♡</button>${image}</div><div class="cardBody"><span class="cat">${esc(p.category)}</span><h3>${esc(p.name)}</h3><div class="priceRow"><span class="money">${compare}${money(p.price, p.currency)}</span><button class="plus" type="button" data-add="${p.id}" aria-label="Add ${esc(p.name)} to cart">＋</button></div></div></a>`;
    }).join('');

    grid.querySelectorAll('[data-add]').forEach((btn) => btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      btn.disabled = true;
      try {
        const r = await fetch('/api/cart/items', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_id: Number(btn.dataset.add), quantity: 1 })
        });
        if (r.status === 401) { window.location.href = '/user-login'; return; }
        const body = await r.json();
        if (!r.ok) { alert(body.error || 'Could not add this product.'); return; }
        setCartCount(body.item_count);
        btn.textContent = '✓';
        setTimeout(() => { btn.textContent = '＋'; }, 900);
      } finally {
        btn.disabled = false;
      }
    }));
  }

  async function loadHome() {
    try {
      const res = await fetch('/api/home', { headers: { Accept: 'application/json' } });
      if (!res.ok) return; // Keep server-rendered fallback state visible if the API errors.
      const data = await res.json();

      setCartCount(data.cart_count);

      const featured = data.products?.find((p) => p.featured) || data.products?.[0] || null;
      renderFeatured(featured);
      renderTrending(data.products);
    } catch (_) {
      // Network/parse failure: leave the loading/fallback state as-is rather than
      // showing broken partial content.
    }
  }

  function setupNewsletter() {
    const form = $('.news .form');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = form.querySelector('input[type=email]');
      const button = form.querySelector('button');
      const email = input?.value.trim();
      if (!email) return;
      button.disabled = true;
      try {
        const csrfToken = form.querySelector('input[name=csrf_token]')?.value || '';
        const body = new URLSearchParams({ subscriber_email: email, csrf_token: csrfToken });
        const r = await fetch('/subscribe', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body });
        const text = await r.text();
        if (!r.ok) throw new Error(text);
        input.value = '';
        button.textContent = 'Subscribed ✓';
      } catch (err) {
        alert(err.message || 'Subscription failed.');
      } finally {
        button.disabled = false;
      }
    });
  }

  function setupCountdown() {
    const boxes = document.querySelectorAll('.time b');
    if (boxes.length !== 3) return;
    let end = Date.now() + (6 * 3600 + 42 * 60 + 18) * 1000;
    const tick = () => {
      let seconds = Math.max(0, Math.floor((end - Date.now()) / 1000));
      const h = Math.floor(seconds / 3600); seconds %= 3600;
      const m = Math.floor(seconds / 60); const s = seconds % 60;
      boxes[0].textContent = String(h).padStart(2, '0');
      boxes[1].textContent = String(m).padStart(2, '0');
      boxes[2].textContent = String(s).padStart(2, '0');
      if (end <= Date.now()) end = Date.now() + 24 * 3600 * 1000;
    };
    tick();
    setInterval(tick, 1000);
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadHome();
    setupNewsletter();
    setupCountdown();
  });
})();
