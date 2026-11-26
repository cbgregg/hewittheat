import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {clone as skClone} from 'three/addons/utils/SkeletonUtils.js';
/* Downtown Everett built from City of Everett GIS data: street centerlines, building footprints, 2 ft contours, parks, bus stops, 2022 aerial imagery. 10 units = 1 m, one tile = 2 m. */
const PI=Math.PI,T=20,DV='?v=1125m';
let MW=0,MH=0,WW=0,WH=0,map=new Uint8Array(1),HMAP=null,gw=0,gh=0,GS=80,WORLD=null;
const WATER=0,GRASS=1,ROAD=2,WALK=3,BLDG=4,PARK=5,CONC=6,HOUSE=7;
const SOL=[1,0,0,0,1,0,0,0];
const I=(x,y)=>y*MW+x,inb=(x,y)=>x>=0&&y>=0&&x<MW&&y<MH;
const tile=(x,y)=>inb(x,y)?map[I(x,y)]:(GT&&gReady?ROAD:WATER);
const tileAt=(px,py)=>tile(Math.floor(px/T),Math.floor(py/T));
function h2(x,y){let n=(Math.imul(x,374761393)+Math.imul(y,668265263))|0;n=Math.imul(n^(n>>>13),1274126177);return((n^(n>>>16))>>>0)/4294967296;}
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
const adiff=(a,b)=>{let d=(a-b)%(2*PI);if(d>PI)d-=2*PI;if(d<-PI)d+=2*PI;return d;};
const rand=(a,b)=>a+Math.random()*(b-a),pick=a=>a[(Math.random()*a.length)|0];
const dist=(ax,ay,bx,by)=>Math.hypot(ax-bx,ay-by);
const r10=v=>Math.round(v/10)*10;
function Hat(x,y){if(!HMAP)return 0;const fx=clamp(x/GS,0,gw-1.001),fy=clamp(y/GS,0,gh-1.001),ix=fx|0,iy=fy|0,ax=fx-ix,ay=fy-iy,i=iy*gw+ix;return(HMAP[i]*(1-ax)+HMAP[i+1]*ax)*(1-ay)+(HMAP[i+gw]*(1-ax)+HMAP[i+gw+1]*ax)*ay;}
const solidAt=(px,py)=>{const x=Math.floor(px/T),y=Math.floor(py/T);return !inb(x,y)?!(GT&&gReady):SOL[map[I(x,y)]]===1;};
function nearestTile(cx,cy,type,maxr){cx=Math.floor(cx);cy=Math.floor(cy);let best=null,bd=1e9;
 for(let r=0;r<(maxr||80)&&!best;r++){for(let y=cy-r;y<=cy+r;y++)for(let x=cx-r;x<=cx+r;x++){if(Math.max(Math.abs(x-cx),Math.abs(y-cy))!==r)continue;if(inb(x,y)&&map[I(x,y)]===type){const d=Math.hypot(x-cx,y-cy);if(d<bd){bd=d;best={x:(x+.5)*T,y:(y+.5)*T};}}}}
 return best;}
const nodes=[],edges=new Map(),egrid=new Map();let LM=[],DEST=[],STOPS=[],SPOTS=[],PKG=[],AIRIMG=[];
const lm=n=>LM.find(l=>l.n===n);
function lane(ai,bi){const A=nodes[ai],B=nodes[bi];let dx=B.x-A.x,dy=B.y-A.y;const L=Math.hypot(dx,dy)||1;dx/=L;dy/=L;const e=edges.get(ai*65536+bi)||{o:16,lim:108};return{sx:A.x-dy*e.o,sy:A.y+dx*e.o,dx,dy,L,lim:e.lim};}
function nearestNode(x,y){let b=0,bd=1e9;for(let i=0;i<nodes.length;i++){const d=Math.abs(nodes[i].x-x)+Math.abs(nodes[i].y-y);if(d<bd){bd=d;b=i;}}return b;}
function streetAt(x,y){const cx=Math.floor(x/600),cy=Math.floor(y/600);let bn=null,bd=1e9;
 for(let j=-1;j<=1;j++)for(let i=-1;i<=1;i++){const l=egrid.get((cx+i)+','+(cy+j));if(!l)continue;for(const [a,b,e] of l){const A=nodes[a],B=nodes[b],dx=B.x-A.x,dy=B.y-A.y,t=clamp(((x-A.x)*dx+(y-A.y)*dy)/(dx*dx+dy*dy||1),0,1),d=Math.hypot(A.x+dx*t-x,A.y+dy*t-y)-e.w/2;if(d<bd){bd=d;bn=e.name;}}}
 return bd<90?bn:null;}
function xnode(n1,n2){for(let i=0;i<nodes.length;i++){const s=new Set(nodes[i].nb.map(k=>edges.get(i*65536+k).name));if(s.has(n1)&&s.has(n2))return i;}return -1;}
async function loadImg(src){const im=new Image();im.src=src;await im.decode();return im;}
function pixels(im){const c=document.createElement('canvas');c.width=im.naturalWidth;c.height=im.naturalHeight;const x=c.getContext('2d',{willReadFrequently:true});x.drawImage(im,0,0);return x.getImageData(0,0,c.width,c.height).data;}
let CITY=null,DBGC=null,EXTRA={trees:[],props:[]};const PROPS={},SETS={};
async function loadWorld(){
 WORLD=await (await fetch('data/world.json'+DV)).json();try{CITY=(await new GLTFLoader().loadAsync('data/city.glb'+DV)).scene;}catch(e){console.warn('city model unavailable, using generated buildings',e);CITY=null;}
 try{EXTRA=Object.assign(EXTRA,await (await fetch('data/extras.json'+DV)).json());}catch(e){}
 await Promise.all(['lamp','signal','busstop','tree','pine','hydrant','bench','trash','excavator'].map(async k=>{try{PROPS[k]=(await new GLTFLoader().loadAsync('models/p_'+k+'.glb'+DV)).scene;}catch(e){console.warn('prop missing',k);}}));
 for(const k of ['office','chamber','bar'])try{const g=(await new GLTFLoader().loadAsync('models/set_'+k+'.glb'+DV)).scene;g.visible=false;g.traverse(o=>{if(o.isMesh){o.castShadow=false;o.receiveShadow=/^floor|^shell/.test(o.name);}});const LS=k==='bar'?[[0xffb070,1.7,0,24,6],[0xff4a32,0.6,-52,20,12],[0x35d6c2,0.35,-52,16,12],[0xffc890,1.0,0,20,-36]]:[[0xffe2bd,1.5,0,30,0],[0xdcebff,0.8,-30,24,-40]];for(const q of LS){const a=new THREE.PointLight(q[0],q[1],0,0);a.position.set(q[2],q[3],q[4]);g.add(a);}g.userData.k=k==='bar'?0.5:1;SETS[k]=g;}catch(e){console.warn('set missing',k);}MW=WORLD.mw;MH=WORLD.mh;WW=MW*T;WH=MH*T;
 const md=pixels(await loadImg('data/map.png'+DV));map=new Uint8Array(MW*MH);for(let i=0;i<MW*MH;i++)map[i]=Math.round(md[i*4]/30);
 const hd=pixels(await loadImg('data/hm.png'));gw=WORLD.gw;gh=WORLD.gh;GS=WORLD.gs*10;HMAP=new Float32Array(gw*gh);for(let i=0;i<gw*gh;i++)HMAP[i]=((hd[i*4]<<8)|hd[i*4+1])-1000;
 if(window.EV_NOAIR)AIRIMG=[null,null,null,null,null,null];else{for(let ty=0;ty<2;ty++)for(let tx=0;tx<3;tx++)AIRIMG.push(loadImg('data/airlo_'+tx+'_'+ty+'.jpg').catch(()=>null));AIRIMG=await Promise.all(AIRIMG);}
 WORLD.nodes.forEach(n=>nodes.push({x:n[0],y:n[1],nb:[],edge:false,sig:false,r:60}));
 for(const [a,b,w,sp,ni,c] of WORLD.edges){nodes[a].nb.push(b);nodes[b].nb.push(a);const e={w:w*10,lim:sp,o:clamp(w*2,16,32),name:WORLD.names[ni],cls:c};edges.set(a*65536+b,e);edges.set(b*65536+a,e);
  nodes[a].r=Math.max(nodes[a].r,w*5+25);nodes[b].r=Math.max(nodes[b].r,w*5+25);const A=nodes[a],B=nodes[b],k=Math.floor((A.x+B.x)/1200)+','+Math.floor((A.y+B.y)/1200);if(!egrid.has(k))egrid.set(k,[]);egrid.get(k).push([a,b,e]);
  // curbside parking spots on local streets
  const L=dist(A.x,A.y,B.x,B.y);if(c>=6&&L>=300){const dx=(B.x-A.x)/L,dy=(B.y-A.y)/L;for(let t=140;t<L-140;t+=68)for(const s of [-1,1])if(h2((A.x+t)|0,((A.y+s*7)|0))<0.34){const o=w*5-13,x=A.x+dx*t-dy*o*s,y=A.y+dy*t+dx*o*s;if(tileAt(x,y)===ROAD)SPOTS.push({x,y,a:Math.atan2(dy,dx)+(s<0?PI:0),on:false,taken:false});}}}
 for(const s of WORLD.sig)nodes[s].sig=true;
 nodes.forEach(n=>{if(n.nb.length===1&&(n.x<400||n.y<400||n.x>WW-400||n.y>WH-400))n.edge=true;});
 LM=WORLD.pois.map(p=>({n:p[0],cx:p[1],cy:p[2],t:p[3]}));LM.push({n:'Port of Everett',cx:WORLD.piers[1][0],cy:WORLD.piers[1][1],t:'lm'});
 for(const l of LM){l.door=nearestTile(l.cx/T,l.cy/T,ROAD,110);l.curb=nearestTile(l.cx/T,l.cy/T,WALK,110);l.ok=!!l.door&&dist(l.door.x,l.door.y,l.cx,l.cy)<1400;
  if(!l.door){const n=nodes[nearestNode(l.cx,l.cy)];l.door={x:n.x,y:n.y};}if(!l.curb)l.curb=l.door;}
 DEST=LM.filter(l=>l.ok&&l.n!=='Naval Station Everett');
 STOPS=WORLD.stops.map(s=>({x:s[0],y:s[1],n:s[2]}));
 PKG=LM.filter(l=>(l.t==='park'||l.t==='hist'||l.t==='school')).slice(0,25).map((l,i)=>({x:l.curb.x+((i*37)%5-2)*14,y:l.curb.y+((i*53)%5-2)*14,i,n:l.n}));
}
/* ---------- STATE ---------- */
const P={x:0,y:0,a:0,hp:100,car:null,money:0,cd:0,dead:0,bust:false,flash:0,wp:'pistol',am:{pistol:24,smg:0,shotgun:0,rifle:0},own:{pistol:true}};
Object.defineProperty(P,'ammo',{get(){return P.am[P.wp];},set(v){P.am[P.wp]=Math.max(0,v);}});
const WSPEC={pistol:{n:'PISTOL',cd:0.28,dmg:60,range:520,pel:1,spr:0},smg:{n:'SMG',cd:0.085,dmg:26,range:480,pel:1,spr:0.05},shotgun:{n:'SHOTGUN',cd:0.85,dmg:34,range:300,pel:7,spr:0.16},rifle:{n:'AK-47',cd:0.11,dmg:40,range:720,pel:1,spr:0.03}};
let pkgGot={},STREET='',strT=0,spotT=0,autoCd=2,NAV=null,CONTACTS=[],barks=[],bumpCd=0;
function bark(p,t){if(barks.some(b=>b.p===p))return;barks.push({p,t,time:2.6});barkVo(p,t);if(barks.length>6)barks.shift();}
let cars=[],peds=[],fx=[],picks=[],stains=[];
let pts=0,stars=0,cool=0,copT=0,M=null,big=null,toast=null,paused=true,time=0,rain=0,rainT=50;
let shopCd=0,pawnCd=0,hospCd=0,navalT=0;
const TH=[0,1,4,9,16,25];
const CARCOL=['#ffffff','#c9ccd1','#9a3b2f','#3d5a78','#c9b98a','#4f6b52','#34373c','#b9bcc0','#7a1f1f','#27466b'];
let GV=[],SHOP=null,PAWN=null,HOSP=null,COPS=null;
function initPlaces(){
 const st=lm('Everett Station'),ar=lm('Angel of the Winds Arena'),po=lm('Port of Everett');NAV=lm('Naval Station Everett');HOSP=lm('Providence Pacific Campus')||st;COPS=lm('Everett Police HQ')||st;
 GV=[{type:'courier',lm:st.n,x:st.curb.x,y:st.curb.y,cd:0},{type:'export',lm:po.n,x:po.door.x,y:po.door.y,cd:0},{type:'race',lm:ar.n,x:ar.curb.x,y:ar.curb.y,cd:0}];
 const side=(ni,nm)=>{const n=nodes[ni];let k=n.nb.find(q=>edges.get(ni*65536+q).name===nm);if(k==null)k=n.nb[0];const B=nodes[k],L=dist(n.x,n.y,B.x,B.y)||1;return{x:n.x+(B.x-n.x)/L*Math.min(L*0.6,n.r+130),y:n.y+(B.y-n.y)/L*Math.min(L*0.6,n.r+130)};};
 let s=xnode('Broadway','35th St');if(s<0)s=xnode('Broadway','34th St');if(s<0)s=nearestNode(st.cx,st.cy+3000);const sp=side(s,'35th St');SHOP={n:'Body Shop',door:sp,curb:sp};
 let w=xnode('Hewitt Ave','Maple St');if(w<0)w=xnode('Hewitt Ave','Cedar St');if(w<0)w=nearestNode(ar.cx+2000,ar.cy);const wp=side(w,'Maple St'),wc=nearestTile(wp.x/T,wp.y/T,WALK,30)||wp;PAWN={n:'Guns & Ammo',door:wp,curb:wc};
 const face=(x,y,gv)=>Math.atan2(gv.y-y,gv.x-x);
 CONTACTS=[{nm:'Dee - dispatch',who:'dee',ch:'hh_dee',gv:GV[0],hi:'Got a rush job if you can keep it under the limit. Kidding.'},{nm:'Olsen - dock boss',who:'olsen',ch:'hh_olsen',gv:GV[1],hi:'I buy clean cars. Scratch it and the price drops.'},{nm:'Tink - race promoter',who:'tink',ch:'hh_ped_m2',gv:GV[2],hi:'Bring wheels. Seven lights, one clock.'}].map((c,i)=>{const x=c.gv.x+34,y=c.gv.y+(i-1)*8;return Object.assign(c,{x,y,a:face(x,y,c.gv),kind:'civ',col:'#ccc',said:0});});
 try{pkgGot=JSON.parse(localStorage.getItem('everett_pk')||'{}')||{};}catch(e){pkgGot={};}
}
function say(t,s){toast={t,time:s||3};}
function crime(p){pts+=p;cool=0;}
function save(){try{localStorage.setItem('everett_ow',JSON.stringify({m:P.money}));}catch(e){}}
try{const s=JSON.parse(localStorage.getItem('everett_ow')||'null');if(s&&s.m>0)P.money=s.m|0;}catch(e){}

const VSPEC={moto:{f:'v_moto',l:23,ry:PI/2},van:{f:'veh_van',l:60,ry:PI/2},stepvan:{f:'veh_stepvan',l:62,ry:PI/2},foodtruck:{f:'veh_foodtruck',l:68,ry:PI/2},van50:{f:'veh_van50',l:54,ry:PI/2},sedan:{f:'veh_sedan',l:48,ry:PI,tint:1},hatch:{f:'veh_hatch',l:42,ry:PI/2,tint:1},car50:{f:'veh_car50',l:54,ry:PI/2,tint:'Body'},car50b:{f:'veh_car50b',l:54,ry:PI/2},pickup:{f:'veh_pickup50',l:50,ry:PI/2},boxtruck:{f:'veh_boxtruck',l:74,ry:PI/2},bus:{f:'veh_bus',l:112,ry:0},
 police:{f:'v_police',l:52,ry:0,liv:1},taxi:{f:'v_taxi',l:52,ry:0,liv:1},ambulance:{f:'v_ambulance',l:54,ry:0,liv:1},lct:{f:'v_lct',l:64,ry:0},muscle:{f:'v_muscle',l:49,ry:0,tre:/Bodymat/i},fair:{f:'v_fair',l:50,ry:0,tre:/Bodymat/i},kiri:{f:'v_kiri',l:43,ry:0,tre:/Bodymat/i},wagon:{f:'v_wagon',l:50,ry:0,tre:/Bodymat/i},river:{f:'v_river',l:49,ry:0,tre:/Bodymat/i},illinois:{f:'v_illinois',l:52,ry:0,tre:/Bodymat/i}};
const CIVM=['sedan','sedan','hatch','hatch','car50','car50b','pickup','van','van50','stepvan','foodtruck','muscle','fair','fair','kiri','kiri','wagon','wagon','river','river','illinois','illinois','muscle'];
function makeCar(x,y,a,kind,mdl){const k=kind||'civ',has=m=>VSPEC[m].tpl?m:null;let model=mdl||(k==='truck'?(Math.random()<0.5&&has('lct')||'boxtruck'):k==='bus'?'bus':k==='gold'?'car50':k==='cop'?(has('police')||'sedan'):k==='taxi'?(has('taxi')||'sedan'):k==='amb'?(has('ambulance')||'van'):pick(CIVM));if(!VSPEC[model].tpl&&/^[vg]_/.test(VSPEC[model].f))model=k==='truck'?'boxtruck':'sedan';const sp=VSPEC[model];
 const c={x,y,a,v:0,hp:100,mhp:100,kind:k,model,drv:null,ai:null,w:sp.w||20,l:sp.l,max:300,acc:230,col:pick(CARCOL),stuck:0,rev:0,wait:0,lat:0,slip:0,fire:0,dead:false,keep:false,park:false,sir:false,direct:false,gone:false};
 if(k==='cop'){c.col='#ffffff';c.max=350;c.acc=280;}
 else if(k==='taxi')c.col='#f2c21a';
 else if(k==='amb'){c.col='#ffffff';c.max=300;c.hp=c.mhp=140;}
 else if(k==='truck'){c.max=230;c.acc=150;c.hp=c.mhp=160;}
 else if(k==='bus'){c.max=200;c.acc=120;c.hp=c.mhp=220;}
 cars.push(c);return c;}
function carBlocked(x,y,a,c){const co=Math.cos(a),si=Math.sin(a),h=c.l/2-4,s=c.w/2-2;
 return solidAt(x,y)||solidAt(x+co*h,y+si*h)||solidAt(x-co*h,y-si*h)||solidAt(x+co*h-si*s,y+si*h+co*s)||solidAt(x+co*h+si*s,y+si*h-co*s)||solidAt(x-co*h-si*s,y-si*h+co*s)||solidAt(x-co*h+si*s,y-si*h-co*s);}
function viewR(){return 900;}
function spawnOK(x,y,fr,bk){const dx=x-P.x,dy=y-P.y,d=Math.hypot(dx,dy),f=dx*Math.cos(yaw)+dy*Math.sin(yaw);return f>-300?(d>fr&&d<fr+700):(d>bk&&d<bk+700);}
function farOff(x,y,fr,bk){const dx=x-P.x,dy=y-P.y,d=Math.hypot(dx,dy),f=dx*Math.cos(yaw)+dy*Math.sin(yaw);return d>fr||(f<-300&&d>bk);}
function spawnTraffic(kind,any){
 for(let t=0;t<60;t++){const ni=(Math.random()*nodes.length)|0,n=nodes[ni];if(!n.nb.length||!(any?dist(n.x,n.y,P.x,P.y)>400&&dist(n.x,n.y,P.x,P.y)<3600:spawnOK(n.x,n.y,2700,800)))continue;
  const bi=pick(n.nb),b=nodes[bi],e=lane(ni,bi);if(cars.some(c=>dist(c.x,c.y,e.sx,e.sy)<100))continue;
  const c=makeCar(e.sx,e.sy,Math.atan2(b.y-n.y,b.x-n.x),kind);c.drv=kind==='cop'?'cop':'ai';c.ai={a:ni,b:bi};c.v=50;return c;}
 return null;}
function makePed(x,y,kind){const p={x,y,a:pick([0,PI/2,PI,-PI/2]),hp:kind==='cop'?100:60,kind:kind||'civ',st:'walk',t:rand(2,8),dead:false,cd:1,j:0,col:pick(['#c96f6f','#6f8fc9','#7fc96f','#c9b86f','#b36fc9','#e0e0e0','#555','#d98f4f'])};peds.push(p);return p;}
function spawnPed(any){if(Math.random()<0.3&&STOPS.length)for(let t=0;t<12;t++){const s=pick(STOPS),x=s.x+rand(-22,22),y=s.y+rand(-22,22);if((any?dist(x,y,P.x,P.y)<2600:spawnOK(x,y,1500,450))&&!solidAt(x,y)&&tileAt(x,y)!==ROAD){const p=makePed(x,y,'civ');p.st='wait';p.t=rand(25,70);p.a=rand(-PI,PI);return p;}}
 for(let t=0;t<20;t++){const a=rand(0,2*PI),d=rand(any?150:450,2400),x=P.x+Math.cos(a)*d,y=P.y+Math.sin(a)*d,tt=tileAt(x,y);if((tt===WALK||tt===PARK)&&(any||spawnOK(x,y,1500,450))){const tx=Math.floor(x/T),ty=Math.floor(y/T);return makePed((tx+.5)*T,(ty+.5)*T,'civ');}}}

/* ---------- PHYSICS ---------- */
function moveEnt(e,dx,dy,r){let m=false;const ok=(x,y)=>!(solidAt(x-r,y-r)||solidAt(x+r,y-r)||solidAt(x-r,y+r)||solidAt(x+r,y+r));
 if(ok(e.x+dx,e.y)){e.x+=dx;m=true;}if(ok(e.x,e.y+dy)){e.y+=dy;m=true;}return m;}
function carStep(c,thr,steer,hb,dt){
 if(c.dead)thr=0;const pl=c.drv==='player',bike=c.model==='moto',co=Math.cos(c.a),si=Math.sin(c.a);let v=c.v,lat=c.lat||0;
 if(pl){const r=(steer===0?8:5.5)*dt;c.st=(c.st||0)+clamp(steer-(c.st||0),-r,r);steer=c.st;}
 if(thr>0)v+=thr*c.acc*dt*(pl?1.3-clamp(v/c.max,0,1)*0.95:1-clamp(v/c.max,0,1)*0.55);else if(thr<0){if(v>5)v+=thr*(pl?560:390)*dt;else v+=thr*c.acc*0.7*dt;}
 v-=v*(c.dead?3:0.22)*dt;if(thr===0)v-=Math.sign(v)*Math.min(Math.abs(v),38*dt);
 if(hb)v-=Math.sign(v)*Math.min(Math.abs(v),pl?230:520)*dt*(pl?1:1);
 const tt=tileAt(c.x,c.y);if(tt===GRASS||tt===PARK){v*=1-1.0*dt;}
 v-=95*((GT&&c.gy!=null)?clamp(c.gsl||0,-0.3,0.3):(Hat(c.x+co*20,c.y+si*20)-Hat(c.x-co*20,c.y-si*20))/40)*dt;
 v=clamp(v,-c.max*0.35,c.max);
 let vx=co*v-si*lat,vy=si*v+co*lat;
 const lock=0.6-0.43*clamp(Math.abs(v)/c.max,0,1),na=c.a+(pl?clamp(v/(c.l*0.62)*Math.tan(steer*lock)*(hb?1.4:1)*(bike?1.15:1),-3.3,3.3)*dt:steer*dt*2.7*clamp(v/85,-1,1));
 const nc=Math.cos(na),ns=Math.sin(na);v=vx*nc+vy*ns;lat=-vx*ns+vy*nc;
 lat*=Math.exp(-(pl?(hb?1.25:(tt===GRASS||tt===PARK?3.0:(bike?9.5:7.4))*(Math.abs(lat)>75?0.5:1)):10)*dt);c.slip=Math.abs(lat);
 vx=nc*v-ns*lat;vy=ns*v+nc*lat;c.v=v;c.lat=lat;
 const nx=c.x+vx*dt,ny=c.y+vy*dt;
 if(carBlocked(c.x,c.y,c.a,c)||!carBlocked(nx,ny,na,c)){c.x=nx;c.y=ny;c.a=na;return;}
 const imp=Math.hypot(v,lat);
 if(!carBlocked(nx,c.y,c.a,c)){c.x=nx;c.v*=1-2.5*dt;c.lat*=0.5;}
 else if(!carBlocked(c.x,ny,c.a,c)){c.y=ny;c.v*=1-2.5*dt;c.lat*=0.5;}
 else{c.v*=-0.3;c.lat*=-0.3;if(imp>110){c.hp-=imp*0.06;if(c===P.car){shake=Math.min(10,imp*0.03);sfx('crash');}}}
}
function nextEdge(c,cop){const b=c.ai.b,a=c.ai.a,n=nodes[b];let o=n.nb.filter(k=>k!==a);
 if(!o.length){if(!cop&&n.edge&&dist(c.x,c.y,P.x,P.y)>1500){c.gone=true;return;}o=n.nb.slice();}
 if(!o.length)return;let nx=pick(o);
 if(a>=0&&o.length>1&&Math.random()<0.62){const A=nodes[a],ia=Math.atan2(n.y-A.y,n.x-A.x);let bd=9;for(const k of o){const d=Math.abs(adiff(Math.atan2(nodes[k].y-n.y,nodes[k].x-n.x),ia));if(d<bd){bd=d;nx=k;}}}
 if(cop){let bd=1e9;for(const k of o){const d=dist(nodes[k].x,nodes[k].y,P.x,P.y);if(d<bd){bd=d;nx=k;}}}
 c.ai={a:b,b:nx};}
function aiCar(c,dt){
 const cop=c.drv==='cop'&&stars>0&&!P.dead,dp=dist(c.x,c.y,P.x,P.y);let tx,ty,lim=135,red=false;
 const pSlow=!P.car||Math.abs(P.car.v)<50;
 if(cop&&dp<700){c.direct=true;tx=P.x;ty=P.y;lim=c.max;c.sir=true;
  if(dp<150&&pSlow){lim=0;if(Math.abs(c.v)<60&&peds.filter(p=>p.kind==='cop'&&!p.dead).length<6){const s=c.a+PI/2;const p=makePed(c.x+Math.cos(s)*18,c.y+Math.sin(s)*18,'cop');if(solidAt(p.x,p.y)){p.x=c.x;p.y=c.y;}c.drv=null;c.ai=null;c.park=false;return;}}}
 else{
  if(c.direct||!c.ai){c.direct=false;c.ai={a:-1,b:nearestNode(c.x,c.y)};}
  c.sir=cop;const B=nodes[c.ai.b];
  if(c.ai.a<0){tx=B.x;ty=B.y;lim=cop?280:110;if(dist(c.x,c.y,tx,ty)<75)nextEdge(c,cop);}
  else{const ln=lane(c.ai.a,c.ai.b),t=(c.x-ln.sx)*ln.dx+(c.y-ln.sy)*ln.dy,la=Math.min(t+110,ln.L);tx=ln.sx+ln.dx*la;ty=ln.sy+ln.dy*la;lim=cop?Math.max(ln.lim*1.9,300):ln.lim;if(!cop&&B.sig){const dB=ln.L-t;if(dB>B.r+12&&dB<B.r+120&&sigState(Math.abs(ln.dy)>Math.abs(ln.dx))!==2)red=true;}if(t>ln.L-58)nextEdge(c,cop);}
 }
 if(c.gone)return;
 const d=adiff(Math.atan2(ty-c.y,tx-c.x),c.a);let steer=clamp(d*2.4,-1,1),target=lim;
 if(Math.abs(d)>0.45)target=Math.min(target,c.direct?160:75);
 const fd=c.l/2+22+Math.abs(c.v)*0.14,fc=Math.cos(c.a),fs=Math.sin(c.a);let obs=false;
 const ahead=(ox,oy,ol,ow)=>{const dx=ox-c.x,dy=oy-c.y,f=dx*fc+dy*fs;return f>0&&f<fd+ol&&Math.abs(-dx*fs+dy*fc)<c.w/2+ow;};
 if(!cop){if(!P.car&&!P.dead&&ahead(P.x,P.y,6,7))obs=true;if(!obs)for(const p of peds)if(!p.dead&&ahead(p.x,p.y,5,6)){obs=true;break;}}
 if(!obs)for(const o of cars){if(o===c||(cop&&o===P.car))continue;if(Math.abs(o.x-c.x)+Math.abs(o.y-c.y)<260&&ahead(o.x,o.y,o.l/2,o.w/2+1)){obs=true;break;}}
 if(obs){c.wait+=dt;if(c.wait<9)target=0;else if(c.wait>10.5)c.wait=0;else target=45;}else c.wait=Math.max(0,c.wait-dt*0.5);
 if(red)target=0;
 let thr=c.v<target-5?1:(c.v>target+10?-1:0);
 if(c.rev>0){c.rev-=dt;thr=-1;steer=-steer;}
 else if(target>0&&Math.abs(c.v)<8){c.stuck+=dt;if(c.stuck>1.8){c.stuck=0;c.rev=1;}}else c.stuck=0;
 carStep(c,thr,steer,false,dt);
}
function killPed(p,byPlayer){if(p.dead)return;sfx('thud',p.x,p.y);p.dead=true;p.t=0;stains.push({x:p.x,y:p.y,t:40});if(stains.length>40)stains.shift();
 if(p.kind==='cop')picks.push({x:p.x,y:p.y,k:'ammo',amt:12,t:40});else if(Math.random()<0.8)picks.push({x:p.x,y:p.y,k:'cash',amt:(rand(5,45))|0,t:40});
 if(byPlayer)crime(p.kind==='cop'?6:2);scare(p.x,p.y,260);}
