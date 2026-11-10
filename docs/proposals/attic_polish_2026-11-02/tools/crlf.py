"""crlf.py <file> - rewrite a text file with CRLF line ends (make_newgame3d wants main.urc in its core.autocrlf working-copy form;
gen_weapon_viewer.py writes it back as LF)."""
import sys

p = sys.argv[1]
b = open(p, "rb").read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
open(p, "wb").write(b)
