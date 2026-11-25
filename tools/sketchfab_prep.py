"""Normalises downloaded Sketchfab models for the game: props are joined, re-based, scaled and
stripped to a base-colour texture; people get Mixamo-standard bone names and split outfits."""
import bpy, sys, os, re, math
from mathutils import Vector, Matrix

def load(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    f = 'dl/%s/scene.glb' % name
    bpy.ops.import_scene.gltf(filepath=f)
    return [o for o in bpy.context.scene.objects if o.type == 'MESH']

def slim_materials(maxpx):
    for m in bpy.data.materials:
        nt = m.node_tree
        if not nt:
            continue
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not b:
            continue
        for inp in list(b.inputs):
            if inp.name not in ('Base Color', 'Alpha'):
                for l in list(inp.links):
                    nt.links.remove(l)
        b.inputs['Metallic'].default_value = 0.0
        b.inputs['Roughness'].default_value = 0.8
    for im in bpy.data.images:
        if im.size[0] > maxpx or im.size[1] > maxpx:
            k = maxpx / max(im.size[0], im.size[1])
            im.scale(max(1, int(im.size[0] * k)), max(1, int(im.size[1] * k)))

def export(path):
    kw = dict(filepath=path, export_format='GLB', export_yup=True, export_apply=False, export_animations=False)
    try:
        bpy.ops.export_scene.gltf(export_image_format='JPEG', export_jpeg_quality=82, **kw)
    except TypeError:
        bpy.ops.export_scene.gltf(**kw)

def prop(name, height, anchor='center', keep_png=False, maxpx=512):
    ms = load(name)
    bpy.ops.object.select_all(action='DESELECT')
    for o in ms:
        o.select_set(True)
    bpy.context.view_layer.objects.active = ms[0]
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    if len(ms) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    vs = [v.co.copy() for v in ob.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    H = hi.z - lo.z
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    rot = 0.0
    if anchor == 'pole':
        low = [v for v in vs if v.z < lo.z + H * 0.06]
        bx, by = sum(v.x for v in low) / len(low), sum(v.y for v in low) / len(low)
        rot = -math.atan2(cy - by, cx - bx)      # arm ends up pointing +X
        cx, cy = bx, by
    k = height / H
    M = Matrix.Rotation(rot, 4, 'Z') @ Matrix.Scale(k, 4) @ Matrix.Translation((-cx, -cy, -lo.z))
    ob.data.transform(M)
    ob.data.update()
    for o in list(bpy.context.scene.objects):
        if o != ob:
            bpy.data.objects.remove(o, do_unlink=True)
    slim_materials(maxpx)
    export('out/p_%s.glb' % name)
    d = ob.dimensions
    print('PROP', name, 'tris', sum(len(p.vertices) - 2 for p in ob.data.polygons), 'dims', [round(x, 1) for x in d], 'mats', len(ob.data.materials), os.path.getsize('out/p_%s.glb' % name) // 1024, 'KB', flush=True)

def person(name, out):
    ms = load(name)
    arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    for b in arm.data.bones:
        b.name = re.sub(r'_\d+$', '', b.name).replace(':', '')
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    hips = arm.data.bones.get('mixamorigHips')
    hz = (arm.matrix_world @ hips.head_local).z
    pants = bpy.data.materials.new('pants')
    try:
        pants.use_nodes = True
    except Exception:
        pass
    names = []
    for o in ms:
        for sl in o.material_slots:
            if sl.material and 'cloth' in sl.material.name.lower():
                b = next((n for n in sl.material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if b and not b.inputs['Base Color'].links:
                    b.inputs['Base Color'].default_value = (1, 1, 1, 1)
                sl.material.name = 'clothing'
                o.data.materials.append(pants)
                pi = len(o.data.materials) - 1
                ci = list(o.data.materials).index(sl.material)
                gn = {g.index: g.name for g in o.vertex_groups}
                for p in o.data.polygons:
                    if p.material_index != ci:
                        continue
                    leg = tot = 0.0
                    for vi in p.vertices:
                        for g in o.data.vertices[vi].groups:
                            nm = gn.get(g.group, '')
                            tot += g.weight
                            if re.search(r'UpLeg|Leg|Foot|Toe', nm):
                                leg += g.weight
                            elif nm.endswith('Hips'):
                                leg += g.weight * 0.6
                    if tot and leg / tot >= 0.5:
                        p.material_index = pi
        names += [sl.material.name for sl in o.material_slots if sl.material]
    b = next((n for n in pants.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    b.inputs['Base Color'].default_value = (1, 1, 1, 1)
    slim_materials(256)
    export('out/%s.glb' % out)
    zs = [(o.matrix_world @ Vector(c)).z for o in ms for c in o.bound_box]
    print('PERSON', out, 'bones', len(arm.data.bones), [b.name for b in arm.data.bones][:3], 'height', round(max(zs) - min(zs), 2), 'hips z', round(hz, 2), 'mats', sorted(set(names)), os.path.getsize('out/%s.glb' % out) // 1024, 'KB', flush=True)

import sys
if 'props' in sys.argv:
    prop('pine2', 110); prop('trash2', 11, maxpx=256); prop('signal2', 62, 'pole')
else:
    person('p_male', 'man'); person('p_female', 'woman')
