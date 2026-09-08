window.__T=[]; window.__state2='start'; window.__cursor=null; window.__seen=new Set();
(async()=>{ const H={'x-ig-app-id':'936619743392459','x-requested-with':'XMLHttpRequest'}; const ME='77138870834'; let pages=0;
try{ while(pages<MAXPAGES){
  const u='/api/v1/direct_v2/inbox/?folder=&limit=40&thread_message_limit=20'+(window.__cursor?'&cursor='+encodeURIComponent(window.__cursor):'');
  const r=await fetch(u,{credentials:'include',headers:H});
  if(r.status===429){window.__state2='RATE LIMIT page '+(pages+1);return;} if(!r.ok){window.__state2='ERR '+r.status;return;}
  const j=await r.json();
  for(const t of j.inbox.threads){ if(window.__seen.has(t.thread_id)) continue; window.__seen.add(t.thread_id);
    const lead=t.users[0]||{}; const pk=String(lead.pk||'');
    const items=(t.items||[]).slice().sort((a,b)=>a.timestamp-b.timestamp).map(i=>({w:String(i.user_id)===ME?'L':'P',t:Math.floor(i.timestamp/1e6),ty:i.item_type,x:i.item_type==='text'?(i.text||''):(i.item_type==='link'&&i.link?(i.link.text||''):''),re:(i.reactions&&i.reactions.emojis&&i.reactions.emojis.length)?i.reactions.emojis.map(e=>String(e.sender_id)===ME?'L':'P').join(''):''}));
    window.__T.push({id:t.thread_id,u:lead.username||'',n:lead.full_name||'',rs:t.read_state,seen:(t.last_seen_at&&t.last_seen_at[pk]&&t.last_seen_at[pk].timestamp)?Math.floor(t.last_seen_at[pk].timestamp/1e6):0,la:Math.floor((t.last_activity_at||0)/1e6),items,nItems:(t.items||[]).length}); }
  pages++; window.__state2='page '+pages+' threads '+window.__T.length; window.__cursor=j.inbox.oldest_cursor;
  if(!j.inbox.has_older){window.__state2='done';return;} await new Promise(r=>setTimeout(r,8000)); }
window.__state2='done(max)'; }catch(e){window.__state2='EXC '+e.message} })();
