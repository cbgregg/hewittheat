"""Whole-map pass of the building dossier (see tools/dossier.py): every footprint in data/world.json is joined to its
parcel, LiDAR roofprint and register listing, and its roof colour is read from the county 2024 aerial at 1 ft per pixel.

  python3 tools/dossier_all.py

Writes
  data/dossier/all.json    per footprint: address, parcel, use code, LiDAR height, register name (public record, no owners)
  data/dossier/auto.json   per footprint, what tools/citygen.py applies under the hand-set looks in tools/blocks.py:
      hft     roof height in feet, from LiDAR
      rc      roof colour seen in the aerial (citygen picks the roof material and a tint that renders as this colour)
      lead    the footprint whose walls this one copies (same parcel, touching, similar height: one real building)
      shopon  sides that face a street (commercial and apartment buildings only)
      blank   sides that touch a neighbouring building
Raw downloads are cached in dossier/_all/raw (not committed)."""
import json, math, os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dossier as D

ROOT = D.ROOT
OUT = os.path.join(ROOT, 'dossier', '_all'); CACHE = os.path.join(OUT, 'raw'); os.makedirs(CACHE, exist_ok=True)
W = json.load(open(ROOT + '/data/world.json'))
BLD = W['bld']
ring = lambda f: f['geometry']['rings'][0]
bbox = lambda r: (min(p[0] for p in r), min(p[1] for p in r), max(p[0] for p in r), max(p[1] for p in r))


