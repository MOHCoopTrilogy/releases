#!/usr/bin/env python
"""
rcon.py - drive a running OpenMOHAA server's console from here.

WHY THIS EXISTS (again)
    docs/SOURCE_OF_TRUTH.md records that the canonical rcon client lived in a `scratchpad/`
    directory that resolved to a session-scoped temp path and no longer exists, taking the whole
    "drive the console yourself" workflow with it. This is that tool, rebuilt in docs/tools/ where
    it cannot evaporate.

THE ONE DETAIL THAT MAKES IT WORK
    A connectionless packet is FOUR 0xFF bytes followed by a DIRECTION byte, then the command.
    Omitting the 0x02 is what made rcon look dead for a long time and produced a wrong "rcon is
    broken" diagnosis - see bug-1143 and bug-1681, and the note in launch_dedicated_2player.ps1.
    Everything else is ordinary Quake3 rcon.

USAGE
    python docs/tools/rcon.py "status"
    python docs/tools/rcon.py --port 12203 --pw <password> "map m3l1a"
    python docs/tools/rcon.py --pw <password> "sv_fps"        # query a cvar

    The dedicated harness (launch_dedicated_2player.ps1) seeds a fixed password, so with no --pw
    this defaults to that one.
"""
import argparse, socket, sys

HARNESS_PW = "kRXYGDbvFdH6arXXaEYjoUGy"


def rcon(cmd, host="127.0.0.1", port=12203, pw=HARNESS_PW, timeout=2.5, quiet=False):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    # 0xFF 0xFF 0xFF 0xFF + 0x02 direction byte. The 0x02 is the part people leave out.
    pkt = b"\xff\xff\xff\xff\x02" + ("rcon %s %s" % (pw, cmd)).encode("latin-1")
    s.sendto(pkt, (host, port))
    out = []
    while True:
        try:
            data, _ = s.recvfrom(65536)
        except socket.timeout:
            break
        # reply is the same connectionless header, then "print\n" then the payload
        body = data.lstrip(b"\xff")
        if body[:1] in (b"\x02", b"\x01"):
            body = body[1:]
        if body.startswith(b"print"):
            body = body[5:].lstrip(b"\n")
        out.append(body.decode("latin-1", "replace"))
    s.close()
    text = "".join(out)
    if not quiet:
        sys.stdout.buffer.write(text.encode("utf-8", "replace"))
        if text and not text.endswith("\n"):
            print()
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=12203)
    ap.add_argument("--pw", default=HARNESS_PW)
    ap.add_argument("--timeout", type=float, default=2.5)
    a = ap.parse_args()
    txt = rcon(a.command, a.host, a.port, a.pw, a.timeout)
    if not txt.strip():
        print("(no reply - server not listening on %s:%d, or the password is wrong)" % (a.host, a.port))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
