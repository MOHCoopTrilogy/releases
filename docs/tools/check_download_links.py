"""Verify that every installer download link on the public README actually resolves.

Why this exists: README.md used to say "go to /releases/latest and download
MOHCoopTrilogy-Setup-<version>.exe". That was true for as long as every release carried an
installer. The full installer is ~6.8 GB and is therefore published only periodically, so the
moment a release shipped without one, /releases/latest stopped containing any setup exe and the
install instructions silently became impossible to follow. Nothing failed, nothing warned - a new
user just could not find the file. v1.2.9 shipped in exactly that state.

So the README now names the five installer files explicitly, with pinned URLs, and this checks
that those URLs still answer. A pinned link that 404s is a broken front door; better to hear it
from the build than from a player who gave up.

Exit 0 = all good or could not check (offline). Exit 1 only with --strict and a real 404.
"""
import re
import os
import sys

README = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "README.md")
URL_RE = re.compile(r'\((https://github\.com/[^)\s]+/releases/download/[^)\s]+)\)')


def check(url, timeout=15):
    """Range-GET one KB. HEAD is unreliable on GitHub's asset redirects."""
    import urllib.request
    import urllib.error
    req = urllib.request.Request(url, headers={"Range": "bytes=0-1023",
                                               "User-Agent": "mohcoop-linkcheck"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:                       # offline, DNS, TLS - not a link fault
        return None, str(e)


def main():
    strict = "--strict" in sys.argv
    try:
        with open(README, encoding="utf-8") as f:
            urls = []
            for u in URL_RE.findall(f.read()):
                if u not in urls:
                    urls.append(u)
    except Exception as e:
        print("download links: cannot read README (%s)" % e)
        return 0

    if not urls:
        print("download links: none found in README - did the install section change?")
        return 1 if strict else 0

    bad, unknown = [], 0
    for u in urls:
        code, err = check(u)
        if code is None:
            unknown += 1
        elif code not in (200, 206):
            bad.append((u, code))

    if bad:
        print("download links: %d of %d BROKEN" % (len(bad), len(urls)))
        for u, c in bad:
            print("  HTTP %s  %s" % (c, u.rsplit("/", 1)[-1]))
        print("  The README's install instructions point at files that are not there.")
        print("  Re-point them at a release that still carries the installer, or publish one.")
        return 1 if strict else 0
    if unknown:
        print("download links: could not verify (offline?) - %d link(s)" % unknown)
        return 0
    print("download links: %d installer link(s) OK" % len(urls))
    return 0


if __name__ == "__main__":
    sys.exit(main())
