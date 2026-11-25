import json,sys
p=sys.argv[1]+'/data/story.json';s=json.load(open(p))
D=lambda w,t,**k:dict(w=w,t=t,**k)
s['cast']['attendant']={"n":"Lot Attendant","c":"#b8c0c8","ch":"man","look":{"sh":"#d9a13a","pa":"#2a3550","tn":"#c99a76","hair":"#2a1d14"}}
s['cast']['pruitt'].pop('low',None)
new=[
{"id":"w1","title":"WELCOME BACK","giver":"Lot Attendant","who":"attendant","ch":"man","at":"Wetmore Theatre Plaza","reward":50,
 "intro":[D("danny","Ninety one minutes."),D("attendant","Ninety is the limit."),D("danny","I can pay the ticket."),D("attendant","Can't release it. Your tabs are expired."),
          D("danny","I can't renew the tabs. There are toll penalties on the plate."),D("attendant","So pay those."),D("danny","With the job I can't drive to."),
          D("attendant","Mister Pruitt is hiring. Commerce Building, on Hewitt. You'll have to walk.")],
 "steps":[{"t":"go","lm":"Commerce Building","text":"Your car is booted. Walk to Pruitt's office at the Commerce Building"}],
 "outro":[D("pruitt","You know what a parking meter is, Danny? It is a clock that pays me when it stops."),D("danny","The city runs the meters."),
          D("pruitt","The city runs the street. I run everywhere you go when the street says no.")],
 "news":"Port Gardner Radio news. Downtown parking: experts say ninety minutes is plenty, if you know what you want."},
{"id":"w2","title":"90 MINUTES","giver":"Lyle Pruitt","who":"pruitt","ch":"rpm","at":"Commerce Building","reward":400,
 "intro":[D("pruitt","Cars on Wetmore and Colby are about to hit ninety minutes. I want them in my lot before the owners finish lunch."),D("danny","And my car?"),
          D("pruitt","The boot comes off when you bring me two. Take whatever is over the limit.")],
 "steps":[{"t":"steal","lm":"Wetmore Theatre Plaza","model":"wagon","kind":"civ","text":"A wagon by the theatre plaza just ran over ninety minutes. Take it","done":[D("pruitt","Ninety one minutes. That one is mine now.",r=1)]},
          {"t":"deliver","lm":"Everett Downtown Storage","text":"Drive it to Pruitt's impound lot at Everett Downtown Storage"},
          {"t":"steal","lm":"Everett Public Library","model":"kiri","kind":"civ","text":"One more. A sedan outside the library is over the limit","done":[D("danny","Somebody is going to come out of that library very unhappy.")]},
          {"t":"deliver","lm":"Everett Downtown Storage","text":"Bring the sedan to the impound lot"}],
 "outro":[D("marge","That is my car. I was returning books. The library closes at five now. Did you know that?"),D("danny","I just drive the truck."),D("marge","Everybody just drives the truck, honey.")],
 "news":"Port Gardner Radio news. Tow volumes are up forty percent. City Hall calls it a sign of a busy downtown."}]
s['chapters']=[c for c in s['chapters'] if c['id'] not in ('w1','w2')]
s['chapters']=new+s['chapters']
json.dump(s,open(p,'w'),ensure_ascii=False,separators=(',',':'))
print('chapters',[c['id'] for c in s['chapters']])
