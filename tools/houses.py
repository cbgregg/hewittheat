"""Reads every house roof from the county 2024 aerial (1 ft per pixel): data/dossier/houses.json.

  python3 tools/houses.py        (after tools/dossier_all.py, which downloads the aerial)

Per house and outbuilding footprint:
  rc    shingle colour, as one of nine roofing colours nearest to what the aerial shows (pixels under tree canopy left out)
  ax    1 when the ridge runs across the short side of the footprint (the two roof planes differ in brightness across it)
  hip   1 for a hip roof (the planes' brightness difference fades at the ends of the ridge), 0 for a gable
  fa    the compass angle of the wall that faces the nearest street
  yr    year built: from the county's recent-sales layer when this parcel sold (yx=1), otherwise the nearest sold house
        within 150 m, as an estimate of the neighbourhood's era
tools/citygen.py builds the houses from this."""
import json, math, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dossier as D
import streets

ROOT = D.ROOT
Image.MAX_IMAGE_PIXELS = None
SHINGLE = [('#3c3f42', 'charcoal'), ('#55585c', 'dark grey'), ('#74777a', 'grey'), ('#9a9d9f', 'light grey'), ('#c9cac8', 'white'),
           ('#54453a', 'dark brown'), ('#766250', 'brown'), ('#7e4a40', 'red'), ('#4d5a4c', 'green')]