function scare(x,y,r){for(const p of peds)if(!p.dead&&p.kind==='civ'&&dist(p.x,p.y,x,y)<r){if(p.st!=='flee'&&Math.random()<0.25)bark(p,pick(['He has a gun!','Run!','Call 911!','Get down!']));else if(p.st!=='flee'&&(p.ch==='michelle'||p.ch==='woman'||/ped_w|marge|dee/.test(p.ch))&&scrCd<=0){scrCd=5;play('s_scream',0.5,p.x,p.y);}p.st='flee';p.t=rand(4,7);p.j=rand(-.5,.5);}}
function hurt(d){if(P.dead||CUT)return;P.hp-=d;P.flash=0.25;if(P.hp<=0)die(false);}
function die(b){if(P.dead||CUT)return;P.dead=3;P.bust=b;P.hp=Math.max(0,P.hp);if(P.car){P.car.drv=null;P.car=null;}big={t:b?'BUSTED':'WASTED',c:b?'#3d7be0':'#c0392b',time:3};sfx('fail');if(b)vo(pick(['cop','cop2'])+'_bust');if(M)endMission(false,b?'Mission failed':'Mission failed');}
function respawn(){const l=P.bust?COPS:HOSP;P.x=l.curb.x;P.y=l.curb.y;P.hp=100;P.dead=0;pts=0;stars=0;cool=0;P.money=Math.floor(P.money*0.9);if(P.bust)P.ammo=0;
 cars=cars.filter(c=>c.kind!=='cop'||c.keep);peds=peds.filter(p=>p.kind!=='cop');say(P.bust?'Released from Everett PD. They kept your ammo.':'Patched up at Providence. Bill: 10%.',4);save();}
function explode(c){c.dead=true;c.fire=0;c.drv=null;c.ai=null;c.col='#222';sfx('boom',c.x,c.y);fx.push({k:'boom',x:c.x,y:c.y,t:0.7});shake=12;
 if(P.car===c){P.car=null;P.hp=0;die(false);}else if(dist(c.x,c.y,P.x,P.y)<85)hurt(P.car?0:60);
 for(const p of peds)if(dist(p.x,p.y,c.x,c.y)<80)killPed(p,false);
 for(const o of cars)if(o!==c&&!o.dead&&dist(o.x,o.y,c.x,c.y)<85)o.hp-=60;
 if(M&&M.car===c)endMission(false,'The car is toast');}
function los(x1,y1,x2,y2){const d=dist(x1,y1,x2,y2),n=Math.ceil(d/12);for(let i=1;i<n;i++){const t=i/n;if(solidTileNoWater(x1+(x2-x1)*t,y1+(y2-y1)*t))return false;}return true;}
function solidTileNoWater(px,py){const t=tileAt(px,py);return t===BLDG||t===HOUSE;}
function shoot(){
 if(P.cd>0)return;
 if(P.ammo<=0){P.cd=0.45;if(!play('s_punch',0.7))sfx('thud');fx.push({k:'punch',x:P.x+Math.cos(P.a)*14,y:P.y+Math.sin(P.a)*14,t:.12});
  for(const p of peds)if(!p.dead&&dist(p.x,p.y,P.x+Math.cos(P.a)*14,P.y+Math.sin(P.a)*14)<18){p.hp-=30;if(p.hp<=0)killPed(p,true);else{if(p.kind==='civ'){p.st='flee';p.t=5;}crime(p.kind==='cop'?3:0.5);}break;}
  return;}
 const ws=WSPEC[P.wp];P.cd=ws.cd;P.ammo--;P.shot=time;sfx('shot',null,null,P.wp);
 let best=null,bd=ws.range;
 for(const p of peds){if(p.dead)continue;const d=dist(p.x,p.y,P.x,P.y);if(d>bd)continue;const da=Math.abs(adiff(Math.atan2(p.y-P.y,p.x-P.x),P.a));if(da<(AIM?0.16:p.kind==='cop'&&stars>0?1.6:0.7)&&los(P.x,P.y,p.x,p.y)){bd=d;best=p;}}
 if(best)P.a=Math.atan2(best.y-P.y,best.x-P.x);
 for(let q=0;q<ws.pel;q++){const an=P.a+(Math.random()-0.5)*2*ws.spr,co=Math.cos(an),si=Math.sin(an);let ex=P.x,ey=P.y,hit=false;
  for(let s=10;s<=ws.range&&!hit;s+=8){ex=P.x+co*s;ey=P.y+si*s;if(solidTileNoWater(ex,ey))break;
   for(const p of peds)if(!p.dead&&dist(p.x,p.y,ex,ey)<9){p.hp-=p.kind==='cop'?ws.dmg*0.57:ws.dmg;if(p.hp<=0)killPed(p,true);else{crime(p.kind==='cop'?3:1);if(p.kind==='civ'){p.st='flee';p.t=6;}}hit=true;break;}
   if(!hit)for(const c of cars)if(dist(c.x,c.y,ex,ey)<c.w*0.8){if(!c.dead)c.hp-=ws.dmg*0.2;if(c.drv==='cop')crime(1);hit=true;break;}}
  fx.push({k:'tr',x1:P.x+co*10,y1:P.y+si*10,x2:ex,y2:ey,t:.07});}
 scare(P.x,P.y,450);if(peds.some(p=>!p.dead&&dist(p.x,p.y,P.x,P.y)<350))crime(0.34);
}
function nextWeapon(){const o=['pistol','smg','shotgun','rifle'].filter(k=>P.own[k]);P.wp=o[(o.indexOf(P.wp)+1)%o.length];say(WSPEC[P.wp].n+' '+P.ammo,1.2);}
function useBtn(){
 if(P.dead||paused)return;
 if(P.car){const c=P.car;if(Math.abs(c.v)>90){say('Slow down to bail out',1.5);return;}
  for(const s of [-1,1]){const a=c.a+s*PI/2,x=c.x+Math.cos(a)*20,y=c.y+Math.sin(a)*20;if(!solidAt(x,y)){P.x=x;P.y=y;c.drv=null;P.car=null;return;}}
  P.x=c.x;P.y=c.y;c.drv=null;P.car=null;return;}
 const c=nearCar();if(!c)return;
 if(c.drv==='ai'||c.drv==='cop'){const p=makePed(P.x,P.y,c.drv==='cop'?'cop':'civ');if(p.kind==='civ'){p.st='flee';p.t=8;bark(p,pick(['Hey, that is my car!','Are you kidding me?!','Somebody stop him!']));}crime(c.drv==='cop'?4:1);}
 else if(c.kind==='cop')crime(2);
 sfx('door');if(c.spot){c.spot.taken=true;c.spot=null;}c.drv='player';c.ai=null;c.park=false;c.sir=false;c.direct=false;P.car=c;
 if(c.kind==='taxi')say('Taxi: fares come to you. Stay in the cab.',3);else if(c.kind==='bus')say('Everett Transit: drive the route for fares.',3);
 if(M&&M.type==='export'&&M.car===c&&M.stage===0){M.stage=1;const l=lm('Port of Everett');M.tx=l.door.x;M.ty=l.door.y;M.text='Get it to the Port of Everett in one piece';crime(1);}
}
function nearCar(){let b=null,bd=48;for(const c of cars){if(c.dead)continue;const d=dist(c.x,c.y,P.x,P.y);if(d<bd){bd=d;b=c;}}return b;}

/* ---------- STORY (fictional characters; see data/story.json) ---------- */
let STORY=[],ST=0,stCd=2;
try{ST=+(localStorage.getItem('everett_st')||0)|0;}catch(e){}
function saveStory(){try{localStorage.setItem('everett_st',String(ST));}catch(e){}}
async function loadStory(){try{const j=await (await fetch('data/story.json'+DV,{cache:'no-store'})).json();CAST=j.cast||{};PRO=j.prologue||[];EPI=j.epilogue||[];try{const sv=String(j.v||1);if(localStorage.getItem('everett_stv')!==sv){ST=0;saveStory();localStorage.setItem('everett_stv',sv);}}catch(e){}STORY=j.chapters.filter(c=>lm(c.at)&&c.steps.every(s=>!s.lm||lm(s.lm)));if(ST>STORY.length)ST=STORY.length;
 STORY.forEach((c,i)=>{const l=lm(c.at);c.gx=l.curb.x;c.gy=l.curb.y;const x=c.gx+30,y=c.gy+10,cs=CAST[c.who]||{};c.ped={who:'st',cw:c.who,ch:cs.ch||c.ch,look:cs.look,x,y,a:Math.atan2(c.gy-y,c.gx-x),kind:'civ',col:'#ccc',said:Infinity,hi:null,story:i};});syncStoryPed();}catch(e){console.warn('story unavailable',e);STORY=[];}}
function syncStoryPed(){for(let i=CONTACTS.length-1;i>=0;i--)if(CONTACTS[i].story!=null){const c=CONTACTS[i];if(c.story!==ST||MODE!=='story'){if(c._m){c._m.parent&&c._m.parent.remove(c._m);const k=dyn.indexOf(c);if(k>=0)dyn.splice(k,1);c._m=null;}CONTACTS.splice(i,1);}}
 if(MODE==='story'&&ST<STORY.length&&!CONTACTS.includes(STORY[ST].ped))CONTACTS.push(STORY[ST].ped);
 if(MODE==='story'&&ST<STORY.length){const a=new Set([STORY[ST].who]);castOf(STORY[ST],a);for(const w of a){const cs=CAST[w];if(cs&&cs.ch&&!cs.remote)want(cs.ch);}}}
function stStep(){const ch=M.ch;if(M.si>=0){const ps=ch.steps[M.si];if(ps&&ps.done)queueRadio(ps.done,ch.id+'_s'+M.si+'d');}M.si++;if(M.si>=ch.steps.length){endMission(true);return;}const s=ch.steps[M.si],l=s.lm&&lm(s.lm);saveCP();M.text=s.text||'';M.time=s.time||0;M.step=s;M.ht=0;M.hide=false;
 if(s.heat){pts=Math.max(pts,TH[s.heat]);cool=0;}if(s.radio)queueRadio(s.radio,ch.id+'_s'+M.si+'r');
 if(s.t==='go'){M.tx=l.door.x;M.ty=l.door.y;}
 else if(s.t==='steal'){let c=makeCar(l.curb.x,l.curb.y,0,s.kind||'civ',VSPEC[s.model]?s.model:null);if(carBlocked(c.x,c.y,0,c)){c.a=PI/2;if(carBlocked(c.x,c.y,c.a,c)){c.x=l.door.x;c.y=l.door.y;}}if(s.kind==='gold'){c.col='#d4af37';c.max=350;c.acc=270;}c.keep=true;c.park=true;M.car=c;M.tx=c.x;M.ty=c.y;}
 else if(s.t==='deliver'){M.dx=l.door.x;M.dy=l.door.y;M.tx=M.dx;M.ty=M.dy;}
 else if(s.t==='heat'){pts=Math.max(pts,TH[s.stars]);cool=0;M.hide=true;M.tx=P.x;M.ty=P.y;}
 else if(s.t==='scene'){M.hide=true;M.tx=P.x;M.ty=P.y;pts=0;cool=0;RQ.length=0;if(NOCUT){stStep();return;}const m=M;let un=null,opt={};
  if(s.set&&SETS[s.set]){const L=lm(s.at||ch.at),w=(s.lines.find(q=>!q.r&&q.w!=='danny')||{}).w;if(P.car){const c=P.car;c.drv=null;c.v=0;c.lat=0;P.car=null;}const sv=[P.x,P.y,P.a];P.x=L.cx-11;P.y=L.cy+2;P.a=0;setShow(s.set,L.cx,L.cy,Math.max(Hat(L.cx-11,L.cy+2),Hat(L.cx+11,L.cy-2)));
   let g=null;if(w){g=mkActor(w,L.cx+11,L.cy-2,PI);CONTACTS.push(g);opt={giver:g};}un=()=>{setHide();P.x=sv[0];P.y=sv[1];P.a=sv[2];if(g){const k=CONTACTS.indexOf(g);if(k>=0)CONTACTS.splice(k,1);}};}
  playScene(s.lines,ch.id+'_s'+M.si+'l',opt,()=>{if(un)un();if(M===m)stStep();});return;}
 if(M.si>0)sfx('pick');}
function saveCP(){if(!M||M.type!=='story')return;const st=M.ch.steps;let si=M.si;while(si>0&&(st[si].t==='deliver'||st[si].t==='heat'))si--;try{localStorage.setItem('everett_cp',JSON.stringify({id:M.ch.id,si,x:P.x,y:P.y,m:P.money}));}catch(e){}}
function loadCP(ch){try{const c=JSON.parse(localStorage.getItem('everett_cp')||'null');return c&&ch&&c.id===ch.id&&c.si>0&&c.si<ch.steps.length?c:null;}catch(e){return null;}}
function resumeCP(ch,cp,move){if(move&&!solidAt(cp.x,cp.y)){P.x=cp.x;P.y=cp.y;}M={type:'story',ch,si:cp.si-1,time:0,reward:ch.reward,text:''};big={t:'CHECKPOINT',c:'#40e0ff',time:2.2};sfx('job');stStep();}
function beginChapter(ch){M={type:'story',ch,si:-1,time:0,reward:ch.reward,text:''};big={t:ch.title,c:'#40e0ff',time:2.2};sfx('job');stStep();}
function setShow(name,cx,cy,hy){const S=SETS[name];if(!S)return null;for(const k in SETS)SETS[k].visible=false;S.position.set(cx,hy+0.6,cy);if(!S.parent)scene.add(S);S.visible=true;for(const m of STATIC)m.visible=false;DN.inset=true;DN.insetK=S.userData.k||1;return S;}
function setHide(){for(const k in SETS)SETS[k].visible=false;if(!(GT&&gReady))for(const m of STATIC)m.visible=true;DN.inset=false;}
function stageOn(ch){if(!(ch.set&&SETS[ch.set])||P.car)return null;const g=ch.ped,l=lm(ch.at),cx=l.cx,cy=l.cy,sv=[P.x,P.y,P.a,g.x,g.y,g.a,g.fa];
 P.x=cx-11;P.y=cy+2;P.a=0;g.x=cx+11;g.y=cy-2;g.a=PI;g.fa=PI;setShow(ch.set,cx,cy,Math.max(Hat(cx-11,cy+2),Hat(cx+11,cy-2)));
 return()=>{setHide();P.x=sv[0];P.y=sv[1];P.a=sv[2];g.x=sv[3];g.y=sv[4];g.a=sv[5];g.fa=sv[6];};}
function startStory(ch){{const cp=loadCP(ch);if(cp){resumeCP(ch,cp,false);return;}}if(NOCUT){beginChapter(ch);say(ch.giver.toUpperCase()+': '+ch.intro[0].t,6);return;}
 const g=ch.ped,un=stageOn(ch),n=STORY.indexOf(ch)+1,b=buildScene(ch.intro,ch.id+'_intro',{giver:g});b.shots.unshift({cam:pickCam(shotWide(P,g,1),shotWide(P,g,-1),shotWide(P,g,0.6),shotWide(P,g,-0.6),shotOTS(P,g,1)),d:2.6,title:'CHAPTER '+n,sub:ch.title});playCut(b.shots,()=>{b.cleanup();if(un)un();beginChapter(ch);});}
function storyStep(dt){const s=M.step,d=dist(P.x,P.y,M.tx,M.ty),slow=!P.car||Math.abs(P.car.v)<60;
 if(M.car&&(M.car.dead||M.car.gone)){endMission(false,'The vehicle was destroyed');return;}
 if(s.t==='go'){if(s.car&&!P.car){M.hint=1;return;}if(d<(P.car?130:75)&&slow)stStep();}
 else if(s.t==='steal'){M.tx=M.car.x;M.ty=M.car.y;if(P.car===M.car){crime(1);stStep();}}
 else if(s.t==='deliver'){if(P.car!==M.car){M.tx=M.car.x;M.ty=M.car.y;}else{M.tx=M.dx;M.ty=M.dy;if(d<130&&slow)stStep();}}
 else if(s.t==='heat'){M.tx=P.x;M.ty=P.y;M.ht+=dt;if(stars===0&&M.ht>2)stStep();}}
function storyDone(m){const ch=m.ch;try{localStorage.removeItem('everett_cp');}catch(e){}RAINON=false;P.money+=ch.reward;ST++;saveStory();save();syncStoryPed();needPack();stCd=14;RQ.length=0;const last=ST>=STORY.length,news=()=>setTimeout(()=>{vo('st_'+ch.id+'_news',null,null,1.3);say('RADIO: '+ch.news,9);},1200);pts=0;cool=0;
 if(NOCUT){big={t:(last?'STORY COMPLETE':'CHAPTER COMPLETE')+'  +$'+ch.reward,c:'#40e0ff',time:4};news();return;}
 const shots=[{cam:SH.orbit(()=>P.x,()=>P.y,58,20,P.a+2.4,0.22,12),d:2.8,title:'MISSION PASSED',sub:'+$'+ch.reward,gold:1,sfx:'win'}],cl=[];
 const nx=ST<STORY.length?STORY[ST]:null,unO=(ch.oset&&nx&&nx.ped&&(ch.outro||[]).some(l=>l.w===nx.ped.cw))?stageOn({set:ch.oset,ped:nx.ped,at:nx.at}):null;
 const o=buildScene(ch.outro||[],ch.id+'_outro',{});shots.push(...o.shots);cl.push(o.cleanup);if(unO)cl.push(unO);
 if(ch.post){const ps=(ch.pset&&SETS[ch.pset])?lm(ch.pat):null,sv=[P.x,P.y,P.a];if(ps){P.x=ps.cx-20;P.y=ps.cy;P.a=0;}const q=buildScene(ch.post,ch.id+'_post',{cutaway:1});if(ps){P.x=sv[0];P.y=sv[1];P.a=sv[2];}
  if(q.shots.length){q.shots[0].card='MEANWHILE';q.shots[0].fade=1;if(ps){const f0=q.shots[0].on;q.shots[0].on=()=>{setShow(ch.pset,ps.cx,ps.cy,Hat(ps.cx-20,ps.cy));if(f0)f0();};cl.push(setHide);}shots.push(...q.shots);cl.push(q.cleanup);}}
 if(last){EPI.forEach((l,i)=>shots.push(flyShot(l,'epi_'+i)));shots.push({cam:SH.orbit(WW/2,WH/2,2600,900,2,0.04,80),d:4,title:'HEWITT HEAT',sub:'THE END'},
  {cam:SH.orbit(WW/2,WH/2,2600,900,2.2,0.04,80),d:10,credits:['A game by Carter Gregg, built with Claude','Map: City of Everett GIS · Google Photorealistic 3D Tiles','Vehicles: Daniel Zhabotinsky (CC BY) · Weapons: TastyTony (CC BY)','Street props, trees and civilians: Sketchfab artists, CC BY (full list in README)','Voices and sound: ElevenLabs stock voices','Every character in the story is fictional']});}
 playCut(shots,()=>{cl.forEach(f=>f());news();if(last)say('Story complete. Downtown and the county are yours.',6);});}
/* ---------- SCENES: actors, shot grammar (wide, over-the-shoulder, close-up, low angle, reaction), radio lines ---------- */
let CAST={},PRO=[],EPI=[],RQ=[],rqT=0;const PK={};
function loadPack(id){if(PK[id]||!AC)return PK[id];return PK[id]=fetch('data/vo_'+id+'.json'+DV).then(r=>r.json()).then(j=>{for(const k in j){const b=atob(j[k]),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);AC.decodeAudioData(u.buffer,buf=>{SND[k]=buf;},()=>{});}}).catch(()=>{delete PK[id];});}
function needPack(){if(MODE!=='story'||!AC)return;if(ST===0)loadPack('c0');if(ST<STORY.length)loadPack(STORY[ST].id);for(let i=0;i<ST-1;i++){const id=STORY[i].id;if(PK[id]){for(const k in SND)if(k.startsWith('v_'+id+'_'))delete SND[k];}}}
function queueRadio(lines,kp){lines.forEach((l,i)=>RQ.push({k:kp+'_'+i,l}));}
function radioStep(dt){rqT-=dt;if(!RQ.length||rqT>0)return;const q=RQ.shift(),b=SND['v_'+q.k],d=b?b.duration:Math.max(2.5,q.l.t.length/14);vo(q.k,null,null,1.1);say(((CAST[q.l.w]||{}).n||'').toUpperCase()+': '+q.l.t,d+0.9);rqT=d+0.55;}
const HDT={michelle:14.1,rpm:16.5,cesium:15,soldier:16.6},_hv=new THREE.Vector3();
function headH(e){const u=e._m&&e._m.userData;if(u&&u.head){u.head.getWorldPosition(_hv);const h=_hv.y-e._m.position.y;if(h>8&&h<24)return h+1.1;}return HDT[e.ch]||16.4;}
function camOK(f){const q=f(0);return !solidAt(q[0],q[2])&&los(q[0],q[2],q[3],q[5]);}
function pickCam(...fs){for(const f of fs)if(f&&camOK(f))return f;return fs[fs.length-1];}
function shotWide(a,b,sg){sg=sg||1;const d=Math.atan2(b.y-a.y,b.x-a.x),L=Math.max(24,dist(a.x,a.y,b.x,b.y));return t=>{const mx=(a.x+b.x)/2,my=(a.y+b.y)/2,sl=-L*0.2+t*1.5,r=(L*1.05+26)*Math.abs(sg),k=Math.sign(sg),gy=Hg(mx,my);return[mx-Math.sin(d)*r*k+Math.cos(d)*sl,gy+15,my+Math.cos(d)*r*k+Math.sin(d)*sl,mx,gy+12.8,my,38];};}
function shotOTS(l,sp,side){const d=Math.atan2(sp.y-l.y,sp.x-l.x);return t=>{const hl=headH(l),hs=headH(sp);return[l.x-Math.cos(d)*9.5-Math.sin(d)*5.6*side,Hg(l.x,l.y)+hl+1.6,l.y-Math.sin(d)*9.5+Math.cos(d)*5.6*side,sp.x,Hg(sp.x,sp.y)+hs-0.9,sp.y,30-Math.min(2,t*0.25)];};}
function shotCU(sp,o,side,low){const d=Math.atan2(o.y-sp.y,o.x-sp.x);return t=>{const b=low?12.5:14.5-Math.min(1.8,t*0.24),gy=Hg(sp.x,sp.y),h=headH(sp);return[sp.x+Math.cos(d)*b-Math.sin(d)*4.6*side,gy+(low?h-8.5:h+0.1),sp.y+Math.sin(d)*b+Math.cos(d)*4.6*side,sp.x,gy+(low?h+0.3:h-0.6),sp.y,low?37:25];};}
function flyShot(l,key){const L=n=>lm(n)||{cx:WW/2,cy:WH/2},po=L('Port of Everett'),li=L('Everett Public Library'),st=L('Everett Station'),ha=L('City Hall'),f=l.fly;
 const cam=f==='port'?SH.orbit(po.cx,po.cy,950,430,2.2,0.05,40):f==='library'?SH.orbit(li.cx,li.cy,330,150,0.4,0.09,30):f==='station'?SH.orbit(st.cx,st.cy,430,190,3.6,0.07,30):f==='hall'?SH.orbit(ha.cx,ha.cy,390,180,1.2,0.08,40):f==='city2'?SH.fly(WW*0.2,WH*0.52,300,WW*0.62,WH*0.5,210,WW*0.9,WH*0.5,60,13):SH.orbit(WW/2,WH/2,2300,820,0.3,0.035,80);
 const cs=CAST[l.w]||{};return{cam,vo:key,who:(cs.n||'')+(l.r||l.fly?' (V.O.)':''),col:cs.c,text:l.t};}
function mkActor(w,x,y,a){const cs=CAST[w]||{};return{x,y,a,fa:a,kind:'civ',ch:cs.ch||'rpm',look:cs.look,col:'#ccc',who:'st',cw:w,said:Infinity,hi:null,actor:1};}
function buildScene(lines,kp,o){o=o||{};const tmp=[],cast={};
 if(P.car&&!o.cutaway){const c=P.car,sx=c.x+Math.cos(c.a+PI/2)*(c.w/2+10),sy=c.y+Math.sin(c.a+PI/2)*(c.w/2+10);c.drv=null;c.v=0;c.lat=0;P.car=null;if(!solidAt(sx,sy)){P.x=sx;P.y=sy;}else{P.x=c.x;P.y=c.y;}P.gy=c.gy;P.gt=c.gt;P.a=c.a;}
 if(!o.cutaway)cast.danny=P;const g=o.giver;if(g){cast[g.cw]=g;const gd=dist(g.x,g.y,P.x,P.y);if(gd>26){const k=24/gd,nx=g.x+(P.x-g.x)*k,ny=g.y+(P.y-g.y)*k;if(!solidAt(nx,ny)&&los(nx,ny,g.x,g.y)){P.x=nx;P.y=ny;}}}
 const pres=[...new Set(lines.filter(l=>!l.r&&l.w!=='danny'&&!(CAST[l.w]||{}).remote).map(l=>l.w))].filter(w=>!cast[w]);
 const fa=g?Math.atan2(g.y-P.y,g.x-P.x):P.a,D0=o.cutaway?44:23,bx=g?g.x:P.x+Math.cos(fa)*D0,by=g?g.y:P.y+Math.sin(fa)*D0;
 pres.forEach((w,i)=>{const k=g?i+1:i,off=(k%2?1:-1)*Math.ceil(k/2)*15+(g||pres.length%2?0:7.5);let x=bx-Math.sin(fa)*off,y=by+Math.cos(fa)*off;if((!DN.inset&&solidAt(x,y))){x=P.x+Math.cos(fa)*18-Math.sin(fa)*off;y=P.y+Math.sin(fa)*18+Math.cos(fa)*off;}if((!DN.inset&&solidAt(x,y))){x=P.x-Math.sin(fa)*(off||12);y=P.y+Math.cos(fa)*(off||12);}
  const ex=CONTACTS.find(q=>q.cw===w&&!q.actor&&dist(q.x,q.y,P.x,P.y)<260);if(ex){cast[w]=ex;ex.fa=Math.atan2(P.y-ex.y,P.x-ex.x);tmp.push(ex);return;}
  const a=mkActor(w,x,y,Math.atan2(P.y-y,P.x-x));a.hid=!!o.cutaway;cast[w]=a;tmp.push(a);CONTACTS.push(a);});
 if(!o.cutaway)P.a=fa;if(g)g.fa=Math.atan2(P.y-g.y,P.x-g.x);
 const all=Object.values(cast),shots=[];let prev=null,n=0;
 lines.forEach((l,i)=>{const cs=CAST[l.w]||{},sp=(l.r||cs.remote)?null:cast[l.w];let other=sp?(prev&&prev!==sp?prev:(sp!==P&&cast.danny?cast.danny:all.find(q=>q!==sp))):null;let cam,cam2=null;
  const W2=(a,b)=>pickCam(shotWide(a,b,1),shotWide(a,b,-1),shotWide(a,b,0.6),shotWide(a,b,-0.6),shotOTS(a,b,1)),C2=(a,b,sd,lw)=>pickCam(shotCU(a,b,sd,lw),shotCU(a,b,-sd,lw),shotCU(a,b,sd*0.2,lw));
  if(!sp){const tg=cast.danny||all[0]||P,fx=tg.x+Math.cos(tg.a||0)*20,fy=tg.y+Math.sin(tg.a||0)*20;cam=C2(tg,{x:fx,y:fy},i%2?1:-1);}
  else if(!other)cam=C2(sp,{x:sp.x+Math.cos(sp.a)*20,y:sp.y+Math.sin(sp.a)*20},1);
  else{const side=sp===P?-1:1;if(n===0)cam=W2(sp===P?sp:other,sp===P?other:sp);else if(cs.low&&n%2===1)cam=C2(sp,other,side,true);else if(n%3===1)cam=pickCam(shotOTS(other,sp,side),shotOTS(other,sp,-side),shotCU(sp,other,side));else cam=C2(sp,other,side);
   if(l.t.length>95)cam2=n%2?C2(other,sp,-side):W2(sp===P?sp:other,sp===P?other:sp);n++;}
  shots.push({cam,cam2,vo:kp+'_'+i,who:(cs.n||'')+((l.r||cs.remote)?' (phone)':''),col:cs.c,text:l.t,on:()=>{P.cutHide=!!o.cutaway;for(const q of all){q.talk=false;q.hid=false;}if(sp){sp.talk=true;for(const q of all){if(q===P)continue;const tg=q===sp?(other||cast.danny||q):sp;if(tg&&tg!==q)q.fa=Math.atan2(tg.y-q.y,tg.x-q.x);}if(cast.danny&&sp!==P)P.a=Math.atan2(sp.y-P.y,sp.x-P.x);else if(sp===P&&other)P.a=Math.atan2(other.y-P.y,other.x-P.x);}}});if(sp)prev=sp;});
 return{shots,cleanup:()=>{P.cutHide=false;for(const q of all)q.talk=false;if(g)g.fa=null;for(const a of tmp){a.fa=null;if(!a.actor)continue;const k=CONTACTS.indexOf(a);if(k>=0)CONTACTS.splice(k,1);}}};}
function playScene(lines,kp,o,onEnd){const b=buildScene(lines,kp,o);playCut(b.shots,()=>{b.cleanup();if(onEnd)onEnd();});}
/* ---------- CINEMATICS: menu camera, cutscenes with letterbox, subtitles, title cards ---------- */
let MODE='story',MENU=true,CUT=null,CAMO=null,skipTap=false,voSrc=null,storyOwn=null;const NOCUT=!!window.EV_NOCUT||new URLSearchParams(location.search).has('nocut');
const fv=v=>typeof v==='function'?v():v,ease=k=>k*k*(3-2*k);
const SH={
 orbit:(cx,cy,r,h,a0,w,lh)=>t=>{const x=fv(cx),y=fv(cy),a=a0+w*t,gy=Hg(x,y);return[x+Math.cos(a)*r,gy+h,y+Math.sin(a)*r,x,gy+(lh||0),y];},
 two:(ax,ay,bx,by)=>t=>{const d=Math.atan2(by-ay,bx-ax),b=30-t*1.6;return[ax-Math.cos(d)*b+Math.sin(d)*11,Hg(ax,ay)+19,ay-Math.sin(d)*b-Math.cos(d)*11,bx,Hg(bx,by)+14,by];},
 face:(bx,by,ax,ay)=>t=>{const d=Math.atan2(ay-by,ax-bx),b=Math.max(11,19-t*0.5);return[bx+Math.cos(d)*b-Math.sin(d)*5,Hg(bx,by)+16,by+Math.sin(d)*b+Math.cos(d)*5,bx,Hg(bx,by)+15.2,by];},
 fly:(x0,y0,h0,x1,y1,h1,lx,ly,lh,dur)=>t=>{const k=ease(clamp(t/dur,0,1)),x=x0+(x1-x0)*k,y=y0+(y1-y0)*k;return[x,Hg(x,y)+h0+(h1-h0)*k,y,lx,Hg(lx,ly)+lh,ly];}};
