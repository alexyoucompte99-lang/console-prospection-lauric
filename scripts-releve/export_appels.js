// Export complet pour le sous-onglet « Appels proposés » : à lancer dans l'onglet Instagram APRÈS extract.js (window.__T).
// Garde les convs utiles (le lead a écrit, ou Lauric a proposé un appel), une conv JSON par ligne, tranches J<k>.
const EXC=['constant_blt','majorel_alex','juliensergent_','lrtemmanuelle','damienrealise'];
const PROP=/\b(appel|call|visio|cr[ée]neau|rdv|rendez[- ]vous|calendly|zoom|google ?meet|t[ée]l[ée]phone|on s'appelle|t'appeler|vous appeler|de vive voix|1 ?h d'accompagnement)\b/i;
const keep=window.__T.filter(t=>t.u&&!EXC.includes(t.u)&&t.items.some(i=>i.w==='L')&&(t.items.some(i=>i.w==='P'&&i.ty!=='action_log')||t.items.some(i=>i.w==='L'&&i.x&&(PROP.test(i.x)||(/dispo/i.test(i.x)&&i.x.includes('?'))))));
window.__out5=keep.map(t=>JSON.stringify({id:t.id,u:t.u,n:t.n,seen:t.seen,la:t.la,nItems:t.nItems,items:t.items.map(i=>({w:i.w,t:i.t,ty:i.ty,x:i.x||''}))})).join('\n')+'\nENDDUMP';
window.__dump=(txt)=>{const m=document.querySelector('main')||document.body;m.innerHTML='';const d=document.createElement('pre');d.textContent=txt;m.appendChild(d);return txt.length};
window.__jpart=(k)=>{const s=window.__out5.slice(k*47000,k*47000+49000); return window.__dump('J'+k+'\n'+s+'\nENDJPART\n'+window.__out5.slice(0,30000))};
'keep '+keep.length+' len '+window.__out5.length+' parts '+Math.ceil(window.__out5.length/47000)
