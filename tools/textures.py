"""Hewitt Heat material set. Every texture is modelled as real geometry
(recessed windows, sills, mullions, seams) with procedural shaders and rendered
orthographically in Blender Cycles. Nothing here comes from photographs.
Usage: python3 textures.py OUTDIR [name ...]"""
import bpy, sys, math, random
from mathutils import Vector

OUT = sys.argv[1]
ONLY = set(sys.argv[2:])
PPM = 128  # pixels per metre


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 40
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.view_settings.view_transform = 'Standard'
    try:
        sc.view_settings.look = 'None'
    except Exception:
        pass
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 88
    w = bpy.data.worlds.new('w')
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = w.node_tree.nodes.get('Background')
    if bg is None:
        bg = w.node_tree.nodes.new('ShaderNodeBackground')
        out = w.node_tree.nodes.new('ShaderNodeOutputWorld')
        w.node_tree.links.new(bg.outputs[0], out.inputs[0])
    bg.inputs[0].default_value = (0.92, 0.95, 1.0, 1)
    bg.inputs[1].default_value = 0.85
    return sc


def mat(name, build):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    if b is None:
        b = nt.nodes.new('ShaderNodeBsdfPrincipled')
        o = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(b.outputs[0], o.inputs[0])
    build(nt, b)
    return m


def N(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        if hasattr(n, k):
            setattr(n, k, v)
        else:
            n.inputs[k].default_value = v
    return n


def L(nt, a, b):
    nt.links.new(a, b)


def uv_vec(nt, sx=1.0, sy=1.0):
    tc = N(nt, 'ShaderNodeTexCoord')
    mp = N(nt, 'ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (sx, sy, 1)
    L(nt, tc.outputs['UV'], mp.inputs['Vector'])
    return mp.outputs['Vector']


def rgb(h, k=1.0):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) * k for x in c]
    return (c[0], c[1], c[2], 1)


def flat(name, col, rough=0.8, metal=0.0, noise=0.0, nscale=6.0):
    def b(nt, bs):
        bs.inputs['Roughness'].default_value = rough
        bs.inputs['Metallic'].default_value = metal
        if noise:
            nz = N(nt, 'ShaderNodeTexNoise')
            nz.inputs['Scale'].default_value = nscale
            nz.inputs['Detail'].default_value = 6
            L(nt, uv_vec(nt), nz.inputs['Vector'])
            mx = N(nt, 'ShaderNodeMixRGB', blend_type='MULTIPLY')
            mx.inputs[0].default_value = noise
            mx.inputs[1].default_value = rgb(col)
            L(nt, nz.outputs[0], mx.inputs[2])
            L(nt, mx.outputs[0], bs.inputs['Base Color'])
        else:
            bs.inputs['Base Color'].default_value = rgb(col)
    return mat(name, b)


