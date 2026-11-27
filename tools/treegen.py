"""Tree models for the game, built procedurally (no downloaded assets): models/t_<kind>.glb and their textures in tex/t/.

  python3 tools/treegen.py

Each tree is a bark-textured trunk with real branches, and a crown of alpha-cut leaf cards whose normals point away
from the crown centre so the canopy shades as one rounded mass. Units: 10 = 1 m, y up.

  0 maple     rounded street tree, 9 m          3 cherry    small ornamental, 5.5 m
  1 bigleaf   broad old shade tree, 16 m        4 fir       Douglas fir, 26 m
  2 column    narrow upright street tree, 10 m  5 cedar     western red cedar, 17 m, drooping sprays
"""
import json, math, os, random, struct
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = ROOT + '/tex/t'
os.makedirs(TEX, exist_ok=True)


# ---------------------------------------------------------------- textures
def leaf_texture(path, seed, base, kind='broad'):
    r = random.Random(seed)
    S = 512
    im = Image.new('RGBA', (S, S), base + (0,))
    d = ImageDraw.Draw(im)
    if kind == 'broad':
        # twigs first, then three depths of leaves, dark to light
        for _ in range(9):
            a = r.uniform(0, 6.28); x, y = S / 2 + r.uniform(-40, 40), S / 2 + r.uniform(-40, 40)
            for k in range(14):
                x2, y2 = x + math.cos(a) * 17, y + math.sin(a) * 17
                d.line([x, y, x2, y2], fill=(58, 44, 30, 255), width=max(1, 4 - k // 4)); x, y = x2, y2; a += r.uniform(-0.3, 0.3)
        for layer, n in ((0, 420), (1, 380), (2, 260)):
            for _ in range(n):
                ang = r.uniform(0, 6.28); rad = (r.random() ** 0.6) * S * 0.47
                cx, cy = S / 2 + math.cos(ang) * rad, S / 2 + math.sin(ang) * rad
                ln, wd, rot = r.uniform(20, 32), r.uniform(11, 17), r.uniform(0, 6.28)
                k = (0.62, 0.84, 1.06)[layer] * r.uniform(0.88, 1.12)
                col = tuple(max(0, min(255, int(c * k + r.uniform(-8, 8)))) for c in base)
                pts = []
                for q in range(12):
                    t = q / 12 * 6.28
                    px, py = math.cos(t) * ln / 2, math.sin(t) * wd / 2 * (1 - 0.35 * math.cos(t))
                    pts.append((cx + px * math.cos(rot) - py * math.sin(rot), cy + px * math.sin(rot) + py * math.cos(rot)))
                d.polygon(pts, fill=col + (255,))
                d.line([cx - math.cos(rot) * ln / 2, cy - math.sin(rot) * ln / 2, cx + math.cos(rot) * ln / 2, cy + math.sin(rot) * ln / 2], fill=tuple(min(255, int(c * 1.25)) for c in col) + (255,), width=1)
    else:
        # conifer bough seen flat: a stem from the top edge with side twigs that shorten toward the tip, needles on each
        def twig(x, y, a, ln, wd):
            n = max(2, int(ln / 6))
            for k in range(n):
                x2, y2 = x + math.cos(a) * 6, y + math.sin(a) * 6
                d.line([x, y, x2, y2], fill=(50, 40, 28, 255), width=wd)
                for s in (-1, 1):
                    for j in range(2):
                        na = a + s * r.uniform(0.7, 1.2); nl = r.uniform(7, 12) * (1.0 if kind == 'fir' else 1.35)
                        k2 = r.uniform(0.6, 1.2)
                        ox, oy = x + j * 3 * math.cos(a), y + j * 3 * math.sin(a)
                        d.line([ox, oy, ox + math.cos(na) * nl, oy + math.sin(na) * nl], fill=tuple(min(255, int(c * k2)) for c in base) + (255,), width=3)
                x, y = x2, y2; a += r.uniform(-0.05, 0.05)
            return x, y
        x, y, a = S / 2, 4, math.pi / 2
        n = 26
        for k in range(n):
            f = k / n
            x2, y2 = x + math.cos(a) * (S * 0.95 / n), y + math.sin(a) * (S * 0.95 / n)
            d.line([x, y, x2, y2], fill=(50, 40, 28, 255), width=5 - int(f * 3))
            if k > 1:
                for s in (-1, 1):
                    ln = S * 0.40 * (1 - f) ** 0.7 * r.uniform(0.75, 1.1)
                    ex, ey = twig(x2, y2, a + s * r.uniform(0.75, 1.0) + (0.25 * s if kind == 'cedar' else 0), ln, 3 if f < 0.5 else 2)
                    if kind == 'cedar' or k % 2:
                        for s2 in (-1, 1):
                            mx, my = (x2 + ex) / 2, (y2 + ey) / 2
                            twig(mx, my, a + s * 0.85 + s2 * 0.7, ln * 0.35, 2)
            x, y = x2, y2; a += r.uniform(-0.03, 0.03)
    im = im.resize((256, 256), Image.LANCZOS)
    # keep the colour under transparent pixels so mip levels do not grow dark halos
    px = im.load()
    for y in range(256):
        for x in range(256):
            if px[x, y][3] < 8:
                px[x, y] = base + (0,)
    im.save(path, optimize=True)


def bark_texture(path):
    r = random.Random(3)
    im = Image.new('RGB', (128, 256), (92, 80, 68))
    d = ImageDraw.Draw(im)
    for _ in range(420):
        x = r.randrange(128); y = r.randrange(256); ln = r.randrange(18, 80); k = r.uniform(0.55, 1.3)
        d.line([x, y, x + r.randrange(-3, 4), y + ln], fill=tuple(int(c * k) for c in (92, 80, 68)), width=r.choice((1, 2, 2, 3)))
    im.filter(ImageFilter.GaussianBlur(0.6)).save(path, quality=88)


# ---------------------------------------------------------------- geometry
class Mesh:
    def __init__(self):
        self.p, self.n, self.u, self.c, self.i = [], [], [], [], []

    def vert(self, p, n, u, c):
        self.p.append(p); self.n.append(n); self.u.append(u); self.c.append(c)
        return len(self.p) - 1

    def quad(self, a, b, c, d):
        self.i += [a, b, c, a, c, d]


def norm(v):
    l = math.sqrt(sum(x * x for x in v)) or 1
    return tuple(x / l for x in v)


def limb(M, pts, radii, sides=7, col=(1, 1, 1), vscale=0.02):
    """tapered tube through a list of points"""
    rings = []
    v = 0.0
    total = sum(math.dist(pts[k], pts[k - 1]) for k in range(1, len(pts))) or 1
    for k, (p, rad) in enumerate(zip(pts, radii)):
        a = pts[max(0, k - 1)]; b = pts[min(len(pts) - 1, k + 1)]
        t = norm((b[0] - a[0], b[1] - a[1], b[2] - a[2]))
        ref = (1, 0, 0) if abs(t[0]) < 0.8 else (0, 0, 1)
        u = norm((t[1] * ref[2] - t[2] * ref[1], t[2] * ref[0] - t[0] * ref[2], t[0] * ref[1] - t[1] * ref[0]))
        w = (t[1] * u[2] - t[2] * u[1], t[2] * u[0] - t[0] * u[2], t[0] * u[1] - t[1] * u[0])
        if k:
            v += math.dist(p, pts[k - 1]) / total
        ring = []
        for s in range(sides + 1):
            an = s / sides * 2 * math.pi
            nx = tuple(u[q] * math.cos(an) + w[q] * math.sin(an) for q in range(3))
            uu = s / sides * 2
            ring.append(M.vert(tuple(p[q] + nx[q] * rad for q in range(3)), nx, (0.52 + 0.46 * abs(uu % 2 - 1), 0.02 + 0.96 * v), col))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for s in range(sides):
            M.quad(rings[k][s], rings[k][s + 1], rings[k + 1][s + 1], rings[k + 1][s])


def card(M, c, ax, up, w, h, nrm, col, uv=(0, 0, 1, 1), pivot=0.5):
    """textured quad centred (or hung) at c, spanning ax (width) and up (height)"""
    hw = w / 2
    P = [tuple(c[q] - ax[q] * hw - up[q] * h * pivot for q in range(3)), tuple(c[q] + ax[q] * hw - up[q] * h * pivot for q in range(3)),
         tuple(c[q] + ax[q] * hw + up[q] * h * (1 - pivot) for q in range(3)), tuple(c[q] - ax[q] * hw + up[q] * h * (1 - pivot) for q in range(3))]
    U = [(uv[0] * 0.5, uv[3]), (uv[2] * 0.5, uv[3]), (uv[2] * 0.5, uv[1]), (uv[0] * 0.5, uv[1])]
    ids = [M.vert(P[k], nrm[k] if isinstance(nrm, list) else nrm, U[k], col) for k in range(4)]
    M.quad(*ids)


def broadleaf(seed, H, crown_r, crown_h, base, cards, trunk_r, tint, spread=1.0, lean=0.0):
    r = random.Random(seed)
    B = L = Mesh()
    cx = lean * H
    cc = (cx * 0.7, base + crown_h * 0.5, 0.0)
    # trunk with a slight sweep, flared at the foot
    tp = [(0, -3, 0), (0, 0, 0), (cx * 0.15 + r.uniform(-2, 2), base * 0.5, r.uniform(-2, 2)), (cx * 0.4, base, r.uniform(-2, 2)), (cx * 0.6, base + crown_h * 0.45, 0)]
    limb(B, tp, [trunk_r * 1.5, trunk_r * 1.25, trunk_r, trunk_r * 0.85, trunk_r * 0.45], 8)
    nb = r.randint(4, 6)
    for k in range(nb):
        a = k / nb * 6.28 + r.uniform(-0.4, 0.4)
        s = tp[3] if k % 2 else (cx * 0.3, base * r.uniform(0.75, 0.95), 0)
        e = (cc[0] + math.cos(a) * crown_r * 0.72, base + crown_h * r.uniform(0.45, 0.85), math.sin(a) * crown_r * 0.72)
        m = tuple(s[q] + (e[q] - s[q]) * 0.5 for q in range(3)); m = (m[0], m[1] + crown_h * 0.08, m[2])
        limb(B, [s, m, e], [trunk_r * 0.5, trunk_r * 0.3, trunk_r * 0.08], 5)
    for k in range(cards):
        # points through the crown volume, denser near the outside
        a, z = r.uniform(0, 6.28), r.uniform(-0.75, 1)
        rr = math.sqrt(max(0, 1 - z * z)); f = r.uniform(0.55, 1.0) ** 0.6
        p = (cc[0] + math.cos(a) * rr * crown_r * f * spread, cc[1] + z * crown_h * 0.5 * f, math.sin(a) * rr * crown_r * f * spread)
        out = norm((p[0] - cc[0], (p[1] - cc[1]) * 1.2 + crown_h * 0.25, p[2]))
        t = norm((-math.sin(a) + r.uniform(-0.5, 0.5), r.uniform(-0.4, 0.4), math.cos(a) + r.uniform(-0.5, 0.5)))
        up = norm((out[0] * 0.5 + r.uniform(-0.4, 0.4), 0.8, out[2] * 0.5 + r.uniform(-0.4, 0.4)))
        dp = sum(up[q] * t[q] for q in range(3))
        up = norm(tuple(up[q] - t[q] * dp for q in range(3)))
        sz = crown_r * r.uniform(0.62, 0.95)
        shade = (0.62 + 0.38 * (z * 0.5 + 0.5)) * r.uniform(0.88, 1.08) * (0.8 + 0.2 * f)
        card(L, p, t, up, sz, sz, out, tuple(min(1.0, c * shade) for c in tint))
    return B, L


def conifer(seed, H, base_r, tint, levels, per, droop, trunk_r, first=0.16, kind='fir'):
    r = random.Random(seed)
    B = L = Mesh()
    limb(B, [(0, -3, 0), (0, 0, 0), (0, H * 0.5, 0), (0, H * 0.97, 0)], [trunk_r * 1.5, trunk_r * 1.2, trunk_r * 0.6, trunk_r * 0.06], 8)
    for lv in range(levels):
        f = lv / (levels - 1)
        y = H * (first + (1 - first) * f ** 0.92)
        ln = base_r * (1 - f) ** 0.75 * r.uniform(0.9, 1.1) + H * 0.025
        n = max(4, round(per * (1 - 0.45 * f)))
        for k in range(n):
            a = k / n * 6.28 + lv * 1.1 + r.uniform(-0.25, 0.25)
            dr = (math.cos(a), 0, math.sin(a))
            dp = droop * (1 - 0.7 * f) * r.uniform(0.6, 1.4)
            dn = norm((dr[0], -dp, dr[2]))
            side = (-math.sin(a), 0, math.cos(a))
            shade = (0.6 + 0.4 * f) * r.uniform(0.88, 1.1)
            col = tuple(min(1.0, c * shade) for c in tint)
            nrm = norm((dr[0] * 0.7, 0.7, dr[2] * 0.7))
            yy = y + r.uniform(-0.02, 0.02) * H
            # each bough: a narrow frond lying along it, and sprays hanging from it so it has body from below and from the side
            card(L, (0, yy, 0), side, dn, ln * 0.5, ln, nrm, col, pivot=0.0)
            for q_ in (0.35, 0.62, 0.86):
                c_ = (dn[0] * ln * q_, yy + dn[1] * ln * q_, dn[2] * ln * q_)
                hang = norm((dn[0] * 0.35, -1.0, dn[2] * 0.35))
                sz = ln * (0.52 - 0.22 * q_) * r.uniform(0.85, 1.15)
                ax_ = norm((side[0] + dr[0] * r.uniform(-0.5, 0.5), 0, side[2] + dr[2] * r.uniform(-0.5, 0.5)))
                card(L, c_, ax_, hang, sz * 1.25, sz, nrm, tuple(c * (0.8 + 0.1 * q_) for c in col), pivot=0.0)
    # a tuft at the leader
    for k in range(3):
        a = k * 2.1
        card(L, (0, H * 0.985, 0), (math.cos(a), 0, math.sin(a)), (0, -1, 0), H * 0.07, H * 0.13, (math.cos(a + 1.57) * 0.5, 0.8, math.sin(a + 1.57) * 0.5), tint, pivot=0.0)
    return B, L


# ---------------------------------------------------------------- glb
def write_glb(path, mesh, _same, leaf_tex):
    buf = bytearray()
    views, accs = [], []

    def add(data, target=None):
        while len(buf) % 4:
            buf.append(0)
        views.append(dict(buffer=0, byteOffset=len(buf), byteLength=len(data), **({'target': target} if target else {})))
        buf.extend(data)
        return len(views) - 1
    M = mesh
    n = len(M.p)
    a = {}
    for key, arr, typ in (('POSITION', M.p, 'VEC3'), ('NORMAL', M.n, 'VEC3'), ('TEXCOORD_0', M.u, 'VEC2'), ('COLOR_0', M.c, 'VEC3')):
        flat = [float(x) for v in arr for x in v]
        bv = add(struct.pack('<%df' % len(flat), *flat), 34962)
        acc = dict(bufferView=bv, componentType=5126, count=n, type=typ)
        if key == 'POSITION':
            acc['min'] = [min(v[q] for v in arr) for q in range(3)]; acc['max'] = [max(v[q] for v in arr) for q in range(3)]
        accs.append(acc); a[key] = len(accs) - 1
    bv = add(struct.pack('<%dH' % len(M.i), *M.i), 34963)
    accs.append(dict(bufferView=bv, componentType=5123, count=len(M.i), type='SCALAR'))
    g = dict(asset=dict(version='2.0', generator='hewittheat treegen'), scene=0, scenes=[dict(nodes=[0])], nodes=[dict(mesh=0, name=os.path.basename(path)[:-4])],
             meshes=[dict(primitives=[dict(attributes=a, indices=len(accs) - 1, material=0)])], buffers=[dict(byteLength=len(buf))], bufferViews=views, accessors=accs,
             images=[dict(uri='../tex/t/' + leaf_tex)], samplers=[dict(magFilter=9729, minFilter=9987, wrapS=33071, wrapT=33071)], textures=[dict(source=0, sampler=0)],
             materials=[dict(name='leaf', doubleSided=True, alphaMode='MASK', alphaCutoff=0.3, pbrMetallicRoughness=dict(baseColorTexture=dict(index=0), metallicFactor=0, roughnessFactor=0.85))])
    js = json.dumps(g, separators=(',', ':')).encode()
    js += b' ' * (-len(js) % 4)
    while len(buf) % 4:
        buf.append(0)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(buf)))
        f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack('<II', len(buf), 0x004E4942)); f.write(buf)
    return len(M.i) // 3


