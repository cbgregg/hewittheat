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
    'f_sheath': (80, 66, 2, 2, 6, False),
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

    def quad(self, B, a, b, c, d, uv, col, bot=1.0):
        # bot darkens the first two corners (the foot of a wall) so buildings sit in a soft contact shade
        P, U, C, I = B
        n = len(P) // 3
        u0, v0, u1, v1 = uv
        for k, (q, u) in enumerate(((a, (u0, v0)), (b, (u1, v0)), (c, (u1, v1)), (d, (u0, v1)))):
            P.extend(q)
            U.extend(u)
            C.extend(col if k > 1 or bot == 1.0 else tuple(v * bot for v in col))
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
    ovr(i, wall='f_glass', tint=lin('#3a4048'), shop=None, roof='r_membrane', rtint=(0.9, 0.9, 0.9), names=['County administration tower'])  # near-black glass in the flyover
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

# ---------- block-by-block looks (tools/blocks.py) ----------
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blocks
FLH = 33.0


def blk(d):
    d = dict(d)
    for k in ('tint', 'rtint', 'awn'):
        if isinstance(d.get(k), str):
            d[k] = lin(d[k])
    if d.get('stripe'):
        d['stripe'] = (lin(d['stripe'][0]),) + tuple(d['stripe'][1:])
    if d.get('spire'):
        d['spire'] = (lin(d['spire'][0]), d['spire'][1])
    if d.get('special') == 'construction':
        d.update(wall='f_sheath', tint=WHITE, shop=None, roof='plain', rtint=lin('#b89a62'), units=False, pitched=False)
    if 'wall' in d:
        d.setdefault('pitched', False)
    return d


def clip_y(px, py, ya, yb):
    # keep the part of a polygon between two east-west lines
    P = list(zip(px, py))
    for sgn, lim in ((1, ya), (-1, yb)):
        Q = []
        for k in range(len(P)):
            a, b = P[k], P[(k + 1) % len(P)]
            ia, ib = sgn * (a[1] - lim) >= 0, sgn * (b[1] - lim) >= 0
            if ia:
                Q.append(a)
            if ia != ib:
                t = (lim - a[1]) / (b[1] - a[1])
                Q.append((a[0] + (b[0] - a[0]) * t, lim))
        P = Q
    return P


for i, parts in blocks.SPLIT.items():
    b = BLD[i]
    n = (len(b) - 3) // 2
    px = [b[3 + k * 2] for k in range(n)]
    py = [b[4 + k * 2] for k in range(n)]
    y0, y1 = min(py), max(py)
    for q, (f0, f1, d) in enumerate(parts):
        P = clip_y(px, py, y0 + (y1 - y0) * f0, y0 + (y1 - y0) * f1)
        if len(P) < 3:
            continue
        nb = [b[0], b[1], b[2]] + [v for p in P for v in p]
        if q == 0:
            BLD[i] = nb
            j = i
        else:
            BLD.append(nb)
            j = len(BLD) - 1
            INFO.append(None)
        qx, qy = [p[0] for p in P], [p[1] for p in P]
        INFO[j] = (sum(qx) / len(P), sum(qy) / len(P), abs(area2(qx, qy)) / 2)
        OVR[j] = dict(blk(d), names=OVR.get(j, {}).get('names', []))
for br in getattr(blocks, 'BRIDGES', []):
    for key in ('a', 'b'):
        i = br[key]
        op, lim = br[key + '_keep']
        b = BLD[i]
        qx, qy = b[3::2], b[4::2]
        P = [(x, y) for y, x in clip_y(qy, qx, -1e9, lim)] if op == 'x<' else [(x, y) for y, x in clip_y(qy, qx, lim, 1e9)]
        BLD[i] = [b[0], b[1], b[2]] + [v for p_ in P for v in p_]
        INFO[i] = (sum(p_[0] for p_ in P) / len(P), sum(p_[1] for p_ in P) / len(P), abs(area2([p_[0] for p_ in P], [p_[1] for p_ in P])) / 2)
for i, d in blocks.B.items():
    ovr(i, **blk(d))
