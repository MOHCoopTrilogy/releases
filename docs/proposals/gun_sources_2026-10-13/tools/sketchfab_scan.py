"""List Sketchfab models marked downloadable for each of our gun families, from the public search API.

METADATA ONLY: no model or texture is downloaded, no account, no token. One GET per query against
https://api.sketchfab.com/v3/search (the same listing the site's search page shows). Keeps CC0 and
CC Attribution rows (the two licences a free mod can redistribute under), counts the rest.
The licence is the value the UPLOADER picked in Sketchfab's dropdown - it is not proof of authorship.
Writes ../sketchfab_scan.tsv.

    python sketchfab_scan.py            # all guns
    python sketchfab_scan.py "sten mk2" # one query
"""
import sys, os, json, time, urllib.request, urllib.parse

GUNS = {
    "M1 Garand": ["m1 garand"], "M1 Carbine": ["m1 carbine"], "Thompson": ["thompson m1a1", "thompson m1928"],
    "BAR": ["m1918 bar", "browning automatic rifle"], "M1911": ["colt m1911", "m1911a1"],
    "M1919": ["m1919 browning", "browning m1919a4"], "M3 Grease Gun": ["m3 grease gun"],
    "Springfield 1903": ["springfield 1903", "m1903"], "Trench shotgun": ["winchester 1897", "m1897 trench", "ithaca 37"],
    "Johnson M1941": ["johnson m1941"], "Bazooka": ["m1 bazooka", "m9 bazooka"],
    "Kar98k": ["kar98k", "karabiner 98k"], "MP40": ["mp40", "mp 40"], "StG 44": ["stg44", "sturmgewehr 44"],
    "G43": ["gewehr 43", "g43"], "FG 42": ["fg42", "fg 42"], "MG42": ["mg42", "mg 42"], "P38": ["walther p38"],
    "Luger": ["luger p08"], "C96": ["mauser c96"], "MP18": ["mp18", "mp 18"], "PPK": ["walther ppk"],
    "Panzerschreck": ["panzerschreck"], "Lee-Enfield": ["lee enfield", "smle"], "Sten": ["sten mk2", "sten gun"],
    "Webley": ["webley revolver"], "De Lisle": ["de lisle carbine"], "Vickers-Berthier / Bren": ["vickers berthier", "bren gun"],
    "Welrod": ["welrod"], "PIAT": ["piat"], "Lewis": ["lewis gun"],
    "Mosin-Nagant": ["mosin nagant"], "SVT-40": ["svt-40", "svt 40"], "PPSh-41": ["ppsh-41", "ppsh 41"],
    "PPS-43": ["pps-43", "pps 43"], "DP-28": ["dp-28", "dp28"], "TT-33": ["tt-33 tokarev", "tokarev tt"],
    "Nagant revolver": ["nagant m1895", "nagant revolver"], "Carcano": ["carcano"], "Beretta M38": ["beretta m38", "beretta mab 38"],
    "Beretta M1934": ["beretta m1934"], "Breda 30": ["breda 30"], "Arisaka": ["arisaka"], "Type 100": ["type 100 smg"],
    "Nambu": ["nambu type 14"], "Hi-Standard": ["high standard hdm"], "S&W M10": ["smith wesson model 10", "s&w victory"],
}
RED = ["call of duty", " cod ", "cod:", "codm", "warzone", "vanguard", "battlefield", "bf1", "bfv", "bf5", "pubg", "free fire",
       "freefire", "day of infamy", "red orchestra", "rising storm", "insurgency", "hell let loose", "enlisted", "roblox",
       "fortnite", "cs:go", "csgo", "counter-strike", "ripped", "rip from", "extracted", "ported", "port from", "from the game",
       "game rip", "sniper elite", "world at war", "waw", "medal of honor", "wolfenstein", "valorant", "apex", "tarkov", "payday",
       "far cry", "crossfire", "standoff", "garena", "world of guns", "h3vr", "arma", "squad", "heroes and generals", "heroes & generals"]
KEEP = {"CC0 Public Domain": "CC0", "CC Attribution": "CC-BY"}


def search(q, n=24):
    url = "https://api.sketchfab.com/v3/search?" + urllib.parse.urlencode(
        dict(type="models", q=q, downloadable="true", count=n, sort_by="-likeCount"))
    req = urllib.request.Request(url, headers={"User-Agent": "hzm-coop-research/1 (metadata listing only)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("results", [])


def main():
    guns = GUNS if len(sys.argv) < 2 else {sys.argv[1]: [sys.argv[1]]}
    rows = ["gun\tlicence\tname\tauthor\ttris\ttex_max_px\ttex_count\tanims\tlikes\tviews\tpublished\tflags\turl\tdesc"]
    seen = set()
    for gun, qs in guns.items():
        other = {}
        kept = 0
        for q in qs:
            try:
                res = search(q)
            except Exception as e:  # noqa: BLE001
                rows.append("%s\tERROR %s" % (gun, e))
                continue
            time.sleep(0.6)
            toks = [t for t in q.replace("-", " ").lower().split() if len(t) > 1]
            for r in res:
                if r["uid"] in seen:
                    continue
                lic = (r.get("license") or {}).get("label", "?")
                text = " ".join([r.get("name") or "", r.get("description") or "",
                                 " ".join(t.get("name", "") for t in (r.get("tags") or []))]).lower()
                name = (r.get("name") or "").lower().replace("-", " ").replace(".", " ")
                # relevance: every query token must be in the name or the tags
                if not all(t in name or t in text[:400] for t in toks):
                    continue
                seen.add(r["uid"])
                if lic not in KEEP:
                    other[lic] = other.get(lic, 0) + 1
                    continue
                arch = (r.get("archives") or {}).get("gltf") or {}
                flags = [w.strip() for w in RED if w in " " + text + " "]
                desc = " ".join((r.get("description") or "").split())[:160]
                rows.append("\t".join(str(x) for x in [
                    gun, KEEP[lic], (r.get("name") or "").strip()[:50], r["user"]["username"], r.get("faceCount"),
                    arch.get("textureMaxResolution"), arch.get("textureCount"), r.get("animationCount"),
                    r.get("likeCount"), r.get("viewCount"), (r.get("publishedAt") or "")[:10],
                    ",".join(flags) or "-", "https://sketchfab.com/3d-models/" + r["uid"], desc]))
                kept += 1
        rows.append("%s\t(other licences, not kept)\t%s" % (gun, json.dumps(other)))
    out = "\n".join(rows) + "\n"
    if len(sys.argv) < 2:
        open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sketchfab_scan.tsv"), "w",
             encoding="utf-8", newline="\n").write(out)
    sys.stdout.buffer.write(out.encode("utf-8", "replace"))


if __name__ == "__main__":
    main()
