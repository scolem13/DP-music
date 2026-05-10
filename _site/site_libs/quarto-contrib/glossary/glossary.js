document.addEventListener('DOMContentLoaded', function () {

  // ── Term highlighting on arrival from a "Used in" book link ──────────────
  var hash = window.location.hash;
  if (hash.startsWith('#glterm=')) {
    var termId = hash.slice(8);
    var targets = document.querySelectorAll('button.glossary[data-term="' + termId + '"]');
    if (targets.length > 0) {
      history.replaceState(null, '', window.location.pathname + window.location.search);
      targets[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
      targets.forEach(function (btn) {
        btn.classList.add('glterm-highlight');
        setTimeout(function () { btn.classList.remove('glterm-highlight'); }, 2500);
      });
    }
  }

  // ── Popup: body-move approach ─────────────────────────────────────────────
  var _popup = null; // { btn, def }

  var POPUP_BASE = [
    'display:block',
    'position:fixed',
    'z-index:2147483647',
    'box-sizing:border-box',
    'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif',
    'font-size:0.85rem',
    'font-weight:normal',
    'font-style:normal',
    'line-height:1.5',
    'text-align:center',
    'color:white',
    'background-color:#333',
    'padding:9px 13px',
    'border-radius:7px',
    'white-space:normal',
    'pointer-events:none',
  ].join(';');

  function openPopup(btn) {
    closePopup();
    var def = btn.querySelector('.def');
    if (!def) return;
    document.body.appendChild(def);
    _popup = { btn: btn, def: def };
    def.style.cssText = POPUP_BASE;
    positionPopup(btn, def);
    btn.classList.add('popup-open');
  }

  function closePopup() {
    if (!_popup) return;
    _popup.btn.appendChild(_popup.def);
    _popup.def.style.cssText = '';
    _popup.def.classList.remove('gldef-above', 'gldef-below');
    _popup.btn.classList.remove('popup-open');
    _popup = null;
  }

  function positionPopup(btn, def) {
    var MARGIN = 10;
    var rect = btn.getBoundingClientRect();
    var vw = window.innerWidth || document.documentElement.clientWidth;

    var defW = Math.min(360, vw - 2 * MARGIN);
    def.style.width = defW + 'px';

    var defH = def.offsetHeight || 120;

    var cx   = rect.left + rect.width / 2;
    var left = Math.max(MARGIN, Math.min(cx - defW / 2, vw - defW - MARGIN));

    def.classList.remove('gldef-above', 'gldef-below');
    var top;
    if (rect.top - defH - 8 >= MARGIN) {
      top = rect.top - defH - 8;
      def.classList.add('gldef-above');
    } else {
      top = rect.bottom + 8;
      def.classList.add('gldef-below');
    }

    def.style.left = left + 'px';
    def.style.top  = top  + 'px';
    def.style.setProperty('--arrow-offset', (cx - (left + defW / 2)) + 'px');
  }

  // ── Event delegation for clicks (handles both static and dynamic buttons) ──
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('button.glossary');
    if (btn && btn.querySelector('.def')) {
      e.stopPropagation();
      if (_popup && _popup.btn === btn) {
        closePopup();
      } else {
        openPopup(btn);
      }
    } else {
      closePopup();
    }
  });

  window.addEventListener('scroll', closePopup, { passive: true, capture: true });
  window.addEventListener('resize', closePopup, { passive: true });

  // ── Double-click: navigate to glossary page (delegation, uses #glterm= hash) ─
  document.addEventListener('dblclick', function (e) {
    var btn = e.target.closest('button.glossary[data-glossary-url]');
    if (!btn) return;
    e.preventDefault();
    closePopup();
    var url  = btn.getAttribute('data-glossary-url');
    var term = btn.getAttribute('data-term') || '';
    (window.top || window).location.href = url + '#glterm=' + term;
  });
});