function stopVo(){try{if(voSrc&&voSrc.stop)voSrc.stop();}catch(e){}voSrc=null;}
function playCut(shots,onEnd){CUT={shots,i:-1,t:0,T:0,onEnd};skipTap=false;document.body.classList.add('cine');nextShot();}
function endCut(){const c=CUT;if(!c)return;stopVo();CUT=null;CAMO=null;document.body.classList.remove('cine');if(c.onEnd)c.onEnd();}
function nextShot(){const c=CUT;c.i++;if(c.i>=c.shots.length){endCut();return;}const s=c.shots[c.i];c.t=0;c.started=false;c.wait=0;s.dd=s.d||Math.max(2.6,(s.text||'').length/13+1.2);if(s.sfx)sfx(s.sfx);if(s.on)s.on();}
function cutStep(dt){const c=CUT;if(!c)return;if(skipTap&&c.T>0.7){skipTap=false;if(c.T-(c.tap||-9)<0.45){endCut();return;}c.tap=c.T;stopVo();nextShot();return;}skipTap=false;const s=c.shots[c.i];c.T+=dt;
 if(s.vo&&!c.started){const b=SND['v_'+s.vo];if(b||c.wait>4||!AC||!sndOn){c.started=true;if(b){stopVo();const r=vo(s.vo,null,null,1.1);voSrc=r&&r.stop?r:null;s.dd=b.duration+0.9;}else VOX=null;}else c.wait+=dt;}
 c.t+=dt;const alt=s.cam2&&c.t>s.dd*0.52,q=(alt?s.cam2:s.cam)(alt?c.t-s.dd*0.52:c.t),hh=Math.sin(c.T*1.7)*0.12,hv=Math.sin(c.T*2.3+1)*0.09,pk=ease(clamp(c.t/Math.max(s.dd,0.5),0,1))*(s.text?0.075:0.02);q[0]+=(q[3]-q[0])*pk;q[1]+=(q[4]-q[1])*pk;q[2]+=(q[5]-q[2])*pk;q[3]+=hh;q[4]+=hv;CAMO=q;if(c.t>=s.dd&&(c.started||!s.vo))nextShot();}
function drawCut(){const c=CUT,s=c.shots[c.i],bh=Math.round(H*0.12);g.fillStyle='#000';g.fillRect(0,0,W,bh);g.fillRect(0,H-bh,W,bh);
 const nx=c.shots[c.i+1],fi=(c.i===0||s.fade)?clamp(1-c.t/0.7,0,1):0,fo=(!nx||nx.fade)?clamp(1-(s.dd-c.t)/0.55,0,1):0,a=Math.max(fi,c.started||!s.vo?fo:0);
 g.textAlign='center';g.textBaseline='middle';
 if(s.title){const k=clamp(c.t/0.5,0,1),fs=Math.min(64,W*0.1);g.font='900 '+fs+'px system-ui,sans-serif';g.lineJoin='round';g.lineWidth=fs*0.16;g.strokeStyle='rgba(0,0,0,.9)';g.globalAlpha=k;g.strokeText(s.title,W/2,H*0.42);g.fillStyle=s.gold?'#ffd23f':'#fff';g.fillText(s.title,W/2,H*0.42);
  if(s.sub){g.font='800 '+fs*0.42+'px system-ui,sans-serif';g.lineWidth=fs*0.09;g.strokeText(s.sub,W/2,H*0.42+fs*0.9);g.fillStyle=s.gold?'#5fd068':'#40e0ff';g.fillText(s.sub,W/2,H*0.42+fs*0.9);}g.globalAlpha=1;}
 if(s.credits){g.font='700 '+Math.min(17,W*0.034)+'px system-ui,sans-serif';s.credits.forEach((l,i)=>{const y=H*0.3+i*Math.min(34,H*0.085),k=clamp((c.t-i*0.6)/0.6,0,1);g.globalAlpha=k;g.lineWidth=4;g.strokeStyle='rgba(0,0,0,.85)';g.strokeText(l,W/2,y);g.fillStyle=i?'#fff':'#ffd23f';g.fillText(l,W/2,y);});g.globalAlpha=1;}
 if(s.text){const fs=Math.min(17,Math.max(13,W*0.022));g.font='600 '+fs+'px system-ui,sans-serif';const full=s.text,n=Math.floor(clamp((c.started||!s.vo?c.t:0)*38,0,full.length)),ws=full.split(' ');let ln='',ls=[];for(const wd of ws){const t=ln?ln+' '+wd:wd;if(g.measureText(t).width>Math.min(W-40,720)&&ln){ls.push(ln);ln=wd;}else ln=t;}ls.push(ln);
  let y=H-bh-12-ls.length*(fs+5),left=n;if(s.who){g.font='800 '+(fs-1)+'px system-ui,sans-serif';g.lineWidth=4;g.strokeStyle='rgba(0,0,0,.9)';g.strokeText(s.who.toUpperCase(),W/2,y-fs*0.3);g.fillStyle=s.col||'#ffd23f';g.fillText(s.who.toUpperCase(),W/2,y-fs*0.3);g.font='600 '+fs+'px system-ui,sans-serif';}
  y+=fs+2;for(const l of ls){const part=l.slice(0,Math.max(0,left));left-=l.length+1;if(part){g.lineWidth=4;g.strokeStyle='rgba(0,0,0,.9)';g.textAlign='left';const x=W/2-g.measureText(l).width/2;g.strokeText(part,x,y);g.fillStyle='#fff';g.fillText(part,x,y);g.textAlign='center';}y+=fs+5;}}
 if(s.card&&c.t<2.2){g.font='800 13px system-ui,sans-serif';g.textAlign='left';g.fillStyle='rgba(255,255,255,'+clamp(2.2-c.t,0,1)+')';g.fillText(s.card,16,bh+18);g.textAlign='center';}
 if(a>0){g.fillStyle='rgba(0,0,0,'+a+')';g.fillRect(0,0,W,H);}
 if(c.T>1.2){g.font='700 11px system-ui,sans-serif';g.fillStyle='rgba(255,255,255,.55)';g.textAlign='right';g.fillText(usedTouch?'TAP TO SKIP':'TAP: NEXT LINE  ·  DOUBLE TAP: SKIP SCENE',W-14,bh/2);}}
function menuCam(){const t=performance.now()/1000,c=WW/2,d=WH/2,goog=GT&&gReady;return SH.orbit(c,d,goog?3000:2100,goog?950:640,0.6,0.03,goog?60:120)(t);}
function updateMenu(){const $=id=>document.getElementById(id),sb=$('start');if(!sb||sb.disabled)return;const done=STORY.length&&ST>=STORY.length;sb.textContent=ST>0&&!done?'CONTINUE STORY':'STORY MODE';const sub=$('stsub');if(sub)sub.textContent=done?'Story complete: all '+STORY.length+' chapters':ST>0?'Chapter '+(ST+1)+' of '+STORY.length+': '+STORY[ST].title:STORY.length?STORY.length+' chapters · starts at the Everett Public Library':'';const ns=$('newstory');if(ns)ns.style.display=ST>0?'':'none';}
function leaveMenu(){document.getElementById('intro').style.display='none';MENU=false;paused=false;CAMO=null;initAudio();if(AC&&AC.resume)AC.resume();document.body.classList.remove('menu');}
function startStoryMode(fresh){if(MODE==='free'&&storyOwn){P.own=storyOwn.own;P.am=storyOwn.am;P.wp='pistol';}MODE='story';if(fresh){try{localStorage.removeItem('everett_cp');}catch(e){}ST=0;saveStory();P.money=0;P.am={pistol:24,smg:0,shotgun:0,rifle:0};P.own={pistol:true};P.wp='pistol';save();}reset();syncStoryPed();stCd=2;leaveMenu();
 needPack();
 PRE=null;RAINON=false;
 {const cp=ST<STORY.length?loadCP(STORY[ST]):null;if(cp){if(ST===0){RAINON=true;TOFF=((22.7*60-540-time)%1440+1440)%1440;}resumeCP(STORY[ST],cp,true);say('Checkpoint restored.',4);return;}}
 if(ST===0&&STORY.length){const ch=STORY[0],j=lm('Snohomish County Courthouse');RAINON=true;TOFF=((22.7*60-540-time)%1440+1440)%1440;
  if(j){P.x=j.curb.x;P.y=j.curb.y;if(solidAt(P.x,P.y)){P.x=j.door.x;P.y=j.door.y;}cam.x=P.x;cam.y=P.y;if(VSPEC.moto&&VSPEC.moto.tpl){const bk=makeCar(P.x+26,P.y+10,PI,'civ','moto');bk.keep=true;bk.park=true;bk.max=330;bk.acc=300;}}
  if(ch.pre){const g=ch.ped;let best=null,bd=1e9;for(const l of DN.lit){const d=dist(l.x,l.z,g.x,g.y);if(d<bd&&!solidAt(l.x+12,l.z+8)){bd=d;best=l;}}if(best&&bd<1400){g.x=best.x+12;g.y=best.z+8;}
   const o=mkActor('olsen',g.x-13,g.y+7,g.a);o.actor=0;CONTACTS.push(o);g.wave=o.wave=true;PRE={g,o,seen:false,done:false};
   if(!PRE_L){PRE_L=new THREE.PointLight(0xffd9a0,0,620,1.7);scene.add(PRE_L);}PRE_L.position.set(g.x-6,Hg(g.x,g.y)+62,g.y+3);PRE_L.intensity=11000;PRE_L.visible=true;}}
 if(ST===0&&STORY.length&&!NOCUT){const O=(r,h,a0,w,lh)=>SH.orbit(()=>P.x,()=>P.y,r,h,a0,w,lh),CS=[O(110,44,P.a+2.3,0.035,12),O(24,15.5,P.a+0.45,0.03,15.2),O(48,8,P.a-0.8,-0.04,13),O(30,17,P.a+0.25,0.02,15.5),O(170,80,P.a+1.3,0.03,10)];
  const sh=PRO.map((l,k)=>({cam:CS[k%CS.length],vo:'pro_'+k,who:'Danny (V.O.)',col:(CAST.danny||{}).c,text:l.t}));sh.push({cam:O(70,24,P.a+PI,0.25,12),d:3.4,title:'HEWITT HEAT',sub:'CHAPTER 1 · '+STORY[0].title});setTimeout(()=>ambOne('door_heavy',0.8),1600);playCut(sh,()=>say('Your bike is at the kerb. Ride west on Hewitt and go home.',8));}
 else if(ST<STORY.length){big={t:'CHAPTER '+(ST+1)+': '+STORY[ST].title,c:'#40e0ff',time:3};say('Follow the blue STORY marker to '+STORY[ST].at+'.',6);}else say('Story complete. Downtown and the county are yours.',5);}
let PRE=null,PRE_L=null;
function preTick(){if(PRE_L&&(!PRE||PRE.done||MODE!=='story'||ST!==0))PRE_L.visible=false;if(!PRE||PRE.done||CUT||M||MODE!=='story'||ST!==0)return;const g=PRE.g,o=PRE.o,ch=STORY[0],d=dist(P.x,P.y,g.x,g.y),mx=(g.x+o.x)/2,my=(g.y+o.y)/2,a=Math.atan2(P.y-my,P.x-mx);
 if(!PRE.seen&&d<620&&d>170){PRE.seen=true;g.fa=o.fa=a;if(NOCUT)return;ambOne('stinger_low',0.7);let fa=a+0.25,fr=128;pick:for(const r of [128,90,60,40])for(const da of [0.25,-0.25,0.6,-0.6,1.1,-1.1,1.8,-1.8,2.6,-2.6]){const x=mx+Math.cos(a+da)*r,y=my+Math.sin(a+da)*r;if(!solidAt(x,y)&&los(x,y,mx,my)){fa=a+da;fr=r;break pick;}}
  const sh2=[{cam:t=>{const r=Math.max(26,fr-t*fr*0.13),gy=Hg(mx,my);return[mx+Math.cos(fa)*r,gy+15+t*0.5,my+Math.sin(fa)*r,mx,gy+15,my];},d:4.6}];{const bx=mx-Math.cos(a)*38+Math.sin(a)*20,by=my-Math.sin(a)*38-Math.cos(a)*20;if(!solidAt(bx,by)&&los(bx,by,P.x,P.y))sh2.push({cam:t=>{const gy=Hg(mx,my);return[bx,gy+20,by,P.x,gy+12,P.y];},d:2.4});}
  playCut(sh2,()=>say('Two men under the street light are flagging you down.',6));return;}
 if(d<150&&(!P.car||Math.abs(P.car.v)<90)){PRE.done=true;g.fa=o.fa=a;const fin=()=>{g.wave=o.wave=false;const k=CONTACTS.indexOf(o);if(k>=0)CONTACTS.splice(k,1);startStory(ch);};if(NOCUT){fin();return;}const b=buildScene(ch.pre,ch.id+'_pre',{giver:g});playCut(b.shots,()=>{b.cleanup();fin();});}}
function startFree(){PRE=null;RAINON=false;if(MODE==='story')storyOwn={own:P.own,am:P.am};MODE='free';reset();syncStoryPed();P.own={pistol:true,smg:true,shotgun:true,rifle:true};P.am={pistol:120,smg:300,shotgun:48,rifle:240};P.wp='pistol';if(P.money<5000)P.money=5000;leaveMenu();big={t:'FREE PLAY',c:'#ffd23f',time:2.5};say('No story. Every weapon unlocked. Jobs, taxis, buses, packages and the county are open.',6);}
function toMenu(){const o=document.getElementById('mapov');if(o)o.style.display='none';if(CUT){const c=CUT;c.onEnd=null;endCut();}M=null;pts=0;stars=0;MENU=true;paused=true;document.getElementById('intro').style.display='flex';document.body.classList.add('menu');updateMenu();}
/* ---------- JOBS & ACTIVITIES ---------- */
function randLM(not){let l,k=0;do{l=pick(DEST);}while((l.n===not||dist(l.door.x,l.door.y,P.x,P.y)<1800)&&k++<40);return l;}
function startMission(gv){
 if(gv.type==='courier'){const d=randLM(gv.lm),dd=dist(P.x,P.y,d.door.x,d.door.y);M={type:'courier',stage:0,tx:d.door.x,ty:d.door.y,time:dd/150+32,reward:r10(120+dd*0.035),text:'Courier: rush this package to '+d.n};}
 else if(gv.type==='race'){const cps=[],pool=nodes.filter(n=>n.sig);let cur={x:P.x,y:P.y},tot=0;for(let i=0;i<7;i++){let best=null,bd=1e9;for(const n of pool){if(cps.includes(n))continue;const d=dist(n.x,n.y,cur.x,cur.y);if(d>1700&&d<bd){bd=d;best=n;}}if(!best)break;tot+=bd;cps.push(best);cur=best;}
  if(!cps.length)return;M={type:'race',stage:0,cps,i:0,tx:cps[0].x,ty:cps[0].y,time:tot/165+28,reward:r10(250+tot*0.03),text:'Street race: checkpoint 1/'+cps.length};}
 else{const d=randLM(gv.lm);let c=makeCar(d.curb.x,d.curb.y,0,'gold');if(carBlocked(c.x,c.y,0,c)){c.a=PI/2;if(carBlocked(c.x,c.y,c.a,c)){c.x=d.door.x;c.y=d.door.y;}}
  c.col='#d4af37';c.max=350;c.acc=270;c.keep=true;c.park=true;M={type:'export',stage:0,car:c,tx:c.x,ty:c.y,time:0,reward:0,text:'Export job: steal the gold coupe near '+d.n};}
 big={t:'JOB STARTED',c:'#ffd23f',time:1.6};sfx('job');const ct=CONTACTS.find(c=>c.gv===gv);if(ct&&M){M.who=ct.who;vo(ct.who+'_start');}if(ct)say(ct.nm.split(' - ')[0].toUpperCase()+': '+(gv.type==='courier'?'Get this there before the clock runs out. No detours.':gv.type==='race'?'Checkpoints are live. Go, go, go.':'Gold coupe. Bring it to my pier without a scratch.'),5);}
function endMission(ok,msg){if(!M)return;RQ.length=0;if(M.car)M.car.keep=false;sfx(ok?'win':'fail');if(M.who)vo(M.who+(ok?'_win':'_fail'));if(M.type==='cab'&&ok)vo(pick(['m1','f1'])+'_fare1');if(ok&&M.type==='story'){storyDone(M);M=null;GV.forEach(gv=>gv.cd=4);autoCd=3.5;return;}if(M.type==='story')stCd=6;if(ok){P.money+=M.reward;big={t:'JOB DONE  +$'+M.reward,c:'#5fd068',time:3};save();}else{big=big&&big.time>1?big:{t:'JOB FAILED',c:'#c0392b',time:2.5};if(msg)say(msg,3);}M=null;GV.forEach(gv=>gv.cd=4);autoCd=3.5;}
function missionStep(dt){
 stCd=Math.max(0,stCd-dt);if(MODE==='story'&&!M&&!P.dead&&stCd<=0&&ST<STORY.length){const ch=STORY[ST];if(dist(P.x,P.y,ch.gx,ch.gy)<50){startStory(ch);stCd=4;}}
 for(const gv of GV){gv.cd=Math.max(0,gv.cd-dt);if(!M&&!(MODE==='story'&&ST<STORY.length&&dist(gv.x,gv.y,STORY[ST].gx,STORY[ST].gy)<160)&&!P.dead&&gv.cd<=0&&dist(P.x,P.y,gv.x,gv.y)<46&&(gv.type!=='race'||P.car)){startMission(gv);gv.cd=4;}}
 autoCd=Math.max(0,autoCd-dt);
 if(!M&&P.car&&!P.dead&&autoCd<=0){
  if(P.car.kind==='taxi'){const c=STOPS.filter(s=>{const d=dist(s.x,s.y,P.x,P.y);return d>700&&d<5000;});if(c.length){const s=pick(c);M={type:'cab',stage:0,tx:s.x,ty:s.y,time:0,reward:0,text:'Taxi: pick up the fare at '+s.n};sfx('pick');}}
  else if(P.car.kind==='bus'){const r=[];let cur={x:P.x,y:P.y};for(let i=0;i<6;i++){let b=null,bd=1e9;for(const s of STOPS){if(r.includes(s))continue;const d=dist(s.x,s.y,cur.x,cur.y);if(d>450&&d<bd){bd=d;b=s;}}if(!b)break;r.push(b);cur=b;}
   if(r.length){M={type:'bus',stage:0,stops:r,i:0,tx:r[0].x,ty:r[0].y,time:0,reward:200,text:'Everett Transit: next stop '+r[0].n+' (1/'+r.length+')'};sfx('pick');}}
  autoCd=2;}
 if(!M)return;
 if((M.type==='cab'&&(!P.car||P.car.kind!=='taxi'))||(M.type==='bus'&&(!P.car||P.car.kind!=='bus'))){M=null;autoCd=5;say('Shift ended',2);return;}
 if(M.time>0){M.time-=dt;if(M.time<=0){endMission(false,'Out of time');return;}}
 if(M.type==='story'){storyStep(dt);return;}
 if(M.type==='export'&&M.stage===0){M.tx=M.car.x;M.ty=M.car.y;return;}
 const d=dist(P.x,P.y,M.tx,M.ty),slow=P.car&&Math.abs(P.car.v)<50;
 if(M.type==='courier'){if(d<70)endMission(true);}
 else if(M.type==='race'){if(d<170&&P.car){M.i++;sfx('pick');if(M.i>=M.cps.length)endMission(true);else{M.tx=M.cps[M.i].x;M.ty=M.cps[M.i].y;M.text='Street race: checkpoint '+(M.i+1)+'/'+M.cps.length;}}}
 else if(M.type==='bus'){if(d<120&&slow){M.i++;P.money+=30;sfx('pick');say('Fares +$30',1.5);if(M.i>=M.stops.length)endMission(true);else{const s=M.stops[M.i];M.tx=s.x;M.ty=s.y;M.text='Everett Transit: next stop '+s.n+' ('+(M.i+1)+'/'+M.stops.length+')';}}}
 else if(M.type==='cab'){if(d<100&&slow){if(M.stage===0){const dst=randLM(''),dd=dist(P.x,P.y,dst.door.x,dst.door.y);M.stage=1;M.tx=dst.door.x;M.ty=dst.door.y;M.time=dd/170+28;M.reward=r10(60+dd*0.045);M.text='Fare wants '+dst.n+' — step on it';sfx('door');vo(pick(['m2','f2'])+'_fare2');}else endMission(true);}}
 else if(M.type==='export'){if(P.car!==M.car){M.tx=M.car.x;M.ty=M.car.y;}else{const l=lm('Port of Everett');M.tx=l.door.x;M.ty=l.door.y;if(d<110&&slow){M.reward=r10(250+Math.max(0,M.car.hp)*4.5);const c=M.car;useBtn();c.gone=true;endMission(true);}}}
}

/* ---------- INPUT ---------- */
const keys={};const joy={on:false,id:-1,ox:0,oy:0,x:0,y:0};let fireHeld=false,usedTouch=false;
let pitch=0.2,lookT=9,lookDX=0,lookDY=0,mouseFire=false,mouseAim=false,mouseDown=false,runHeld=false,jumpTap=false,AIM=false,lookBack=false,padOn=false,padPrev=[];
const lookTouch={id:-1,x:0,y:0};let noLock=false;if(typeof document!=='undefined')document.addEventListener('pointerlockerror',()=>{noLock=true;});
// One input frame from keyboard + mouse, touch and gamepad (standard mapping, GTA-style layout)
function readInput(dt){const I={mx:0,my:0,lx:0,ly:0,sprint:false,jump:false,fire:false,aim:false,use:false,wpn:false,map:false,hb:false,thr:0,back:false,analog:false};
 if(CUT){jumpTap=false;lookDX=lookDY=0;try{const gp=navigator.getGamepads&&[...navigator.getGamepads()].find(q=>q&&q.connected);if(gp&&gp.buttons[0]&&gp.buttons[0].pressed&&CUT.t>0.7)skipTap=true;}catch(e){}return I;}
 if(keys.KeyW||keys.ArrowUp)I.my-=1;if(keys.KeyS||keys.ArrowDown)I.my+=1;if(keys.KeyA||keys.ArrowLeft)I.mx-=1;if(keys.KeyD||keys.ArrowRight)I.mx+=1;
 I.thr=-I.my;I.sprint=!!(keys.ShiftLeft||keys.ShiftRight)||runHeld;I.fire=fireHeld||mouseFire||!!keys.ControlLeft||!!keys.KeyJ;I.aim=mouseAim;I.hb=!!keys.Space||fireHeld;I.back=!!keys.KeyC;I.jump=jumpTap;jumpTap=false;
 if(joy.on){I.mx=joy.x;I.my=joy.y;I.thr=Math.abs(joy.y)>0.18?clamp(-joy.y*1.3,-1,1):0;I.analog=true;if(Math.hypot(joy.x,joy.y)>0.97)I.sprint=I.sprint||runHeld;}
 I.lx=lookDX*0.0026;I.ly=lookDY*0.0022;lookDX=lookDY=0;
 const gp=(navigator.getGamepads?[...navigator.getGamepads()]:[]).find(p=>p&&p.connected&&p.buttons.length>=10);
 if(gp){if(!padOn){padOn=true;say('Controller connected',2.5);}const dz=v=>Math.abs(v)<0.16?0:(v-Math.sign(v)*0.16)/0.84,b=i=>gp.buttons[i]?gp.buttons[i].value:0,hit=i=>b(i)>0.5&&!(padPrev[i]>0.5);
  const ax=dz(gp.axes[0]||0),ay=dz(gp.axes[1]||0),rx=dz(gp.axes[2]||0),ry=dz(gp.axes[3]||0);
  if(ax||ay){I.mx=ax;I.my=ay;I.analog=true;}I.lx+=rx*2.8*dt*(b(6)>0.3?0.55:1);I.ly+=ry*1.7*dt;
  if(b(7)>0.05||b(6)>0.05){I.thr=b(7)-b(6);}                      // RT gas, LT brake / reverse
  I.fire=I.fire||b(7)>0.4;I.aim=I.aim||b(6)>0.3;I.sprint=I.sprint||b(0)>0.5||b(10)>0.5;I.hb=I.hb||b(0)>0.5||b(5)>0.5;I.back=I.back||b(11)>0.5;
  if(hit(2))I.jump=true;if(hit(3))I.use=true;if(hit(5)||hit(4)||hit(15)||hit(14))I.wpn=true;if(hit(9)||hit(8))I.map=true;
  if(hit(0)||hit(9)){const st=document.getElementById('start'),it=document.getElementById('intro');if(it&&it.style.display!=='none'&&!st.disabled)st.click();}
  padPrev=gp.buttons.map(q=>q.value);}
 else if(padOn){padOn=false;}
 return I;}
let W=800,H=600,DPR=1,shake=0;const cam={x:0,y:0,z:1};

