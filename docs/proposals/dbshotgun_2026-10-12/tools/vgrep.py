"""look inside the shipped pak set (read-only):
    python tools/vgrep.py name <substring>              list pak files whose path contains it (engine order, last wins)
    python tools/vgrep.py cat <vpath> [regex]           print the winning copy (lines matching regex, with numbers)
"""
import os, sys, re, importlib.util
import dbslib as L

sp = importlib.util.spec_from_file_location('weapon_hd_vfs', os.path.join(L.DOCS, 'tools', 'weapon_hd', 'vfs.py'))
HV = importlib.util.module_from_spec(sp); sp.loader.exec_module(HV)


def main():
    cmd, arg = sys.argv[1], sys.argv[2]
    idx = HV.index()
    if cmd == 'name':
        for k in sorted(idx):
            if arg.lower() in k:
                print(k, '<-', ', '.join(os.path.basename(p) for p, _ in idx[k]))
    else:
        data = HV.read(arg)
        if data is None:
            print('not found'); return
        txt = data.decode('latin-1')
        rx = re.compile(sys.argv[3], re.I) if len(sys.argv) > 3 else None
        for i, ln in enumerate(txt.splitlines(), 1):
            if rx is None or rx.search(ln):
                print('%4d %s' % (i, ln.rstrip()))


if __name__ == '__main__':
    main()
