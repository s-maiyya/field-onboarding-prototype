"""Build regions.json for the prototype: a coarse district lookup grid + recent crop areas per district.
Inputs (in DATA dir): apy.csv (DES APY via India Data Portal, ODC-By), adm2.geojson / adm1.geojson (geoBoundaries IND, ODbL).
"""
import csv, json, sys, re, unicodedata, difflib, collections, math

DATA = sys.argv[1]
OUT = sys.argv[2]
RES = 0.03
LAT0, LAT1, LNG0, LNG1 = 6.0, 37.2, 68.0, 97.5
YEARS = ('2020-2021', '2021-2022', '2022-2023')

# app key, display name, kind (day|month|age)
CROPMAP = {
 'Rice': 'paddy', 'Wheat': 'wheat', 'Cotton(Lint)': 'cotton', 'Soyabean': 'soybean', 'Gram': 'chickpea', 'Maize': 'maize',
 'Rapeseed &Mustard': 'mustard', 'Bajra': 'bajra', 'Sugarcane': 'sugarcane', 'Groundnut': 'groundnut', 'Moong(Green Gram)': 'green gram',
 'Arhar/Tur': 'tur', 'Urad': 'black gram', 'Jowar': 'jowar', 'Guar Seed': 'guar', 'Coconut': 'coconut', 'Sesamum': 'sesame',
 'Potato': 'potato', 'Masoor': 'lentil', 'Ragi': 'ragi', 'Moth': 'moth bean', 'Castor Seed': 'castor', 'Arecanut': 'arecanut',
 'Arcanut (Processed)': 'arecanut', 'Peas & Beans (Pulses)': 'peas', 'Jute': 'jute', 'Barley': 'barley', 'Dry Chillies': 'chilli',
 'Onion': 'onion', 'Tobacco': 'tobacco', 'Horse-Gram': 'horse gram', 'Small Millets': 'small millets', 'Khesari': 'khesari',
 'Black Pepper': 'black pepper', 'Sunflower': 'sunflower', 'Banana': 'banana', 'Cashewnut': 'cashew', 'Linseed': 'linseed',
 'Tapioca': 'tapioca', 'Garlic': 'garlic', 'Cowpea(Lobia)': 'cowpea', 'Coriander': 'coriander', 'Turmeric': 'turmeric',
 'Ginger': 'ginger', 'Dry Ginger': 'ginger', 'Safflower': 'safflower', 'Niger Seed': 'niger', 'Cardamom': 'cardamom',
 'Sweet Potato': 'sweet potato', 'Mesta': 'mesta', 'Sannhamp': 'sunn hemp',
}
SEASONS = {'Kharif': 0, 'Autumn': 1, 'Winter': 2, 'Rabi': 3, 'Summer': 4, 'Whole Year': 5}

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = s.replace('&', 'and')
    s = re.sub(r'\b(district|dist)\b', '', s)
    return re.sub(r'[^a-z]', '', s)

# ---------- crops per APY district ----------
# area[(state,dcode)][crop][season] = list of yearly areas ; same crop from 2 source names -> max per year
raw = collections.defaultdict(lambda: collections.defaultdict(float))
names = {}
for r in csv.DictReader(open(DATA + '/apy.csv', encoding='utf-8', errors='replace')):
    if r['year'] not in YEARS or r['season'] not in SEASONS: continue
    k = CROPMAP.get(r['crop_name'])
    if not k: continue
    try: a = float(r['area'] or 0)
    except ValueError: continue
    if a <= 0: continue
    d = (r['state_name'], r['district_code'])
    names[d] = r['district_name']
    key = (d, k, SEASONS[r['season']], r['year'], r['crop_name'])
    raw[key[:4]][r['crop_name']] = max(raw[key[:4]][r['crop_name']], a)
dist = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0] * 6))
years_seen = collections.defaultdict(set)
for (d, k, s, y), by_src in raw.items():
    dist[d][k][s] += max(by_src.values())
    years_seen[d].add(y)
apy = {}
for d, crops in dist.items():
    ny = len(years_seen[d])
    rows = sorted(([k] + [round(v / ny) for v in a] for k, a in crops.items()), key=lambda x: -sum(x[1:]))
    apy[d] = [x for x in rows if sum(x[1:]) >= 50][:20]  # >=50 ha average, top 20
