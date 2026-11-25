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
W,D,H=124,104,34
wall=mat('wall','#d8d2c4');wood=mat('floor','#7a5636',0.6);ceil=mat('ceiling','#ebe8e0');dark=mat('dark','#2b2622',0.5);trim=mat('trim','#6e5a46',0.7)
# shell: one inward-facing box, materials by face direction
sh=box('shell',0,0,0,W,D,H,wall,flip=True);sh.data.materials.append(wood);sh.data.materials.append(ceil)
for p in sh.data.polygons:
    if p.normal.z>0.5: p.material_index=1          # floor (normal up after flip)
    elif p.normal.z<-0.5: p.material_index=2
# floor planks and rug
for i in range(-6,7):
    box('floor_plank%d'%i,0,i*8,0.05,W-0.5,0.5,0.12,dark)
box('floor_rug',0,0,0.1,62,44,0.25,mat('rug','#5d2f2a',0.95));box('floor_rug2',0,0,0.12,54,36,0.28,mat('rug2','#7d443a',0.95))
# wainscot and baseboard on all four walls
for (cx,cy,sx,sy) in ((0,D/2-0.4,W,0.8),(0,-D/2+0.4,W,0.8),(W/2-0.4,0,0.8,D),(-W/2+0.4,0,0.8,D)):
    box('wains',cx,cy,0,sx,sy,10,trim);box('rail',cx,cy,10,sx*1.0,sy*1.6 if sx>sy else sy,1.0,dark) if False else None
# windows on the +Y wall: bright panes, frames, blinds
sky=mat('window','#cfe4f4',0.3,emit=2.2);frame=mat('frame','#3a332d',0.5)
for wx in (-38,0,38):
    box('win',wx,D/2-0.7,11,26,0.6,19,sky);box('winf_t',wx,D/2-1.0,29.5,28,1.4,1.4,frame);box('winf_b',wx,D/2-1.2,10,29,2.2,1.2,frame)
    box('winf_l',wx-13.5,D/2-1.0,11,1.4,1.4,19,frame);box('winf_r',wx+13.5,D/2-1.0,11,1.4,1.4,19,frame);box('winf_m',wx,D/2-1.0,11,1.0,1.2,19,frame)
    for k in range(7): box('blind',wx,D/2-1.6,25.5-k*1.1+3,25,0.5,0.35,mat('blind','#e9e2d0',0.7))
# ceiling lights
for lx in (-30,30):
    for ly in (-22,22): box('light',lx,ly,H-0.6,24,7,0.6,mat('lightpanel','#fff6e0',0.4,emit=3.0))
# the wall map behind Pruitt's side (+X wall), framed
mp=mat('map','#ffffff',0.7,tex='/home/claude/work/set/map.jpg')
bpy.ops.mesh.primitive_plane_add(size=1,location=(W/2-1.45,0,20),rotation=(math.pi/2,0,-math.pi/2));o=bpy.context.object;o.name='map';o.scale=(46,29.7,1);bpy.ops.object.transform_apply(rotation=True,scale=True);o.data.materials.append(mp)
box('mapframe',W/2-0.8,0,4.6,0.8,49,31,dark)
# desk between the two actors, running along Y
desk=mat('desk','#4a3324',0.45)
box('desk_top',0,0,7.2,9,24,0.7,desk);box('desk_l',0,-10.5,0,8,1.2,7.2,desk);box('desk_r',0,10.5,0,8,1.2,7.2,desk);box('desk_mod',1.5,0,2.2,0.6,20,5,desk)
box('laptop_b',1.2,5,7.9,3.2,4.4,0.2,mat('alu','#b9bcc0',0.4));box('laptop_s',2.9,5,8.0,0.2,4.4,3.0,dark,rz=0)
box('papers',-1.5,-4,7.9,3,2.2,0.25,mat('paper','#f1eee6',0.9));box('papers2',-0.6,-7.6,7.9,2.2,3,0.4,mat('folder','#c9a44c',0.9))
box('phone',1.6,-2,7.9,1.6,2.4,0.7,dark);box('mug',-2.2,1.5,7.9,0.9,0.9,1.1,mat('mug','#f4f1ea',0.6))
box('lamp_b',2.2,-9,7.9,1.6,1.6,0.3,dark);box('lamp_p',2.2,-9,8.2,0.3,0.3,4.2,dark);box('lamp_h',2.2,-9,12.2,2.4,2.4,1.6,mat('shade','#3f6b4e',0.6))
# chairs
ch=mat('leather','#3a2a22',0.5)
for cx,s in ((19,1),(-19,-1)):
    box('chair_seat',cx,0 if s>0 else 0,4.2,5.2,5.2,1.0,ch);box('chair_back',cx+2.4*s,0,5.2,0.9,5.2,6.4,ch);box('chair_leg',cx,0,0,1,1,4.2,dark)
# filing cabinets, bookcase, couch, plant, door
cab=mat('cabinet','#8f9499',0.5)
for k in range(4):
    box('cab',-40+k*6.2,-D/2+3,0,6,5.4,13.5,cab)
    for q in range(3): box('cab_h',-40+k*6.2,-D/2+5.9,2.5+q*4.3,2.2,0.3,0.5,dark)
box('book',20,-D/2+2.2,0,34,4,22,desk)
for q in range(4):
    box('shelf',20,-D/2+4.3,4.6+q*5,32,0.4,0.5,dark)
    for b in range(9): box('bk',6.5+b*3.4,-D/2+3.4,0.8+q*5,2.6,2.2,3.6,mat('bk%d'%((b+q)%5),['#7a2f2a','#2f4a6b','#3f6b4e','#c9a44c','#5a5a60'][(b+q)%5],0.8))
co=mat('couch','#56606b',0.9);box('couch_s',-48,22,0,9,26,4.2,co);box('couch_b',-52,22,4.2,2.2,26,5.5,co);box('couch_a1',-48,35.6,4.2,9,1.6,2.6,co);box('couch_a2',-48,8.4,4.2,9,1.6,2.6,co)
box('pot',50,-38,0,5,5,4.5,mat('pot','#8a5a3c',0.8));box('plant',50,-38,4.5,7,7,13,mat('leaf','#3d6b3a',0.9));box('plant2',50,-38,13,4,4,7,M['leaf'])
box('door',-W/2+0.7,-24,0,0.7,10.5,22,desk);box('door_k',-W/2+1.3,-20.2,10,0.5,0.8,0.8,mat('brass','#c9a44c',0.3))
box('pic1',-W/2+0.6,18,15,0.4,12,9,dark);box('pic1i',-W/2+0.9,18,16,0.3,10,7,mat('pic','#9fb7c9',0.6));box('clock',0,-D/2+0.8,24,4.4,0.5,4.4,dark)
bpy.ops.export_scene.gltf(filepath='/home/claude/work/set/set_office.glb',export_format='GLB',export_yup=True,export_apply=True,export_image_format='JPEG')
print('SET objects',len(sc.objects))