GONE = set(blocks.GONE)
ADDED = []
for d in blocks.ADD:
    d = dict(d)
    P = d.pop('poly')
    BLD.append([d['fl'] * FLH, 1, 0] + [v for p in P for v in p])
    qx, qy = [p[0] for p in P], [p[1] for p in P]
    INFO.append((sum(qx) / len(P), sum(qy) / len(P), abs(area2(qx, qy)) / 2))
    OVR[len(BLD) - 1] = dict(blk(d), names=[])
    ADDED.append(P)

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
    if i in GONE:
        continue
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
    L = look(i)
    if L.get('fl'):
        h = L['fl'] * FLH + (10 if L.get('special') != 'construction' else 0)
    base, top = lo - 4, gm + h
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
    build = L.get('special') == 'construction'
    if flat and kind != 4 and h > 45 and L['roof'] != 'r_parking' and not build:
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
                BF.quad(SB, (a[0], z0, a[1]), (c[0], z0, c[1]), (c[0], z0 + sh, c[1]), (a[0], z0 + sh, a[1]), (0, 0, ns, 1), WHITE, 0.7)
            z0 += sh
        ua, ub, vs = wall_uv(wm, ln, max(hh, 8))
        st = L.get('stripe')
        nseg = max(1, round(ln / st[1])) if st and ln > st[1] * 0.75 else 1
        for q in range(nseg):
            t0, t1 = q / nseg, (q + 1) / nseg
            sa_, sc_ = (a[0] + (c[0] - a[0]) * t0, a[1] + (c[1] - a[1]) * t0), (a[0] + (c[0] - a[0]) * t1, a[1] + (c[1] - a[1]) * t1)
            BF.quad(WB, (sa_[0], z0, sa_[1]), (sc_[0], z0, sc_[1]), (sc_[0], rt, sc_[1]), (sa_[0], rt, sa_[1]),
                    (ua + (ub - ua) * t0, 0.0, ua + (ub - ua) * t1, (rt - z0) * vs), st[0] if st and (q + k) % (st[2] if len(st) > 2 else 2) == (st[2] if len(st) > 2 else 2) - 1 else tint, 0.9 if sh else 0.72)
        onx, ony = (py[j] - py[k]) / ln, -(px[j] - px[k]) / ln
        if L.get('awn') and sh and ln > 60:
            na = max(1, round(ln / 80))
            for q in range(na):
                t0, t1 = (q + 0.12) / na, (q + 0.88) / na
                p0, p1 = (a[0] + (c[0] - a[0]) * t0, a[1] + (c[1] - a[1]) * t0), (a[0] + (c[0] - a[0]) * t1, a[1] + (c[1] - a[1]) * t1)
                zt, zb, out = gm + sh - 3, gm + sh - 12, 13
                BF.quad(plain, (p0[0] + onx * out, zb, p0[1] + ony * out), (p1[0] + onx * out, zb, p1[1] + ony * out), (p1[0], zt, p1[1]), (p0[0], zt, p0[1]), (0, 0, 1, 1), L['awn'])
                BF.quad(plain, (p0[0] + onx * out, zb - 3, p0[1] + ony * out), (p1[0] + onx * out, zb - 3, p1[1] + ony * out), (p1[0] + onx * out, zb, p1[1] + ony * out), (p0[0] + onx * out, zb, p0[1] + ony * out), (0, 0, 1, 1), tuple(v * 0.75 for v in L['awn']))
        if build and ln > 30:
            # open framing above the top plate and a scaffold run along the wall
            for q in range(max(2, round(ln / 40)) + 1):
                t = q / max(2, round(ln / 40))
                BF.box(plain, a[0] + (c[0] - a[0]) * t, rt, a[1] + (c[1] - a[1]) * t, 1.6, 24, 1.6, lin('#c9a66b'))
            BF.quad(plain, (a[0], rt + 23, a[1]), (c[0], rt + 23, c[1]), (c[0], rt + 25, c[1]), (a[0], rt + 25, a[1]), (0, 0, 1, 1), lin('#c9a66b'))
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
    if L.get('spire'):
        # square tower and a pointed spire at the end of the building nearest the street corner
        sc_, sh_ = L['spire']
        k0 = max(range(n), key=lambda q: px[q] - py[q])  # north-east corner
        tx, ty = px[k0] + (cx - px[k0]) * 0.18, py[k0] + (cy - py[k0]) * 0.18
        BF.box(plain, tx, base, ty, 46, wt - base + 40, 46, tuple(v * 0.9 for v in tint))
        z0s, z1s = wt + 40, wt + 40 + sh_
        for q, (dx_, dy_) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
            ex, ey = ((1, -1), (1, 1), (-1, 1), (-1, -1))[q]
            BF.tri(plain, [(tx + dx_ * 25, z0s, ty + dy_ * 25), (tx + ex * 25, z0s, ty + ey * 25), (tx, z1s, ty)], [(0, 0), (1, 0), (0.5, 1)], tuple(v * (0.8 if q % 2 else 1.0) for v in sc_))
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

