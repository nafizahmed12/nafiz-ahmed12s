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

  function initCategoryHoverMenus(){
    const nav=document.querySelector('.nav .wrap');
    if(!nav || nav.dataset.categoryMenusReady==='1') return;
    nav.dataset.categoryMenusReady='1';
    const menuData={
      'Home':[['Featured Products','/shop'],['New Arrivals','/shop?category=new'],['Hot Offers','/shop?category=offers'],['All Products','/shop']],
      'Apple Products':[['iPhone','/phones?brand=Apple'],['iPad','/shop?category=tablets'],['MacBook','/shop?category=computers'],['Apple Watch','/shop?category=wearables'],['AirPods','/shop?category=audio'],['Accessories','/shop?category=accessories']],
      'iPhone':[['All iPhone','/phones?brand=Apple'],['Latest iPhone','/phones?brand=Apple'],['iPhone Deals','/shop?category=offers'],['Compare Phones','/phone-compare']],
      'Phones':[['All Phones','/phones'],['Apple','/phones?brand=Apple'],['Samsung','/phones?brand=Samsung'],['Xiaomi','/phones?brand=Xiaomi'],['Phone Deals','/shop?category=offers']],
      'Tablets & Accessories':[['All Tablets','/shop?category=tablets'],['iPad','/shop?category=tablets'],['Tablet Accessories','/shop?category=accessories'],['Tablet Deals','/shop?category=offers']],
      'Desktop':[['Laptops','/shop?category=computers'],['Desktop PCs','/shop?category=computers'],['Monitors','/shop?category=computers'],['Computer Accessories','/shop?category=accessories']],
      'Gadgets & Accessories':[['All Gadgets','/shop?category=gadgets'],['Audio','/shop?category=audio'],['Wearables','/shop?category=wearables'],['Gaming','/shop?category=gaming'],['Accessories','/shop?category=accessories']],
      'Appliances':[['All Appliances','/shop?category=appliances'],['Home Appliances','/shop?category=appliances'],['Smart Home','/shop?category=appliances'],['Appliance Offers','/shop?category=offers']],
      'Lifestyle':[['All Lifestyle','/shop?category=lifestyle'],['Bags & Essentials','/shop?category=lifestyle'],['Personal Tech','/shop?category=gadgets'],['Lifestyle Offers','/shop?category=offers']],
      'Camera & Networking':[['Cameras','/shop?category=camera'],['Networking','/shop?category=camera'],['Camera Accessories','/shop?category=accessories'],['Deals','/shop?category=offers']],
      'Offer':[['All Offers','/shop?category=offers'],['Phone Deals','/shop?category=offers'],['Gadget Deals','/shop?category=offers'],['Latest Deals','/shop?category=offers']]
    };
    const existingApple=nav.querySelector('.apple-menu-wrap');
    [...nav.children].forEach(item=>{
      if(item===existingApple) return;
      if(item.tagName!=='A') return;
      const label=item.textContent.trim();
      const data=menuData[label];
      if(!data) return;
      const wrap=document.createElement('div');
      wrap.className='nav-hover-wrap';
      wrap.innerHTML=`<button class="nav-hover-trigger" type="button" aria-expanded="false">${esc(label)} <span class="nav-hover-chevron">⌄</span></button><div class="nav-hover-menu" role="menu">${data.map(([name,url])=>`<a href="${url}" role="menuitem"><strong>${esc(name)}</strong><span>Explore ${esc(name.toLowerCase())}</span></a>`).join('')}</div>`;
      item.replaceWith(wrap);
      const trigger=wrap.querySelector('.nav-hover-trigger');
      const close=()=>{wrap.classList.remove('is-open');trigger.setAttribute('aria-expanded','false');};
      const open=()=>{document.querySelectorAll('.nav-hover-wrap.is-open').forEach(x=>x!==wrap&&x.classList.remove('is-open'));wrap.classList.add('is-open');trigger.setAttribute('aria-expanded','true');};
      trigger.addEventListener('click',e=>{e.preventDefault();wrap.classList.contains('is-open')?close():open();});
      wrap.addEventListener('mouseenter',open);
      wrap.addEventListener('mouseleave',()=>setTimeout(()=>{if(!wrap.matches(':hover'))close();},80));
      wrap.addEventListener('focusin',open);
      wrap.addEventListener('focusout',e=>{if(!wrap.contains(e.relatedTarget))close();});
    });
    const style=document.createElement('style');
    style.textContent=`.nav-hover-wrap{position:relative;height:46px;display:flex;align-items:center}.nav-hover-trigger{height:46px;padding:14px 13px;border:0;background:transparent;color:inherit;font:inherit;font-size:11px;font-weight:650;cursor:pointer;white-space:nowrap}.nav-hover-trigger:hover,.nav-hover-wrap.is-open .nav-hover-trigger{color:var(--r)}.nav-hover-chevron{display:inline-block;margin-left:4px;font-size:9px;transition:transform .16s}.nav-hover-wrap.is-open .nav-hover-chevron{transform:rotate(180deg)}.nav-hover-menu{position:absolute;top:45px;left:0;min-width:245px;padding:10px;background:#fff;border:1px solid var(--line);border-radius:0 0 13px 13px;box-shadow:0 18px 40px rgba(0,0,0,.15);opacity:0;visibility:hidden;transform:translateY(-7px);pointer-events:none;transition:.16s;z-index:100}.nav-hover-wrap:hover .nav-hover-menu,.nav-hover-wrap.is-open .nav-hover-menu{opacity:1;visibility:visible;transform:translateY(0);pointer-events:auto}.nav-hover-menu a{display:block!important;padding:10px 11px!important;border-radius:9px!important;color:inherit!important;background:transparent!important}.nav-hover-menu a:hover{background:#f6f6f6!important;color:var(--r)!important}.nav-hover-menu a strong{display:block;font-size:10px}.nav-hover-menu a span{display:block;color:#888;font-size:8px;margin-top:2px}.nav-hover-wrap+.nav-hover-wrap{}.apple-menu-wrap{z-index:101}@media(max-width:760px){.nav-hover-wrap,.nav-hover-trigger{height:42px}.nav-hover-trigger{padding:13px 9px;font-size:9px}.nav-hover-menu{position:fixed;top:110px;left:10px;right:10px;min-width:0;max-height:70vh;overflow:auto;border-radius:12px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px;padding:10px}.nav-hover-menu a{padding:10px!important}.nav-hover-menu a span{display:none}}`;
    document.head.appendChild(style);
    document.addEventListener('click',e=>{if(!e.target.closest('.nav-hover-wrap'))document.querySelectorAll('.nav-hover-wrap.is-open').forEach(closeWrap=>{closeWrap.classList.remove('is-open');const t=closeWrap.querySelector('.nav-hover-trigger');if(t)t.setAttribute('aria-expanded','false');});});
    document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.nav-hover-wrap.is-open').forEach(closeWrap=>{closeWrap.classList.remove('is-open');const t=closeWrap.querySelector('.nav-hover-trigger');if(t)t.setAttribute('aria-expanded','false');});});
  }

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
  function mobileNavSize(){
    const style=document.createElement('style');
    style.textContent=`@media(max-width:420px){.bottom-nav{min-height:82px!important;padding:8px 6px calc(10px + env(safe-area-inset-bottom))!important}.bottom-nav a{min-height:62px!important;display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;gap:4px!important;font-size:26px!important;font-weight:700!important;line-height:1!important}.bottom-nav a>span,.bottom-nav a>i,.bottom-nav a>.icon,.bottom-nav a>svg,.bottom-nav a>img{width:28px!important;height:28px!important;font-size:26px!important;line-height:28px!important}.bottom-nav b{font-size:11px!important;line-height:1!important;margin:0!important;font-weight:700!important}.bottom-nav .badge{min-width:20px!important;height:20px!important;font-size:10px!important;line-height:20px!important}body{padding-bottom:92px!important}}`;
    document.head.appendChild(style);
  }
  async function load(){try{const r=await fetch('/api/home',{headers:{Accept:'application/json'}});if(!r.ok)throw Error();render(await r.json());}catch(_){const sale=$('#products');if(sale)sale.innerHTML='<p>Products could not be loaded. Please try again.</p>';}}
  document.addEventListener('DOMContentLoaded',()=>{mobileNavSize();initCategoryHoverMenus();search();newsletter();timer();load();});
})();