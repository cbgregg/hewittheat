"""Builds the whole downtown as one textured model (data/city.glb) from the City of Everett
footprints in data/world.json. Materials reference the Blender-rendered textures in tex/b/.
The same file is loaded by the game and imported into Blender for renders."""
import json, math, random, struct, sys
from PIL import Image

REPO = sys.argv[1]
OUT = sys.argv[2]
W = json.load(open(REPO + '/data/world.json'))
GS = W['gs'] * 10
gw, gh = W['gw'], W['gh']
hm = Image.open(REPO + '/data/hm.png').convert('RGBA')
hp = hm.load()
HM = [[((hp[x, y][0] << 8) | hp[x, y][1]) - 1000 for x in range(gw)] for y in range(gh)]


def Hat(x, y):
    fx = min(max(x / GS, 0), gw - 1.001)
    fy = min(max(y / GS, 0), gh - 1.001)
    ix, iy = int(fx), int(fy)
    ax, ay = fx - ix, fy - iy
    return (HM[iy][ix] * (1 - ax) + HM[iy][ix + 1] * ax) * (1 - ay) + (HM[iy + 1][ix] * (1 - ax) + HM[iy + 1][ix + 1] * ax) * ay


def lin(h, k=1.0):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(min(1.0, (((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4)) * k) for x in c)


WHITE = (1, 1, 1)
# name: tile U, tile V (world units, 10 = 1 m), bays per tile, floors per tile, blank width, continuous
FAC = {
    'f_brick_red': (80, 66, 2, 2, 24, False), 'f_brick_buff': (80, 66, 3, 2, 13, False), 'f_brick_dark': (80, 64, 2, 2, 13, False),
    'f_concrete': (80, 70, 2, 2, 6, False), 'f_glass': (60, 72, 4, 2, 0, False), 'f_panel': (80, 62, 2, 2, 5, False),
    'f_stucco': (80, 64, 2, 2, 25, False), 'f_siding': (46, 30, 1, 1, 30, False), 'f_garage': (80, 30, 1, 1, 0, False),
    'f_metal': (64, 64, 1, 1, 0, True), 'f_cmu': (64, 64, 1, 1, 0, True), 'f_lap': (32, 32, 1, 1, 0, True),
}
ROOF = {'r_membrane': 64, 'r_gravel': 64, 'r_shingle': 64, 'r_seam': 64, 'r_parking': 0, 'r_dome': 0}
SHOPS = ['shop_brick', 'shop_modern', 'shop_buff']

HOUSE = [('#8c9096', 9), ('#6f757c', 7), ('#a7abae', 7), ('#6f8aa3', 6), ('#8fa6b5', 5), ('#4f6b85', 3), ('#e6e2d6', 9), ('#d9d4c4', 7),
         ('#b9a88c', 6), ('#9a8a6f', 4), ('#7d8c75', 4), ('#5f7060', 3), ('#5fb7b0', 1), ('#d9c36a', 2), ('#8a4a3c', 2), ('#4a4d52', 3), ('#c9b7a0', 3)]
HROOF = [('#565a60', 45), ('#7b7e82', 25), ('#6b584c', 15), ('#9a9c9e', 10), ('#7e4a40', 5)]
PASTEL = [('#eceae4', 8), ('#d9d4c4', 6), ('#c9c7c1', 6), ('#b8bcc0', 4), ('#e3d2b5', 3), ('#bfd0d6', 2), ('#d6b9a6', 2), ('#a9b9a4', 2), ('#8f979e', 3)]
INDC = [('#e6e6e2', 8), ('#c9cbcc', 6), ('#d6cbb4', 3), ('#9fb0bd', 3), ('#7fa79b', 2), ('#aab0b5', 4)]
BRICKT = [(1, 1, 1), (0.9, 0.86, 0.86), (1.0, 0.93, 0.86), (0.78, 0.74, 0.74), (1.0, 0.98, 0.92)]


def pick(r, table):
    t = sum(w for _, w in table)
    x = r.random() * t
    for v, w in table:
        x -= w
        if x <= 0:
            return v
    return table[-1][0]


class Bufs:
    def __init__(self):
        self.b = {}

    def get(self, cx, cy, mat):
        k = (int(cx // 3200), int(cy // 3200), mat)
        if k not in self.b:
            self.b[k] = ([], [], [], [])
        return self.b[k]

    def tri(self, B, p, uv, col):
        P, U, C, I = B
        n = len(P) // 3
        for q, u in zip(p, uv):
            P.extend(q)
            U.extend(u)
            C.extend(col)
        I.extend((n, n + 1, n + 2))

    def quad(self, B, a, b, c, d, uv, col):
        P, U, C, I = B
        n = len(P) // 3
        u0, v0, u1, v1 = uv
        for q, u in ((a, (u0, v0)), (b, (u1, v0)), (c, (u1, v1)), (d, (u0, v1))):
            P.extend(q)
            U.extend(u)
            C.extend(col)
        I.extend((n, n + 1, n + 2, n, n + 2, n + 3))

    def box(self, B, cx, cy, cz, sx, sy, sz, col, ang=0.0):
        ca, sa = math.cos(ang), math.sin(ang)

        def R(dx, dz):
            return (cx + dx * ca - dz * sa, cz + dx * sa + dz * ca)
        c = [R(-sx / 2, -sz / 2), R(sx / 2, -sz / 2), R(sx / 2, sz / 2), R(-sx / 2, sz / 2)]
        y0, y1 = cy, cy + sy
        for i in range(4):
            a, b = c[i], c[(i + 1) % 4]
            sh = 0.8 if i % 2 else 0.92
            self.quad(B, (a[0], y0, a[1]), (b[0], y0, b[1]), (b[0], y1, b[1]), (a[0], y1, a[1]), (0, 0, 1, 1), tuple(v * sh for v in col))
        self.quad(B, (c[0][0], y1, c[0][1]), (c[1][0], y1, c[1][1]), (c[2][0], y1, c[2][1]), (c[3][0], y1, c[3][1]), (0, 0, 1, 1), col)


def area2(px, py):
    return sum(px[i] * py[(i + 1) % len(px)] - px[(i + 1) % len(px)] * py[i] for i in range(len(px)))


def earclip(px, py):
    n = len(px)
    idx = list(range(n))
    if area2(px, py) < 0:
        idx.reverse()
    out = []

    def cross(o, a, b):
        return (px[a] - px[o]) * (py[b] - py[o]) - (py[a] - py[o]) * (px[b] - px[o])

    def inside(p, a, b, c):
        return cross(a, b, p) >= 0 and cross(b, c, p) >= 0 and cross(c, a, p) >= 0
    guard = 0
    while len(idx) > 3 and guard < 5000:
        guard += 1
        m = len(idx)
        done = False
        for i in range(m):
            a, b, c = idx[(i - 1) % m], idx[i], idx[(i + 1) % m]
            if cross(a, b, c) <= 1e-9:
                continue
            if any(inside(p, a, b, c) for p in idx if p not in (a, b, c)):
                continue
            out.append((a, b, c))
            idx.pop(i)
            done = True
            break
        if not done:
            idx.pop(0)
    if len(idx) == 3:
        out.append(tuple(idx))
    return out


def pip(x, y, px, py):
    n = len(px)
    c = False
    j = n - 1
    for i in range(n):
        if ((py[i] > y) != (py[j] > y)) and (x < (px[j] - px[i]) * (y - py[i]) / (py[j] - py[i]) + px[i]):
            c = not c
        j = i
    return c


def edge_dist(x, y, px, py):
    best = 1e9
    n = len(px)
    for i in range(n):
        j = (i + 1) % n
        dx, dy = px[j] - px[i], py[j] - py[i]
        L2 = dx * dx + dy * dy or 1
        t = max(0, min(1, ((x - px[i]) * dx + (y - py[i]) * dy) / L2))
        best = min(best, math.hypot(x - px[i] - t * dx, y - py[i] - t * dy))
    return best


def wall_uv(mat, ln, hh):
    U, V, bays, fpt, blank, cont = FAC[mat]
    if cont:
        return 0.0, ln / U, 1.0 / V
    nf = max(1, round(hh / (V / fpt)))
    vs = (nf / fpt) / max(hh, 1)
    bay = U / bays
    if ln < blank:
        return -ln / 2 / U, ln / 2 / U, vs
    if ln < bay * 0.6 and blank:
        return -blank / 2 / U, blank / 2 / U, vs
    n = max(1, round(ln / bay))
    return 0.0, n / bays, vs


# ---------- per-building look, from the flyover reference ----------
POI = {p[0]: (p[1], p[2]) for p in W['pois']}
BLD = W['bld']
INFO = []
for i, b in enumerate(BLD):
    n = (len(b) - 3) // 2
    px = [b[3 + k * 2] for k in range(n)]
    py = [b[4 + k * 2] for k in range(n)]
    INFO.append((sum(px) / n, sum(py) / n, abs(area2(px, py)) / 2))


def nearest(name, kinds=None, maxd=900, tallest=False):
    x, y = POI[name]
    c = [(math.hypot(INFO[i][0] - x, INFO[i][1] - y), i) for i in range(len(BLD)) if (kinds is None or BLD[i][1] in kinds)]
    c = [t for t in c if t[0] < maxd]
    if not c:
        return None
    if tallest:
        return max(c, key=lambda t: BLD[t[1]][0])[1]
    return min(c)[1]


OVR = {}


def ovr(i, **kw):
    if i is not None:
        OVR.setdefault(i, {}).update(kw)
        OVR[i].setdefault('names', [])


def named(name, **kw):
    i = nearest(name, maxd=kw.pop('maxd', 700))
    if i is not None:
        ovr(i, **kw)
        OVR[i]['names'].append(name)


ovr(4392, special='dome')
ovr(5768, wall='f_metal', tint=lin('#9aa4ad'), shop='shop_modern', roof='r_seam', rtint=lin('#c9ced2'), names=['Angel of the Winds Arena'])
ovr(5805, wall='f_garage', tint=WHITE, shop=None, roof='r_parking', rtint=WHITE, names=['County parking garage'])
named('Everett Station', wall='f_brick_red', tint=(0.82, 0.78, 0.78), shop=None, roof='r_seam', rtint=lin('#4f8a6f'), pitched=True)
named('Snohomish County Courthouse', wall='f_concrete', tint=(0.9, 0.9, 0.9), shop=None, roof='r_gravel', rtint=WHITE)
i = nearest('Snohomish County Courthouse', maxd=1500, tallest=True)
if i is not None and i not in OVR:
    ovr(i, wall='f_glass', tint=(0.85, 0.95, 1.0), shop=None, roof='r_membrane', rtint=(0.75, 0.76, 0.78), names=['County administration tower'])
named('City Hall', wall='f_brick_buff', tint=WHITE, shop=None, roof='r_gravel', rtint=WHITE)
named('Federal Building', wall='f_concrete', tint=(1, 0.97, 0.9), shop=None, roof='r_gravel', rtint=WHITE)
named('Everett Police HQ', wall='f_brick_red', tint=(0.9, 0.86, 0.86), shop=None, roof='r_membrane', rtint=(0.75, 0.76, 0.78))
named('Everett Municipal Court', wall='f_brick_buff', tint=(0.95, 0.95, 0.95), shop=None, roof='r_membrane', rtint=WHITE)
named('Everett Public Library', wall='f_brick_buff', tint=(1, 0.96, 0.9), shop=None, roof='r_membrane', rtint=(0.8, 0.8, 0.8))
named('Everett Performing Arts Center', wall='f_brick_red', tint=WHITE, shop='shop_modern', roof='r_membrane', rtint=WHITE)
named('Snohomish County PUD', wall='f_glass', tint=(0.95, 0.95, 0.9), shop=None, roof='r_membrane', rtint=WHITE)
named('Providence Pacific Campus', wall='f_stucco', tint=lin('#e2b3a2'), shop=None, roof='r_membrane', rtint=WHITE)
named('US Postal Service', wall='f_cmu', tint=lin('#e9e7e1'), shop=None, roof='r_membrane', rtint=WHITE)
named('Carl Gipson Center', wall='f_brick_red', tint=(1, 0.93, 0.86), shop=None, roof='r_membrane', rtint=WHITE)
named('Monte Cristo Hotel', wall='f_brick_buff', tint=WHITE, shop='shop_buff', roof='r_gravel', rtint=WHITE)
named('City Service Center', wall='f_metal', tint=lin('#c9cbcc'), shop=None, roof='r_seam', rtint=lin('#b9bcc0'))
named('Fire Administration', wall='f_brick_red', tint=WHITE, shop=None, roof='r_membrane', rtint=WHITE)
named('Fire Station 1', wall='f_brick_red', tint=WHITE, shop=None, roof='r_membrane', rtint=WHITE)
named('Kimberly Clark', wall='f_metal', tint=lin('#c9cbcc'), shop=None, roof='r_seam', rtint=lin('#c9ced2'), maxd=2500)
for nm in ('Culmback Building', 'Krieger Laundry', 'Evergreen Building', 'Morrow Building', "Watson's Bakery", 'Everett Downtown Storage', 'Walsh Platt Motors Building', 'McCabe Building', 'Challacombe & Fickel Building'):
    named(nm, wall='f_brick_red', tint=BRICKT[len(nm) % 5], shop='shop_brick', roof='r_gravel', rtint=(0.8, 0.8, 0.8))
for nm in ('Commerce Building', 'Port Gardner Building', 'Bank of Everett (Cope Gillette Theatre)', 'Apex Art and Culture Center Building'):
    named(nm, wall='f_brick_buff', tint=WHITE, shop='shop_buff', roof='r_gravel', rtint=(0.8, 0.8, 0.8))
for nm in ('Everett High School', 'North Middle School', 'Garfield Elementary School', 'Jackson Elementary School', 'Immaculate Conception School', 'Sequoia High School', 'Everett Christian School'):
    named(nm, wall='f_brick_red', tint=(1.0, 0.93, 0.86), shop=None, roof='r_membrane', rtint=(0.8, 0.8, 0.8), maxd=900)

CORE = lambda x, y: 12500 < x < 20500 and 9500 < y < 15500


def look(i):
    b = BLD[i]
    h, kind = b[0], b[1]
    cx, cy, A = INFO[i]
    r = random.Random(i * 7919 + 13)
    L = dict(wall='f_stucco', tint=WHITE, shop=None, roof='r_membrane', rtint=WHITE, pitched=False, special=None, units=True)
    m2 = A / 100
    if kind in (0, 3):
        L.update(wall='f_siding' if kind == 0 else 'f_lap', tint=lin(pick(r, HOUSE), 1.0 if kind == 0 else 0.85), roof='r_shingle', rtint=lin(pick(r, HROOF), 1.25), pitched=True, units=False)
    elif kind == 4:
        L.update(wall='f_metal', tint=lin(pick(r, INDC)), roof=r.choice(['r_seam', 'r_seam', 'r_membrane']), rtint=lin(r.choice(['#d9dbdc', '#b9bcc0', '#e9e9e6', '#9aa4ad'])))
    elif kind == 5:
        if m2 < 420 and h <= 105:
            L.update(wall='f_siding', tint=lin(pick(r, HOUSE)), roof='r_shingle', rtint=lin(pick(r, HROOF), 1.25), pitched=True, units=False)
        else:
            w = pick(r, [('f_panel', 35), ('f_brick_dark', 22), ('f_stucco', 20), ('f_brick_red', 12), ('f_brick_buff', 11)])
            t = lin(pick(r, PASTEL)) if w in ('f_stucco',) else (r.choice([(1, 1, 1), (0.92, 0.94, 0.97), (1, 0.97, 0.92)]) if w == 'f_panel' else r.choice(BRICKT))
            L.update(wall=w, tint=t, roof='r_membrane', rtint=r.choice([(0.86, 0.86, 0.86), (0.8, 0.81, 0.82), (0.66, 0.67, 0.68)]))
    else:
        core = CORE(cx, cy)
        if h <= 62:
            w = pick(r, [('f_cmu', 34), ('f_stucco', 26), ('f_brick_red', 20 if core else 12), ('f_metal', 10), ('f_brick_buff', 10)])
        elif h <= 165:
            w = pick(r, [('f_brick_red', 40), ('f_brick_buff', 20), ('f_stucco', 14), ('f_concrete', 10), ('f_brick_dark', 10), ('f_panel', 6)] if core else
                     [('f_stucco', 28), ('f_cmu', 16), ('f_brick_red', 22), ('f_panel', 16), ('f_concrete', 18)])
        else:
            w = pick(r, [('f_concrete', 34), ('f_glass', 20), ('f_brick_buff', 16), ('f_brick_red', 10), ('f_brick_dark', 10), ('f_panel', 10)])
        if w in ('f_cmu', 'f_stucco', 'f_metal'):
            t = lin(pick(r, PASTEL))
        elif w in ('f_brick_red', 'f_brick_buff', 'f_brick_dark'):
            t = r.choice(BRICKT)
        else:
            t = r.choice([(1, 1, 1), (0.92, 0.92, 0.92), (1, 0.97, 0.92)])
        shop = None
        if h >= 45 and w not in ('f_metal', 'f_glass'):
            shop = 'shop_brick' if w == 'f_brick_red' else 'shop_buff' if w == 'f_brick_buff' else 'shop_modern'
            if r.random() < 0.18:
                shop = None
        rf = pick(r, [('r_membrane', 62), ('r_gravel', 38)] if not core or h > 120 else [('r_membrane', 45), ('r_gravel', 55)])
        rt = r.choice([(0.86, 0.86, 0.86), (0.82, 0.83, 0.84), (0.66, 0.67, 0.68), (0.8, 0.77, 0.7)]) if rf == 'r_membrane' else r.choice([(1, 1, 1), (0.7, 0.7, 0.7), (0.55, 0.55, 0.56)])
        L.update(wall=w, tint=t, shop=shop, roof=rf, rtint=rt)
    if i in OVR:
        L.update({k: v for k, v in OVR[i].items() if k != 'names'})
    return L


BF = Bufs()
stats = {}
tris_total = 0
for i, b in enumerate(BLD):
    h, kind = b[0], b[1]
    n = (len(b) - 3) // 2
    px = [b[3 + k * 2] for k in range(n)]
    py = [b[4 + k * 2] for k in range(n)]
    if area2(px, py) < 0:
        px.reverse()
        py.reverse()
    cx, cy, A = INFO[i]
    es = [Hat(px[k], py[k]) for k in range(n)]
    lo, hi = min(es), max(es)
    gm = (lo + hi) / 2
    base, top = lo - 4, gm + h
    L = look(i)
    r = random.Random(i * 104729 + 7)
    stats[L['wall']] = stats.get(L['wall'], 0) + 1
    plain = BF.get(cx, cy, 'plain')
    if L['special'] == 'dome':
        # the port's storage dome: low ring wall and a ribbed spherical cap
        R = math.sqrt(A / math.pi)
        seg, rings = 40, 9
        wallh, rise = 55, R * 0.62
        ring = lin('#c9c7c1')
        BD = BF.get(cx, cy, 'r_dome')
        for s in range(seg):
            a0, a1 = 2 * math.pi * s / seg, 2 * math.pi * (s + 1) / seg
            p0 = (cx + R * math.cos(a0), cy + R * math.sin(a0))
            p1 = (cx + R * math.cos(a1), cy + R * math.sin(a1))
            BF.quad(plain, (p0[0], base, p0[1]), (p1[0], base, p1[1]), (p1[0], gm + wallh, p1[1]), (p0[0], gm + wallh, p0[1]), (0, 0, 1, 1), ring)
            for k in range(rings):
                t0, t1 = k / rings, (k + 1) / rings
                r0, r1 = R * math.cos(t0 * math.pi / 2), R * math.cos(t1 * math.pi / 2)
                y0, y1 = gm + wallh + rise * math.sin(t0 * math.pi / 2), gm + wallh + rise * math.sin(t1 * math.pi / 2)
                a = (cx + r0 * math.cos(a0), y0, cy + r0 * math.sin(a0))
                bb = (cx + r0 * math.cos(a1), y0, cy + r0 * math.sin(a1))
                c = (cx + r1 * math.cos(a1), y1, cy + r1 * math.sin(a1))
                d = (cx + r1 * math.cos(a0), y1, cy + r1 * math.sin(a0))
                BF.quad(BD, a, bb, c, d, (s / 2, t0 * 2.5, (s + 1) / 2, t1 * 2.5), WHITE)
        BF.box(plain, cx, gm + wallh + rise - 4, cy, 60, 22, 60, lin('#b9bcc0'))
        continue
    pitched = L['pitched']
    rise = 0
    RA = RB = None
    if pitched:
        sxx = sum((x - cx) ** 2 for x in px)
        syy = sum((y - cy) ** 2 for y in py)
        sxy = sum((px[k] - cx) * (py[k] - cy) for k in range(n))
        th = 0.5 * math.atan2(2 * sxy, sxx - syy)
        ax, ay = math.cos(th), math.sin(th)
        us = [(px[k] - cx) * ax + (py[k] - cy) * ay for k in range(n)]
        vs_ = [-(px[k] - cx) * ay + (py[k] - cy) * ax for k in range(n)]
        u0, u1, v0, v1 = min(us), max(us), min(vs_), max(vs_)
        lng = (u1 - u0) >= (v1 - v0)
        le, se = (u1 - u0, v1 - v0) if lng else (v1 - v0, u1 - u0)
        hl = max(0, (le - se) / 2)
        uc, vc = (u0 + u1) / 2, (v0 + v1) / 2
        mx, my = cx + uc * ax - vc * ay, cy + uc * ay + vc * ax
        dx, dy = (ax, ay) if lng else (-ay, ax)
        rise = min(max(se * 0.3, 5 if kind == 3 else 10), 34 if kind in (0, 3, 5) else 60)
        RA, RB = (mx - dx * hl, my - dy * hl), (mx + dx * hl, my + dy * hl)
    wt = max(base + 24, top - rise) if pitched else top
    flat = not pitched
    par = 0
    if flat and kind != 4 and h > 45 and L['roof'] != 'r_parking':
        par = 7 if h < 120 else 10
    if L['roof'] == 'r_parking':
        par = 11
    rt = wt - par
    shop = L['shop']
    sh = 38 if shop and (wt - gm) > 44 else 0
    if shop and not sh:
        shop = None
    wm = L['wall']
    WB = BF.get(cx, cy, wm)
    tint = L['tint']
    found = tuple(v * 0.55 for v in lin('#b6b3ab'))
    hh = rt - gm - sh
    for k in range(n):
        j = (k + 1) % n
        ln = math.hypot(px[j] - px[k], py[j] - py[k])
        if ln < 0.5:
            continue
        a, c = (px[k], py[k]), (px[j], py[j])
        # foundation below the mean ground line
        if gm - min(es[k], es[j]) > 2.5:
            BF.quad(plain, (a[0], base, a[1]), (c[0], base, c[1]), (c[0], gm, c[1]), (a[0], gm, a[1]), (0, 0, 1, 1), found)
        z0 = gm
        if sh:
            SB = BF.get(cx, cy, shop)
            ns = max(1, round(ln / 80))
            if ln < 30:
                BF.quad(WB, (a[0], z0, a[1]), (c[0], z0, c[1]), (c[0], z0 + sh, c[1]), (a[0], z0 + sh, a[1]), (0.0, 0.0, 0.0, 0.0), tuple(v * 0.8 for v in tint))
            else:
                BF.quad(SB, (a[0], z0, a[1]), (c[0], z0, c[1]), (c[0], z0 + sh, c[1]), (a[0], z0 + sh, a[1]), (0, 0, ns, 1), WHITE)
            z0 += sh
        ua, ub, vs = wall_uv(wm, ln, max(hh, 8))
        BF.quad(WB, (a[0], z0, a[1]), (c[0], z0, c[1]), (c[0], rt, c[1]), (a[0], rt, a[1]), (ua, 0.0, ub, (rt - z0) * vs), tint)
        if par:
            pc = tuple(v * 0.6 for v in lin('#c9c7c1'))
            BF.quad(plain, (a[0], rt, a[1]), (c[0], rt, c[1]), (c[0], wt, c[1]), (a[0], wt, a[1]), (0, 0, 1, 1), pc)
            if wm in ('f_brick_red', 'f_brick_buff', 'f_brick_dark', 'f_concrete') and h > 60 and ln > 20:
                # projecting cornice: soffit, face and cap
                ox_, oy_ = (py[j] - py[k]) / ln * 3.5, -(px[j] - px[k]) / ln * 3.5
                cc = tuple(v * 0.62 for v in lin('#3a3532' if wm == 'f_brick_dark' else '#d6cfbf'))
                A0, C0 = (a[0] + ox_, a[1] + oy_), (c[0] + ox_, c[1] + oy_)
                z0c, z1c = wt - 5, wt + 1.5
                BF.quad(plain, (a[0], z0c, a[1]), (c[0], z0c, c[1]), (C0[0], z0c, C0[1]), (A0[0], z0c, A0[1]), (0, 0, 1, 1), tuple(v * 0.6 for v in cc))
                BF.quad(plain, (A0[0], z0c, A0[1]), (C0[0], z0c, C0[1]), (C0[0], z1c, C0[1]), (A0[0], z1c, A0[1]), (0, 0, 1, 1), cc)
                BF.quad(plain, (A0[0], z1c, A0[1]), (C0[0], z1c, C0[1]), (c[0], z1c, c[1]), (a[0], z1c, a[1]), (0, 0, 1, 1), tuple(min(1, v * 1.25) for v in cc))
    RBf = BF.get(cx, cy, L['roof'])
    rc = L['rtint']
    if pitched:
        S = 64.0
        E = [(RA[0], wt + rise, RA[1]), (RB[0], wt + rise, RB[1])]

        def ne(x, y):
            return 0 if (x - RA[0]) ** 2 + (y - RA[1]) ** 2 <= (x - RB[0]) ** 2 + (y - RB[1]) ** 2 else 1

        def ruv(p):
            # shingle courses run along the ridge
            return (((p[0] - cx) * dx + (p[2] - cy) * dy) / S, (p[1] * 2.2 + abs(-(p[0] - cx) * dy + (p[2] - cy) * dx)) / S)
        for k in range(n):
            j = (k + 1) % n
            vi, vj = (px[k], wt, py[k]), (px[j], wt, py[j])
            a_, b_ = ne(px[k], py[k]), ne(px[j], py[j])
            if a_ == b_:
                T = [(vi, vj, E[a_])]
            else:
                T = [(vi, vj, E[b_]), (vi, E[b_], E[a_])]
            for t in T:
                BF.tri(RBf, t, [ruv(p) for p in t], rc)
        if kind == 0 and rise > 9 and r.random() < 0.6:
            f = r.choice([0.25, 0.7])
            qx, qy = RA[0] + (RB[0] - RA[0]) * f - dy * 9, RA[1] + (RB[1] - RA[1]) * f + dx * 9
            BF.box(plain, qx, wt + rise - 14, qy, 6, 24, 6, lin(r.choice(['#7a4034', '#8a5a48', '#9a9c9e'])), math.atan2(dy, dx))
    else:
        tr = earclip(px, py)
        if L['roof'] == 'r_parking':
            sxx = sum((x - cx) ** 2 for x in px)
            syy = sum((y - cy) ** 2 for y in py)
            sxy = sum((px[k] - cx) * (py[k] - cy) for k in range(n))
            th = 0.5 * math.atan2(2 * sxy, sxx - syy)
            ca, sa = math.cos(th), math.sin(th)
            uvf = lambda x, y: (((x - cx) * ca + (y - cy) * sa) / 52.0, (-(x - cx) * sa + (y - cy) * ca) / 170.0)
        else:
            ox, oy = math.floor(cx / 64.0), math.floor(cy / 64.0)
            uvf = lambda x, y: (x / 64.0 - ox, y / 64.0 - oy)
        for t in tr:
            BF.tri(RBf, [(px[q], rt, py[q]) for q in t], [uvf(px[q], py[q]) for q in t], rc)
        # rooftop plant
        if L['units'] and A > 15000 and L['roof'] != 'r_parking':
            cnt = max(1, min(7, int(A / 45000) + 1))
            placed = 0
            x0, x1, y0, y1 = min(px), max(px), min(py), max(py)
            for _ in range(60):
                if placed >= cnt:
                    break
                x, y = r.uniform(x0, x1), r.uniform(y0, y1)
                if not pip(x, y, px, py) or edge_dist(x, y, px, py) < 32:
                    continue
                e = math.atan2(py[1] - py[0], px[1] - px[0])
                BF.box(plain, x, rt, y, r.uniform(18, 38), r.uniform(10, 17), r.uniform(14, 28), lin(r.choice(['#b9bcc0', '#8d9196', '#d0d2d4'])), e)
                placed += 1
            if h > 230 and pip(cx, cy, px, py):
                BF.box(plain, cx, rt, cy, 2.5, 90, 2.5, lin('#d0d2d4'))
                BF.box(plain, cx, rt + 60, cy, 14, 1.5, 1.5, lin('#d0d2d4'))
            if h > 150 and A > 30000:
                for _ in range(40):
                    x, y = r.uniform(x0, x1), r.uniform(y0, y1)
                    if pip(x, y, px, py) and edge_dist(x, y, px, py) > 45:
                        e = math.atan2(py[1] - py[0], px[1] - px[0])
                        BF.box(plain, x, rt, y, 60, 30, 45, tuple(v * 0.8 for v in lin('#b6b3ab')), e)
                        break

# ---------- write GLB ----------
mats = sorted(set(k[2] for k in BF.b))
bin_ = bytearray()
views, accs, meshes, nodes = [], [], [], []


def pad():
    while len(bin_) % 4:
        bin_.append(0)


def view(data, target):
    pad()
    off = len(bin_)
    bin_.extend(data)
    views.append({'buffer': 0, 'byteOffset': off, 'byteLength': len(data), 'target': target})
    return len(views) - 1


QUANT = len(sys.argv) > 3 and sys.argv[3] == 'quant'
PQ, UQ = 0.25, 256
clip = 0
for (ix, iy, m), (P, U, C, I) in sorted(BF.b.items()):
    nv = len(P) // 3
    if not nv:
        continue
    tris_total += len(I) // 3
    node = {'name': f'{m}_{ix}_{iy}'}
    UF = [u if k % 2 == 0 else 1 - u for k, u in enumerate(U)]
    if QUANT:
        ox, oz = ix * 3200 + 1600, iy * 3200 + 1600
        q = []
        for k in range(nv):
            q.extend((round((P[k * 3] - ox) / PQ), round(P[k * 3 + 1] / PQ), round((P[k * 3 + 2] - oz) / PQ)))
        assert max(abs(v) for v in q) < 32767, (m, ix, iy)
        xs, ys, zs = q[0::3], q[1::3], q[2::3]
        pv = view(struct.pack('<%dh' % len(q), *q), 34962)
        accs.append({'bufferView': pv, 'componentType': 5122, 'count': nv, 'type': 'VEC3', 'min': [min(xs), min(ys), min(zs)], 'max': [max(xs), max(ys), max(zs)]})
        pa = len(accs) - 1
        uq = [max(-32767, min(32767, round(u * UQ))) for u in UF]
        clip += sum(1 for u in UF if abs(u * UQ) > 32767)
        uv = view(struct.pack('<%dh' % len(uq), *uq), 34962)
        accs.append({'bufferView': uv, 'componentType': 5122, 'count': nv, 'type': 'VEC2'})
        ua = len(accs) - 1
        node['translation'] = [ox, 0, oz]
        node['scale'] = [PQ, PQ, PQ]
    else:
        xs, ys, zs = P[0::3], P[1::3], P[2::3]
        pv = view(struct.pack('<%df' % len(P), *P), 34962)
        accs.append({'bufferView': pv, 'componentType': 5126, 'count': nv, 'type': 'VEC3', 'min': [min(xs), min(ys), min(zs)], 'max': [max(xs), max(ys), max(zs)]})
        pa = len(accs) - 1
        uv = view(struct.pack('<%df' % len(UF), *UF), 34962)
        accs.append({'bufferView': uv, 'componentType': 5126, 'count': nv, 'type': 'VEC2'})
        ua = len(accs) - 1
    c16 = []
    for k in range(nv):
        c16.extend((int(min(1, C[k * 3]) * 255 + 0.5), int(min(1, C[k * 3 + 1]) * 255 + 0.5), int(min(1, C[k * 3 + 2]) * 255 + 0.5), 255))
    cv = view(bytes(c16), 34962)
    accs.append({'bufferView': cv, 'componentType': 5121, 'normalized': True, 'count': nv, 'type': 'VEC4'})
    ca_ = len(accs) - 1
    if nv < 65536:
        iv = view(struct.pack('<%dH' % len(I), *I), 34963)
        ct = 5123
    else:
        iv = view(struct.pack('<%dI' % len(I), *I), 34963)
        ct = 5125
    accs.append({'bufferView': iv, 'componentType': ct, 'count': len(I), 'type': 'SCALAR'})
    ia = len(accs) - 1
    meshes.append({'name': f'{m}_{ix}_{iy}', 'primitives': [{'attributes': {'POSITION': pa, 'TEXCOORD_0': ua, 'COLOR_0': ca_}, 'indices': ia, 'material': mats.index(m)}]})
    node['mesh'] = len(meshes) - 1
    nodes.append(node)
pad()
textured = [m for m in mats if m != 'plain']
g = {'asset': {'version': '2.0', 'generator': 'Hewitt Heat citygen'}, 'scene': 0, 'scenes': [{'nodes': list(range(len(nodes)))}], 'nodes': nodes, 'meshes': meshes,
     'accessors': accs, 'bufferViews': views, 'buffers': [{'byteLength': len(bin_)}],
     'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}],
     'images': [{'uri': '../tex/b/%s.jpg' % m} for m in textured], 'textures': [{'sampler': 0, 'source': k} for k in range(len(textured))],
     'materials': [dict(name=m, doubleSided=True, pbrMetallicRoughness=dict(metallicFactor=0.0, roughnessFactor=0.85, **({'baseColorTexture': dict(index=textured.index(m), **({'extensions': {'KHR_texture_transform': {'scale': [1 / UQ, 1 / UQ]}}} if QUANT else {}))} if m != 'plain' else {}))) for m in mats]}
if QUANT:
    g['extensionsUsed'] = ['KHR_mesh_quantization', 'KHR_texture_transform']
    g['extensionsRequired'] = ['KHR_mesh_quantization', 'KHR_texture_transform']
    print('uv clipped', clip)
js = json.dumps(g, separators=(',', ':')).encode()
while len(js) % 4:
    js += b' '
with open(OUT, 'wb') as f:
    f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(bin_)))
    f.write(struct.pack('<I4s', len(js), b'JSON'))
    f.write(js)
    f.write(struct.pack('<I4s', len(bin_), b'BIN\x00'))
    f.write(bin_)
print('buildings', len(BLD), 'meshes', len(meshes), 'tris', tris_total, 'bytes', 20 + len(js) + 8 + len(bin_))
print('walls', sorted(stats.items(), key=lambda t: -t[1]))
print('named', sorted(sum((v['names'] for v in OVR.values()), [])))
json.dump({'materials': mats, 'named': {str(k): v['names'] for k, v in OVR.items() if v['names']}}, open(OUT.replace('.glb', '_info.json'), 'w'))
