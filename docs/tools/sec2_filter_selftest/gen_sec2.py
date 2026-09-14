#!/usr/bin/env python3
# SEC2 self-test generator (security layer 2: the exe-side server-origin command filter).
#
# Everything the harness links is pasted or copied from live source so a pass is produced by the shipped
# code, never a transcription (docs/TRAPS.md T14):
#
#   work tree  openmohaa-hzm/code/qcommon/cmd.c, cmd_filter.c, q_shared.c  compiled in place by build.bat
#   head/      cmd.c + qcommon.h at HEAD                                   the shipped layer-1-only exe
#   mut_*/     work cmd.c with ONE planted defect each                     must make the harness FAIL
#   real_cvarcmds.inc   Cvar_Command / Cvar_Set_f / Cvar_Append_f          (qcommon/cvar.c)
#   real_clcg.inc       CL_CG_StuffServer / CL_CG_Stuff + the pending block (client/cl_cgame.cpp)
#   cgf_work.inc        the working-tree cgame reception filter
#   cgf_head.inc        the HEAD cgame reception filter (the previous cgame.dll)
#   corpus.inc          every coop script stufftext, runtime pieces made concrete
#   reached.inc         every statement the server reaches through exec / vstr (sec2_guardlist closure)
#   guardw.inc          every reached server write that lands on a guard-list cvar
#   engcmds.inc / engcvars.inc / basecvars.inc   engine command + cvar registries, tree cvar values
#
#   python gen_sec2.py                      generate
#   python gen_sec2.py --compare A B        compare two corpus trace files (exit 1 on any difference)
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import sec2_guardlist as G  # noqa: E402

ENGROOT = os.path.join(G.DEV, "openmohaa-hzm")
REV_153 = "9045a836"  # v1.5.3: the cgame.dll players actually have today (ARM_OLDCG153)
W = G.W
Q = '"'


def die(msg):
    sys.exit("gen_sec2: " + msg)


def read(p):
    return open(p, encoding="latin-1").read()


def write(name, text):
    p = os.path.join(HERE, name)
    d = os.path.dirname(p)
    if not os.path.isdir(d):
        os.makedirs(d)
    open(p, "w", newline="\n", encoding="latin-1").write(text)


def git_show(path, rev="HEAD"):
    r = subprocess.run(["git", "-C", ENGROOT, "show", rev + ":" + path], capture_output=True)
    if r.returncode != 0:
        die("git show %s:%s failed: %s" % (rev, path, r.stderr.decode("latin-1")))
    return r.stdout.decode("latin-1").replace("\r\n", "\n")


def extract(text, sig):
    """The whole function whose signature matches `sig` (brace-balanced, string/comment aware)."""
    m = re.search(sig, text, re.M)
    if not m:
        die("signature not found: " + sig)
    i = m.start()
    k = text.index("{", m.end() - 1)
    d = 0
    n = len(text)
    while k < n:
        c = text[k]
        if text.startswith("//", k):
            k = text.index("\n", k)
            continue
        if text.startswith("/*", k):
            k = text.index("*/", k) + 2
            continue
        if c in "\"'":
            q = c
            k += 1
            while text[k] != q:
                if text[k] == "\\":
                    k += 1
                k += 1
            k += 1
            continue
        if c == "{":
            d += 1
        elif c == "}":
            d -= 1
            if d == 0:
                return text[i:k + 1]
        k += 1
    die("unbalanced " + sig)


def strip_includes(txt):
    return re.sub(r'^#include.*$', '', txt, flags=re.M)


def cesc(s):
    out = []
    prev_hex = False
    for ch in s:
        o = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == Q:
            out.append('\\"')
        elif o < 32 or o >= 127:
            out.append("\\%03o" % o)
        elif prev_hex and ch in "01234567":
            out.append('""' + ch)  # never let a digit extend a preceding octal escape
        else:
            out.append(ch)
        prev_hex = o < 32 or o >= 127
    return "".join(out)


def mutate(src, anchor, repl, name):
    if src.count(anchor) != 1:
        die("mutant %s: anchor matched %d times" % (name, src.count(anchor)))
    return src.replace(anchor, repl)


