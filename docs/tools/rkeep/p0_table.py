#!/usr/bin/env python3
"""p0_table.py - turn a rkeep_p0.py run (summary.json + qconsole.log) into the P0 tables (markdown on stdout).

  python p0_table.py runs/<tag> [runs/<baseline-tag>]
"""
import json, os, re, statistics, sys


def f(x, d=1):
    try:
        return ("%." + str(d) + "f") % float(x)
    except (TypeError, ValueError):
        return "-"


def load(run):
    s = json.load(open(os.path.join(run, "summary.json")))
    n = json.load(open(os.path.join(run, "notes.json")))
    return s, n


def registrations(s):
    """pair every RKEEP (end of RE_BeginRegistration) with the RKEEPINIT/RKEEPGLSL of that R_Init and the RKEEPIMG
    end/final lines of the same reg number."""
    inits = {int(x["rinit"]): x for x in s.get("RKEEPINIT", [])}
    glsl = {int(x["rinit"]): x for x in s.get("RKEEPGLSL", [])}
    imgs_end = {int(x["reg"]): x for x in s.get("RKEEPIMG", []) if x.get("when") == "end"}
    imgs_final = {int(x["reg"]): x for x in s.get("RKEEPIMG", []) if x.get("when") == "final"}
    vram = {int(x["reg"]): x for x in s.get("RKEEPVRAM", [])}
    out = []
    for r in s.get("RKEEP", []):
        reg = int(r["reg"]); ri = int(r["rinit"])
        out.append({"reg": reg, "ts": r.get("ts"), "rkeep": r, "init": inits.get(ri, {}), "glsl": glsl.get(ri, {}),
                    "img_end": imgs_end.get(reg, {}), "img_final": imgs_final.get(reg, {}), "vram": vram.get(reg, {})})
    return out


def main():
    run = sys.argv[1]
    s, n = load(run)
    regs = registrations(s)
    print("### Run %s  (renderer %s, probe %s, soak servers during run: %s)\n" % (n["tag"], n["renderer"], n["probe"],
                                                                              n.get("soak_servers_running")))
    print("| reg | time | map (at end) | BeginRegistration ms | teardown ms | R_Init ms | gl | images | fbo | glsl | "
          "shd_int | shd_scan | shd_ext | skins+models | ft+queries | sky+marks | font | gfxinfo |")
    print("|" + "---|" * 18)
    for g in regs:
        i = g["init"]; r = g["rkeep"]
        mp = g["img_end"].get("map") or g["img_final"].get("map") or "(menu/boot)"
        print("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            g["reg"], (g["ts"] or "")[11:], mp, f(r.get("ms")), f(r.get("teardown")), f(i.get("total")),
            f(i.get("gl")), f(i.get("images")), f(i.get("fbo")), f(i.get("glsl")), f(i.get("shd_internal")),
            f(i.get("shd_scan")), f(i.get("shd_external")), f(i.get("skins_models")), f(i.get("freetype_queries")),
            f(i.get("sky_marks")), f(i.get("font")), f(i.get("gfxinfo"))))
    print()
    print("| reg | programs | compile+link ms | uniform print ms | binary tested/ok | binary MB | capture ms | "
          "reload ms | uniform-location re-query ms | reload+locations ms |")
    print("|" + "---|" * 10)
    for g in regs:
        x = g["glsl"]
        if not x:
            continue
        print("| %d | %s | %s | %s | %s/%s | %s | %s | %s | %s | %s |" % (
            g["reg"], x.get("programs"), f(x.get("compileLink")), f(x.get("uniformPrint")), x.get("tested"),
            x.get("reloadOk"), f(x.get("MB"), 2), f(x.get("capture")), f(x.get("reload")), f(x.get("locQuery")),
            f(x.get("reloadPlusLoc"))))
    print()
    print("| reg | map | disk image loads | load ms | MB | vs previous registration: n / ms / MB | "
          "vs last world: n / ms / MB | tick ms excluded | VRAM used MB |")
    print("|" + "---|" * 9)
    for g in regs:
        x = g["img_final"] or g["img_end"]
        if not x:
            continue
        print("| %d | %s | %s | %s | %s | %s (%s) / %s / %s | %s (%s) / %s / %s | %s | %s |" % (
            g["reg"], x.get("map"), x.get("loads"), f(x.get("ms")), f(x.get("MB")),
            x.get("prev_n"), (x.get("prev_vsPrev") or "").strip("()") if False else "", f(x.get("prev_ms")),
            f(x.get("prev_MB")), x.get("world_n"), "", f(x.get("world_ms")), f(x.get("world_MB")), f(x.get("tickMs")),
            g["vram"].get("usedMB", "-")))
    print()
    print("CL_InitCGame seconds:", [c for _, c in s.get("cgame", [])])
    print("Server lines:", s.get("server"))
    print("engine GLSL lines:", s.get("glsl_engine_line"))
    print("error/warning line counts:", s.get("errors"))


if __name__ == "__main__":
    main()
