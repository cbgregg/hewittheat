import json,sys,math
from PIL import Image,ImageDraw,ImageFont
W=json.load(open(''+__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__)))+'/data/world.json'));N=W['nodes'];E=W['edges'];NM=W['names'];B=W['bld']
def street(nm): return [e for e in E if NM[e[4]]==nm]
def cross(a,b):
    na=set();[na.update(e[:2]) for e in street(a)];nb=set();[nb.update(e[:2]) for e in street(b)];c=na&nb
    if c: i=sorted(c)[0];return N[i][0],N[i][1]
    best=None
    for i in na:
        for j in nb:
            d=math.hypot(N[i][0]-N[j][0],N[i][1]-N[j][1])
            if best is None or d<best[0]: best=(d,(N[i][0]+N[j][0])/2,(N[i][1]+N[j][1])/2)
    return best[1],best[2]
def draw(x0,y0,x1,y1,out,sc=None,label=True):
    sc=sc or 1700/(x1-x0);Wd,Hd=int((x1-x0)*sc),int((y1-y0)*sc);im=Image.new('RGB',(Wd,Hd),(235,235,230));d=ImageDraw.Draw(im)
    try: f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',11);fb=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',14)
    except: f=fb=None
    X=lambda x:(x-x0)*sc;Y=lambda y:(y-y0)*sc
    for e in E:
        a,b=N[e[0]],N[e[1]]
        if max(a[0],b[0])<x0 or min(a[0],b[0])>x1 or max(a[1],b[1])<y0 or min(a[1],b[1])>y1: continue
        d.line([X(a[0]),Y(a[1]),X(b[0]),Y(b[1])],fill=(200,200,205),width=max(2,int(e[3]*sc)))
    seen={}
    for e in E:
        a,b=N[e[0]],N[e[1]];mx,my=(a[0]+b[0])/2,(a[1]+b[1])/2
        if x0<mx<x1 and y0<my<y1:
            nm=NM[e[4]];k=(nm,int(mx//900),int(my//900))
            if k not in seen: seen[k]=1;d.text((X(mx)-20,Y(my)-6),nm,fill=(40,60,160),font=fb)
    KC={0:(250,225,170),3:(230,215,190),1:(240,150,140),2:(160,190,240),4:(190,190,190),5:(200,160,220)}
    ids=[]
    for i,b in enumerate(B):
        n=(len(b)-3)//2;px=[b[3+k*2] for k in range(n)];py=[b[4+k*2] for k in range(n)];cx,cy=sum(px)/n,sum(py)/n
        if not(x0<cx<x1 and y0<cy<y1): continue
        d.polygon([(X(px[k]),Y(py[k])) for k in range(n)],fill=KC.get(b[1],(220,220,220)),outline=(60,60,60));ids.append(i)
        if label: d.text((X(cx)-12,Y(cy)-10),'%d\n%d'%(i,b[0]/10/3.3+0.5),fill=(0,0,0),font=f)
    for p in W['pois']:
        if x0<p[1]<x1 and y0<p[2]<y1: d.ellipse([X(p[1])-3,Y(p[2])-3,X(p[1])+3,Y(p[2])+3],fill=(0,140,0));d.text((X(p[1])+5,Y(p[2])-5),p[0][:26],fill=(0,110,0),font=f)
    im.save(out);return ids
if __name__=='__main__':
    a=sys.argv[1:]
    if a[0]=='x':
        for s in a[1].split(','):
            for t in a[2].split(','): print(s,'&',t,[round(v) for v in cross(s,t)])
    else:
        x0,y0,x1,y1=[float(v) for v in a[:4]];print(len(draw(x0,y0,x1,y1,a[4])))
