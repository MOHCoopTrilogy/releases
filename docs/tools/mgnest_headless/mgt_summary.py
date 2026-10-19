#!/usr/bin/env python
# [bug-2976] Summarise the ^~^~^ MGT lines written by zz_mgtest.scr (mgnest_boot.ps1 rig), per gunner:
# samples, off-gun samples (on=0), max drift, idle-think / thinkstate / anim histograms, first off-gun sample.
# usage: python docs/tools/mgnest_headless/mgt_summary.py <homepath>/maintt/qconsole.log
import re, sys, collections

path = sys.argv[1]
rx = re.compile(r"\^~\^~\^ MGT (\S+) t=([\d.]+) ph=(\d) on=(\d) d=(\d+) tidl=(\S+) tatk=(\S+) ts=(\S+) wg=(\S+) anm=(\S+) foe=(\d) surr=(\d)")
st = collections.OrderedDict()
for line in open(path, "rb"):
    m = rx.search(line.decode("latin-1", "replace"))
    if not m:
        continue
    tn, t, ph, on, d, ti, ta, ts, wg, an, foe, su = m.groups()
    s = st.setdefault(tn, dict(n=0, nB=0, off=0, offB=0, dmax=0, t0=None, t1=None, tidl=collections.Counter(),
                               ts=collections.Counter(), anm=collections.Counter(), wg=collections.Counter(), foe=0, firstOff=None))
    t = float(t)
    s["n"] += 1
    s["t0"] = t if s["t0"] is None else s["t0"]
    s["t1"] = t
    if ph == "1":
        s["nB"] += 1
    if on == "0":
        s["off"] += 1
        if ph == "1":
            s["offB"] += 1
        if s["firstOff"] is None:
            s["firstOff"] = (t, d, ti, an)
    s["dmax"] = max(s["dmax"], int(d))
    s["tidl"][ti] += 1
    s["ts"][ts] += 1
    s["anm"][an] += 1
    s["wg"][wg] += 1
    s["foe"] += int(foe)
for tn, s in st.items():
    print("%-22s samples=%d (phaseB %d, %.0fs..%.0fs)  off-gun=%d (phaseB %d)  maxDrift=%du  foeSamples=%d" % (
        tn, s["n"], s["nB"], s["t0"], s["t1"], s["off"], s["offB"], s["dmax"], s["foe"]))
    print("    tidl=%s  ts=%s  wg=%s  anm=%s  firstOff=%s" % (dict(s["tidl"]), dict(s["ts"]), dict(s["wg"]), dict(s["anm"]), s["firstOff"]))