print('APY districts with data:', len(apy))

# ---------- geometry ----------
def rings_of(geom):
    if geom['type'] == 'Polygon': return geom['coordinates']
    return [r for poly in geom['coordinates'] for r in poly]

adm2 = json.load(open(DATA + '/adm2.geojson'))['features']
adm1 = json.load(open(DATA + '/adm1.geojson'))['features']
NR, NC = int(math.ceil((LAT1 - LAT0) / RES)), int(math.ceil((LNG1 - LNG0) / RES))
grid = [[-1] * NC for _ in range(NR)]
sample = {}
cells = collections.defaultdict(list)
for idx, f in enumerate(adm2):
    rings = rings_of(f['geometry'])
    lats = [p[1] for r in rings for p in r]
    r0, r1 = max(0, int((min(lats) - LAT0) / RES)), min(NR - 1, int((max(lats) - LAT0) / RES))
    for row in range(r0, r1 + 1):
        y = LAT0 + (row + 0.5) * RES
        xs = []
        for ring in rings:
            for i in range(len(ring) - 1):
                (x1, y1), (x2, y2) = ring[i][:2], ring[i + 1][:2]
                if (y1 > y) != (y2 > y):
                    xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for j in range(0, len(xs) - 1, 2):
            c0 = int(math.ceil((xs[j] - LNG0) / RES - 0.5)); c1 = int(math.floor((xs[j + 1] - LNG0) / RES - 0.5))
            for c in range(max(0, c0), min(NC - 1, c1) + 1):
                grid[row][c] = idx
                cells[idx].append((y, LNG0 + (c + 0.5) * RES))
                if idx not in sample: sample[idx] = (y, LNG0 + (c + 0.5) * RES)
    if idx not in sample:  # tiny district: use first vertex
        p = rings[0][0]; sample[idx] = (p[1], p[0])
        row, c = int((p[1] - LAT0) / RES), int((p[0] - LNG0) / RES)
        if 0 <= row < NR and 0 <= c < NC: grid[row][c] = idx

def inside(lat, lng, geom):
    n = False
    for ring in rings_of(geom):
        for i in range(len(ring) - 1):
            (x1, y1), (x2, y2) = ring[i][:2], ring[i + 1][:2]
            if (y1 > lat) != (y2 > lat) and lng < x1 + (lat - y1) * (x2 - x1) / (y2 - y1): n = not n
    return n
st_bbox = []
for f in adm1:
    pts = [p for r in rings_of(f['geometry']) for p in r]
    st_bbox.append((min(p[1] for p in pts), max(p[1] for p in pts), min(p[0] for p in pts), max(p[0] for p in pts)))
def state_of(lat, lng):
    for f, (a, b, c, d) in zip(adm1, st_bbox):
        if a <= lat <= b and c <= lng <= d and inside(lat, lng, f['geometry']): return f['properties']['shapeName']
    return None

