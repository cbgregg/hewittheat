"""Imports the city model into Blender, adds terrain, water, sun and sky, and renders stills.
Usage: python3 render_city.py CITY_GLB REPO OUTDIR [shot ...]"""
import bpy, sys, math, json
from mathutils import Vector
from PIL import Image

GLB, REPO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
ONLY = set(sys.argv[4:])
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=GLB)
print('imported', len([o for o in sc.objects if o.type == 'MESH']), 'meshes', flush=True)
for m in bpy.data.materials:
    nt = m.node_tree
    if not nt:
        continue
    b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b:
        b.inputs['Roughness'].default_value = 0.25 if 'glass' in m.name else 0.85
        b.inputs['Metallic'].default_value = 0.0

W = json.load(open(REPO + '/data/world.json'))
GS = W['gs'] * 10
gw, gh = W['gw'], W['gh']
WW, WH = W['mw'] * 20, W['mh'] * 20
hm = Image.open(REPO + '/data/hm.png').convert('RGBA').load()
H = lambda ix, iy: ((hm[ix, iy][0] << 8) | hm[ix, iy][1]) - 1000


def Hat(x, y):
    fx = min(max(x / GS, 0), gw - 1.001)
    fy = min(max(y / GS, 0), gh - 1.001)
    ix, iy = int(fx), int(fy)
    ax, ay = fx - ix, fy - iy
    return (H(ix, iy) * (1 - ax) + H(ix + 1, iy) * ax) * (1 - ay) + (H(ix, iy + 1) * (1 - ax) + H(ix + 1, iy + 1) * ax) * ay


# terrain: the game's height grid, coloured from the game's land-use mask
ST = 2
nx, ny = (gw - 1) // ST + 1, (gh - 1) // ST + 1
verts, faces, uvs = [], [], []
for j in range(ny):
    for i in range(nx):
        x, y = i * ST * GS, j * ST * GS
        verts.append((x, -y, H(min(i * ST, gw - 1), min(j * ST, gh - 1))))
for j in range(ny - 1):
    for i in range(nx - 1):
        a = j * nx + i
        faces.append((a, a + nx, a + nx + 1, a + 1))
me = bpy.data.meshes.new('ground')
me.from_pydata(verts, [], faces)
uvl = me.uv_layers.new(name='UVMap')
for p in me.polygons:
    for li in p.loop_indices:
        v = verts[me.loops[li].vertex_index]
        uvl.data[li].uv = (v[0] / WW, 1 + v[1] / WH)
    p.use_smooth = True
gm = bpy.data.materials.new('ground')
try:
    gm.use_nodes = True
except Exception:
    pass
nt = gm.node_tree
bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
img = nt.nodes.new('ShaderNodeTexImage')
img.image = bpy.data.images.load(REPO + '/data/mask.png')
img.image.colorspace_settings.name = 'Non-Color'
sep = nt.nodes.new('ShaderNodeSeparateColor')
nt.links.new(img.outputs['Color'], sep.inputs[0])


def step(sock, lo, hi):
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.interpolation_type = 'SMOOTHSTEP'
    mr.inputs['From Min'].default_value = lo
    mr.inputs['From Max'].default_value = hi
    nt.links.new(sock, mr.inputs['Value'])
    return mr.outputs[0]


def mix(fac, a, b):
    mx = nt.nodes.new('ShaderNodeMixRGB')
    nt.links.new(fac, mx.inputs[0])
    for k, v in ((1, a), (2, b)):
        if isinstance(v, tuple):
            mx.inputs[k].default_value = v
        else:
            nt.links.new(v, mx.inputs[k])
    return mx.outputs[0]


nz = nt.nodes.new('ShaderNodeTexNoise')
nz.inputs['Scale'].default_value = 900
nz.inputs['Detail'].default_value = 6
road = step(sep.outputs[0], 0.42, 0.58)
walk = step(sep.outputs[1], 0.70, 0.86)
urb = step(sep.outputs[1], 0.25, 0.42)
c = mix(urb, (0.085, 0.13, 0.05, 1), (0.25, 0.25, 0.245, 1))      # grass -> paved lot
c = mix(walk, c, (0.52, 0.52, 0.50, 1))                           # sidewalks
lotf = nt.nodes.new('ShaderNodeMath')
lotf.operation = 'MULTIPLY'
inv = nt.nodes.new('ShaderNodeMath')
inv.operation = 'SUBTRACT'
inv.inputs[0].default_value = 1.0
nt.links.new(road, inv.inputs[1])
nt.links.new(step(sep.outputs[2], 0.5, 0.72), lotf.inputs[0])
nt.links.new(inv.outputs[0], lotf.inputs[1])
c = mix(lotf.outputs[0], c, (0.075, 0.077, 0.082, 1))            # parking lots
c = mix(road, c, (0.055, 0.057, 0.062, 1))                        # asphalt
mm = nt.nodes.new('ShaderNodeMixRGB')
mm.blend_type = 'MULTIPLY'
mm.inputs[0].default_value = 0.35
nt.links.new(c, mm.inputs[1])
nt.links.new(nz.outputs[0], mm.inputs[2])
nt.links.new(mm.outputs[0], bs.inputs['Base Color'])
bs.inputs['Roughness'].default_value = 0.95
me.materials.append(gm)
sc.collection.objects.link(bpy.data.objects.new('ground', me))