# ---------- skybridges: a glazed box over the street, open underneath ----------
for br in getattr(blocks, 'BRIDGES', []):
    q = br['quad']
    mx_, my_ = sum(p_[0] for p_ in q) / 4, sum(p_[1] for p_ in q) / 4
    g0 = Hat(mx_, my_)
    z0, z1 = g0 + br['z0'], g0 + br['z1']
    GB, PBk = BF.get(mx_, my_, 'f_glass'), BF.get(mx_, my_, 'plain')
    steel = lin('#5a6068')
    for k in range(4):
        a_, c_ = q[k], q[(k + 1) % 4]
        ln_ = math.hypot(c_[0] - a_[0], c_[1] - a_[1])
        ua, ub, vs = wall_uv('f_glass', ln_, z1 - z0 - 6)
        BF.quad(GB, (a_[0], z0 + 3, a_[1]), (c_[0], z0 + 3, c_[1]), (c_[0], z1 - 3, c_[1]), (a_[0], z1 - 3, a_[1]), (ua, 0.0, ub, (z1 - z0 - 6) * vs), lin('#9fb4c4'))
        for zz in (z0, z1 - 3):
            BF.quad(PBk, (a_[0], zz, a_[1]), (c_[0], zz, c_[1]), (c_[0], zz + 3, c_[1]), (a_[0], zz + 3, a_[1]), (0, 0, 1, 1), steel)
    for zz, sh_ in ((z0, 0.55), (z1, 1.0)):
        BF.quad(PBk, *[(p_[0], zz, p_[1]) for p_ in q], (0, 0, 1, 1), tuple(v * sh_ for v in steel))

# ---------- cleared lots, street trees and site machines (tools/blocks.py) ----------
NODES, EDGES, NAMES = W['nodes'], W['edges'], W['names']


def crossing(sa, sb):
    na = set(v for e in EDGES if NAMES[e[4]] == sa for v in e[:2])
    nb = set(v for e in EDGES if NAMES[e[4]] == sb for v in e[:2])
    c = na & nb
    if c:
        q = sorted(c)[0]
        return NODES[q][0], NODES[q][1]
    d, x, y = min((math.hypot(NODES[i][0] - NODES[j][0], NODES[i][1] - NODES[j][1]), (NODES[i][0] + NODES[j][0]) / 2, (NODES[i][1] + NODES[j][1]) / 2) for i in na for j in nb)
    return x, y


EXTRA = {'trees': [], 'props': [], 'clear': [list(t['box']) for t in blocks.SITES]}
for st, ca, cb, side, cnt, size in blocks.TREES:
    (ax, ay), (bx, by) = crossing(st, ca), crossing(st, cb)
    wd = max(e[3] for e in EDGES if NAMES[e[4]] == st)
    ln = math.hypot(bx - ax, by - ay)
    nx, ny = (by - ay) / ln, -(bx - ax) / ln
    want = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}[side]
    if nx * want[0] + ny * want[1] < 0:
        nx, ny = -nx, -ny
    off = wd / 2 + 16
    rr = random.Random(hash((st, ca, cb, side)) & 0xffff)
    for q in range(cnt):
        t = 0.14 + 0.72 * (q + 0.5) / cnt
        EXTRA['trees'].append([round(ax + (bx - ax) * t + nx * off), round(ay + (by - ay) * t + ny * off), round(size * rr.uniform(0.88, 1.12), 2)])
