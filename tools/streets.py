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
STRIP = 14.0        # planting strip between kerb and walk outside downtown
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


def chains(W, CORE):
    """junction-to-junction runs of the network, and the legs meeting at each junction"""
    NODES, EDGES = W['nodes'], W['edges']
    # ---------- streets as chains: the network has shape points every few metres, so walk through them from junction to junction ----------
    inc = {}
    for ei, e in enumerate(EDGES):
        if math.hypot(NODES[e[0]][0] - NODES[e[1]][0], NODES[e[0]][1] - NODES[e[1]][1]) < 0.5:
            continue
        inc.setdefault(e[0], []).append(ei); inc.setdefault(e[1], []).append(ei)
    isj = lambda n: len(inc[n]) != 2 or EDGES[inc[n][0]][2] != EDGES[inc[n][1]][2] or EDGES[inc[n][0]][4] != EDGES[inc[n][1]][4]
    JUNC = set(n for n in inc if isj(n))
    used, CHAINS, LEG, eids = set(), [], {}, []

    def walk(n0, ei):
        ids, cur, e = [n0], n0, ei
        eids.clear()
        while True:
            used.add(e); eids.append(e)
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
        ch = dict(ids=ids, eids=list(eids), pts=pts, cum=cum, L=cum[-1], w=e[2] * 10.0, nm=e[4], cls=e[5], core=core, sw=36.0 if core else 30.0, A=None, B=None, med=[])
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
    return CHAINS, LEG


