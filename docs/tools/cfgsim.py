#!/usr/bin/env python3
"""cfgsim.py - a tiny model of the engine's console, to test the generated ui/loadout cfg chains OFFLINE.

What is modelled (what the Armory's cfg chains rely on, verified against the existing generated pages):
  * text is consumed one statement at a time (newline or ';' outside quotes);
  * `exec <file>` and `vstr <cvar>` INSERT their text at the FRONT of the pending buffer (depth first, before the rest of the line);
  * `set|seta|setu <name> <rest>`: the value is the rest of the statement (argv 2.. re-joined, one blank apart), quotes stripped
    when the value is exactly one quoted token;
  * `append`, `echo`, `wait`, `beep`-style unknown commands are recorded and ignored.
Not modelled: cvar flags, archiving, stufftext, the Cbuf size limit (a depth/loop guard stands in for it).

    sim = Sim(mod_dir); sim.run("exec ui/loadout/open.cfg"); sim.cv["coop_loK0T1"]
"""
import io, os, re

MAX_STEPS = 400000


def split_statements(text):
    """yield statements of a buffer chunk: lines, then ';' outside quotes; // comments stripped"""
    for line in text.replace("\r\n", "\n").split("\n"):
        out, cur, q = [], [], False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"':
                q = not q
                cur.append(ch)
            elif not q and ch == "/" and line[i:i + 2] == "//":
                break
            elif not q and ch == ";":
                out.append("".join(cur))
                cur = []
            else:
                cur.append(ch)
            i += 1
        out.append("".join(cur))
        for s in out:
            s = s.strip()
            if s:
                yield s


def tokenize(stmt):
    toks, cur, q = [], [], False
    for ch in stmt:
        if ch == '"':
            q = not q
            if not q and not cur:
                toks.append("")      # an empty quoted token
            continue
        if ch in " \t" and not q:
            if cur:
                toks.append("".join(cur))
                cur = []
            continue
        cur.append(ch)
    if cur:
        toks.append("".join(cur))
    return toks


class Sim:
    def __init__(self, mod_dir):
        self.mod = mod_dir
        self.cv = {}
        self.log = []            # unknown commands / missing cvars / missing files, in order
        self.exec_count = {}
        self.steps = 0

    def _cvar(self, name):
        return self.cv.get(name.lower())

    def run(self, text):
        """run statements; insertion semantics via an explicit stack of pending statement lists"""
        pending = list(split_statements(text))
        pending.reverse()           # pop() from the end = front
        while pending:
            self.steps += 1
            if self.steps > MAX_STEPS:
                raise RuntimeError("cfgsim: step limit (loop?)")
            stmt = pending.pop()
            toks = tokenize(stmt)
            if not toks:
                continue
            cmd = toks[0].lower()
            if cmd in ("set", "seta", "setu", "sets"):
                if len(toks) < 2:
                    continue
                name = toks[1].lower()
                rest = stmt.split(None, 2)
                val = rest[2].strip() if len(rest) > 2 else ""
                if len(val) >= 2 and val[0] == '"' and val.count('"') == 2 and val[-1] == '"':
                    val = val[1:-1]
                else:
                    val = " ".join(tokenize(val)) if '"' in val else " ".join(val.split())
                self.cv[name] = val
            elif cmd == "vstr":
                name = toks[1].lower() if len(toks) > 1 else ""
                if name not in self.cv:
                    self.log.append("vstr: no cvar %s" % name)
                    continue
                pending.extend(reversed(list(split_statements(self.cv[name]))))
            elif cmd == "exec":
                rel = toks[1] if len(toks) > 1 else ""
                p = os.path.join(self.mod, rel.replace("/", os.sep))
                if not os.path.isfile(p):
                    self.log.append("exec: missing file %s" % rel)
                    continue
                self.exec_count[rel] = self.exec_count.get(rel, 0) + 1
                txt = io.open(p, encoding="latin-1", newline="").read()
                pending.extend(reversed(list(split_statements(txt))))
            else:
                self.log.append("cmd: %s" % stmt[:80])
        return self

    def exec(self, rel):
        return self.run("exec %s" % rel)

    def get(self, name, default=None):
        return self.cv.get(name.lower(), default)
