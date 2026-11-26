"""Prepares the two civilian models straight from the downloaded glTF (no re-export, so the skin
binding is untouched): bones get Mixamo-standard names, and body surfaces are re-assigned by
which bones drive them so each character has a full top and trousers that can be coloured."""
import json, struct, re, base64, sys, copy
CT = {5121: ('B', 1), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}

def run(src, out, cover_arms):
    b = open(src, 'rb').read()
    jl = struct.unpack('<I', b[12:16])[0]
    g = json.loads(b[20:20 + jl])
    bl = struct.unpack('<I', b[20 + jl:24 + jl])[0]
    bn = bytearray(b[28 + jl:28 + jl + bl])
    for n in g['nodes']:
        if 'name' in n and 'mixamorig' in n['name']:
            n['name'] = re.sub(r'_\d+$', '', n['name']).replace(':', '')
    g.pop('animations', None)

    def read(ai):
        a = g['accessors'][ai]; v = g['bufferViews'][a['bufferView']]
        f, sz = CT[a['componentType']]; nc = NC[a['type']]
        st = v.get('byteStride') or sz * nc
        o = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        return [struct.unpack_from('<%d%s' % (nc, f), bn, o + i * st) for i in range(a['count'])]
    mats = g['materials']
    name = lambda i: mats[i].get('name', '')
    ci = next(i for i, m in enumerate(mats) if m.get('name') == 'clothing')
    pm = copy.deepcopy(mats[ci]); pm['name'] = 'pants'; mats.append(pm); pi = len(mats) - 1
    jn = [g['nodes'][j].get('name', '') for j in g['skins'][0]['joints']]

    def cat(nm):
        if re.search(r'UpLeg|Leg$', nm): return 'leg'
        if re.search(r'Foot|Toe', nm): return 'foot'
        if re.search(r'Hand', nm): return 'hand'
        if re.search(r'Neck|Head', nm): return 'head'
        if re.search(r'ForeArm|Arm$', nm): return 'arm'
        return 'torso'
    moved = 0
    for me in g['meshes']:
        prims = []
        for p in me['primitives']:
            mn = name(p.get('material', 0))
            if mn not in ('skin', 'clothing') or 'JOINTS_0' not in p['attributes'] or 'indices' not in p:
                prims.append(p); continue
            J, Wt, I = read(p['attributes']['JOINTS_0']), read(p['attributes']['WEIGHTS_0']), [x[0] for x in read(p['indices'])]
            vc = [cat(jn[j[max(range(4), key=lambda k: w[k])]]) for j, w in zip(J, Wt)]
            groups = {}
            for t in range(0, len(I), 3):
                cs = [vc[I[t]], vc[I[t + 1]], vc[I[t + 2]]]
                c = max(set(cs), key=cs.count)
                if c == 'leg' or (c == 'torso' and mn == 'clothing' and cs.count('leg') > 0): m = pi
                elif mn == 'skin' and (c == 'torso' or (c == 'arm' and cover_arms)): m = ci
                else: m = p.get('material', 0)
                groups.setdefault(m, []).extend(I[t:t + 3])
            for m, idx in groups.items():
                while len(bn) % 4: bn.append(0)
                off = len(bn); bn.extend(struct.pack('<%dI' % len(idx), *idx))
                g['bufferViews'].append({'buffer': 0, 'byteOffset': off, 'byteLength': len(idx) * 4, 'target': 34963})
                g['accessors'].append({'bufferView': len(g['bufferViews']) - 1, 'componentType': 5125, 'count': len(idx), 'type': 'SCALAR'})
                q = dict(p); q['indices'] = len(g['accessors']) - 1; q['material'] = m; prims.append(q)
                if m != p.get('material', 0): moved += len(idx) // 3
        me['primitives'] = prims
    while len(bn) % 4: bn.append(0)
    g['buffers'][0]['byteLength'] = len(bn)
    js = json.dumps(g, separators=(',', ':')).encode()
    while len(js) % 4: js += b' '
    o = struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(bn)) + struct.pack('<I4s', len(js), b'JSON') + js + struct.pack('<I4s', len(bn), b'BIN\x00') + bytes(bn)
    open(out, 'w').write(base64.b64encode(o).decode())
    print(out.split('/')[-1], len(o) // 1024, 'KB, triangles re-dressed', moved)

run(sys.argv[1] + '/p_male/scene.glb', 'models/man.b64.txt', False)
run(sys.argv[1] + '/p_female/scene.glb', 'models/woman.b64.txt', True)
