/* Save & share kit, shared by every niche site (copied to each site's public/kit.js by install_kit.py).
   - Floating "Share · Saved" pill (position:fixed, so it never shifts the page).
   - Share: the phone's own share sheet when available, else WhatsApp / Facebook / X / (Pinterest) / Email / Copy.
     The shared text is the page's answer, not just the title.
   - Save this page: kept in localStorage on the visitor's device; the Saved list opens from the pill.
   - Home screen / bookmark hint: only from the 2nd visit, once per 30 days, dismissible.
   - Registers /sw.js so the site can be installed and visited pages open offline.
   Config on the script tag: data-name, data-lang="hi", data-pin="1". */
(() => {
  const S = document.currentScript, NAME = S.dataset.name || document.title, PIN = S.dataset.pin === '1';
  const HI = S.dataset.lang === 'hi';
  const T = HI
    ? { share: 'शेयर', saved: 'सेव', save: 'यह पेज सेव करें', unsave: 'सेव से हटाएँ', copy: 'लिंक कॉपी करें', copied: 'कॉपी हो गया', none: 'अभी कोई सेव पेज नहीं।', close: 'बंद करें', install: 'होम स्क्रीन पर जोड़ें', add: 'जोड़ें', later: 'बाद में', ios: 'Safari में शेयर ⬆ दबाएँ, फिर "Add to Home Screen"', desk: 'बुकमार्क करने के लिए Ctrl+D दबाएँ (Mac: ⌘+D)' }
    : { share: 'Share', saved: 'Saved', save: 'Save this page', unsave: 'Remove from saved', copy: 'Copy link', copied: 'Copied', none: 'Nothing saved yet. Tap “Save this page” on any page you come back to.', close: 'Close', install: `Add ${NAME} to your home screen`, add: 'Add', later: 'Not now', ios: 'In Safari tap Share ⬆, then “Add to Home Screen”', desk: 'Press Ctrl+D (⌘+D on Mac) to bookmark this page' };
  const LS = { get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} } };
  const K = { saved: 'kit-saved', visits: 'kit-visits', hint: 'kit-hint' };

  // The answer to share: the first answer-like block on the page, else the meta description.
  const answer = () => {
    const el = document.querySelector('.res, .answer, .hl, .lead, .tldr, main h1 + p');
    const t = (el ? el.textContent : document.querySelector('meta[name=description]')?.content || '').replace(/\s+/g, ' ').trim();
    return t.length > 180 ? t.slice(0, 177).replace(/\s+\S*$/, '') + '…' : t;
  };
  const url = () => location.href.split('#')[0];

  const css = `.kit-pill{position:fixed;right:max(12px,env(safe-area-inset-right));bottom:max(12px,env(safe-area-inset-bottom));z-index:50;display:flex;border-radius:999px;box-shadow:0 2px 10px rgba(0,0,0,.18);overflow:hidden;font:600 14px/1 system-ui,Segoe UI,Roboto,Arial,sans-serif}
.kit-pill button{border:0;background:#fff;color:#1f2937;padding:10px 13px;cursor:pointer;display:flex;gap:6px;align-items:center}.kit-pill button+button{border-left:1px solid #e5e7eb}.kit-pill button:hover{background:#f3f4f6}
.kit-panel{position:fixed;right:max(12px,env(safe-area-inset-right));bottom:62px;z-index:51;width:min(340px,calc(100vw - 24px));max-height:70vh;overflow:auto;background:#fff;color:#1f2937;border-radius:14px;box-shadow:0 6px 28px rgba(0,0,0,.22);padding:12px;font:15px/1.45 system-ui,Segoe UI,Roboto,Arial,sans-serif}
.kit-panel h2{font-size:15px;margin:2px 4px 8px;color:#111827}.kit-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.kit-grid a,.kit-grid button,.kit-row{display:flex;flex-direction:column;align-items:center;gap:4px;padding:9px 4px;border-radius:10px;border:1px solid #e5e7eb;background:#fff;color:#1f2937;text-decoration:none;font-size:12.5px;cursor:pointer}
.kit-grid a:hover,.kit-grid button:hover{background:#f9fafb}.kit-grid i{font-style:normal;font-size:19px;line-height:1}
.kit-save{width:100%;margin-top:8px;padding:10px;border-radius:10px;border:1px solid #e5e7eb;background:#f9fafb;cursor:pointer;font:600 14px system-ui,sans-serif;color:#1f2937}
.kit-list{list-style:none;margin:0;padding:0}.kit-list li{display:flex;gap:6px;align-items:center;border-bottom:1px solid #f1f5f9}.kit-list a{flex:1;padding:9px 4px;color:#1d4ed8;text-decoration:none}.kit-list button{border:0;background:none;color:#9ca3af;cursor:pointer;font-size:16px;padding:6px}
.kit-hint{position:fixed;left:12px;right:12px;bottom:max(64px,calc(env(safe-area-inset-bottom) + 64px));z-index:50;max-width:460px;margin:0 auto;background:#111827;color:#fff;border-radius:12px;padding:11px 12px;display:flex;gap:10px;align-items:center;font:14px/1.35 system-ui,Segoe UI,Roboto,Arial,sans-serif;box-shadow:0 4px 18px rgba(0,0,0,.25)}
.kit-hint span{flex:1}.kit-hint button{border:0;border-radius:8px;padding:7px 11px;font:600 13px system-ui,sans-serif;cursor:pointer}.kit-hint .y{background:#fff;color:#111827}.kit-hint .n{background:transparent;color:#d1d5db}
@media print{.kit-pill,.kit-panel,.kit-hint{display:none!important}}`;
  const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);

  const el = (tag, attrs = {}, html = '') => { const e = document.createElement(tag); Object.assign(e, attrs); if (html) e.innerHTML = html; return e; };
  let panel = null;
  const close = () => { panel?.remove(); panel = null; };
  const open = (build) => { close(); panel = el('div', { className: 'kit-panel', role: 'dialog' }); build(panel); document.body.appendChild(panel); panel.querySelector('a,button')?.focus(); };
  document.addEventListener('keydown', (e) => e.key === 'Escape' && close());
  document.addEventListener('click', (e) => { if (panel && !panel.contains(e.target) && !e.target.closest('.kit-pill')) close(); });

  const isSaved = () => LS.get(K.saved, []).some((s) => s.u === location.pathname);
  const toggleSave = () => {
    let list = LS.get(K.saved, []);
    list = isSaved() ? list.filter((s) => s.u !== location.pathname)
      : [{ u: location.pathname, t: (document.querySelector('h1')?.textContent || document.title).trim().slice(0, 90) }, ...list].slice(0, 20);
    LS.set(K.saved, list);
  };

  const copy = async (btn) => {
    const text = `${answer()}\n${url()}`;
    try { await navigator.clipboard.writeText(text); } catch { const t = el('textarea', { value: text }); document.body.appendChild(t); t.select(); document.execCommand('copy'); t.remove(); }
    btn.querySelector('small').textContent = T.copied;
  };

  function sharePanel(p) {
    const a = answer(), u = encodeURIComponent(url()), at = encodeURIComponent(a);
    const img = document.querySelector('meta[property="og:image"]')?.content || '';
    const items = [
      ['WhatsApp', '💬', `https://wa.me/?text=${encodeURIComponent(a + ' ' + url())}`],
      ['Facebook', 'f', `https://www.facebook.com/sharer/sharer.php?u=${u}`],
      ['X', '𝕏', `https://twitter.com/intent/tweet?text=${at}&url=${u}`],
      ...(PIN ? [['Pinterest', 'P', `https://pinterest.com/pin/create/button/?url=${u}&description=${at}&media=${encodeURIComponent(img)}`]] : []),
      ['Email', '✉', `mailto:?subject=${encodeURIComponent(document.title)}&body=${encodeURIComponent(a + '\n\n' + url())}`],
    ];
    p.appendChild(el('h2', {}, T.share));
    const g = el('div', { className: 'kit-grid' });
    for (const [n, i, href] of items) g.appendChild(el('a', { href, target: '_blank', rel: 'noopener nofollow' }, `<i>${i}</i>${n}`));
    const c = el('button', { type: 'button' }, `<i>🔗</i><small>${T.copy}</small>`); c.onclick = () => copy(c); g.appendChild(c);
    p.appendChild(g);
    const s = el('button', { type: 'button', className: 'kit-save' }, isSaved() ? '★ ' + T.unsave : '☆ ' + T.save);
    s.onclick = () => { toggleSave(); s.innerHTML = isSaved() ? '★ ' + T.unsave : '☆ ' + T.save; pill.update(); };
    p.appendChild(s);
  }

  function savedPanel(p) {
    const list = LS.get(K.saved, []);
    p.appendChild(el('h2', {}, `★ ${T.saved}`));
    if (!list.length) p.appendChild(el('p', { style: 'margin:4px;color:#6b7280' }, T.none));
    const ul = el('ul', { className: 'kit-list' });
    for (const s of list) {
      const li = el('li'); li.appendChild(el('a', { href: s.u, textContent: s.t }));
      const x = el('button', { type: 'button', title: T.unsave, ariaLabel: T.unsave, textContent: '×' });
      x.onclick = () => { LS.set(K.saved, LS.get(K.saved, []).filter((o) => o.u !== s.u)); li.remove(); pill.update(); };
      li.appendChild(x); ul.appendChild(li);
    }
    p.appendChild(ul);
    const s = el('button', { type: 'button', className: 'kit-save' }, isSaved() ? '★ ' + T.unsave : '☆ ' + T.save);
    s.onclick = () => { toggleSave(); close(); pill.update(); open(savedPanel); };
    p.appendChild(s);
  }

  const pill = el('div', { className: 'kit-pill' });
  const bShare = el('button', { type: 'button', ariaLabel: T.share }, `↗ ${T.share}`);
  const bSaved = el('button', { type: 'button', ariaLabel: T.saved });
  pill.update = () => { const n = LS.get(K.saved, []).length; bSaved.innerHTML = `${isSaved() ? '★' : '☆'} ${T.saved}${n ? ` (${n})` : ''}`; };
  bShare.onclick = async (e) => {
    e.stopPropagation();
    const touch = matchMedia('(pointer:coarse)').matches;
    if (touch && navigator.share) { try { await navigator.share({ title: document.title, text: answer(), url: url() }); return; } catch (err) { if (err && err.name === 'AbortError') return; } }
    panel ? close() : open(sharePanel);
  };
  bSaved.onclick = (e) => { e.stopPropagation(); panel ? close() : open(savedPanel); };
  pill.append(bShare, bSaved); pill.update();
  document.body.appendChild(pill);

  // Home-screen / bookmark hint: returning visitors only, at most once a month.
  let deferred = null;
  addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferred = e; });
  const visits = LS.get(K.visits, 0) + 1; LS.set(K.visits, visits);
  const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  if (visits >= 2 && !standalone && Date.now() - LS.get(K.hint, 0) > 30 * 864e5) {
    setTimeout(() => {
      const ios = /iphone|ipad|ipod/i.test(navigator.userAgent) && !/crios|fxios/i.test(navigator.userAgent);
      const msg = deferred ? T.install : ios ? T.ios : matchMedia('(pointer:fine)').matches ? T.desk : null;
      if (!msg) return;
      const h = el('div', { className: 'kit-hint', role: 'status' }, `<span>${msg}</span>`);
      if (deferred) { const y = el('button', { type: 'button', className: 'y', textContent: T.add }); y.onclick = async () => { deferred.prompt(); await deferred.userChoice; h.remove(); }; h.appendChild(y); }
      const n = el('button', { type: 'button', className: 'n', textContent: deferred ? T.later : '×', ariaLabel: T.close }); n.onclick = () => h.remove(); h.appendChild(n);
      LS.set(K.hint, Date.now());
      document.body.appendChild(h);
    }, 6000);
  }

  if ('serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register('/sw.js').catch(() => {});
})();
