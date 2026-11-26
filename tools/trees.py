"""Places the game's trees where real ones stand: data/trees.json.

  python3 tools/trees.py            (after tools/citygen.py, which writes the kerbside street trees and the road mask)

Source: Snohomish County's tree canopy layer (pds_tree_canopy_2020, about 1.6 m per pixel, three canopy classes).
Each canopy patch is filled with trees sized to the patch: the widest point of the canopy gets a tree first and
smaller ones fill in around it. A tree whose spot is green in the county's leaf-off March 2024 aerial is an evergreen
(fir or cedar); the rest are broadleaf. Nothing is placed on a road, a building or water.
The canopy tiles and the aerial are downloaded to dossier/ (not committed).

Each tree: [x, y, scale x100, kind] with kinds as in tools/treegen.py."""
import io, json, math, os, random, sys, urllib.request
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt as edt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dossier as D
import treegen

ROOT = D.ROOT
CACHE = ROOT + '/dossier/_streets'
os.makedirs(CACHE, exist_ok=True)
Image.MAX_IMAGE_PIXELS = None
W = json.load(open(ROOT + '/data/world.json'))
WW, WH = W['wm'] * 10, W['hm'] * 10


def canopy():
    import pyproj
    T = pyproj.Transformer.from_crs(2285, 3857, always_xy=True)
    ox, oy, res, z = -20037508.342787, 20037508.342787, 2.388657133911758, 16
    f = CACHE + '/canopy_z16.png'
    cs = [T.transform(*D.w2sp(x, y)) for x, y in ((0, 0), (WW, 0), (WW, WH), (0, WH))]
    c0, c1 = int((min(c[0] for c in cs) - ox) / (res * 256)), int((max(c[0] for c in cs) - ox) / (res * 256))
    r0, r1 = int((oy - max(c[1] for c in cs)) / (res * 256)), int((oy - min(c[1] for c in cs)) / (res * 256))
    if not os.path.exists(f):
        M = Image.new('RGBA', ((c1 - c0 + 1) * 256, (r1 - r0 + 1) * 256))
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                try:
                    b = urllib.request.urlopen('https://gis.snoco.org/host/rest/services/Hosted/pds_tree_canopy_2020/MapServer/tile/%d/%d/%d' % (z, r, c), timeout=60).read()
                    M.paste(Image.open(io.BytesIO(b)).convert('RGBA'), ((c - c0) * 256, (r - r0) * 256))
                except Exception:
                    pass
        M.save(f)
    M = np.asarray(Image.open(f).convert('RGBA'))
    inv = pyproj.Transformer.from_crs(3857, 2285, always_xy=True)

    def to_world(px, py):
        e, n = inv.transform(ox + c0 * res * 256 + (np.asarray(px) + 0.5) * res, oy - r0 * res * 256 - (np.asarray(py) + 0.5) * res)
        e = np.asarray(e) - D.A[0][2]; n = np.asarray(n) - D.A[1][2]
        return (D.A[1][1] * e - D.A[0][1] * n) / D.DET, (-D.A[1][0] * e + D.A[0][0] * n) / D.DET
    return M, to_world, res * math.cos(math.radians(47.98))        # metres per pixel on the ground


