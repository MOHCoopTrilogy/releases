"""Per-gun ADS tune sweep.

The existing ads_audit.py proves every weapon RESOLVES to a tune row. It says nothing about whether
the values in that row are right. This looks for rows that do not behave like their peers - the
shape a mis-dial, a typo or a never-actually-tuned entry takes.
"""
import re, io, statistics, collections

SRC = 'C:/mohaa-coop-dev/openmohaa-hzm/code/cgame/cg_modelanim.c'
s = io.open(SRC, encoding='utf-8', errors='replace').read()

# ---- the tuned rows ----------------------------------------------------------------------------
m = re.search(r's_adsGunTune\[\]\s*=\s*\{(.*?)\n\};', s, re.S)
body = m.group(1)
rows = []
for line in body.split('\n'):
    r = re.match(r'\s*\{\s*"([^"]+)"\s*,(.*?)\}\s*,?\s*(?://.*)?$', line)
    if not r:
        continue
    nums = [float(x) for x in re.findall(r'-?\d+\.?\d*f?', r.group(2).replace('f', ''))]
    if len(nums) != 10:
        continue
    rows.append((r.group(1), nums))

# ---- the donor aliases -------------------------------------------------------------------------
d = re.search(r's_adsDonor\[\]\[2\]\s*=\s*\{(.*?)\n\};', s, re.S)
donors = re.findall(r'\{\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\}', d.group(1)) if d else []

FIELDS = ['sPitch', 'sYaw', 'sRoll', 'sShiftX', 'sShiftY',
          'cPitch', 'cYaw', 'cRoll', 'cShiftX', 'cShiftY']

print('=' * 92)
print('ADS TUNE SWEEP - %d tuned rows, %d donor aliases' % (len(rows), len(donors)))
print('=' * 92)

# ---- distribution per field --------------------------------------------------------------------
cols = {f: [r[1][i] for r in rows] for i, f in enumerate(FIELDS)}
print('\nfield        median      min       max     stdev')
for f in FIELDS:
    v = cols[f]
    print('%-9s %9.3f %9.3f %9.3f %9.3f'
          % (f, statistics.median(v), min(v), max(v), statistics.pstdev(v)))

# ---- 1. never-tuned rows -----------------------------------------------------------------------
print('\n' + '-' * 92)
print('[1] ROWS THAT LOOK UNTUNED (all-zero standing pose = the sights were never dialled)')
print('-' * 92)
n = 0
for name, v in rows:
    if abs(v[0]) < 0.01 and abs(v[1]) < 0.01 and abs(v[2]) < 0.01 \
       and abs(v[3]) < 0.001 and abs(v[4]) < 0.001:
        print('   %-28s standing pose is entirely zero' % name)
        n += 1
if not n:
    print('   none - every row has a real standing correction')

# ---- 2. statistical outliers -------------------------------------------------------------------
print('\n' + '-' * 92)
print('[2] OUTLIERS (>3 sigma from the field median) - a typo or a genuinely odd gun')
print('-' * 92)
n = 0
for i, f in enumerate(FIELDS):
    med = statistics.median(cols[f])
    sd = statistics.pstdev(cols[f])
    if sd < 1e-6:
        continue
    for name, v in rows:
        if abs(v[i] - med) > 3.0 * sd:
            print('   %-28s %-8s = %8.3f   (median %7.3f, %.1f sigma)'
                  % (name, f, v[i], med, abs(v[i] - med) / sd))
            n += 1
if not n:
    print('   none')

# ---- 3. sign disagreement with the population --------------------------------------------------
print('\n' + '-' * 92)
print('[3] SIGN DISAGREEMENT - a correction pointing the opposite way to every peer')
print('-' * 92)
n = 0
for i, f in enumerate(FIELDS):
    v = cols[f]
    pos = sum(1 for x in v if x > 0.01)
    neg = sum(1 for x in v if x < -0.01)
    if pos + neg < 8:
        continue
    if pos and neg and min(pos, neg) <= 2:
        odd = [nm for nm, vv in rows
               if (vv[i] > 0.01) == (pos < neg) and abs(vv[i]) > 0.01]
        for nm in odd:
            val = dict(rows)[nm][i]
            print('   %-28s %-8s = %8.3f   (%d of %d peers use the other sign)'
                  % (nm, f, val, max(pos, neg), pos + neg))
            n += 1
if not n:
    print('   none')

# ---- 4. crouch corrections that are implausibly large ------------------------------------------
print('\n' + '-' * 92)
print('[4] LARGEST CROUCH CORRECTIONS - these now BLEND (they used to snap), so verify by eye')
print('-' * 92)
byc = sorted(rows, key=lambda r: -abs(r[1][6]))
for name, v in byc[:8]:
    print('   %-28s cYaw %7.2f  cPitch %6.2f  cRoll %6.2f  cShiftX %7.3f'
          % (name, v[6], v[5], v[7], v[8]))

# ---- 5. donor sanity ---------------------------------------------------------------------------
print('\n' + '-' * 92)
print('[5] DONOR ALIASES - a gun inheriting another gun\'s dialled values')
print('-' * 92)
tuned = set(nm for nm, _ in rows)
for a, b in donors:
    ok = 'OK' if b in tuned else '*** TARGET NOT IN TABLE ***'
    print('   %-28s -> %-24s %s' % (a, b, ok))

print('\n' + '=' * 92)
