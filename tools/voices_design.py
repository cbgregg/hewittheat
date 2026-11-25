import json,os,sys,urllib.request,base64
K=os.environ['ELEVEN'];H={'xi-api-key':K,'Content-Type':'application/json'}
def post(url,body,raw=False):
    r=urllib.request.urlopen(urllib.request.Request('https://api.elevenlabs.io'+url,data=json.dumps(body).encode(),headers=H),timeout=180)
    return r.read() if raw else json.load(r)
BRIEF={
 'danny':("American man in his mid thirties from the Pacific Northwest, working class. Dry, tired and understated, with a low, slightly rough voice. Unhurried, natural conversational delivery, never theatrical.","I left for eight years. Came back with a duffel bag and a car that is not mine. First call I got was from the library, and nobody calls from the library with good news."),
 'marge':("American woman in her early seventies, a retired librarian. Slightly raspy, sharp and stern but warm underneath. Clear diction, measured pace, natural and conversational.","They cut our hours again. Closed Sundays, closed Mondays, the same week they found millions for a ballpark. Four thousand signatures, and the clerk locks the door at five."),
 'pruitt':("American man around sixty with a soft Texas drawl, a property developer. Smooth, friendly on the surface and quietly threatening underneath. Medium low pitch, relaxed unhurried pace.","You know what a parking meter is? It is a clock that pays me when it stops. The city runs the street. I run everywhere you go when the street says no."),
 'attendant':("American man in his early twenties, a bored parking lot attendant. Flat, monotone and indifferent, slightly nasal, casual and low energy.","Ninety is the limit. I can't release it, your tabs are expired. So pay those. Mister Pruitt is hiring, Commerce Building on Hewitt. You will have to walk.")}
vf='voices.json';V=json.load(open(vf)) if os.path.exists(vf) else {}
for who,(desc,text) in BRIEF.items():
    if who in V: continue
    try:
        try: r=post('/v1/text-to-voice/design',{'voice_description':desc,'text':text,'model_id':'eleven_multilingual_ttv_v2'})
        except Exception as e:
            r=post('/v1/text-to-voice/create-previews',{'voice_description':desc,'text':text})
        g=r['previews'][0]['generated_voice_id']
        try: c=post('/v1/text-to-voice',{'voice_name':'HH '+who.title(),'voice_description':desc,'generated_voice_id':g})
        except Exception as e:
            c=post('/v1/text-to-voice/create-voice-from-preview',{'voice_name':'HH '+who.title(),'voice_description':desc,'generated_voice_id':g})
        V[who]=c['voice_id'];json.dump(V,open(vf,'w'));print('voice',who,'ok')
    except Exception as e:
        body=getattr(e,'read',lambda:b'')()[:300] if hasattr(e,'read') else b''
        print('voice',who,'FAIL',str(e)[:80],body)
print(sorted(V))
