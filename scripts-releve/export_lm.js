// Export « Lead magnet » : à lancer dans l'onglet Instagram APRÈS extract.js (window.__T rempli).
// Une ligne par message de Lauric qui propose ou envoie un lead magnet (scan dirigeant Tally, vidéo YouTube),
// avec ce que le lead en a fait : vu, réaction, réponse. Sortie compacte (tranches L<k>) lue par get_page_text,
// puis `python3 lead_magnets.py <fichier> --date JJ/MM/AAAA` → data/lead-magnets.json.
const EXC=['constant_blt','majorel_alex','juliensergent_','lrtemmanuelle','damienrealise'];
const TPL=[
  ['LIKE',/merci pour ton like sur mon post/i],
  ['BIENV',/bienvenue sur mon compte/i],
  ['RESS',/ressource 100\s*% maison/i],
  ['RELSCAN',/(jet[ée]|regard[ée]) un (œ|oe)il au scan|as-tu (fait|rempli) (le|ton) scan/i],
];
const kindOf=x=>/tally\.so/i.test(x)?'scan_lien':/youtu\.?be/i.test(x)?'yt':/\bscan\b/i.test(x)?'scan_offre':'';
const clean=s=>(s||'').replace(/┃/g,'|').replace(/\r?\n/g,'⏎').slice(0,220);
const out=[];
for(const t of window.__T){
  if(!t.u||EXC.includes(t.u)) continue;
  const it=t.items;
  it.forEach((i,k)=>{
    if(i.w!=='L'||!i.x) return;
    const kind=kindOf(i.x); if(!kind) return;
    const tpl=(TPL.find(([,re])=>re.test(i.x))||['PERSO'])[0];
    const after=it.slice(k+1);
    const rep=after.find(m=>m.w==='P'&&m.ty!=='action_log');
    const reac=(i.re||'').includes('P')||after.some(m=>m.w==='P'&&m.ty==='action_log');
    const vu=t.seen>=i.t||!!rep||reac;
    const repTxt=rep?(rep.x||('['+rep.ty+']')):'';
    const firstL=it.find(m=>m.w==='L');
    out.push([t.u,clean(t.n),t.id,kind,tpl,i.t,vu?1:0,reac?1:0,rep?rep.t:0,clean(repTxt),clean(i.x),firstL&&firstL.t===i.t?1:0,it.length].join('┃'));
  });
}
window.__outLM='PSEUDO┃NOM┃THREAD┃KIND┃TPL┃TS┃VU┃REAC┃REPTS┃REPTXT┃TEXTE┃PREMIER┃NITEMS\n'+out.join('\n')+'\nENDLM';
window.__dump=(txt)=>{const m=document.querySelector('main')||document.body;m.innerHTML='';const d=document.createElement('pre');d.textContent=txt;m.appendChild(d);return txt.length};
window.__lpart=(k)=>{const s=window.__outLM.slice(k*47000,k*47000+49000); return window.__dump('L'+k+'\n'+s+'\nENDLPART\n'+window.__outLM.slice(0,30000))};
'envois '+out.length+' len '+window.__outLM.length+' parts '+Math.ceil(window.__outLM.length/47000)