def brick(name, c1, c2, mortar, bw, rh, msize=0.012, bump=0.35, dirt=0.25):
    def b(nt, bs):
        v = uv_vec(nt)
        br = N(nt, 'ShaderNodeTexBrick')
        br.offset = 0.5
        br.offset_frequency = 2
        br.inputs['Color1'].default_value = rgb(c1)
        br.inputs['Color2'].default_value = rgb(c2)
        br.inputs['Mortar'].default_value = rgb(mortar)
        br.inputs['Scale'].default_value = 1.0
        br.inputs['Mortar Size'].default_value = msize
        br.inputs['Mortar Smooth'].default_value = 0.1
        br.inputs['Bias'].default_value = 0.0
        br.inputs['Brick Width'].default_value = bw
        br.inputs['Row Height'].default_value = rh
        L(nt, v, br.inputs['Vector'])
        nz = N(nt, 'ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 1.3
        nz.inputs['Detail'].default_value = 5
        L(nt, v, nz.inputs['Vector'])
        mx = N(nt, 'ShaderNodeMixRGB', blend_type='MULTIPLY')
        mx.inputs[0].default_value = dirt
        L(nt, br.outputs['Color'], mx.inputs[1])
        L(nt, nz.outputs[0], mx.inputs[2])
        L(nt, mx.outputs[0], bs.inputs['Base Color'])
        bs.inputs['Roughness'].default_value = 0.9
        bp = N(nt, 'ShaderNodeBump')
        bp.inputs['Strength'].default_value = bump
        bp.inputs['Distance'].default_value = 0.02
        inv = N(nt, 'ShaderNodeInvert')
        L(nt, br.outputs['Fac'], inv.inputs['Color'])
        L(nt, inv.outputs[0], bp.inputs['Height'])
        L(nt, bp.outputs[0], bs.inputs['Normal'])
    return mat(name, b)


def stripes(name, col, period, depth=0.5, rough=0.6, metal=0.0, axis=0, dark=0.72):
    """corrugation / lap siding / standing seam: a wave along one axis."""
    def b(nt, bs):
        v = uv_vec(nt)
        sep = N(nt, 'ShaderNodeSeparateXYZ')
        L(nt, v, sep.inputs[0])
        m1 = N(nt, 'ShaderNodeMath', operation='MULTIPLY')
        m1.inputs[1].default_value = 1.0 / period
        L(nt, sep.outputs[axis], m1.inputs[0])
        fr = N(nt, 'ShaderNodeMath', operation='FRACT')
        L(nt, m1.outputs[0], fr.inputs[0])
        ramp = N(nt, 'ShaderNodeMapRange')
        ramp.inputs['From Min'].default_value = 0.0
        ramp.inputs['From Max'].default_value = 1.0
        ramp.inputs['To Min'].default_value = dark
        ramp.inputs['To Max'].default_value = 1.0
        L(nt, fr.outputs[0], ramp.inputs['Value'])
        mx = N(nt, 'ShaderNodeMixRGB', blend_type='MULTIPLY')
        mx.inputs[0].default_value = 1.0
        mx.inputs[1].default_value = rgb(col)
        L(nt, ramp.outputs[0], mx.inputs[2])
        nz = N(nt, 'ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 2.0
        nz.inputs['Detail'].default_value = 5
        L(nt, v, nz.inputs['Vector'])
        m2 = N(nt, 'ShaderNodeMixRGB', blend_type='MULTIPLY')
        m2.inputs[0].default_value = 0.18
        L(nt, mx.outputs[0], m2.inputs[1])
        L(nt, nz.outputs[0], m2.inputs[2])
        L(nt, m2.outputs[0], bs.inputs['Base Color'])
        bs.inputs['Roughness'].default_value = rough
        bs.inputs['Metallic'].default_value = metal
        bp = N(nt, 'ShaderNodeBump')
        bp.inputs['Strength'].default_value = depth
        bp.inputs['Distance'].default_value = 0.03
        L(nt, fr.outputs[0], bp.inputs['Height'])
        L(nt, bp.outputs[0], bs.inputs['Normal'])
    return mat(name, b)


def glass(name, top, bot, rough=0.12):
    """window glass seen from outside: a sky-to-interior gradient, no real reflections needed."""
    def b(nt, bs):
        v = uv_vec(nt)
        sep = N(nt, 'ShaderNodeSeparateXYZ')
        L(nt, v, sep.inputs[0])
        fr = N(nt, 'ShaderNodeMath', operation='FRACT')
        L(nt, sep.outputs[1], fr.inputs[0])
        mx = N(nt, 'ShaderNodeMixRGB', blend_type='MIX')
        mx.inputs[1].default_value = rgb(bot)
        mx.inputs[2].default_value = rgb(top)
        L(nt, fr.outputs[0], mx.inputs[0])
        nz = N(nt, 'ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 0.9
        L(nt, v, nz.inputs['Vector'])
        m2 = N(nt, 'ShaderNodeMixRGB', blend_type='MULTIPLY')
        m2.inputs[0].default_value = 0.35
        L(nt, mx.outputs[0], m2.inputs[1])
        L(nt, nz.outputs[0], m2.inputs[2])
        L(nt, m2.outputs[0], bs.inputs['Base Color'])
        bs.inputs['Roughness'].default_value = rough
        em = bs.inputs.get('Emission Color') or bs.inputs.get('Emission')
        if em is not None:
            L(nt, m2.outputs[0], em)
            es = bs.inputs.get('Emission Strength')
            if es is not None:
                es.default_value = 0.35
    return mat(name, b)


class Geo:
    def __init__(self):
        self.v = []
        self.f = []
        self.m = []
        self.uv = []
        self.mats = []

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def quad(self, p, m, uv=None):
        i = len(self.v)
        self.v += p
        self.f.append((i, i + 1, i + 2, i + 3))
        self.m.append(self.mi(m))
        self.uv.append(uv or [(q[0], q[2]) for q in p])

    def box(self, x0, x1, y0, y1, z0, z1, m, uvmode='xz'):
        P = lambda x, y, z: (x, y, z)
        f = lambda q: [(a[0], a[2]) for a in q] if uvmode == 'xz' else [(a[0], a[1]) for a in q]
        for q in (
            [P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)],
            [P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1)],
            [P(x0, y1, z0), P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1)],
            [P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)],
            [P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)],
            [P(x0, y1, z0), P(x1, y1, z0), P(x1, y0, z0), P(x0, y0, z0)],
        ):
            self.quad(q, m, f(q))

    def wall(self, W, H, holes, m, y=0.0):
        xs = sorted(set([0, W] + [h[0] for h in holes] + [h[2] for h in holes]))
        zs = sorted(set([0, H] + [h[1] for h in holes] + [h[3] for h in holes]))
        for i in range(len(xs) - 1):
            for j in range(len(zs) - 1):
                cx = (xs[i] + xs[i + 1]) / 2
                cz = (zs[j] + zs[j + 1]) / 2
                if any(h[0] < cx < h[2] and h[1] < cz < h[3] for h in holes):
                    continue
                self.quad([(xs[i], y, zs[j]), (xs[i + 1], y, zs[j]), (xs[i + 1], y, zs[j + 1]), (xs[i], y, zs[j + 1])], m)

    def window(self, x0, z0, x1, z1, wallm, gm, fm, depth=0.16, fr=0.06, mull=(1, 1), sill=None, lintel=None, blind=None, blindm=None):
        # reveals
        self.quad([(x0, 0, z0), (x0, depth, z0), (x0, depth, z1), (x0, 0, z1)], wallm, [(0, z0), (depth, z0), (depth, z1), (0, z1)])
        self.quad([(x1, depth, z0), (x1, 0, z0), (x1, 0, z1), (x1, depth, z1)], wallm, [(0, z0), (depth, z0), (depth, z1), (0, z1)])
        self.quad([(x0, 0, z1), (x0, depth, z1), (x1, depth, z1), (x1, 0, z1)], wallm, [(x0, 0), (x0, depth), (x1, depth), (x1, 0)])
        self.quad([(x0, depth, z0), (x0, 0, z0), (x1, 0, z0), (x1, depth, z0)], wallm, [(x0, 0), (x0, depth), (x1, depth), (x1, 0)])
        # glass, uv 0..1 vertically so the gradient spans one pane
        self.quad([(x0, depth, z0), (x1, depth, z0), (x1, depth, z1), (x0, depth, z1)], gm, [(x0, 0.02), (x1, 0.02), (x1, 0.98), (x0, 0.98)])
        if blind and blindm:
            zb = z1 - (z1 - z0) * blind
            self.quad([(x0, depth - 0.01, zb), (x1, depth - 0.01, zb), (x1, depth - 0.01, z1), (x0, depth - 0.01, z1)], blindm)
        d0 = depth - 0.05
        self.box(x0, x0 + fr, d0, depth, z0, z1, fm)
        self.box(x1 - fr, x1, d0, depth, z0, z1, fm)
        self.box(x0 + fr, x1 - fr, d0, depth, z0, z0 + fr, fm)
        self.box(x0 + fr, x1 - fr, d0, depth, z1 - fr, z1, fm)
        nx, nz = mull
        for k in range(1, nx):
            xm = x0 + (x1 - x0) * k / nx
            self.box(xm - fr / 2, xm + fr / 2, d0 - 0.004, depth, z0 + fr, z1 - fr, fm)
        for k in range(1, nz):
            zm = z0 + (z1 - z0) * k / nz
            self.box(x0 + fr, x1 - fr, d0 - 0.002, depth, zm - fr / 2, zm + fr / 2, fm)
        if sill:
            self.box(x0 - 0.08, x1 + 0.08, -0.06, depth * 0.5, z0 - 0.09, z0, sill)
        if lintel:
            self.box(x0 - 0.1, x1 + 0.1, -0.02, 0.02, z1, z1 + 0.2, lintel)

    def build(self, name='g'):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in self.mats:
            me.materials.append(m)
        for p, k in zip(me.polygons, self.m):
            p.material_index = k
        uvl = me.uv_layers.new(name='UVMap')
        i = 0
        for uvs in self.uv:
            for u in uvs:
                uvl.data[i].uv = u
                i += 1
        me.update()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def shoot(sc, name, W, H, top=False, sun=(0.42, 0.55, -0.72), strength=2.6, ppm=PPM):
    cam = bpy.data.cameras.new('c')
    cam.type = 'ORTHO'
    cam.ortho_scale = max(W, H)
    co = bpy.data.objects.new('c', cam)
    sc.collection.objects.link(co)
    if top:
        co.location = (W / 2, H / 2, 30)
        co.rotation_euler = (0, 0, 0)
        d = Vector((0.45, 0.4, -0.8))
    else:
        co.location = (W / 2, -30, H / 2)
        co.rotation_euler = (math.pi / 2, 0, 0)
        d = Vector(sun)
    sc.camera = co
    li = bpy.data.lights.new('s', 'SUN')
    li.energy = strength
    li.angle = math.radians(8)
    lo = bpy.data.objects.new('s', li)
    sc.collection.objects.link(lo)
    lo.rotation_euler = d.normalized().to_track_quat('-Z', 'Y').to_euler()
    sc.render.resolution_x = int(round(W * ppm))
    sc.render.resolution_y = int(round(H * ppm))
    sc.render.resolution_percentage = 100
    sc.render.filepath = f'{OUT}/{name}.jpg'
    bpy.ops.render.render(write_still=True)
    print('RENDERED', name, sc.render.resolution_x, sc.render.resolution_y, flush=True)


