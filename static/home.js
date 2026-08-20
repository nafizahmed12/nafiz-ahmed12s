(() => {
  const $ = (s) => document.querySelector(s);
  const esc = (v) => String(v ?? '').replace(/[&<>\"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
  const money = (v, currency='BDT') => `${currency === 'BDT' ? '৳' : currency + ' '}${esc(v)}`;

  async function loadHome() {
    try {
      const res = await fetch('/api/home', { headers: { Accept: 'application/json' } });
      if (!res.ok) return;
      const data = await res.json();
      const count = $('.cart-count');
      if (count) count.textContent = data.cart_count || '0';

      const grid = $('.prod-grid');
      if (grid && data.products?.length) {
        grid.innerHTML = data.products.slice(0, 8).map((p, i) => {
          const image = p.image_url
            ? `<img src="${esc(p.image_url)}" alt="${esc(p.name)}" loading="lazy" style="width:100%;height:100%;object-fit:cover;border-radius:18px">`
            : '<div class="prod-blob" aria-hidden="true"></div>';
          const compare = p.compare_at_price && Number(p.compare_at_price) > Number(p.price)
            ? `<s>${money(p.compare_at_price, p.currency)}</s>` : '';
          const badge = p.featured || i < 2 ? '<span class="prod-badge hot">🔥 Trending</span>' : '<span class="prod-badge">New</span>';
          return `<article class="prod-card">
            <a href="${esc('/shop')}" aria-label="View ${esc(p.name)}">
              <div class="prod-img">${badge}<button class="wish-btn" type="button" aria-label="Save" data-wish="${p.id}">♡</button>${image}</div>
              <div class="prod-body"><span class="prod-cat">${esc(p.category)}</span><h3>${esc(p.name)}</h3>
                <div class="prod-stars">★★★★★<span>Popular</span></div>
                <div class="prod-price-row"><div class="prod-price">${compare}${money(p.price, p.currency)}</div>
                  <button class="add-btn" type="button" data-add="${p.id}" aria-label="Add ${esc(p.name)} to cart">+</button>
                </div>
              </div>
            </a>
          </article>`;
        }).join('');

        grid.querySelectorAll('[data-add]').forEach((btn) => btn.addEventListener('click', async (e) => {
          e.preventDefault(); e.stopPropagation();
          btn.disabled = true;
          try {
            const r = await fetch('/api/cart/items', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({product_id:Number(btn.dataset.add), quantity:1}) });
            if (r.status === 401) { window.location.href = '/user-login'; return; }
            const body = await r.json();
            if (!r.ok) { alert(body.error || 'Could not add this product.'); return; }
            const badge = $('.cart-count'); if (badge) badge.textContent = body.item_count ?? 0;
            btn.textContent = '✓';
            setTimeout(() => { btn.textContent = '+'; }, 900);
          } finally { btn.disabled = false; }
        }));
      }

      const catGrid = $('.cat-scroll');
      if (catGrid && data.categories?.length) {
        const icons = ['📱','🏠','💄','👕','🎮','✨'];
        catGrid.innerHTML = data.categories.map((c, i) => `<a class="cat-pill" href="${esc('/shop?category=' + encodeURIComponent(c.slug))}"><span class="em">${icons[i % icons.length]}</span><span>${esc(c.name)}</span></a>`).join('');
      }
    } catch (_) { /* Keep server-rendered fallback visible if the API is unavailable. */ }
  }

  function setupNewsletter() {
    const form = $('.nl-form');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = form.querySelector('input[type=email]');
      const button = form.querySelector('button');
      const email = input?.value.trim();
      if (!email) return;
      button.disabled = true;
      try {
        const body = new URLSearchParams({ subscriber_email: email });
        const r = await fetch('/subscribe', { method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body });
        const text = await r.text();
        if (!r.ok) throw new Error(text);
        input.value = '';
        button.textContent = 'Subscribed ✓';
      } catch (err) { alert(err.message || 'Subscription failed.'); }
      finally { button.disabled = false; }
    });
  }

  function setupCountdown() {
    const boxes = document.querySelectorAll('.count-box b');
    if (boxes.length !== 3) return;
    let end = Date.now() + (6 * 3600 + 42 * 60 + 18) * 1000;
    const tick = () => {
      let seconds = Math.max(0, Math.floor((end - Date.now()) / 1000));
      const h = Math.floor(seconds / 3600); seconds %= 3600;
      const m = Math.floor(seconds / 60); const s = seconds % 60;
      boxes[0].textContent = String(h).padStart(2,'0');
      boxes[1].textContent = String(m).padStart(2,'0');
      boxes[2].textContent = String(s).padStart(2,'0');
      if (end <= Date.now()) end = Date.now() + 24 * 3600 * 1000;
    };
    tick(); setInterval(tick, 1000);
  }

  document.addEventListener('DOMContentLoaded', () => { loadHome(); setupNewsletter(); setupCountdown(); });
})();
