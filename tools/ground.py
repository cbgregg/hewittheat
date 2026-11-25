"""Extends the land-use mask (data/mask.png) so the ground around commercial and industrial
buildings is paved instead of grass, and flags parking lots (blue channel, off-road only).
Derived only from the City footprints: a pixel is paved when its nearest building is
commercial. Usage: python3 tools/ground.py REPO"""
import json, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt as edt

REPO = sys.argv[1]
Image.MAX_IMAGE_PIXELS = None
W = json.load(open(REPO + '/data/world.json'))
src = REPO + '/data/mask_base.png'
import os, shutil
if not os.path.exists(src):
    shutil.copy(REPO + '/data/mask.png', src)
m = np.array(Image.open(src).convert('RGB'))
H, Wd = m.shape[:2]
layers = {k: Image.new('L', (Wd, H), 0) for k in ('com', 'ind', 'res')}
draw = {k: ImageDraw.Draw(v) for k, v in layers.items()}
for b in W['bld']:
    n = (len(b) - 3) // 2
    pts = [(b[3 + k * 2] / 10, b[4 + k * 2] / 10) for k in range(n)]
    a = abs(sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))) / 2
    kind, h = b[1], b[0]
    k = 'res' if kind in (0, 3) or (kind == 5 and a < 420 and h <= 105) else 'ind' if kind == 4 else 'com'
    draw[k].polygon(pts, fill=255)
com, ind, res = (np.asarray(layers[k]) > 0 for k in ('com', 'ind', 'res'))
d_com, d_ind, d_res = edt(~com), edt(~ind), edt(~res)
R, G, B = m[..., 0].copy(), m[..., 1].copy(), m[..., 2].copy()
road = (R > 0) | (G == 255)
d_road = edt(~road)
park = np.zeros((H, Wd), bool)
yy, xx = np.mgrid[0:H, 0:Wd]
for p in W['pois']:
    if p[3] == 'park':
        park |= (xx - p[1] / 10) ** 2 + (yy - p[2] / 10) ** 2 < 85 ** 2
free = (R == 0) & (G == 0) & ~park
paved = free & (((d_com < 46) & (d_com < d_res + 4)) | ((d_ind < 80) & (d_ind < d_res)))
G[paved] = 128
# close thin unpaved slivers between paved ground, sidewalks and roads
from scipy.ndimage import binary_closing
hard = (G > 0) | (R > 0)
closed = binary_closing(hard, structure=np.ones((3, 3), bool), iterations=4)
G[closed & ~hard & ~park & ~res] = 128
lot = (G == 128) & (R == 0) & (d_com > 7) & (d_com < 46) & (d_road > 5) & (d_res > 6) & (d_ind > 3) & ~park
B[lot] = 255
out = np.dstack([R, G, B])
Image.fromarray(out).save(REPO + '/data/mask.png', optimize=True)
print('paved px', int(paved.sum()), 'lot px', int(lot.sum()), 'of', H * Wd)