def build(BF, W, Hat, bsolid, CORE, lin, EXTRA, sig_nodes, repo):
    NODES, EDGES, NAMES = W['nodes'], W['edges'], W['names']
    walkc = lin('#c9c6bd'); kerbtop = lin('#d4d1c8'); kerbc = tuple(v * 0.6 for v in lin('#b4b1a8'))
    plainb = lambda x, y: BF.get(x, y, 'plain')
    R = random.Random(7)
    out_tiles = [None]
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

    CHAINS, LEG = chains(W, CORE)
    JUNC = set(LEG)
    LANES = []
    try:
        import blocks as _bl
        PARKING = getattr(_bl, 'PARKING', [])
    except Exception:
        PARKING = []
    for ch in CHAINS:
        my_ = pt(ch, ch['L'] / 2, 0)[1]
        if any(NAMES[ch['nm']] == nm_ and ya < my_ < yb for nm_, ya, yb, sd in PARKING):
            ch['core'] = True; ch['sw'] = 36.0          # a downtown block by what the aerial shows, whatever the core box says
            for L_ in (ch['A'], ch['B']):
                if L_:
                    L_['core'] = True; L_['sw'] = 36.0
    MED = []
    mf = repo + '/data/dossier/streets.json'
    if os.path.exists(mf):
        for poly in json.load(open(mf)).get('medians', []):
            cx, cy = sum(q[0] for q in poly) / len(poly), sum(q[1] for q in poly) / len(poly)
            best = None
            for ch in CHAINS:
                xs = [q[0] for q in ch['pts']]; ys = [q[1] for q in ch['pts']]
                if not (min(xs) - 60 < cx < max(xs) + 60 and min(ys) - 60 < cy < max(ys) + 60):
                    continue
                t = 0.0
                while t <= ch['L']:
                    q = pt(ch, t, 0); dq = math.hypot(q[0] - cx, q[1] - cy)
                    if best is None or dq < best[0]:
                        best = (dq, ch, t)
                    t += 15
            if best and best[0] < 45:
                ch = best[1]
                half = max(math.hypot(q[0] - cx, q[1] - cy) for q in poly)
                ch['med'].append((best[2] - half - 6, best[2] + half + 6))
                MED.append((poly, ch, best[2], half))

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
            top_cls = min(L['ch']['cls'] for L in legs)      # street class: lower is more major
            minor = [L for L in legs if L['ch']['cls'] > top_cls]
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
                if not core and sw >= 30:
                    # outside downtown: kerb, a 1.2 m planting strip left as ground, then the walk
                    S0, S1 = pt(ch, t0, side * (w / 2 + STRIP)), pt(ch, t1, side * (w / 2 + STRIP))
                    walkpoly([S0, S1, Q1, Q0] if side > 0 else [S1, S0, Q0, Q1])
                    face(S0, S1) if side < 0 else face(S1, S0)
                    face(K1, K0) if side < 0 else face(K0, K1)
                else:
                    walkpoly([K0, K1, Q1, Q0] if side > 0 else [K1, K0, Q0, Q1])
                face(P0, P1) if side < 0 else face(P1, P0)
                stat['walk'] += 1
            ch['run' + ('R' if side > 0 else 'L')] = (ta, ln - tb)
        # ---- paint
        end = lambda L: 0.0 if L is None else (L['bar'] + 5 if (L['ctl'] or L['xwalk']) else L['s0'])
        m0, m1 = end(LA), ln - end(LB)
        if m1 - m0 > 30:
            marked = core or ch['cls'] < 8
            lane_o = max(16.0, min(32.0, w / 5.0))            # where the game's traffic drives, measured from the centreline

            def split(t0, t1):
                """the stretch t0..t1 with the median islands cut out"""
                parts, a_ = [], t0
                for ma, mb in sorted(ch['med']):
                    if mb < a_ or ma > t1:
                        continue
                    if ma > a_:
                        parts.append((a_, ma))
                    a_ = max(a_, mb)
                if a_ < t1:
                    parts.append((a_, t1))
                return parts
            # parking seen in the aerials (PARKING in tools/blocks.py): 45 degree stalls on one side, parallel on the other,
            # and the centre line moved off-centre to suit, as on the real street
            sh_, pk = 0.0, None
            for nm_, ya, yb, sd in PARKING:
                my_ = pt(ch, ln / 2, 0)[1]
                if NAMES[ch['nm']] == nm_ and ya < my_ < yb and w >= 132 and not ch['med']:
                    es = 1 if pt(ch, ln / 2, 1)[0] > pt(ch, ln / 2, 0)[0] else -1
                    an = es if sd == 'E' else -es
                    pk = {an: 52.0, -an: 23.0}; sh_ = -an * 14.5
                    lo = (w - 75) / 4
                    for k_ in range(len(ch['eids'])):
                        LANES.append([ch['ids'][k_], ch['ids'][k_ + 1], sh_, round(lo, 1)])
            if marked:
                for a_, b_ in split(m0, m1):
                    cline(ch, a_, b_, sh_ - 1.5, 1.2, YELLOW); cline(ch, a_, b_, sh_ + 1.5, 1.2, YELLOW)
                for ma, mb in ch['med']:
                    for s_ in (-1, 1):
                        cline(ch, max(m0, ma), min(m1, mb), s_ * 19, 1.2, YELLOW)
            if ch['cls'] in (4, 5) and w >= 130:
                for s_ in (-1, 1):
                    cline(ch, m0 + 6, m1 - 6, s_ * w / 4, 1.1, WHITE, (30, 90))
                    cline(ch, m0, m1, s_ * (w / 2 - 4), 1.1, WHITE)
            elif marked:
                # parking by what fits beside the traffic lane at the real kerb-to-kerb width:
                # 45 degree stalls need 5.2 m, parallel stalls 2.3 m
                depth0 = 52.0 if (w / 2 - 52 >= lane_o + 7.5 and not ch['med']) else 23.0 if w / 2 - 23 >= lane_o + 13 else 0
                if depth0 or pk:
                    for s_ in (-1, 1):
                        depth = pk[s_] if pk else depth0
                        cline(ch, m0 + 20, m1 - 20, s_ * (w / 2 - depth), 1.0, WHITE)
                        t = m0 + 22
                        while t < m1 - 22 - (depth if depth > 30 else 0):
                            if depth > 30:
                                q0, q1 = pt(ch, t + depth * s_ * 0.0, s_ * (w / 2 - depth)), pt(ch, t + depth, s_ * (w / 2 - 0.5))
                                dx_, dy_ = q1[0] - q0[0], q1[1] - q0[1]; l_ = math.hypot(dx_, dy_) or 1
                                nx_, ny_ = -dy_ / l_ * 0.5, dx_ / l_ * 0.5
                                paint([(q0[0] - nx_, q0[1] - ny_), (q1[0] - nx_, q1[1] - ny_), (q1[0] + nx_, q1[1] + ny_), (q0[0] + nx_, q0[1] + ny_)], WHITE)
                                t += 37
                            else:
                                paint([pt(ch, t - 0.5, s_ * (w / 2 - 23)), pt(ch, t + 0.5, s_ * (w / 2 - 23)), pt(ch, t + 0.5, s_ * (w / 2 - 14)), pt(ch, t - 0.5, s_ * (w / 2 - 14))], WHITE)
                                t += 62
            t = m0 + R.uniform(60, 260)
            while t < m1 - 40:
                lat = R.choice((-1, 1)) * R.uniform(22, max(23, w / 2 - 28))
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

    # ---------- kerbside and median trees: the detected crowns (tools/trees.py detect) that stand over a street ----------
    used = []
    rf = repo + '/data/dossier/trees_raw.json'
    if os.path.exists(rf):
        raw = json.load(open(rf))['trees']
        grid = {}
        for ci, ch in enumerate(CHAINS):
            for k in range(len(ch['pts']) - 1):
                a_, b_ = ch['pts'][k], ch['pts'][k + 1]
                for gx in range(int(min(a_[0], b_[0]) // 300) - 1, int(max(a_[0], b_[0]) // 300) + 2):
                    for gy in range(int(min(a_[1], b_[1]) // 300) - 1, int(max(a_[1], b_[1]) // 300) + 2):
                        grid.setdefault((gx, gy), []).append((ci, k))
        placed = {}
        for ti, (X, Y, crown, ever, tall) in enumerate(raw):
            best = None
            for ci, k in grid.get((int(X // 300), int(Y // 300)), ()):
                ch = CHAINS[ci]; a_, b_ = ch['pts'][k], ch['pts'][k + 1]
                dx_, dy_ = b_[0] - a_[0], b_[1] - a_[1]; l2 = dx_ * dx_ + dy_ * dy_ or 1
                f = max(0.0, min(1.0, ((X - a_[0]) * dx_ + (Y - a_[1]) * dy_) / l2))
                qx, qy = a_[0] + dx_ * f, a_[1] + dy_ * f
                dq = math.hypot(X - qx, Y - qy)
                if best is None or dq < best[0]:
                    lat = ((X - qx) * -dy_ + (Y - qy) * dx_) / math.sqrt(l2)
                    best = (dq, ci, ch['cum'][k] + f * math.sqrt(l2), lat)
            if not best:
                continue
            dq, ci, t, lat = best
            ch = CHAINS[ci]; w = ch['w']; side = 1 if lat > 0 else -1
            if abs(lat) > w / 2 + (ch['sw'] if ch['core'] else STRIP + 2):
                continue                                   # in a yard or a lot: tools/trees.py places it where it is
            kind = 5 if ever else (3 if crown < 20 else 2 if crown < 25 and ch['core'] else 0 if crown < 40 else 1)
            sc = round(max(0.6, min(1.35, crown / (40, 62, 18, 26, 44, 40)[kind] * 1.1)), 2)
            if any(ma <= t <= mb for ma, mb in ch['med']) and abs(lat) < 24:
                q = pt(ch, t, 0)
                if all(abs(t - t2) > 45 for t2 in placed.setdefault((ci, 0), [])):
                    placed[(ci, 0)].append(t); trees.append([round(q[0]), round(q[1]), sc, kind]); stat['medtree'] = stat.get('medtree', 0) + 1
                used.append(ti); continue
            run = ch.get('runR' if side > 0 else 'runL')
            if abs(lat) < w / 2 - 50 or not run or not (run[0] + 12 < t < run[1] - 12):
                used.append(ti) if abs(lat) < w / 2 else None   # over the travel lanes or in a junction: no place to stand
                continue
            off = 9.0 if ch['core'] else STRIP / 2 + 1
            x, y = pt(ch, t, side * (w / 2 + off))
            used.append(ti)
            if bsolid(x, y) or any(abs(t - t2) < 45 for t2 in placed.setdefault((ci, side), [])):
                continue
            placed[(ci, side)].append(t)
            trees.append([round(x), round(y), sc, kind])
            stat['kerbtree'] = stat.get('kerbtree', 0) + 1
            if ch['core']:
                q = [pt(ch, t + u, side * (w / 2 + 9 + v)) for u, v in ((-7, -6), (7, -6), (7, 6), (-7, 6))]
                BF.quad(plainb(x, y), *[(px, Hat(px, py) + KH + 0.1, py) for px, py in (q if side > 0 else q[::-1])], (0, 0, 1, 1), (0.09, 0.075, 0.06))
                stat['pit'] += 1
    EXTRA['used'] = used

    # ---------- median islands (real kerb loops from the city's kerb lines): raised, planted, with trees ----------
    soil = (0.10, 0.15, 0.06)
    for poly, ch, tc, half in MED:
        cx, cy = sum(q[0] for q in poly) / len(poly), sum(q[1] for q in poly) / len(poly)
        pts_ = [tuple(q) for q in poly]
        if math.hypot(pts_[0][0] - pts_[-1][0], pts_[0][1] - pts_[-1][1]) < 2:
            pts_ = pts_[:-1]
        for k in range(len(pts_)):
            a_, b_ = pts_[k], pts_[(k + 1) % len(pts_)]
            face(a_, b_); face(b_, a_)
            ins = lambda q: (q[0] + (cx - q[0]) * 0.12, q[1] + (cy - q[1]) * 0.12)
            ia, ib = ins(a_), ins(b_)
            top(plainb(*a_), [a_, b_, ib, ia], kerbtop)
            BF.tri(plainb(cx, cy), [(ia[0], Hat(*ia) + KH + 0.6, ia[1]), (ib[0], Hat(*ib) + KH + 0.6, ib[1]), (cx, Hat(cx, cy) + KH + 1.2, cy)], [(0, 0), (1, 0), (0, 1)], tuple(v * R.uniform(0.9, 1.1) for v in soil))
        stat['median'] = stat.get('median', 0) + 1

    # ---------- what the game stands up ----------
    out = dict(r={}, signals=[], stops=[], names=NAMES, xw=[], stopleg=[], lanes=LANES)
    for ni, legs in LEG.items():
        if ni in CTRL:
            out['r'][ni] = round(max(L['bar'] for L in legs) + 4)
    grp = lambda v: 0 if abs(v[1]) > abs(v[0]) else 1          # 0 = north-south movement, 1 = east-west
    for ni, (kind, sel) in CTRL.items():
        n = NODES[ni]; legs = LEG[ni]
        if kind == 'stop':
            for L in sel:
                out['stopleg'].append([ni, L['ch']['ids'][1] if L['end'] == 0 else L['ch']['ids'][-2]])
                dd = L['d']; h = (-dd[0], -dd[1]); rgt = (-h[1], h[0])
                x, y = n[0] + dd[0] * (L['bar'] + 4) + rgt[0] * (L['w'] / 2 + 7), n[1] + dd[1] * (L['bar'] + 4) + rgt[1] * (L['w'] / 2 + 7)
                if bsolid(x, y):
                    continue
                cross = [M['nm'] for M in legs if abs(M['d'][0] * dd[0] + M['d'][1] * dd[1]) < 0.7]
                out['stops'].append([round(x), round(y), round(math.atan2(dd[1], dd[0]), 3), L['nm'], cross[0] if cross else -1, 1 if len(sel) == len(legs) else 0])
            continue
        S = dict(n=ni, x=n[0], y=n[1], ap=[], cab=None)
        for L in legs:
            # the crosswalk over this leg, kerb to kerb: people cross it while the traffic running alongside them has green
            cd = L['d']; cr = (-cd[1], cd[0]); ct = L['s0'] + 20
            out['xw'].append([round(n[0] + cd[0] * ct + cr[0] * (L['w'] / 2 + 9)), round(n[1] + cd[1] * ct + cr[1] * (L['w'] / 2 + 9)),
                              round(n[0] + cd[0] * ct - cr[0] * (L['w'] / 2 + 9)), round(n[1] + cd[1] * ct - cr[1] * (L['w'] / 2 + 9)), grp(cr)])
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
    st_o = Image.new('L', (mk.width * 2, mk.height * 2), 0); st_i = Image.new('L', (mk.width * 2, mk.height * 2), 0)
    do, di = ImageDraw.Draw(st_o), ImageDraw.Draw(st_i)
    for ch in CHAINS:
        if not ch['core']:
            ra, rb = ch.get('runR', (0, 0)), ch.get('runL', (0, 0))
            t0_, t1_ = max(ra[0], rb[0]), min(ra[1], rb[1])
            if t1_ - t0_ > 20:
                pl = [(x / 5.0, y / 5.0) for x, y in [pt(ch, t, 0) for t in samples(ch, t0_, t1_, 60.0)]]
                do.line(pl, fill=255, width=int(round((ch['w'] + 2 * STRIP) / 5.0))); di.line(pl, fill=255, width=int(round((ch['w'] + 2) / 5.0)))
    strip = (np.asarray(st_o.resize(mk.size, Image.BOX)) > 128) & (np.asarray(st_i.resize(mk.size, Image.BOX)) < 128)
    G_[strip & (R_ < 100)] = 0
    G_[(old > 100) & (R_ < 100) & (G_ < 128)] = 128        # asphalt the old mask had where there is no street: treat as paved ground
    Image.merge('RGB', (Image.fromarray(R_), Image.fromarray(G_), b0)).save(repo + '/data/mask.png', optimize=True)
    json.dump(out, open(repo + '/data/street.json', 'w'), separators=(',', ':'))
    road_t = np.asarray(newr.resize((mk.width // 2, mk.height // 2), Image.BOX)) > 110
    band = Image.new('L', (mk.width, mk.height), 0)
    db = ImageDraw.Draw(band)
    for ch in CHAINS:
        db.line([(x / 10.0, y / 10.0) for x, y in ch['pts']], fill=255, width=int(round((ch['w'] + 2 * ch['sw']) / 10.0)), joint='curve')
    walk_t = (np.asarray(band.resize((mk.width // 2, mk.height // 2), Image.BOX)) > 110) & ~road_t
    paved_t = np.asarray(g0.resize((mk.width // 2, mk.height // 2), Image.BOX)) >= 100

    def tiles(mp):
        """rewrite the road and sidewalk tiles of the collision map (2 m tiles) from this geometry; buildings and water stay"""
        m = np.asarray(mp).copy()
        h_, w_ = min(m.shape[0], road_t.shape[0]), min(m.shape[1], road_t.shape[1])
        v = m[:h_, :w_]
        keep = (v == 120) | (v == 0)
        was = (v == 60) | (v == 90)
        v[was & ~keep] = np.where(paved_t[:h_, :w_], 180, 30)[was & ~keep]
        v[walk_t[:h_, :w_] & ~keep] = 90
        v[road_t[:h_, :w_] & ~keep] = 60
        m[:h_, :w_] = v
        return Image.fromarray(m).copy()
    out_tiles[0] = tiles
    print('streets:', stat, '| signals', len(out['signals']), 'stop signs', len(out['stops']), 'street trees', len(trees))
    return out, out_tiles[0]
