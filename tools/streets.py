"""Streets for the city model: kerbs with rounded corners, sidewalks, lane markings, parking lanes, crosswalks, stop
lines, tactile pads, manholes and drains, tree pits and downtown street trees. Called by tools/citygen.py.

Also decides how every junction is controlled and writes what the game needs to stand up its hardware
(data/street.json): signal poles, mast arms, heads and pedestrian heads at the signalised junctions, stop signs
with street-name blades elsewhere, and how far back each junction's stop line sits.

Signalised junctions are the real ones: the city's pedestrian push-button records (Streets/Transportation layer 7)
name every signalised intersection, and each is matched to its node in the street network (see SIGNALS in
tools/street_data.py). Units: 10 = 1 m, y runs south."""
import json, math, os, random

KH = 1.5            # kerb height
PZ = 0.45           # paint sits this far above the road
WHITE = (0.80, 0.80, 0.78)
YELLOW = (0.78, 0.56, 0.06)


def seg(ch, t):
    cum = ch['cum']
    t = max(0.0, min(ch['L'], t))
    lo, hi = 0, len(cum) - 2
    while lo < hi:
        m = (lo + hi + 1) // 2
        if cum[m] <= t:
            lo = m
        else:
            hi = m - 1
    return lo, t


def dirat(ch, t):
    """travel direction at arc length t, smoothed over a bend"""
    out = [0.0, 0.0]
    for tt in (t - 4, t + 4):
        i, _ = seg(ch, tt)
        a, b = ch['pts'][i], ch['pts'][i + 1]
        l = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
        out[0] += (b[0] - a[0]) / l; out[1] += (b[1] - a[1]) / l
    l = math.hypot(*out) or 1
    return out[0] / l, out[1] / l


def pt(ch, t, lat):
    """point at arc length t along a chain, lat to the right of travel"""
    i, t = seg(ch, t)
    a, b = ch['pts'][i], ch['pts'][i + 1]
    l = (ch['cum'][i + 1] - ch['cum'][i]) or 1
    f = (t - ch['cum'][i]) / l
    x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
    if lat:
        d = dirat(ch, t)
        x -= d[1] * lat; y += d[0] * lat
    return x, y


def samples(ch, t0, t1, step):
    ts = [t0] + [c for c in ch['cum'] if t0 + 3 < c < t1 - 3] + [t1]
    out = [t0]
    for k in range(1, len(ts)):
        n = max(1, math.ceil((ts[k] - ts[k - 1]) / step))
        out += [ts[k - 1] + (ts[k] - ts[k - 1]) * q / n for q in range(1, n + 1)]
    return out


