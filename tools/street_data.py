"""Real street measurements for tools/streets.py, from the City of Everett's kerb lines (Streets/Transportation layer 5:
CC = concrete kerb, EP = edge of pavement).

  python3 tools/street_data.py          writes data/dossier/streets.json

For every junction-to-junction run of the network it casts rays left and right from points along the centreline and
takes the median distance to the first kerb line on each side: the real kerb-to-kerb width and how far the real
street sits off the network's centreline. Kerb loops that sit in the middle of a street are median islands and are
kept as polygons. Raw downloads are cached in dossier/_streets (not committed)."""
import json, math, os, sys, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dossier as D
import streets

ROOT = D.ROOT
CACHE = ROOT + '/dossier/_streets'


def main():
    W = json.load(open(ROOT + '/data/world.json'))
    WW, WH = W['wm'] * 10, W['hm'] * 10
    cs = [D.w2sp(x, y) for x, y in ((0, 0), (WW, 0), (WW, WH), (0, WH))]
    env = dict(xmin=min(p[0] for p in cs), xmax=max(p[0] for p in cs), ymin=min(p[1] for p in cs), ymax=max(p[1] for p in cs))
    D.LAYERS['kerb'] = D.CITY + 'Streets/Transportation/MapServer/5'
    os.makedirs(CACHE, exist_ok=True)
    K = [f for f in D.layer('kerb', env, CACHE) if f['attributes'].get('CODE') in ('CC', 'EP')]
    paths = [[D.sp2w(*q[:2]) for q in p] for f in K for p in f['geometry']['paths']]
    G = {}
    segs = []
    for pi, p in enumerate(paths):
        for k in range(len(p) - 1):
            a, b = p[k], p[k + 1]
            si = len(segs); segs.append((a, b, pi))
            for gx in range(int(min(a[0], b[0]) // 200), int(max(a[0], b[0]) // 200) + 1):
                for gy in range(int(min(a[1], b[1]) // 200), int(max(a[1], b[1]) // 200) + 1):
                    G.setdefault((gx, gy), []).append(si)

    def ray(o, d, far):
        """distances along d from o to every kerb segment hit within far"""
        hits = []
        seen = set()
        for s in range(0, int(far) + 200, 150):
            key = (int((o[0] + d[0] * min(s, far)) // 200), int((o[1] + d[1] * min(s, far)) // 200))
            for si in G.get(key, ()):
                if si in seen:
                    continue
                seen.add(si)
                a, b, pi = segs[si]
                ex, ey = b[0] - a[0], b[1] - a[1]
                den = d[0] * ey - d[1] * ex
                if abs(den) < 1e-9:
                    continue
                t = ((a[0] - o[0]) * ey - (a[1] - o[1]) * ex) / den
                u = ((a[0] - o[0]) * d[1] - (a[1] - o[1]) * d[0]) / den
                if 0 < t < far and 0 <= u <= 1:
                    hits.append((t, pi))
        return sorted(hits)

    CH, _ = streets.chains(W, lambda x, y: False)
    out = {}
    med_paths = {}
    for ch in CH:
        L = ch['L']
        if L < 260:
            continue
        dl, dr = [], []
        t = 130.0
        while t < L - 130:
            o = streets.pt(ch, t, 0); d = streets.dirat(ch, t)
            for sgn, acc in ((1, dr), (-1, dl)):
                n = (-d[1] * sgn, d[0] * sgn)
                h = ray(o, n, 230)
                for dist, pi in h:
                    if dist < 26:            # a kerb this close to the centreline is a median island
                        med_paths.setdefault(pi, []).append(ch['ids'][0])
                        continue
                    acc.append(dist); break
            t += 60
        if len(dl) >= 3 and len(dr) >= 3:
            a, b = statistics.median(dl), statistics.median(dr)
            sp = (statistics.pstdev(dl) + statistics.pstdev(dr)) / 2
            if 55 <= a + b <= 320 and sp < 30 and abs(b - a) < 70:
                out['%d-%d' % (ch['ids'][0], ch['ids'][-1])] = [round(a + b, 1), round((b - a) / 2, 1)]
                for ei in ch['eids']:
                    W['edges'][ei][2] = round((a + b) / 10, 1)        # the game and the street builder both read the width from here
    # median islands: kerb paths that were met from the centreline at least twice, closed into polygons
    med = []
    for pi, hits in med_paths.items():
        p = paths[pi]
        if len(hits) >= 2 and len(p) >= 4:
            xs = [q[0] for q in p]; ys = [q[1] for q in p]
            if max(max(xs) - min(xs), max(ys) - min(ys)) > 40 and min(max(xs) - min(xs), max(ys) - min(ys)) < 120:
                med.append([[round(q[0], 1), round(q[1], 1)] for q in p])
    json.dump(dict(source='City of Everett kerb lines (Streets/Transportation layer 5, CC and EP); widths are medians of rays cast from the street centreline',
                   widths=out, medians=med), open(ROOT + '/data/dossier/streets.json', 'w'), separators=(',', ':'))
    json.dump(W, open(ROOT + '/data/world.json', 'w'), separators=(',', ':'))
    nm = W['names']
    by = {}
    for ch in CH:
        k = '%d-%d' % (ch['ids'][0], ch['ids'][-1])
        if k in out:
            by.setdefault(nm[ch['nm']], []).append((out[k][0], {8: 100, 6: 120, 5: 140, 4: 170}.get(ch['cls'], ch['w'])))
    print('runs', len(CH), 'measured', len(out), 'median islands', len(med))
    for s in ('Hewitt Ave', 'Colby Ave', 'Wetmore Ave', 'Rockefeller Ave', 'Oakes Ave', 'Broadway', 'Rucker Ave', 'Pacific Ave', 'Everett Ave', 'Grand Ave', 'Lombard Ave', '23rd St'):
        v = by.get(s, [])
        if v:
            print(' ', s, 'real m:', round(statistics.median(x[0] for x in v) / 10, 1), 'was', statistics.median(x[1] for x in v) / 10, 'n', len(v))
    allw = [v[0] for v in out.values()]
    print('all real widths m: median', round(statistics.median(allw) / 10, 1), 'p10', round(sorted(allw)[len(allw) // 10] / 10, 1), 'p90', round(sorted(allw)[len(allw) * 9 // 10] / 10, 1))


if __name__ == '__main__':
    main()