for site in blocks.SITES:
    x0, y0, x1, y1 = site['box']
    rr = random.Random(int(x0 + y0))
    dirt = lin(site.get('color', '#8c7656'))
    PB = BF.get((x0 + x1) / 2, (y0 + y1) / 2, 'plain')
    nx_, ny_ = max(1, round((x1 - x0) / 40)), max(1, round((y1 - y0) / 40))
    gx = [x0 + (x1 - x0) * k / nx_ for k in range(nx_ + 1)]
    gy = [y0 + (y1 - y0) * k / ny_ for k in range(ny_ + 1)]
    for iy in range(ny_):
        for ix in range(nx_):
            sh_ = rr.uniform(0.95, 1.04)
            c4 = [(gx[ix], gy[iy]), (gx[ix + 1], gy[iy]), (gx[ix + 1], gy[iy + 1]), (gx[ix], gy[iy + 1])]
            BF.quad(PB, *[(x, Hat(x, y) + 1.4, y) for x, y in c4[::-1]], (0, 0, 1, 1), tuple(v * sh_ for v in dirt))
    if site.get('fence'):
        fc = lin(site['fence'])
        per = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for k in range(4):
            (ax, ay), (bx, by) = per[k], per[(k + 1) % 4]
            m = max(1, round(math.hypot(bx - ax, by - ay) / 36))
            for q in range(m):
                mx, my = ax + (bx - ax) * (q + 0.5) / m, ay + (by - ay) * (q + 0.5) / m
                BF.box(PB, mx, Hat(mx, my) + 1, my, math.hypot(bx - ax, by - ay) / m - 3, 11, 1.2, fc, math.atan2(by - ay, bx - ax))
    for nm, x, y, ang, sc in site.get('props', []):
        EXTRA['props'].append([nm, x, y, ang, sc])
# ---------- every street: raised sidewalks with kerbs, crosswalks at signals, street trees ----------
_mp = Image.open(REPO + ('/data/map_base.png' if os.path.exists(REPO + '/data/map_base.png') else '/data/map.png')).convert('L')
_mx = _mp.load()