/* ---------- UPDATE ---------- */
function update(dt){
 time+=dt;
 if(big){big.time-=dt;if(big.time<=0)big=null;}
 if(toast){toast.time-=dt;if(toast.time<=0)toast=null;}
 rainT-=dt;if(rainT<=0){rain=rain?0:1;rainT=rain?rand(40,80):rand(50,110);}
 P.cd=Math.max(0,P.cd-dt);P.flash=Math.max(0,P.flash-dt);shake=Math.max(0,shake-dt*30);
 shopCd=Math.max(0,shopCd-dt);pawnCd=Math.max(0,pawnCd-dt);hospCd=Math.max(0,hospCd-dt);
 if(P.dead){P.dead-=dt;if(P.dead<=0){P.dead=0;respawn();}}
 // player input
 const IN=readInput(dt);
 if(IN.map)toggleMap();
 if(IN.lx||IN.ly){yaw+=IN.lx;pitch=clamp(pitch+IN.ly,-0.3,1.0);lookT=0;}else lookT+=dt;
 lookBack=IN.back;
 if(!P.dead){
  if(IN.use)useBtn();if(IN.wpn&&!P.car)nextWeapon();
  if(P.car){const c=P.car;let thr=IN.thr;AIM=false;
   c.st=(c.st||0)+(clamp(IN.mx*(IN.analog?1.15:1),-1,1)-(c.st||0))*Math.min(1,dt*(IN.analog?9:5.5));   // steering eases in instead of snapping
   if(c.dead||c.hp<=0)thr=0;
   carStep(c,thr,c.st,IN.hb,dt);P.x=c.x;P.y=c.y;P.a=c.a;P.z=0;P.vz=0;
  }else{
   AIM=IN.aim&&P.ammo>0;const m=Math.min(1,Math.hypot(IN.mx,IN.my));P.mov=m>0.15;
   const run=IN.sprint&&P.mov&&P.stam>0.02&&!AIM;P.stam=clamp((P.stam==null?1:P.stam)+(run?-dt/7:dt/4.5),0,1);
   let tvx=0,tvy=0;if(P.mov){const sp=(AIM?26:run?84:46)*m,f=-IN.my,r=IN.mx,l=Math.hypot(f,r)||1,wx=(Math.cos(yaw)*f-Math.sin(yaw)*r)/l,wy=(Math.sin(yaw)*f+Math.cos(yaw)*r)/l;tvx=wx*sp;tvy=wy*sp;}
   const k=Math.min(1,dt*(P.z>0?2.5:11));P.vx=(P.vx||0)+(tvx-(P.vx||0))*k;P.vy=(P.vy||0)+(tvy-(P.vy||0))*k;
   if(Math.abs(P.vx)+Math.abs(P.vy)>0.5)moveEnt(P,P.vx*dt,P.vy*dt,5);
   if(AIM)P.a+=adiff(yaw,P.a)*Math.min(1,dt*16);else if(P.mov)P.a+=adiff(Math.atan2(tvy,tvx),P.a)*Math.min(1,dt*12);
   if(IN.jump&&!(P.z>0)){P.vz=60;P.z=0.01;sfx('thud');}
   if(P.z>0){P.z+=P.vz*dt;P.vz-=190*dt;if(P.z<=0){P.z=0;P.vz=0;}}
   if(IN.fire){if(AIM)P.a=yaw;shoot();}
  }
 }
 // cars
 const vr=viewR();
 for(const c of cars){
  const dp=dist(c.x,c.y,P.x,P.y);
  if(c!==P.car&&!c.keep&&(c.park?dp>3400:farOff(c.x,c.y,4600,2400))){c.gone=true;continue;}
  if(c.hp<=0&&!c.dead){c.fire+=dt;if(c.drv==='ai'||c.drv==='cop'){const p=makePed(c.x,c.y,c.drv==='cop'?'cop':'civ');if(p.kind==='civ'){p.st='flee';p.t=8;}c.drv=null;c.ai=null;}if(c.fire>3.5)explode(c);}
  if(c.drv==='ai'||c.drv==='cop'){if(c.hp>0)aiCar(c,dt);else carStep(c,0,0,true,dt);}
  else if(c!==P.car&&Math.abs(c.v)>1)carStep(c,0,0,!c.dead&&Math.abs(c.v)<40,dt);
  // run over
  if(Math.abs(c.v)>55){const s=Math.sign(c.v),fx_=c.x+Math.cos(c.a)*s*(c.l/2-6),fy_=c.y+Math.sin(c.a)*s*(c.l/2-6);
   for(const p of peds)if(!p.dead&&dist(p.x,p.y,fx_,fy_)<13){if(c.drv==='player'||Math.abs(c.v)>90)killPed(p,c.drv==='player');}
   if(!P.car&&!P.dead&&c.drv!=='player'&&Math.abs(c.v)>75&&dist(P.x,P.y,fx_,fy_)<13){hurt(Math.abs(c.v)*0.14);c.v*=0.5;}}
 }
 // car-car
 for(let i=0;i<cars.length;i++){const a=cars[i];if(a.gone)continue;for(let j=i+1;j<cars.length;j++){const b=cars[j];if(b.gone)continue;
  if(Math.abs(a.x-b.x)>130||Math.abs(a.y-b.y)>130)continue;if(Math.abs(a.v)<2&&Math.abs(b.v)<2)continue;
  const ao=a.l/2-a.w/2,bo=b.l/2-b.w/2,rr2=(a.w+b.w)/2,ac=Math.cos(a.a)*ao,as=Math.sin(a.a)*ao,bc=Math.cos(b.a)*bo,bs=Math.sin(b.a)*bo;let hit=false;
  for(const sa of [-1,0,1]){for(const sb of [-1,0,1]){const dx=(a.x+ac*sa)-(b.x+bc*sb),dy=(a.y+as*sa)-(b.y+bs*sb),d=Math.hypot(dx,dy)||0.01;
   if(d<rr2){const o=(rr2-d)/2,nx=dx/d,ny=dy/d;
    if(!carBlocked(a.x+nx*o,a.y+ny*o,a.a,a)){a.x+=nx*o;a.y+=ny*o;}if(!carBlocked(b.x-nx*o,b.y-ny*o,b.a,b)){b.x-=nx*o;b.y-=ny*o;}hit=true;}}}
  if(hit){const rel=Math.hypot(Math.cos(a.a)*a.v-Math.cos(b.a)*b.v,Math.sin(a.a)*a.v-Math.sin(b.a)*b.v);
   if(rel>70){sfx('crash',a.x,a.y);const dm=rel*0.045;a.hp-=dm;b.hp-=dm;const av=a.v;a.v=a.v*0.45+b.v*0.2*Math.cos(a.a-b.a);b.v=b.v*0.45+av*0.2*Math.cos(a.a-b.a);
    if(a===P.car||b===P.car){shake=Math.min(10,rel*0.04);const o=a===P.car?b:a;if(o.drv==='cop'&&Math.abs(P.car.v)>60)crime(1);}}
   else{a.v*=0.9;b.v*=0.9;}}
 }}
 for(const c of cars)if(c.gone&&c.spot){c.spot.on=false;c.spot=null;}
 cars=cars.filter(c=>!c.gone);
 // peds
 for(const p of peds){
  if(p.dead){p.t+=dt;continue;}
  const dpp=dist(p.x,p.y,P.x,P.y);
  if(p.kind==='cop'&&stars>0&&!P.dead){p.a=Math.atan2(P.y-p.y,P.x-p.x);
   if(dpp>(stars>=2?100:8))moveEnt(p,Math.cos(p.a)*58*dt,Math.sin(p.a)*58*dt,5);
   p.cd-=dt;
   if(stars>=2&&dpp<480&&p.cd<=0&&los(p.x,p.y,P.x,P.y)){p.cd=rand(0.8,1.4);sfx('shot',p.x,p.y,'pistol');fx.push({k:'tr',x1:p.x,y1:p.y,x2:P.x+rand(-8,8),y2:P.y+rand(-8,8),t:.08});if(Math.random()<0.5){if(P.car)P.car.hp-=6;else hurt(8);}}
   if(Math.random()<dt*0.25)bark(p,pick(['Everett PD! Stop!','Hands where I can see them!','Suspect on foot!']));
   if(stars===1&&dpp<18&&(!P.car||Math.abs(P.car.v)<25))die(true);
   continue;}
  if(p.st==='wait'){p.t-=dt;if(p.t<=0){p.st='walk';p.t=0;}if(dpp<13&&!P.car&&bumpCd<=0){bumpCd=2.5;bark(p,pick(['Bus is late again.','You waiting on the 7?','Nice day for it.']));}continue;}
  if(dpp<12&&!P.car&&p.kind==='civ'&&p.st==='walk'&&bumpCd<=0){bumpCd=2.5;bark(p,pick(['Watch it!','Hey!','Excuse you.','Easy, man.']));}
  if(p.st==='flee'){p.t-=dt;if(p.t<=0){p.st='walk';p.t=0;}p.a=Math.atan2(p.y-P.y,p.x-P.x)+p.j;if(!moveEnt(p,Math.cos(p.a)*52*dt,Math.sin(p.a)*52*dt,5))p.j=rand(-1.6,1.6);continue;}
  p.t-=dt;const okT=t=>t===WALK||t===PARK||t===CONC;
  if(p.t<=0||!okT(tileAt(p.x+Math.cos(p.a)*14,p.y+Math.sin(p.a)*14))){
   let o=[0,PI/2,PI,-PI/2].filter(a=>okT(tileAt(p.x+Math.cos(a)*20,p.y+Math.sin(a)*20)));const fwd=o.filter(a=>Math.abs(adiff(a,p.a+PI))>0.2);if(fwd.length)o=fwd;
   p.a=o.length?pick(o):rand(-PI,PI);p.t=rand(3,10);}
  moveEnt(p,Math.cos(p.a)*14*dt,Math.sin(p.a)*14*dt,5);
 }
 peds=peds.filter(p=>!(p.dead&&p.t>25)&&!farOff(p.x,p.y,3000,1500));
 // spawning
 let nt=0,np=0;for(const c of cars)if(c.drv==='ai')nt++;for(const p of peds)if(!p.dead&&p.kind==='civ')np++;
 if(nt<(LOW?16:24)){const r=Math.random();spawnTraffic(r<0.1?'taxi':r<0.19?'truck':r<0.25?'bus':r<0.28?'amb':'civ');}
 if(np<(LOW?16:30))spawnPed();
 // wanted
 let ns=0;while(ns<5&&pts>=TH[ns+1])ns++;stars=ns;dispCd-=dt;scrCd-=dt;if(ns>pStars&&dispCd<=0){vo('disp_s'+ns,null,null,1.2);dispCd=6;}pStars=ns;
 if(NAV&&!P.dead&&P.y<NAV.cy+2600&&P.x<NAV.cx+2600&&tileAt(P.x,P.y)===CONC&&dist(P.x,P.y,NAV.cx,NAV.cy)<3000){if(pts<9){pts=9;say('RESTRICTED: Naval Station Everett',3);}cool=0;}
 if(stars>0){
  let near=false;for(const c of cars)if(c.drv==='cop'&&dist(c.x,c.y,P.x,P.y)<950){near=true;break;}
  if(!near)for(const p of peds)if(p.kind==='cop'&&!p.dead&&dist(p.x,p.y,P.x,P.y)<700){near=true;break;}
  if(near)cool=0;else{cool+=dt;if(cool>9+stars*2){pts=TH[stars-1];cool=0;if(stars===1){say('You lost them',2);vo('disp_lost',null,null,1.2);}}}
  copT-=dt;let n=0;for(const c of cars)if(c.drv==='cop')n++;for(const p of peds)if(p.kind==='cop'&&!p.dead)n+=0.5;
  if(n<stars&&copT<=0){spawnTraffic('cop');copT=2.5;}
 }
 // pickups & shops
 for(const k of picks){k.t-=dt;if(!P.dead&&dist(k.x,k.y,P.x,P.y)<(P.car?26:18)){if(k.k==='cash'){P.money+=k.amt;if(!play('s_cash',0.5))sfx('pick');}else{P.ammo+=k.amt;sfx('pick');}k.t=0;}}
 picks=picks.filter(k=>k.t>0);for(const s of stains)s.t-=dt;stains=stains.filter(s=>s.t>0);
 for(const f of fx)f.t-=dt;fx=fx.filter(f=>f.t>0);
 if(!P.dead){
  if(P.car&&shopCd<=0&&dist(P.x,P.y,SHOP.door.x,SHOP.door.y)<60&&Math.abs(P.car.v)<50){shopCd=5;if(P.money>=150){P.money-=150;P.car.hp=P.car.mhp;P.car.fire=0;P.car.col=pick(CARCOL);pts=0;cool=0;peds.forEach(p=>{if(p.kind==='cop')p.st='walk';});say('Resprayed & repaired — heat cleared (-$150)',3);save();}else say('Body shop: $150',2);}
  if(pawnCd<=0&&!P.car&&dist(P.x,P.y,PAWN.curb.x,PAWN.curb.y)<46){pawnCd=3;if(!P.own.smg&&P.money>=400){P.money-=400;P.own.smg=true;P.am.smg+=120;P.wp='smg';say('Bought SMG +120 (-$400)',3);}else if(!P.own.shotgun&&P.money>=300){P.money-=300;P.own.shotgun=true;P.am.shotgun+=16;P.wp='shotgun';say('Bought shotgun +16 (-$300)',3);}else if(P.own.smg&&P.own.shotgun&&!P.own.rifle&&P.money>=900){P.money-=900;P.own.rifle=true;P.am.rifle+=90;P.wp='rifle';say('Bought AK-47 +90 (-$900)',3);}else if(P.money>=60){P.money-=60;P.ammo+=P.wp==='smg'?90:P.wp==='rifle'?60:P.wp==='shotgun'?12:24;say(WSPEC[P.wp].n+' ammo (-$60)',2);}else say('Guns & Ammo: ammo $60, shotgun $300, SMG $400, AK $900',3);sfx('pick');}
  if(hospCd<=0&&!P.car&&P.hp<100&&dist(P.x,P.y,HOSP.curb.x,HOSP.curb.y)<42){hospCd=5;if(P.money>=40){P.money-=40;P.hp=100;say('Patched up (-$40)',2);}else say('Treatment: $40',2);}
 }
 if(!CUT){missionStep(dt);radioStep(dt);}else{cutStep(dt);if(P.car){P.car.v*=Math.max(0,1-dt*4);}}bumpCd=Math.max(0,bumpCd-dt);for(const b of barks)b.time-=dt;barks=barks.filter(b=>b.time>0&&!b.p.dead);
 for(const c of CONTACTS){const d=dist(c.x,c.y,P.x,P.y);if(d<170&&time-c.said>25&&!M){c.said=time;bark(c,c.hi);}c.a=c.fa!=null?c.fa:d<400?Math.atan2(P.y-c.y,P.x-c.x):c.a;}
 // hidden packages
 if(!P.dead&&!P.car)for(const p of PKG)if(!pkgGot[p.i]&&Math.abs(p.x-P.x)<24&&Math.abs(p.y-P.y)<24){pkgGot[p.i]=1;const n=Object.keys(pkgGot).length;P.money+=100;sfx('win');big={t:'PACKAGE '+n+'/'+PKG.length,c:'#40e0ff',time:2};if(n===PKG.length){P.money+=5000;say('All packages found: +$5000',5);}try{localStorage.setItem('everett_pk',JSON.stringify(pkgGot));}catch(e){}save();}
 // street name + curbside parked cars near the player
 strT-=dt;if(strT<=0){strT=0.4;STREET=OOB(P.x,P.y)?nearPlace():streetAt(P.x,P.y)||(tileAt(P.x,P.y)===PARK?'Park':tileAt(P.x,P.y)===CONC?'Waterfront':'Everett');}
 spotT-=dt;if(spotT<=0){spotT=0.5;streamSpots(false);}
 // camera: free look from the right stick / mouse / right-side drag; it drifts back behind you after a moment
 if(P.car&&lookT>0.35){const c=P.car;yaw+=adiff(c.a+(c.v<-25?PI:0)+(c.st||0)*0.16,yaw)*Math.min(1,dt*(3.0+Math.abs(c.v)/80));}
 if(lookT>1.4){if(P.car){}else if(P.mov&&!P.dead&&!AIM){const d=adiff(P.a,yaw);if(Math.abs(d)<2.4)yaw+=d*Math.min(1,dt*1.2);}
  pitch+=((P.car?0.2:0.13)-pitch)*Math.min(1,dt*1.5);}
 cam.x=P.x;cam.y=P.y;
}

function streamSpots(first){let act=0;for(const c of cars)if(c.park)act++;const cap=LOW?22:48,cy=Math.cos(yaw),sy=Math.sin(yaw);
 for(const s of SPOTS){if(act>=cap)break;if(s.on||s.taken)continue;const dx=s.x-P.x,dy=s.y-P.y,d=Math.abs(dx)+Math.abs(dy);if(d>2600||d<250)continue;if(!first&&d<1500&&dx*cy+dy*sy>-200)continue;
  const c=makeCar(s.x,s.y,s.a,'civ');if(c.model==='stepvan'||c.model==='foodtruck'||carBlocked(c.x,c.y,c.a,c)){cars.pop();s.taken=true;continue;}c.park=true;c.spot=s;s.on=true;act++;}}
/* ---------- AUDIO ---------- */
let AC=null,MG,engO,engO2,engG,sirO,sirG,skG,NB,sndOn=true;
function initAudio(){if(AC)return;try{AC=new (window.AudioContext||window.webkitAudioContext)();}catch(e){AC=null;return;}
 MG=AC.createGain();MG.gain.value=0.6;{const lim=AC.createDynamicsCompressor();lim.threshold.value=-9;lim.knee.value=10;lim.ratio.value=8;lim.attack.value=0.004;lim.release.value=0.22;MG.connect(lim);lim.connect(AC.destination);}
 NB=AC.createBuffer(1,AC.sampleRate,AC.sampleRate);const d=NB.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;
 const lp=AC.createBiquadFilter();lp.type='lowpass';lp.frequency.value=520;engG=AC.createGain();engG.gain.value=0;lp.connect(engG);engG.connect(MG);
 engO=AC.createOscillator();engO.type='sawtooth';engO.frequency.value=50;engO.connect(lp);engO.start();engO2=AC.createOscillator();engO2.type='square';engO2.frequency.value=25;engO2.connect(lp);engO2.start();
 sirO=AC.createOscillator();sirO.type='triangle';sirG=AC.createGain();sirG.gain.value=0;sirO.connect(sirG);sirG.connect(MG);sirO.start();loadSnd();
 const sk=AC.createBufferSource();sk.buffer=NB;sk.loop=true;const bp=AC.createBiquadFilter();bp.type='bandpass';bp.frequency.value=1900;bp.Q.value=3;skG=AC.createGain();skG.gain.value=0;sk.connect(bp);bp.connect(skG);skG.connect(MG);sk.start();}
const SND={},LP={};let sndReq=false,scrCd=0,dispCd=0,pStars=0;
async function loadSnd(){if(sndReq)return;sndReq=true;try{const j=await (await fetch('data/snd.json')).json();for(const k in j){const b=atob(j[k]),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);AC.decodeAudioData(u.buffer,buf=>{SND[k]=buf;},()=>{});}}catch(e){console.warn('sound pack unavailable',e);}}
function play(k,vol,x,y,rate){const b=SND[k];if(!b||!AC||!sndOn)return false;let g=vol==null?1:vol;if(x!=null){const d=dist(x,y,P.x,P.y);if(d>900)return true;g*=1-d/900;}try{const s=AC.createBufferSource();s.buffer=b;if(rate)s.playbackRate.value=rate;const gn=AC.createGain();gn.gain.value=g;s.connect(gn);gn.connect(MG);s.start();return s;}catch(e){}return true;}
let VOX=null;const ENV=new Map();
function envOf(b){let e=ENV.get(b);if(!e){const d=b.getChannelData(0),n=Math.floor(b.sampleRate/30),m=Math.ceil(d.length/n);e=new Float32Array(m);let mx=1e-4;for(let i=0;i<m;i++){let q=0;const a=i*n,z=Math.min(d.length,a+n);for(let j=a;j<z;j++)q+=d[j]*d[j];e[i]=Math.sqrt(q/(z-a||1));if(e[i]>mx)mx=e[i];}const vc=Array.from(e).filter(v=>v>0.02*mx).sort((p,q)=>p-q),rf=vc.length?vc[Math.floor(vc.length*0.8)]:mx;for(let i=0;i<m;i++)e[i]=Math.pow(clamp((e[i]/rf-0.08)/0.92,0,1),0.7);ENV.set(b,e);}return e;}
function voxLevel(){if(!VOX||!AC)return -1;const t=(AC.currentTime-VOX.t)*30,e=VOX.e;if(t<0||t>=e.length-1)return 0;const i=t|0;return e[i]+(e[i+1]-e[i])*(t-i);}
function vo(k,x,y,vol){const b=SND['v_'+k];VOX=b&&AC&&b.getChannelData?{t:AC.currentTime,e:envOf(b)}:null;return play('v_'+k,vol==null?1.15:vol,x,y);}
function loopG(k){if(LP[k])return LP[k];const b=SND[k];if(!b)return null;const s=AC.createBufferSource();s.buffer=b;s.loop=true;s.loopStart=0.04;s.loopEnd=b.duration-0.07;const g=AC.createGain();g.gain.value=0;s.connect(g);g.connect(MG);s.start();return LP[k]=g;}
const BK={'He has a gun!':'gun','Run!':'run','Call 911!':'911','Get down!':'down','Hey, that is my car!':'mycar','Are you kidding me?!':'kid','Somebody stop him!':'stophim','Bus is late again.':'bus','You waiting on the 7?':'seven','Nice day for it.':'nice','Watch it!':'watch','Hey!':'hey','Excuse you.':'excuse','Easy, man.':'easy','Everett PD! Stop!':'stop','Hands where I can see them!':'hands','Suspect on foot!':'foot'};
function barkVo(p,t){if(p.who){if(t===p.hi)vo(p.who+'_hi',p.x,p.y,1.6);return;}const k=BK[t];if(!k)return;const w=p.kind==='cop'?(p.vw||(p.vw=Math.random()<0.5?'cop':'cop2')):(p.vw||(p.vw=(p.ch==='michelle'||p.ch==='woman'||/ped_w|marge|dee/.test(p.ch))?pick(['f1','f2']):pick(['m1','m2'])));vo(w+'_'+k,p.x,p.y,1.5);}
function noise(dur,freq,vol,type){const s=AC.createBufferSource();s.buffer=NB;const f=AC.createBiquadFilter();f.type=type||'lowpass';f.frequency.value=freq;const gn=AC.createGain(),t=AC.currentTime;gn.gain.setValueAtTime(vol,t);gn.gain.exponentialRampToValueAtTime(0.001,t+dur);s.connect(f);f.connect(gn);gn.connect(MG);s.start(t,Math.random()*0.5,dur+0.05);}
function tone(f1,f2,dur,vol,type,delay){const o=AC.createOscillator(),gn=AC.createGain(),t=AC.currentTime+(delay||0);o.type=type||'sine';o.frequency.setValueAtTime(f1,t);o.frequency.exponentialRampToValueAtTime(f2,t+dur);gn.gain.setValueAtTime(vol,t);gn.gain.exponentialRampToValueAtTime(0.001,t+dur);o.connect(gn);gn.connect(MG);o.start(t);o.stop(t+dur+0.05);}
function sfx(n,x,y,w){if(!AC||!sndOn)return;const sm=n==='shot'?'s_'+(w||'pistol'):n==='crash'?'s_crash':n==='boom'?'s_boom':n==='door'?'s_door':null;if(sm&&SND[sm]){play(sm,n==='shot'?0.75:n==='boom'?1.3:0.9,x,y,0.94+Math.random()*0.12);return;}
 let k=1;if(x!=null){const d=dist(x,y,P.x,P.y);if(d>800)return;k=1-d/800;}
 try{if(n==='shot'){noise(0.16,2600,0.7*k);tone(160,45,0.1,0.5*k,'square');}
 else if(n==='crash'){noise(0.28,700,0.8*k);tone(90,40,0.2,0.4*k,'sawtooth');}
 else if(n==='boom'){noise(1.1,260,1.2*k);tone(70,25,0.8,0.8*k,'sine');}
 else if(n==='thud'){tone(120,50,0.12,0.5*k,'sine');noise(0.08,900,0.3*k);}
 else if(n==='pick'){tone(880,1320,0.09,0.25,'square');tone(1320,1760,0.1,0.2,'square',0.08);}
 else if(n==='job'){tone(330,330,0.12,0.25,'square');tone(440,440,0.12,0.25,'square',0.13);tone(660,660,0.25,0.25,'square',0.26);}
 else if(n==='win'){[392,494,587,784].forEach((f,i)=>tone(f,f,0.22,0.25,'square',i*0.14));}
 else if(n==='fail'){tone(300,120,0.7,0.3,'sawtooth');}
 else if(n==='door'){tone(200,90,0.07,0.4,'square');noise(0.06,1200,0.3);}
 }catch(e){}}
function audioStep(){if(!AC)return;const t=AC.currentTime,c=P.car,on=sndOn&&!paused&&!MENU;
 if(c&&!c.dead&&on){const v=Math.abs(c.v),gear=(v%95)/95;engO.frequency.setTargetAtTime(48+v*0.22+gear*38,t,0.05);engO2.frequency.setTargetAtTime(24+v*0.11+gear*19,t,0.05);engG.gain.setTargetAtTime(0.13,t,0.1);{const sk=clamp(((c.slip||0)-28)/160,0,0.22),lg=loopG('s_skid');if(lg){lg.gain.setTargetAtTime(sk*2.6,t,0.05);skG.gain.setTargetAtTime(0,t,0.05);}else skG.gain.setTargetAtTime(sk,t,0.05);}}
 else{engG.gain.setTargetAtTime(0,t,0.1);skG.gain.setTargetAtTime(0,t,0.05);if(LP.s_skid)LP.s_skid.gain.setTargetAtTime(0,t,0.05);}
 {const cg=loopG('s_city');if(cg)cg.gain.setTargetAtTime(on&&!MENU?(c?0.16:0.3):0,t,0.4);const mg=loopG('s_menu');if(mg)mg.gain.setTargetAtTime(sndOn&&MENU?0.55:0,t,0.5);}
 let sd=1e9;if(on)for(const o of cars)if(o.sir&&!o.dead){const d=dist(o.x,o.y,P.x,P.y);if(d<sd)sd=d;}
 {const sv=sd<1000?(1-sd/1000):0,lg=loopG('s_siren');if(lg){lg.gain.setTargetAtTime(sv*0.5,t,0.15);sirG.gain.setTargetAtTime(0,t,0.1);}else sirG.gain.setTargetAtTime(0.11*sv,t,0.15);}sirO.frequency.setTargetAtTime(880+330*Math.sin(time*4.2),t,0.03);}

/* ---------- 3D RENDER: Breachpoint stack + real Everett geometry ---------- */
let cv,hc,g,mm,bigmap,ren,scene,cam3,dynG,sun,yaw=PI,camD=60,frameId=0,SOLD=null,lastT=0;const dyn=[],MAT={},LBL=[];
const LOW=typeof matchMedia!=='undefined'&&matchMedia('(pointer:coarse)').matches;
const HWALL=['#e6dccb','#c3d0d6','#d9cfb2','#b5c4aa','#d6bfae','#f0ece4','#9fb0c4','#c9b29a'];
const hex=h=>{const c=new THREE.Color(h);return[c.r,c.g,c.b];};
const mul=(c,k)=>[c[0]*k,c[1]*k,c[2]*k];
const B_=()=>({p:[],n:[],c:[],u:[]});
function tri(b,a,bb,c,col,ua,ub,uc){const e1=[bb[0]-a[0],bb[1]-a[1],bb[2]-a[2]],e2=[c[0]-a[0],c[1]-a[1],c[2]-a[2]];let nx=e1[1]*e2[2]-e1[2]*e2[1],ny=e1[2]*e2[0]-e1[0]*e2[2],nz=e1[0]*e2[1]-e1[1]*e2[0];const nl=Math.hypot(nx,ny,nz)||1;nx/=nl;ny/=nl;nz/=nl;
 const V=[a,bb,c],U=[ua,ub,uc];for(let k=0;k<3;k++){b.p.push(V[k][0],V[k][1],V[k][2]);b.n.push(nx,ny,nz);b.c.push(col[0],col[1],col[2]);b.u.push(U[k]?U[k][0]:0,U[k]?U[k][1]:0);}}
function quad(b,a,bb,c,d,col,uv){const u=uv||[0,0,0,0];tri(b,a,bb,c,col,[u[0],u[1]],[u[2],u[1]],[u[2],u[3]]);tri(b,a,c,d,col,[u[0],u[1]],[u[2],u[3]],[u[0],u[3]]);}
function cube(b,cx,cy,cz,sx,sy,sz,col){const x0=cx-sx/2,x1=cx+sx/2,y0=cy-sy/2,y1=cy+sy/2,z0=cz-sz/2,z1=cz+sz/2;
 quad(b,[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],col);quad(b,[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1],col);quad(b,[x0,y0,z0],[x0,y0,z1],[x0,y1,z1],[x0,y1,z0],col);quad(b,[x1,y0,z0],[x1,y0,z1],[x1,y1,z1],[x1,y1,z0],col);quad(b,[x0,y1,z0],[x0,y1,z1],[x1,y1,z1],[x1,y1,z0],col);}
