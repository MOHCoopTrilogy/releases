#!/usr/bin/env python
"""glsl_glslang.py - run Khronos glslang on every source glsl_variant_lint.py --emit rebuilt, and LINK the pairs.

WHY. glsl_variant_lint.py is a structural lint (declarations, versions, uniforms, varyings); it does not type-check
expressions. glslang is the reference front end, so a program it rejects will very likely fail on a driver too, and
every gl2 GLSL failure is ri.Error(ERR_FATAL) at start-up. Promoted 2026-09-27 from a session-scoped scratchpad copy
(scratchpad/gfx/run_glslang.py), per docs/proposals/postfx_ports_2026-09-27 plan Q0.2.

    python docs/tools/glsl_variant_lint.py --post --emit OUT     # rebuild every variant (+ OUT/pairs.json)
    python docs/tools/glsl_glslang.py OUT                        # compile all, link every vp+fp pair
    python docs/tools/glsl_glslang.py OUT --only "dof|bloom"     # regex filter on file names / pair labels

Exit code 0 only if every compile and every link passes (T14c: gate on the tool's own code, never a pipe).
pairs.json is written by --post only; without it, compile-only (the old behaviour).
Known failures: pass --allow REGEX (applied to "<file or label>: <first error>") to report without failing - e.g.
fsr_easu without GL_ARB_gpu_shader5 support in the validator. Keep that list short and named.
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

GLSLANG = r"C:\mohaa-coop-dev\_tools\glslang\bin\glslang.exe"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("emit_dir")
    ap.add_argument("--only", default=None)
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--jobs", type=int, default=12)
    a = ap.parse_args()
    if not os.path.exists(GLSLANG):
        print("glslang not found at %s" % GLSLANG)
        sys.exit(2)
    only = re.compile(a.only) if a.only else None
    allow = [re.compile(x) for x in a.allow]
    files = sorted(f for f in os.listdir(a.emit_dir) if f.endswith((".vert", ".frag")))
    if only:
        files = [f for f in files if only.search(f)]
    pairs = []
    pj = os.path.join(a.emit_dir, "pairs.json")
    if os.path.exists(pj):
        seen = set()
        for p in json.load(open(pj)):
            k = (p["vert"], p["frag"])
            if k in seen or (only and not only.search(p["label"]) and not only.search(p["frag"])):
                continue
            seen.add(k)
            pairs.append(p)

    def run(args):
        r = subprocess.run([GLSLANG] + args, capture_output=True, text=True)
        out = r.stdout + r.stderr
        errs = [l.strip() for l in out.splitlines() if "ERROR" in l and "compilation terminated" not in l]
        return r.returncode, errs

    jobs = [("compile", f, [os.path.join(a.emit_dir, f)]) for f in files]
    jobs += [("link", "%s v%d" % (p["label"], p["version"]),
              ["-l", os.path.join(a.emit_dir, p["vert"]), os.path.join(a.emit_dir, p["frag"])]) for p in pairs
             if os.path.exists(os.path.join(a.emit_dir, p["vert"])) and os.path.exists(os.path.join(a.emit_dir, p["frag"]))]
    tally = collections.defaultdict(lambda: [0, 0, 0])   # pass, fail, allowed
    fails = []
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for (kind, name, args), (rc, errs) in zip(jobs, ex.map(lambda j: run(j[2]), jobs)):
            m = re.match(r"(\w+?)_(vp|fp)_v(\d+)_", name)
            key = ("%s %s_%s v%s" % (kind, m.group(1), m.group(2), m.group(3))) if m else \
                  ("%s %s" % (kind, re.sub(r"\[.*?\]", "", name)))
            if rc == 0:
                tally[key][0] += 1
                continue
            line = "%s: %s" % (name, errs[0] if errs else "exit %d" % rc)
            if any(x.search(line) for x in allow):
                tally[key][2] += 1
            else:
                tally[key][1] += 1
                fails.append((kind, line, errs[:3]))
    for k in sorted(tally):
        p, f, al = tally[k]
        if f or al:
            print("%-40s pass=%4d FAIL=%4d allowed=%d" % (k, p, f, al))
    tp = sum(v[0] for v in tally.values())
    tf = sum(v[1] for v in tally.values())
    ta = sum(v[2] for v in tally.values())
    print("glslang: %d compiles + %d links; pass=%d fail=%d allowed=%d" % (len(files), len(jobs) - len(files), tp, tf, ta))
    for kind, line, errs in fails[:40]:
        print("FAIL", kind, line)
    sys.exit(1 if tf else 0)


if __name__ == "__main__":
    main()
