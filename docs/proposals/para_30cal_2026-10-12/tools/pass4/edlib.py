"""edlib.py - text edits of a .scr that tolerate a wrong guess of the tab depth: the old text is matched line by line
with any number of leading tabs, and the new text is shifted by the difference found."""
import io, re


class Ed:
    def __init__(self, path):
        self.path = path
        raw = io.open(path, encoding="latin-1", newline="").read()
        self.nl = "\r\n" if "\r\n" in raw else "\n"
        self.s = raw.replace("\r\n", "\n")

    def sub(self, old, new, n=1):
        s = self.s
        if s.count(old) == n:
            self.s = s.replace(old, new)
            return
        ol = old.split("\n")
        rx = "\n".join((r"(\t*)" if i == 0 else r"\t*") + re.escape(l.lstrip("\t")) if l.strip() else re.escape(l)
                       for i, l in enumerate(ol))
        ms = list(re.finditer("(?m)^" + rx if not old.startswith("\n") else rx, s))
        assert len(ms) == n, (len(ms), old[:80])
        for m in reversed(ms):
            d = len(m.group(1)) - (len(ol[0]) - len(ol[0].lstrip("\t")))
            nw = "\n".join((("\t" * d + l) if d >= 0 else l[min(-d, len(l) - len(l.lstrip("\t"))):]) if l.strip() else l
                           for l in new.split("\n"))
            s = s[:m.start()] + nw + s[m.end():]
        self.s = s

    def func(self, name, new):
        m = re.search(r"(?m)^%s( [^\n]*)?:\{\n" % re.escape(name), self.s)
        assert m, name
        e = re.compile(r"(?m)^\}end[^\n]*\n").search(self.s, m.end())
        self.s = self.s[:m.start()] + new.strip("\n") + "\n" + self.s[e.end():]

    def save(self):
        io.open(self.path, "w", encoding="latin-1", newline="").write(self.s.replace("\n", self.nl))
        print("saved", self.path, len(self.s.splitlines()), "lines")