class Grid:
    def __init__(self, cell):
        self.c = cell; self.d = {}

    def add(self, bb, v):
        for gx in range(int(bb[0] // self.c), int(bb[2] // self.c) + 1):
            for gy in range(int(bb[1] // self.c), int(bb[3] // self.c) + 1):
                self.d.setdefault((gx, gy), []).append(v)

    def near(self, bb):
        s = {}
        for gx in range(int(bb[0] // self.c), int(bb[2] // self.c) + 1):
            for gy in range(int(bb[1] // self.c), int(bb[3] // self.c) + 1):
                for v in self.d.get((gx, gy), ()):
                    s[id(v)] = v
        return list(s.values())


def main():
    cs = [D.w2sp(x, y) for x, y in ((0, 0), (W['wm'] * 10, 0), (W['wm'] * 10, W['hm'] * 10), (0, W['hm'] * 10))]
    env = dict(xmin=min(p[0] for p in cs) - 50, xmax=max(p[0] for p in cs) + 50, ymin=min(p[1] for p in cs) - 50, ymax=max(p[1] for p in cs) + 50)
    L = {}
    for k in ('footprints', 'parcels', 'roofs', 'reg_city', 'reg_state', 'district'):
        L[k] = D.layer(k, env, CACHE); print(k, len(L[k]), flush=True)

    # ---- aerial mosaic at 1 ft per pixel
    e0, n0, e1, n1 = env['xmin'], env['ymin'], env['xmax'], env['ymax']
    mos = os.path.join(CACHE, 'mosaic_2024.jpg')
    if not os.path.exists(mos):
        im = Image.new('RGB', (int(e1 - e0), int(n1 - n0)))
        nx, ny = math.ceil((e1 - e0) / 3000), math.ceil((n1 - n0) / 3000)
        for a in range(nx):
            for b in range(ny):
                ea, eb = e0 + a * 3000, min(e1, e0 + (a + 1) * 3000); na, nb = n0 + b * 3000, min(n1, n0 + (b + 1) * 3000)
                t = D.aerial('2024', ea, na, eb, nb, CACHE, 'm%d_%d' % (a, b), ppf=1)
                im.paste(t.resize((int(eb - ea), int(nb - na))), (int(ea - e0), int(n1 - nb)))
                print('aerial tile', a, b, flush=True)
        im.save(mos, quality=90)
    Image.MAX_IMAGE_PIXELS = None
    M = Image.open(mos); MP = M.load(); MW, MH = M.size

    # ---- indexes
    gp, gr, gh = Grid(300), Grid(300), Grid(300)
    for f in L['parcels']:
        for rg in f['geometry']['rings']:
            gp.add(bbox(rg), (f, rg))
    for f in L['roofs']:
        if f['attributes'].get('ht_95'):
            gr.add(bbox(ring(f)), (f, ring(f), D.area(ring(f))))
    for k in ('reg_city', 'reg_state'):
        for f in L[k]:
            for rg in f['geometry']['rings']:
                gh.add(bbox(rg), (f, rg))
    gc = Grid(300)
    for f in L['footprints']:
        gc.add(bbox(ring(f)), (f, D.cen(ring(f))))
    RW = [[(b[3 + 2 * k], b[4 + 2 * k]) for k in range((len(b) - 3) // 2)] for b in BLD]
    gb = Grid(400)
    for i, rw in enumerate(RW):
        gb.add(bbox(rw), (i, rw))
    ge = Grid(600)
    for e in W['edges']:
        a, b = W['nodes'][e[0]], W['nodes'][e[1]]
        ge.add((min(a[0], b[0]) - 250, min(a[1], b[1]) - 250, max(a[0], b[0]) + 250, max(a[1], b[1]) + 250), e)

    rec, auto = {}, {}
    for i, b in enumerate(BLD):
        rw = RW[i]; rs = [D.w2sp(*p) for p in rw]; bb = bbox(rs); ce, cn = D.cen(rs); A = D.area(rs); kind = b[1]
        R = dict(k=kind)
        m = min(gc.near(bb), key=lambda t: math.hypot(t[1][0] - ce, t[1][1] - cn), default=None)
        if m and math.hypot(m[1][0] - ce, m[1][1] - cn) < 12:
            a = m[0]['attributes']
            R['a'] = ' '.join(str(a[k]).strip() for k in ('ADD_NO', 'HALF', 'ST_PRE', 'ST_NM', 'ST_SUFX', 'ST_POST') if a.get(k) and str(a[k]).strip() not in ('', '0'))
        for f, rg in gp.near(bb):
            if D.pip(ce, cn, rg):
                a = f['attributes']; R['p'] = a['parcel_id']; R['u'] = a['usecode']; R['s'] = a['situsline1']
                break
        step = max(2.0, math.sqrt(A) / 9)
        hs = []
        for f, rg, ra in gr.near(bb):
            mine = D.grid_overlap(rs, rg, step)
            if mine > 0.5 or (mine > 0.02 and D.grid_overlap(rg, rs, max(2.0, math.sqrt(ra) / 9)) > 0.5):
                a = f['attributes']; hs.append((max(mine, 0.05), a['ht_mean'], a['ht_95'], a['ht_max'], ra / max(1.0, A)))
        if hs:
            ws = sum(h[0] for h in hs)
            R['h'] = [round(sum(h[0] * h[1] for h in hs) / ws, 1), round(max(h[2] for h in hs), 1), round(max(h[3] for h in hs), 1)]
            if max(h[4] for h in hs) > 1.6:
                R['hs'] = 1                     # the roofprint also covers neighbours, so the height is a blend
        for f, rg in gh.near(bb):
            if D.pip(ce, cn, rg) or D.pip(*D.cen(rg), rs):
                a = f['attributes']; R['n'] = a.get('NAME'); R['y'] = a.get('Const_Year') or R.get('y')
        # roof colour: median of aerial pixels inside the footprint, pulled in from the walls
        px = []
        st = max(1, int(math.sqrt(A) / 14))
        for yy in range(int(n1 - bb[3]), int(n1 - bb[1]) + 1, st):
            for xx in range(int(bb[0] - e0), int(bb[2] - e0) + 1, st):
                if 0 <= xx < MW and 0 <= yy < MH:
                    e, n = e0 + xx, n1 - yy
                    if D.pip(ce + (e - ce) * 1.3, cn + (n - cn) * 1.3, rs):
                        px.append(MP[xx, yy])
        if len(px) >= 4:
            px.sort(key=lambda p: sum(p)); R['c'] = '#%02x%02x%02x' % px[len(px) // 2]
        rec[i] = R

        # ---- what citygen applies
        Au = {}
        if 'h' in R:
            mean, p95 = R['h'][0], R['h'][1]
            if kind in (0, 3):
                hft = min(p95, mean * 1.35 + 2)          # ridge height; trees over a house inflate the top percentiles
                if 8 <= hft <= 48:
                    Au['hft'] = round(hft, 1)
            elif mean >= 8:
                Au['hft'] = round(mean + (3 if mean > 14 else 1), 1)
        if 'c' in R:
            r_, g_, b_ = [int(R['c'][k:k + 2], 16) for k in (1, 3, 5)]
            lum = 0.3 * r_ + 0.59 * g_ + 0.11 * b_
            green = g_ > r_ * 1.10 and g_ > b_ * 1.10      # tree canopy over the roof: leave the colour alone
            if not green and lum > 28:
                Au['rc'] = R['c']
        if kind not in (0, 3):
            cx, cy = D.cen(rw)
            # orientation, so the outward side of each wall is known
            s2 = sum(rw[k][0] * rw[(k + 1) % len(rw)][1] - rw[(k + 1) % len(rw)][0] * rw[k][1] for k in range(len(rw)))
            front, party, tot = {}, {}, {}
            nb = [t for t in gb.near(bbox(rw)) if t[0] != i]
            ed = ge.near(bbox(rw))
            for k in range(len(rw)):
                (x1, y1), (x2, y2) = rw[k], rw[(k + 1) % len(rw)]
                ln = math.hypot(x2 - x1, y2 - y1)
                if ln < 25:
                    continue
                ox, oy = (y2 - y1) / ln, -(x2 - x1) / ln
                if s2 < 0:
                    ox, oy = -ox, -oy
                side = ('E' if ox > 0 else 'W') if abs(ox) > abs(oy) else ('S' if oy > 0 else 'N')
                tot[side] = tot.get(side, 0) + ln
                # party wall: points just outside the wall fall inside another footprint
                hit = 0
                for t in (0.2, 0.5, 0.8):
                    qx, qy = x1 + (x2 - x1) * t + ox * 14, y1 + (y2 - y1) * t + oy * 14
                    hit += any(D.pip(qx, qy, r2) for _, r2 in nb)
                if hit >= 2:
                    party[side] = party.get(side, 0) + ln
                    continue
                # street front: a street running along this wall within 26 m with nothing in between
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                for e in ed:
                    a_, b_2 = W['nodes'][e[0]], W['nodes'][e[1]]; dx, dy = b_2[0] - a_[0], b_2[1] - a_[1]; L2 = dx * dx + dy * dy or 1
                    t = ((mx - a_[0]) * dx + (my - a_[1]) * dy) / L2
                    if not 0 <= t <= 1:
                        continue
                    px_, py_ = a_[0] + t * dx, a_[1] + t * dy; d = math.hypot(mx - px_, my - py_)
                    if d < 260 and (px_ - mx) * ox + (py_ - my) * oy > 0.6 * d and abs(dx * (x2 - x1) + dy * (y2 - y1)) / math.sqrt(L2) / ln > 0.8:
                        if not any(D.pip(mx + (px_ - mx) * 0.5, my + (py_ - my) * 0.5, r2) for _, r2 in nb):
                            front[side] = front.get(side, 0) + ln
                            break
            Au['shopon'] = ''.join(s for s in 'NESW' if front.get(s, 0) > 0.4 * tot.get(s, 1))
            bl = ''.join(s for s in 'NESW' if party.get(s, 0) > 0.6 * tot.get(s, 1) and s not in Au['shopon'])
            if bl:
                Au['blank'] = bl
        auto[i] = Au
        if i % 800 == 0:
            print(i, flush=True)

    # ---- one real building = touching footprints on one parcel at about the same height (not houses)
    lead = list(range(len(BLD)))

    def find(a):
        while lead[a] != a:
            lead[a] = lead[lead[a]]; a = lead[a]
        return a
    for i, rw in enumerate(RW):
        if BLD[i][1] in (0, 3) or 'p' not in rec[i] or 'h' not in rec[i]:
            continue
        for j, r2 in gb.near(bbox(rw)):
            if j <= i or BLD[j][1] in (0, 3) or rec[j].get('p') != rec[i]['p'] or 'h' not in rec[j] or abs(rec[j]['h'][0] - rec[i]['h'][0]) > 6:
                continue
            touch = sum(1 for p in rw for k in range(len(r2)) if _seg_d(p, r2[k], r2[(k + 1) % len(r2)]) < 6)
            if touch >= 2:
                lead[find(j)] = find(i)
    groups = {}
    for i in range(len(BLD)):
        groups.setdefault(find(i), []).append(i)
    ng = 0
    for g in groups.values():
        if len(g) > 1:
            ng += 1
            big = max(g, key=lambda q: D.area(RW[q]))
            hft = max((auto[q].get('hft', 0) for q in g), default=0)
            for q in g:
                if q != big:
                    auto[q]['lead'] = big
                if hft:
                    auto[q]['hft'] = hft
                for k in ('rc',):
                    if k in auto[big]:
                        auto[q][k] = auto[big][k]
    os.makedirs(ROOT + '/data/dossier', exist_ok=True)
    json.dump(dict(source='City of Everett GIS; Snohomish County Assessor and GIS (parcels, LiDAR roofprints); roof colour from the county 2024 aerial',
                   keys=dict(k='kind', a='address', p='parcel', u='assessor use code', s='situs', h='LiDAR roof height ft [mean, 95th, max]', hs='height shared with neighbours',
                             n='register name', y='built', c='roof colour'), buildings=rec), open(ROOT + '/data/dossier/all.json', 'w'), separators=(',', ':'))
    json.dump(auto, open(ROOT + '/data/dossier/auto.json', 'w'), separators=(',', ':'))
    n = len(BLD)
    print('footprints', n, '| height', sum('hft' in a for a in auto.values()), '| roof colour', sum('rc' in a for a in auto.values()),
          '| parcel', sum('p' in r for r in rec.values()), '| address', sum('a' in r for r in rec.values()),
          '| multi-footprint buildings', ng, 'covering', sum(len(g) for g in groups.values() if len(g) > 1),
          '| no LiDAR', sum('h' not in r for r in rec.values()), '| LiDAR under 8 ft', sum(1 for r in rec.values() if 'h' in r and r['h'][0] < 8))


def _seg_d(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy or 1
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


if __name__ == '__main__':
    main()
