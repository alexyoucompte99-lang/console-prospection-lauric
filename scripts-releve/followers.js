window.__F=[]; window.__fstate='start'; window.__fmax=null; window.__flat=[]; window.__FMAX=10;
(async()=>{ const H={'x-ig-app-id':'936619743392459','x-requested-with':'XMLHttpRequest'}; let pages=0;
try{ while(pages<window.__FMAX){
  const u='/api/v1/friendships/77138870834/followers/?count=50&search_surface=follow_list_page'+(window.__fmax?'&max_id='+encodeURIComponent(window.__fmax):'');
  const t0=Date.now(); const r=await fetch(u,{credentials:'include',headers:H}); const lat=Date.now()-t0; window.__flat.push(lat);
  if(r.status===429){window.__fstate='RATE LIMIT page '+(pages+1);return;} if(!r.ok){window.__fstate='ERR '+r.status;return;}
  const j=await r.json();
  for(const x of (j.users||[])) window.__F.push({pk:String(x.pk),u:x.username,n:x.full_name||'',p:x.is_private?1:0,v:x.is_verified?1:0});
  pages++; window.__fstate='page '+pages+' users '+window.__F.length+' lat '+lat+'ms'; window.__fmax=j.next_max_id||null;
  if(!window.__fmax){window.__fstate='done (fin) users '+window.__F.length;return;}
  if(lat>20000){window.__fstate='STOP lenteur '+lat+'ms page '+pages;return;}
  await new Promise(r=>setTimeout(r,15000)); }
window.__fstate='done(max) users '+window.__F.length; }catch(e){window.__fstate='EXC '+e.message} })();
'started'