function geoOf(b){const ge=new THREE.BufferGeometry();ge.setAttribute('position',new THREE.Float32BufferAttribute(b.p,3));ge.setAttribute('normal',new THREE.Float32BufferAttribute(b.n,3));ge.setAttribute('color',new THREE.Float32BufferAttribute(b.c,3));ge.setAttribute('uv',new THREE.Float32BufferAttribute(b.u,2));return ge;}
function ltex(path,srgb){const t=new THREE.TextureLoader().load(path);t.wrapS=t.wrapT=THREE.RepeatWrapping;if(srgb)t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=LOW?4:8;return t;}
function airMat(tex,U){const m=new THREE.MeshStandardMaterial({map:tex,roughness:0.93,metalness:0});
 m.onBeforeCompile=sh=>{Object.assign(sh.uniforms,U);sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nvarying vec2 vGP;').replace('#include <begin_vertex>','#include <begin_vertex>\nvGP=position.xz;');
  sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nuniform sampler2D maskMap;uniform sampler2D aspMap;uniform sampler2D conMap;uniform sampler2D grsMap;uniform vec2 uWS;uniform float uNoAir,uRain;varying vec2 vGP;float gH=0.0,gWet=0.0;').replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=mix(roughnessFactor,0.16,gWet);').replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
{float fd=smoothstep(700.,120.,length(vViewPosition));float dHx=dFdx(gH)*fd,dHy=dFdy(gH)*fd;vec3 sX=dFdx(-vViewPosition),sY=dFdy(-vViewPosition),R1=cross(sY,normal),R2=cross(normal,sX);float fDet=dot(sX,R1);normal=normalize(abs(fDet)*normal-sign(fDet)*(dHx*R1+dHy*R2)*(1.-gWet*0.85));}`).replace('#include <map_fragment>',`#include <map_fragment>
  {vec3 aer=mix(diffuseColor.rgb,vec3(0.17),uNoAir);float al=dot(aer,vec3(0.333));vec3 mk=texture2D(maskMap,vec2(vGP.x/uWS.x,1.0-vGP.y/uWS.y)).rgb;
   float road=smoothstep(0.42,0.58,mk.r),walk=smoothstep(0.7,0.86,mk.g)*(1.0-road),urb=smoothstep(0.25,0.42,mk.g);
   vec3 asp=texture2D(aspMap,vGP*0.0125).rgb,con=texture2D(conMap,vGP*0.02).rgb,grs=texture2D(grsMap,vGP*0.012).rgb;
   float far=dot(texture2D(aspMap,vGP*0.0016).rgb,vec3(0.333));
   float veg=smoothstep(0.03,0.11,(aer.g-max(aer.r,aer.b))/(al+0.03))*smoothstep(0.015,0.04,al);veg*=1.0-urb*0.92;veg=mix(veg,1.0-urb,uNoAir);
   vec3 lot=con*vec3(0.56,0.58,0.62)*mix(vec3(1.0),aer*4.5,0.6);vec3 gr=dot(grs,vec3(0.333))*vec3(0.62,1.25,0.42)*mix(vec3(1.0),aer*5.0,0.45);
   vec3 c=mix(lot,gr,veg);c=mix(c,con*vec3(0.86,0.88,0.92)*mix(1.0,al*4.0,0.2),walk);
   c=mix(c,asp*1.5*mix(1.0,far*5.0,0.3)*mix(1.0,al*4.0,0.22),road);
   float edge=smoothstep(0.25,0.5,mk.r)*(1.0-smoothstep(0.5,0.78,mk.r));c*=1.0-edge*0.5;
   c=mix(c,vec3(0.72,0.52,0.08),smoothstep(0.5,0.72,mk.b)*road);
   {float lot=smoothstep(0.5,0.72,mk.b)*(1.0-road)*(1.0-walk);vec2 pq=vGP/vec2(26.0,170.0);float pv=fract(pq.y),stall=step(pv,0.31)+step(0.69,pv),fw=fwidth(pq.x)+1e-5,ln=stall*smoothstep(0.47-fw,0.47+fw,abs(fract(pq.x)-0.5))*clamp(0.05/fw,0.0,1.0);
    c=mix(c,vec3(dot(asp,vec3(0.333)))*vec3(1.08,1.12,1.2)*mix(1.0,far*5.0,0.3),lot*0.9);c=mix(c,vec3(0.74),lot*ln*0.8);}
   gH=dot(mix(mix(con,grs,veg),asp,road),vec3(0.333))*mix(2.2,1.2,road);
   {float pd=smoothstep(0.50,0.62,dot(texture2D(aspMap,vGP*0.0031+0.37).rgb,vec3(0.333))*0.6+far*0.6);gWet=max(road*pd*0.92+walk*pd*0.35,uRain*(road*0.88+walk*0.55+0.2)*(0.75+0.25*pd));c*=1.-gWet*0.45;}
   diffuseColor.rgb=c;}`);};
 return m;}
function inst(geo,mat,mats,cast){const im=new THREE.InstancedMesh(geo,mat,mats.length);mats.forEach((m,k)=>im.setMatrixAt(k,m));im.castShadow=!!cast;im.receiveShadow=true;im.frustumCulled=false;scene.add(im);return im;}
function instGLB(g,mats,cast,ry,col,out){if(!g||!mats.length)return;g.updateMatrixWorld(true);const R=new THREE.Matrix4().makeRotationY(ry||0);g.traverse(o=>{if(!o.isMesh)return;const ge=o.geometry.clone();ge.applyMatrix4(o.matrixWorld);ge.applyMatrix4(R);const m=o.material;m.metalness=0;m.roughness=0.8;if(m.emissive){m.emissive.set(0);m.emissiveMap=null;}if(col)m.color.set(col);if(m.map)m.map.anisotropy=4;if(m.transparent){m.transparent=false;m.alphaTest=0.5;m.depthWrite=true;}if(mats.length>30&&!out){const C=new Map();for(const mm of mats){const e=mm.elements,k=Math.floor(e[12]/1400)+','+Math.floor(e[14]/1400);let c=C.get(k);if(!c){c={m:[],x:0,y:0,o:[]};C.set(k,c);}c.m.push(mm);c.x+=e[12];c.y+=e[14];}C.forEach(c=>{c.x/=c.m.length;c.y/=c.m.length;const im=inst(ge,m,c.m,cast);im.computeBoundingSphere();im.frustumCulled=true;c.o.push(im);TCELLS.push(c);});}
  else{const im=inst(ge,m,mats,cast);if(out){im.computeBoundingSphere();im.frustumCulled=true;out.push(im);}}});}
function buildStatic(){
 const n0=scene.children.length;buildStatic2();for(let i=n0;i<scene.children.length;i++)if(!scene.children[i].isSprite)STATIC.push(scene.children[i]);}
function buildStatic2(){
 const mkT=new THREE.TextureLoader().load('data/mask.png');mkT.anisotropy=LOW?4:8;const det={maskMap:{value:mkT},aspMap:{value:ltex('tex/asphalt_c.jpg',1)},conMap:{value:ltex('tex/concrete_c.jpg',1)},grsMap:{value:ltex('tex/grass_c.jpg',1)},uWS:{value:new THREE.Vector2(WW,WH)},uNoAir:{value:window.EV_NOAIR?1:0},uRain:RAINU},TXN=3,TYN=2,roofM=[],tw=WW/TXN,th=WH/TYN;
 for(let ty=0;ty<TYN;ty++)for(let tx=0;tx<TXN;tx++){let t;const li=AIRIMG[ty*TXN+tx];
  if(window.EV_NOAIR){t=new THREE.DataTexture(new Uint8Array([120,120,120,255]),1,1);t.needsUpdate=true;}else if(LOW&&li){t=new THREE.Texture(li);t.needsUpdate=true;}else t=new THREE.TextureLoader().load('data/air_'+tx+'_'+ty+'.jpg');
  t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=LOW?4:8;t.wrapS=t.wrapT=THREE.ClampToEdgeWrapping;roofM.push(window.EV_NOAIR?new THREE.MeshStandardMaterial({color:0x4d4f54,roughness:0.9,side:THREE.DoubleSide}):new THREE.MeshStandardMaterial({map:t,roughness:0.9,side:THREE.DoubleSide}));
  const x0=tx*tw,y0=ty*th,nx=Math.ceil(tw/GS),ny=Math.ceil(th/GS),pos=new Float32Array((nx+1)*(ny+1)*3),uv=new Float32Array((nx+1)*(ny+1)*2),idx=[];
  for(let j=0;j<=ny;j++)for(let i=0;i<=nx;i++){const x=x0+tw*i/nx,y=y0+th*j/ny,k=j*(nx+1)+i;pos[k*3]=x;pos[k*3+1]=Hat(x,y);pos[k*3+2]=y;uv[k*2]=i/nx;uv[k*2+1]=1-j/ny;}
  for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){const a=j*(nx+1)+i,b=a+1,c=a+nx+1,d=c+1;idx.push(a,c,b,b,c,d);}
  const ge=new THREE.BufferGeometry();ge.setAttribute('position',new THREE.BufferAttribute(pos,3));ge.setAttribute('uv',new THREE.BufferAttribute(uv,2));ge.setIndex(idx);ge.computeVertexNormals();
  const m=new THREE.Mesh(ge,airMat(t,det));m.receiveShadow=true;scene.add(m);}
 const wm=new THREE.Mesh(new THREE.PlaneGeometry(120000,120000),new THREE.MeshStandardMaterial({color:0x2c5670,roughness:0.12,metalness:0.25}));wm.rotation.x=-PI/2;wm.position.set(WW/2,-3,WH/2);scene.add(wm);
 // buildings: real footprints, estimated heights
 const cells=new Map(),cellOf=(x,y,k)=>{const key=Math.floor(x/3200)+','+Math.floor(y/3200)+'|'+k;let b=cells.get(key);if(!b){b=B_();b.k=k;cells.set(key,b);}return b;};
 const FS=[[92,72],[112,72],[82,76],[82,150],[92,170]],HW=HWALL.map(hex),W1=[1,1,1],IND=[hex('#9aa0a6'),hex('#b9b3a4'),hex('#7f8a93'),hex('#a89a86')],V2=[];
 for(const bd of (CITY?[]:WORLD.bld)){const h=bd[0],kind=bd[1],st=bd[2],n=(bd.length-3)/2;let cx=0,cy=0,lo=1e9,hi=-1e9;const px=[],py=[];
  for(let i=0;i<n;i++){const x=bd[3+i*2],y=bd[4+i*2];px.push(x);py.push(y);cx+=x;cy+=y;const e=Hat(x,y);if(e<lo)lo=e;if(e>hi)hi=e;}cx/=n;cy/=n;
  const base=lo-4,top=(lo+hi)/2+h,hs=h2(px[0]|0,py[0]|0),key=(kind===0||kind===3)?'house':kind===4?'ind':'f'+st,wb=cellOf(cx,cy,key);
  const col=kind===0?HW[(hs*8)|0]:kind===3?mul(HW[(hs*8)|0],0.75):kind===4?IND[(hs*4)|0]:mul(W1,0.9+hs*0.2),U=key==='house'?46:key==='ind'?40:FS[st][0],V=key==='house'?30:key==='ind'?60:FS[st][1];
  // houses: ridge along the long axis (hip roof); the measured height is the ridge
  let rise=0,RA=null,RB=null;if(kind===0||kind===3){let sxx=0,syy=0,sxy=0;for(let i=0;i<n;i++){const dx=px[i]-cx,dy=py[i]-cy;sxx+=dx*dx;syy+=dy*dy;sxy+=dx*dy;}const th=0.5*Math.atan2(2*sxy,sxx-syy),ax=Math.cos(th),ay=Math.sin(th);let u0=1e9,u1=-1e9,v0=1e9,v1=-1e9;
   for(let i=0;i<n;i++){const dx=px[i]-cx,dy=py[i]-cy,uu=dx*ax+dy*ay,vv=-dx*ay+dy*ax;if(uu<u0)u0=uu;if(uu>u1)u1=uu;if(vv<v0)v0=vv;if(vv>v1)v1=vv;}
   const long=(u1-u0)>=(v1-v0),le=long?u1-u0:v1-v0,se=long?v1-v0:u1-u0,hl=Math.max(0,(le-se)/2),uc=(u0+u1)/2,vc=(v0+v1)/2,mx=cx+uc*ax-vc*ay,my=cy+uc*ay+vc*ax,dx=long?ax:-ay,dy=long?ay:ax;rise=clamp(se*0.3,kind===3?5:10,34);RA=[mx-dx*hl,my-dy*hl];RB=[mx+dx*hl,my+dy*hl];}
  const wt=rise?Math.max(base+24,top-rise):top,shop=(kind===1||kind===2)&&h>55?38:0,gm=(lo+hi)/2;
  let acc=Math.floor(hs*7)*U;
  for(let i=0;i<n;i++){const j=(i+1)%n,len=Math.hypot(px[j]-px[i],py[j]-py[i]),nb=Math.max(1,Math.round(len/U)),u1=acc+(key==='house'?nb:len/U);
   if(shop){const sbb=cellOf(cx,cy,'shop'),su=len/118;quad(sbb,[px[i],base,py[i]],[px[j],base,py[j]],[px[j],gm+shop,py[j]],[px[i],gm+shop,py[i]],W1,[acc,(base-gm)/shop,acc+Math.max(1,Math.round(su)),1]);
    quad(wb,[px[i],gm+shop,py[i]],[px[j],gm+shop,py[j]],[px[j],wt,py[j]],[px[i],wt,py[i]],col,[acc,0,u1,(wt-gm-shop)/V]);}
   else quad(wb,[px[i],base,py[i]],[px[j],base,py[j]],[px[j],wt,py[j]],[px[i],wt,py[i]],col,[acc,(base-gm)/V,u1,(wt-gm)/V]);acc=u1;}
  const tx=Math.min(TXN-1,Math.floor(cx/tw)),ty=Math.min(TYN-1,Math.floor(cy/th)),rb=cellOf(cx,cy,'roof'+(ty*TXN+tx)),uf=(x,y)=>[(x-tx*tw)/tw,1-(y-ty*th)/th];
  if(rise){const E=[[RA[0],wt+rise,RA[1]],[RB[0],wt+rise,RB[1]]],EU=[uf(RA[0],RA[1]),uf(RB[0],RB[1])],ne=(x,y)=>((x-RA[0])**2+(y-RA[1])**2<=(x-RB[0])**2+(y-RB[1])**2)?0:1;
   for(let i=0;i<n;i++){const j=(i+1)%n,a=ne(px[i],py[i]),b=ne(px[j],py[j]),vi=[px[i],wt,py[i]],vj=[px[j],wt,py[j]],ui=uf(px[i],py[i]),uj=uf(px[j],py[j]);
    if(a===b)tri(rb,vi,vj,E[a],W1,ui,uj,EU[a]);else{tri(rb,vi,vj,E[b],W1,ui,uj,EU[b]);tri(rb,vi,E[b],E[a],W1,ui,EU[b],EU[a]);}}}
  else{V2.length=0;for(let i=0;i<n;i++)V2.push(new THREE.Vector2(px[i],py[i]));let f;try{f=THREE.ShapeUtils.triangulateShape(V2,[]);}catch(e){f=[];}
   for(const t of f)tri(rb,[px[t[0]],top,py[t[0]]],[px[t[1]],top,py[t[1]]],[px[t[2]],top,py[t[2]]],W1,uf(px[t[0]],py[t[0]]),uf(px[t[1]],py[t[1]]),uf(px[t[2]],py[t[2]]));
   if(kind!==4&&h>90){const pc=mul(col,0.6);for(let i=0;i<n;i++){const j=(i+1)%n;quad(cellOf(cx,cy,'ind'),[px[i],top,py[i]],[px[j],top,py[j]],[px[j],top+7,py[j]],[px[i],top+7,py[i]],pc);}}}}
 const hc2=document.createElement('canvas');hc2.width=128;hc2.height=64;{const x=hc2.getContext('2d');x.fillStyle='#f4f1ea';x.fillRect(0,0,128,64);x.strokeStyle='rgba(0,0,0,.13)';for(let y=3;y<64;y+=6){x.beginPath();x.moveTo(0,y);x.lineTo(128,y);x.stroke();}
  x.fillStyle='#fff';x.fillRect(40,12,48,38);x.fillStyle='#27333f';x.fillRect(44,16,40,30);x.fillStyle='#54697c';x.fillRect(44,16,40,10);x.fillStyle='#fff';x.fillRect(63,16,2,30);x.fillStyle='rgba(0,0,0,.25)';x.fillRect(0,60,128,4);}
 const ht=new THREE.CanvasTexture(hc2);ht.wrapS=ht.wrapT=THREE.RepeatWrapping;ht.colorSpace=THREE.SRGBColorSpace;ht.anisotropy=4;
 const S=o=>new THREE.MeshStandardMaterial(Object.assign({vertexColors:true,roughness:0.85,metalness:0,side:THREE.DoubleSide},o));
 const ic=document.createElement('canvas');ic.width=64;ic.height=64;{const x=ic.getContext('2d');x.fillStyle='#e9e9e6';x.fillRect(0,0,64,64);for(let i=0;i<64;i+=4){x.fillStyle=i%8?'rgba(0,0,0,.10)':'rgba(255,255,255,.25)';x.fillRect(i,0,2,64);}x.fillStyle='rgba(0,0,0,.18)';x.fillRect(0,60,64,4);}
 const it=new THREE.CanvasTexture(ic);it.wrapS=it.wrapT=THREE.RepeatWrapping;it.colorSpace=THREE.SRGBColorSpace;it.anisotropy=4;MAT.house=S({map:ht});MAT.ind=S({map:it});MAT.shop=S({map:ltex('data/shop.jpg',1)});for(let i=0;i<5;i++)MAT['f'+i]=S({map:ltex('data/f'+i+'.jpg',1)});for(let i=0;i<6;i++)MAT['roof'+i]=roofM[i];
 cells.forEach(b=>{if(!b.p.length)return;const m=new THREE.Mesh(geoOf(b),MAT[b.k]);m.castShadow=true;m.receiveShadow=true;scene.add(m);});
 if(CITY){CITY.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;const m=o.material;m.metalness=0;m.roughness=0.86;if(m.map)m.map.anisotropy=LOW?4:8;
   if(m.map&&!m.userData.nm&&!LOW){m.userData.nm=1;const nt=new THREE.TextureLoader().load('tex/b/'+m.name+'_n.jpg');nt.flipY=false;nt.wrapS=nt.wrapT=THREE.RepeatWrapping;nt.repeat.copy(m.map.repeat);nt.offset.copy(m.map.offset);nt.rotation=m.map.rotation;nt.center.copy(m.map.center);nt.anisotropy=LOW?2:4;m.normalMap=nt;m.normalScale=new THREE.Vector2(0.9,0.9);}
   if(/^(f_|shop_)/.test(m.name)&&!/metal|cmu|lap/.test(m.name)&&!m.userData.gl){m.userData.gl=1;m.onBeforeCompile=sh=>{sh.uniforms.uNight=NIGHT;sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nfloat glassK=0.0;uniform float uNight;')
     .replace('#include <map_fragment>','#include <map_fragment>\n{vec3 tc=texture2D(map,vMapUv).rgb;glassK=smoothstep(0.03,0.14,tc.b-tc.r)*smoothstep(0.75,0.45,tc.r);}')
     .replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=mix(roughnessFactor,0.06,glassK);')
     .replace('#include <emissivemap_fragment>',`#include <emissivemap_fragment>
     #ifdef USE_NORMALMAP_TANGENTSPACE
     if(glassK>0.02){ // a room behind every window: walk the view ray into a box one bay wide and one storey tall
      vec3 V=normalize(vViewPosition),vT=vec3(dot(V,tbn[0]),dot(V,tbn[1]),dot(V,tbn[2]));vec2 cell=floor(vMapUv*2.0),o=fract(vMapUv*2.0);
      vec3 r=vec3(-vT.x,-vT.y,max(abs(vT.z),0.06));float D=0.85;
      float tx=r.x>0.?(1.-o.x)/r.x:-o.x/min(r.x,-1e-4),ty=r.y>0.?(1.-o.y)/r.y:-o.y/min(r.y,-1e-4),tz=D/r.z,tt=min(tx,min(ty,tz));vec3 hp=vec3(o,0.)+r*tt;
      float hr=fract(sin(dot(cell,vec2(12.9898,78.233)))*43758.5453),hr2=fract(hr*57.31);
      vec3 wall=mix(vec3(0.62,0.55,0.46),vec3(0.50,0.56,0.62),hr2),rc;
      if(tt==tz){rc=wall*(0.85+0.15*step(0.38,hp.y));rc=mix(rc,wall*0.45,step(hp.y,0.34)*step(0.2,hp.x)*step(hp.x,0.2+0.5*hr2));}
      else if(tt==ty)rc=r.y>0.?vec3(0.78):wall*0.5;else rc=wall*0.72;
      rc*=1.-0.45*hp.z/D;float lit=step(0.58,hr)*uNight;
      diffuseColor.rgb=mix(diffuseColor.rgb,rc*mix(0.22,0.05,uNight),glassK);
      totalEmissiveRadiance+=rc*vec3(1.0,0.80,0.52)*glassK*lit*2.6;
      normal=normalize(mix(normal,nonPerturbedNormal,glassK));}
     #else
     {vec2 wc=floor(vMapUv*2.0);float on=step(0.58,fract(sin(dot(wc,vec2(12.9898,78.233)))*43758.5453));totalEmissiveRadiance+=vec3(1.0,0.74,0.42)*glassK*on*uNight*2.4;}
     #endif`);};}}});scene.add(CITY);}
 // trees (parks, plus a thin scatter on open grass)
 const M4=()=>new THREE.Matrix4(),Q=new THREE.Quaternion(),UP=new THREE.Vector3(0,1,0),tb=B_(),gc=hex('#2f5a34'),tc=hex('#4a3526');
 cube(tb,0,12,0,4,24,4,tc);for(let k=0;k<3;k++){const y0=18+k*24,ss=26*(1-k*0.27),tp=[0,k===2?110:y0+46,0],c4=[[-ss,y0,-ss],[-ss,y0,ss],[ss,y0,ss],[ss,y0,-ss]];for(let q=0;q<4;q++)tri(tb,c4[q],c4[(q+1)%4],tp,mul(gc,(q%2?1:0.82)*(1-k*0.05)));}
 const tm=[];for(let y=3;y<MH;y+=6)for(let x=3;x<MW;x+=6){const t=map[I(x,y)],p=h2(x,y);if(!((t===PARK&&p<0.42)||(t===GRASS&&p<0.035)))continue;if(tile(x+3,y)===BLDG||tile(x-3,y)===BLDG||tile(x,y+3)===BLDG||tile(x,y-3)===BLDG||tile(x+3,y)===ROAD||tile(x-3,y)===ROAD)continue;
  const wx=(x+h2(x,y+1)*4-2)*T,wy=(y+h2(x+1,y)*4-2)*T,s=0.75+h2(y,x)*0.8;if((EXTRA.clear||[]).some(b=>wx>b[0]-40&&wx<b[2]+40&&wy>b[1]-40&&wy<b[3]+40))continue;Q.setFromAxisAngle(UP,p*40);tm.push(M4().compose(new THREE.Vector3(wx,Hat(wx,wy),wy),Q,new THREE.Vector3(s,s*(0.9+p),s)));}
 // street trees and site machines placed block by block (data/extras.json, from tools/blocks.py)
 if(tm.length){if(PROPS.tree&&PROPS.pine){const ta=[],tp=[];tm.forEach((m,i)=>((i*7)%10<6?ta:tp).push(m));instGLB(PROPS.tree,ta,true);instGLB(PROPS.pine,tp,true);}else inst(geoOf(tb),S({}),tm,true);}
 {const TC=new Map();for(const t of EXTRA.trees||[]){Q.setFromAxisAngle(UP,(t[0]*0.37+t[1]*0.11)%6.28);const k=Math.floor(t[0]/1600)+','+Math.floor(t[1]/1600);let c=TC.get(k);if(!c){c={m:[],x:0,y:0,o:[]};TC.set(k,c);}c.m.push(M4().compose(new THREE.Vector3(t[0],Hat(t[0],t[1]),t[1]),Q,new THREE.Vector3(t[2],t[2],t[2])));c.x+=t[0];c.y+=t[1];}
  TC.forEach(c=>{c.x/=c.m.length;c.y/=c.m.length;if(PROPS.tree)instGLB(PROPS.tree,c.m,true,0,null,c.o);else c.o.push(inst(geoOf(tb),S({}),c.m,true));TCELLS.push(c);});}
 {const by={};for(const p of EXTRA.props||[]){Q.setFromAxisAngle(UP,-p[3]);(by[p[0]]=by[p[0]]||[]).push(M4().compose(new THREE.Vector3(p[1],Hat(p[1],p[2]),p[2]),Q,new THREE.Vector3(p[4],p[4],p[4])));}for(const k in by)if(PROPS[k])instGLB(PROPS[k],by[k],true);}
 // street lamps, signals, bus stops along the real street network
 const lb=B_(),pc=[0.2,0.22,0.23];cube(lb,0,37,0,1.8,74,1.8,pc);cube(lb,11,73,0,22,1.6,1.6,pc);cube(lb,21,72,0,8,2,4,[0.9,0.88,0.8]);
 const lmx=[],sgx=[],nsx=[],ewx=[],hyx=[],seen=new Set();let hk=0;
 edges.forEach((e,key)=>{const a=Math.floor(key/65536),b=key%65536;if(a>b)return;const A=nodes[a],B=nodes[b],L=dist(A.x,A.y,B.x,B.y);if(L<260)return;const dx=(B.x-A.x)/L,dy=(B.y-A.y)/L;let s=((a+b)%2)?1:-1;
  for(let t=170;t<L-120;t+=430,s=-s){const x=A.x+dx*t-dy*s*(e.w/2+24),y=A.y+dy*t+dx*s*(e.w/2+24);if(solidAt(x,y))continue;Q.setFromAxisAngle(UP,-Math.atan2(dx*s,-dy*s));lmx.push(M4().compose(new THREE.Vector3(x,Hat(x,y),y),Q,new THREE.Vector3(1,1,1)));if((hk++)%3===0){const hx=A.x+dx*(t+46)-dy*s*(e.w/2+15),hy=A.y+dy*(t+46)+dx*s*(e.w/2+15);if(!solidAt(hx,hy))hyx.push(M4().makeTranslation(hx,Hat(hx,hy),hy));}}});
 if(hyx.length)instGLB(PROPS.hydrant,hyx,false);
 if(lmx.length){if(PROPS.lamp)instGLB(PROPS.lamp,lmx,false,PI,'#4a4e54');else inst(geoOf(lb),S({}),lmx,false);
  const hg=new THREE.SphereGeometry(2.6,8,6);hg.scale(1.5,0.5,1);hg.translate(PROPS.lamp?-14:21,PROPS.lamp?73.2:70.6,0);DN.glowM=new THREE.MeshBasicMaterial({color:0x000000,toneMapped:false});DN.glow=inst(hg,DN.glowM,lmx,false);DN.glow.receiveShadow=false;DN.glow.visible=false;
  const hv=new THREE.Vector3(PROPS.lamp?-14:21,62,0);DN.lit=lmx.map(m=>hv.clone().applyMatrix4(m));
  for(let i=0;i<(LOW?2:5);i++){const pl=new THREE.PointLight(0xffd9a0,0,520,1.8);pl.visible=false;scene.add(pl);DN.pool.push(pl);}}
 const TLA=[],TLH=[],TLL=[[[],[],[]],[[],[],[]]];
 const sb=B_();cube(sb,0,30,0,2.2,60,2.2,[0.13,0.14,0.15]);cube(sb,0,54,0,6,14,6,[0.13,0.14,0.15]);const lg=new THREE.BoxGeometry(7.4,4,7.4);
 nodes.forEach((n,ni)=>{if(!n.sig)return;for(const k of n.nb){const B=nodes[k],L=dist(n.x,n.y,B.x,B.y)||1,dx=(B.x-n.x)/L,dy=(B.y-n.y)/L,e=edges.get(ni*65536+k),x=n.x+dx*n.r-dy*(e.w/2+16),y=n.y+dy*n.r+dx*(e.w/2+16),hh=Hat(x,y);
   sgx.push(M4().makeTranslation(x,hh,y));(Math.abs(dy)>Math.abs(dx)?nsx:ewx).push(M4().makeTranslation(x,hh+56,y));
   {const la=e.w/2+16-e.w*0.22,hx=n.x+dx*n.r-dy*(e.w*0.22),hy=n.y+dy*n.r+dx*(e.w*0.22),g_=Math.abs(dy)>Math.abs(dx)?0:1,V=(a,b,c)=>new THREE.Vector3(a,b,c);
    Q.setFromAxisAngle(UP,-Math.atan2(dx,-dy));TLA.push(M4().compose(V((x+hx)/2,hh+58,(y+hy)/2),Q,V(la,1.5,1.5)));
    Q.setFromAxisAngle(UP,Math.atan2(dx,dy));TLH.push(M4().compose(V(hx,hh+53.5,hy),Q,V(3,10.5,2.6)));
    for(let c=0;c<3;c++)TLL[g_][c].push(M4().compose(V(hx+dx*1.5,hh+56.8-c*3.3,hy+dy*1.5),Q,V(2.1,2.1,0.6)));}}});
 MAT.tlNS=new THREE.MeshBasicMaterial({color:0xff2020,toneMapped:false});MAT.tlEW=new THREE.MeshBasicMaterial({color:0x20ff40,toneMapped:false});
 if(sgx.length){if(PROPS.signal)instGLB(PROPS.signal,sgx,true,0,'#3a3d42');else inst(geoOf(sb),S({}),sgx,true);if(TLH.length){const hm=new THREE.MeshStandardMaterial({color:0x1b1d20,roughness:0.6});inst(BOX,hm,TLA,true);inst(BOX,hm,TLH,true);MAT.tl=[0,1].map(()=>[0,1,2].map(()=>new THREE.MeshBasicMaterial({color:0x111111,toneMapped:false})));for(let g_=0;g_<2;g_++)for(let c=0;c<3;c++)if(TLL[g_][c].length)inst(BOX,MAT.tl[g_][c],TLL[g_][c],false);}}
 const bs=B_();cube(bs,0,14,0,1.4,28,1.4,[0.5,0.52,0.55]);cube(bs,0,25,0,0.8,7,6,[0.1,0.3,0.7]);if(PROPS.busstop){const bsx=[],bnx=[],trx=[],V1=new THREE.Vector3(1,1,1);for(const s of STOPS){const rd=nearestTile(s.x/T,s.y/T,ROAD,40);let ux=1,uy=0;if(rd){const L=dist(rd.x,rd.y,s.x,s.y)||1;ux=(rd.x-s.x)/L;uy=(rd.y-s.y)/L;}Q.setFromAxisAngle(UP,-Math.atan2(uy,ux));const at=(ox,oy)=>{const x=s.x+ox,y=s.y+oy;return solidAt(x,y)?null:M4().compose(new THREE.Vector3(x,Hat(x,y),y),Q,V1);};
   const m0=at(-ux*6,-uy*6)||at(ux*5,uy*5)||at(0,0),m1=at(-uy*30-ux*4,ux*30-uy*4),m2=at(uy*24,-ux*24);if(m0)bsx.push(m0);if(m1)bnx.push(m1);if(m2)trx.push(m2);}
  instGLB(PROPS.busstop,bsx,true);instGLB(PROPS.bench,bnx,true);instGLB(PROPS.trash,trx,false);}
 else{const bsx=STOPS.map(s=>M4().makeTranslation(s.x,Hat(s.x,s.y),s.y));if(bsx.length)inst(geoOf(bs),S({}),bsx,false);}
 for(const l of LM){const big=l.t==='lm'||l.t==='police',s=textSprite(l.n,l.t==='park'?'#b8f0b0':l.t==='hist'?'#ffe2a8':'#fff',big?1.5:0.9);s.position.set(l.cx,Hat(l.cx,l.cy)+(big?420:l.t==='park'?130:230),l.cy);s.userData.far=big?9000:2600;scene.add(s);LBL.push(s);}
}
function textSprite(t,col,big){const c=document.createElement('canvas'),x=c.getContext('2d');x.font='bold 30px system-ui,sans-serif';const w=Math.ceil(x.measureText(t).width)+20;c.width=w;c.height=44;x.font='bold 30px system-ui,sans-serif';x.textAlign='center';x.textBaseline='middle';x.lineWidth=6;x.strokeStyle='rgba(0,0,0,.85)';x.strokeText(t,w/2,23);x.fillStyle=col;x.fillText(t,w/2,23);
 const tx=new THREE.CanvasTexture(c);tx.colorSpace=THREE.SRGBColorSpace;const s=new THREE.Sprite(new THREE.SpriteMaterial({map:tx,transparent:true,depthWrite:false,toneMapped:false}));const k=big||0.5;s.scale.set(w*k,44*k,1);return s;}
let BOX,SPH,CYL;const mats={};
const mat=c=>mats[c]||(mats[c]=new THREE.MeshStandardMaterial({color:new THREE.Color(c),roughness:0.6}));
const bmat=c=>mats['b'+c]||(mats['b'+c]=new THREE.MeshBasicMaterial({color:new THREE.Color(c),toneMapped:false}));
function box(sx,sy,sz,c,x,y,z,par,m){const o=new THREE.Mesh(BOX,m||mat(c));o.scale.set(sx,sy,sz);o.position.set(x||0,y||0,z||0);o.castShadow=true;o.userData.fix=1;if(par)par.add(o);return o;}
/* --- model loading --- */
async function loadGLB(name){const r=await fetch('models/'+name+'.b64.txt'+DV);if(!r.ok)throw new Error(name);const bin=atob((await r.text()).trim()),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
 return new Promise((res,rej)=>new GLTFLoader().parse(u.buffer,'',res,rej));}
function prepVehicle(key,gltf){const sp=VSPEC[key],o=gltf.scene;o.updateMatrixWorld(true);const b=new THREE.Box3().setFromObject(o,true),s=b.getSize(new THREE.Vector3()),c=b.getCenter(new THREE.Vector3());
 o.position.set(-c.x,-b.min.y,-c.z);const Rg=new THREE.Group();Rg.add(o);Rg.rotation.y=sp.ry;const k=sp.l/Math.max(s.x,s.z);Rg.scale.setScalar(k);const G=new THREE.Group();G.add(Rg);sp.w=Math.min(s.x,s.z)*k;sp.h=s.y*k;
 o.traverse(m=>{if(!m.isMesh)return;m.castShadow=true;m.receiveShadow=true;if(m.material.isMeshBasicMaterial){const q=m.material;m.material=new THREE.MeshStandardMaterial({map:q.map,color:q.color,side:q.side,transparent:q.transparent,opacity:q.opacity,alphaTest:q.alphaTest,roughness:0.5,metalness:0});m.material.name=q.name;}
  m.material.side=THREE.FrontSide;if(m.material.map)m.material.map.anisotropy=4;});sp.tpl=G;}
async function loadAssets(onp){const jobs=Object.keys(CH).filter(k=>!CH[k].late).map(k=>[CH[k].f,g=>{CH[k].scene=g.scene;CH[k].clips=g.animations;}]);
 for(const k in VSPEC)jobs.push([VSPEC[k].f,g=>prepVehicle(k,g)]);for(const k in GUN)jobs.push([GUN[k].f,g=>prepGun(k,g)]);let done=0;const tot=jobs.length+2;
 const w=loadWorld().then(()=>onp(++done,tot));
 await Promise.all([w,...jobs.map(([n,fn])=>loadGLB(n).then(fn).catch(e=>console.warn('model unavailable, using procedural:',n,e)).then(()=>onp(++done,tot)))]);
 try{const sky=await new THREE.TextureLoader().loadAsync('tex/sky.jpg');sky.mapping=THREE.EquirectangularReflectionMapping;sky.colorSpace=THREE.SRGBColorSpace;scene.background=sky;scene.environment=sky;}catch(e){scene.add(new THREE.HemisphereLight(0xdfe8f0,0x55554a,1.6));}prepChars();ASSETS_DONE=true;onp(++done,tot);}
let ASSETS_DONE=false;
const GUN={pistol:{f:'g_pistol',L:0.2,gx:0.17,gy:0.62},smg:{f:'g_smg',L:0.62,gx:0.42,gy:0.55},shotgun:{f:'g_shotgun',L:0.76,gx:0.06,gy:0.5},rifle:{f:'g_rifle',L:0.88,gx:0.31,gy:0.55}};
const GMAT=new THREE.MeshStandardMaterial({color:0x24262a,roughness:0.42,metalness:0.7});
function prepGun(k,gltf){const sp=GUN[k],o=gltf.scene;o.updateMatrixWorld(true);const b=new THREE.Box3().setFromObject(o,true),sz=b.getSize(new THREE.Vector3()),c=b.getCenter(new THREE.Vector3()),s=sp.L/sz.x;
 o.position.set(-(b.min.x+sp.gx*sz.x),-(b.min.y+sp.gy*sz.y),-c.z);const R=new THREE.Group();R.add(o);R.scale.setScalar(s);o.traverse(m=>{if(m.isMesh){m.material=GMAT;m.castShadow=false;}});sp.tpl=R;}
