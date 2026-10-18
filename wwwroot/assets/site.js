(function () {
  var root = document.documentElement;
  root.classList.add('js');

  // Theme toggle: an explicit choice is remembered, otherwise the OS setting wins.
  var toggle = document.querySelector('.theme-toggle');
  function currentTheme() {
    var t = root.getAttribute('data-theme');
    if (t) return t;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  if (toggle) {
    toggle.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('ab.theme', next); } catch (e) {}
    });
  }

  // Nav border once the page scrolls.
  var nav = document.querySelector('.nav');
  function onScroll() { if (nav) nav.classList.toggle('scrolled', window.scrollY > 8); }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // Stagger index for the MVP year bars.
  document.querySelectorAll('.mvp-bar li').forEach(function (li, i) { li.style.setProperty('--i', i); });

  // Reveal on scroll; without IntersectionObserver everything is shown at once.
  var items = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window)) {
    items.forEach(function (el) { el.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    items.forEach(function (el) { io.observe(el); });
  }

  // Highlight the nav link of the section in view.
  var links = Array.prototype.slice.call(document.querySelectorAll('.nav-links a'));
  if ('IntersectionObserver' in window && links.length) {
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        links.forEach(function (a) {
          a.classList.toggle('active', a.getAttribute('href') === '#' + entry.target.id);
        });
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    links.forEach(function (a) {
      var target = document.querySelector(a.getAttribute('href'));
      if (target) spy.observe(target);
    });
  }

  // The address is never in the HTML: it is stored reversed and base64-encoded,
  // decoded only here, and the mailto: link is attached on the first real
  // interaction, so crawlers that only read markup (or render without
  // interacting) find no address and no mailto: to harvest.
  var MAIL = 'dGkubmloY3NvYkBhZXJkbmE=';
  function address() {
    try { return atob(MAIL).split('').reverse().join(''); } catch (e) { return ''; }
  }
  document.querySelectorAll('[data-mail]').forEach(function (a) {
    var label = a.querySelector('[data-mail-text]');
    if (label) {
      var shown = address();
      if (shown) label.textContent = shown;
    }
    function arm() {
      if (a.dataset.armed) return;
      a.dataset.armed = '1';
      a.setAttribute('href', 'mai' + 'lto:' + address());
    }
    ['pointerenter', 'focus', 'touchstart', 'mousedown'].forEach(function (ev) {
      a.addEventListener(ev, arm, { passive: true, once: true });
    });
    // Keyboard activation without a prior focus event (rare) still works.
    a.addEventListener('click', arm);
  });

  // Language menu: remember the choice and close the menu on outside click.
  document.querySelectorAll('.lang a[data-lang]').forEach(function (a) {
    a.addEventListener('click', function () {
      try { localStorage.setItem('ab.lang', a.getAttribute('data-lang')); } catch (e) {}
    });
  });
  document.addEventListener('click', function (e) {
    document.querySelectorAll('details.lang[open]').forEach(function (d) {
      if (!d.contains(e.target)) d.removeAttribute('open');
    });
  });

  // CV download: like the address, the file path is not in the markup and the
  // link is armed only on a real interaction, so crawlers do not discover it.
  var CV = 'ZmRwLjQ2MWIzYTcwODNjNS12Yy9zZWxpZi9zdGVzc2E=';
  function cvPath() {
    try { return atob(CV).split('').reverse().join(''); } catch (e) { return ''; }
  }
  document.querySelectorAll('[data-cv]').forEach(function (a) {
    function arm() {
      if (a.dataset.armed) return;
      var path = cvPath();
      if (!path) return;
      a.dataset.armed = '1';
      a.setAttribute('href', path);
      // A new tab, so viewing the PDF never replaces the site.
      a.setAttribute('target', '_blank');
      a.setAttribute('rel', 'noopener');
    }
    ['pointerenter', 'focus', 'touchstart', 'mousedown'].forEach(function (ev) {
      a.addEventListener(ev, arm, { passive: true, once: true });
    });
    a.addEventListener('click', arm);
  });

  // Certificate links open the image in a dialog, loading it only then. Without
  // JavaScript or <dialog> support the link simply opens the image.
  document.querySelectorAll('[data-dialog]').forEach(function (a) {
    var dialog = document.getElementById(a.getAttribute('data-dialog'));
    if (!dialog || typeof dialog.showModal !== 'function') return;
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var img = dialog.querySelector('img[data-src]');
      if (img && !img.getAttribute('src')) img.setAttribute('src', img.getAttribute('data-src'));
      dialog.showModal();
    });
    // A click outside the image lands on the dialog itself (its backdrop).
    dialog.addEventListener('click', function (e) { if (e.target === dialog) dialog.close(); });
  });

  var year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
})();
