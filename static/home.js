(() => {
  const $ = (s) => document.querySelector(s);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money = (v, c='BDT') => `${c === 'BDT' ? '৳' : `${c} `}${esc(v)}`;
  const setCart = (n) => { const x=$('#cartCount'); if(x)x.textContent=String(n??0); };
  const iconFor = (slug='') => ({mobile:'📱',mobiles:'📱',laptop:'💻',accessories:'🎧',electronics:'⚡',fashion:'👕',home:'🏠'}[String(slug).toLowerCase()] || '🛍️');
  function categoryCard(c){ return `<a class="category" href="/shop?category=${encodeURIComponent(c.slug)}"><div class="cat-icon">${iconFor(c.slug)}</div><b>${esc(c.name)}</b><span>${esc(c.product_count)} products</span></a>`; }
  function card(p,i=0){
    const old=p.compare_at_price&&Number(p.compare_at_price)>Number(p.price)?`<span class="old">${money(p.compare_at_price,p.currency)}</span>`:'';
    const discount=p.compare_at_price&&Number(p.compare_at_price)>Number(p.price)?`${Math.round((1-Number(p.price)/Number(p.compare_at_price))*100)}% OFF`:(i<2?'TRENDING':'NEW');
    const image=p.image_url?`<img src="${esc(p.image_url)}" alt="${esc(p.name)}" loading="lazy" onerror="this.style.display='none'">`:`<span style="font-size:42px">${iconFor(p.category_slug)}</span>`;
    return `<article class="card"><div class="pic"><span class="hot">${discount}</span><button class="heart" type="button" aria-label="Save product">♡</button>${image}</div><div class="body"><div class="type">${esc(p.category||'Product')}</div><h3><a href="/shop?search=${encodeURIComponent(p.name||'')}">${esc(p.name)}</a></h3><div class="desc">${esc(p.description||'Quality product from our catalog.')}</div><div class="rating"><span>★★★★★</span> <small>Popular choice</small></div><div class="bottom"><div><span class="price">${money(p.price,p.currency)}</span>${old}</div><button class="plus" type="button" data-add="${esc(p.id)}" aria-label="Add to cart">＋</button></div></div></article>`;
  }
  function bindCart(){document.querySelectorAll('[data-add]').forEach(btn=>btn.addEventListener('click',async()=>{btn.disabled=true;try{const r=await fetch('/api/cart/items',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:Number(btn.dataset.add),quantity:1})});if(r.status===401){location.href='/user-login';return;}const d=await r.json();if(!r.ok){alert(d.error||'Could not add this product.');return;}setCart(d.item_count);btn.textContent='✓';setTimeout(()=>btn.textContent='＋',900);}catch(_){alert('Could not add this product.');}finally{btn.disabled=false;}}));}
  function render(d){
    const cats=d.categories||[],products=d.products||[];
    const c=$('#categories');if(c)c.innerHTML=cats.length?cats.map(categoryCard).join(''):`<a class="category" href="/shop"><div class="cat-icon">🛍️</div><b>All Products</b><span>Browse catalog</span></a>`;
    const sale=$('#products'),trend=$('#trendingGrid');
    if(!products.length){if(sale)sale.innerHTML='<p>No products available yet.</p>';if(trend)trend.innerHTML='';return;}
    if(sale)sale.innerHTML=products.slice(0,4).map(card).join('');
    if(trend)trend.innerHTML=products.slice(4,12).map((p,i)=>card(p,i+4)).join('')||products.slice(0,8).map((p,i)=>card(p,i)).join('');
    setCart(d.cart_count||0);bindCart();
  }
  function search(){const f=$('#homeSearch'),i=$('#homeSearchInput');if(f)f.addEventListener('submit',e=>{e.preventDefault();const q=(i?.value||'').trim();location.href=q?`/shop?search=${encodeURIComponent(q)}`:'/shop';});}
  function newsletter(){const f=$('.form');if(!f)return;f.addEventListener('submit',async e=>{e.preventDefault();const i=f.querySelector('input[type=email]'),b=f.querySelector('button');if(!i?.value.trim())return;b.disabled=true;try{const r=await fetch('/subscribe',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({subscriber_email:i.value.trim(),csrf_token:f.querySelector('[name=csrf_token]')?.value||''})});if(!r.ok)throw Error();i.value='';b.textContent='Subscribed ✓';}catch(_){alert('Subscription failed.');}finally{b.disabled=false;}});}
  function timer(){const h=$('#hh'),m=$('#mm'),s=$('#ss');if(!h||!m||!s)return;let end=Date.now()+((6*3600+42*60+18)*1000);setInterval(()=>{let n=Math.max(0,Math.floor((end-Date.now())/1000));h.textContent=String(Math.floor(n/3600)).padStart(2,'0');n%=3600;m.textContent=String(Math.floor(n/60)).padStart(2,'0');s.textContent=String(n%60).padStart(2,'0');if(Date.now()>=end)end=Date.now()+86400000;},1000);}
  async function load(){try{const r=await fetch('/api/home',{headers:{Accept:'application/json'}});if(!r.ok)throw Error();render(await r.json());}catch(_){const sale=$('#products');if(sale)sale.innerHTML='<p>Products could not be loaded. Please try again.</p>';}}
  document.addEventListener('DOMContentLoaded',()=>{search();newsletter();timer();load();});
})();