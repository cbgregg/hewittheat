"""Building dossiers: an internal reference tool for matching the game's buildings to the real ones.

For every game footprint inside a box it joins the public records for that spot and cuts aerial crops, so each
building can be set from evidence instead of guesses:

  City of Everett building footprints   street address, use code
  Snohomish County parcels              parcel number, situs address, assessor use code, lot size
  Snohomish County roofprints           LiDAR roof heights in feet (mean, 95th percentile, max)
  Snohomish County 911 address points   every address on the footprint and what each is used as
  City / state / national registers     historic name, construction year, district
  County 2024 and city 2022 aerials     3 inch per pixel crops (two flights lean differently, so different walls show)
  Wikimedia Commons                     geotagged street-level photos near the box, with licence and link (reference only)

Usage:
  python3 tools/dossier.py NAME X0 Y0 X1 Y1      # box in game world units (tools/blockmap.py prints crossings)

Writes dossier/NAME/: records.json, index.html (one card per building), b<index>_2024.jpg / b<index>_2022.jpg,
overview.jpg, street_photos.json. The dossier/ folder is reference material and is not
committed: the aerial photos belong to the county, the city and their contractor and never go into game assets.
A trimmed copy of the records (no owner names, no values) is written to data/dossier/NAME.json for citygen.
"""
import json, math, os, sys, time, urllib.parse, urllib.request, io
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# game world (10 units = 1 m, y south) -> WA State Plane North, US feet (EPSG 2285).
# Least-squares fit of 99 footprints to the city layer, median error 0.17 ft. The 1.02 degree turn is grid convergence.
A = ((3.28665683e-01, -5.72911741e-03, 1.29868259e+06), (-5.84056013e-03, -3.27901988e-01, 3.64216409e+05))
DET = A[0][0] * A[1][1] - A[0][1] * A[1][0]


def w2sp(x, y):
    return A[0][0] * x + A[0][1] * y + A[0][2], A[1][0] * x + A[1][1] * y + A[1][2]


def sp2w(e, n):
    e -= A[0][2]; n -= A[1][2]
    return (A[1][1] * e - A[0][1] * n) / DET, (-A[1][0] * e + A[0][0] * n) / DET


CITY = 'https://gismaps.everettwa.gov/manarcgis/rest/services/'
CNTY = 'https://gis.snoco.org/host/rest/services/Hosted/'
LAYERS = {
    'footprints': CITY + 'Buildings/Buildings/MapServer/0',
    'parcels': CNTY + 'CADASTRAL__parcels/FeatureServer/0',
    'roofs': CNTY + 'BUILDINGS__roofprints/FeatureServer/0',
    'addr911': CNTY + 'BUILDINGS__address_911/FeatureServer/0',
    'reg_city': CITY + 'Planning/Planning/MapServer/18',
    'reg_state': CITY + 'Planning/Planning/MapServer/25',
    'district': CITY + 'Planning/Planning/MapServer/24',
}
AERIAL = {'2024': 'https://gis.snoco.org/img/rest/services/Imagery/Aerial_2024/ImageServer',
          '2022': CITY + 'Imagery/Image2022_3in_sid/ImageServer'}


def get(url, params, binary=False, tries=3):
    u = url + '?' + urllib.parse.urlencode(params)
    for t in range(tries):
        try:
            r = urllib.request.urlopen(u, timeout=120).read()
            return r if binary else json.loads(r)
        except Exception as ex:
            if t == tries - 1:
                raise
            time.sleep(2 + 3 * t)


def layer(name, env, cache):
    f = os.path.join(cache, name + '.json')
    if os.path.exists(f):
        return json.load(open(f))
    out, off = [], 0
    while True:
        d = get(LAYERS[name] + '/query', {'f': 'json', 'geometry': json.dumps(env), 'geometryType': 'esriGeometryEnvelope', 'inSR': 2285, 'outSR': 2285,
                                           'spatialRel': 'esriSpatialRelIntersects', 'outFields': '*', 'returnGeometry': 'true', 'resultOffset': off})
        if 'error' in d:
            raise RuntimeError(name + ': ' + json.dumps(d['error']))
        out += d['features']
        if not d.get('exceededTransferLimit'):
            break
        off += len(d['features'])
    json.dump(out, open(f, 'w'))
    return out


