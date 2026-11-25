import json,sys,urllib.request,os,zipfile,io
tok=os.environ['SKF']
for name,uid in [a.split('=') for a in sys.argv[1:]]:
    d='dl/'+name
    if os.path.exists(d+'/scene.gltf') or os.path.exists(d+'/done'): print(name,'cached');continue
    try:
        r=json.load(urllib.request.urlopen(urllib.request.Request('https://api.sketchfab.com/v3/models/%s/download'%uid,headers={'Authorization':'Token '+tok}),timeout=40))
        g=r.get('glb') or r.get('gltf')
        data=urllib.request.urlopen(g['url'],timeout=180).read()
        os.makedirs(d,exist_ok=True)
        if 'glb' in r and g is r['glb']: open(d+'/scene.glb','wb').write(data)
        else:
            z=zipfile.ZipFile(io.BytesIO(data))
            for zi in z.infolist():
                if zi.filename.startswith('/') or '..' in zi.filename: continue
                z.extract(zi,d)
        open(d+'/done','w').write(uid)
        print(name,'ok',len(data)//1024,'KB',sorted(os.listdir(d))[:5])
    except Exception as e: print(name,'FAIL',str(e)[:160])
