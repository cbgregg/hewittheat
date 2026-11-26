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


def naip():
    """leaf-on NAIP mosaic (USGS, 4 bands with near infrared) over the map at 2 ft per pixel, in State Plane feet"""
    import urllib.parse
    cs = [D.w2sp(x, y) for x, y in ((0, 0), (WW, 0), (WW, WH), (0, WH))]
    e0, e1, n0, n1 = min(p[0] for p in cs) - 50, max(p[0] for p in cs) + 50, min(p[1] for p in cs) - 50, max(p[1] for p in cs) + 50
    f = CACHE + '/naip_2ft.npy'
    if not os.path.exists(f):
        Wp, Hp = int((e1 - e0) / 2), int((n1 - n0) / 2)
        A = np.zeros((Hp, Wp, 4), np.uint8)
        TS = 1500
        nx, ny = math.ceil(Wp / TS), math.ceil(Hp / TS)
        for a in range(nx):
            for b in range(ny):
                x0, x1, y0, y1 = a * TS, min(Wp, (a + 1) * TS), b * TS, min(Hp, (b + 1) * TS)
                q = {'f': 'image', 'bbox': '%f,%f,%f,%f' % (e0 + x0 * 2, n1 - y1 * 2, e0 + x1 * 2, n1 - y0 * 2), 'bboxSR': 2285, 'imageSR': 2285, 'size': '%d,%d' % (x1 - x0, y1 - y0),
                     'format': 'tiff', 'pixelType': 'U8', 'interpolation': 'RSP_BilinearInterpolation'}
                raw = D.get('https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage', q, binary=True)
                A[y0:y1, x0:x1] = np.asarray(Image.open(io.BytesIO(raw)).convert('RGBA'))[:y1 - y0, :x1 - x0]
                print('naip tile', a, b, flush=True)
        np.save(f, A)
    return np.load(f), e0, n1