def build(BF, W, Hat, bsolid, CORE, lin, EXTRA, sig_nodes, repo):
    NODES, EDGES, NAMES = W['nodes'], W['edges'], W['names']
    walkc = lin('#c9c6bd'); kerbtop = lin('#d4d1c8'); kerbc = tuple(v * 0.6 for v in lin('#b4b1a8'))
    plainb = lambda x, y: BF.get(x, y, 'plain')
    R = random.Random(7)
    stat = dict(walk=0, corner=0, paint=0, cross=0, stopbar=0, pad=0, manhole=0, pit=0)

    def top(B, pts, col, uv=None):
        """flat polygon (3 or 4 points) on the sidewalk surface"""
        v = [(x, Hat(x, y) + KH, y) for x, y in pts]
        if len(pts) == 4:
            BF.quad(B, v[0], v[1], v[2], v[3], uv or (0, 0, 1, 1), col)
        else:
            BF.tri(B, v, [(p[0] / 64.0, p[1] / 64.0) for p in pts], col)

    def walkpoly(pts, col=None):
        """concrete polygon with world-aligned texture, fan triangulated from the first point"""
        for k in range(1, len(pts) - 1):
            t = (pts[0], pts[k], pts[k + 1])
            c = ((t[0][0] + t[1][0] + t[2][0]) / 3, (t[0][1] + t[1][1] + t[2][1]) / 3)
            ox, oy = math.floor(c[0] / 64.0), math.floor(c[1] / 64.0)
            BF.tri(BF.get(c[0], c[1], 'g_walk'), [(x, Hat(x, y) + KH, y) for x, y in t], [(x / 64.0 - ox, y / 64.0 - oy) for x, y in t], col or walkc)

    def face(p0, p1):
        h0, h1 = Hat(*p0), Hat(*p1)
        BF.quad(plainb(*p0), (p0[0], h0 - 0.3, p0[1]), (p1[0], h1 - 0.3, p1[1]), (p1[0], h1 + KH, p1[1]), (p0[0], h0 + KH, p0[1]), (0, 0, 1, 1), kerbc)

    def paint(pts, col, z=PZ):
        BF.quad(plainb(*pts[0]), *[(x, Hat(x, y) + z, y) for x, y in pts], (0, 0, 1, 1), col)
        stat['paint'] += 1

    def line(o, d, t0, t1, lat, wd, col, dash=None):
        """stripe along direction d from o, between t0 and t1, centred lat to the right of d"""
        if t1 - t0 < 4:
            return
        r = (-d[1], d[0])
        segs = []
        if dash:
            t = t0
            while t < t1:
                segs.append((t, min(t1, t + dash[0]))); t += dash[0] + dash[1]
        else:
            n = max(1, math.ceil((t1 - t0) / 70.0))
            segs = [(t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n) for k in range(n)]
        for a, b in segs:
            paint([(o[0] + d[0] * a + r[0] * (lat - wd / 2), o[1] + d[1] * a + r[1] * (lat - wd / 2)), (o[0] + d[0] * b + r[0] * (lat - wd / 2), o[1] + d[1] * b + r[1] * (lat - wd / 2)),
                   (o[0] + d[0] * b + r[0] * (lat + wd / 2), o[1] + d[1] * b + r[1] * (lat + wd / 2)), (o[0] + d[0] * a + r[0] * (lat + wd / 2), o[1] + d[1] * a + r[1] * (lat + wd / 2))], col)

    def disc(x, y, rad, col, z=PZ - 0.1, n=10):
        B = plainb(x, y); c = (x, Hat(x, y) + z, y)
        for k in range(n):
            a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            p0, p1 = (x + rad * math.cos(a0), y + rad * math.sin(a0)), (x + rad * math.cos(a1), y + rad * math.sin(a1))
            BF.tri(B, [c, (p1[0], Hat(*p1) + z, p1[1]), (p0[0], Hat(*p0) + z, p0[1])], [(0, 0), (1, 0), (0, 1)], col)

    # ---------- streets as chains: the network has shape points every few metres, so walk through them from junction to junction ----------
    inc = {}
    for ei, e in enumerate(EDGES):
        if math.hypot(NODES[e[0]][0] - NODES[e[1]][0], NODES[e[0]][1] - NODES[e[1]][1]) < 0.5:
            continue
        inc.setdefault(e[0], []).append(ei); inc.setdefault(e[1], []).append(ei)
    isj = lambda n: len(inc[n]) != 2 or EDGES[inc[n][0]][2] != EDGES[inc[n][1]][2] or EDGES[inc[n][0]][4] != EDGES[inc[n][1]][4]
    JUNC = set(n for n in inc if isj(n))
    used, CHAINS, LEG = set(), [], {}

    def walk(n0, ei):
        ids, cur, e = [n0], n0, ei
        while True:
            used.add(e)
            cur = EDGES[e][1] if EDGES[e][0] == cur else EDGES[e][0]
            ids.append(cur)
            if cur in JUNC or cur == n0:
                break
            e = inc[cur][1] if inc[cur][0] == e else inc[cur][0]
        return ids
    starts = [(n, ei) for n in JUNC for ei in inc[n]] + [(EDGES[ei][0], ei) for ei in range(len(EDGES)) if EDGES[ei][0] in inc]
    for n0, ei in starts:
        if ei in used or n0 not in inc:
            continue
        ids = walk(n0, ei)
        pts = [tuple(NODES[q]) for q in ids]
        cum = [0.0]
        for k in range(1, len(pts)):
            cum.append(cum[-1] + math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]))
        e = EDGES[ei]
        mid = pts[len(pts) // 2]
        core = CORE((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2) and CORE(*mid)
        ch = dict(ids=ids, pts=pts, cum=cum, L=cum[-1], w=e[2] * 10.0, nm=e[4], core=core, sw=36.0 if core else 22.0, A=None, B=None)
        if ch['L'] < 2:
            continue
        CHAINS.append(ch)
        for end, nd in ((0, ids[0]), (1, ids[-1])):
            if end == 1 and ids[-1] == ids[0]:
                continue
            q = pt(ch, min(60.0, ch['L'] * 0.5), 0) if end == 0 else pt(ch, ch['L'] - min(60.0, ch['L'] * 0.5), 0)
            dl = math.hypot(q[0] - NODES[nd][0], q[1] - NODES[nd][1]) or 1
            L = dict(ch=ch, end=end, d=((q[0] - NODES[nd][0]) / dl, (q[1] - NODES[nd][1]) / dl), w=ch['w'], ln=ch['L'], nm=ch['nm'], sw=ch['sw'], core=core, cw=0.0, ccw=0.0)
            ch['A' if end == 0 else 'B'] = L
            LEG.setdefault(nd, []).append(L)

    def isect(n, d1, p1, h1, d2, p2, h2):
        # n + d1*t + p1*h1 = n + d2*s + p2*h2
        bx, by = p2[0] * h2 - p1[0] * h1, p2[1] * h2 - p1[1] * h1
        det = d1[0] * (-d2[1]) - (-d2[0]) * d1[1]
        if abs(det) < 1e-6:
            return None
        t = (bx * (-d2[1]) - (-d2[0]) * by) / det
        s = (d1[0] * by - d1[1] * bx) / det
        return t, s

    CORNERS = []
    for ni, legs in LEG.items():
        n = NODES[ni]
        for L in legs:
            L['ang'] = math.atan2(L['d'][1], L['d'][0])
        legs.sort(key=lambda L: L['ang'])
        m = len(legs)
        if m < 2:
            continue
        for k in range(m):
            L1, L2 = legs[k], legs[(k + 1) % m]
            phi = (L2['ang'] - L1['ang']) % (2 * math.pi)
            if m == 2 and k == 1:
                phi = (L2['ang'] - L1['ang']) % (2 * math.pi)
            if phi > 2.62 or phi < 0.5:
                continue
            d1, d2 = L1['d'], L2['d']
            p1, p2 = (-d1[1], d1[0]), (d2[1], -d2[0])
            r = isect(n, d1, p1, L1['w'] / 2, d2, p2, L2['w'] / 2)
            if not r:
                continue
            rad = 45.0 if (L1['core'] or L2['core']) else 32.0
            td = rad / math.tan(phi / 2)
            lim = min(L1['ln'], L2['ln']) * 0.42
            if r[0] + td > lim or r[1] + td > lim:
                k_ = max(0.0, min(1.0, (lim - max(r[0], r[1])) / max(td, 1e-6)))
                td *= k_; rad *= k_
                if rad < 6:
                    continue
            t1, t2 = r[0] + td, r[1] + td
            L1['cw'], L2['ccw'] = max(L1['cw'], t1), max(L2['ccw'], t2)
            T1 = (n[0] + d1[0] * t1 + p1[0] * L1['w'] / 2, n[1] + d1[1] * t1 + p1[1] * L1['w'] / 2)
            T2 = (n[0] + d2[0] * t2 + p2[0] * L2['w'] / 2, n[1] + d2[1] * t2 + p2[1] * L2['w'] / 2)
            cen = (T1[0] + p1[0] * rad, T1[1] + p1[1] * rad)
            ro = isect(n, d1, p1, L1['w'] / 2 + L1['sw'], d2, p2, L2['w'] / 2 + L2['sw'])
            OC = (n[0] + d1[0] * ro[0] + p1[0] * (L1['w'] / 2 + L1['sw']), n[1] + d1[1] * ro[0] + p1[1] * (L1['w'] / 2 + L1['sw']))
            CORNERS.append(dict(node=ni, L1=L1, L2=L2, T1=T1, T2=T2, cen=cen, rad=rad, OC=OC, p1=p1, p2=p2, phi=phi))

    # ---------- how each junction is controlled ----------
    SIG = set(sig_nodes)
    CTRL = {}
    for ni, legs in LEG.items():
        if ni in SIG and len(legs) >= 3:
            CTRL[ni] = ('sig', legs)
        elif len(legs) >= 3:
            wm = max(L['w'] for L in legs)
            minor = [L for L in legs if L['w'] < wm]
            if minor:
                CTRL[ni] = ('stop', minor)
            elif any(L['core'] for L in legs):
                CTRL[ni] = ('stop', legs)
    for ni, legs in LEG.items():
        c = CTRL.get(ni)
        for L in legs:
            L['s0'] = max(L['cw'], L['ccw'], L['w'] * 0.0)
            L['ctl'] = 'sig' if c and c[0] == 'sig' else ('stop' if c and L in c[1] else None)
            L['xwalk'] = bool(c) and (c[0] == 'sig' or L['core'])
            L['bar'] = L['s0'] + (40 if L['xwalk'] else 8)       # where the stop line sits, measured from the node

    # ---------- corners: kerb return, sidewalk fill, tactile pads, drain ----------
    for C in CORNERS:
        L1, L2, T1, T2, cen, rad = C['L1'], C['L2'], C['T1'], C['T2'], C['cen'], C['rad']
        a0 = math.atan2(T1[1] - cen[1], T1[0] - cen[0]); a1 = math.atan2(T2[1] - cen[1], T2[0] - cen[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        ns = 7
        arc = [(cen[0] + rad * math.cos(a0 + da * q / ns), cen[1] + rad * math.sin(a0 + da * q / ns)) for q in range(ns + 1)]
        O1 = (T1[0] + C['p1'][0] * L1['sw'], T1[1] + C['p1'][1] * L1['sw']); O2 = (T2[0] + C['p2'][0] * L2['sw'], T2[1] + C['p2'][1] * L2['sw'])
        if bsolid(*C['OC']):
            poly = [cen] + arc              # a building stands on the corner: keep the walk tight to the kerb
        else:
            poly = [C['OC'], O1] + arc + [O2]
        walkpoly(poly)
        for q in range(ns):
            face(arc[q + 1], arc[q])
        stat['corner'] += 1
        ctl = CTRL.get(C['node'])
        if ctl and (ctl[0] == 'sig' or L1['core'] or L2['core']):
            # tactile pads where each crosswalk meets the corner
            for L, T, p in ((L1, T1, C['p1']), (L2, T2, C['p2'])):
                d = L['d']
                c = (T[0] + d[0] * 17 + p[0] * 5.5, T[1] + d[1] * 17 + p[1] * 5.5)
                q = [(c[0] + d[0] * u + p[0] * v, c[1] + d[1] * u + p[1] * v) for u, v in ((-7, -3.5), (7, -3.5), (7, 3.5), (-7, 3.5))]
                BF.quad(plainb(*c), *[(x, Hat(x, y) + KH + 0.12, y) for x, y in q], (0, 0, 1, 1), (0.72, 0.5, 0.05))
                stat['pad'] += 1
        # storm drain in the gutter just before the corner
        d = L1['d']; g = (T1[0] + d[0] * 9 - C['p1'][0] * 3.2, T1[1] + d[1] * 9 - C['p1'][1] * 3.2)
        q = [(g[0] + d[0] * u + C['p1'][0] * v, g[1] + d[1] * u + C['p1'][1] * v) for u, v in ((-4.5, -2.8), (4.5, -2.8), (4.5, 2.8), (-4.5, 2.8))]
        paint(q, (0.02, 0.02, 0.022), PZ - 0.2)

    # ---------- every street: sidewalks, kerbs, markings ----------
    def cline(ch, t0, t1, lat, wd, col, dash=None):
        if t1 - t0 < 4:
            return
        if dash:
            ts, t = [], t0
            while t < t1:
                ts.append((t, min(t1, t + dash[0]))); t += dash[0] + dash[1]
        else:
            q = samples(ch, t0, t1, 70.0); ts = [(q[k], q[k + 1]) for k in range(len(q) - 1)]
        for a_, b_ in ts:
            paint([pt(ch, a_, lat - wd / 2), pt(ch, b_, lat - wd / 2), pt(ch, b_, lat + wd / 2), pt(ch, a_, lat + wd / 2)], col)

    trees = []
    for ci, ch in enumerate(CHAINS):
        ln, w, LA, LB, core, sw0 = ch['L'], ch['w'], ch['A'], ch['B'], ch['core'], ch['sw']
        for side in (1, -1):
            ta = (LA['cw'] if side > 0 else LA['ccw']) if LA else 0.0
            tb = (LB['ccw'] if side > 0 else LB['cw']) if LB else 0.0
            if ln - ta - tb < 6:
                continue
            ts = samples(ch, ta, ln - tb, 150.0)
            for k in range(len(ts) - 1):
                t0, t1 = ts[k], ts[k + 1]
                tm = (t0 + t1) / 2
                sw = sw0
                while sw > 9 and bsolid(*pt(ch, tm, side * (w / 2 + sw))):
                    sw -= 12.0 if sw > 24 else 11.0
                if sw < 9:
                    continue
                P0, P1 = pt(ch, t0, side * w / 2), pt(ch, t1, side * w / 2)
                K0, K1 = pt(ch, t0, side * (w / 2 + 1.6)), pt(ch, t1, side * (w / 2 + 1.6))
                Q0, Q1 = pt(ch, t0, side * (w / 2 + sw)), pt(ch, t1, side * (w / 2 + sw))
                top(plainb(*P0), [P0, P1, K1, K0] if side > 0 else [P1, P0, K0, K1], kerbtop)
                walkpoly([K0, K1, Q1, Q0] if side > 0 else [K1, K0, Q0, Q1])
                face(P0, P1) if side < 0 else face(P1, P0)
                stat['walk'] += 1
            # street trees in pits along the kerb: downtown every 12 m or so, on the wide streets every 30 m
            if core or w >= 140:
                gap = 125.0 if core else 300.0
                rr = random.Random(ci * 31 + side)
                t = ta + 40 + rr.uniform(0, gap * 0.5)
                while t < ln - tb - 40:
                    x, y = pt(ch, t, side * (w / 2 + 9))
                    if not bsolid(x, y) and not bsolid(*pt(ch, t, side * (w / 2 + 23))):
                        trees.append([round(x), round(y), round(rr.uniform(0.75, 1.1), 2), rr.choice((0, 0, 2, 2, 3)) if core else rr.choice((0, 1))])
                        if core:
                            q = [pt(ch, t + u, side * (w / 2 + 9 + v)) for u, v in ((-7, -6), (7, -6), (7, 6), (-7, 6))]
                            BF.quad(plainb(x, y), *[(px, Hat(px, py) + KH + 0.1, py) for px, py in (q if side > 0 else q[::-1])], (0, 0, 1, 1), (0.09, 0.075, 0.06))
                            stat['pit'] += 1
                    t += gap * rr.uniform(0.85, 1.2)
        # ---- paint
        end = lambda L: 0.0 if L is None else (L['bar'] + 5 if (L['ctl'] or L['xwalk']) else L['s0'])
        m0, m1 = end(LA), ln - end(LB)
        if m1 - m0 > 30:
            if w >= 120 or core:
                cline(ch, m0, m1, -1.5, 1.2, YELLOW); cline(ch, m0, m1, 1.5, 1.2, YELLOW)
            if w >= 140:
                for s_ in (-1, 1):
                    cline(ch, m0 + 6, m1 - 6, s_ * w / 4, 1.1, WHITE, (30, 90))
                    cline(ch, m0, m1, s_ * (w / 2 - 4), 1.1, WHITE)
            elif core or w >= 120:
                # parking lanes: a line 2.3 m off each kerb with a tick at every stall
                for s_ in (-1, 1):
                    cline(ch, m0 + 20, m1 - 20, s_ * (w / 2 - 23), 1.0, WHITE)
                    t = m0 + 20
                    while t < m1 - 20:
                        paint([pt(ch, t - 0.5, s_ * (w / 2 - 23)), pt(ch, t + 0.5, s_ * (w / 2 - 23)), pt(ch, t + 0.5, s_ * (w / 2 - 14)), pt(ch, t - 0.5, s_ * (w / 2 - 14))], WHITE)
                        t += 62
            t = m0 + R.uniform(60, 260)
            while t < m1 - 40:
                lat = R.choice((-1, 1)) * R.uniform(6, max(7, w / 2 - 28))
                disc(*pt(ch, t, lat), 3.4, (0.045, 0.045, 0.05)); stat['manhole'] += 1
                t += R.uniform(380, 900)
        for L, o in ((LA, ch['pts'][0]), (LB, ch['pts'][-1])):
            if L is None:
                continue
            dd = L['d']
            if L['xwalk']:
                c0 = L['s0'] + 6
                if L['ctl'] == 'sig' or w >= 120:
                    nb = int((w - 6) / 12)
                    for q in range(nb):
                        line(o, dd, c0, c0 + 28, -(nb - 1) * 6 + q * 12, 6.0, WHITE)
                else:
                    line((o[0] + dd[0] * c0, o[1] + dd[1] * c0), (-dd[1], dd[0]), -w / 2 + 2, w / 2 - 2, 0, 1.6, WHITE)
                    line((o[0] + dd[0] * (c0 + 26), o[1] + dd[1] * (c0 + 26)), (-dd[1], dd[0]), -w / 2 + 2, w / 2 - 2, 0, 1.6, WHITE)
                stat['cross'] += 1
            if L['ctl']:
                rgt = (dd[1], -dd[0])
                line((o[0] + dd[0] * (L['bar'] + 2.2), o[1] + dd[1] * (L['bar'] + 2.2)), rgt, 1.0, w / 2 - 2, 0, 4.4, WHITE)
                stat['stopbar'] += 1

    # ---------- what the game stands up ----------
    out = dict(r={}, signals=[], stops=[], names=NAMES)
    for ni, legs in LEG.items():
        if ni in CTRL:
            out['r'][ni] = round(max(L['bar'] for L in legs) + 4)
    grp = lambda v: 0 if abs(v[1]) > abs(v[0]) else 1          # 0 = north-south movement, 1 = east-west
    for ni, (kind, sel) in CTRL.items():
        n = NODES[ni]; legs = LEG[ni]
        if kind == 'stop':
            for L in sel:
                dd = L['d']; h = (-dd[0], -dd[1]); rgt = (-h[1], h[0])
                x, y = n[0] + dd[0] * (L['bar'] + 4) + rgt[0] * (L['w'] / 2 + 7), n[1] + dd[1] * (L['bar'] + 4) + rgt[1] * (L['w'] / 2 + 7)
                if bsolid(x, y):
                    continue
                cross = [M['nm'] for M in legs if abs(M['d'][0] * dd[0] + M['d'][1] * dd[1]) < 0.7]
                out['stops'].append([round(x), round(y), round(math.atan2(dd[1], dd[0]), 3), L['nm'], cross[0] if cross else -1, 1 if len(sel) == len(legs) else 0])
            continue
        S = dict(n=ni, x=n[0], y=n[1], ap=[], cab=None)
        for L in legs:
            dd = L['d']; h = (-dd[0], -dd[1]); rgt = (-h[1], h[0])           # h: the way traffic on this leg heads into the junction
            opp = next((M for M in legs if M['d'][0] * h[0] + M['d'][1] * h[1] > 0.7), None)
            cross = [M for M in legs if abs(M['d'][0] * dd[0] + M['d'][1] * dd[1]) < 0.7]
            far = (opp['s0'] + 9) if opp else (max([M['w'] for M in cross] or [100]) / 2 + 14)
            wf = opp['w'] if opp else L['w']
            px, py = n[0] + h[0] * far + rgt[0] * (wf / 2 + 9), n[1] + h[1] * far + rgt[1] * (wf / 2 + 9)
            lane = max(16.0, min(32.0, L['w'] / 10 * 2))
            heads = [wf / 2 + 9 - lane] + ([wf / 2 + 9 - (wf / 4 + 16)] if wf >= 140 else []) + [wf / 2 + 9 - 4]
            S['ap'].append(dict(x=round(px, 1), y=round(py, 1), h=[round(h[0], 4), round(h[1], 4)], g=grp(h), arm=round(wf / 2 + 9 - 2, 1), heads=[round(v, 1) for v in heads],
                                nm=cross[0]['nm'] if cross else -1, own=L['nm'], xw=round(wf, 1)))
        c0 = next((C for C in CORNERS if C['node'] == ni), None)
        if c0:
            S['cab'] = [round(c0['OC'][0] * 0.75 + c0['cen'][0] * 0.25, 1), round(c0['OC'][1] * 0.75 + c0['cen'][1] * 0.25, 1), round(math.atan2(c0['L1']['d'][1], c0['L1']['d'][0]), 3)]
        out['signals'].append(S)
    EXTRA['trees'] = trees
    # ---------- ground mask: redraw the road channel from this geometry so asphalt runs exactly kerb to kerb (1 px = 1 m) ----------
    from PIL import Image, ImageDraw
    src = repo + '/data/mask_roads0.png'
    if not os.path.exists(src):
        Image.open(repo + '/data/mask.png').save(src)
    mk = Image.open(src).convert('RGB')
    r0, g0, b0 = mk.split()
    S_ = 4
    big = Image.new('L', (mk.width * S_, mk.height * S_), 0)
    dr = ImageDraw.Draw(big)
    k_ = S_ / 10.0
    for ch in CHAINS:
        dr.line([(x * k_, y * k_) for x, y in ch['pts']], fill=255, width=int(round((ch['w'] + 14) * k_)), joint='curve')
        for x, y in (ch['pts'][0], ch['pts'][-1]):
            rr_ = (ch['w'] + 14) / 2 * k_
            dr.ellipse([x * k_ - rr_, y * k_ - rr_, x * k_ + rr_, y * k_ + rr_], fill=255)
    for C in CORNERS:
        n = NODES[C['node']]
        a0 = math.atan2(C['T1'][1] - C['cen'][1], C['T1'][0] - C['cen'][0]); a1 = math.atan2(C['T2'][1] - C['cen'][1], C['T2'][0] - C['cen'][0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        rad = max(1.0, C['rad'] - 7)
        arc = [(C['cen'][0] + rad * math.cos(a0 + da * q / 8), C['cen'][1] + rad * math.sin(a0 + da * q / 8)) for q in range(9)]
        dr.polygon([(x * k_, y * k_) for x, y in [tuple(n)] + arc], fill=255)
    newr = big.resize(mk.size, Image.LANCZOS)
    import numpy as np
    R_, G_ = np.asarray(newr).copy(), np.asarray(g0).copy()
    old = np.asarray(r0)
    G_[(old > 100) & (R_ < 100) & (G_ < 128)] = 128        # asphalt the old mask had where there is no street: treat as paved ground
    Image.merge('RGB', (Image.fromarray(R_), Image.fromarray(G_), b0)).save(repo + '/data/mask.png', optimize=True)
    json.dump(out, open(repo + '/data/street.json', 'w'), separators=(',', ':'))
    print('streets:', stat, '| signals', len(out['signals']), 'stop signs', len(out['stops']), 'street trees', len(trees))
    return out
