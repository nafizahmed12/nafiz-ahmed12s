(() => {
  const $ = (s) => document.querySelector(s);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money = (v, currency = 'BDT') => `${currency === 'BDT' ? '৳' : currency + ' '}${esc(v)}`;

  function setCartCount(n) { const badge = $('#cartCount'); if (badge) badge.textContent = String(n ?? 0); }

  function applyHomeDesign() {
    if (document.getElementById('nafiz-home-design')) return;
    const style = document.createElement('style');
    style.id = 'nafiz-home-design';
    style.textContent = `
      :root{--ink:#07152f!important;--muted:#64748b!important;--line:#dbe4f0!important;--soft:#eef6ff!important;--brand:#2563eb!important;--brand2:#06b6d4!important}
      body{background:#f8fbff!important}
      .announcement{background:linear-gradient(90deg,#07152f,#123a72,#075985)!important}
      .header{background:rgba(248,251,255,.94)!important;border-bottom-color:#dbe7f5!important}
      .brand{color:#07152f!important}.brand em{color:#2563eb!important}
      .navlinks a:hover{color:#2563eb!important}.iconbtn:hover{background:#e8f2ff!important}
      .hero-grid{background:linear-gradient(135deg,#e8f3ff 0%,#f7fbff 48%,#e0f2fe 100%)!important}
      .hero h1 span{color:#2563eb!important}.dot{background:#2563eb!important}
      .btn-dark{background:linear-gradient(135deg,#2563eb,#0891b2)!important;box-shadow:0 12px 26px rgba(37,99,235,.25)!important}
      .btn-light{color:#1550b5!important;border-color:#bfdbfe!important}
      .hero-art{background:radial-gradient(circle at 50% 40%,#dbeafe,#bfdbfe 45%,#93c5fd 100%)!important}
      .phone{background:linear-gradient(150deg,#0f172a,#2563eb,#06b6d4)!important}
      .trust-icon{background:#eaf3ff!important;color:#2563eb!important}.trust strong{color:#0f274d!important}
      .section-head h2{color:#07152f!important}.viewall{color:#2563eb!important;border-color:#2563eb!important}
      .cat:hover{border-color:#93c5fd!important}.cat-icon{color:#2563eb!important}
      .products{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:24px!important}
      .product{padding:16px!important;border-color:#d8e5f3!important;border-radius:24px!important;box-shadow:0 8px 28px rgba(30,64,175,.06)!important}
      .product-media{height:380px!important;background:linear-gradient(145deg,#eff6ff,#e0f2fe)!important;border-radius:19px!important}
      .product-media img{object-fit:contain!important;mix-blend-mode:multiply!important;padding:12px!important;transform:scale(1.04)!important;transition:transform .3s ease!important}
      .product:hover .product-media img{transform:scale(1.1)!important}
      .product-name{font-size:17px!important}.price{font-size:20px!important;color:#1550b5!important}
      .badge{background:linear-gradient(135deg,#2563eb,#0891b2)!important}.heart{color:#2563eb!important}
      .promo{background:linear-gradient(135deg,#07152f,#0f3b73,#075985)!important}.promo-art{background:radial-gradient(circle at 50%,#2563eb,#07152f 65%)!important}
      .emailbox button{background:linear-gradient(135deg,#2563eb,#0891b2)!important}
      footer{background:#eef6ff!important}
      @media(max-width:1000px){.products{grid-template-columns:repeat(2,minmax(0,1fr))!important}.product-media{height:300px!important}}
      @media(max-width:600px){.products{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:12px!important}.product{padding:10px!important;border-radius:17px!important}.product-media{height:245px!important;border-radius:14px!important}.product-name{font-size:13px!important}.price{font-size:16px!important}.product-media img{padding:6px!important}}
    `;
    document.head.appendChild(style);
  }

  function renderFeatured(product) {
    const frame = $('#featuredProduct'); if (!frame) return;
    if (!product) { frame.dataset.state='empty'; $('#featuredName').textContent='No featured product yet'; $('#featuredStars').textContent=''; $('#featuredPrice').innerHTML=''; $('#featuredSale').hidden=true; return; }
    frame.dataset.state='ready'; const visual=$('#featuredVisual');
    if(product.image_url) visual.innerHTML=`<img src="${esc(product.image_url)}" alt="${esc(product.name)}" style="width:100%;height:100%;object-fit:cover;border-radius:17px">`;
    $('#featuredName').textContent=product.name; $('#featuredStars').textContent='';
    const priceEl=$('#featuredPrice'); const compareHtml=product.compare_at_price?`<s>${money(product.compare_at_price,product.currency)}</s>`:''; priceEl.innerHTML=`${compareHtml}${money(product.price,product.currency)}`;
    const saleEl=$('#featuredSale');
    if(product.compare_at_price&&Number(product.compare_at_price)>Number(product.price)){const pct=Math.round((1-Number(product.price)/Number(product.compare_at_price))*100);saleEl.textContent=`UP TO ${pct}% OFF`;saleEl.hidden=false;}else saleEl.hidden=true;
  }

  function renderTrending(products) {
    const grid=$('#trendingGrid'); if(!grid)return;
    if(!products||products.length===0){grid.dataset.state='empty';grid.innerHTML='<p class="trendingEmpty">No trending products yet — check back soon.</p>';return;}
    grid.dataset.state='ready';
    grid.innerHTML=products.slice(0,4).map((p,i)=>{const image=p.image_url?`<img src="${esc(p.image_url)}" alt="${esc(p.name)}" loading="lazy" style="width:100%;height:100%;object-fit:cover">`:'<div class="shape"></div>';const compare=p.compare_at_price&&Number(p.compare_at_price)>Number(p.price)?`<s>${money(p.compare_at_price,p.currency)}</s>`:'';const badge=p.featured||i<2?'<span class="badge hot">TRENDING</span>':'<span class="badge">NEW</span>';return `<a class="card" href="/shop"><div class="pic">${badge}<button class="heart" onclick="event.preventDefault()" aria-label="Save">♡</button>${image}</div><div class="cardBody"><span class="cat">${esc(p.category)}</span><h3>${esc(p.name)}</h3><div class="priceRow"><span class="money">${compare}${money(p.price,p.currency)}</span><button class="plus" type="button" data-add="${p.id}" aria-label="Add ${esc(p.name)} to cart">＋</button></div></div></a>`;}).join('');
    grid.querySelectorAll('[data-add]').forEach(btn=>btn.addEventListener('click',async(e)=>{e.preventDefault();e.stopPropagation();btn.disabled=true;try{const r=await fetch('/api/cart/items',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:Number(btn.dataset.add),quantity:1})});if(r.status===401){window.location.href='/user-login';return;}const body=await r.json();if(!r.ok){alert(body.error||'Could not add this product.');return;}setCartCount(body.item_count);btn.textContent='✓';setTimeout(()=>{btn.textContent='＋';},900);}finally{btn.disabled=false;}}));
  }

  async function loadHome(){try{const res=await fetch('/api/home',{headers:{Accept:'application/json'}});if(!res.ok)return;const data=await res.json();setCartCount(data.cart_count);const featured=data.products?.find((p)=>p.featured)||data.products?.[0]||null;renderFeatured(featured);renderTrending(data.products);}catch(_){} }
  function setupNewsletter(){const form=$('.news .form');if(!form)return;form.addEventListener('submit',async(e)=>{e.preventDefault();const input=form.querySelector('input[type=email]');const button=form.querySelector('button');const email=input?.value.trim();if(!email)return;button.disabled=true;try{const csrfToken=form.querySelector('input[name=csrf_token]')?.value||'';const body=new URLSearchParams({subscriber_email:email,csrf_token:csrfToken});const r=await fetch('/subscribe',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});const text=await r.text();if(!r.ok)throw new Error(text);input.value='';button.textContent='Subscribed ✓';}catch(err){alert(err.message||'Subscription failed.');}finally{button.disabled=false;}});}
  function setupCountdown(){const boxes=document.querySelectorAll('.time b');if(boxes.length!==3)return;let end=Date.now()+(6*3600+42*60+18)*1000;const tick=()=>{let seconds=Math.max(0,Math.floor((end-Date.now())/1000));const h=Math.floor(seconds/3600);seconds%=3600;const m=Math.floor(seconds/60);const s=seconds%60;boxes[0].textContent=String(h).padStart(2,'0');boxes[1].textContent=String(m).padStart(2,'0');boxes[2].textContent=String(s).padStart(2,'0');if(end<=Date.now())end=Date.now()+24*3600*1000;};tick();setInterval(tick,1000);}
  document.addEventListener('DOMContentLoaded',()=>{applyHomeDesign();loadHome();setupNewsletter();setupCountdown();});
})();