def main():
    M, to_world, mpp = canopy()
    mask = M[..., 3] > 128
    dark = mask & (M[..., 0] < 45)             # the tallest canopy class
    dt = edt(mask)
    # greedy fill: biggest crowns first, each claims a disc so neighbours stand a crown apart
    ys, xs = np.nonzero(dt >= 0.9)
    order = np.argsort(-dt[ys, xs], kind='stable')
    taken = np.zeros(mask.shape, bool)
    picks = []
    H_, W_ = mask.shape
    for k in order:
        y, x = int(ys[k]), int(xs[k])
        if taken[y, x]:
            continue
        rad = float(dt[y, x])
        sp = max(2.0, min(5.2, rad * 1.55))       # spacing in pixels: 3 to 8 m
        r_ = int(math.ceil(sp))
        y0, y1, x0, x1 = max(0, y - r_), min(H_, y + r_ + 1), max(0, x - r_), min(W_, x + r_ + 1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        taken[y0:y1, x0:x1] |= (yy - y) ** 2 + (xx - x) ** 2 <= sp * sp
        picks.append((x, y, min(rad, 4.6), bool(dark[y, x])))
    px = np.array([p[0] for p in picks]); py = np.array([p[1] for p in picks])
    wx, wy = to_world(px, py)
    # what is there now: road and building masks (1 px = 1 m), and the leaf-off aerial
    gm = np.asarray(Image.open(ROOT + '/data/mask.png').convert('RGB'))
    cm = np.asarray(Image.open(ROOT + ('/data/map_base.png' if os.path.exists(ROOT + '/data/map_base.png') else '/data/map.png')).convert('L'))
    bl = Image.new('L', (gm.shape[1], gm.shape[0]), 0)
    from PIL import ImageDraw
    dr = ImageDraw.Draw(bl)
    for b in W['bld']:
        dr.polygon([(b[3 + 2 * k] / 10, b[4 + 2 * k] / 10) for k in range((len(b) - 3) // 2)], fill=255)
    near_b = edt(np.asarray(bl) == 0)
    mos = ROOT + '/dossier/_all/raw/mosaic_2024.jpg'
    AIR = Image.open(mos).load() if os.path.exists(mos) else None
    if AIR:
        cs = [D.w2sp(x, y) for x, y in ((0, 0), (WW, 0), (WW, WH), (0, WH))]
        e0 = min(p[0] for p in cs) - 50; n1 = max(p[1] for p in cs) + 50
        aw, ah = Image.open(mos).size
    R = random.Random(5)
    extras = json.load(open(ROOT + '/data/extras.json'))
    clear = extras.get('clear', [])
    out = [[t[0], t[1], int(round(t[2] * 100)), t[3] if len(t) > 3 else 0] for t in extras.get('trees', [])]
    nstreet = len(out)
    KR = [k[1] for k in treegen.KINDS]
    stat = {}
    for k, (x, y, rad, dk) in enumerate(picks):
        X, Y = float(wx[k]) + R.uniform(-5, 5), float(wy[k]) + R.uniform(-5, 5)
        ix, iy = int(X / 10), int(Y / 10)
        if not (20 < X < WW - 20 and 20 < Y < WH - 20):
            continue
        if gm[iy, ix, 0] > 90 or near_b[iy, ix] < 2.5 or cm[int(Y // 20), int(X // 20)] in (0, 120):
            continue
        if any(b[0] - 40 < X < b[2] + 40 and b[1] - 40 < Y < b[3] + 40 for b in clear):
            continue
        ever = False
        if AIR:
            e, n = D.w2sp(X, Y); ax, ay = int(e - e0), int(n1 - n)
            if 2 <= ax < aw - 2 and 2 <= ay < ah - 2:
                g = [AIR[ax + i, ay + j] for i in (-2, 0, 2) for j in (-2, 0, 2)]
                r_, g_, b_ = (sum(p[q] for p in g) / 9 for q in range(3))
                ever = g_ > r_ * 1.06 and g_ > b_ * 1.10 and g_ < 98      # dark green: lawns under bare trees are brighter
        crown = rad * mpp * 10                       # crown radius in game units
        if ever:
            kind = 4 if (dk or crown > 38 or R.random() < 0.55) else 5
        elif crown < 24:
            kind = 3 if R.random() < 0.6 else 0
        elif crown > 48 or (dk and crown > 36):
            kind = 1
        else:
            kind = R.choice((0, 0, 1, 2)) if crown < 34 else R.choice((0, 1, 1))
        sc = max(0.6, min(1.5, crown / KR[kind] * (1.25 if kind >= 4 else 1.1))) * R.uniform(0.9, 1.12) * (1.15 if dk else 1.0)
        out.append([int(round(X)), int(round(Y)), int(round(sc * 100)), kind])
        stat[kind] = stat.get(kind, 0) + 1
    # a street tree gives way to a real canopy tree standing in the same spot
    json.dump(dict(source='Snohomish County tree canopy 2020 (pds_tree_canopy_2020); evergreen/broadleaf from the county leaf-off aerial, March 2024; kerbside trees from tools/streets.py',
                   kinds=[k[0] for k in treegen.KINDS], trees=out), open(ROOT + '/data/trees.json', 'w'), separators=(',', ':'))
    print('canopy pixels', int(mask.sum()), 'picked', len(picks), 'placed', len(out) - nstreet, 'by kind', {treegen.KINDS[k][0]: v for k, v in sorted(stat.items())}, 'street', nstreet)


if __name__ == '__main__':
    main()