/* --- vehicles --- */
const tintC=new Map();
function tinted(base,col){const k=base.uuid+col;let m=tintC.get(k);if(!m){m=base.clone();m.color.set(col);tintC.set(k,m);}return m;}
function paintCar(m,c){const sp=VSPEC[c.model],u=m.userData;u.col=c.col;u.dead=c.dead;if(!u.meshes)return;
 for(const q of u.meshes){const b=q.userData.base;q.material=c.dead?tinted(b,'#1c1c1c'):(sp.tint===1||b.name===sp.tint||(sp.tre&&sp.tre.test(b.name)))?tinted(b,c.col):b;}}
function mkCar(c){const G=new THREE.Group(),B=new THREE.Group(),u=G.userData,sp=VSPEC[c.model],l=c.l,w=c.w;G.add(B);u.B=B;
 if(sp&&sp.tpl){const t=sp.tpl.clone(true);B.add(t);u.meshes=[];t.traverse(q=>{if(q.isMesh){q.userData.base=q.material;u.meshes.push(q);}});}
 else{box(l,7,w,c.col,0,7.5,0,B);box(l*0.5,6,w-3,'#16212c',-l*0.07,14,0,B);}
 const hh=(sp&&sp.h)||15;
 if(c.kind==='cop'&&sp&&sp.liv&&sp.tpl){u.l1=box(2.4,1.6,w*0.2,0,-l*0.03,hh+0.3,-w*0.16,B,bmat('#ff3030'));u.l2=box(2.4,1.6,w*0.2,0,-l*0.03,hh+0.3,w*0.16,B,bmat('#3060ff'));}
 else if(c.kind==='cop'){box(l*0.3,5,w+0.5,'#16254d',0,hh*0.45,0,B);box(3,1.2,w*0.6,'#222',-l*0.04,hh+0.4,0,B);u.l1=box(3,2,w*0.26,0,-l*0.04,hh+1.6,-w*0.17,B,bmat('#ff3030'));u.l2=box(3,2,w*0.26,0,-l*0.04,hh+1.6,w*0.17,B,bmat('#3060ff'));}
 if(c.kind==='taxi'&&!(sp&&sp.liv&&sp.tpl))box(5,2.6,9,0,-l*0.04,hh+1.2,0,B,bmat('#fff2a0'));
 u.smoke=new THREE.Mesh(SPH,new THREE.MeshBasicMaterial({color:0x555555,transparent:true,opacity:0.7}));u.smoke.position.set(l*0.36,hh*0.8,0);G.add(u.smoke);
 paintCar(G,c);return G;}
/* --- people: four rigs sharing the soldier's Idle / Walk / Run clips (retargeted) --- */
const CH={soldier:{f:'soldier',s:10,ry:-PI/2},michelle:{f:'michelle',s:10,ry:-PI/2,cap:LOW?5:12},rpm:{f:'rpm',s:9.6,ry:-PI/2,cap:LOW?5:12,strip:1,ps:0.0102},cesium:{f:'cesium',s:11.4,ry:PI/2},man:{f:'man',s:5.7,ry:-PI/2,ps:0.0102,cap:LOW?5:12},woman:{f:'woman',s:5.5,ry:-PI/2,ps:0.0102,cap:LOW?5:12}};const MYL=["attendant","cong","cop","danny","dee","hargrove","marge","olsen","ped_m1","ped_m2","ped_w1","ped_w2","pruitt","sam"];for(const k of MYL)CH['hh_'+k]={f:'hh_'+k,s:10.5,ry:PI/2,my:1,late:!/^(danny|cop|ped_)/.test(k)};for(const k of ['michelle','cesium','man','woman'])CH[k].late=true;
function avgClip(c){const tr=[];for(const t of c.tracks){const n=t.getValueSize(),v=t.values,m=new Float32Array(n),k=v.length/n;for(let i=0;i<k;i++){let sg=1;if(n===4){let d=0;for(let j=0;j<4;j++)d+=v[j]*v[i*4+j];sg=d<0?-1:1;}for(let j=0;j<n;j++)m[j]+=sg*v[i*n+j];}let L=0;for(let j=0;j<n;j++){m[j]/=k;L+=m[j]*m[j];}if(n===4){L=Math.sqrt(L)||1;for(let j=0;j<4;j++)m[j]/=L;}tr.push(new t.constructor(t.name,[0,1],[...m,...m]));}return new THREE.AnimationClip('Idle',1,tr);}
const HAIR=['#2a1d14','#5a3a22','#b08a4a','#15151a','#8a8a8a','#7a3020','#d9c9a0'];
const SHIRT=['#ffffff','#c0392b','#2e6fb0','#3c8f55','#d9a13a','#7d4fa8','#30343a','#d9d4c5','#e07a9a','#3aa6a0'],PANT=['#2a3550','#3a3a3a','#5a4a3a','#27313d','#6b6f76','#1d1d22'],TONE=['#ffffff','#e6c3a6','#c99a76','#9a6a48','#6e4a32'];
function retarget(clip,c,tq,sq){const corr=tq.clone().invert().multiply(sq),q=new THREE.Quaternion(),v=new THREE.Vector3(),tr=[];
 for(const t of clip.tracks){const k=t.name.lastIndexOf('.'),node=t.name.slice(0,k),prop=t.name.slice(k+1),hips=/Hips$/.test(node);if(prop==='scale'||(prop==='position'&&!hips))continue;const val=Float32Array.from(t.values);
  if(hips&&prop==='quaternion')for(let i=0;i<val.length;i+=4){q.set(val[i],val[i+1],val[i+2],val[i+3]).premultiply(corr);val[i]=q.x;val[i+1]=q.y;val[i+2]=q.z;val[i+3]=q.w;}
  if(hips&&prop==='position')for(let i=0;i<val.length;i+=3){v.set(val[i],val[i+1],val[i+2]).applyQuaternion(corr).multiplyScalar(c.ps||0.91);val[i]=v.x;val[i+1]=v.y;val[i+2]=v.z;}
  tr.push(new t.constructor((c.strip?node.replace(/^mixamorig/,''):node)+'.'+prop,t.times,val));}
 return new THREE.AnimationClip(clip.name,clip.duration,tr);}
function prepChars(){const S=CH.soldier;if(!S.scene)return;const hp=o=>{let h=null;o.traverse(n=>{if(!h&&/Hips$/.test(n.name))h=n;});const q=new THREE.Quaternion();if(h&&h.parent){o.updateMatrixWorld(true);h.parent.getWorldQuaternion(q);}return q;};
 const sq=hp(S.scene),by=n=>THREE.AnimationClip.findByName(S.clips,n);S.anim={Idle:by('Idle'),Walk:by('Walk'),Run:by('Run')};
 for(const k of ['rpm','man','woman']){const c=CH[k];if(!c.scene||(c.anim&&c.anim.Idle))continue;const tq=hp(c.scene);c.anim={};for(const n of ['Idle','Walk','Run'])c.anim[n]=retarget(S.anim[n],c,tq,sq);}
 if(CH.cesium.scene&&CH.cesium.clips[0])CH.cesium.anim={Walk:CH.cesium.clips[0]};
 for(const k in CH){const c=CH[k];if(!c.my||!c.scene||!c.clips||c.anim)continue;const W=c.clips.find(a=>/walk/i.test(a.name)),R=c.clips.find(a=>/run/i.test(a.name));if(W)c.anim={Walk:W,Run:R||W,Idle:avgClip(W)};}}
/* story cast and spare models load when first needed; a pedestrian stands in until the real one arrives */
function want(k){const c=CH[k];if(!c||c.scene||c.ld)return;c.ld=1;loadGLB(c.f).then(g=>{c.scene=g.scene;c.clips=g.animations;prepChars();for(const e of [P,...peds,...CONTACTS])if(e.ch===k&&e._m){dynG.remove(e._m);e._m=null;const i=dyn.indexOf(e);if(i>=0)dyn.splice(i,1);}}).catch(e=>console.warn('model unavailable:',k,e));}
function castOf(o,a,d){if(!o||typeof o!=='object'||(d||0)>6)return;if(Array.isArray(o)){for(const v of o)castOf(v,a,(d||0)+1);return;}if(typeof o.w==='string'&&typeof o.t==='string'){a.add(o.w);return;}for(const k of ['intro','outro','post','steps','radio','lines','done'])if(o[k])castOf(o[k],a,(d||0)+1);}
function pickChar(p){const ok=k=>CH[k]&&CH[k].scene&&CH[k].anim;if(p===P&&ok('hh_danny'))return 'hh_danny';if(p.kind==='cop'&&ok('hh_cop'))return 'hh_cop';if(p!==P&&p.kind!=='cop'){const pd=MYL.filter(k=>/^ped_/.test(k)&&ok('hh_'+k));if(pd.length)return 'hh_'+pick(pd);}
 if(p===P)return CH.rpm.scene?'rpm':'soldier';if(p.kind==='cop')return 'soldier';const n={michelle:0,rpm:0,man:0,woman:0};for(const q of peds)if(q._m&&n[q.ch]!=null)n[q.ch]++;
 const o=[];if(CH.woman.scene&&n.woman<CH.woman.cap)o.push('woman','woman','woman');if(CH.man.scene&&n.man<CH.man.cap)o.push('man','man','man');if(!o.length&&CH.rpm.scene&&n.rpm<CH.rpm.cap)o.push('rpm','rpm');if(!o.length)o.push('soldier');return pick(o);}
function mkPed(p){const G=new THREE.Group(),u=G.userData,pl=p===P,cop=p.kind==='cop';u.px=p.x;u.py=p.y;u.sp=0;p.ch=p.ch||pickChar(p);let c=CH[p.ch];if(c&&!c.scene&&c.late){want(p.ch);c=CH[pickChar({kind:'civ'})];}
 if(c&&c.scene){const m=skClone(c.scene),s=c.s*(pl?1:0.94+Math.random()*0.1);m.scale.setScalar(s);m.rotation.y=c.ry;const In=new THREE.Group();In.add(m);G.add(In);u.In=In;
  const LK=p.look||{},sh=LK.sh||(pl?'#22252b':pick(SHIRT)),pa=LK.pa||(pl?'#2a3550':pick(PANT)),tn=LK.tn||(pl?TONE[1]:pick(TONE)),one=LK.one||(p.ch==='soldier'?(cop?'#3b55b8':'#d8c9a8'):p.ch==='cesium'?pick(SHIRT):pick(['#ffffff','#ffe9e2','#e6ecff','#f1ffe6','#e9e0d2']));
  m.traverse(q=>{if(!q.isMesh)return;q.castShadow=true;q.frustumCulled=false;const nm=q.material.name||'';
   if(p.ch==='rpm'){q.material=/Outfit_Top/.test(nm)?tinted(q.material,sh):/Outfit_Bottom/.test(nm)?tinted(q.material,pa):/Skin|Body/.test(nm)?tinted(q.material,tn):/Headwear/.test(nm)?tinted(q.material,LK.hw||(pl?'#b3261e':pick(SHIRT))):q.material;if(LK.nohat&&/Headwear/.test(nm))q.visible=false;}
   else if(c.my){}
   else if(p.ch==='man'||p.ch==='woman'){q.material=nm==='clothing'?tinted(q.material,sh):nm==='pants'?tinted(q.material,pa):nm==='skin'?tinted(q.material,LK.tn||(tn==='#ffffff'?TONE[1]:tn)):nm==='hair'?tinted(q.material,LK.hair||pick(HAIR)):nm==='shoes'?tinted(q.material,'#2a2622'):q.material;}
   else q.material=tinted(q.material,one);});
  m.traverse(n=>{if(n.isBone&&!u.head&&/Head$/.test(n.name))u.head=n;if(n.isMesh&&n.morphTargetDictionary){const d=n.morphTargetDictionary;if(d.mouthOpen!=null){(u.mo=u.mo||[]).push([n,d.mouthOpen,d.mouthSmile]);}}});u.mx=new THREE.AnimationMixer(m);const A=n=>{const cl=c.anim&&c.anim[n];if(!cl)return null;const a=u.mx.clipAction(cl);a.play();return a;};u.idle=A('Idle');u.walk=A('Walk');u.run=A('Run');if(u.walk&&u.idle)u.walk.setEffectiveWeight(0);if(u.run)u.run.setEffectiveWeight(0);u.w=[1,0,0];u.mx.update(Math.random());if(pl)attachGuns(u,m,['pistol','smg','shotgun','rifle']);else if(cop)attachGuns(u,m,['pistol']);}
 else{const In=new THREE.Group();G.add(In);u.In=In;box(3.4,7.5,6.2,pl?'#eee':cop?'#27407a':p.col,0,13,0,In);box(3.4,3.8,3.4,'#d9a982',0,19.6,0,In);box(3,9,5.6,'#333',0,4.5,0,In);}
 if(p.nm){const s=textSprite(p.nm,'#ffe9a0',0.22);s.position.y=27;G.add(s);}
 return G;}
function syncPed(p,dead,dt){const m=ent(p,mkPed),u=m.userData,ride=p===P&&P.car&&P.car.model==='moto'?P.car:null,mv=ride?0:Math.hypot(p.x-u.px,p.y-u.py);u.px=p.x;u.py=p.y;
 m.position.set(p.x,gY(p,p===P)+(p.z||0)-(ride?1.6:0),p.y);m.rotation.y=-(ride?ride.a:p.a);u.In.rotation.z=dead?PI/2:0;u.In.position.set(dead?-8:0,dead?2.5:0,0);m.visible=(!!p.actor||Math.abs(p.x-P.x)+Math.abs(p.y-P.y)<4200)&&!(p===P&&P.cutHide&&CUT)&&!p.hid;
 if(u.mx&&!dead&&m.visible){const s=dt>0?mv/dt:0;u.sp+=(s-u.sp)*Math.min(1,dt*10);
  if(u.idle){const t=u.sp<3?[1,0,0]:u.sp<32?[0,1,0]:[0,0,1],k=Math.min(1,dt*9);for(let i=0;i<3;i++)u.w[i]+=(t[i]-u.w[i])*k;u.idle.setEffectiveWeight(u.w[0]);u.walk.setEffectiveWeight(u.w[1]);u.run.setEffectiveWeight(u.w[2]);u.walk.timeScale=clamp(u.sp/15,0.7,1.7);u.run.timeScale=clamp(u.sp/58,0.75,1.5);}
  else if(u.walk)u.walk.timeScale=u.sp<3?0:clamp(u.sp/14,0.7,3.2);
  if(Math.abs(p.x-P.x)+Math.abs(p.y-P.y)<2400)u.mx.update(dt);
  if(ride||p.wave){if(!u.bn){u.bn={};m.traverse(n=>{if(n.isBone){const k=n.name.replace(/^mixamorig:?/,'');if(/^(Left|Right)(UpLeg|Leg|Foot|Arm|ForeArm|Hand)$/.test(k))u.bn[k]=n;}});}const B=u.bn,A=ride?ride.a:(p.fa!=null?p.fa:p.a),fx=Math.cos(A),fz=Math.sin(A),sx=-fz,sz=fx,D=(f,s_,up)=>_ad.set(fx*f+sx*s_,up,fz*f+sz*s_).normalize();
   if(ride&&B.LeftUpLeg&&B.LeftFoot&&B.LeftHand){for(const [S,sg] of [['Left',-1],['Right',1]]){aimBone(B[S+'UpLeg'],B[S+'Leg'],D(0.9,sg*0.38,-0.22));aimBone(B[S+'Leg'],B[S+'Foot'],D(-0.3,sg*0.05,-1));aimBone(B[S+'Arm'],B[S+'ForeArm'],D(0.72,sg*0.3,-0.6));aimBone(B[S+'ForeArm'],B[S+'Hand'],D(0.95,-sg*0.12,-0.18));}}
   else if(p.wave&&B.RightArm&&B.RightHand){const w=Math.sin(time*8+u.px)*0.6;aimBone(B.RightArm,B.RightForeArm,D(0.28,0.3,1));aimBone(B.RightForeArm,B.RightHand,D(0.2,w,1));}}
  if(!u.mo&&u.head&&p.talk){u.head.rotation.x+=Math.sin(time*11+u.px)*0.045*(0.6+0.4*Math.sin(time*3.9));u.head.rotation.y+=Math.sin(time*2.3+u.py)*0.03;}
  if(u.mo){const lv=voxLevel(),tv=p.talk?(lv>=0?lv:0.18+0.62*Math.abs(Math.sin(time*12.5+u.px))*(0.55+0.45*Math.sin(time*4.7+u.py))):0;u.mv=(u.mv||0)+(tv-(u.mv||0))*Math.min(1,dt*20);for(const q of u.mo){q[0].morphTargetInfluences[q[1]]=u.mv;if(q[2]!=null)q[0].morphTargetInfluences[q[2]]=p.talk?0.12:0;}}}
 if(u.guns){const pl=p===P,cop=p.kind==='cop',wp=pl?(P.ammo>0?P.wp:null):(cop&&stars>0?'pistol':null);for(const k in u.guns)u.guns[k].visible=!dead&&k===wp;
  const aim=!dead&&wp&&(pl?(AIM||P.shot>time-0.45):(stars>=2&&p.cd<0.5&&dist(p.x,p.y,P.x,P.y)<480));
  if(aim&&u.arm&&u.fore&&u.hand){_ad.set(Math.cos(p.a),pl?clamp(0.22-pitch,-0.5,0.4):0,Math.sin(p.a)).normalize();aimBone(u.arm,u.fore,_ad);aimBone(u.fore,u.hand,_ad);if(u.mid)aimBone(u.hand,u.mid,_ad);}
  if(u.head&&p.talk&&CUT){u.head.rotation.x+=Math.sin(time*10.5)*0.045+0.03;u.head.rotation.y+=Math.sin(time*3.9)*0.07;u.head.rotation.z+=Math.sin(time*5.7)*0.04;}}
 return m;}
const _ad=new THREE.Vector3(),_a1=new THREE.Vector3(),_a2=new THREE.Vector3(),_aq=new THREE.Quaternion(),_wq=new THREE.Quaternion(),_pq=new THREE.Quaternion();
// swing one bone so it points from itself to its child along a world direction (works on any of the rigs)
function aimBone(B,C,dir){B.updateWorldMatrix(true,true);B.getWorldPosition(_a1);C.getWorldPosition(_a2);_a2.sub(_a1).normalize();_aq.setFromUnitVectors(_a2,dir);B.getWorldQuaternion(_wq).premultiply(_aq);B.parent.getWorldQuaternion(_pq);B.quaternion.copy(_pq.invert().multiply(_wq));B.updateMatrixWorld(true);}
// low-poly guns in metres, barrel along +X, sights up +Y
function gunMesh(k){if(GUN[k]&&GUN[k].tpl)return GUN[k].tpl.clone(true);const G=new THREE.Group(),bx=(sx,sy,sz,c,x,y,z)=>{const m=box(sx,sy,sz,c,x,y,z,G);m.castShadow=false;return m;},D='#17181a',W='#5a3d28';
 if(k==='pistol'){bx(0.19,0.036,0.03,D,0.075,0.03,0);bx(0.04,0.11,0.028,D,0.0,-0.035,0);bx(0.03,0.02,0.02,D,0.045,0.0,0);}
 else if(k==='smg'){bx(0.32,0.06,0.042,D,0.11,0.03,0);bx(0.12,0.026,0.026,D,0.32,0.035,0);bx(0.035,0.16,0.03,D,0.13,-0.08,0);bx(0.04,0.1,0.03,D,0.0,-0.04,0);bx(0.17,0.035,0.03,D,-0.13,0.03,0);}
 else if(k==='rifle'){bx(0.5,0.05,0.04,D,0.2,0.03,0);bx(0.26,0.07,0.04,W,-0.2,0.0,0);bx(0.04,0.16,0.03,D,0.15,-0.08,0);bx(0.04,0.09,0.03,D,0.0,-0.04,0);}
 else{bx(0.62,0.032,0.032,D,0.3,0.045,0);bx(0.2,0.05,0.05,W,0.26,0.01,0);bx(0.2,0.07,0.045,D,0.03,0.03,0);bx(0.28,0.075,0.04,W,-0.2,0.0,0);bx(0.04,0.09,0.03,D,0.0,-0.04,0);}
 return G;}
function attachGuns(u,m,kinds){const find=re=>{let r=null;m.traverse(n=>{if(!r&&n.isBone&&re.test(n.name))r=n;});return r;};u.hand=find(/RightHand$/);u.fore=find(/RightForeArm$/);u.arm=find(/RightArm$/);
 const mid=find(/RightHandMiddle1$/),idx=find(/RightHandIndex1$/),pk=find(/RightHandPinky1$/);if(!u.hand||!mid||!idx||!pk)return;u.mid=mid;
 const X=mid.position.clone().normalize(),S=idx.position.clone().sub(pk.position).normalize(),Y=S.sub(X.clone().multiplyScalar(S.dot(X))).normalize(),Z=new THREE.Vector3().crossVectors(X,Y),un=mid.position.length()/0.09;
 u.guns={};for(const k of kinds){const h=new THREE.Group();h.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(X,Y,Z));h.scale.setScalar(un);h.position.copy(mid.position).multiplyScalar(0.55);h.add(gunMesh(k));h.visible=false;u.hand.add(h);u.guns[k]=h;}}
function ent(e,mk){if(!e._m){e._m=mk(e);dynG.add(e._m);dyn.push(e);}e._s=frameId;return e._m;}
const MK={};
function mkMarker(col,l){const G=new THREE.Group();const c=new THREE.Mesh(CYL,new THREE.MeshBasicMaterial({color:new THREE.Color(col),transparent:true,opacity:0.4,side:THREE.DoubleSide,depthWrite:false,toneMapped:false}));c.position.y=22;G.add(c);const s=textSprite(l,col,0.28);s.position.y=56;G.add(s);G.userData.c=c;scene.add(G);return G;}
function setMarker(k,x,y,vis){const m=MK[k];m.visible=vis;if(!vis)return;m.position.set(x,Hg(x,y),y);const s=1+Math.sin(time*4)*0.08;m.userData.c.scale.set(s,1,s);}
function init3D(){
 ren=new THREE.WebGLRenderer({canvas:cv,antialias:!LOW,powerPreference:'high-performance'});ren.outputColorSpace=THREE.SRGBColorSpace;ren.toneMapping=THREE.ACESFilmicToneMapping;ren.toneMappingExposure=0.82;if(!new URLSearchParams(location.search).has('nofx'))initFX();
 ren.shadowMap.enabled=true;ren.shadowMap.type=THREE.PCFSoftShadowMap;
 scene=new THREE.Scene();scene.background=new THREE.Color(0xb7c6d6);scene.fog=new THREE.Fog(0xc3d0dc,1800,LOW?5200:7000);
 cam3=new THREE.PerspectiveCamera(60,1,3,LOW?5600:7400);
 sun=new THREE.DirectionalLight(0xfff1d6,2.6);sun.castShadow=true;const sm=LOW?1024:4096;sun.shadow.mapSize.set(sm,sm);const sc=sun.shadow.camera;sc.left=-1100;sc.right=1100;sc.top=1100;sc.bottom=-1100;sc.near=10;sc.far=5000;sun.shadow.bias=-0.0004;sun.shadow.normalBias=2.5;scene.add(sun);scene.add(sun.target);
 BOX=new THREE.BoxGeometry(1,1,1);SPH=new THREE.SphereGeometry(1,10,8);CYL=new THREE.CylinderGeometry(20,20,44,18,1,true);
 dynG=new THREE.Group();scene.add(dynG);
}
function initMarkers(){GV.forEach((gv,i)=>MK['g'+i]=mkMarker(gv.type==='race'?'#ff5ad0':'#ffd23f',gv.type==='courier'?'COURIER':gv.type==='race'?'RACE':'EXPORT'));PKG.forEach(p=>{p.m=box(9,9,9,0,0,0,0,null,bmat('#40e0ff'));p.m.castShadow=false;scene.add(p.m);});
 MK.shop=mkMarker('#ff8a30','BODY SHOP');MK.pawn=mkMarker('#7ad06a','AMMO');MK.hosp=mkMarker('#ff5a6a','HEAL');MK.tgt=mkMarker('#ffe45a','▼');MK.story=mkMarker('#40e0ff','STORY');}
/* --- optional: Google Photorealistic 3D Tiles. Needs the player's own Map Tiles API key and a normal web host (blocked inside the Claude artifact). --- */
const BUILD='Nov 26 1:00am - Signals, skybridge';
/* ---------- film pass: HDR scene -> sharpen, glow, tone map, grade, grain ---------- */
let FX=null;const GTKU={value:1};
function initFX(){try{const sz=ren.getDrawingBufferSize(new THREE.Vector2()),rt=new THREE.WebGLRenderTarget(sz.x,sz.y,{samples:LOW?0:4,type:THREE.HalfFloatType});rt.depthTexture=new THREE.DepthTexture(sz.x,sz.y);
 const mat=new THREE.ShaderMaterial({depthTest:false,depthWrite:false,uniforms:{t:{value:rt.texture},px:{value:new THREE.Vector2(1/sz.x,1/sz.y)},time:{value:0},ex:{value:0.86},sat:{value:1},dt:{value:rt.depthTexture},nf:{value:new THREE.Vector2(3,7400)},pr:{value:new THREE.Vector2(1,1)},aoK:{value:new URLSearchParams(location.search).has('aodbg')?2.0:LOW?0.0:1.0}},
  vertexShader:'varying vec2 v;void main(){v=uv;gl_Position=vec4(position.xy,0.,1.);}',
  fragmentShader:`precision highp float;uniform sampler2D t,dt;uniform vec2 px,nf,pr;uniform float time,ex,sat,aoK;varying vec2 v;
  float lz(vec2 u){float z=texture2D(dt,u).x*2.-1.;return 2.*nf.x*nf.y/(nf.y+nf.x-z*(nf.y-nf.x));}
  vec3 vp(vec2 u){float z=lz(u);return vec3((u*2.-1.)*pr*z,-z);}
  float hh(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}
  float ssao(vec2 u){vec3 p=vp(u);float z=-p.z;if(z>nf.y*0.6)return 1.;
   vec3 r=vp(u+vec2(px.x,0.))-p,l=p-vp(u-vec2(px.x,0.)),up=vp(u+vec2(0.,px.y))-p,dn=p-vp(u-vec2(0.,px.y));
   vec3 n=normalize(cross(abs(r.z)<abs(l.z)?r:l,abs(up.z)<abs(dn.z)?up:dn));
   vec2 rad=clamp(vec2(26.)/(2.*z*pr),vec2(px*2.),vec2(0.09));float a=hh(u/px)*6.2832,o=0.;
   for(int i=0;i<12;i++){float fi=float(i),k=(fi+0.6)/12.;vec2 of=vec2(cos(a+fi*2.4),sin(a+fi*2.4))*rad*k;vec3 q=vp(u+of)-p;float d=length(q)+1e-3;o+=max(0.,dot(n,q)/d-0.12)*(1.-smoothstep(8.,46.,d));}
   return mix(1.-clamp(o/12.*2.3*aoK,0.,0.85),1.,smoothstep(1400.,3600.,z));}
  vec3 tm(vec3 x){x=max(x,0.)*ex/0.6;return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.,1.);}
  float h(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}
  void main(){vec3 hc=texture2D(t,v).rgb;vec3 c=tm(hc),n=tm(texture2D(t,v+vec2(0.,px.y)).rgb),s=tm(texture2D(t,v-vec2(0.,px.y)).rgb),e=tm(texture2D(t,v+vec2(px.x,0.)).rgb),w=tm(texture2D(t,v-vec2(px.x,0.)).rgb);
   vec3 mn=min(c,min(min(n,s),min(e,w))),mx=max(c,max(max(n,s),max(e,w)));vec3 a=sqrt(clamp(min(mn,1.-mx)/max(mx,vec3(1e-3)),0.,1.))*(-1./5.5);c=clamp((c+(n+s+e+w)*a)/(1.+4.*a),0.,1.);
   vec3 g=vec3(0.);for(int i=0;i<8;i++){float an=float(i)*0.7854+0.4;vec2 o=vec2(cos(an),sin(an));g+=max(texture2D(t,v+o*px*5.).rgb-1.05,0.)+max(texture2D(t,v+o*px*13.).rgb-1.05,0.)*0.6;}c+=tm(g/12.8)*0.55;
   float l=dot(c,vec3(.2126,.7152,.0722));c=mix(vec3(l),c,1.14*sat);c=mix(c,c*c*(3.-2.*c),0.32);c+=(l-0.5)*vec3(0.035,0.006,-0.04);
   if(aoK>0.)c*=ssao(v);if(aoK>1.5)c=vec3(ssao(v));
   vec2 q=v-0.5;c*=1.-dot(q,q)*0.5;c+=(h(v*vec2(1./px.x,1./px.y)+fract(time)*61.)-0.5)*0.022;
   c=clamp(c,0.,1.);gl_FragColor=vec4(mix(c*12.92,1.055*pow(c,vec3(1./2.4))-0.055,step(0.0031308,c)),1.);}`});
 const sc=new THREE.Scene(),q=new THREE.Mesh(new THREE.PlaneGeometry(2,2),mat);q.frustumCulled=false;sc.add(q);FX={rt,mat,sc,cam:new THREE.OrthographicCamera(-1,1,1,-1,0,1),sz:new THREE.Vector2(sz.x,sz.y),v:new THREE.Vector2()};}catch(e){console.warn('film pass unavailable',e);FX=null;}}
function drawFrame(){GTKU.value=FX&&qual>0?0.62:1;if(FX&&qual>0){ren.getDrawingBufferSize(FX.v);if(FX.v.x!==FX.sz.x||FX.v.y!==FX.sz.y){FX.sz.copy(FX.v);FX.rt.setSize(FX.v.x,FX.v.y);FX.mat.uniforms.px.value.set(1/FX.v.x,1/FX.v.y);}
  FX.mat.uniforms.time.value=time;{const th=Math.tan(cam3.fov*PI/360);FX.mat.uniforms.pr.value.set(th*cam3.aspect,th);FX.mat.uniforms.nf.value.set(cam3.near,cam3.far);}{const u=FX.mat.uniforms.sat,tg=P.dead>0&&!MENU?0.12:1;u.value+=(tg-u.value)*0.08;}ren.setRenderTarget(FX.rt);ren.render(scene,cam3);ren.setRenderTarget(null);ren.render(FX.sc,FX.cam);}else ren.render(scene,cam3);}let GT=null,GTG=null,gAttrT=0,gReady=false,rayBudget=0,gDt=0.016,CW=null,COUNTY=null;const STATIC=[];