def aerial(year, e0, n0, e1, n1, cache, key, ppf=4):
    """3 inch imagery is 4 px per foot. Returns a PIL image of the State Plane box."""
    f = os.path.join(cache, '%s_%s.jpg' % (key, year))
    if not os.path.exists(f):
        w, h = int((e1 - e0) * ppf), int((n1 - n0) * ppf)
        k = max(1.0, w / 4000, h / 4000)
        raw = get(AERIAL[year] + '/exportImage', {'f': 'image', 'bbox': '%f,%f,%f,%f' % (e0, n0, e1, n1), 'bboxSR': 2285, 'imageSR': 2285,
                                                   'size': '%d,%d' % (w / k, h / k), 'format': 'jpgpng', 'interpolation': 'RSP_BilinearInterpolation'}, binary=True)
        Image.open(io.BytesIO(raw)).convert('RGB').save(f, quality=92)
    return Image.open(f)


def commons(x0, y0, x1, y1, cache):
    """Geotagged Commons photos around the box. The API rate-limits hard, so failures are skipped and results cached."""
    f = os.path.join(cache, 'commons.json')
    if os.path.exists(f):
        return json.load(open(f))
    ll = lambda x, y: (47.9790 - (y - 11910) * 0.1 / 111200, -122.2079 + (x - 15165) * 0.1 / 74520)   # good to a few metres downtown
    seen = {}
    xs = [x0 + 1200 * k for k in range(int((x1 - x0) / 1200) + 2)]; ys = [y0 + 1200 * k for k in range(int((y1 - y0) / 1200) + 2)]
    for x in xs:
        for y in ys:
            lat, lon = ll(min(x, x1), min(y, y1))
            q = urllib.parse.urlencode({'action': 'query', 'format': 'json', 'generator': 'geosearch', 'ggscoord': '%f|%f' % (lat, lon), 'ggsradius': 130, 'ggsnamespace': 6,
                                        'ggslimit': 50, 'prop': 'coordinates|imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': 960, 'colimit': 50})
            try:
                time.sleep(4)
                d = json.loads(urllib.request.urlopen(urllib.request.Request('https://commons.wikimedia.org/w/api.php?' + q, headers={'User-Agent': 'hewittheat-dossier/0.1 (building reference)'}), timeout=60).read())
            except Exception as ex:
                print('commons skipped:', ex); continue
            for pg in (d.get('query', {}).get('pages') or {}).values():
                ii = (pg.get('imageinfo') or [{}])[0]; c = (pg.get('coordinates') or [{}])[0]; m = ii.get('extmetadata', {})
                seen[pg['title']] = dict(title=pg['title'], lat=c.get('lat'), lon=c.get('lon'), page=ii.get('descriptionurl'), thumb=ii.get('thumburl'),
                                         licence=m.get('LicenseShortName', {}).get('value'), date=m.get('DateTimeOriginal', {}).get('value', '')[:10])
    json.dump(list(seen.values()), open(f, 'w'), indent=1)
    return list(seen.values())


def pip(x, y, ring):
    c = False
    for k in range(len(ring)):
        x1, y1 = ring[k][:2]; x2, y2 = ring[k - 1][:2]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def area(r):
    return abs(sum(r[k][0] * r[k - 1][1] - r[k - 1][0] * r[k][1] for k in range(len(r)))) / 2


def cen(r):
    xs = [p[0] for p in r]; ys = [p[1] for p in r]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def grid_overlap(a, b, step=3.0):
    """Share of ring a (State Plane feet) that lies inside ring b, sampled on a grid."""
    xs = [p[0] for p in a]; ys = [p[1] for p in a]
    n = hit = 0
    y = min(ys) + step / 2
    while y < max(ys):
        x = min(xs) + step / 2
        while x < max(xs):
            if pip(x, y, a):
                n += 1; hit += pip(x, y, b)
            x += step
        y += step
    return hit / n if n else 0.0


def font(sz, bold=False):
    try:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else ''), sz)
    except Exception:
        return None


