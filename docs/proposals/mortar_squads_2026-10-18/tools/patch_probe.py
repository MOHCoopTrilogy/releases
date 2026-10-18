p = r"C:\mohaa-coop-dev\docs\proposals\mortar_squads_2026-10-18\tools\mz_probe.py"
s = open(p, encoding="utf-8").read()
a = s.index('            m = re.search(r"MZ SITETEST')
b = s.index('        errs = G.errors()')
new = '''            m = re.search(r"MZ SITETEST map=\\S+ player=[^\\r\\n]*alliedspots=(\\d+) site=([^\\r\\n]*)", R.read_log()[p0:])
            res = m.group(2).strip() if m else "?"
            na = int(m.group(1)) if m else 0
            log(mp, "placement", k, "-> german site", res, "| allied spots", na)
            if res not in ("none", "?"):
                found += 1
            if na >= 3:
                afound += 1
        log("RESULT", mp, "german sites", found, "of 8; allied-spot placements", afound, "of 8",
            "KEEP-G" if found >= 2 else "drop-G", "KEEP-A" if afound >= 2 else "drop-A")
'''
s = s[:a] + new + s[b:]
open(p, "w", encoding="utf-8").write(s)
print("patched")
