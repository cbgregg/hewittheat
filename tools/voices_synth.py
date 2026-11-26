import json,os,sys,urllib.request,base64,hashlib,glob
REPO=sys.argv[1];K=os.environ['ELEVEN'];V=json.load(open('voices.json'))
s=json.load(open(REPO+'/data/story.json'))
lines={};DIR={}   # key -> (pack, who, text); DIR: key -> acted version of the line (audio tags, emphasis) for the expressive model
for i,l in enumerate(s['prologue']): lines['v_pro_%d'%i]=('c0',l['w'],l['t']);DIR['v_pro_%d'%i]=l.get('d')
for i,l in enumerate(s['epilogue']): lines['v_epi_%d'%i]=(None,l['w'],l['t'])
for c in s['chapters']:
    for part in ('pre','intro','outro','post'):
        for i,l in enumerate(c.get(part,[])): lines['v_%s_%s_%d'%(c['id'],part,i)]=(c['id'],l['w'],l['t']);DIR['v_%s_%s_%d'%(c['id'],part,i)]=l.get('d')
    for si,st in enumerate(c['steps']):
        for tag,f in (('r','radio'),('l','lines'),('d','done')):
            for i,l in enumerate(st.get(f,[])): lines['v_%s_s%d%s_%d'%(c['id'],si,tag,i)]=(c['id'],l['w'],l['t']);DIR['v_%s_s%d%s_%d'%(c['id'],si,tag,i)]=l.get('d')
packs={}
for f in glob.glob(REPO+'/data/vo_*.json'):
    packs[os.path.basename(f)[3:-5]]=json.load(open(f))
have={k:p for p,d in packs.items() for k in d}
miss=[k for k in lines if k not in have and lines[k][0] not in ('w1','w2')]
extra=[k for k in have if k not in lines]
print('lines',len(lines),'existing keys',len(have),'unmatched story lines',miss[:6],'unmatched pack keys',extra[:6])
os.makedirs('cache_hq',exist_ok=True)
n=chars=0
for k,(pk,w,t) in lines.items():
    if w not in V: continue
    pk=pk or have.get(k)
    if pk is None: continue
    d=DIR.get(k);h=hashlib.sha1((V[w]+'|'+t+('|v4|'+d if d else '')).encode()).hexdigest()[:16];cf='cache_hq/%s.mp3'%h
    if not os.path.exists(cf):
        body=json.dumps({'text':d,'model_id':'eleven_v4','voice_settings':{'stability':0.5,'similarity_boost':0.8}} if d else {'text':t,'model_id':'eleven_multilingual_v2','voice_settings':{'stability':0.5,'similarity_boost':0.8,'style':0.15}}).encode()
        try:
            a=urllib.request.urlopen(urllib.request.Request('https://api.elevenlabs.io/v1/text-to-speech/%s?output_format=mp3_44100_96'%V[w],data=body,headers={'xi-api-key':K,'Content-Type':'application/json'}),timeout=120).read()
        except Exception as e:
            print('FAIL',k,str(e)[:60],(e.read()[:160] if hasattr(e,'read') else ''));continue
        open(cf,'wb').write(a);chars+=len(d or t)
    packs.setdefault(pk,{})[k]=base64.b64encode(open(cf,'rb').read()).decode();n+=1
for p,d in packs.items(): json.dump(d,open(REPO+'/data/vo_%s.json'%p,'w'),separators=(',',':'))
by={}
for k,(pk,w,t) in lines.items(): by[w]=by.get(w,0)+1
print('voiced',n,'new chars',chars,'lines by speaker',by,'packs',{p:len(d) for p,d in sorted(packs.items())})
