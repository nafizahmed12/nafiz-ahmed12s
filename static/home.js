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
      :root{--ink:#f7f8ff!important;--muted:#9299ad!important;--line:#252a3a!important;--soft:#171b27!important;--brand:#4aa8ff!important;--brand2:#a44cff!important;--bg:#080a10!important}
      html{background:#080a10!important}
      body{background:radial-gradient(circle at 50% -10%,#171a2b 0,#0b0d14 42%,#07090e 100%)!important;color:#f7f8ff!important}
      .container{width:min(1280px,calc(100% - 36px))!important}
      .announcement{background:linear-gradient(90deg,#090b12,#17122a,#090b12)!important;border-bottom:1px solid #202535!important;color:#aeb5c8!important}
      .announcement b{color:#fff!important}
      .header{background:rgba(8,10,16,.86)!important;border-bottom:1px solid rgba(50,56,75,.7)!important;backdrop-filter:blur(22px)!important}
      .brand{color:#fff!important;font-size:22px!important}.brand em{color:#8d65ff!important}
      .navlinks a{color:#9da5b9!important}.navlinks a:hover{color:#fff!important}
      .iconbtn{color:#e9ecf5!important}.iconbtn:hover{background:#171b28!important}.count{background:linear-gradient(135deg,#4aa8ff,#a44cff)!important}
      .hero{padding-top:22px!important}
      .hero-grid{min-height:470px!important;border:1px solid #252b3b!important;border-radius:30px!important;background:radial-gradient(circle at 80% 45%,rgba(96,54,190,.32),transparent 38%),linear-gradient(135deg,#10131d,#111421 55%,#171126)!important;box-shadow:0 25px 80px rgba(0,0,0,.28)!important}
      .hero-copy{padding:58px 62px!important}.eyebrow{color:#aeb6ca!important}.dot{background:linear-gradient(135deg,#4aa8ff,#a44cff)!important}
      .hero h1{color:#fff!important;font-size:clamp(44px,5.4vw,74px)!important}.hero h1 span{color:#9f6cff!important}
      .hero p{color:#9ba3b8!important}.btn{border-radius:15px!important}.btn-dark{background:linear-gradient(135deg,#329fff,#9b45ff)!important;color:#fff!important;box-shadow:0 14px 35px rgba(112,65,255,.28)!important}.btn-light{background:#171b27!important;color:#e9edf7!important;border:1px solid #2b3245!important}
      .hero-art{background:radial-gradient(circle at 50% 45%,#25213f,#121523 55%,#0a0c13)!important}.orb{width:390px!important;height:390px!important;background:radial-gradient(circle,rgba(97,75,255,.32),rgba(54,169,255,.07) 48%,transparent 70%)!important}.phone{background:linear-gradient(150deg,#05060a,#252b3c,#111421)!important;box-shadow:22px 28px 70px rgba(0,0,0,.55),inset 0 0 0 2px rgba(255,255,255,.12)!important}.screen{background:radial-gradient(circle at 68% 25%,#6d5cff 0,#354b86 22%,#171d2d 58%,#07090e 100%)!important}.floating{background:rgba(20,24,36,.84)!important;color:#e8ecf6!important;border-color:#343b50!important;box-shadow:0 15px 35px rgba(0,0,0,.35)!important}.f1{left:7%!important}.f2{right:7%!important}
      .trust{background:#10131c!important;border-color:#252b3b!important}.trust-item{border-color:#252b3b!important}.trust-icon{background:#191e2b!important;color:#69b7ff!important}.trust strong{color:#f3f5fb!important}.trust span{color:#81899d!important}
      .section-head h2{color:#fff!important}.section-head p{color:#858da2!important}.viewall{color:#9b73ff!important;border-color:#9b73ff!important}
      .cats{gap:12px!important}.cat{min-height:104px!important;background:#10131c!important;border-color:#252b3b!important;color:#fff!important;border-radius:18px!important}.cat:hover{background:#151a27!important;border-color:#4b4e72!important;box-shadow:0 15px 35px rgba(0,0,0,.22)!important}.cat-icon{color:#7cbcff!important}.cat small{color:#7e879c!important}
      .products{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:18px!important}
      .product{background:linear-gradient(145deg,#11151f,#0e1119)!important;border-color:#292f40!important;border-radius:24px!important;padding:12px!important;box-shadow:0 15px 40px rgba(0,0,0,.22)!important}
      .product:hover{border-color:#465070!important;box-shadow:0 20px 50px rgba(0,0,0,.38)!important;transform:translateY(-5px)!important}
      .product-media{height:370px!important;background:radial-gradient(circle at 50% 38%,#252b3d,#141925 55%,#0d1017 100%)!important;border-radius:20px!important}
      .product-media img{object-fit:contain!important;mix-blend-mode:normal!important;padding:14px!important;transform:scale(1.04)!important;filter:drop-shadow(0 22px 25px rgba(0,0,0,.34))!important;transition:transform .3s ease,filter .3s ease!important}.product:hover .product-media img{transform:scale(1.11)!important;filter:drop-shadow(0 28px 30px rgba(89,83,255,.2))!important}
      .badge{background:linear-gradient(135deg,#35a7ff,#8b4dff)!important;border-radius:9px!important}.heart{background:rgba(11,14,22,.8)!important;color:#fff!important;border:1px solid #30374a!important}
      .product-info{padding:16px 5px 5px!important}.product-type{color:#778197!important}.product-name{color:#fff!important;font-size:17px!important}.rating{color:#8b93a7!important}.stars{color:#ffc857!important}.price-row{margin-top:14px!important}.price{font-size:20px!important;color:#fff!important}.stock{color:#7f899f!important}
      .promo{background:radial-gradient(circle at 75% 50%,rgba(130,64,255,.35),transparent 30%),linear-gradient(135deg,#111521,#0d1018)!important;border:1px solid #282e40!important;min-height:300px!important}.promo h2{color:#fff!important}.promo p{color:#8e97ab!important}.promo-art{background:radial-gradient(circle at 50%,#3d2e87,#15182a 55%,#0a0c12)!important}.promo-ring{border-color:rgba(165,126,255,.32)!important}.promo-ring b{color:#fff!important}
      .newsletter{color:#fff!important}.newsletter h2{color:#fff!important}.newsletter p{color:#858ea3!important}.emailbox{background:#11151f!important;border-color:#292f40!important}.emailbox input{background:transparent!important;color:#fff!important}.emailbox button{background:linear-gradient(135deg,#35a7ff,#9b48ff)!important}
      footer{background:#090b11!important;border-top-color:#222838!important}.footer-brand{color:#fff!important}.footer-copy,.footer a{color:#7f899e!important}.footer h4{color:#e9edf6!important}.copyright{border-top-color:#222838!important;color:#697389!important}
      .skeleton{background:linear-gradient(90deg,#11151f 25%,#1a1f2c 37%,#11151f 63%)!important;background-size:400% 100%!important}
      @media(max-width:1000px){.products{grid-template-columns:repeat(2,minmax(0,1fr))!important}.product-media{height:310px!important}.hero-grid{grid-template-columns:1fr!important}.hero-art{min-height:390px!important}.cats{grid-template-columns:repeat(3,1fr)!important}}
      @media(max-width:600px){.container{width:calc(100% - 24px)!important}.announcement .inner{height:32px!important}.announcement .inner span:last-child{display:none}.nav{height:62px!important}.brand{font-size:18px!important}.hero{padding-top:10px!important}.hero-grid{border-radius:22px!important}.hero-copy{padding:36px 24px!important}.hero h1{font-size:43px!important}.hero p{font-size:13px!important}.hero-art{min-height:330px!important}.phone{width:185px!important;height:340px!important}.trust-item{padding:14px 10px!important}.cats{grid-template-columns:repeat(2,1fr)!important}.products{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:10px!important}.product{padding:8px!important;border-radius:17px!important}.product-media{height:230px!important;border-radius:14px!important}.product-media img{padding:5px!important}.product-info{padding:12px 3px 4px!important}.product-name{font-size:13px!important}.price{font-size:16px!important}.rating{font-size:9px!important}.promo{margin-top:48px!important}.promo-copy{padding:30px 23px!important}.footer-grid{grid-template-columns:1fr 1fr!important}}
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
