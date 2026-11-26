"""Stills of data/city.glb through tools/preview.html (headless Chrome via Playwright).
  python3 tools/shot.py OUT.png "p=15600,300,12700&t=15600,80,11900" [glb path relative to tools/] [width height]"""
import sys, os, subprocess, time
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out, qs = sys.argv[1], sys.argv[2]
glb = sys.argv[3] if len(sys.argv) > 3 else '../data/city.glb'
w, h = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (1600, 900)
srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8765', '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = b.new_page(viewport={'width': w, 'height': h})
        pg.on('console', lambda m: print('console:', m.text) if m.type == 'error' else None)
        for i, q in enumerate(qs.split('|')):
            pg.goto('http://127.0.0.1:8765/tools/preview.html?glb=%s&%s' % (glb, q))
            pg.wait_for_function('window.READY', timeout=180000)
            o = out if '|' not in qs else out.replace('.', '_%d.' % i, 1) if out.count('.') == 1 else out
            pg.screenshot(path=o)
            print(o, pg.evaluate('window.READY'))
        b.close()
finally:
    srv.terminate()
