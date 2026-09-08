# recolle part0..partN par ligne commune → dump.txt
import glob,re
parts=sorted(glob.glob('part*.txt'),key=lambda p:int(re.findall(r'\d+',p)[0]))
out=open(parts[0]).read()
for p in parts[1:]:
    t=open(p).read()
    # première ligne complète de t
    first_nl=t.find('\n'); lines=t.split('\n')
    anchor=None
    for l in lines[1:6]:
        if len(l)>30 and l in out: anchor=l; break
    if not anchor: print('NO ANCHOR',p); continue
    i=out.rfind(anchor); out=out[:i]+t[t.find(anchor):]
    print(p,'ok',len(out))
open('dump.txt','w').write(out)
print('lines',out.count('\n'),'ENDDUMP' in out)