/* ---------- Google ground: with 3D Tiles on, heights come from the photogrammetry mesh, so bridges, ramps and underpasses work, and the world continues past the downtown map ---------- */
const RC=new THREE.Raycaster(),RDN=new THREE.Vector3(0,-1,0),RO=new THREE.Vector3(),RDIR=new THREE.Vector3();
const OOB=(x,y)=>x<0||y<0||x>=WW||y>=WH;
function gCast(x,y,top,range,first){RO.set(x,top,y);RC.set(RO,RDN);RC.near=0;RC.far=range;RC.firstHitOnly=!!first;const h=[];try{GT.raycast(RC,h);}catch(e){}return h;}
function gY(e,pri){
 if(!GT||!gReady){e.gy=null;return Hat(e.x,e.y);}
 if(e.gf===frameId)return e.gyr;e.gf=frameId;
 const out=OOB(e.x,e.y),fb=()=>e.gy!=null?e.gy:(out?(P.gyr!=null&&e!==P&&e!==P.car?P.gyr:(e.gl!=null?e.gl:0)):Hat(e.x,e.y));
 if(e.gy==null||e.gst>0){if(e.gst>0)e.gst-=gDt;
  if(pri||rayBudget>0){if(!pri)rayBudget--;const ref=out?null:Hat(e.x,e.y),base=e.gy!=null?e.gy:(ref!=null?ref:(e.gl!=null?e.gl:(P.gyr||0)));const h=gCast(e.x,e.y,base+30000,70000,false);
   if(h.length){let b=null,bd=1e9;for(const q of h){const d=ref!=null?Math.abs(q.point.y-ref):-q.point.y;if(d<bd){bd=d;b=q.point.y;}}e.gy=b;e.gt=b;e.gx0=e.x;e.gy0=e.y;e.gmiss=0;}}
  return e.gyr=fb();}
 if(pri||(time>=(e.gn||0)&&rayBudget>0)){if(!pri)rayBudget--;e.gn=time+(Math.abs(e.x-P.x)+Math.abs(e.y-P.y)<700?0.1:0.45)+Math.random()*0.05;
  const h=gCast(e.x,e.y,e.gy+40,460,true);
  if(h.length){let ty=h[0].point.y;for(const q of h)if(q.point.y>ty)ty=q.point.y;const ds=Math.hypot(e.x-e.gx0,e.y-e.gy0);if(ds>2){e.gsl=(e.gsl||0)*0.6+clamp((ty-e.gt)/ds,-0.5,0.5)*0.4;e.gx0=e.x;e.gy0=e.y;e.gt=ty;}else if(ds<=2)e.gt=e.gt*0.5+ty*0.5;e.gmiss=0;}
  else if(++e.gmiss>2){e.gy=null;e.gmiss=0;return e.gyr=fb();}}
 e.gy+=(e.gt-e.gy)*Math.min(1,gDt*14);return e.gyr=e.gy;}
const Hg=(x,y)=>(GT&&gReady&&P.gyr!=null)?P.gyr+(OOB(x,y)||OOB(P.x,P.y)?0:Hat(x,y)-Hat(P.x,P.y)):Hat(x,y);
function gBump(){if(!GT||!gReady||!OOB(P.x,P.y)||P.gyr==null)return;const c=P.car,e=c||P,sg=c&&c.v<0?-1:1,sp=c?Math.abs(c.v):60;if(c&&sp<12)return;
 RDIR.set(Math.cos(e.a)*sg,0,Math.sin(e.a)*sg);RO.set(e.x,P.gyr+11,e.y);RC.set(RO,RDIR);RC.near=0;RC.far=(c?c.l/2:6)+10+sp*gDt;RC.firstHitOnly=true;const h=[];try{GT.raycast(RC,h);}catch(er){}
 if(!h.length)return;const back=(c?5:2.5)*sg;e.x-=Math.cos(e.a)*back;e.y-=Math.sin(e.a)*back;if(c){if(sp>90){sfx('crash');c.hp-=sp*0.04;shake=Math.min(10,sp*0.03);}c.v=-c.v*0.25;c.lat=0;}}
function ll2w(lon,lat,h){const v=new THREE.Vector3();GT.ellipsoid.getCartographicToPosition(lat*PI/180,lon*PI/180,h||0,v);GT.group.updateWorldMatrix(true,false);return v.applyMatrix4(GT.group.matrixWorld);}
function buildCounty(){if(!COUNTY||!GT||CW)return;try{const w=(p)=>{const v=ll2w(p[0],p[1]);return [v.x,v.z];};CW={ring:COUNTY.ring.map(w),roads:COUNTY.roads.map(r=>{const pts=r[2].map(w);let x0=1e12,y0=1e12,x1=-1e12,y1=-1e12;for(const q of pts){x0=Math.min(x0,q[0]);y0=Math.min(y0,q[1]);x1=Math.max(x1,q[0]);y1=Math.max(y1,q[1]);}return{n:r[0],c:r[1],pts,x0,y0,x1,y1};}),places:COUNTY.places.map(p=>{const q=w([p[1],p[2]]);return{n:p[0],x:q[0],y:q[1],city:p[3],lon:p[1],lat:p[2]};})};
  const sel=document.getElementById('trav');if(sel&&sel.options.length<3){for(const pl of CW.places){const o=document.createElement('option');o.value=pl.n;o.textContent=(pl.city?'':'· ')+pl.n;sel.appendChild(o);}}}catch(e){console.warn('county map unavailable',e);}}
function nearPlace(){if(!CW)return 'Snohomish County';let b=null,bd=1e12;for(const p of CW.places){const d=dist(p.x,p.y,P.x,P.y);if(d<bd){bd=d;b=p;}}return b&&bd<90000?(bd<15000?b.n:'Near '+b.n):'Off the map';}
function travel(name){const msg=t=>{const e=document.getElementById('gmsg');if(e)e.textContent=t;};
 if(name==='__home'){const l=HOSP||{curb:{x:WW/2,y:WH/2}};if(P.car){P.car.drv=null;P.car=null;}P.x=l.curb.x;P.y=l.curb.y;P.gy=null;P.gst=3;return true;}
 if(!GT||!gReady){msg('Turn on Google 3D first: the county outside downtown is built from Google 3D Tiles.');return false;}buildCounty();const pl=CW&&CW.places.find(q=>q.n===name);if(!pl)return false;
 if(M)endMission(false,'Left the job');let c=P.car;if(!c){c=makeCar(pl.x,pl.y,0,'civ',VSPEC.muscle.tpl?'muscle':'sedan');c.drv='player';c.keep=true;P.car=c;}c.x=pl.x;c.y=pl.y;c.v=0;c.lat=0;P.x=pl.x;P.y=pl.y;
 c.gy=null;c.gst=7;c.gl=ll2w(pl.lon,pl.lat,150).y;P.gy=null;P.gyr=c.gl;pts=0;cool=0;say('Travelling to '+name+'. The area sharpens as it loads.',5);return true;}
function countyMini(mx,my,mr){const k=mr/26000,X=x=>mx+(x-P.x)*k,Y=y=>my+(y-P.y)*k,R=26000;g.fillStyle='#1c2a30';g.fillRect(mx-mr,my-mr,mr*2,mr*2);if(!CW)return;g.lineJoin='round';
 for(const pass of [2,1])for(const r of CW.roads){if(r.c!==pass||r.x1<P.x-R||r.x0>P.x+R||r.y1<P.y-R||r.y0>P.y+R)continue;g.strokeStyle=pass===1?'#e9c35a':'#93a7b3';g.lineWidth=pass===1?2.4:1.2;g.beginPath();r.pts.forEach((q,i)=>i?g.lineTo(X(q[0]),Y(q[1])):g.moveTo(X(q[0]),Y(q[1])));g.stroke();}
 g.fillStyle='#4fb3ff';g.fillRect(X(WW/2)-3,Y(WH/2)-3,6,6);g.font='bold 9px system-ui,sans-serif';g.textAlign='center';g.textBaseline='bottom';for(const pl of CW.places){if(!pl.city||Math.abs(pl.x-P.x)>R||Math.abs(pl.y-P.y)>R)continue;g.fillStyle='#fff';g.fillText(pl.n,X(pl.x),Y(pl.y)-2);}}
function drawCountyMap(cv2){if(!CW)return;const x0=Math.min(...CW.ring.map(q=>q[0])),x1=Math.max(...CW.ring.map(q=>q[0])),y0=Math.min(...CW.ring.map(q=>q[1])),y1=Math.max(...CW.ring.map(q=>q[1])),Wc=1100,k=Wc/(x1-x0),Hc=Math.round((y1-y0)*k);cv2.width=Wc;cv2.height=Hc;const c=cv2.getContext('2d'),X=x=>(x-x0)*k,Y=y=>(y-y0)*k;
 c.fillStyle='#16242b';c.fillRect(0,0,Wc,Hc);c.fillStyle='#22363d';c.beginPath();CW.ring.forEach((q,i)=>i?c.lineTo(X(q[0]),Y(q[1])):c.moveTo(X(q[0]),Y(q[1])));c.closePath();c.fill();c.strokeStyle='#5d7884';c.lineWidth=2;c.stroke();c.lineJoin='round';
 for(const pass of [2,1])for(const r of CW.roads){if(r.c!==pass)continue;c.strokeStyle=pass===1?'#e9c35a':'#8fa3b0';c.lineWidth=pass===1?3:1.4;c.beginPath();r.pts.forEach((q,i)=>i?c.lineTo(X(q[0]),Y(q[1])):c.moveTo(X(q[0]),Y(q[1])));c.stroke();}
 c.font='bold 15px system-ui,sans-serif';c.textAlign='center';c.textBaseline='bottom';for(const pl of CW.places){if(!pl.city)continue;c.fillStyle='#fff';c.beginPath();c.arc(X(pl.x),Y(pl.y),4,0,7);c.fill();c.fillText(pl.n,X(pl.x),Y(pl.y)-6);}
 c.fillStyle='#e02020';c.strokeStyle='#000';c.lineWidth=2;c.beginPath();c.arc(X(P.x),Y(P.y),8,0,7);c.fill();c.stroke();
 cv2.onclick=ev=>{const r=cv2.getBoundingClientRect(),wx=x0+(ev.clientX-r.left)/r.width*(x1-x0),wy=y0+(ev.clientY-r.top)/r.height*(y1-y0);let b=null,bd=1e12;for(const pl of CW.places){const d=dist(pl.x,pl.y,wx,wy);if(d<bd){bd=d;b=pl;}}if(b&&bd<(x1-x0)*0.04){const s=document.getElementById('trav');if(s)s.value=b.n;}};}
async function enableGoogleTiles(key){const msg=t=>{const e=document.getElementById('gmsg');if(e)e.textContent=t;};if(GT||!key)return;
 try{msg('Loading Google 3D Tiles...');
  const [T3,D3]=await Promise.all([import('../lib/tiles.js'),import('three/addons/loaders/DRACOLoader.js')]);
  const t=new T3.TilesRenderer();t.registerPlugin(new T3.GoogleCloudAuthPlugin({apiToken:key}));
  const dr=new D3.DRACOLoader();dr.setDecoderPath('lib/draco/');const gl=new GLTFLoader(t.manager);gl.setDRACOLoader(dr);t.manager.addHandler(/\.(gltf|glb)$/g,gl);
  t.setLatLonToYUp(47.9785*PI/180,-122.2045*PI/180);t.setCamera(cam3);t.setResolutionFromRenderer(cam3,ren);const ge=parseFloat(new URLSearchParams(location.search).get('ge'));t.errorTarget=isNaN(ge)?(LOW?12:6):ge;
  t.addEventListener('load-model',e=>{e.scene.traverse(m=>{if(m.isMesh&&m.material&&!m.material.userData.gt){const o=m.material;if(o.map){o.map.anisotropy=Math.min(8,ren.capabilities.getMaxAnisotropy());o.map.needsUpdate=true;}const n=new THREE.MeshLambertMaterial({map:o.map,toneMapped:false});n.userData.gt=1;n.onBeforeCompile=sh=>{sh.uniforms.GTK=GTKU;sh.fragmentShader='uniform float GTK;\n'+sh.fragmentShader;sh.fragmentShader=sh.fragmentShader.replace('#include <shadowmap_pars_fragment>','#include <shadowmap_pars_fragment>\n#include <shadowmask_pars_fragment>').replace('#include <opaque_fragment>','outgoingLight=diffuseColor.rgb*GTK*(0.5+0.5*getShadowMask());\n#include <opaque_fragment>');};m.material=n;m.receiveShadow=true;o.dispose();}});});
  const R=new THREE.Group();R.rotation.y=PI/2;R.add(t.group);GTG=new THREE.Group();GTG.add(R);GTG.scale.setScalar(10);GTG.position.set(WW/2,0,WH/2);
  const gz=parseFloat(new URLSearchParams(location.search).get('gz'));GTG.position.y=isNaN(gz)?220:gz;scene.add(GTG);
  let ok=false;t.addEventListener('load-tile-set',()=>{if(!ok){ok=true;gReady=true;for(const m of STATIC)m.visible=false;msg('Google 3D Tiles on');cam3.far=LOW?26000:60000;cam3.updateProjectionMatrix();scene.fog.near=LOW?2500:4000;scene.fog.far=LOW?24000:56000;setTimeout(buildCounty,50);}});
  t.addEventListener('load-error',e=>{if(!ok)msg('Google refused the key on this device. On iPhone the key must allow https://cbgregg.github.io/* (see chat).');});
  GT=t;try{localStorage.setItem('everett_gkey',key);localStorage.removeItem('everett_goff');}catch(e){}
 }catch(e){console.warn(e);msg('Google 3D Tiles are not available here: '+(e&&e.message||e));}}
function disableGoogleTiles(){try{localStorage.removeItem('everett_gon2');localStorage.removeItem('everett_gkey');localStorage.setItem('everett_goff','1');}catch(e){}if(GT){scene.remove(GTG);GT.dispose();GT=null;gReady=false;for(const m of STATIC)m.visible=true;cam3.far=LOW?5600:7400;cam3.updateProjectionMatrix();scene.fog.near=1800;scene.fog.far=LOW?5200:7000;if(OOB(P.x,P.y))travel('__home');for(const c of cars)if(OOB(c.x,c.y)){c.gone=true;c.keep=false;}}const e=document.getElementById('gattr');if(e)e.textContent='';const g2=document.getElementById('gmsg');if(g2)g2.textContent='Google 3D Tiles off';}
const sigState=v=>{const ph=time%18,vg=ph>=9,yl=(ph%9)>7.3;return v===vg?(yl?1:2):0;};
const SUNV=new THREE.Vector3(-0.45,0.78,0.42).normalize();
/* ---------- day and night: one game minute per second, so a full day is 24 minutes. The sun rises in the east at 06:00,
   crosses the southern sky and sets in the west at 20:00; the moon takes over as a dim blue light. ---------- */
let TOFF=(()=>{const h=parseFloat(new URLSearchParams(location.search).get('hour'));return isFinite(h)?(h*60-540+1440)%1440:0;})();
const gmin=()=>(540+time+TOFF)%1440,NIGHT={value:0},DN={k:1,inset:false,lit:[],pool:[],pt:0,sunC:new THREE.Color(),c0:new THREE.Color(0xff8a4a),c1:new THREE.Color(0xfff1d6),cm:new THREE.Color(0x8fa8ff),f0:new THREE.Color(0xc3d0dc),f1:new THREE.Color(0x0a1220),f2:new THREE.Color(0xe9b48a)};
const TCELLS=[];let RAIN=null,RAINON=false,RAINS=null;const RAINU={value:0};
function rainTick(dt){const tg=RAINON&&!DN.inset?1:0;RAINU.value+=(tg-RAINU.value)*Math.min(1,dt*0.9);
 if(!RAIN){const n=LOW?800:1900,p=new Float32Array(n*6),bb=new Float32Array(n*2);for(let i=0;i<n;i++){const x=(Math.random()-0.5)*760,z=(Math.random()-0.5)*760,y=Math.random()*400;p.set([x,0,z,x+1.6,-14,z+0.9],i*6);bb[i*2]=bb[i*2+1]=y;}
  const ge=new THREE.BufferGeometry();ge.setAttribute('position',new THREE.BufferAttribute(p,3));ge.setAttribute('b',new THREE.BufferAttribute(bb,1));
  RAIN=new THREE.LineSegments(ge,new THREE.ShaderMaterial({transparent:true,depthWrite:false,fog:false,uniforms:{t:{value:0},a:RAINU,k:{value:1}},vertexShader:'attribute float b;uniform float t;void main(){vec3 p=position;p.y+=mod(b-t*440.,400.)-70.;gl_Position=projectionMatrix*viewMatrix*vec4(p+cameraPosition,1.);}',fragmentShader:'uniform float a,k;void main(){gl_FragColor=vec4(vec3(0.78,0.85,1.0)/k,0.36*a);}'}));RAIN.frustumCulled=false;RAIN.renderOrder=6;scene.add(RAIN);}
 RAIN.visible=RAINU.value>0.02;RAIN.material.uniforms.t.value=time;RAIN.material.uniforms.k.value=Math.max(DN.k,0.3);
 if(AC&&MG&&RAINON&&!RAINS){try{const bf=AC.createBuffer(1,AC.sampleRate*2,AC.sampleRate),d=bf.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;const sr=AC.createBufferSource();sr.buffer=bf;sr.loop=true;const f=AC.createBiquadFilter();f.type='bandpass';f.frequency.value=2600;f.Q.value=0.35;RAINS=AC.createGain();RAINS.gain.value=0;sr.connect(f);f.connect(RAINS);RAINS.connect(MG);sr.start();}catch(e){}}
 if(RAINS)RAINS.gain.value=AMB.rain_loop?0:0.11*RAINU.value*(sndOn?1:0);}
/* ambience loops, one-shot effects and music from data/amb.json (tools/audio_gen.py) */
const AMB={};let AMBL=null,AMBT={nt:0,wr:0};
function loadAmb(){if(AMBL||!AC)return;AMBL=fetch('data/amb.json'+DV).then(r=>r.json()).then(j=>{for(const k in j){const b=atob(j[k]),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);AC.decodeAudioData(u.buffer,buf=>{AMB[k]={b:buf};},()=>{});}}).catch(()=>{});}
function ambSet(k,vol){const a=AMB[k];if(!a||!AC||!MG)return;if(!a.g){if(vol<=0.001)return;a.g=AC.createGain();a.g.gain.value=0;a.s=AC.createBufferSource();a.s.buffer=a.b;a.s.loop=true;a.s.connect(a.g);a.g.connect(MG);a.s.start();}a.g.gain.value+=((sndOn?vol:0)-a.g.gain.value)*0.04;}
function ambOne(k,vol){const a=AMB[k];if(!a||!AC||!MG||!sndOn)return;try{const sr=AC.createBufferSource(),gn=AC.createGain();gn.gain.value=vol||1;sr.buffer=a.b;sr.connect(gn);gn.connect(MG);sr.start();}catch(e){}}
function ambTick(){loadAmb();const rn=RAINU.value,night=NIGHT.value,bar=DN.inset&&(DN.insetK||1)<0.9?1:0,ride=P.car&&P.car.model==='moto'?1:0,cut=CUT&&!MENU?1:0;
 ambSet('rain_loop',rn*(DN.inset?0.1:0.5));ambSet('city_night',(1-rn*0.6)*(DN.inset?0:0.22)*(0.4+0.6*night));ambSet('bar_room',bar*0.5);ambSet('moto_loop',ride*(0.22+Math.min(0.4,Math.abs(P.car?P.car.v:0)/600)));
 ambSet('music_menu',MENU?0.5:0);ambSet('music_tense',cut?(bar?0.1:0.2):0);ambSet('music_ride',!MENU&&!cut&&ride&&MODE==='story'&&ST===0?0.3:0);
 if(ride&&!AMBT.wr)ambOne('moto_start',0.7);AMBT.wr=ride;
 if(rn>0.5&&!DN.inset&&!MENU&&time>AMBT.nt){AMBT.nt=time+16+Math.random()*28;if(AMB.thunder){ambOne(Math.random()<0.5?'thunder':'thunder2',0.6);DN.flash=1;}}}
let SKY=null;
function mkSky(){const m=new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,fog:false,uniforms:{sunD:{value:new THREE.Vector3(0,1,0)},moonD:{value:new THREE.Vector3(0,1,0)},day:{value:1},night:{value:0},t:{value:0},k:{value:1}},
 vertexShader:'varying vec3 d;void main(){d=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);gl_Position.z=gl_Position.w*0.99995;}',
 fragmentShader:`precision highp float;varying vec3 d;uniform vec3 sunD,moonD;uniform float day,night,t,k;
 float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
 float n2(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(h(i),h(i+vec2(1.,0.)),f.x),mix(h(i+vec2(0.,1.)),h(i+vec2(1.,1.)),f.x),f.y);}
 float fbm(vec2 p){float a=.5,s=0.;for(int i=0;i<5;i++){s+=a*n2(p);p=p*2.03+17.;a*=.5;}return s;}
 void main(){vec3 v=normalize(d);float up=max(v.y,0.),hz=pow(1.-up,3.5),se=sunD.y,sd=max(dot(v,sunD),0.);
  vec3 zen=mix(vec3(0.004,0.008,0.022),vec3(0.10,0.27,0.72),day),hor=mix(vec3(0.012,0.018,0.04),vec3(0.60,0.75,0.93),day);
  float gold=day*(1.-smoothstep(0.05,0.5,se));hor=mix(hor,vec3(1.0,0.50,0.20),gold*(0.3+0.7*pow(sd,2.5)));zen=mix(zen,vec3(0.22,0.20,0.46),gold*0.55);
  vec3 c=mix(zen,hor,hz);
  c+=vec3(1.0,0.72,0.42)*pow(sd,10.)*0.4*min(1.,day*3.);c+=vec3(1.0,0.95,0.86)*smoothstep(0.99955,0.9998,sd)*30.*step(-0.02,se)*min(1.,day*4.+gold);
  float md=max(dot(v,moonD),0.);c+=(vec3(0.85,0.9,1.0)*smoothstep(0.9996,0.99975,md)*1.6+vec3(0.25,0.33,0.6)*pow(md,80.)*0.12)*night;
  vec3 q=v*190.,qi=floor(q),qf=fract(q)-0.5;float sr=h(qi.xy+qi.z*13.7);c+=vec3(0.9,0.93,1.0)*step(0.992,sr)*smoothstep(0.16,0.02,length(qf))*night*smoothstep(0.03,0.3,v.y)*(0.5+0.5*sin(t*1.7+sr*90.))*0.9;
  vec2 cp=v.xz/(v.y+0.2)*1.5+vec2(t*0.006,t*0.003);float f=fbm(cp),cl=smoothstep(0.46,0.8,f)*smoothstep(-0.02,0.2,v.y);
  vec3 cc=mix(vec3(0.02,0.025,0.04),vec3(1.0,0.98,0.96),day);cc=mix(cc,vec3(1.0,0.58,0.36),gold*0.75*(0.4+0.6*sd));cc*=0.72+0.4*fbm(cp*2.4+5.);c=mix(c,cc,cl*0.88);
  gl_FragColor=vec4(c/max(k,0.2),1.);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
 }`});
 SKY=new THREE.Mesh(new THREE.SphereGeometry(4800,32,18),m);SKY.frustumCulled=false;SKY.renderOrder=-10;scene.add(SKY);}
function dayNight(){const h=gmin()/60,ss=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
 const dt_=(h-6)/14,isDay=dt_>0&&dt_<1,nt=((h+4)%24)/10,u=isDay?dt_:nt,el=Math.sin(u*PI)*(isDay?1.0:0.8),az=u*PI;
 SUNV.set(Math.cos(az)*Math.cos(Math.max(el,0.14)),Math.sin(Math.max(el,0.14)),Math.sin(az)*Math.cos(Math.max(el,0.14))+0.18).normalize();
 const up=Math.sin(el),day=isDay?ss(0.0,0.3,up):0,night=1-(isDay?ss(-0.02,0.16,up):0);NIGHT.value=night;
 if(DN.inset){sun.intensity=0.8*(DN.insetK||1);sun.color.copy(DN.c1);DN.k=DN.insetK||1;}
 else{if(isDay){sun.color.copy(DN.c0).lerp(DN.c1,ss(0.08,0.5,up));sun.intensity=2.6*ss(0.0,0.3,up);}else{sun.color.copy(DN.cm);sun.intensity=0.7*ss(0.0,0.25,up);}DN.k=0.36+0.64*(1-night);}
 rainTick(gDt);preTick();ambTick();if(DN.flash>0){DN.k+=DN.flash*1.1;DN.flash=Math.max(0,DN.flash-gDt*4.5);if(FX)FX.mat.uniforms.ex.value=0.86*DN.k;ren.toneMappingExposure=0.82*DN.k;}if(!SKY)mkSky();{const U=SKY.material.uniforms;SKY.position.copy(cam3.position);U.day.value=1-night;U.night.value=night;U.t.value=time;U.k.value=DN.k;if(isDay){U.sunD.value.copy(SUNV);U.moonD.value.set(-SUNV.x,-0.3,-SUNV.z).normalize();}else{U.moonD.value.copy(SUNV);U.sunD.value.set(-SUNV.x,-0.25,-SUNV.z).normalize();}if(scene.background&&scene.background.isTexture)scene.background=null;}
if(scene.fog){const gold=isDay?(1-ss(0.1,0.45,up))*(1-night):0;scene.fog.color.copy(DN.f0).lerp(DN.f2,gold*0.55).lerp(DN.f1,night);}
 if(FX)FX.mat.uniforms.ex.value=0.86*DN.k;ren.toneMappingExposure=0.82*DN.k;
 const boost=1/Math.max(DN.k,0.3);for(const m of [MAT.tlNS,MAT.tlEW])if(m)m.color.multiplyScalar(boost);
 if(DN.glow){DN.glow.visible=night>0.05;DN.glowM.color.setRGB(3.2*night*boost,2.5*night*boost,1.5*night*boost);}
 if(DN.pool.length&&time-DN.pt>0.4){DN.pt=time;const cx=P.x,cy=P.y;const near=DN.lit.map(l=>[(l.x-cx)**2+(l.z-cy)**2,l]).sort((a,b)=>a[0]-b[0]);
  DN.pool.forEach((pl,i)=>{const l=near[i]&&near[i][0]<1500*1500?near[i][1]:null;pl.visible=!!l&&night>0.05&&!DN.inset;if(l)pl.position.copy(l);});}
 for(const pl of DN.pool)pl.intensity=7000*night;
 if(!DN.pf){DN.pf=new THREE.PointLight(0xffe8cc,0,190,1.5);scene.add(DN.pf);}DN.pf.position.set(P.x+(cam3.position.x-P.x)*0.4,Hg(P.x,P.y)+34,P.y+(cam3.position.z-P.y)*0.4);DN.pf.intensity=DN.inset||MENU?0:800*night;
 if(time-(DN.tt||-9)>0.4){DN.tt=time;const R=(LOW?1500:2600)*(qual===0?0.65:1);for(const c of TCELLS){const v=!DN.inset&&!(GT&&gReady)&&Math.abs(c.x-P.x)+Math.abs(c.y-P.y)<R;for(const o of c.o)o.visible=v;}}}
