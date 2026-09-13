(function () {
  function initAppleMenu() {
    const wrap = document.getElementById('appleMenu');
    const trigger = document.getElementById('appleTrigger');
    const menu = document.getElementById('appleMega');
    if (!wrap || !trigger || !menu || wrap.dataset.appleMenuReady === '1') return;
    wrap.dataset.appleMenuReady = '1';
    const isMobile = () => window.matchMedia('(max-width: 700px)').matches;
    function open() { wrap.classList.add('is-open'); trigger.setAttribute('aria-expanded', 'true'); }
    function close() { wrap.classList.remove('is-open'); trigger.setAttribute('aria-expanded', 'false'); }
    trigger.addEventListener('click', function (event) {
      if (!isMobile()) return;
      event.preventDefault(); event.stopPropagation();
      wrap.classList.contains('is-open') ? close() : open();
    });
    trigger.addEventListener('touchend', function (event) {
      if (!isMobile()) return;
      event.preventDefault(); event.stopPropagation();
      wrap.classList.contains('is-open') ? close() : open();
    }, { passive: false });
    document.addEventListener('click', function (event) {
      if (isMobile() && !wrap.contains(event.target)) close();
    });
    window.addEventListener('resize', function () { if (!isMobile()) close(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initAppleMenu);
  else initAppleMenu();
})();
