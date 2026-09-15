/* Relevé des publications de @lauric_sergent pour l'onglet Contenu › 🎬 Reels (lecture seule).
   À coller dans javascript_tool sur un onglet https://www.instagram.com/robots.txt (pas la messagerie :
   un onglet instagram.com figé bloque les autres), compte lauric_sergent connecté.

   1) window.__reels(MAXP, dMin, dMax) : pages de /api/v1/feed/user/<id>/ (12 publications par page),
      en arrière-plan. Suivre window.__rstate. Rythme conseillé : 8 pages max, 45 à 60 s entre pages.
      Arrêt tout seul si une page dépasse 8 s ou si Instagram répond autre chose que 200.
   2) window.__rpart(k) : écrit la tranche k de l'export (JSON, une publication par ligne) dans la page,
      à lire avec get_page_text puis à recoller avec scripts-releve/glue_json.py <out.json> --prefix R. */
window.__R = window.__R || []; window.__rlat = window.__rlat || []; window.__rmax = window.__rmax || null;
window.__rseen = window.__rseen || new Set();
window.__reels = async (MAXP, dMin, dMax) => {
  const H = { 'x-ig-app-id': '936619743392459', 'x-requested-with': 'XMLHttpRequest' };
  let pages = 0;
  try {
    while (pages < MAXP) {
      const u = '/api/v1/feed/user/77138870834/?count=12' + (window.__rmax ? '&max_id=' + encodeURIComponent(window.__rmax) : '');
      const t0 = Date.now(); const r = await fetch(u, { credentials: 'include', headers: H }); const lat = Date.now() - t0;
      window.__rlat.push(lat);
      if (!r.ok) { window.__rstate = 'ERR ' + r.status + ' page ' + (pages + 1); return; }
      const j = await r.json();
      for (const m of (j.items || [])) {
        if (window.__rseen.has(String(m.pk))) continue; window.__rseen.add(String(m.pk));
        if (!window.__keys) window.__keys = Object.keys(m).sort().join(',');
        const cands = (m.image_versions2 && m.image_versions2.candidates) || (m.carousel_media && m.carousel_media[0] && m.carousel_media[0].image_versions2 && m.carousel_media[0].image_versions2.candidates) || [];
        const cov = (cands.filter(c => c.width <= 640).sort((a, b) => b.width - a.width)[0] || cands[cands.length - 1] || {}).url || '';
        const ci = m.clips_metadata || {};
        const mu = ci.music_info && ci.music_info.music_asset_info;
        window.__R.push({
          pk: String(m.pk), code: m.code, t: m.taken_at, mt: m.media_type, pt: m.product_type || '',
          plays: m.play_count ?? null, igp: m.ig_play_count ?? null, views: m.view_count ?? null,
          likes: m.like_count ?? null, comms: m.comment_count ?? null,
          share: m.reshare_count ?? m.share_count ?? m.media_repost_count ?? null, save: m.save_count ?? null,
          dur: m.video_duration ?? null, cap: (m.caption && m.caption.text) || '', cov,
          audio: mu ? (mu.title + ' · ' + mu.display_artist) : (ci.original_sound_info ? 'son original' : ''),
          nc: m.carousel_media_count || 0, collab: (m.coauthor_producers || []).map(x => x.username),
          paid: !!m.is_paid_partnership, acc: m.accessibility_caption || '',
        });
      }
      pages++; window.__rmax = j.next_max_id || null;
      const last = window.__R[window.__R.length - 1];
      window.__rstate = 'page ' + pages + ' publications ' + window.__R.length + ' lat ' + lat + ' plus ancienne ' + (last ? new Date(last.t * 1000).toISOString().slice(0, 10) : '?');
      if (!j.more_available || !window.__rmax) { window.__rstate = 'done (fin du profil) ' + window.__rstate; return; }
      if (lat > 8000) { window.__rstate = 'STOP lenteur ' + window.__rstate; return; }
      await new Promise(res => setTimeout(res, dMin + Math.random() * (dMax - dMin)));
    }
    window.__rstate = 'done (max) ' + window.__rstate;
  } catch (e) { window.__rstate = 'EXC ' + e.message + ' ' + (window.__rstate || ''); }
};
window.__rdump = (txt) => { const m = document.querySelector('main') || document.body; m.innerHTML = ''; const d = document.createElement('pre'); d.textContent = txt; m.appendChild(d); return txt.length; };
window.__rpart = (k) => {
  const all = window.__R.map(x => JSON.stringify(x)).join('\n') + '\nENDDUMP';
  return window.__rdump('R' + k + '\n' + all.slice(k * 47000, k * 47000 + 49000) + '\nENDRPART\n' + all.slice(0, 30000));
};