def detect():
    """every tree crown the imagery shows: data/dossier/trees_raw.json, [x, y, crown radius, evergreen] in game units"""
    A, e0, n1 = naip()
    Hp, Wp = A.shape[:2]
    nir, red = A[..., 3].astype(np.float32), A[..., 0].astype(np.float32)
    veg = (nir - red) / (nir + red + 1) > 0.2
    # world position of every pixel (the State Plane to game transform is affine)
    ee = (e0 + (np.arange(Wp, dtype=np.float32) + 0.5) * 2 - D.A[0][2])[None, :]
    nn = (n1 - (np.arange(Hp, dtype=np.float32) + 0.5) * 2 - D.A[1][2])[:, None]
    wx = (D.A[1][1] * ee - D.A[0][1] * nn) / D.DET
    wy = (-D.A[1][0] * ee + D.A[0][0] * nn) / D.DET
    inside = (wx > 20) & (wx < WW - 20) & (wy > 20) & (wy < WH - 20)
    # trees, not lawns: the county's LiDAR-based canopy layer says where vegetation is tall; over pavement any vegetation is a tree crown
    M, to_world, mpp = canopy()
    cy_, cx_ = np.nonzero(M[..., 3] > 128)
    cwx, cwy = to_world(cx_, cy_)
    ce, cn = D.A[0][0] * cwx + D.A[0][1] * cwy + D.A[0][2], D.A[1][0] * cwx + D.A[1][1] * cwy + D.A[1][2]
    px, py = ((ce - e0) / 2).astype(int), ((n1 - cn) / 2).astype(int)
    tall = np.zeros((Hp, Wp), bool)
    ok = (px > 3) & (px < Wp - 4) & (py > 3) & (py < Hp - 4)
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            tall[py[ok] + dy, px[ok] + dx] = True
    tiles = np.asarray(Image.open(ROOT + '/data/map_base.png').convert('L'))
    tx, ty = np.clip((wx / 20).astype(int), 0, tiles.shape[1] - 1), np.clip((wy / 20).astype(int), 0, tiles.shape[0] - 1)
    tx, ty = np.broadcast_arrays(tx, ty)
    tv = tiles[ty, tx]
    paved = (tv == 60) | (tv == 90) | (tv == 180)
    from PIL import ImageDraw
    bl = Image.new('L', (int(WW / 10), int(WH / 10)), 0)
    dr = ImageDraw.Draw(bl)
    for b in W['bld']:
        dr.polygon([(b[3 + 2 * k] / 10, b[4 + 2 * k] / 10) for k in range((len(b) - 3) // 2)], fill=255)
    bl = np.asarray(bl) > 0
    bx, by = np.broadcast_arrays(np.clip((wx / 10).astype(int), 0, bl.shape[1] - 1), np.clip((wy / 10).astype(int), 0, bl.shape[0] - 1))
    T = veg & (tall | paved) & inside & ~bl[by, bx] & (tv != 0)
    dt = edt(T)
    ys, xs = np.nonzero(dt >= 2.2)
    order = np.argsort(-dt[ys, xs], kind='stable')
    taken = np.zeros(T.shape, bool)
    mos = ROOT + '/dossier/_all/raw/mosaic_2024.jpg'
    AIR = np.asarray(Image.open(mos)) if os.path.exists(mos) else None
    out = []
    for k in order:
        y, x = int(ys[k]), int(xs[k])
        if taken[y, x]:
            continue
        rad = float(dt[y, x])
        sp = max(6.0, min(15.0, rad * 1.6))        # 3.6 to 9 m between trunks
        r_ = int(math.ceil(sp))
        y0, y1, x0, x1 = max(0, y - r_), min(Hp, y + r_ + 1), max(0, x - r_), min(Wp, x + r_ + 1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        taken[y0:y1, x0:x1] |= (yy - y) ** 2 + (xx - x) ** 2 <= sp * sp
        ever = 0
        if AIR is not None:
            ax, ay = x * 2 + 1, y * 2 + 1          # the leaf-off mosaic shares this origin at 1 ft per pixel
            if 3 <= ax < AIR.shape[1] - 3 and 3 <= ay < AIR.shape[0] - 3:
                r3, g3, b3 = AIR[ay - 2:ay + 3, ax - 2:ax + 3].reshape(-1, 3).mean(0)
                ever = int(g3 > r3 * 1.06 and g3 > b3 * 1.10 and g3 < 98)
        out.append([int(round(float(wx[0, x] if wx.shape[0] == 1 else wx[y, x]))), int(round(float(wy[y, 0] if wy.shape[1] == 1 else wy[y, x]))), int(round(min(rad, 13.0) * 6.1)), ever, int(tall[y, x])])
    os.makedirs(ROOT + '/data/dossier', exist_ok=True)
    json.dump(dict(source='Tree crowns from USGS NAIP leaf-on imagery (near-infrared vegetation index, 0.6 m), kept where Snohomish County\'s LiDAR canopy layer shows tall vegetation or where the crown is over pavement; evergreen = dark green in the county leaf-off aerial of March 2024',
                   fields=['x', 'y', 'crown radius', 'evergreen', 'in county canopy layer'], trees=out), open(ROOT + '/data/dossier/trees_raw.json', 'w'), separators=(',', ':'))
    print('vegetation px', int(veg.sum()), 'tree px', int(T.sum()), 'crowns', len(out), 'evergreen', sum(t[3] for t in out), 'outside canopy layer (over pavement)', sum(1 for t in out if not t[4]))


def main():
    raw = json.load(open(ROOT + '/data/dossier/trees_raw.json'))['trees']
    gm = np.asarray(Image.open(ROOT + '/data/mask.png').convert('RGB'))
    extras = json.load(open(ROOT + '/data/extras.json'))
    clear = extras.get('clear', [])
    used = set(extras.get('used', []))
    out = [[t[0], t[1], int(round(t[2] * 100)), t[3] if len(t) > 3 else 0] for t in extras.get('trees', [])]
    nstreet = len(out)
    KR = [k[1] for k in treegen.KINDS]
    R = random.Random(5)
    stat = {}
    for i, (X, Y, crown, ever, tall) in enumerate(raw):
        if i in used:
            continue
        ix, iy = min(gm.shape[1] - 1, int(X / 10)), min(gm.shape[0] - 1, int(Y / 10))
        if gm[iy, ix, 0] > 90:
            continue                       # crown centre over a street: taken by the street builder or left out
        if any(b[0] - 40 < X < b[2] + 40 and b[1] - 40 < Y < b[3] + 40 for b in clear):
            continue
        if ever:
            kind = 4 if (crown > 38 or R.random() < 0.6) else 5
        elif crown < 24:
            kind = 3 if R.random() < 0.6 else 0
        elif crown > 50:
            kind = 1
        else:
            kind = R.choice((0, 0, 1, 2)) if crown < 34 else R.choice((0, 1, 1))
        sc = max(0.55, min(1.5, crown / KR[kind] * (1.3 if kind >= 4 else 1.1))) * R.uniform(0.9, 1.12)
        out.append([X, Y, int(round(sc * 100)), kind])
        stat[kind] = stat.get(kind, 0) + 1
    json.dump(dict(source='tools/trees.py: crowns from NAIP leaf-on imagery and the Snohomish County canopy layer (data/dossier/trees_raw.json); kerbside and median trees are the detected crowns that stand over a street, moved to the kerb or island by tools/streets.py',
                   kinds=[k[0] for k in treegen.KINDS], trees=out), open(ROOT + '/data/trees.json', 'w'), separators=(',', ':'))
    print('placed', len(out) - nstreet, 'by kind', {treegen.KINDS[k][0]: v for k, v in sorted(stat.items())}, '| street and median trees', nstreet)


if __name__ == '__main__':
    detect() if 'detect' in sys.argv else main()
