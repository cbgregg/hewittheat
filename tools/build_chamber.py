"""Pruitt's office: a cutscene set modelled in Blender (units: 10 = 1 m, origin at floor centre).
Shell faces point inward so cameras outside the walls still see in."""
import bpy,bmesh,math
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
def lin(h):
    h=h.lstrip('#');c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return [((x/12.92) if x<=0.04045 else ((x+0.055)/1.055)**2.4) for x in c]+[1]
M={}
def mat(name,col,rough=0.8,emit=0.0,tex=None):
    if name in M: return M[name]
    m=bpy.data.materials.new(name)
    try: m.use_nodes=True
    except Exception: pass
    b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=lin(col);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=0
    if emit:
        (b.inputs.get('Emission Color') or b.inputs.get('Emission')).default_value=lin(col);b.inputs['Emission Strength'].default_value=emit
    if tex:
        t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(tex);m.node_tree.links.new(t.outputs['Color'],b.inputs['Base Color'])
    m.use_backface_culling=True;M[name]=m;return m
def box(name,cx,cy,z0,sx,sy,sz,m,flip=False,rz=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(cx,cy,z0+sz/2));o=bpy.context.object;o.name=name;o.scale=(sx,sy,sz);o.rotation_euler[2]=rz
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    o.data.materials.append(m)
    if flip:
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.reverse_faces(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free()
    return o
W,D,H=224,150,46
wall=mat('wall','#d9d3c6');carpet=mat('floor','#4a5868',0.95);ceil=mat('ceiling','#ebe8e0');dark=mat('dark','#2b2622',0.5);wood=mat('wood','#5a3d28',0.5);wood2=mat('wood2','#7a5636',0.55)
sh=box('shell',0,0,0,W,D,H,wall,flip=True);sh.data.materials.append(carpet);sh.data.materials.append(ceil)
for p in sh.data.polygons:
    if p.normal.z>0.5: p.material_index=1
    elif p.normal.z<-0.5: p.material_index=2
box('floor_aisle',-30,0,0.08,150,16,0.2,mat('aisle','#6b2f2a',0.95))
for (cx,cy,sx,sy) in ((0,D/2-0.4,W,0.8),(0,-D/2+0.4,W,0.8),(-W/2+0.4,0,0.8,D)): box('wains',cx,cy,0,sx,sy,12,wood2)
# dais, back wall panelling, seal and flags
box('floor_dais',80,0,0,60,130,5,wood2);box('floor_dais_step',47,0,0,6,130,2.5,wood2)
box('backpanel',W/2-1.2,0,0,1.6,134,H-4,wood)
for k in range(-5,6): box('panel_rib',W/2-2.2,k*12,0,0.6,1.2,H-4,dark)
bpy.ops.mesh.primitive_cylinder_add(vertices=40,radius=10,depth=0.8,location=(W/2-2.6,0,30),rotation=(0,math.pi/2,0));o=bpy.context.object;o.name='seal';o.data.materials.append(mat('seal','#c9a44c',0.35))
bpy.ops.mesh.primitive_cylinder_add(vertices=40,radius=7.4,depth=1.0,location=(W/2-2.9,0,30),rotation=(0,math.pi/2,0));o=bpy.context.object;o.name='seal_in';o.data.materials.append(mat('seal2','#27345c',0.5))
for fy,c in ((-56,'#27345c'),(56,'#2f5a3c')):
    box('flagpole',100,fy,5,0.7,0.7,30,mat('brass','#c9a44c',0.3));box('flag',100,fy+ (2.5 if fy<0 else -2.5),18,0.5,6,15,mat('flag'+c,c,0.9));box('flagbase',100,fy,5,3,3,0.8,dark)
# council desk with seven seats, nameplates, microphones and the speaker timer
box('desk_front',56,0,5,2,116,9.5,wood);box('desk_top',59,0,14.2,9,118,0.8,wood2);box('desk_cap',55.2,0,13.2,1.2,117,1.2,dark)
for k in range(-3,4):
    y=k*15.5
    box('seat',69,y,5,5.5,6,4.6,mat('leather','#3a2a22',0.5));box('seat_back',72,y,9.6,1,6,8,M['leather'])
    box('plate',56.6,y,15,0.4,5,1.3,mat('plate','#e9e2d0',0.6));box('mic_b',58,y+3.4,15,1,1,0.3,dark);box('mic',58,y+3.4,15.3,0.25,0.25,2.6,dark)
box('timer',54.6,0,9,0.5,9,3.6,dark);box('timer_d',54.3,0,9.6,0.2,7.4,2.4,mat('timer','#ff3a2a',0.4,emit=3.0))
# public podium, clerk table, benches
box('podium',-6,0,0,5,7,11,wood);box('podium_top',-6.6,0,11,6.4,8,0.7,wood2);box('podium_mic',-5,0,11.7,0.25,0.25,3.2,dark)
box('clerk',30,-52,0,10,22,7.6,wood2);box('clerk_seat',38,-52,0,5,5,4.4,M['leather'])
for r in range(5):
    x=-42-r*14
    for y in (-40,40):
        box('bench_s',x,y,0,5.5,52,4.3,wood2);box('bench_b',x-2.6,y,4.3,0.9,52,5.4,wood2)
        box('bench_e1',x,y-26,0,6.2,0.9,7.4,wood);box('bench_e2',x,y+26,0,6.2,0.9,7.4,wood)
for lx in (-70,-10,50):
    for ly in (-40,40): box('light',lx,ly,H-0.6,30,9,0.6,mat('lightpanel','#fff6e0',0.4,emit=3.0))
for ly in (-74.2,74.2):
    for lx in (-80,-30,20): box('sconce',lx,ly,26,4,0.8,5,mat('sconce','#ffe9c4',0.4,emit=2.0))
box('door',-W/2+0.7,0,0,0.7,18,26,wood);box('exit',-W/2+0.8,0,27.5,0.4,7,2.4,mat('exit','#3fbf5a',0.4,emit=2.5))
bpy.ops.export_scene.gltf(filepath='/home/claude/work/set/set_chamber.glb',export_format='GLB',export_yup=True,export_apply=True)
print('SET objects',len(sc.objects))
