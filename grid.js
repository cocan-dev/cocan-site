// Hourly activity bars are generated with UTC tooltips; show them in the
// visitor's own time zone instead (the UTC text stays as the fallback).
(function () {
  var bars = document.querySelectorAll('.bar[data-h]');
  for (var i = 0; i < bars.length; i++) {
    var b = bars[i], d = new Date(b.getAttribute('data-h')), n = +b.getAttribute('data-n');
    if (isNaN(d)) continue;
    var when = d.toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    b.title = when + ': ' + n + ' commit' + (n === 1 ? '' : 's');
  }
})();

// Hero grid with "gravity": grid lines bend towards the pointer and glow near it.
// Everything is drawn locally on a canvas: no network, no storage. It only runs
// while the pointer is over the hero, and is skipped when the visitor prefers
// reduced motion (the plain CSS grid stays).
(function () {
  var fx = document.querySelector('.gridfx');
  if (!fx || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var hero = fx.parentElement;
  var cv = document.createElement('canvas');
  var ctx = cv.getContext('2d');
  if (!ctx) return;
  fx.appendChild(cv);
  fx.classList.add('canvas');

  var CELL = 32, STEP = 8, RADIUS = 150, PULL = 0.42;
  var W = 0, H = 0;
  var tx = 0, ty = 0, cx = 0, cy = 0, power = 0, target = 0, raf = 0;
  var fg = '#888', rgb = [240, 138, 93];

  function readColors() {
    var s = getComputedStyle(fx);
    fg = s.color || fg;
    var a = s.getPropertyValue('--accent').trim();
    var m = /^#?([0-9a-f]{6})$/i.exec(a);
    if (m) rgb = [0, 2, 4].map(function (i) { return parseInt(m[1].substr(i, 2), 16); });
  }

  function size() {
    var r = fx.getBoundingClientRect();
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = r.width; H = r.height;
    cv.width = Math.round(W * dpr);
    cv.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    readColors();
    draw();
  }

  // Pull a point towards the pointer; the pull fades with distance.
  function warp(x, y) {
    var dx = cx - x, dy = cy - y;
    var f = power * PULL * Math.exp(-(dx * dx + dy * dy) / (2 * RADIUS * RADIUS));
    return [x + dx * f, y + dy * f];
  }

  function lines() {
    ctx.beginPath();
    var x, y, p;
    for (x = 0; x <= W; x += CELL) {
      for (y = 0; y <= H; y += STEP) {
        p = warp(x, y);
        if (y === 0) ctx.moveTo(p[0], p[1]); else ctx.lineTo(p[0], p[1]);
      }
    }
    for (y = 0; y <= H; y += CELL) {
      for (x = 0; x <= W; x += STEP) {
        p = warp(x, y);
        if (x === 0) ctx.moveTo(p[0], p[1]); else ctx.lineTo(p[0], p[1]);
      }
    }
    ctx.stroke();
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.16;
    ctx.strokeStyle = fg;
    lines();
    if (power > 0.02) {
      var g = ctx.createRadialGradient(cx, cy, 0, cx, cy, RADIUS * 1.3);
      var c = rgb.join(',');
      g.addColorStop(0, 'rgba(' + c + ',1)');
      g.addColorStop(1, 'rgba(' + c + ',0)');
      ctx.globalAlpha = Math.min(1, power);
      ctx.lineWidth = 1.3;
      ctx.strokeStyle = g;
      lines();
    }
    ctx.globalAlpha = 1;
  }

  function tick() {
    cx += (tx - cx) * 0.18;
    cy += (ty - cy) * 0.18;
    power += (target - power) * 0.09;
    draw();
    var moving = Math.abs(tx - cx) > 0.3 || Math.abs(ty - cy) > 0.3 || Math.abs(target - power) > 0.01;
    raf = moving ? requestAnimationFrame(tick) : 0;
    if (!moving && target === 0) { power = 0; draw(); }
  }

  function kick() { if (!raf) raf = requestAnimationFrame(tick); }

  hero.addEventListener('pointermove', function (e) {
    var r = fx.getBoundingClientRect();
    tx = e.clientX - r.left;
    ty = e.clientY - r.top;
    if (target === 0 && power < 0.02) { cx = tx; cy = ty; }
    target = 1;
    kick();
  });
  hero.addEventListener('pointerleave', function () { target = 0; kick(); });

  if (window.ResizeObserver) new ResizeObserver(size).observe(fx); else window.addEventListener('resize', size);
  size();
})();