def atlas(leaf_png, out):
    """leaves on the left half, bark on the right, so a whole tree is one mesh and one draw call"""
    lf = Image.open(leaf_png).convert('RGBA'); bk = Image.open(TEX + '/bark.jpg').convert('RGBA').resize((256, 256))
    im = Image.new('RGBA', (512, 256)); im.paste(lf, (0, 0)); im.paste(bk, (256, 0))
    im.save(out, optimize=True)


KINDS = [
    # name, crown radius (units) used by tools/trees.py to scale a tree to the canopy it stands for
    ('maple', 34), ('bigleaf', 62), ('column', 18), ('cherry', 26), ('fir', 44), ('cedar', 40),
]

if __name__ == '__main__':
    leaf_texture(TEX + '/_broad.png', 1, (80, 120, 54))
    leaf_texture(TEX + '/_fir.png', 2, (56, 104, 62), 'fir')
    leaf_texture(TEX + '/_cedar.png', 3, (74, 120, 58), 'cedar')
    bark_texture(TEX + '/bark.jpg')
    for k in ('broad', 'fir', 'cedar'):
        atlas(TEX + '/_%s.png' % k, TEX + '/tree_%s.png' % k); os.remove(TEX + '/_%s.png' % k)
    os.remove(TEX + '/bark.jpg')
    for old in ('leaf_broad.png', 'leaf_fir.png', 'leaf_cedar.png'):
        if os.path.exists(TEX + '/' + old):
            os.remove(TEX + '/' + old)
    out = {}
    out['maple'] = write_glb(ROOT + '/models/t_maple.glb', *broadleaf(11, 92, 34, 58, 30, 64, 2.3, (1.0, 1.0, 0.95)), 'tree_broad.png')
    out['bigleaf'] = write_glb(ROOT + '/models/t_bigleaf.glb', *broadleaf(12, 160, 62, 105, 48, 110, 4.6, (0.86, 0.96, 0.82), spread=1.05, lean=0.03), 'tree_broad.png')
    out['column'] = write_glb(ROOT + '/models/t_column.glb', *broadleaf(13, 100, 18, 78, 22, 52, 1.9, (0.82, 1.0, 0.8)), 'tree_broad.png')
    out['cherry'] = write_glb(ROOT + '/models/t_cherry.glb', *broadleaf(14, 56, 26, 34, 20, 46, 1.6, (1.0, 0.94, 0.8), spread=1.1), 'tree_broad.png')
    out['fir'] = write_glb(ROOT + '/models/t_fir.glb', *conifer(15, 262, 46, (0.92, 1.0, 0.95), 17, 6, 0.36, 4.4, first=0.24), 'tree_fir.png')
    out['cedar'] = write_glb(ROOT + '/models/t_cedar.glb', *conifer(16, 172, 42, (1.0, 1.0, 0.9), 13, 6, 0.6, 4.2, first=0.16, kind='cedar'), 'tree_cedar.png')
    print('triangles', out)