# ---------- facades: tile = 2 bays x 2 floors ----------
def facade(name, W, H, wallm, floors, bays, win, glassm, framem, sillm=None, lintelm=None, bands=(), blindm=None, mull=(1, 2), seed=1, depth=0.16, piers=None):
    rnd = random.Random(seed)
    g = Geo()
    fh = H / floors
    bw = W / bays
    ww, wh, sill_h = win
    holes = []
    for f in range(floors):
        for b in range(bays):
            x0 = b * bw + (bw - ww) / 2
            z0 = f * fh + sill_h
            holes.append((x0, z0, x0 + ww, z0 + wh))
    g.wall(W, H, holes, wallm)
    for h in holes:
        bl = rnd.choice([0, 0, 0.25, 0.4, 0.6, 1.0 if rnd.random() < 0.3 else 0.35])
        g.window(h[0], h[1], h[2], h[3], wallm, glassm, framem, depth=depth, mull=mull, sill=sillm, lintel=lintelm, blind=bl, blindm=blindm)
    for (z, t, proj, m) in bands:
        g.box(0, W, -proj, 0.01, z, z + t, m)
    if piers:
        pw, proj, m = piers
        for b in range(bays):
            g.box(b * bw - pw / 2, b * bw + pw / 2, -proj, 0.01, 0, H, m)
        g.box(W - pw / 2, W + pw / 2, -proj, 0.01, 0, H, m)
    g.build(name)


