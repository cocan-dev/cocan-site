// Hero grid: a bright copy of the grid is revealed around the pointer.
// No network, no storage; skipped when the visitor prefers reduced motion.
(function () {
  var fx = document.querySelector('.gridfx');
  if (!fx || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var hero = fx.parentElement, raf = 0, x = 0, y = 0;
  function paint() {
    raf = 0;
    fx.style.setProperty('--mx', x + 'px');
    fx.style.setProperty('--my', y + 'px');
  }
  hero.addEventListener('pointermove', function (e) {
    var r = hero.getBoundingClientRect();
    x = e.clientX - r.left;
    y = e.clientY - r.top;
    fx.classList.add('active');
    if (!raf) raf = requestAnimationFrame(paint);
  });
  hero.addEventListener('pointerleave', function () { fx.classList.remove('active'); });
})();