wm = bpy.data.meshes.new('water')
S = 200000
wm.from_pydata([(-S, -S, -6), (S, -S, -6), (S, S, -6), (-S, S, -6)], [], [(0, 1, 2, 3)])
wmat = bpy.data.materials.new('water')
try:
    wmat.use_nodes = True
except Exception:
    pass
wb = next(n for n in wmat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
wb.inputs['Base Color'].default_value = (0.02, 0.07, 0.10, 1)
wb.inputs['Roughness'].default_value = 0.12
wm.materials.append(wmat)
sc.collection.objects.link(bpy.data.objects.new('water', wm))

# light
wd = bpy.data.worlds.new('w')
sc.world = wd
try:
    wd.use_nodes = True
except Exception:
    pass
bg = wd.node_tree.nodes.get('Background')
bg.inputs[0].default_value = (0.55, 0.68, 0.92, 1)
bg.inputs[1].default_value = 0.55
sun = bpy.data.lights.new('sun', 'SUN')
sun.energy = 5.5
sun.color = (1.0, 0.95, 0.86)
sun.angle = math.radians(1.2)
so = bpy.data.objects.new('sun', sun)
sc.collection.objects.link(so)
so.rotation_euler = Vector((-0.62, 0.48, -0.56)).normalized().to_track_quat('-Z', 'Y').to_euler()

sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 32
sc.cycles.max_bounces = 4
try:
    sc.cycles.use_denoising = True
except Exception:
    pass
try:
    sc.view_settings.view_transform = 'Filmic'
    sc.view_settings.look = 'Medium High Contrast'
except Exception as e:
    print('view', e)
import os
Q = os.environ.get('QUICK')
sc.render.resolution_x, sc.render.resolution_y = (800, 450) if Q else (1600, 900)
if Q:
    sc.cycles.samples = 12
sc.render.image_settings.file_format = 'JPEG'
sc.render.image_settings.quality = 90
cam = bpy.data.cameras.new('cam')
cam.clip_start, cam.clip_end = 5, 400000
co = bpy.data.objects.new('cam', cam)
sc.collection.objects.link(co)
sc.camera = co


def shot(name, eye, look, lens=35):
    """eye/look in game coordinates: (x, y, height above ground at that point)"""
    if ONLY and name not in ONLY:
        return
    e = Vector((eye[0], -eye[1], Hat(eye[0], eye[1]) + eye[2]))
    t = Vector((look[0], -look[1], Hat(look[0], look[1]) + look[2]))
    co.location = e
    co.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
    cam.lens = lens
    sc.render.filepath = f'{OUT}/{name}.jpg'
    bpy.ops.render.render(write_still=True)
    print('SHOT', name, flush=True)


POI = {p[0]: (p[1], p[2]) for p in W['pois']}
ch = POI['City Hall']
shot('01_downtown', (15165 - 3300, 11910 + 3600, 1900), (15165 + 1400, 11910 - 300, 60), 32)
shot('02_port_dome', (6477 - 1900, 12638 + 1700, 700), (6477, 12638, 150), 35)
es = POI['Everett Station']
shot('03_everett_station', (es[0] + 1500, es[1] + 1400, 520), (es[0], es[1], 80), 35)
ar = POI['Angel of the Winds Arena']
shot('04_arena_courthouse', (ar[0] + 2600, ar[1] + 2600, 1300), (ar[0] - 1200, ar[1] + 600, 80), 40)
shot('05_hewitt_street', (14420, 11899, 16), (18000, 11935, 40), 24)
shot('07_colby_hewitt', (15165 - 900, 11910 + 1100, 330), (15165 + 300, 11910 - 100, 40), 30)
shot('06_north_homes', (15500, 5200, 600), (17500, 2600, 20), 40)
print('DONE')
