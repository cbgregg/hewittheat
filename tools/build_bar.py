"""The Low Tide: a dim bar interior for cutscenes, modelled in Blender (units: 10 = 1 m, origin at floor centre).
Uses the helpers at the top of build_office.py. The middle of the room is kept clear for the actors."""
import os, math
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build_office.py')).read().split('W,D,H=')[0])
W, D, H = 136, 112, 32
wall = mat('wall', '#3a2a22', 0.85); floor = mat('floor', '#2a2320', 0.5); ceil = mat('ceiling', '#17130f', 0.9)
wood = mat('wood', '#4a2f1e', 0.45); dark = mat('dark', '#17120f', 0.5); brass = mat('brass', '#b08a3e', 0.3); red = mat('vinyl', '#6a1f1c', 0.5)
sh = box('shell', 0, 0, 0, W, D, H, wall, flip=True); sh.data.materials.append(floor); sh.data.materials.append(ceil)
for p in sh.data.polygons:
    if p.normal.z > 0.5: p.material_index = 1
    elif p.normal.z < -0.5: p.material_index = 2
for i in range(-8, 9): box('floor_plank%d' % i, 0, i * 6.5, 0.04, W - 0.5, 0.4, 0.1, dark)
for (cx, cy, sx, sy) in ((0, D / 2 - 0.4, W, 0.8), (0, -D / 2 + 0.4, W, 0.8), (W / 2 - 0.4, 0, 0.8, D), (-W / 2 + 0.4, 0, 0.8, D)):
    box('wains', cx, cy, 0, sx, sy, 11, wood)
# the bar along the +Y wall: counter, foot rail, stools, back bar with lit shelves and bottles
by = D / 2 - 20
box('bar_front', 0, by, 0, 92, 5, 10.4, wood); box('bar_top', 0, by - 0.6, 10.4, 95, 7.5, 0.8, mat('bartop', '#2b1a12', 0.25)); box('bar_rail', 0, by - 3.6, 2.0, 92, 0.5, 0.5, brass)
for k in range(8):
    sx = -40 + k * 11.4
    box('stool_seat', sx, by - 8, 7.0, 3.6, 3.6, 0.8, red); box('stool_leg', sx, by - 8, 0, 0.6, 0.6, 7.0, brass); box('stool_base', sx, by - 8, 0, 3.0, 3.0, 0.3, dark)
box('backbar', 0, D / 2 - 3, 0, 96, 4.5, 9.5, wood); box('backpanel', 0, D / 2 - 1.2, 9.5, 96, 0.6, 17, mat('mirror', '#5b6b70', 0.15))
glow = mat('shelfglow', '#ffb060', 0.4, emit=2.6)
cols = ['#3f6b4e', '#8a5a2c', '#c9a44c', '#7a2f2a', '#2f4a6b', '#d8d2c4']
for q in range(3):
    box('shelf', 0, D / 2 - 3.2, 12.5 + q * 5, 92, 3.2, 0.4, dark); box('shelf_light', 0, D / 2 - 1.9, 12.9 + q * 5, 90, 0.3, 0.25, glow)
    for b in range(30): box('bottle', -43.5 + b * 3.0, D / 2 - 3.4, 12.9 + q * 5, 1.1, 1.1, 2.6 + ((b * 7 + q) % 3) * 0.5, mat('bt%d' % ((b + q) % 6), cols[(b + q) % 6], 0.2))
for k in range(5): box('tap', -8 + k * 4, by - 0.5, 11.2, 0.5, 0.5, 3.2, brass)
box('till', 30, by, 11.2, 5, 4, 3.5, dark)
# pendant lamps over the bar and the room, neon on the side wall
shade = mat('shade', '#1d3b34', 0.5); bulb = mat('bulb', '#ffcf8a', 0.4, emit=5.0)
for lx in (-36, -12, 12, 36):
    box('pend_cord', lx, by - 1, 22, 0.2, 0.2, H - 22, dark); box('pend_shade', lx, by - 1, 20.5, 5, 5, 1.6, shade); box('pend_bulb', lx, by - 1, 19.9, 2.2, 2.2, 0.6, bulb)
for (lx, ly) in ((-30, -8), (30, -8), (0, -30)):
    box('pend_cord', lx, ly, 23, 0.2, 0.2, H - 23, dark); box('pend_shade', lx, ly, 21.5, 6, 6, 1.6, shade); box('pend_bulb', lx, ly, 20.9, 2.6, 2.6, 0.6, bulb)
