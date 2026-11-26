"""Packs a Meshy-generated static prop for the game: texture reduced, model re-based to sit on the
ground at its centre and scaled so its longest horizontal side is LENGTH world units (10 = 1 m).
Usage: python3 tools/prop_meshy.py IN.glb models/p_<name>.glb LENGTH"""
import json, struct, sys, io
from PIL import Image
src, out, length = sys.argv[1], sys.argv[2], float(sys.argv[3])
b = open(src, 'rb').read(); jl = struct.unpack('<I', b[12:16])[0]; g = json.loads(b[20:20 + jl]); bn = b[28 + jl:]
iv = g['images'][0]['bufferView']; v = g['bufferViews'][iv]
im = Image.open(io.BytesIO(bn[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']])).convert('RGB'); im.thumbnail((768, 768))
bio = io.BytesIO(); im.save(bio, 'JPEG', quality=82); g['images'][0]['mimeType'] = 'image/jpeg'
buf = bytearray()
for i, v in enumerate(g['bufferViews']):
    d = bio.getvalue() if i == iv else bn[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]
    while len(buf) % 4: buf.append(0)
    v['byteOffset'] = len(buf); v['byteLength'] = len(d); buf.extend(d)
a = g['accessors'][g['meshes'][0]['primitives'][0]['attributes']['POSITION']]; mn, mx = a['min'], a['max']
k = length / max(mx[0] - mn[0], mx[2] - mn[2])
n = g['nodes'][0]; n.pop('matrix', None); n['scale'] = [k, k, k]; n['translation'] = [-(mn[0] + mx[0]) / 2 * k, -mn[1] * k, -(mn[2] + mx[2]) / 2 * k]
while len(buf) % 4: buf.append(0)
g['buffers'] = [{'byteLength': len(buf)}]; js = json.dumps(g, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
open(out, 'wb').write(struct.pack('<4sII', b'glTF', 2, 28 + len(js) + len(buf)) + struct.pack('<I4s', len(js), b'JSON') + js + struct.pack('<I4s', len(buf), b'BIN\x00') + bytes(buf))
print(out, len(js) + len(buf), 'bytes; size', [round((mx[i] - mn[i]) * k, 1) for i in range(3)])