def storefront(name, W, H, wallm, glassm, framem, signm, basem, awning=None, doorm=None, seed=3):
    g = Geo()
    pier = 0.45
    bulk = 0.5
    sign0 = H - 0.95
    holes = [(pier, bulk, W / 2 - 0.75, sign0 - 0.25), (W / 2 - 0.6, 0.02, W / 2 + 0.6, sign0 - 0.25), (W / 2 + 0.75, bulk, W - pier, sign0 - 0.25)]
    g.wall(W, H, holes, wallm)
    g.window(*holes[0], wallm, glassm, framem, depth=0.12, mull=(2, 1), fr=0.07)
    g.window(*holes[2], wallm, glassm, framem, depth=0.12, mull=(2, 1), fr=0.07)
    g.window(*holes[1], wallm, glassm, doorm or framem, depth=0.3, mull=(2, 1), fr=0.11)
    g.box(0, W, -0.04, 0.01, 0, bulk, basem)
    g.box(0.25, W - 0.25, -0.06, 0.01, sign0, sign0 + 0.6, signm)
    g.box(0, W, -0.1, 0.01, H - 0.16, H, basem)
    if awning:
        g.quad([(pier - 0.1, -0.02, sign0 - 0.2), (W - pier + 0.1, -0.02, sign0 - 0.2), (W - pier + 0.1, -0.9, sign0 - 0.75), (pier - 0.1, -0.9, sign0 - 0.75)], awning)
    g.build(name)