def frontage(ring_w, edges, nodes, names):
    """Streets a footprint faces: nearest named street to each wall midpoint within 22 m, with compass side and wall length (m)."""
    out = {}
    cx, cy = cen(ring_w)
    for k in range(len(ring_w)):
        (x1, y1), (x2, y2) = ring_w[k - 1], ring_w[k]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2; ln = math.hypot(x2 - x1, y2 - y1) / 10
        if ln < 3:
            continue
        best = None
        for e in edges:
            a, b = nodes[e[0]], nodes[e[1]]; dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy or 1
            t = max(0, min(1, ((mx - a[0]) * dx + (my - a[1]) * dy) / L2)); d = math.hypot(mx - a[0] - t * dx, my - a[1] - t * dy)
            if 0 < t < 1 and abs(dx * (x2 - x1) + dy * (y2 - y1)) / math.sqrt(L2) / (ln * 10) > 0.8 and (best is None or d < best[0]):
                best = (d, names[e[4]])
        if best and best[0] < 220:
            ox, oy = mx - cx, my - cy
            side = ('E' if ox > 0 else 'W') if abs(ox) > abs(oy) else ('S' if oy > 0 else 'N')
            key = (best[1], side)
            out[key] = out.get(key, 0) + ln
    return [dict(street=k[0], side=k[1], m=round(v, 1)) for k, v in sorted(out.items(), key=lambda t: -t[1])]


