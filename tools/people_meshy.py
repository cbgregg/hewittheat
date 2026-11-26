"""Packs Meshy-generated characters for the game: one GLB per person with a 1024 px texture and
its own Walk and Run clips (taken from Meshy's rigging output), written to models/hh_<name>.b64.txt.
Then registers whoever is available in js/game.js and data/story.json.
Usage: python3 tools/people_meshy.py MESHY_OUT_DIR"""
import json, struct, os, sys, io, re, base64
from PIL import Image
SRC = sys.argv[1] if len(sys.argv) > 1 else '.'
def load(f):
    b = open(f, 'rb').read(); jl = struct.unpack('<I', b[12:16])[0]; g = json.loads(b[20:20 + jl])
    bl = struct.unpack('<I', b[20 + jl:24 + jl])[0]; return g, b[28 + jl:28 + jl + bl]
# where the lip line sits on each face, as a fraction from chin (0) to top of head (1); read off tools' debug view
MOUTH = {'attendant': 0.168, 'cong': 0.212, 'cop': 0.178, 'danny': 0.186, 'dee': 0.15, 'hargrove': 0.195, 'marge': 0.188, 'olsen': 0.32,
         'ped_m1': 0.15, 'ped_m2': 0.198, 'ped_w1': 0.292, 'ped_w2': 0.065, 'pruitt': 0.23, 'sam': 0.208}
def head_frame(g, buf, names):
    """Body axes from the T-pose skeleton and every vertex's place on the head (t: 0 chin .. 1 top, z: forward)."""
    import numpy as np
    pr = g['meshes'][0]['primitives'][0]; sk = g['skins'][0]; jn = [names[j] for j in sk['joints']]
    CT = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
    def arr(ai, nc):
        A = g['accessors'][ai]; V = g['bufferViews'][A['bufferView']]; dt = CT[A['componentType']]; st = V.get('byteStride') or np.dtype(dt).itemsize * nc
        o = V.get('byteOffset', 0) + A.get('byteOffset', 0)
        return np.array([np.frombuffer(buf, dt, nc, o + i * st) for i in range(A['count'])])
    P = arr(pr['attributes']['POSITION'], 3).astype(np.float64); J = arr(pr['attributes']['JOINTS_0'], 4)
    W = arr(pr['attributes']['WEIGHTS_0'], 4).astype(np.float64); W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    I = arr(pr['indices'], 1).reshape(-1, 3).astype(np.int64)
    IB = arr(sk['inverseBindMatrices'], 16).reshape(-1, 4, 4).transpose(0, 2, 1).astype(np.float64)
    jp = lambda nm: np.linalg.inv(IB[jn.index(nm)])[:3, 3]
    Hh = jp('Head'); up = Hh - jp('Hips'); body = np.linalg.norm(up); up /= body
    rt = jp('RightArm') - jp('LeftArm'); rt -= up * (rt @ up); rt /= np.linalg.norm(rt)
    fw = np.cross(rt, up); toe = (jp('LeftToeBase') - jp('LeftFoot')) + (jp('RightToeBase') - jp('RightFoot'))
    if fw @ toe < 0: fw = -fw
    hw = sum(np.where(J == i, W, 0).sum(1) for i, n in enumerate(jn) if n.lower().startswith('head'))
    y = (P - Hh) @ up; z = (P - Hh) @ fw; x = (P - Hh) @ rt; head = hw > 0.5
    zmax = z[head].max(); yt = y[head].max()
    for _ in range(2):  # chin = lowest point of the face front; forward reach measured on the face, not on hair or a hat brim
        ych = np.percentile(y[head & (z > 0.5 * zmax)], 1); zmax = z[head & (y < ych + 0.6 * (yt - ych))].max()
    return dict(np=np, pr=pr, P=P, I=I, UV=arr(pr['attributes']['TEXCOORD_0'], 2).astype(np.float64), up=up, body=body, hw=hw, head=head, x=x, z=z, zmax=zmax, t=(y - ych) / (yt - ych), face=yt - ych)