def generate():
    q = os.path.join(G.ENG, "qcommon")
    cmd_work = read(os.path.join(q, "cmd.c")).replace("\r\n", "\n")
    cvar_c = read(os.path.join(q, "cvar.c")).replace("\r\n", "\n")
    clcg = read(os.path.join(G.ENG, "client", "cl_cgame.cpp")).replace("\r\n", "\n")

    # ---- real cvar command handlers
    parts = [extract(cvar_c, r"^qboolean Cvar_Command\( void \)"),
             extract(cvar_c, r"^void Cvar_Set_f\( void \)"),
             extract(cvar_c, r"^void Cvar_Append_f\( void \)")]
    write("real_cvarcmds.inc", "/* pasted by gen_sec2.py from qcommon/cvar.c */\n" + "\n\n".join(parts) + "\n")

    # ---- real cl_cgame.cpp stufftext plumbing
    m = re.search(r"// HZM coop \[SEC2\] the last stufftext handed to cgame.*?static qboolean\tcl_cgPendingNewline = qfalse;\n",
                  clcg, re.S)
    if not m:
        die("cl_cgame.cpp pending declarations not found")
    decls = m.group(0)
    f1 = extract(clcg, r"^static void CL_CG_StuffServer\( const char \*text \)")
    f2 = extract(clcg, r"^static void CL_CG_Stuff\( const char \*text \)")
    m = re.search(r"(\t// HZM coop \[SEC2\] remember a stufftext.*?)\treturn CL_ProcessServerCommand\(s, cmd, differentServer\);",
                  clcg, re.S)
    if not m:
        die("cl_cgame.cpp pending block not found")
    block = ("/* CL_GetServerCommand's pending block, verbatim, run right after it tokenized the server command */\n"
             "static void clcg_after_tokenize(void) {\n\tconst char *cmd = Cmd_Argv(0);\n" + m.group(1) + "}\n")
    write("real_clcg.inc", "/* pasted by gen_sec2.py from client/cl_cgame.cpp */\n" + decls + "\n" + f1 + "\n\n" + f2 + "\n\n" + block)

    # ---- cgame reception filters
    write("cgf_work.inc", strip_includes(read(os.path.join(G.ENG, "cgame", "cg_servercmds_filter.cpp"))))
    write("cgf_head.inc", strip_includes(git_show("code/cgame/cg_servercmds_filter.cpp")))
    write("cgf_153.inc", strip_includes(git_show("code/cgame/cg_servercmds_filter.cpp", REV_153)))

    # ---- the systeminfo cvar scan (client/cl_parse.cpp): neither command filter sees configstrings, so the
    # scan is the third way a server writes a client cvar. The work tree's split-out function, and the same
    # loop at HEAD (no SEC2 skip) wrapped in that signature, so each arm runs its own exe's real code.
    clpar = read(os.path.join(G.ENG, "client", "cl_parse.cpp")).replace("\r\n", "\n")
    write("real_sysinfo_work.inc", "/* pasted by gen_sec2.py from client/cl_parse.cpp */\n"
          + extract(clpar, r"^static qboolean CL_SystemInfoSetCvars\( const char \*systemInfo \)") + "\n")
    head_par = git_show("code/client/cl_parse.cpp")
    a0, a1 = "\tgameSet = qfalse;\n", "\t// if game folder should not be set"
    if head_par.count(a0) != 1 or head_par.count(a1) != 1:
        die("HEAD cl_parse.cpp systeminfo scan anchors are not unique")
    loop = head_par[head_par.index(a0):head_par.index(a1)]
    write("real_sysinfo_head.inc",
          "/* pasted by gen_sec2.py from client/cl_parse.cpp at HEAD (the scan with no SEC2 skip), wrapped in\n"
          "   the working tree's signature */\n"
          "static qboolean CL_SystemInfoSetCvars( const char *systemInfo ) {\n"
          "\tconst char\t*s;\n\tchar\t\tkey[BIG_INFO_KEY];\n\tchar\t\tvalue[BIG_INFO_VALUE];\n"
          "\tqboolean\tgameSet;\n\n" + loop + "\n\treturn gameSet;\n}\n")

    # ---- HEAD exe sources (the shipped layer-1-only build)
    write(os.path.join("head", "cmd.c"), git_show("code/qcommon/cmd.c"))
    write(os.path.join("head", "qcommon.h"), git_show("code/qcommon/qcommon.h"))
    write(os.path.join("head", "cg_public.h"), git_show("code/cgame/cg_public.h"))  # abi.c: the previous import struct

    # ---- planted mutants of the work cmd.c (each must make a specific group fail)
    muts = {
        "mut_vstrlocal": ('Cbuf_InsertTextOrigin( va("%s\\n", v ), Cmd_ChildOrigin( origin ) );',
                          'Cbuf_InsertTextOrigin( va("%s\\n", v ), CMD_ORIGIN_LOCAL );'),
        "mut_noshift": ('\t\tcmd_text_origin[ i + len ] = cmd_text_origin[ i ];\n', ''),
        "mut_nomemmove": ('\t\t\tmemmove (cmd_text_origin, cmd_text_origin+i, cmd_text.cursize);\n', ''),
        "mut_lsforced": ('env.localServer\t\t\t\t= ( com_sv_running && com_sv_running->integer ) ? qtrue : qfalse;',
                         'env.localServer\t\t\t\t= qtrue;'),
    }
    for name, (a, r) in muts.items():
        write(os.path.join(name, "cmd.c"), mutate(cmd_work, a, r, name))

    # ---- tree-derived corpora
    fams, closure, tree = G.derive()

    def guarded(name):
        n = name.lower()
        for e in fams.values():
            p = e["prefix"].lower()
            if e["kind"] == "EXACT" and n == p:
                return True
            if e["kind"] == "DIGITS" and n.startswith(p) and n[len(p):].isdigit() and len(n) > len(p):
                return True
        return False

    def concrete_variants(cmd):
        """Concrete stufftexts for one reconstructed command: runtime exec paths / vstr names expand to real
        files / assigned names (up to 6, evenly spread), every other runtime piece becomes 1."""
        stmts = G.cbuf_split(cmd)
        choices = []
        for st in stmts:
            t = G.tokenize(st)
            opts = None
            if t and W in st:
                v = t[0].lower()
                if v == "exec" and len(t) > 1 and W in t[1]:
                    files = tree.exec_files(t[1])
                    if files:
                        opts = [st.replace(t[1], f) for f in files]
                elif v == "vstr" and len(t) > 1 and W in t[1]:
                    names = sorted(k for k in tree.assigns if W not in k and G.name_match(t[1], k))
                    if names:
                        opts = [st.replace(t[1], nm) for nm in names]
            if not opts:
                opts = [st.replace(W, "1")]
            if len(opts) > 6:
                step = len(opts) / 6.0
                opts = [opts[int(i * step)] for i in range(6)]
            choices.append(opts)
        n = max(len(c) for c in choices) if choices else 0
        out = []
        for i in range(n):
            out.append(";".join(c[i % len(c)] for c in choices))
        return out

    corpus = []
    seen = set()
    for rel, p in G.mod_files((".scr",)):
        for ln, line in enumerate(open(p, encoding="latin-1"), 1):
            s = G.strip_line_comment(line).strip()
            if "stufftext" not in s:
                continue
            expr = G.stufftext_expr(s)
            if expr is None or expr == W:
                continue  # opaque: the whole command is built at runtime
            cmd = G.reconstruct(expr).replace("\n", "")
            if cmd.replace(W, "").strip() == "":
                continue
            for v in concrete_variants(cmd):
                if v not in seen and v.strip():
                    seen.add(v)
                    corpus.append((v, "%s:%d" % (rel, ln)))
    write("corpus.inc", "/* generated by gen_sec2.py */\n" +
          "".join('CORPUS("%s", "%s")\n' % (cesc(v), cesc(w)) for v, w in corpus))

    reached = {}
    for st in closure:
        k = st.strip()
        if not k:
            continue
        c = k.replace(W, "1")
        # an opaque statement (the whole command built at runtime) is not a statement any static rule can
        # judge - gen prints those separately - so it never carries the expanded flag
        opaque = k.replace(W, "").strip() == ""
        reached[c] = reached.get(c, 0) | (0 if opaque else (1 if k in tree.expanded else 0))
    write("reached.inc", "/* generated by gen_sec2.py */\n"
          + "".join('REACHED("%s", %d)\n' % (cesc(s), e) for s, e in sorted(reached.items())))

    gw = []
    for st in sorted(closure):
        c = st.strip().replace(W, "1")
        for name, value in tree.writes(G.tokenize(c)):
            if guarded(name):
                gw.append(c)
                break
    write("guardw.inc", "/* generated by gen_sec2.py */\n" + "".join('GUARDW("%s")\n' % cesc(s) for s in sorted(set(gw))))

    write("engcmds.inc", "/* generated by gen_sec2.py */\n" +
          "".join('ENG_CMD("%s")\n' % cesc(c) for c in sorted(tree.commands)))

    client_cv, host_cv = set(), set()
    for rel, p in G.engine_files():
        t = G.strip_c_comments(read(p))
        names = set(re.findall(r'Cvar_Get\s*\(\s*"([A-Za-z0-9_]+)"', t))
        (host_cv if rel.startswith(("fgame/", "server/")) else client_cv).update(names)
    write("engcvars.inc", "/* generated by gen_sec2.py */\n" +
          "".join('ENG_CVAR("%s")\n' % c for c in sorted(client_cv, key=str.lower)))

    eng_lower = set(c.lower() for c in client_cv)
    base = {}
    for rel, p in sorted(G.mod_files((".cfg", ".urc"))):
        for st in G.cbuf_split(read(p)):
            t = G.tokenize(st)
            if len(t) >= 3 and t[0].lower() in G.SET_VERBS:
                k = t[1].lower()
                if k not in eng_lower and k not in base and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t[1]):
                    base[k] = (t[1], " ".join(t[2:]))
    write("basecvars.inc", "/* generated by gen_sec2.py */\n" +
          "".join('BASE_CVAR("%s", "%s")\n' % (cesc(n), cesc(v)) for k, (n, v) in sorted(base.items())))

    write("paths.inc", '#define MOD_ROOT "%s"\n' % G.MOD.replace("\\", "/"))

    print("gen_sec2: corpus %d stufftexts, reached %d statements (%d of them through an exec/vstr), guarded "
          "writes %d, engine commands %d, engine cvars %d, tree cvars %d"
          % (len(corpus), len(reached), sum(reached.values()), len(set(gw)), len(tree.commands),
             len(client_cv), len(base)))


