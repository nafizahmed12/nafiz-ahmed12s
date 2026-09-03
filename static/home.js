(() => {
  const $ = (s) => document.querySelector(s);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money = (v, currency='BDT') => `${currency === 'BDT' ? '৳' : currency + ' '}${esc(v)}`;
  const setCart = (n) => { const a=$('#cartCount'); const b=$('#bottomItems'); if(a)a.textContent=String(n??0); if(b)b.textContent=`${n??0} Items`; };

  function productCard(p, compact=false, i=0) {
    const image = p.image_url ? `<img src="${esc(p.image_url)}" alt="${esc(p.name)}" loading="lazy">` : '<div></div>';
    const compare = p.compare_at_price && Number(p.compare_at_price)>Number(p.price) ? `<s>${money(p.compare_at_price,p.currency)}</s>` : '';
    const badge = p.featured || i<2 ? '<span class="hot">TRENDING</span>' : '';
    return `<article class="card"><div class="pic">${badge}<button class="heart" type="button" aria-label="Save">♡</button>${image}</div><div class="card-body"><div class="type">${esc(p.category || 'Product')}</div><h3>${esc(p.name)}</h3><div class="sub">${esc(p.description || 'Premium quality')}</div><div class="price-row"><span class="money">${compare}${money(p.price,p.currency)}</span><button class="plus" type="button" data-add="${esc(p.id)}" aria-label="Add ${esc(p.name)}">＋</button></div></div></article>`;
  }

  function bindAddButtons(){
    document.querySelectorAll('[data-add]').forEach(btn=>btn.addEventListener('click',async()=>{
      btn.disabled=true;
      try{
        const r=await fetch('/api/cart/items',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:Number(btn.dataset.add),quantity:1})});
        if(r.status===401){location.href='/user-login';return;}
        const body=await r.json();
        if(!r.ok){alert(body.error||'Could not add this product.');return;}
        setCart(body.item_count);
        const total=$('#bottomTotal'); if(total) total.textContent=money(body.total ?? 0,'BDT');
        btn.textContent='✓'; setTimeout(()=>btn.textContent='＋',900);
      }catch(e){alert('Could not add this product.');}finally{btn.disabled=false;}
    }));
  }

  function renderFeatured(list){
    const box=$('#featuredProducts'); if(!box)return;
    if(!list?.length){box.innerHTML='<div class="empty">No products available yet.</div>';return;}
    box.innerHTML=list.slice(0,5).map((p,i)=>productCard(p,false,i)).join('');
    bindAddButtons();
  }

  function renderHero(p){
    const visual=$('#featuredVisual'); const sale=$('#featuredSale');
    if(!visual)return;
    if(!p){visual.innerHTML='<span style="color:#727b91;font-size:12px">Featured product coming soon</span>';return;}
    visual.innerHTML=p.image_url?`<img src="${esc(p.image_url)}" alt="${esc(p.name)}">`:`<span style="color:#727b91">${esc(p.name)}</span>`;
    if(p.compare_at_price&&Number(p.compare_at_price)>Number(p.price)){const pct=Math.round((1-Number(p.price)/Number(p.compare_at_price))*100);sale.textContent=`UP TO ${pct}% OFF`;sale.hidden=false;}
  }

  function renderPopular(list){
    const grid=$('#trendingGrid'); if(!grid)return;
    if(!list?.length){grid.innerHTML='<div class="empty">No products available yet.</div>';return;}
    grid.innerHTML=list.slice(0,6).map((p,i)=>productCard(p,true,i)).join('');
    bindAddButtons();
  }

  function setupSearch(){
    const input=$('#homeSearch'); if(!input)return;
    input.addEventListener('keydown',e=>{if(e.key==='Enter'){const q=input.value.trim();location.href=q?`/shop?search=${encodeURIComponent(q)}`:'/shop';}});
  }

  function setupNewsletter(){
    const form=$('.form'); if(!form)return;
    form.addEventListener('submit',async e=>{e.preventDefault();const input=form.querySelector('input[type=email]');const button=form.querySelector('button');const email=input?.value.trim();if(!email)return;button.disabled=true;try{const token=form.querySelector('[name=csrf_token]')?.value||'';const r=await fetch('/subscribe',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({subscriber_email:email,csrf_token:token})});if(!r.ok)throw new Error('Subscription failed');input.value='';button.textContent='Subscribed ✓';}catch(err){alert(err.message);}finally{button.disabled=false;}});
  }

  function setupTimer(){const boxes=document.querySelectorAll('.time b');if(boxes.length!==3)return;let end=Date.now()+((6*3600+42*60+18)*1000);setInterval(()=>{let s=Math.max(0,Math.floor((end-Date.now())/1000));const h=Math.floor(s/3600);s%=3600;const m=Math.floor(s/60);s%=60;boxes[0].textContent=String(h).padStart(2,'0');boxes[1].textContent=String(m).padStart(2,'0');boxes[2].textContent=String(s).padStart(2,'0');if(Date.now()>=end)end=Date.now()+86400000;},1000);}

  async function load(){
    try{const r=await fetch('/api/home',{headers:{Accept:'application/json'}});if(!r.ok)return;const data=await r.json();setCart(data.cart_count||0);const products=data.products||[];renderHero(products.find(p=>p.featured)||products[0]);renderFeatured(products);renderPopular(products);}
    catch(_){renderFeatured([]);renderPopular([]);}
  }

  document.addEventListener('DOMContentLoaded',()=>{setupSearch();setupNewsletter();setupTimer();load();});
})();