def roof_scene(name, W, H, base, extra=None):
    g = Geo()
    g.quad([(0, 0, 0), (W, 0, 0), (W, H, 0), (0, H, 0)], base, [(0, 0), (W, 0), (W, H), (0, H)])
    if extra:
        extra(g)
    g.build(name)


def make(name):
    sc = reset()
    white = flat('white', '#eceae4', 0.6)
    stone = flat('stone', '#cfc8b8', 0.85, noise=0.3)
    dark = flat('darkmetal', '#2b2e33', 0.45, metal=0.6)
    alu = flat('alu', '#b9bcc0', 0.35, metal=0.8)
    blind = flat('blind', '#e9e4d6', 0.9)
    gl = glass('glass', '#8fb0c8', '#1d2a36')
    gl2 = glass('glass2', '#a9c3d3', '#2b3a47')

    if name == 'f_brick_red':
        w = brick('b', '#84432f', '#96523c', '#b8b0a2', 8 / 26, 6.6 / 66)
        facade(name, 8, 6.6, w, 2, 2, (1.5, 1.9, 0.95), gl, white, stone, stone, bands=[(0, 0.14, 0.05, stone)], blindm=blind, mull=(1, 2))
        shoot(sc, name, 8, 6.6)
    elif name == 'f_brick_buff':
        w = brick('b', '#b89468', '#c9a878', '#d8cfbd', 8 / 26, 6.6 / 66)
        facade(name, 8, 6.6, w, 2, 3, (1.25, 2.0, 0.9), gl, dark, stone, stone, bands=[(3.18, 0.2, 0.07, stone)], blindm=blind, mull=(1, 2), seed=4)
        shoot(sc, name, 8, 6.6)
    elif name == 'f_brick_dark':
        w = brick('b', '#4d3b34', '#5c463d', '#3a3532', 8 / 20, 6.4 / 48, msize=0.014)
        facade(name, 8, 6.4, w, 2, 2, (2.6, 2.1, 0.75), gl, dark, None, None, bands=[(3.05, 0.22, 0.05, dark)], blindm=blind, mull=(2, 1), seed=6)
        shoot(sc, name, 8, 6.4)
    elif name == 'f_concrete':
        w = flat('conc', '#b6b3ab', 0.9, noise=0.35, nscale=2.5)
        fin = flat('fin', '#a29f97', 0.9, noise=0.3)
        facade(name, 8, 7.0, w, 2, 2, (3.3, 1.7, 1.05), gl, dark, None, None, bands=[(0, 0.1, 0.03, fin), (3.5, 0.1, 0.03, fin)], blindm=blind, mull=(3, 1), seed=8, depth=0.22, piers=(0.5, 0.14, fin))
        shoot(sc, name, 8, 7.0)
    elif name == 'f_glass':
        sp = flat('spandrel', '#3f6f7a', 0.3, metal=0.2)
        g = Geo()
        W, H = 6.0, 7.2
        glt = glass('glt', '#7fc0c8', '#1f4a55', 0.08)
        g.quad([(0, 0.05, 0), (W, 0.05, 0), (W, 0.05, H), (0, 0.05, H)], glt, [(0, 0), (W, 0), (W, 2), (0, 2)])
        for f in range(2):
            g.box(0, W, 0.0, 0.06, f * 3.6, f * 3.6 + 0.85, sp)
        for k in range(5):
            x = k * 1.5
            g.box(x - 0.035, x + 0.035, -0.07, 0.05, 0, H, alu)
        for z in (0.85, 3.6, 4.45):
            g.box(0, W, -0.05, 0.05, z - 0.03, z + 0.03, alu)
        g.box(0, W, -0.05, 0.05, -0.03, 0.03, alu)
        g.box(0, W, -0.05, 0.05, H - 0.03, H + 0.03, alu)
        g.build(name)
        shoot(sc, name, W, H, strength=1.8)
    elif name == 'f_panel':
        w = flat('panel', '#e4e4e0', 0.7, noise=0.12)
        acc = flat('acc', '#6b7680', 0.7)
        g = Geo()
        W, H = 8.0, 6.2
        holes = [(0.6, 0.75, 2.4, 2.75), (4.3, 0.75, 7.4, 2.75), (0.6, 3.85, 2.4, 5.85), (4.3, 3.85, 7.4, 5.85)]
        g.wall(W, H, holes, w)
        for i, h in enumerate(holes):
            g.window(*h, w, gl2, dark, depth=0.14, mull=(1 if i % 2 == 0 else 2, 1), blind=[0, 0.4, 0.3, 0][i], blindm=blind)
        g.box(2.75, 3.95, -0.03, 0.01, 0, H, acc)
        for z in (0.0, 3.1):
            g.box(0, W, -0.015, 0.01, z - 0.012, z + 0.012, dark)
        for x in (0.0, 2.75, 3.95):
            g.box(x - 0.012, x + 0.012, -0.015, 0.01, 0, H, dark)
        g.build(name)
        shoot(sc, name, W, H)
    elif name == 'f_stucco':
        w = flat('stucco', '#e8e4da', 0.95, noise=0.22, nscale=9)
        facade(name, 8, 6.4, w, 2, 2, (1.4, 1.5, 1.1), gl, white, white, None, blindm=blind, mull=(2, 1), seed=11, depth=0.1)
        shoot(sc, name, 8, 6.4)
    elif name == 'f_metal':
        w = stripes('corr', '#e6e6e2', 0.2, depth=0.9, rough=0.5, metal=0.3)
        g = Geo()
        g.quad([(0, 0, 0), (6.4, 0, 0), (6.4, 0, 6.4), (0, 0, 6.4)], w)
        g.box(0, 6.4, -0.03, 0.01, 0, 0.5, flat('base', '#bdbab2', 0.9, noise=0.3))
        g.build(name)
        shoot(sc, name, 6.4, 6.4)
    elif name == 'f_cmu':
        w = brick('b', '#d9d6cf', '#cfccc4', '#b9b6ae', 0.4, 0.2, msize=0.012, bump=0.25, dirt=0.3)
        g = Geo()
        g.quad([(0, 0, 0), (6.4, 0, 0), (6.4, 0, 6.4), (0, 0, 6.4)], w)
        g.build(name)
        shoot(sc, name, 6.4, 6.4)
    elif name == 'f_siding':
        w = stripes('lap', '#f1efe9', 0.16, depth=1.0, rough=0.8, axis=1, dark=0.8)
        trim = flat('trim', '#ffffff', 0.7)
        g = Geo()
        W, H = 4.6, 3.0
        holes = [(1.55, 0.95, 3.05, 2.4)]
        g.wall(W, H, holes, w)
        g.window(*holes[0], w, gl, trim, depth=0.08, mull=(2, 2), fr=0.05, blind=0.3, blindm=blind)
        t = 0.11
        g.box(1.55 - t, 3.05 + t, -0.03, 0.01, 2.4, 2.4 + t * 1.3, trim)
        g.box(1.55 - t, 3.05 + t, -0.05, 0.01, 0.95 - t, 0.95, trim)
        g.box(1.55 - t, 1.55, -0.03, 0.01, 0.95, 2.4, trim)
        g.box(3.05, 3.05 + t, -0.03, 0.01, 0.95, 2.4, trim)
        g.build(name)
        shoot(sc, name, W, H)
    elif name == 'f_lap':
        w = stripes('lap', '#f1efe9', 0.16, depth=1.0, rough=0.8, axis=1, dark=0.8)
        g = Geo()
        g.quad([(0, 0, 0), (3.2, 0, 0), (3.2, 0, 3.2), (0, 0, 3.2)], w)
        g.build(name)
        shoot(sc, name, 3.2, 3.2)
    elif name == 'f_garage':
        w = flat('conc', '#c2bfb7', 0.9, noise=0.35, nscale=2.5)
        inner = flat('inner', '#1c1e21', 1.0)
        g = Geo()
        W, H = 8.0, 3.0
        g.quad([(0, 0.9, 0), (W, 0.9, 0), (W, 0.9, H), (0, 0.9, H)], inner)
        g.quad([(0, 0.9, 2.55), (W, 0.9, 2.55), (W, 0.0, 2.55), (0, 0.0, 2.55)], flat('soffit', '#6f6d68', 1.0))
        g.box(0, W, -0.05, 0.25, 0, 1.15, w)
        g.box(0, W, -0.05, 0.25, 2.75, H, w)
        g.box(-0.3, 0.3, -0.02, 0.3, 0, H, w)
        g.box(W - 0.3, W + 0.3, -0.02, 0.3, 0, H, w)
        g.box(0, W, -0.07, 0.0, 1.12, 1.17, flat('rail', '#8d9196', 0.4, metal=0.7))
        g.build(name)
        shoot(sc, name, W, H)
    elif name == 'r_parking':
        asp = flat('asp', '#4a4c50', 0.95, noise=0.4, nscale=14)
        line = flat('line', '#e9e9e4', 0.8)
        g = Geo()
        W, H = 5.2, 17.0
        g.quad([(0, 0, 0), (W, 0, 0), (W, H, 0), (0, H, 0)], asp, [(0, 0), (W, 0), (W, H), (0, H)])
        for x in (0.0, 2.6, 5.2):
            for (y0, y1) in ((0.0, 5.3), (11.7, 17.0)):
                g.quad([(x - 0.06, y0, 0.01), (x + 0.06, y0, 0.01), (x + 0.06, y1, 0.01), (x - 0.06, y1, 0.01)], line, [(0, 0), (1, 0), (1, 1), (0, 1)])
        g.build(name)
        shoot(sc, name, W, H, top=True, strength=2.0, ppm=64)
    elif name == 'shop_brick':
        w = brick('b', '#84432f', '#96523c', '#b8b0a2', 8 / 26, 0.1)
        storefront(name, 8, 3.8, w, gl, dark, flat('sign', '#e9e2cf', 0.7), stone, awning=flat('awn', '#2f4a3a', 0.9))
        shoot(sc, name, 8, 3.8)
    elif name == 'shop_modern':
        w = flat('conc', '#c9c7c1', 0.9, noise=0.25, nscale=3)
        storefront(name, 8, 3.8, w, gl2, alu, flat('sign', '#3a3f45', 0.5), flat('b2', '#8f8c85', 0.9, noise=0.3))
        shoot(sc, name, 8, 3.8)
    elif name == 'shop_buff':
        w = brick('b', '#b89468', '#c9a878', '#d8cfbd', 8 / 26, 0.1)
        storefront(name, 8, 3.8, w, gl, white, flat('sign', '#27333f', 0.6), stone, awning=flat('awn', '#7a2f2a', 0.9))
        shoot(sc, name, 8, 3.8)
    elif name == 'r_membrane':
        m = brick('seam', '#eeeeea', '#e8e8e4', '#cfcfca', 3.2, 1.6, msize=0.02, bump=0.15, dirt=0.3)
        roof_scene(name, 6.4, 6.4, m)
        shoot(sc, name, 6.4, 6.4, top=True, strength=2.0, ppm=80)
    elif name == 'r_gravel':
        def b(nt, bs):
            v = uv_vec(nt)
            n1 = N(nt, 'ShaderNodeTexNoise')
            n1.inputs['Scale'].default_value = 60
            n1.inputs['Detail'].default_value = 8
            L(nt, v, n1.inputs['Vector'])
            n2 = N(nt, 'ShaderNodeTexNoise')
            n2.inputs['Scale'].default_value = 0.8
            n2.inputs['Detail'].default_value = 4
            L(nt, v, n2.inputs['Vector'])
            cr = N(nt, 'ShaderNodeMixRGB', blend_type='MIX')
            cr.inputs[1].default_value = rgb('#77736c')
            cr.inputs[2].default_value = rgb('#d6d2c8')
            L(nt, n1.outputs[0], cr.inputs[0])
            mx = N(nt, 'ShaderNodeMixRGB', blend_type='MULTIPLY')
            mx.inputs[0].default_value = 0.5
            L(nt, cr.outputs[0], mx.inputs[1])
            L(nt, n2.outputs[0], mx.inputs[2])
            L(nt, mx.outputs[0], bs.inputs['Base Color'])
            bs.inputs['Roughness'].default_value = 1.0
            bp = N(nt, 'ShaderNodeBump')
            bp.inputs['Strength'].default_value = 0.6
            L(nt, n1.outputs[0], bp.inputs['Height'])
            L(nt, bp.outputs[0], bs.inputs['Normal'])
        roof_scene(name, 6.4, 6.4, mat('gravel', b))
        shoot(sc, name, 6.4, 6.4, top=True, strength=2.0, ppm=80)
    elif name == 'r_shingle':
        m = brick('sh', '#d9d9d6', '#bdbdb9', '#8f8f8b', 0.4, 0.2, msize=0.01, bump=0.6, dirt=0.35)
        roof_scene(name, 6.4, 6.4, m)
        shoot(sc, name, 6.4, 6.4, top=True, strength=2.2, ppm=80)
    elif name == 'r_seam':
        m = stripes('ss', '#e9ebe9', 0.4, depth=1.0, rough=0.4, metal=0.5, dark=0.6)
        roof_scene(name, 6.4, 6.4, m)
        shoot(sc, name, 6.4, 6.4, top=True, strength=2.0, ppm=80)
    elif name == 'r_dome':
        m = brick('dp', '#f2f2ee', '#e6e6e2', '#b9b9b4', 2.0, 1.0, msize=0.03, bump=0.5, dirt=0.25)
        roof_scene(name, 8, 4, m)
        shoot(sc, name, 8, 4, top=True, strength=1.8, ppm=64)
    else:
        raise SystemExit('unknown ' + name)


ALL = ['f_brick_red', 'f_brick_buff', 'f_brick_dark', 'f_concrete', 'f_glass', 'f_panel', 'f_stucco', 'f_metal', 'f_cmu', 'f_siding',
       'shop_brick', 'shop_modern', 'shop_buff', 'r_membrane', 'r_gravel', 'r_shingle', 'r_seam', 'r_dome', 'f_lap', 'f_garage', 'r_parking']
for n in ALL:
    if ONLY and n not in ONLY:
        continue
    make(n)
print('DONE')