# ---------- match geoBoundaries districts to APY districts (same state, name) ----------
RENAME = {'Gurgaon': 'Gurugram', 'Mewat': 'Nuh', 'Allahabad': 'Prayagraj', 'Mysore': 'Mysuru', 'Bangalore': 'Bengaluru Urban',
  'Bangalore Rural': 'Bengaluru Rural', 'Belgaum': 'Belagavi', 'Bellary': 'Ballari', 'Bijapur': 'Vijayapura', 'Gulbarga': 'Kalaburagi',
  'Ahmadnagar': 'Ahilyanagar', 'Bid': 'Beed', 'Hoshangabad': 'Narmadapuram', 'Garhwal': 'Pauri Garhwal', 'Hardwar': 'Haridwar',
  'Kadapa(YSR)': 'Y.S.R. Kadapa', 'Dohad': 'Dahod', 'Batod': 'Botad', 'Jalor': 'Jalore',
  'Baleshwar': 'Balasore', 'Subarnapur': 'Sonepur', 'Koch Bihar': 'Cooch Behar', 'Hugli': 'Hooghly', 'Haora': 'Howrah',
  'Darjiling': 'Darjeeling', 'Barddhaman': 'Purba Bardhaman', 'Muktsar': 'Sri Muktsar Sahib', 'Kanshiram Nagar': 'Kasganj',
  'Mahamaya Nagar': 'Hathras', 'Jyotiba Phule Nagar': 'Amroha', 'Sant Ravidas Nagar (Bhadohi)': 'Bhadohi',
  'Pashchimi Singhbhum': 'West Singhbhum', 'Purbi Singhbhum': 'East Singhbhum', 'Uttar Bastar Kanker': 'Kanker',
  'Baloda Bazar': 'Balodabazar-Bhatapara', 'Koriya': 'Korea', 'Bhadradri': 'Bhadradri Kothagudem', 'Komaram Bheem': 'Kumuram Bheem Asifabad',
  'Jayashankar': 'Jayashankar Bhupalapally', 'Medchal': 'Medchal Malkajgiri', 'Jogulamba': 'Jogulamba Gadwal', 'Hydrabad': 'Hyderabad',
  'Kamrup Metropolitan': 'Kamrup Metro', 'Osmanabad': 'Dharashiv', 'Aurangabad': 'Chhatrapati Sambhajinagar', 'Raigarh': 'Raigad',
  'Punch': 'Poonch', 'The Dangs': 'Dang', 'South Twenty Four Parganas': 'South 24 Parganas', 'North Twenty Four Parganas': 'North 24 Parganas',
  'Karimganj': 'Sribhumi', 'Ramanagara': 'Bengaluru South', 'North District': 'Mangan', 'South District': 'Namchi', 'West District': 'Gyalshing', 'East District': 'Gangtok'}
ALIAS = {'dadraandnagarhavelianddamananddiu': 'dadraandnagarhaveli'}
by_state = collections.defaultdict(dict)
for (st, dc), nm in names.items():
    if (st, dc) in apy: by_state[norm(st)][norm(nm)] = (st, dc)
out_d, matched, unmatched = [], 0, []
for idx, f in enumerate(adm2):
    nm = f['properties']['shapeName']
    cs = cells[idx] or [sample[idx]]; step = max(1, len(cs) // 9)
    votes = collections.Counter(state_of(*pt) for pt in cs[::step]); votes.pop(None, None)
    st = votes.most_common(1)[0][0] if votes else None
    cand = by_state.get(ALIAS.get(norm(st or ''), norm(st or '')), {})
    g = norm(RENAME.get(nm, nm))
    key = cand.get(g)
    if not key:
        m = difflib.get_close_matches(g, list(cand), n=1, cutoff=0.8)
        key = cand[m[0]] if m else None
    if not key:  # containment, e.g. "kamrupmetropolitan" vs "kamrupmetro"
        hits = [v for k2, v in cand.items() if len(g) >= 4 and len(k2) >= 4 and (g in k2 or k2 in g)]
        key = hits[0] if len(hits) == 1 else None
    if not key:  # state lookup failed near a border: unique name anywhere
        hits = [v for stn in by_state.values() for k2, v in stn.items() if k2 == g]
        key = hits[0] if len(hits) == 1 else None
    if key: matched += 1; out_d.append([nm, st, apy[key]])
    else: unmatched.append('%s (%s)' % (nm, st)); out_d.append([nm, st, []])
print('geo districts', len(adm2), 'matched', matched, 'unmatched', len(unmatched))
print('unmatched:', ', '.join(unmatched))

# ---------- RLE rows, base36 ----------
def b36(n):
    s = ''
    while True:
        n, r = divmod(n, 36); s = '0123456789abcdefghijklmnopqrstuvwxyz'[r] + s
        if n == 0: return s
rows = []
for row in grid:
    runs, prev, cnt = [], row[0], 0
    for v in row + [None]:
        if v == prev: cnt += 1; continue
        runs.append(b36(cnt) + '.' + ('' if prev == -1 else b36(prev))); prev, cnt = v, 1
    rows.append(','.join(runs))
doc = {'src': 'Crop area: DES Area-Production-Yield 2020-21..2022-23 via India Data Portal (ODC-By). Districts: geoBoundaries IND ADM2 (ODbL).',
       'season_order': ['kharif', 'autumn', 'winter', 'rabi', 'summer', 'whole_year'],
       'res': RES, 'lat0': LAT0, 'lng0': LNG0, 'rows': rows, 'd': out_d}
s = json.dumps(doc, separators=(',', ':'))
open(OUT, 'w').write(s)
print('wrote', OUT, len(s) // 1024, 'KB')