def main():
    name = sys.argv[1]; x0, y0, x1, y1 = [float(v) for v in sys.argv[2:6]]
    out = os.path.join(ROOT, 'dossier', name); cache = os.path.join(out, 'raw'); os.makedirs(cache, exist_ok=True)
    W = json.load(open(ROOT + '/data/world.json'))
    cur = json.load(open(ROOT + '/data/buildings.json'))
    info = json.load(open(ROOT + '/data/city_info.json'))
    c = [w2sp(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    env = dict(xmin=min(p[0] for p in c) - 40, xmax=max(p[0] for p in c) + 40, ymin=min(p[1] for p in c) - 40, ymax=max(p[1] for p in c) + 40)
    L = {k: layer(k, env, cache) for k in LAYERS}
    print({k: len(v) for k, v in L.items()})
    ring = lambda f: f['geometry']['rings'][0]
    recs = []
    for i, b in enumerate(W['bld']):
        n = (len(b) - 3) // 2
        rw = [(b[3 + 2 * k], b[4 + 2 * k]) for k in range(n)]
        cx, cy = cen(rw)
        if not (x0 < cx < x1 and y0 < cy < y1):
            continue
        rs = [w2sp(*p) for p in rw]; ce, cn = cen(rs)
        R = dict(i=i, world=[round(cx), round(cy)], sp=[round(ce, 1), round(cn, 1)], footprint_sqft=round(area(rs)),
                 dims_m=[round((max(p[0] for p in rw) - min(p[0] for p in rw)) / 10, 1), round((max(p[1] for p in rw) - min(p[1] for p in rw)) / 10, 1)],
                 game=dict(zip(('wall', 'tint', 'roof', 'rtint', 'storeys', 'shop'), cur.get(str(i), [])[:6])), game_height_m=b[0] / 10, kind=b[1],
                 names=info['named'].get(str(i), []), fronts=frontage(rw, W['edges'], W['nodes'], W['names']))
        # city footprint: same data the game was built from, so match on centre
        m = min(L['footprints'], key=lambda f: math.hypot(cen(ring(f))[0] - ce, cen(ring(f))[1] - cn), default=None)
        if m and math.hypot(cen(ring(m))[0] - ce, cen(ring(m))[1] - cn) < 12:
            a = m['attributes']
            R['city'] = dict(address=' '.join(str(a[k]).strip() for k in ('ADD_NO', 'HALF', 'ST_PRE', 'ST_NM', 'ST_SUFX', 'ST_POST') if a.get(k) and str(a[k]).strip()),
                             use=a.get('USE_'), code=a.get('CODE'), comments=a.get('COMMENTS'), records=a.get('Laserfiche_Hyperlink'))
        # parcels under the footprint
        R['parcels'] = []
        for f in L['parcels']:
            for rg in f['geometry']['rings']:
                if pip(ce, cn, rg) or pip(*cen(rg), rs):
                    a = f['attributes']
                    R['parcels'].append(dict(id=a['parcel_id'], situs=a['situsline1'], use=a['usecode'], lot_sqft=round(a['gis_sq_ft'] or 0), under=round(grid_overlap(rs, rg), 2),
                                             owner=a['ownername'], value_improvements=a['mkimp'], exempt=a['xmptdescr'],
                                             account='https://wa-snohomish.publicaccessnow.com/PropertyInformation/PropertySearch/PropertyAccountSummary.aspx?p=%s&a=%s&m=%s' % (a['parcel_id'], a['revobjid'], a['parcel_id'])))
                    break
        # LiDAR roof heights: roofprints overlapping this footprint, weighted by overlap
        hs = []
        for f in L['roofs']:
            rg = ring(f); a = f['attributes']
            if not a.get('ht_95') or abs(cen(rg)[0] - ce) > 400 or abs(cen(rg)[1] - cn) > 400:
                continue
            mine = grid_overlap(rs, rg)          # share of this footprint under the roofprint
            if mine > 0.5 or grid_overlap(rg, rs) > 0.5:
                hs.append((max(mine, 0.05) * area(rs), a['ht_mean'], a['ht_95'], a['ht_max'], round(area(rg) / max(1, area(rs)), 1)))
        if hs:
            wsum = sum(h[0] for h in hs)
            R['lidar_ft'] = dict(mean=round(sum(h[0] * h[1] for h in hs) / wsum, 1), p95=round(max(h[2] for h in hs), 1), max=round(max(h[3] for h in hs), 1), roofs=len(hs), shared=max(h[4] for h in hs) > 1.6)
            R['lidar_storeys'] = storeys(R['lidar_ft']['mean'], R['lidar_ft']['p95'])
        # 911 address points on the footprint
        R['addresses'] = []
        for f in L['addr911']:
            g = f['geometry']
            if pip(g['x'], g['y'], rs):
                a = f['attributes']
                R['addresses'].append(dict(addr=(a.get('lfull_add') or '').replace(' EVERETT, WA 98201', ''), unit=a.get('unit'), use=a.get('usecode'), landmark=a.get('landmkname')))
        R['addresses'].sort(key=lambda d: d['addr'])
        # registers
        R['historic'] = []
        for k in ('reg_city', 'reg_state'):
            for f in L[k]:
                if any(pip(ce, cn, rg) or pip(*cen(rg), rs) for rg in f['geometry']['rings']):
                    a = f['attributes']
                    R['historic'].append(dict(register=a.get('Elig_Descr') or 'Everett Register', name=a.get('NAME'), address=a.get('ADDRESS'), built=a.get('Const_Year')))
        R['district'] = [f['attributes']['FULL_NAME'] for f in L['district'] if any(pip(ce, cn, rg) for rg in f['geometry']['rings'])]
        R['_rs'] = rs
        recs.append(R)
    print(len(recs), 'buildings')

    # ---- aerials: one big pull per year, cut per building
    pe0, pn0, pe1, pn1 = env['xmin'] - 30, env['ymin'] - 30, env['xmax'] + 30, env['ymax'] + 30
    tiles = {}

    def big(year):
        if year not in tiles:
            # pull in strips no wider than 900 ft so each request stays at native resolution
            n = max(1, math.ceil((pe1 - pe0) / 900)); m = max(1, math.ceil((pn1 - pn0) / 900))
            im = Image.new('RGB', (int((pe1 - pe0) * 4), int((pn1 - pn0) * 4)))
            for a in range(n):
                for b2 in range(m):
                    ea, eb = pe0 + (pe1 - pe0) * a / n, pe0 + (pe1 - pe0) * (a + 1) / n
                    na, nb = pn0 + (pn1 - pn0) * b2 / m, pn0 + (pn1 - pn0) * (b2 + 1) / m
                    t = aerial(year, ea, na, eb, nb, cache, 't%d_%d' % (a, b2))
                    im.paste(t.resize((int((eb - pe0) * 4) - int((ea - pe0) * 4), int((pn1 - na) * 4) - int((pn1 - nb) * 4))), (int((ea - pe0) * 4), int((pn1 - nb) * 4)))
            tiles[year] = im
        return tiles[year]

    P = lambda e, n: ((e - pe0) * 4, (pn1 - n) * 4)
    f12, f16, f22 = font(12), font(16, True), font(22, True)
    for R in recs:
        rs = R['_rs']; es = [p[0] for p in rs]; ns = [p[1] for p in rs]; pad = 45
        box = [int(v) for v in (*P(min(es) - pad, max(ns) + pad), *P(max(es) + pad, min(ns) - pad))]
        for year in AERIAL:
            im = big(year).crop(box)
            if year == '2024':
                # roof colour: median of the pixels inside the footprint, shrunk away from the walls
                ce, cn = cen(rs); px = []
                step = max(1, int(math.sqrt(area(rs)) / 12))
                for yy in range(0, im.size[1], step * 2):
                    for xx in range(0, im.size[0], step * 2):
                        e = min(es) - pad + xx / 4; n2 = max(ns) + pad - yy / 4
                        if pip(ce + (e - ce) * 1.25, cn + (n2 - cn) * 1.25, rs):
                            px.append(im.getpixel((xx, yy)))
                if px:
                    px.sort(key=lambda p: sum(p)); lo, hi = px[len(px) // 5], px[len(px) * 4 // 5]; md = px[len(px) // 2]
                    R['roof_rgb'] = dict(median='#%02x%02x%02x' % md, dark='#%02x%02x%02x' % lo, light='#%02x%02x%02x' % hi)
            k = min(4.0, 900 / max(im.size)); k = max(k, 1.0) if max(im.size) < 900 else k
            big_im = im.resize((int(im.size[0] * k), int(im.size[1] * k)), Image.LANCZOS)
            d = ImageDraw.Draw(big_im)
            pts = [((e - (min(es) - pad)) * 4 * k, ((max(ns) + pad) - n2) * 4 * k) for e, n2 in rs]
            d.line(pts + [pts[0]], fill=(255, 235, 0), width=2)
            d.rectangle([0, 0, big_im.size[0], 24], fill=(0, 0, 0)); d.text((5, 3), '#%d  %s  %s  N up' % (R['i'], year, (R.get('city') or {}).get('address', '')), fill=(255, 255, 255), font=f16)
            big_im.save(os.path.join(out, 'b%d_%s.jpg' % (R['i'], year)), quality=88)
    # overview with indices
    ov = big('2024').copy(); d = ImageDraw.Draw(ov)
    for R in recs:
        pts = [P(*p) for p in R['_rs']]; d.line(pts + [pts[0]], fill=(255, 235, 0), width=5)
        cx, cy = P(*cen(R['_rs'])); t = str(R['i']); d.rectangle([cx - 46, cy - 18, cx + 46, cy + 18], fill=(0, 0, 0)); d.text((cx - 40, cy - 14), t, fill=(255, 235, 0), font=font(28, True))
    k = 3600 / ov.size[0]; ov.resize((3600, int(ov.size[1] * k)), Image.LANCZOS).save(os.path.join(out, 'overview.jpg'), quality=88)

    # ---- outputs
    photos = [] if '--no-photos' in sys.argv else commons(x0, y0, x1, y1, cache)
    json.dump(photos, open(os.path.join(out, 'street_photos.json'), 'w'), indent=1)
    for R in recs:
        R.pop('_rs')
    json.dump(recs, open(os.path.join(out, 'records.json'), 'w'), indent=1)
    os.makedirs(ROOT + '/data/dossier', exist_ok=True)
    slim = []
    for R in recs:
        s = {k: v for k, v in R.items() if k not in ('sp',)}
        s['parcels'] = [{k: v for k, v in p.items() if k in ('id', 'situs', 'use', 'lot_sqft', 'under')} for p in R['parcels']]
        slim.append(s)
    json.dump(dict(source='City of Everett GIS; Snohomish County Assessor and GIS (parcels, roofprints, 911 address points); roof colours sampled from the county 2024 aerial',
                   box=[x0, y0, x1, y1], buildings=slim), open(ROOT + '/data/dossier/%s.json' % name, 'w'), separators=(',', ':'))
    esc = lambda s: str(s).replace('&', '&amp;').replace('<', '&lt;')
    H = ['<!doctype html><meta charset=utf-8><title>Dossier %s</title><style>body{font:13px system-ui;margin:16px;background:#111;color:#ddd}.c{display:grid;grid-template-columns:420px 420px 1fr;gap:10px;border-top:1px solid #444;padding:12px 0}img{max-width:100%%}h2{margin:0 0 6px}td{padding:1px 8px 1px 0;vertical-align:top}i{display:inline-block;width:14px;height:14px;vertical-align:-2px;border:1px solid #777}a{color:#8cf}</style><h1>%s</h1><img src=overview.jpg>' % (name, name)]
    for R in recs:
        row = lambda a, b: '<tr><td>%s<td>%s' % (a, b)
        sw = lambda c: '<i style="background:%s"></i> %s' % (c, c)
        t = [row('game now', '%s %s, roof %s %s, %.1f storeys, shop %s, %.1f m' % (R['game'].get('wall'), sw(R['game'].get('tint')), R['game'].get('roof'), sw(R['game'].get('rtint')), R['game'].get('storeys') or 0, R['game'].get('shop') or 'none', R['game_height_m'])),
             row('footprint', '%d sq ft, %s m (E-W x N-S)' % (R['footprint_sqft'], ' x '.join(map(str, R['dims_m'])))),
             row('faces', '; '.join('%s (%s wall, %s m)' % (f['street'], f['side'], f['m']) for f in R['fronts']) or 'no street wall')]
        if 'lidar_ft' in R:
            t.append(row('LiDAR', 'mean %(mean)s ft, 95th %(p95)s ft, max %(max)s ft' % R['lidar_ft'] + ' &rarr; <b>%s storeys</b>' % R['lidar_storeys'] + (' (roofprint also covers neighbours)' if R['lidar_ft']['shared'] else '')))
        if 'roof_rgb' in R:
            t.append(row('roof colour', ' '.join(sw(R['roof_rgb'][k]) for k in ('dark', 'median', 'light'))))
        if R.get('city'):
            t.append(row('city', esc('%(address)s, use %(use)s %(comments)s' % R['city'])))
        for p in R['parcels']:
            t.append(row('parcel', '<a href="%s">%s</a> %s, %s, lot %s sq ft, covers %d%% of footprint, improvements $%s, %s' % (p['account'], p['id'], esc(p['situs']), esc(p['use']), p['lot_sqft'], p['under'] * 100, p['value_improvements'], esc(p['owner']))))
        for a in R['addresses']:
            t.append(row('address', esc('%s %s: %s %s' % (a['addr'], a['unit'] or '', a['use'], a['landmark'] or ''))))
        for h in R['historic']:
            t.append(row('historic', esc('%(name)s, %(address)s, built %(built)s (%(register)s)' % h)))
        for dn in R['district']:
            t.append(row('district', esc(dn)))
        H.append('<div class=c id=b%d><img src=b%d_2024.jpg><img src=b%d_2022.jpg><div><h2>#%d %s</h2><table>%s</table></div></div>' % (R['i'], R['i'], R['i'], R['i'], esc(', '.join(R['names']) or (R.get('city') or {}).get('address', '')), ''.join(t)))
    H.append('<h2>Street photos nearby (Wikimedia Commons)</h2>' + ''.join('<div><a href="%s">%s</a> %s, %s, %.5f %.5f</div>' % (ph['page'], esc(ph['title']), ph['date'], ph['licence'], ph['lat'] or 0, ph['lon'] or 0) for ph in photos))
    open(os.path.join(out, 'index.html'), 'w').write(''.join(H))
    print('wrote', out)


def storeys(mean, p95):
    """Storeys from LiDAR roof height in feet. Old commercial blocks: ~16 ft ground floor, ~11.5 ft above, ~3 ft parapet."""
    h = max(mean, p95 - 6)
    return 1 if h < 21 else 1 + max(1, round((h - 3 - 16) / 11.5))


if __name__ == '__main__':
    main()