neon = mat('neon', '#ff3a2a', 0.4, emit=6.0); neon2 = mat('neon2', '#27d6c0', 0.4, emit=6.0)
for k, (z, w) in enumerate(((23, 34), (19.5, 26))): box('neon_bar', -W / 2 + 1.0, -12, z, 0.5, w, 1.0, neon if k == 0 else neon2)
box('neon_back', -W / 2 + 0.7, -12, 16.5, 0.4, 40, 10.5, dark)
# front window with blinds on the -X wall, door
box('win', -W / 2 + 0.7, 26, 11, 0.5, 26, 15, mat('window', '#1f2c3d', 0.2, emit=0.5))
for k in range(9): box('blind', -W / 2 + 1.2, 26, 12 + k * 1.6, 0.4, 25, 0.4, dark)
box('door', W / 2 - 0.7, -30, 0, 0.7, 10.5, 22, wood); box('exit', W / 2 - 0.8, -30, 23.5, 0.4, 6, 2.2, mat('exit', '#30d060', 0.4, emit=4.0))
# booths along the -Y wall
for k in range(4):
    bx = -48 + k * 32
    box('booth_seat_a', bx - 8.5, -D / 2 + 9, 0, 4.5, 15, 4.4, red); box('booth_back_a', bx - 10.4, -D / 2 + 9, 4.4, 1.2, 15, 7.5, red)
    box('booth_seat_b', bx + 8.5, -D / 2 + 9, 0, 4.5, 15, 4.4, red); box('booth_back_b', bx + 10.4, -D / 2 + 9, 4.4, 1.2, 15, 7.5, red)
    box('booth_table', bx, -D / 2 + 9, 6.8, 8, 13, 0.6, wood); box('booth_leg', bx, -D / 2 + 9, 0, 1, 1, 6.8, dark); box('booth_lamp', bx, -D / 2 + 1.4, 17, 2.2, 0.8, 2.2, bulb)
# pool table and jukebox at the +X end
felt = mat('felt', '#1f5a3c', 0.9)
box('pool_body', 44, -8, 5.2, 14, 26, 2.6, wood); box('pool_felt', 44, -8, 7.8, 12, 24, 0.2, felt)
for (px, py) in ((38.5, -19.5), (49.5, -19.5), (38.5, 3.5), (49.5, 3.5)): box('pool_leg', px, py, 0, 1.6, 1.6, 5.2, dark)
for k, c in enumerate(('#f4f1ea', '#c9a44c', '#7a2f2a', '#2f4a6b')): box('ball', 42 + k * 1.4, -6 - k * 2.1, 8.0, 0.6, 0.6, 0.6, mat('ball%d' % k, c, 0.2))
box('juke', W / 2 - 6, 26, 0, 7, 9, 15, mat('juke', '#7a2f2a', 0.35)); box('juke_glow', W / 2 - 9.6, 26, 8, 0.3, 7, 5.5, mat('jukeglow', '#ffb060', 0.4, emit=4.0))
# high-top table between the two actors: glasses and a bottle
box('hi_top', 0, 0, 10.2, 6.5, 6.5, 0.6, wood); box('hi_leg', 0, 0, 0, 0.9, 0.9, 10.2, dark); box('hi_base', 0, 0, 0, 4.5, 4.5, 0.4, dark)
gl = mat('glass', '#d9c79a', 0.1)
box('glass1', -1.6, 0.8, 10.8, 0.7, 0.7, 1.1, gl); box('glass2', 1.5, -1.0, 10.8, 0.7, 0.7, 1.1, gl); box('glass3', 1.2, 1.9, 10.8, 0.7, 0.7, 1.1, gl); box('bottle_t', 0, -0.4, 10.8, 0.9, 0.9, 3.0, mat('whisky', '#8a5a2c', 0.15))
# framed pictures and a dartboard
for k in range(3): box('pic', -30 + k * 30, -D / 2 + 0.7, 16, 9, 0.4, 7, dark); box('pici', -30 + k * 30, -D / 2 + 1.0, 16.7, 7.6, 0.3, 5.6, mat('pic%d' % k, ['#6b7a85', '#8a7a5c', '#5c6b5a'][k], 0.7))
os.makedirs('/home/claude/work/set', exist_ok=True)
bpy.ops.export_scene.gltf(filepath='/home/claude/work/set/set_bar.glb', export_format='GLB', export_yup=True, export_apply=True, export_image_format='JPEG')
print('SET objects', len(sc.objects))
