import json,sys,glob,os
k=sys.argv[1]
files=sorted(glob.glob('/Users/alex/.claude/projects/-Users-alex-Alex/b34a93d1-bcb1-4e6c-8f93-47562d7fa647/tool-results/mcp-claude-in-chrome-get_page_text-*.txt'),key=os.path.getmtime)
for p in reversed(files):
    t=''.join(x['text'] for x in json.load(open(p)))
    i=t.find('P'+k+'\n')
    if i<0 or i>400: continue
    body=t[i+len(k)+2:]
    j=body.find('\nENDPART')
    if j<0:
        for m in ('\n\n[output truncated','\n\nTab Context'):
            jj=body.find(m)
            if jj>0: body=body[:jj]
        complete=False
    else: body=body[:j]; complete=True
    open(f'part{k}.txt','w').write(body); print('part',k,'len',len(body),'complete',complete); break
else: print('NOT FOUND',k)
