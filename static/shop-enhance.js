(() => {
  const css = `
  .shop-market-shell{margin-top:18px}
  #products{grid-template-columns:repeat(4,minmax(0,1fr));gap:20px}
  #products .card{display:flex;flex-direction:column;min-width:0;border:1px solid #ddd;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);transition:box-shadow .18s,transform .18s,border-color .18s}
  #products .card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.14);border-color:#bbb}
  #products .pic{height:285px;background:#fff;border-bottom:1px solid #eee;position:relative;display:grid;place-items:center}
  #products .pic img{width:100%;height:100%;padding:18px;object-fit:contain}
  #products .badge{left:10px;top:10px;background:#f3f4f6;color:#111827;border-radius:4px;padding:5px 8px;font-size:9px;box-shadow:none}
  #products .body{display:flex;flex-direction:column;flex:1;padding:14px 15px 15px}
  #products .body small{color:#6b7280;font-size:9px;font-weight:700;letter-spacing:.7px;text-transform:uppercase}
  #products .body h3{color:#111827;font-size:14px;line-height:1.4;margin:6px 0 4px;min-height:40px;font-weight:700}
  #products .desc{color:#5f6368;font-size:10px;line-height:1.45;height:30px;overflow:hidden}
  .market-meta{display:flex;align-items:center;gap:6px;margin:5px 0 2px;font-size:10px;color:#555}
  .market-stars{color:#f5a623;letter-spacing:1px;font-size:12px}
  .market-reviews{color:#1769aa}
  .market-stock{color:#067d62;font-weight:700}
  #products .price{color:#111;font-size:22px;font-weight:800;margin:9px 0 11px}
  #products .wide{margin-top:auto;border-radius:7px;padding:11px 12px;background:#ffd814;color:#111;border:1px solid #fcd200;font-size:10px;font-weight:800}
  #products .wide:hover{background:#f7ca00}
  .market-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 14px}
  .market-heading strong{font-size:17px;color:#111827}
  .market-heading span{font-size:10px;color:#64748b}
  @media(max-width:1100px){#products{grid-template-columns:repeat(3,minmax(0,1fr))}}
  @media(max-width:800px){#products{grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}#products .pic{height:240px}}
  @media(max-width:500px){#products{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}#products .pic{height:185px}#products .pic img{padding:9px}#products .body{padding:10px}#products .body h3{font-size:12px;min-height:35px}#products .desc{font-size:9px;height:27px}#products .price{font-size:18px;margin:7px 0 9px}.market-meta{gap:4px;font-size:8px}.market-stars{font-size:9px}}
  `;

  function enhance() {
    if (!document.getElementById('marketplace-shop-css')) {
      const style = document.createElement('style');
      style.id = 'marketplace-shop-css';
      style.textContent = css;
      document.head.appendChild(style);
    }
    const products = document.getElementById('products');
    if (products && !document.querySelector('.market-heading')) {
      const heading = document.createElement('div');
      heading.className = 'market-heading';
      heading.innerHTML = '<strong>Featured products</strong><span>Secure shopping · Fast checkout</span>';
      products.parentNode.insertBefore(heading, products);
    }
  }

  function decorate() {
    document.querySelectorAll('#products .card').forEach((card) => {
      if (card.querySelector('.market-meta')) return;
      const body = card.querySelector('.body');
      const price = body?.querySelector('.price');
      if (!body || !price) return;
      const meta = document.createElement('div');
      meta.className = 'market-meta';
      meta.innerHTML = '<span class="market-stars" aria-label="Product rating">★★★★★</span><span class="market-reviews">Reviews</span><span>·</span><span class="market-stock">In stock</span>';
      body.insertBefore(meta, price);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    enhance();
    decorate();
    const grid = document.getElementById('products');
    if (grid) new MutationObserver(decorate).observe(grid, {childList:true});
  });
})();