def bsolid(x, y):
    tx, ty = int(x // 20), int(y // 20)
    return 0 <= tx < _mp.width and 0 <= ty < _mp.height and _mx[tx, ty] == 120


ADJ = {}
for e in EDGES:
    a, b = NODES[e[0]], NODES[e[1]]
    ln = math.hypot(b[0] - a[0], b[1] - a[1])
    if ln < 1:
        continue
    d = ((b[0] - a[0]) / ln, (b[1] - a[1]) / ln)
    ADJ.setdefault(e[0], []).append((e[3], d))
    ADJ.setdefault(e[1], []).append((e[3], (-d[0], -d[1])))
SW, KH = 24.0, 1.6
walkc, kerbc, paint = lin('#c4c1b8'), tuple(v * 0.55 for v in lin('#a8a59d')), (0.82, 0.82, 0.8)
SIG = set(W['sig'])


def hold(node, d):
    cross = [ww for ww, dd in ADJ.get(node, []) if abs(dd[0] * d[0] + dd[1] * d[1]) < 0.7]
    return (max(cross) / 2 + (0 if abs(d[0]) >= abs(d[1]) else SW), max(cross)) if cross else (0, 0)


EXTRA['trees'] = []
nwalk = ncross = 0
for ei, e in enumerate(EDGES):
    a, b, w = NODES[e[0]], NODES[e[1]], e[3]
    ln = math.hypot(b[0] - a[0], b[1] - a[1])
    if ln < 60:
        continue
    dx, dy = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
    (ta, wa), (tb, wb) = hold(e[0], (dx, dy)), hold(e[1], (dx, dy))
    run = ln - ta - tb
    if run < 40:
        continue
    n = max(1, round(run / 170))
    for side in (1, -1):
        nx, ny = -dy * side, dx * side
        for k in range(n):
            t0, t1 = ta + run * k / n, ta + run * (k + 1) / n
            sw = SW
            mxq, myq = a[0] + dx * (t0 + t1) / 2 + nx * (w / 2 + SW), a[1] + dy * (t0 + t1) / 2 + ny * (w / 2 + SW)
            if bsolid(mxq, myq):
                sw = 11.0
                if bsolid(a[0] + dx * (t0 + t1) / 2 + nx * (w / 2 + sw), a[1] + dy * (t0 + t1) / 2 + ny * (w / 2 + sw)):
                    continue
            P0 = (a[0] + dx * t0 + nx * w / 2, a[1] + dy * t0 + ny * w / 2)
            P1 = (a[0] + dx * t1 + nx * w / 2, a[1] + dy * t1 + ny * w / 2)
            Q0, Q1 = (P0[0] + nx * sw, P0[1] + ny * sw), (P1[0] + nx * sw, P1[1] + ny * sw)
            h = [Hat(*q) for q in (P0, P1, Q1, Q0)]
            WBk = BF.get(mxq, myq, 'g_walk')
            BF.quad(WBk, (P0[0], h[0] + KH, P0[1]), (P1[0], h[1] + KH, P1[1]), (Q1[0], h[2] + KH, Q1[1]), (Q0[0], h[3] + KH, Q0[1]), (0.0, 0.0, (t1 - t0) / 64.0, sw / 64.0), walkc)
            BF.quad(BF.get(mxq, myq, 'plain'), (P0[0], h[0] - 0.3, P0[1]), (P1[0], h[1] - 0.3, P1[1]), (P1[0], h[1] + KH, P1[1]), (P0[0], h[0] + KH, P0[1]), (0, 0, 1, 1), kerbc)
            nwalk += 1
        # street trees in the planting strip: close together downtown, sparser outside it
        core = CORE((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if not core and (ei + (side > 0)) % 2:
            continue
        gap = 120.0 if core else 330.0
        rr = random.Random(ei * 31 + side)
        t = ta + 45 + rr.uniform(0, gap * 0.5)
        while t < ln - tb - 45:
            x, y = a[0] + dx * t + nx * (w / 2 + 10), a[1] + dy * t + ny * (w / 2 + 10)
            if not bsolid(x, y) and not bsolid(x + nx * 16, y + ny * 16):
                EXTRA['trees'].append([round(x), round(y), round(rr.uniform(0.62, 0.95), 2)])
            t += gap * rr.uniform(0.85, 1.2)
    # ladder crosswalks on each approach to a signal
    for node, (t_, wc), sgn in ((e[0], (ta, wa), 1), (e[1], (tb, wb), -1)):
        if node not in SIG or not wc:
            continue
        o = NODES[node]
        c0 = wc / 2 + 7
        for q in range(int(w / 9)):
            lat = -w / 2 + 4.5 + q * 9
            c = [(o[0] + sgn * dx * (c0 + u) - dy * (lat + v), o[1] + sgn * dy * (c0 + u) + dx * (lat + v)) for u, v in ((0, -2.2), (17, -2.2), (17, 2.2), (0, 2.2))]
            BF.quad(BF.get(o[0], o[1], 'plain'), *[(x, Hat(x, y) + 0.45, y) for x, y in c], (0, 0, 1, 1), paint)
        sl = [(o[0] + sgn * dx * (c0 + u) - dy * v, o[1] + sgn * dy * (c0 + u) + dx * v) for u, v in ((22, -w / 2 + 2), (25, -w / 2 + 2), (25, w / 2 - 2), (22, w / 2 - 2))]
        BF.quad(BF.get(o[0], o[1], 'plain'), *[(x, Hat(x, y) + 0.45, y) for x, y in sl], (0, 0, 1, 1), paint)
        ncross += 1
print('sidewalk segments', nwalk, 'crosswalks', ncross, 'street trees', len(EXTRA['trees']))
json.dump(EXTRA, open(REPO + '/data/extras.json', 'w'), separators=(',', ':'))
# collision map: clear the tiles of removed footprints, mark the tiles of added buildings (1 tile = 20 units)
if not os.path.exists(REPO + '/data/map_base.png'):
    Image.open(REPO + '/data/map.png').save(REPO + '/data/map_base.png')
mp = Image.open(REPO + '/data/map_base.png').convert('L')
mpx = mp.load()
TL = 20
for i in GONE:
    b = W['bld'][i]
    xs, ys = b[3::2], b[4::2]
    for ty in range(int(min(ys) // TL) - 1, int(max(ys) // TL) + 2):
        for tx in range(int(min(xs) // TL) - 1, int(max(xs) // TL) + 2):
            if mpx[tx, ty] == 120:
                mpx[tx, ty] = 30
for P in ADDED:
    xs, ys = [p[0] for p in P], [p[1] for p in P]
    for ty in range(int(min(ys) // TL), int(max(ys) // TL) + 1):
        for tx in range(int(min(xs) // TL), int(max(xs) // TL) + 1):
            if pip((tx + 0.5) * TL, (ty + 0.5) * TL, xs, ys):
                mpx[tx, ty] = 120
for br in getattr(blocks, 'BRIDGES', []):
    xs, ys = [p_[0] for p_ in br['quad']], [p_[1] for p_ in br['quad']]
    for ty in range(int(min(ys) // TL) - 1, int(max(ys) // TL) + 2):
        for tx in range(int(min(xs) // TL) + 1, int(max(xs) // TL)):
            if mpx[tx, ty] == 120:
                mpx[tx, ty] = 60
mp.save(REPO + '/data/map.png')
print('extras', len(EXTRA['trees']), 'trees', len(EXTRA['props']), 'props')

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