def pack(k):
    g, bn = load('%s/%s_rig.glb' % (SRC, k))
    iv = g['images'][0]['bufferView']
    v = g['bufferViews'][iv]; im = Image.open(io.BytesIO(bn[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']])).convert('RGB')
    im.thumbnail((1024, 1024)); bio = io.BytesIO(); im.save(bio, 'JPEG', quality=84); g['images'][0]['mimeType'] = 'image/jpeg'
    out = bytearray()
    for i, v in enumerate(g['bufferViews']):
        d = bio.getvalue() if i == iv else bn[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]
        while len(out) % 4: out.append(0)
        v['byteOffset'] = len(out); v['byteLength'] = len(d); out.extend(d)
    names = [n.get('name') for n in g['nodes']]
    # smooth normals, then a "mouthOpen" shape: the front of the head below the lip line drops like a jaw
    try:
        fr = head_frame(g, out, names); np = fr['np']; pr = fr['pr']; Pp = fr['P']
        ni = pr['attributes'].get('NORMAL')
        if ni is not None:  # Meshy splits the mesh into many small UV islands with hard normals: average them per position
            A = g['accessors'][ni]; V = g['bufferViews'][A['bufferView']]
            if not V.get('byteStride') or V['byteStride'] == 12:
                I = fr['I']; _, inv = np.unique(np.round(Pp / fr['body'] * 4e4).astype(np.int64), axis=0, return_inverse=True); inv = inv.reshape(-1)
                fn = np.cross(Pp[I[:, 1]] - Pp[I[:, 0]], Pp[I[:, 2]] - Pp[I[:, 0]]); acc_n = np.zeros((inv.max() + 1, 3))
                for c in range(3): np.add.at(acc_n, inv[I[:, c]], fn)
                Nn = acc_n[inv]; Nn /= np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-12)
                o = V['byteOffset'] + A.get('byteOffset', 0); out[o:o + len(Nn) * 12] = Nn.astype(np.float32).tobytes()
        sm = lambda x: np.clip(x, 0, 1) ** 2 * (3 - 2 * np.clip(x, 0, 1))
        ym = MOUTH.get(k, 0.235)
        wgt = sm((fr['z'] / fr['zmax'] - 0.25) / 0.35) * sm((ym - fr['t']) * fr['face'] / (0.016 * fr['body'])) * sm((fr['hw'] - 0.3) / 0.5)
        D = (-fr['up'][None, :] * (0.026 * fr['body']) * wgt[:, None]).astype(np.float32)
        while len(out) % 4: out.append(0)
        g['bufferViews'].append({'buffer': 0, 'byteOffset': len(out), 'byteLength': D.nbytes}); out.extend(D.tobytes())
        g['accessors'].append({'bufferView': len(g['bufferViews']) - 1, 'componentType': 5126, 'count': len(D), 'type': 'VEC3', 'min': D.min(0).tolist(), 'max': D.max(0).tolist()})
        pr['targets'] = [{'POSITION': len(g['accessors']) - 1}]; g['meshes'][0]['weights'] = [0.0]; g['meshes'][0].setdefault('extras', {})['targetNames'] = ['mouthOpen']
        jaw = int((wgt > 0.5).sum())
    except Exception as e:
        jaw = 'no jaw: ' + str(e)[:80]
    g['animations'] = []
    for tag, nm in (('walk', 'Walk'), ('run', 'Run')):
        f = '%s/%s_%s.glb' % (SRC, k, tag)
        if not os.path.exists(f): continue
        h, hb = load(f); hn = [n.get('name') for n in h['nodes']]; a = h['animations'][0]; amap = {}
        def acc(ai):
            if ai in amap: return amap[ai]
            A = dict(h['accessors'][ai]); V = h['bufferViews'][A['bufferView']]
            n = A['count'] * {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[A['type']] * 4
            o = V.get('byteOffset', 0) + A.get('byteOffset', 0); d = hb[o:o + n]
            while len(out) % 4: out.append(0)
            g['bufferViews'].append({'buffer': 0, 'byteOffset': len(out), 'byteLength': len(d)}); out.extend(d)
            A['bufferView'] = len(g['bufferViews']) - 1; A.pop('byteOffset', None); g['accessors'].append(A); amap[ai] = len(g['accessors']) - 1; return amap[ai]
        S, C = [], []
        for c in a['channels']:
            node = hn[c['target']['node']]; path = c['target']['path']
            if path == 'scale' or (path == 'translation' and node != 'Hips') or node not in names: continue
            s = a['samplers'][c['sampler']]; S.append({'input': acc(s['input']), 'output': acc(s['output']), 'interpolation': s.get('interpolation', 'LINEAR')})
            C.append({'sampler': len(S) - 1, 'target': {'node': names.index(node), 'path': path}})
        g['animations'].append({'name': nm, 'samplers': S, 'channels': C})
    while len(out) % 4: out.append(0)
    g['buffers'] = [{'byteLength': len(out)}]
    js = json.dumps(g, separators=(',', ':')).encode()
    while len(js) % 4: js += b' '
    o = struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(out)) + struct.pack('<I4s', len(js), b'JSON') + js + struct.pack('<I4s', len(out), b'BIN\x00') + bytes(out)
    open('models/hh_%s.b64.txt' % k, 'w').write(base64.b64encode(o).decode()); return (len(o) // 1024, jaw)
def main():
    have = sorted(f[:-8] for f in os.listdir(SRC) if f.endswith('_rig.glb'))
    print({k: pack(k) for k in have})
    s = open('js/game.js').read()
    s, n = re.subn(r"const MYL=\[[^\]]*\];", "const MYL=" + json.dumps(have, separators=(',', ':')) + ";", s); assert n == 1
    open('js/game.js', 'w').write(s)
    st = json.load(open('data/story.json'))
    for k, c in st['cast'].items():
        if k in have: c['ch'] = 'hh_' + k; c.pop('look', None)
    json.dump(st, open('data/story.json', 'w'), ensure_ascii=False, separators=(',', ':'))
if __name__ == '__main__': main()
