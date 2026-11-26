"""Stills from the real game (not the preview): python3 tools/gshot.py OUT.png "x,y,up,tx,ty,tup[,fov]|..." [hour]
x,y = map position of the camera, up = height above the street there; tx,ty,tup the same for the look-at point."""
import sys, os, subprocess, time
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out, views = sys.argv[1], sys.argv[2].split('|')
hour = sys.argv[3] if len(sys.argv) > 3 else '13'
srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8767', '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'])
        pg = b.new_page(viewport={'width': 1600, 'height': 900})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
        pg.on('console', lambda m: errs.append(m.text[:300]) if m.type == 'error' and '404' not in m.text else None)
        pg.add_init_script('window.EV_NOADAPT=1')
        pg.goto('http://127.0.0.1:8767/index.html?nocut&hour=' + hour)
        pg.wait_for_function('window.G && G.P && G.nodes && G.nodes.length', timeout=240000)
        time.sleep(float(os.environ.get('BOOTWAIT', '25')))
        pg.evaluate("document.querySelectorAll('body > *:not(canvas)').forEach(e=>{if(e.tagName!=='SCRIPT'&&!e.querySelector('canvas#c,canvas#gl'))e.style.visibility='hidden'})")
        for i, v in enumerate(views):
            a = [float(t) for t in v.split(',')]
            pg.evaluate("""a=>{const h=(x,y)=>G.Hat(x,y);G.P.x=a[3];G.P.y=a[4];G.cam([a[0],h(a[0],a[1])+a[2],a[1],a[3],h(a[3],a[4])+a[5],a[4],a[6]||55]);}""", a)
            time.sleep(float(os.environ.get('SHOTWAIT', '6')))
            o = out if len(views) == 1 else out.replace('.png', '_%d.png' % i)
            pg.screenshot(path=o); print(o)
        print('stats', pg.evaluate('G.stats()'))
        print('errors:', errs[:6])
        b.close()
finally:
    srv.terminate()
