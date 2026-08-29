(() => {
  const css = `
  .grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;align-items:stretch}
  .card{position:relative;border:1px solid #e5e7eb;border-radius:16px;background:#fff;box-shadow:0 2px 8px rgba(15,23,42,.06);transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}
  .card:hover{transform:translateY(-3px);box-shadow:0 12px 28px rgba(15,23,42,.12);border-color:#cbd5e1}
  .pic{height:300px;background:#f8fafc;border-bottom:1px solid #eef2f7}
  .pic img{padding:20px;object-fit:contain;transition:transform .25s ease}
  .card:hover .pic img{transform:scale(1.05)}
  .badge{left:12px;top:12px;background:#111827;color:#fff;border-radius:7px;padding:6px 9px;font-size:9px;box-shadow:none}
  .body{padding:15px 16px 16px;display:flex;flex-direction:column;min-height:205px}
  .body small{font-size:9px;color:#6b7280;letter-spacing:.7px}
  .body h3{font-size:14px;line-height:1.45;margin:7px 0 5px;min-height:41px;color:#111827}
  .desc{height:34px;font-size:10px;color:#6b7280;line-height:1.5}
  .price{font-size:21px;margin:10px 0 12px;color:#111827}
  .wide{margin-top:auto;border-radius:9px;font-size:10px;padding:11px 14px}
  .market-meta{display:flex;align-items:center;gap:8px;margin:2px 0 4px;font-size:10px;color:#64748b}
  .market-stars{letter-spacing:1px;color:#f59e0b;font-size:11px}
  .market-stock{color:#16a34a;font-weight:800}
  @media(max-width:1100px){.grid{grid-template-columns:repeat(3,minmax(0,1fr))}.pic{height:280px}}
  @media(max-width:800px){.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.pic{height:240px}.body{padding:12px}.body h3{font-size:13px}.price{font-size:19px}}
  @media(max-width:500px){.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.pic{height:185px}.pic img{padding:10px}.body{padding:10px}.body h3{font-size:12px;min-height:36px}.desc{font-size:9px;height:30px}.price{font-size:17px;margin:8px 0}.wide{font-size:9px;padding:10px 8px}}
  `;

  function enhance() {
    if (document.getElementById('marketplace-shop-css')) return;
    const style = document.createElement('style');
    style.id = 'marketplace-shop-css';
    style.textContent = css;
    document.head.appendChild(style);
  }

  function decorate() {
    document.querySelectorAll('#products .card').forEach((card) => {
      if (card.querySelector('.market-meta')) return;
      const body = card.querySelector('.body');
      const category = body?.querySelector('small');
      const price = body?.querySelector('.price');
      if (!body || !price) return;
      const meta = document.createElement('div');
      meta.className = 'market-meta';
      meta.innerHTML = '<span class="market-stars">★★★★★</span><span>Product</span><span class="market-stock">In stock</span>';
      body.insertBefore(meta, price);
      if (category) category.setAttribute('aria-label', 'Category');
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    enhance();
    decorate();
    const grid = document.getElementById('products');
    if (grid) new MutationObserver(decorate).observe(grid, {childList:true});
  });
})();
