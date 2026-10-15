"""cn_boot.py <label> <map> - boot only and print the script errors (baseline check)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cnlib as C
G = C.G
rundir = notes = None
try:
    rundir, notes = G.boot("cn_" + sys.argv[1], sys.argv[2], extra=[])
    e = G.errors()
    G.log(sys.argv[1], "errors", len(e), [x[-150:] for x in e[:6]])
finally:
    G.end(rundir, notes)