def main():
    W = json.load(open(ROOT + '/data/world.json'))
    WW, WH = W['wm'] * 10, W['hm'] * 10
    cs = [D.w2sp(x, y) for x, y in ((0, 0), (WW, 0), (WW, WH), (0, WH))]
    e0 = min(p[0] for p in cs) - 50; n1 = max(p[1] for p in cs) + 50
    A = np.asarray(Image.open(ROOT + '/dossier/_all/raw/mosaic_2024.jpg')).astype(np.float32)
    env = dict(xmin=min(p[0] for p in cs), xmax=max(p[0] for p in cs), ymin=min(p[1] for p in cs), ymax=max(p[1] for p in cs))
    D.LAYERS['sales'] = D.CNTY + 'CADASTRAL__recent_sales/FeatureServer/0'
    sales = []
    for f in D.layer('sales', env, ROOT + '/dossier/_all/raw'):
        try:
            y = int(f['attributes'].get('year_built') or 0)
        except ValueError:
            y = 0
        if 1880 < y < 2030:
            rg = [D.sp2w(*q[:2]) for q in f['geometry']['rings'][0]]
            sales.append((sum(q[0] for q in rg) / len(rg), sum(q[1] for q in rg) / len(rg), int(y), rg, f['attributes'].get('style')))
    CH, _ = streets.chains(W, lambda x, y: False)
    sg = {}
    for ch in CH:
        for k in range(len(ch['pts']) - 1):
            a, b = ch['pts'][k], ch['pts'][k + 1]
            for gx in range(int(min(a[0], b[0]) // 400) - 1, int(max(a[0], b[0]) // 400) + 2):
                for gy in range(int(min(a[1], b[1]) // 400) - 1, int(max(a[1], b[1]) // 400) + 2):
                    sg.setdefault((gx, gy), []).append((a, b))
    pal = np.array([[int(c[k:k + 2], 16) for k in (1, 3, 5)] for c, _ in SHINGLE], np.float32)
    out, st = {}, dict(n=0, cross=0, hip=0, gable=0, unsure=0, yr_exact=0, yr_near=0)
    cnt = {}
    for i, b in enumerate(W['bld']):
        if b[1] not in (0, 3):
            continue
        n = (len(b) - 3) // 2
        px = np.array(b[3::2][:n], np.float32); py = np.array(b[4::2][:n], np.float32)
        cx, cy = float(px.mean()), float(py.mean())
        # footprint axes exactly as tools/citygen.py computes them
        sxx, syy, sxy = float(((px - cx) ** 2).sum()), float(((py - cy) ** 2).sum()), float(((px - cx) * (py - cy)).sum())
        th = 0.5 * math.atan2(2 * sxy, sxx - syy); ax, ay = math.cos(th), math.sin(th)
        us = (px - cx) * ax + (py - cy) * ay; vs = -(px - cx) * ay + (py - cy) * ax
        lng = (us.max() - us.min()) >= (vs.max() - vs.min())
        # aerial pixels inside the footprint, pulled in 12% from the walls
        sp = [D.w2sp(float(px[k]), float(py[k])) for k in range(n)]
        xa, xb = int(min(p[0] for p in sp) - e0), int(max(p[0] for p in sp) - e0) + 1
        ya, yb = int(n1 - max(p[1] for p in sp)), int(n1 - min(p[1] for p in sp)) + 1
        if xa < 0 or ya < 0 or xb >= A.shape[1] or yb >= A.shape[0] or xb - xa < 6 or yb - ya < 6:
            continue
        sub = A[ya:yb, xa:xb]
        gy_, gx_ = np.mgrid[ya:yb, xa:xb]
        e = gx_ + 0.5 + e0 - D.A[0][2]; nn = n1 - gy_ - 0.5 - D.A[1][2]
        wx = (D.A[1][1] * e - D.A[0][1] * nn) / D.DET; wy = (-D.A[1][0] * e + D.A[0][0] * nn) / D.DET
        u = (wx - cx) * ax + (wy - cy) * ay; v = -(wx - cx) * ay + (wy - cy) * ax
        uc, vc = (us.max() + us.min()) / 2, (vs.max() + vs.min()) / 2
        hu, hv = (us.max() - us.min()) / 2, (vs.max() - vs.min()) / 2
        inside = (np.abs(u - uc) < hu * 0.86) & (np.abs(v - vc) < hv * 0.86)
        r_, g_, b_ = sub[..., 0], sub[..., 1], sub[..., 2]
        roof = inside & ~((g_ > r_ * 1.1) & (g_ > b_ * 1.1))
        if roof.sum() < 20:
            continue
        lum = 0.3 * r_ + 0.59 * g_ + 0.11 * b_
        med = np.array([np.median(r_[roof]), np.median(g_[roof]), np.median(b_[roof])])
        med = med * 0.6 + med.mean() * 0.4 + np.array([4, -4, 0])            # take out the aerial's green cast
        R = dict(rc=SHINGLE[int(((pal - med) ** 2).sum(1).argmin())][0])
        cnt[R['rc']] = cnt.get(R['rc'], 0) + 1
        du, dv = (u - uc), (v - vc)

        def contrast(c, m):
            a_, b2 = lum[m & (c > 0)], lum[m & (c < 0)]
            return abs(float(a_.mean()) - float(b2.mean())) if len(a_) > 6 and len(b2) > 6 else 0.0
        c_long = contrast(dv, roof) if lng else contrast(du, roof)       # ridge along the long side: the planes split across it
        c_short = contrast(du, roof) if lng else contrast(dv, roof)
        cross = c_short > c_long * 1.5 and c_short > 9
        R['ax'] = int(cross)
        along, across, half = (dv, du, hv) if (lng == cross) else (du, dv, hu)   # ridge direction coordinate
        mid = contrast(across, roof & (np.abs(along) < half * 0.3)); end = contrast(across, roof & (np.abs(along) > half * 0.55))
        if mid > 9:
            R['hip'] = int(end < mid * 0.4)
            st['hip' if R['hip'] else 'gable'] += 1
        else:
            R['hip'] = 0 if b[1] == 3 else int((i * 7) % 10 < 3)        # no clear reading: most are gables, some hips
            st['unsure'] += 1
        st['cross'] += cross
        # the wall that faces the street
        best = None
        for a_, b2 in sg.get((int(cx // 400), int(cy // 400)), ()):
            dx, dy = b2[0] - a_[0], b2[1] - a_[1]; l2 = dx * dx + dy * dy or 1
            t = max(0.0, min(1.0, ((cx - a_[0]) * dx + (cy - a_[1]) * dy) / l2))
            qx, qy = a_[0] + dx * t, a_[1] + dy * t; dq = math.hypot(qx - cx, qy - cy)
            if best is None or dq < best[0]:
                best = (dq, qx, qy)
        if best and best[0] < 450:
            R['fa'] = round(math.atan2(best[2] - cy, best[1] - cx), 2)
        if b[1] == 0:
            near = None
            for sx, sy, yr, rg, sty in sales:
                d = math.hypot(sx - cx, sy - cy)
                if d < 1500 and (near is None or d < near[0]):
                    near = (d, yr, rg, sty)
            if near:
                R['yr'] = near[1]
                if D.pip(cx, cy, near[2]):
                    R['yx'] = 1; st['yr_exact'] += 1
                    if near[3]:
                        R['sty'] = near[3]
                else:
                    st['yr_near'] += 1
        out[i] = R; st['n'] += 1
    json.dump(dict(source='Roofs read from the Snohomish County 2024 aerial; year built from the county recent-sales layer (exact for sold parcels, nearest sold house within 150 m otherwise)',
                   shingles={c: nm for c, nm in SHINGLE}, houses=out), open(ROOT + '/data/dossier/houses.json', 'w'), separators=(',', ':'))
    print(st, {dict(SHINGLE)[k]: v for k, v in sorted(cnt.items(), key=lambda t: -t[1])})


if __name__ == '__main__':
    main()
