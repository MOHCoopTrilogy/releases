"""Shader / tik lookups over the shipped pak set (winning copy of every file).

    python shgrep.py shader <regex>     every shader block (winning .shader files) whose body or name matches
    python shgrep.py tik <regex>        every winning .tik whose text matches: path, pak, the matching lines
    python shgrep.py cat <vpath>        print the winning copy of a text file
"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "docs", "tools", "weapon_hd"))
import vfs


def blocks(text):
    out = []; i = 0; n = len(text)
    text2 = re.sub(r"//[^\n]*", "", text)
    for m in re.finditer(r"(^|\n)\s*([^\s{}]+)\s*\n?\s*\{", text2):
        s = m.end(); d = 1; j = s
        while j < n and d:
            c = text2[j]
            d += (c == "{") - (c == "}")
            j += 1
        if m.start() >= i:
            out.append((m.group(2), text2[s:j - 1])); i = j
    return out


def main():
    mode, arg = sys.argv[1], sys.argv[2]
    idx = vfs.index()
    if mode == "cat":
        w = vfs.winner(arg)
        print("#", w)
        sys.stdout.write(vfs.read(arg).decode("latin-1"))
        return
    rx = re.compile(arg, re.I)
    if mode == "shader":
        for k in sorted(idx):
            if not k.endswith(".shader"):
                continue
            t = vfs.read(k).decode("latin-1")
            if not rx.search(t):
                continue
            for name, body in blocks(t):
                if rx.search(name) or rx.search(body):
                    print("== %s  [%s  %s]" % (name, k, os.path.basename(idx[k][-1][0])))
                    print("\n".join("   " + l.strip() for l in body.splitlines() if l.strip()))
    elif mode == "tik":
        for k in sorted(idx):
            if not k.endswith(".tik"):
                continue
            t = vfs.read(k).decode("latin-1")
            ls = [l.strip() for l in t.splitlines() if rx.search(l)]
            if ls:
                print("== %s [%s]" % (k, os.path.basename(idx[k][-1][0])))
                for l in ls[:12]:
                    print("   " + l)


if __name__ == "__main__":
    main()