function render(){
 frameId++;const dt=clamp(time-lastT,0,0.05);lastT=time;gDt=dt||0.016;rayBudget=LOW?4:7;
 const SC=[0xff2a20,0xffc020,0x20ff50];MAT.tlNS.color.setHex(SC[sigState(true)]);MAT.tlEW.color.setHex(SC[sigState(false)]);if(MAT.tl){const st=[sigState(true),sigState(false)],bs=1.7/Math.max(DN.k,0.3),OFF=[0x2a0806,0x2a2006,0x062a0c];for(let g_=0;g_<2;g_++)for(let c=0;c<3;c++){const m=MAT.tl[g_][c];m.color.setHex(st[g_]===c?SC[c]:OFF[c]);if(st[g_]===c)m.color.multiplyScalar(bs);}}
 for(const c of cars){const m=ent(c,mkCar),u=m.userData,co=Math.cos(c.a),si=Math.sin(c.a),hl=c.l*0.4,hw=c.w*0.5,gy=gY(c,c===P.car),gg=GT&&c.gy!=null;m.position.set(c.x,gy,c.y);m.rotation.y=-c.a;m.visible=Math.abs(c.x-P.x)+Math.abs(c.y-P.y)<5200;
  const gp=gg?Math.atan(clamp(c.gsl||0,-0.4,0.4)):Math.atan2(Hat(c.x+co*hl,c.y+si*hl)-Hat(c.x-co*hl,c.y-si*hl),hl*2),gr=gg?0:-Math.atan2(Hat(c.x-si*hw,c.y+co*hw)-Hat(c.x+si*hw,c.y-co*hw),hw*2);
  const roll=clamp((c.lat||0)*0.004,-0.13,0.13),acc=((c.v-(u.pv==null?c.v:u.pv))||0);u.pv=c.v;u.pit=(u.pit||0)*0.85+clamp(-acc*0.01,-0.05,0.05)*0.15;u.B.rotation.x=roll+gr;u.B.rotation.z=u.pit+gp;
  if(u.col!==c.col||u.dead!==c.dead)paintCar(m,c);
  if(u.l1){const f=c.sir&&Math.floor(time*7)%2;u.l1.material=bmat(f?'#ff3030':c.sir?'#401010':'#a02020');u.l2.material=bmat(c.sir&&!f?'#3060ff':c.sir?'#101840':'#2040a0');}
  const sm=!c.dead&&c.hp<40;u.smoke.visible=sm;if(sm){const s=(c.hp<=0?9:6)+Math.sin(time*9)*1.5;u.smoke.scale.set(s,s*1.4,s);u.smoke.material.color.setHex(c.hp<=0?0xff8a20:0x555555);}}
 for(const p of peds)syncPed(p,p.dead,dt);
 for(const c of CONTACTS)syncPed(c,false,dt);
 if(!P.car||P.car.model==='moto')syncPed(P,!!P.dead&&!P.bust,dt);
 for(const k of picks){const m=ent(k,e=>box(7,4,10,e.k==='cash'?'#58c45a':'#d9c15a'));m.position.set(k.x,Hg(k.x,k.y)+9+Math.sin(time*4+k.x)*2,k.y);m.rotation.y=time*3;}
 for(const p of PKG){p.m.visible=!pkgGot[p.i]&&Math.abs(p.x-P.x)+Math.abs(p.y-P.y)<2500;if(p.m.visible){p.m.position.set(p.x,Hg(p.x,p.y)+12+Math.sin(time*3+p.i)*3,p.y);p.m.rotation.y=time*2;p.m.rotation.x=time;}}
 for(const s of LBL)s.visible=!CUT&&!MENU&&Math.abs(s.position.x-P.x)+Math.abs(s.position.z-P.y)<s.userData.far;
 for(const s of stains){const m=ent(s,()=>{const q=new THREE.Mesh(CYL,new THREE.MeshBasicMaterial({color:0x5a0a0a}));q.scale.set(0.45,0.004,0.45);return q;});m.position.set(s.x,Hg(s.x,s.y)+0.6,s.y);}
 for(const f of fx){if(f.k==='tr'){ent(f,e=>{const ge=new THREE.BufferGeometry();ge.setAttribute('position',new THREE.Float32BufferAttribute([e.x1,Hg(e.x1,e.y1)+13,e.y1,e.x2,Hg(e.x2,e.y2)+12,e.y2],3));return new THREE.Line(ge,new THREE.LineBasicMaterial({color:0xfff0a0,toneMapped:false}));});}
  else if(f.k==='boom'){const m=ent(f,()=>new THREE.Mesh(SPH,new THREE.MeshBasicMaterial({color:0xffa030,transparent:true,toneMapped:false})));const r=(0.7-f.t)/0.7,s=18+r*80;m.position.set(f.x,Hg(f.x,f.y)+12+r*20,f.y);m.scale.set(s,s,s);m.material.opacity=1-r;m.material.color.setRGB(1,0.75-r*0.5,0.15);}}
 for(let i=dyn.length-1;i>=0;i--){const e=dyn[i];if(e._s!==frameId){dynG.remove(e._m);if(e._m.isLine)e._m.geometry.dispose();e._m=null;dyn.splice(i,1);}}
 GV.forEach((gv,i)=>setMarker('g'+i,gv.x,gv.y,!M));setMarker('shop',SHOP.door.x,SHOP.door.y,true);setMarker('pawn',PAWN.curb.x,PAWN.curb.y,true);setMarker('hosp',HOSP.curb.x,HOSP.curb.y,true);setMarker('tgt',M?M.tx:0,M?M.ty:0,!!M&&!M.hide);{const sc=MODE==='story'&&!M&&!CUT&&ST<STORY.length?STORY[ST]:null;setMarker('story',sc?sc.gx:0,sc?sc.gy:0,!!sc);}
 // third-person camera: orbit distance and height from pitch, pulled in when a wall is behind, closer over the shoulder when aiming
 const cy=yaw+(lookBack?PI:0),sp=P.car?Math.abs(P.car.v):0,Dw=P.car?P.car.l*1.2+(P.car.model==='moto'?22:27)+sp*0.06:(AIM?22:30),Hc=P.car?(VSPEC[P.car.model].h||15)+6:(AIM?20.5:16.5);let dd=Dw;
 for(let s=8;s<=Dw;s+=6){if(solidTileNoWater(P.x-Math.cos(cy)*s,P.y-Math.sin(cy)*s)){dd=Math.max(14,s-10);break;}}
 camD+=(dd-camD)*(dd<camD?0.5:0.08);const sx=shake?rand(-shake,shake)*0.5:0,cp=Math.cos(pitch),sn=Math.sin(pitch),sh=AIM?7:(P.car?0:3.2);
 const pg=P.car?gY(P.car,true):gY(P,true);if(P.car){P.gy=P.car.gy;P.gt=P.car.gt;P.gyr=pg;P.gl=pg;}else P.gl=pg;gBump();
 const py=pg+(P.car?0:(P.z||0)*0.6),cxp=P.x-Math.cos(cy)*camD*cp-Math.sin(cy)*sh+sx,czp=P.y-Math.sin(cy)*camD*cp+Math.cos(cy)*sh;
 cam3.position.set(cxp,Math.max(py+Hc+camD*sn+(Dw-camD)*0.35+sx,(GT&&gReady?py:Hat(cxp,czp))+7),czp);
 const lf=AIM?90:(P.car?38:30);if(MENU)CAMO=menuCam();if(DBGC)CAMO=DBGC;if(CAMO){cam3.position.set(CAMO[0],CAMO[1],CAMO[2]);cam3.lookAt(CAMO[3],CAMO[4],CAMO[5]);}else cam3.lookAt(P.x+Math.cos(cy)*lf-Math.sin(cy)*sh,py+Hc-(AIM?0:2)-sn*lf*0.25,P.y+Math.sin(cy)*lf+Math.cos(cy)*sh);
 const bf=(W<H?66:56)-(AIM?12:0),cf=CAMO&&!MENU?(CAMO[6]||42)*(W<H?1.5:1):0,tf=cf||bf+clamp(sp/300,0,1)*12;if(Math.abs(cam3.fov-tf)>0.2){cam3.fov=cf?tf:cam3.fov+(tf-cam3.fov)*0.1;cam3.updateProjectionMatrix();}
 dayNight();sun.target.position.set(Math.round(P.x/20)*20,py,Math.round(P.y/20)*20);sun.position.copy(sun.target.position).addScaledVector(SUNV,2000);
 if(GT){cam3.updateMatrixWorld();GT.update();if(time-gAttrT>2||time<gAttrT){gAttrT=time;const e=document.getElementById('gattr');if(e){const a=GT.getAttributions().filter(q=>q.type==='string').map(q=>q.value).join('; ');e.textContent='Google'+(a?' · '+a:'');}}}
 drawFrame();audioStep();
 g.setTransform(DPR,0,0,DPR,0,0);g.clearRect(0,0,W,H);
 if(rain){g.fillStyle='rgba(40,50,70,.16)';g.fillRect(0,0,W,H);g.strokeStyle='rgba(215,225,240,.4)';g.lineWidth=1;g.beginPath();for(let i=0;i<70;i++){const x=(h2(i,7)*W+time*90)%W,y=(h2(i,13)*H+time*(700+h2(i,3)*300))%H;g.moveTo(x,y);g.lineTo(x+3,y+14);}g.stroke();}
 if(P.flash>0){g.fillStyle='rgba(200,0,0,'+P.flash+')';g.fillRect(0,0,W,H);}
 hud();
}
const _bv=new THREE.Vector3();
function hud(){
 if(MENU)return;if(CUT){drawCut();return;}
 if(barks.length){g.textAlign='center';g.textBaseline='bottom';g.font='bold 13px system-ui,sans-serif';for(const b of barks){_bv.set(b.p.x,Hg(b.p.x,b.p.y)+26,b.p.y).project(cam3);if(_bv.z>1||_bv.z<-1)continue;const x=(_bv.x*0.5+0.5)*W,y=(-_bv.y*0.5+0.5)*H;g.globalAlpha=clamp(b.time,0,1);g.lineWidth=4;g.lineJoin='round';g.strokeStyle='rgba(0,0,0,.85)';g.strokeText(b.t,x,y);g.fillStyle='#fff';g.fillText(b.t,x,y);g.globalAlpha=1;}}
 const mr=Math.min(56,W*0.14),mx=12+mr,my=12+mr;
 // minimap
 g.save();g.beginPath();g.arc(mx,my,mr,0,7);g.clip();g.fillStyle='#16303f';g.fillRect(mx-mr,my-mr,mr*2,mr*2);
 const span=95,k=mr/span;g.imageSmoothingEnabled=true;if(GT&&OOB(P.x,P.y))countyMini(mx,my,mr);else g.drawImage(mm,P.x/T-span,P.y/T-span,span*2,span*2,mx-mr,my-mr,mr*2,mr*2);
 const blip=(x,y,c,r)=>{let dx=(x-P.x)/T*k,dy=(y-P.y)/T*k;const d=Math.hypot(dx,dy);if(d>mr-4){dx*=(mr-4)/d;dy*=(mr-4)/d;}g.fillStyle=c;g.beginPath();g.arc(mx+dx,my+dy,r,0,7);g.fill();};
 for(const c of cars)if(c.drv==='cop'&&stars>0&&dist(c.x,c.y,P.x,P.y)<span*T/k*mr/ mr)blip(c.x,c.y,Math.floor(time*5)%2?'#ff4040':'#4a7dff',3);
 if(MODE==='story'&&!M&&ST<STORY.length){const sc=STORY[ST];blip(sc.gx,sc.gy,'#fff',5);blip(sc.gx,sc.gy,'#40e0ff',3.8);}
 if(!M)for(const gv of GV)blip(gv.x,gv.y,gv.type==='race'?'#ff5ad0':'#ffd23f',3.5);
 for(const p of PKG)if(!pkgGot[p.i]&&Math.abs(p.x-P.x)+Math.abs(p.y-P.y)<span*T*1.3)blip(p.x,p.y,'#40e0ff',2.5);
 blip(SHOP.door.x,SHOP.door.y,'#ff8a30',2.5);blip(PAWN.curb.x,PAWN.curb.y,'#7ad06a',2.5);blip(HOSP.curb.x,HOSP.curb.y,'#ff5a6a',2.5);
 if(M&&!M.hide)blip(M.tx,M.ty,'#fff',4.5),blip(M.tx,M.ty,'#ffb300',3);
 g.restore();g.strokeStyle='#0b0e12';g.lineWidth=3;g.beginPath();g.arc(mx,my,mr,0,7);g.stroke();
 g.save();g.translate(mx,my);g.rotate(P.a);g.fillStyle='#fff';g.beginPath();g.moveTo(6,0);g.lineTo(-4,-4);g.lineTo(-4,4);g.fill();g.restore();
 // stats (top right)
 const F=z=>'italic 900 '+z+'px "Arial Black",Impact,system-ui,sans-serif',ot=(t,x,y,c)=>{g.lineWidth=4;g.lineJoin='round';g.strokeStyle='#000';g.strokeText(t,x,y);g.fillStyle=c;g.fillText(t,x,y);};
 const rx=W-12,gm=gmin(),ch_=Math.floor(gm/60),cm=Math.floor(gm%60);g.textAlign='right';g.textBaseline='top';
 g.font=F(22);ot((ch_<10?'0':'')+ch_+':'+(cm<10?'0':'')+cm,rx,8,'#e6dcc2');ot('$'+String(P.money).padStart(8,'0'),rx,34,'#43b04e');
 ot('\u2665'+String(Math.max(0,Math.ceil(P.hp))).padStart(3,'0'),rx,60,P.hp>35?'#e2553c':'#ff9a2e');
 g.font=F(14);ot(P.car?'CAR '+Math.max(0,Math.round(P.car.hp/P.car.mhp*100))+'%':(P.ammo>0?WSPEC[P.wp].n+' '+P.ammo:'FISTS'),rx,90,'#d8c88a');
 if(!P.car&&P.stam!=null&&P.stam<0.995){g.fillStyle='rgba(0,0,0,.55)';g.fillRect(rx-104,136,104,6);g.fillStyle='#e8d24a';g.fillRect(rx-102,137.5,100*P.stam,3);}
 if(AIM&&!P.car){g.strokeStyle='rgba(255,255,255,.9)';g.lineWidth=2;const cx_=W/2,cy_=H*0.45;g.beginPath();g.moveTo(cx_-11,cy_);g.lineTo(cx_-4,cy_);g.moveTo(cx_+4,cy_);g.lineTo(cx_+11,cy_);g.moveTo(cx_,cy_-11);g.lineTo(cx_,cy_-4);g.moveTo(cx_,cy_+4);g.lineTo(cx_,cy_+11);g.stroke();}
 g.font='22px system-ui,sans-serif';for(let i=0;i<5;i++){const on=i<stars;if(!on&&!stars)continue;ot('\u2605',rx-i*22,108,on?((cool>4&&Math.floor(time*4)%2)?'#6a5a1a':'#ffd23f'):'#2a2a2a');}
 // location
 const loc=STREET||'Everett';
 if(loc!==hud.loc){hud.loc=loc;hud.until=time+4;}
 if(time<hud.until){g.globalAlpha=clamp(hud.until-time,0,1);g.textAlign='center';g.textBaseline='bottom';g.font=F(20);ot(loc,W/2,H-14,'#d9c9a0');g.globalAlpha=1;}
 // mission
 let ty=my+mr+50;g.textBaseline='top';
 if(M){g.font='bold 14px system-ui,sans-serif';const s=M.text+(M.time>0?'  ['+Math.ceil(M.time)+'s]':'');wrap(s,W/2,ty,W-28,(M.time>0&&M.time<10)?'#ff6b5a':'#ffe08a');
  // arrow
  const dx=M.tx-P.x,dy=M.ty-P.y,d=Math.hypot(dx,dy);if(d>110){const a=Math.atan2(dy,dx)-yaw-PI/2,r=Math.min(W,H)*0.28;g.save();g.translate(W/2+Math.cos(a)*r,H*0.42+Math.sin(a)*r);g.rotate(a);g.fillStyle='#ffd23f';g.strokeStyle='#000';g.lineWidth=2;g.beginPath();g.moveTo(14,0);g.lineTo(-8,-9);g.lineTo(-8,9);g.closePath();g.fill();g.stroke();g.restore();}
  ty+=40;}
 if(toast){g.font='bold 14px system-ui,sans-serif';wrap(toast.t,W/2,H-70,W-28,'#fff');}
 if(big){g.font='900 '+Math.min(54,W/9)+'px system-ui,sans-serif';g.textAlign='center';g.textBaseline='middle';g.fillStyle='#000';g.fillText(big.t,W/2+3,H*0.38+3);g.fillStyle=big.c;g.fillText(big.t,W/2,H*0.38);}
 if(joy.on){g.strokeStyle='rgba(255,255,255,.35)';g.lineWidth=3;g.beginPath();g.arc(joy.ox,joy.oy,52,0,7);g.stroke();g.fillStyle='rgba(255,255,255,.4)';g.beginPath();g.arc(joy.ox+joy.x*52,joy.oy+joy.y*52,22,0,7);g.fill();}
}
function wrap(s,x,y,w,c){g.textAlign='center';const ws=s.split(' ');let ln='',ls=[];for(const wd of ws){const t=ln?ln+' '+wd:wd;if(g.measureText(t).width>w&&ln){ls.push(ln);ln=wd;}else ln=t;}ls.push(ln);ls.forEach((l,i)=>{g.fillStyle='rgba(0,0,0,.8)';g.fillText(l,x+1,y+i*18+1);g.fillStyle=c;g.fillText(l,x,y+i*18);});}
const MMC=[[38,78,104],[70,96,66],[150,154,160],[112,116,120],[58,62,70],[52,120,60],[98,102,108]];
function buildMini(){mm=document.createElement('canvas');mm.width=MW;mm.height=MH;const c=mm.getContext('2d'),im=c.createImageData(MW,MH),d=im.data;for(let i=0;i<MW*MH;i++){const q=MMC[map[i]]||MMC[1];d[i*4]=q[0];d[i*4+1]=q[1];d[i*4+2]=q[2];d[i*4+3]=255;}c.putImageData(im,0,0);}
function buildBig(){if(bigmap)return bigmap;bigmap=document.createElement('canvas');const BW=1800,BH=Math.round(BW*WH/WW);bigmap.width=BW;bigmap.height=BH;const c=bigmap.getContext('2d');c.drawImage(mm,0,0,BW,BH);
 for(let ty=0;ty<2;ty++)for(let tx=0;tx<3;tx++){const im=AIRIMG[ty*3+tx];if(im)c.drawImage(im,tx*BW/3,ty*BH/2,BW/3+1,BH/2+1);}
 c.textAlign='center';c.textBaseline='middle';c.font='bold 11px system-ui,sans-serif';c.lineJoin='round';
 const done=new Set();edges.forEach((e,key)=>{const a=Math.floor(key/65536),b=key%65536;if(a>b||e.cls>6||done.has(e.name))return;const A=nodes[a],B=nodes[b];if(dist(A.x,A.y,B.x,B.y)<500)return;done.add(e.name);const x=(A.x+B.x)/2/WW*BW,y=(A.y+B.y)/2/WH*BH;c.save();c.translate(x,y);let an=Math.atan2(B.y-A.y,B.x-A.x);if(an>PI/2||an<-PI/2)an+=PI;c.rotate(an);c.lineWidth=3;c.strokeStyle='rgba(0,0,0,.8)';c.strokeText(e.name,0,0);c.fillStyle='#ffe9a0';c.fillText(e.name,0,0);c.restore();});
 for(const l of LM){if(l.t!=='lm'&&l.t!=='police'&&l.t!=='park')continue;const x=l.cx/WW*BW,y=l.cy/WH*BH;c.lineWidth=3;c.strokeStyle='rgba(0,0,0,.85)';c.strokeText(l.n,x,y);c.fillStyle=l.t==='park'?'#b8f0b0':'#fff';c.fillText(l.n,x,y);}
 c.font='10px system-ui,sans-serif';c.textAlign='right';c.fillStyle='#fff';c.strokeStyle='#000';const cr=window.EV_NOAIR?'Map data: City of Everett GIS':'Data & imagery: City of Everett GIS; imagery © EagleView / Snohomish County / City of Everett';c.strokeText(cr,BW-8,BH-10);c.fillText(cr,BW-8,BH-10);
 return bigmap;}

/* ---------- BOOT ---------- */
function reset(){cars=[];peds=[];fx=[];picks=[];stains=[];pts=0;stars=0;M=null;for(const s of SPOTS){s.on=false;s.taken=false;}
 const s=lm('Everett Station');P.x=s.curb.x+T*5;P.y=s.curb.y;if(solidAt(P.x,P.y)){P.x=s.door.x;P.y=s.door.y;}P.hp=100;P.car=null;P.dead=0;cam.x=P.x;cam.y=P.y;yaw=PI;
 streamSpots(true);for(let i=0;i<(LOW?12:22);i++)spawnTraffic(i===3?'taxi':i===7?'bus':'civ',true);for(let i=0;i<(LOW?10:22);i++)spawnPed(true);}
function resize(){DPR=Math.min(window.devicePixelRatio||1,2);W=window.innerWidth;H=window.innerHeight;hc.width=W*DPR;hc.height=H*DPR;ren.setPixelRatio(Math.min(window.devicePixelRatio||1,LOW?1.25:2));ren.setSize(W,H,false);cam3.aspect=W/H;cam3.fov=W<H?66:56;cam3.updateProjectionMatrix();}
let last=0;
let fpsN=0,fpsT=0,qual=2;
function frame(t){const raw=(t-last)/1000||0,dt=Math.min(0.05,raw);last=t;if(!paused){{let rem=Math.min(0.15,raw||0.016);while(rem>1e-4){const d=Math.min(0.05,rem);update(P.dead>0?d*0.45:d);rem-=d;}}fpsN++;fpsT+=raw;if(fpsT>4){const f=fpsN/fpsT;fpsN=0;fpsT=0;if(f<25&&qual>0&&!window.EV_NOADAPT){qual--;if(qual===1){sun.castShadow=false;}else{ren.setPixelRatio(1);ren.setSize(W,H,false);}}}}render();requestAnimationFrame(frame);}
async function boot(){
 cv=document.getElementById('c');hc=document.getElementById('h');g=hc.getContext('2d');const sb=document.getElementById('start');sb.disabled=true;
 init3D();resize();window.addEventListener('resize',resize);
 await loadAssets((d,n)=>{sb.textContent='LOADING '+Math.round(d/n*100)+'%';});
 initPlaces();await loadStory();try{COUNTY=await (await fetch('data/county.json')).json();}catch(e){}buildStatic();initMarkers();buildMini();reset();sb.textContent='START';sb.disabled=false;
 const $=id=>document.getElementById(id);
 window.addEventListener('keydown',e=>{if(e.code==='Space'&&!keys.Space)jumpTap=true;keys[e.code]=true;if(!e.repeat){if(e.code==='KeyE'||e.code==='KeyF'||e.code==='Enter')useBtn();if(e.code==='KeyM')toggleMap();if(e.code==='KeyQ')nextWeapon();}if(e.code.startsWith('Arrow')||e.code==='Space')e.preventDefault();});
 window.addEventListener('keyup',e=>{keys[e.code]=false;});
 // touch: left half is the move stick, right half drags the camera
 hc.addEventListener('pointerdown',e=>{if(e.pointerType==='mouse'){const lk=document.pointerLockElement===hc;if(e.button===0)mouseFire=lk||noLock;if(e.button===2){mouseAim=true;mouseDown=true;}if(!paused&&!lk&&!noLock){if(hc.requestPointerLock){try{const r=hc.requestPointerLock();if(r&&r.catch)r.catch(()=>{noLock=true;});}catch(_){noLock=true;}}else noLock=true;}return;}
  usedTouch=true;if(e.clientX<W*0.5){if(!joy.on){joy.on=true;joy.id=e.pointerId;joy.ox=e.clientX;joy.oy=e.clientY;joy.x=joy.y=0;}}else if(lookTouch.id<0){lookTouch.id=e.pointerId;lookTouch.x=e.clientX;lookTouch.y=e.clientY;}e.preventDefault();});
 hc.addEventListener('contextmenu',e=>e.preventDefault());
 window.addEventListener('mousemove',e=>{if(document.pointerLockElement===hc||mouseDown){lookDX+=e.movementX||0;lookDY+=e.movementY||0;}});
 window.addEventListener('mouseup',e=>{mouseDown=false;if(e.button===0)mouseFire=false;if(e.button===2)mouseAim=false;});
 window.addEventListener('wheel',e=>{if(!paused&&!P.car)nextWeapon();},{passive:true});
 const mv=e=>{if(joy.on&&e.pointerId===joy.id){let dx=(e.clientX-joy.ox)/52,dy=(e.clientY-joy.oy)/52;const m=Math.hypot(dx,dy);if(m>1){dx/=m;dy/=m;}joy.x=dx;joy.y=dy;}
  else if(e.pointerId===lookTouch.id){lookDX+=(e.clientX-lookTouch.x)*2.2;lookDY+=(e.clientY-lookTouch.y)*1.6;lookTouch.x=e.clientX;lookTouch.y=e.clientY;}};
 const up=e=>{if(e.pointerId===joy.id){joy.on=false;joy.id=-1;joy.x=joy.y=0;}if(e.pointerId===lookTouch.id)lookTouch.id=-1;};
 window.addEventListener('pointermove',mv);window.addEventListener('pointerup',up);window.addEventListener('pointercancel',up);
 $('jump').addEventListener('pointerdown',e=>{jumpTap=true;e.preventDefault();});
 $('run').addEventListener('pointerdown',e=>{runHeld=!runHeld;$('run').style.background=runHeld?'rgba(232,210,74,.45)':'';e.preventDefault();});
 const fb=$('fire'),ub=$('use');
 fb.addEventListener('pointerdown',e=>{fireHeld=true;e.preventDefault();});['pointerup','pointercancel','pointerleave'].forEach(n=>fb.addEventListener(n,()=>{fireHeld=false;}));
 ub.addEventListener('pointerdown',e=>{useBtn();e.preventDefault();});
 $('wpn').addEventListener('pointerdown',e=>{nextWeapon();e.preventDefault();});
 $('gon').addEventListener('click',()=>{const k=$('gkey').value.trim()||(location.hostname==='cbgregg.github.io'?'AIzaSyCMqLVWaLUmddEWfl7vAkAL26TbuepnMSw':'');if(k){$('gkey').value=k;try{localStorage.setItem('everett_gon2','1');}catch(e){}enableGoogleTiles(k);}});$('goff').addEventListener('click',disableGoogleTiles);if($('travgo'))$('travgo').addEventListener('click',()=>{const v=$('trav').value;if(v&&travel(v))toggleMap();});
 {const b=document.createElement('div');b.id='bld';b.style.cssText='font-size:11px;color:#7f97a6;margin-top:14px';$('intro').appendChild(b);setInterval(()=>{b.textContent='Build '+BUILD+' · Google 3D: '+(GT&&gReady?'ON (bridges, freeway and county travel active)':GT?'loading…':'OFF (downtown only)');},500);}
 /* Built-in key: locked by Google to this site's address and to the Map Tiles API, so it is safe to ship. */
 try{const own=location.hostname==='cbgregg.github.io',k=localStorage.getItem('everett_gon2')?(localStorage.getItem('everett_gkey')||(own?'AIzaSyCMqLVWaLUmddEWfl7vAkAL26TbuepnMSw':'')):'';if(k){$('gkey').value=k;enableGoogleTiles(k);}}catch(e){}
 $('mapb').addEventListener('click',toggleMap);$('resume').addEventListener('click',toggleMap);
 $('start').addEventListener('click',()=>startStoryMode(false));if($('newstory'))$('newstory').addEventListener('click',()=>startStoryMode(true));if($('freeplay'))$('freeplay').addEventListener('click',startFree);
 if($('ctrlb'))$('ctrlb').addEventListener('click',()=>{$('menu').style.display='none';$('ctrl').style.display='block';});if($('ctrlx'))$('ctrlx').addEventListener('click',()=>{$('ctrl').style.display='none';$('menu').style.display='';});if($('tomenu'))$('tomenu').addEventListener('click',toMenu);
 $('intro').addEventListener('pointerdown',()=>{initAudio();if(AC&&AC.resume)AC.resume();});
 window.addEventListener('pointerdown',()=>{if(CUT&&CUT.T>0.7)skipTap=true;});window.addEventListener('keydown',e=>{if(CUT&&CUT.T>0.7&&(e.code==='Space'||e.code==='Enter'||e.code==='Escape'))skipTap=true;});
 document.body.classList.add('menu');for(const id of ['freeplay','newstory','ctrlb'])if($(id))$(id).disabled=false;updateMenu();
 $('snd').addEventListener('click',()=>{sndOn=!sndOn;$('snd').textContent='Sound: '+(sndOn?'on':'off');});
 $('newgame').addEventListener('click',()=>{P.money=0;P.am={pistol:24,smg:0,shotgun:0,rifle:0};P.own={pistol:true};P.wp='pistol';pkgGot={};ST=0;saveStory();try{localStorage.removeItem('everett_pk');}catch(e){}save();reset();toggleMap();});
 setInterval(()=>{ub.textContent=P.car?'EXIT':'ENTER';ub.style.opacity=(P.car||nearCar())?1:0.45;fb.textContent=P.car?'BRAKE':(P.ammo>0?'FIRE':'PUNCH');$('jump').style.display=$('run').style.display=(usedTouch&&!P.car)?'':'none';$('wpn').style.display=(!P.car&&(P.own.smg||P.own.shotgun||P.own.rifle))?'':'none';},200);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)for(const k in keys)keys[k]=false;});
 // PDF of the map via downloads capability
 const pb=$('pdf'),ps=$('pdfmsg');let dl=null;
 if(window.claude&&window.claude.use)window.claude.use('downloads').then(d=>{dl=d;if(d)pb.style.display='';}).catch(()=>{});
 else{dl={save:async({filename,data})=>{const a=document.createElement('a');a.href=URL.createObjectURL(data);a.download=filename;a.click();}};pb.style.display='';}
 pb.addEventListener('click',async()=>{if(!dl||!window.jspdf){ps.textContent='PDF export is not available in this view.';return;}
  try{const doc=new window.jspdf.jsPDF({orientation:'landscape',unit:'pt',format:'letter'});doc.setFontSize(16);doc.text('Downtown Everett - game map (City of Everett GIS data, 2022 aerial)',36,40);const b=buildBig();doc.addImage(b.toDataURL('image/jpeg',0.92),'JPEG',36,56,720,720*b.height/b.width);
   await dl.save({filename:'downtown-everett-map.pdf',data:doc.output('blob')});ps.textContent='Saved.';}catch(e){ps.textContent=e&&e.code==='declined'?'':'Could not save the PDF here.';}});
 requestAnimationFrame(frame);
}
function toggleMap(){const o=document.getElementById('mapov');if(document.getElementById('intro').style.display!=='none')return;const open=o.style.display==='none';o.style.display=open?'flex':'none';paused=open;
 if(open){const b=buildBig(),c=document.getElementById('mapc');c.width=b.width;c.height=b.height;const x=c.getContext('2d');x.drawImage(b,0,0);
  const dot=(px,py,col,r)=>{x.fillStyle=col;x.strokeStyle='#000';x.lineWidth=2;x.beginPath();x.arc(px/WW*b.width,py/WH*b.height,r,0,7);x.fill();x.stroke();};
  GV.forEach(gv=>dot(gv.x,gv.y,gv.type==='race'?'#ff5ad0':'#ffd23f',7));dot(SHOP.door.x,SHOP.door.y,'#ff8a30',6);dot(PAWN.curb.x,PAWN.curb.y,'#7ad06a',6);dot(HOSP.curb.x,HOSP.curb.y,'#ff5a6a',6);for(const p of PKG)if(!pkgGot[p.i])dot(p.x,p.y,'#40e0ff',4);if(M)dot(M.tx,M.ty,'#ffb300',9);dot(P.x,P.y,'#e02020',8);
  {const cm=document.getElementById('cmap');if(cm){buildCounty();cm.style.display=CW?'block':'none';if(CW)drawCountyMap(cm);}}
  document.getElementById('pkc').textContent='Packages '+Object.keys(pkgGot).length+'/'+PKG.length;
  const w=document.getElementById('mapwrap');w.scrollLeft=P.x/WW*c.clientWidth-w.clientWidth/2;{const cm=document.getElementById('cmap'),ch=cm&&cm.style.display!=='none'?cm.clientHeight+12:0;w.scrollTop=OOB(P.x,P.y)?0:ch+P.y/WH*c.clientHeight-w.clientHeight/2;}}}
window.G={stats:()=>{ren.info.autoReset=false;ren.info.reset();render();const r={tri:ren.info.render.triangles,calls:ren.info.render.calls,qual};ren.info.autoReset=true;return r;},cam:v=>{DBGC=v;if(!v)CAMO=null;},vo,voxLevel,setHour:h=>{TOFF=((h*60-540-time)%1440+1440)%1440;},setShow,setHide,gtStats:()=>GT&&GT.stats,boot,update,render,P,nextWeapon,makePed,get GV(){return GV;},nodes,get LM(){return LM;},get map(){return map;},Hat,get STOPS(){return STOPS;},get SPOTS(){return SPOTS;},makeCar,tileAt,get cars(){return cars;},get peds(){return peds;},useBtn,crime,startMission,setPaused:v=>paused=v,shoot,tile,solidAt,get M(){return M;},get stars(){return stars;},VSPEC,GUN,SND,get STORY(){return STORY;},get ST(){return ST;},set ST(v){ST=v;syncStoryPed();},get CONTACTS(){return CONTACTS;},setPts:v=>{pts=v;cool=0;},lm,missionStep,travel,startStoryMode,startFree,toMenu,get CUT(){return CUT;},get MODE(){return MODE;},get MENU(){return MENU;},skip:()=>{skipTap=true;},OOB,get CW(){return CW;},get gReady(){return gReady;},gCast};
boot();
