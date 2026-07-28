// ==UserScript==
// @name         Starrydata2 Open Access Filter
// @namespace    user.starrydata.oa
// @version      1.0.0
// @description  論文一覧に Open Access フィルタとバッジ・PDF リンクを追加する
// @author       you
// @match        https://starrydata.nims.go.jp/starrydata2/paperlist/project/*
// @match        https://starrydata.nims.go.jp/starrydata2/paperlist/*
// @grant        GM_xmlhttpRequest
// @connect      api.unpaywall.org
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // ====== 設定 ======
  const UNPAYWALL_EMAIL = 'starrydata1@gmail.com';
  const CACHE_KEY = 'starrydata_oa_cache_v1';
  const FILTER_KEY = 'starrydata_oa_filter';
  const CACHE_TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30 日
  const MAX_CONCURRENT = 5; // Unpaywall への同時リクエスト上限

  // ====== キャッシュ ======
  function loadCache() {
    try { return JSON.parse(localStorage.getItem(CACHE_KEY) || '{}'); }
    catch (_) { return {}; }
  }
  function saveCache(c) {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(c)); } catch (_) {}
  }
  const cache = loadCache();

  // ====== 同時実行制限付きキュー ======
  let active = 0;
  const queue = [];
  function runNext() {
    if (active >= MAX_CONCURRENT) return;
    const job = queue.shift();
    if (!job) return;
    active++;
    job().finally(() => { active--; runNext(); });
  }
  function enqueue(fn) {
    return new Promise(res => {
      queue.push(() => fn().then(res));
      runNext();
    });
  }

  // ====== Unpaywall 問い合わせ ======
  const inFlight = new Map();
  function fetchOA(doi) {
    if (!doi || !/^10\./.test(doi)) {
      return Promise.resolve({ is_oa: null, reason: 'no-doi' });
    }
    const key = doi.toLowerCase();
    const c = cache[key];
    if (c && Date.now() - c.t < CACHE_TTL_MS) return Promise.resolve(c.v);
    if (inFlight.has(key)) return inFlight.get(key);

    const p = enqueue(() => new Promise(resolve => {
      const url = `https://api.unpaywall.org/v2/${encodeURIComponent(doi)}?email=${encodeURIComponent(UNPAYWALL_EMAIL)}`;
      GM_xmlhttpRequest({
        method: 'GET',
        url,
        timeout: 15000,
        onload: r => {
          let val = { is_oa: null, reason: 'parse-error' };
          try {
            if (r.status === 200) {
              const j = JSON.parse(r.responseText);
              const loc = j.best_oa_location || null;
              val = {
                is_oa: !!j.is_oa,
                oa_status: j.oa_status || null,
                pdf_url: loc ? (loc.url_for_pdf || loc.url || null) : null,
                host_type: loc ? loc.host_type || null : null,
              };
            } else if (r.status === 404) {
              val = { is_oa: null, reason: 'not-found' };
            } else {
              val = { is_oa: null, reason: `http-${r.status}` };
            }
          } catch (_) {}
          cache[key] = { t: Date.now(), v: val };
          saveCache(cache);
          resolve(val);
        },
        onerror: () => resolve({ is_oa: null, reason: 'network-error' }),
        ontimeout: () => resolve({ is_oa: null, reason: 'timeout' }),
      });
    }));
    inFlight.set(key, p);
    p.finally(() => inFlight.delete(key));
    return p;
  }

  // ====== UI: スタイル ======
  const style = document.createElement('style');
  style.textContent = `
    .oa-filter-control { display: inline-flex; align-items: center; margin-left: 8px; gap: 4px; }
    .oa-filter-control select { padding: 2px 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 0.9em; }
    .oa-filter-control label { font-size: 0.9em; }
    #oa-stats { font-size: 0.85em; color: #555; margin-left: 8px; }
    .oa-badge { font-weight: bold; margin-bottom: 2px; }
    .oa-badge a { margin-left: 6px; font-weight: normal; }
    li[data-oa-status="oa"]     .oa-badge { color: #0a8a3a; }
    li[data-oa-status="closed"] .oa-badge { color: #b00020; }
    li[data-oa-status="unknown"].oa-badge,
    li[data-oa-status="unknown"] .oa-badge { color: #888; }
  `;
  document.head.appendChild(style);

  // ====== UI: フィルタ ======
  let currentFilter = localStorage.getItem(FILTER_KEY) || 'all';

  function injectFilterUI() {
    document.querySelectorAll('.paper .sub-menu').forEach(menu => {
      if (menu.querySelector('.oa-filter-control')) return;
      const wrap = document.createElement('div');
      wrap.className = 'oa-filter-control';
      wrap.innerHTML = `
        <label>OA: </label>
        <select class="oa-filter-select">
          <option value="all">All</option>
          <option value="oa">🟢 Open Access only</option>
          <option value="closed">🔒 Closed only</option>
          <option value="unknown">❓ Unknown only</option>
        </select>
        <span class="oa-stats" id="oa-stats"></span>
      `;
      menu.appendChild(wrap);
      const sel = wrap.querySelector('.oa-filter-select');
      sel.value = currentFilter;
      sel.addEventListener('change', () => {
        currentFilter = sel.value;
        localStorage.setItem(FILTER_KEY, currentFilter);
        // 全フィルタ UI を同期
        document.querySelectorAll('.oa-filter-select').forEach(s => { s.value = currentFilter; });
        applyFilter();
      });
    });
  }

  // ====== DOI 抽出 ======
  function extractDOI(li) {
    const divs = li.querySelectorAll('.tagarea .sid');
    for (const d of divs) {
      if (d.classList.contains('oa-badge')) continue;
      const t = d.textContent.trim();
      const m = t.match(/^DOI\s*:\s*(.*)$/i);
      if (m) {
        const v = m[1].trim();
        if (!v || /^(unknown|undefined|-)$/i.test(v)) return null;
        return v;
      }
    }
    return null;
  }

  // ====== バッジ表示 ======
  function setBadge(li, oa) {
    let badge = li.querySelector('.oa-badge');
    if (!badge) {
      badge = document.createElement('div');
      badge.className = 'oa-badge sid';
      const tagarea = li.querySelector('.tagarea');
      if (!tagarea) return;
      tagarea.prepend(badge);
    }
    if (!oa) {
      badge.textContent = '⏳ OA: checking...';
      li.dataset.oaStatus = 'unknown';
      return;
    }
    if (oa.is_oa === true) {
      const link = oa.pdf_url
        ? ` <a href="${oa.pdf_url}" target="_blank" rel="noopener noreferrer">[PDF]</a>`
        : '';
      const tag = oa.oa_status ? ` (${oa.oa_status})` : '';
      badge.innerHTML = `🟢 Open Access${tag}${link}`;
      li.dataset.oaStatus = 'oa';
    } else if (oa.is_oa === false) {
      badge.textContent = '🔒 Closed';
      li.dataset.oaStatus = 'closed';
    } else {
      const why = oa.reason ? ` (${oa.reason})` : '';
      badge.textContent = `❓ OA: unknown${why}`;
      li.dataset.oaStatus = 'unknown';
    }
  }

  // ====== フィルタ適用 ======
  function applyFilter() {
    const items = document.querySelectorAll('.paper .field li');
    let oa = 0, closed = 0, unk = 0, total = 0;
    items.forEach(li => {
      total++;
      const st = li.dataset.oaStatus || 'unknown';
      if (st === 'oa') oa++;
      else if (st === 'closed') closed++;
      else unk++;
      const show = currentFilter === 'all' || st === currentFilter;
      li.style.display = show ? '' : 'none';
    });
    document.querySelectorAll('#oa-stats').forEach(s => {
      s.textContent = `(🟢 ${oa} / 🔒 ${closed} / ❓ ${unk} / 全 ${total})`;
    });
  }

  // ====== 各論文の処理 ======
  const processed = new WeakSet();
  async function processLi(li) {
    if (processed.has(li)) return;
    processed.add(li);
    setBadge(li, null);
    const doi = extractDOI(li);
    const oa = await fetchOA(doi);
    setBadge(li, oa);
    applyFilter();
  }

  // ====== 監視ループ ======
  let scanTimer = null;
  function scheduleScan() {
    if (scanTimer) return;
    scanTimer = setTimeout(() => {
      scanTimer = null;
      injectFilterUI();
      document.querySelectorAll('.paper .field li').forEach(processLi);
      applyFilter();
    }, 200);
  }

  const observer = new MutationObserver(scheduleScan);
  observer.observe(document.body, { childList: true, subtree: true });
  scheduleScan();
})();
