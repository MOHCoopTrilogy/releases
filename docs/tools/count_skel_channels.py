"""Count the worst-case unique skeletor channel names across every game asset.

bug-1803: skeletor_c::m_channelNames is a process-global static that is never reset
between maps, so MAX_SKELETOR_CHANNELS must cover the union of every model a session
could load - not what one playthrough happened to use. This parses the real on-disk
tables (SKAN channel-name arrays, SKMD bone lists) rather than scraping strings, and
deliberately over-approximates (derives BOTH " rot" and " pos" for every bone, ignores
IsBogusChannelName filtering) so a "FITS" result is a genuine upper bound.

RUN THIS AFTER ADDING MODEL PACKS. If the union ever approaches MAX_SKELETOR_CHANNELS
in openmohaa-hzm/code/skeletor/skeletor_name_lists.h, raise the ceiling before shipping
- the failure mode is a hang on the loading screen of an innocent map, late in a long
session, which is extremely expensive to diagnose from the symptom.

Measured 2026-08-14 across main + mainta + maintt: 4,589 unique / 16,384 ceiling (28%).

On the ~2,415 files this reports as unparseable: they are all under newanim/, the
engine's preprocessed animation container (tiki_files.cpp CacheAnimSkel tries
"newanim/<path>" via LoadProcessedAnim before the raw file). They are duplicates of
animations that also ship in raw SKAN form - verified: exactly one,
newanim/models/human/animation/dialogue/generic/g/actor_disguise_04.skc, has no raw
counterpart, bounding what this misses at a single dialogue anim (<=32 channels).
"""
import zipfile, glob, os, struct, collections, json, sys, hashlib

ROOTS = [
    "G:/GOG/Medal of Honor - Allied Assault War Chest/main",
    "G:/GOG/Medal of Honor - Allied Assault War Chest/mainta",
    "G:/GOG/Medal of Honor - Allied Assault War Chest/maintt",
]
CEILING = 16384          # keep in sync with MAX_SKELETOR_CHANNELS
WARN_FRACTION = 0.75     # shout if the assets ever demand this much of the ceiling
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "..", ".wolf", "skel_channel_cache.json")


def fingerprint(pk3s):
    """Cheap identity for the asset set - path, size, mtime. Full scan decompresses
    ~7k members and is far too slow to run unconditionally on every build."""
    h = hashlib.sha1()
    for p in pk3s:
        st = os.stat(p)
        h.update(("%s|%d|%d;" % (os.path.basename(p), st.st_size, int(st.st_mtime))).encode())
    return h.hexdigest()


def cstr(b):
    i = b.find(b"\0")
    return b[: i if i >= 0 else len(b)].decode("ascii", "ignore")


def main():
    quiet = "--check" in sys.argv          # build-mode: one line, cached, never fails the build
    pk3s = []
    for r in ROOTS:
        pk3s += sorted(glob.glob(os.path.join(r, "*.pk3")))

    if quiet:
        fp = fingerprint(pk3s)
        try:
            with open(CACHE) as f:
                c = json.load(f)
            if c.get("fingerprint") == fp:
                report(c["total"], c["chan"], c["bones"], cached=True)
                return 0
        except Exception:
            pass

    chan, bones = set(), set()
    vers = collections.Counter()
    bad = nskc = nskd = 0
    seen = set()

    for p in pk3s:
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for info in z.infolist():
            n = info.filename.lower().replace(os.sep, "/").replace("\\", "/")
            if not (n.endswith(".skc") or n.endswith(".skd")):
                continue
            if n in seen:          # a later pk3 overrides the same path; count once
                continue
            seen.add(n)
            try:
                d = z.read(info)
            except Exception:
                bad += 1
                continue

            if n.endswith(".skc"):
                if len(d) < 48 or d[:4] != b"SKAN":
                    bad += 1
                    continue
                nskc += 1
                vers[("skc", struct.unpack_from("<i", d, 4)[0])] += 1
                numCh, ofsCh = struct.unpack_from("<ii", d, 36)
                if not (0 <= numCh < 100000) or not (0 < ofsCh <= len(d)):
                    bad += 1
                    continue
                for k in range(numCh):
                    o = ofsCh + k * 32
                    if o + 32 > len(d):
                        break
                    s = cstr(d[o:o + 32]).strip()
                    if s:
                        chan.add(s)
            else:
                if len(d) < 100 or d[:4] != b"SKMD":
                    bad += 1
                    continue
                nskd += 1
                vers[("skd", struct.unpack_from("<i", d, 4)[0])] += 1
                # ident4 + version4 + name[64] + numSurfaces4 -> numBones at 76
                numBones, ofsBones = struct.unpack_from("<ii", d, 76)
                if not (0 <= numBones < 100000) or not (0 < ofsBones <= len(d)):
                    bad += 1
                    continue
                o = ofsBones
                for _ in range(numBones):
                    if o + 84 > len(d):
                        break
                    nm = cstr(d[o:o + 32]).strip()
                    if nm:
                        bones.add(nm)
                    # boneFileData_t: name32 parent32 boneType4 ofsBaseData4
                    #                 ofsChannelNames4 ofsBoneNames4 ofsEnd4
                    ofsEnd = struct.unpack_from("<i", d, o + 80)[0]
                    if ofsEnd <= 0 or o + ofsEnd > len(d):
                        break
                    o += ofsEnd
        z.close()

    derived = set()
    for b in bones:
        derived.add(b + " rot")
        derived.add(b + " pos")
    allc = chan | derived

    if quiet:
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with open(CACHE, "w") as f:
                json.dump({"fingerprint": fingerprint(pk3s), "total": len(allc),
                           "chan": len(chan), "bones": len(bones)}, f)
        except Exception:
            pass
        report(len(allc), len(chan), len(bones), cached=False)
        return 0

    print("parsed skc: %d   skd: %d   unparseable: %d" % (nskc, nskd, bad))
    print("versions:", dict(vers))
    print()
    print("unique skc channel names        : %6d" % len(chan))
    print("unique skd bone names           : %6d" % len(bones))
    print("bone names x {rot,pos} derived  : %6d" % len(derived))
    print("-" * 55)
    print("WORST-CASE UNION (all assets)   : %6d" % len(allc))
    if len(allc) < CEILING:
        print("ceiling %d -> FITS, %d spare (%.0f%% used)"
              % (CEILING, CEILING - len(allc), 100.0 * len(allc) / CEILING))
    else:
        print("ceiling %d -> DOES NOT FIT, short by %d" % (CEILING, len(allc) - CEILING))
    return 0


def report(total, chan, bones, cached):
    tag = " (cached)" if cached else ""
    pct = 100.0 * total / CEILING
    print("skeletor channels: %d worst-case / %d ceiling (%.0f%%)%s"
          % (total, CEILING, pct, tag))
    if total >= CEILING * WARN_FRACTION:
        print("  WARNING: asset growth is approaching MAX_SKELETOR_CHANNELS. Raise it in")
        print("  openmohaa-hzm/code/skeletor/skeletor_name_lists.h BEFORE shipping - overflow")
        print("  strands players on a loading screen late in a session (bug-1803).")


if __name__ == "__main__":
    sys.exit(main())
