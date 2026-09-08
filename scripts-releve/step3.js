const T=window.__T, EXC=['constant_blt','majorel_alex','juliensergent_','lrtemmanuelle','damienrealise'];
const cl=s=>(s||'').replace(/[┃\t]/g,' ').replace(/\r?\n/g,'⏎').trim();
const code=s=>{ if(!s) return ''; if(/offre (à|a) tous mes abonnés/i.test(s)) return '{BIENV}'; if(/merci pour ton like sur mon post/i.test(s)) return '{LIKE}'; if(/Je me demandais simplement si tu avais bien reçu mon message/i.test(s)) return '{RELB}'; if(/^Hello[^⏎]{0,25}, tu vas bien \?⏎⏎Tu es toi même entrepreneu/i.test(cl(s))) return '{RELQ}'; if(/sûrement vu, ici je parle/i.test(s)) return '{A}'; if(/Merci beaucoup pour ton abonnement, ça fait super plaisir/i.test(s)) return '{B}'; return cl(s); };
const rows=[], act={};
for(const t of T){
  if(EXC.includes(t.u)) continue;
  const L=t.items.filter(i=>i.w==='L'), P=t.items.filter(i=>i.w==='P'); if(!L.length) continue;
  const groups=[]; for(const i of L){const g=groups[groups.length-1]; if(g&&i.t-g.end<900){g.end=i.t;g.items.push(i);} else groups.push({start:i.t,end:i.t,items:[i]});}
  const firstIsAcc=t.items[0].w==='L';
  groups.forEach((g,idx)=>{const d=new Date(g.start*1000).toLocaleDateString('fr-CA',{timeZone:'Europe/Paris'}); const a=act[d]=act[d]||{acc:0,rel:0,voc:0}; if(idx===0&&firstIsAcc&&t.nItems<20)a.acc++; else a.rel++; if(g.items.some(i=>i.ty==='voice_media'))a.voc++;});
  const C0=1787781600, recent=L.some(i=>i.t>=C0);
  const g0=recent?(firstIsAcc&&t.items[0].t>=C0?groups[0]:groups.find(g=>g.start>=C0)):groups[0];
  const accText=g0.items.filter(i=>i.x).map(i=>i.x).join('\n'), accVoc=g0.items.some(i=>i.ty==='voice_media');
  const lastLg=groups[groups.length-1], lastP=P[P.length-1];
  const lastLText=lastLg.items.filter(i=>i.x).map(i=>i.x).join('\n')||(lastLg.items.some(i=>i.ty==='voice_media')?'[vocal]':'['+lastLg.items[0].ty+']');
  const relDays=groups.filter(g=>g!==g0).map(g=>g.start).join(','), reagi=L.some(i=>/P/.test(i.re))?1:0;
  rows.push([t.u,cl(t.n),g0.start,code(accText),accVoc?1:0,t.seen||0,lastLg.start,code(lastLText),lastP?lastP.t:0,lastP?cl(lastP.x||('['+lastP.ty+']')).slice(0,400):'',t.rs,t.id,L.length,P.length,relDays,firstIsAcc?1:0,recent?1:0,t.items[0].t,t.nItems,reagi].join('┃'));
}
const actLines=Object.keys(act).sort().map(d=>'ACT┃'+d+'┃'+act[d].acc+'┃'+act[d].rel+'┃'+act[d].voc);
window.__out4='RICH2\n'+rows.join('\n')+'\n'+actLines.join('\n')+'\nENDDUMP';
window.__dump=(txt)=>{const m=document.querySelector('main');m.innerHTML='';const d=document.createElement('pre');d.textContent=txt;m.appendChild(d);return txt.length};
window.__part=(k)=>{const s=window.__out4.slice(k*47000,k*47000+49000); return window.__dump('P'+k+'\n'+s+'\nENDPART\n'+window.__out4.slice(0,30000))};
'len='+window.__out4.length+' rows='+rows.length+' days='+actLines.length+' parts='+Math.ceil(window.__out4.length/47000)+' oldest='+new Date(Math.min(...T.map(t=>t.la))*1000).toLocaleDateString('fr-FR')+' mois='+JSON.stringify(T.reduce((a,t)=>{const k=new Date(t.la*1000).toISOString().slice(0,7);a[k]=(a[k]||0)+1;return a},{}))