def compare(a, b):
    def load(p):
        out = {}
        for line in open(p, encoding="latin-1"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 4:
                out[(parts[0], parts[1])] = (parts[2], parts[3], parts[4] if len(parts) > 4 else "")
        return out
    A, B = load(a), load(b)
    if not A:
        print("compare: %s is empty" % a)
        return 1
    diff = [k for k in sorted(A) if k not in B or A[k][0] != B[k][0]]
    missing = [k for k in B if k not in A]
    for k in diff[:25]:
        print("  TRACE DIFF ls=%s case=%s  %s" % (k[0], k[1], A[k][1]))
        print("     %s: %s" % (os.path.basename(a), A[k][2][:300]))
        print("     %s: %s" % (os.path.basename(b), B.get(k, ("", "", "(missing)"))[2][:300]))
    print("compare %s vs %s: %d cases, %d differ, %d extra" % (os.path.basename(a), os.path.basename(b),
                                                              len(A), len(diff), len(missing)))
    return 1 if (diff or missing) else 0


def abi(head_out, work_out):
    """abi.c output: the new member must start exactly where the previous struct ended, every shared member must
    keep its offset, and the version must have been bumped."""
    def kv(p):
        toks = open(p, encoding="latin-1").read().split()
        return dict(t.split("=", 1) for t in toks if "=" in t)
    h, w = kv(head_out), kv(work_out)
    checks = [
        ("Cmd_StuffServer starts where the previous struct ended", w.get("Cmd_StuffServer_off") == h.get("sizeof")),
        ("apiversion offset unchanged", w.get("apiversion_off") == h.get("apiversion_off")),
        ("Cmd_Stuff offset unchanged", w.get("Cmd_Stuff_off") == h.get("Cmd_Stuff_off")),
        ("R_ClearAllRagdolls (previous last member) offset unchanged",
         w.get("R_ClearAllRagdolls_off") == h.get("R_ClearAllRagdolls_off")),
        ("struct grew by exactly one pointer", int(w.get("sizeof", 0)) - int(h.get("sizeof", 0)) == 8),
        ("CGAME_IMPORT_API_VERSION bumped", int(w.get("version", 0)) > int(h.get("version", 0))),
    ]
    bad = 0
    for name, ok in checks:
        print("  %s  %s" % ("ok  " if ok else "FAIL", name))
        bad += 0 if ok else 1
    print("abi: previous %s | new %s" % (" ".join("%s=%s" % kvp for kvp in sorted(h.items())),
                                         " ".join("%s=%s" % kvp for kvp in sorted(w.items()))))
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--compare":
        sys.exit(compare(sys.argv[2], sys.argv[3]))
    if len(sys.argv) == 4 and sys.argv[1] == "--abi":
        sys.exit(abi(sys.argv[2], sys.argv[3]))
    generate()
