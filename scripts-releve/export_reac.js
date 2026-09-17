// Export « Réactivité » (délai de premier contact des nouveaux abonnés + temps de réponse aux leads).
// À lancer dans l'onglet instagram.com/robots.txt APRÈS la boucle d'extraction à 40 messages (window.__T40).
// Une conv par ligne : R┃pseudo┃étiquettes┃nItems┃vu par le lead┃items ; items séparés par « ; »,
// chaque item = qui (L/P) , timestamp , type , texte court du lead (≤ 60 caractères, sinon vide).
// Tranches R<k> / ENDRPART via window.__rpart(k), recollées par scripts-releve/glue_text.py --prefix R.
const EXC=['constant_blt','majorel_alex','juliensergent_','lrtemmanuelle','damienrealise'];
const TY={text:'t',voice_media:'v',media_share:'m',clip:'c',link:'k',action_log:'a',like:'h',animated_media:'g',raven_media:'r',story_share:'s',reel_share:'e',media:'p',xma_media_share:'m',xma_story_share:'s',xma_reel_share:'e',xma_clip:'c',placeholder:'x',generic_xma:'x'};
const short=s=>(s||'').replace(/[┃;,\t]/g,' ').replace(/\r?\n/g,' ').trim();
const rows=[];
for(const t of window.__T40){
  if(!t.u||EXC.includes(t.u)||t.g||t.nu>1) continue;
  if(!t.items.length) continue;
  const it=t.items.map(i=>[i.w,i.t,TY[i.ty]||('?'+i.ty),i.w==='P'&&i.x&&i.x.length<=60?short(i.x):''].join(',')).join(';');
  rows.push(['R',t.u,short(t.lb),t.nItems,t.seen||0,it].join('┃'));
}
window.__outR='REAC\n'+rows.join('\n')+'\nENDDUMP';
window.__dump=(txt)=>{const m=document.querySelector('main')||document.body;m.innerHTML='';const d=document.createElement('pre');d.textContent=txt;m.appendChild(d);return txt.length};
window.__rpart=(k)=>{const s=window.__outR.slice(k*47000,k*47000+49000); return window.__dump('R'+k+'\n'+s+'\nENDRPART\n'+window.__outR.slice(0,30000))};
'rows '+rows.length+' len '+window.__outR.length+' parts '+Math.ceil(window.__outR.length/47000)
