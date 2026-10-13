# ---- SMG lane block (inserted into run_smg.py by takeover.py before `def run`; edit HERE, then run takeover.py) ----
# sdemo: ONE continuous capture per gun and case - settled, [raise], fire, reload, [lower].
#   case L = rounds left (three short presses, then `reload`), E = emptied (the trigger held until the gun is dry; an
#   emptied gun starts its reload by itself). Aimed tags end in __demo__after (the shared measure tools read them),
#   hip tags in __demohip__after. A reference frame without the first-person model is taken before the lower.
SMG_HOLD = [175]        # frames the trigger is held to empty the gun (MP40: 32 rounds at 0.08 s = 160 frames of 16 ms)
SMG_REL = [200]         # frames captured from the reload mark


def sdemo(sess, gun, case, ads=True, stance="stand"):
    tag = "ab__%s__%s__%s%s__%s__after" % (sess, gun, ("" if stance == "stand" else stance) + ("ads" if ads else "hip"), case, "demo" if ads else "demohip")
    i = [0]
    L = S.RELEASE + S.TO_STAND + S.APPLY[stance] + A.MODE["after"] + ["wait 600"]
    L += ["coop_braceView"] if stance == "braced" else []
    L += ["set cg_adsSightDebug 2", "echo ^~^~^ ABSCEN begin %s" % tag]
    L += A.frames(tag, 8, i)
    if ads:
        L += ["+button13", "echo ^~^~^ DEMO raise %d" % i[0]] + A.frames(tag, 50, i)
    REF = ["set cg_drawviewmodel 0", "wait 1", "wait 1", "wait 1", "screenshotJPEG %s__ref" % tag, "wait 1", "wait 1",
           "set cg_drawviewmodel 2", "wait 1", "wait 1", "wait 1", "wait 1"]
    if case == "E":
        L += ["echo ^~^~^ DEMO empty %d" % i[0], "+attackprimary", "echo ^~^~^ DEMO fire %d" % i[0]] + A.frames(tag, SMG_HOLD[0], i)
        L += ["-attackprimary", "echo ^~^~^ DEMO reload %d" % i[0]] + A.frames(tag, SMG_REL[0], i)
    else:
        for k in range(3):
            L += ["+attackprimary", "echo ^~^~^ DEMO fire %d" % i[0]] + A.frames(tag, 3, i) + ["-attackprimary"] + A.frames(tag, 22, i)
        L += A.frames(tag, 40, i)
        L += ["reload", "echo ^~^~^ DEMO reload %d" % i[0]] + A.frames(tag, SMG_REL[0], i)
    L += REF
    if ads:
        L += ["-button13", "echo ^~^~^ DEMO lower %d" % i[0]] + A.frames(tag, 40, i)
    else:
        L += ["echo ^~^~^ DEMO lower %d" % i[0]] + A.frames(tag, 10, i)
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"]
    L += ["coop_braceView"] if stance == "braced" else []
    L += S.RELEASE + A.UNAPPLY[stance]
    R.step(L, timeout=2400)


def third_person(sess, gun):
    """the held gun from outside while it fires a burst and reloads: every 2nd frame"""
    tag = "ab__%s__%s__stand__tp__after" % (sess, gun)
    L = S.RELEASE + S.TO_STAND + ["wait 400", "set cg_3rd_person 1", "set cg_cameradist 62", "set cg_cameraheight 6", "set cg_camerasideoffset -34", "wait 600",
                                  "echo ^~^~^ ABSCEN begin %s" % tag]
    k = 0
    for n, pre in ((10, []), (60, ["+attackprimary"]), (20, ["-attackprimary"]), (60, ["reload"])):
        L += pre
        for _ in range(n):
            L += ["screenshotJPEG %s__%04d" % (tag, k), "wait 1", "wait 1", "wait 1", "wait 1"]
            k += 1
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_3rd_person 0", "set cg_camerasideoffset 18", "set cg_cameradist 120", "set cg_cameraheight 18", "wait 400"] + S.RELEASE
    R.step(L, timeout=900)


def ai_fire(sess, tik):
    """an AI spawned in front of the player by the test overlay's own thread (cvar coop_isAi; the dev `spawn` needs
    cheats, which the mod's server start switches off), AI switched on, the player visible and invulnerable: does its
    gun fire, cycle and reload without errors? every 3rd frame for about 12 s"""
    tag = "ab__%s__ai__stand__ai__after" % sess
    L = S.RELEASE + S.TO_STAND + ["wait 400", "echo ^~^~^ ABSCEN begin %s" % tag, "set g_ai 1", "set coop_isAi %s" % tik, "wait 800"]
    for k in range(240):
        L += ["screenshotJPEG %s__%04d" % (tag, k), "wait 1", "wait 1", "wait 1", "wait 1", "wait 1", "wait 1"]
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set g_ai 0", "wait 300"] + S.RELEASE
    R.step(L, timeout=900)


def sbreak(sess, gun, kind, at, case="L", n=150):
    """an AIMED reload broken off `at` 16 ms frames after it starts, EVERY frame captured (the shared `interrupt` part
    takes every 2nd): fire = the trigger, switch = next weapon, sprint = run forward, drop = the aim let go (the row
    hands over to the hip clip mid-reload), crouch = a stance change. case E = the gun emptied first."""
    tag = "ab__%s__%s__brk%s%s%d__demo__after" % (sess, gun, kind, case, at)
    i = [0]
    L = S.RELEASE + S.TO_STAND + A.MODE["after"] + ["wait 600", "set cg_adsSightDebug 2", "echo ^~^~^ ABSCEN begin %s" % tag]
    L += A.frames(tag, 4, i) + ["+button13", "echo ^~^~^ DEMO raise %d" % i[0]] + A.frames(tag, 40, i)
    if case == "E":
        L += ["+attackprimary", "echo ^~^~^ DEMO fire %d" % i[0]] + A.frames(tag, SMG_HOLD[0], i) + ["-attackprimary"]
    else:
        L += ["+attackprimary", "echo ^~^~^ DEMO fire %d" % i[0]] + A.frames(tag, 12, i) + ["-attackprimary"] + A.frames(tag, 50, i) + ["reload"]
    L += ["echo ^~^~^ DEMO reload %d" % i[0]] + A.frames(tag, at, i)
    act = {"fire": ["+attackprimary"], "switch": ["weapnext"], "sprint": ["+speed", "+forward"], "drop": ["-button13"],
           "crouch": ["+movedown"]}[kind]
    L += act + ["echo ^~^~^ DEMO intr %d" % i[0]] + A.frames(tag, 8, i)
    L += (["-attackprimary"] if kind == "fire" else []) + A.frames(tag, n - 8, i)
    L += ["echo ^~^~^ DEMO lower %d" % i[0], "-button13", "-forward", "-speed", "-movedown"] + A.frames(tag, 30, i)
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + S.RELEASE
    if kind == "switch":
        L += ["wait 1200", "weapprev", "wait 2500"]
    if kind == "sprint":
        L += ["+back", "wait 1300", "-back", "wait 400"]
    R.step(L, timeout=2400)


def smg_parts(a, gun):
    for part in a.parts:
        if part.startswith("sbreak"):                # sbreak | sbreak:fire,switch:40,90[:E]   kinds : frames after the reload starts : case
            sp = part.split(":")
            kinds = sp[1].split("+") if len(sp) > 1 else ["fire", "switch", "sprint", "drop"]
            ats = [int(x) for x in sp[2].split("+")] if len(sp) > 2 else [50, 105]
            for kind in kinds:
                for at in ats:
                    R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS["colt45"]) + S.give(A.GUNS[gun]), timeout=120)
                    sbreak(a.session, gun, kind, at, case=(sp[3] if len(sp) > 3 else "L"))
            R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
            continue
        if part.startswith("sdemo"):                 # sdemo | sdemoL | sdemoE  (aimed);  shipdemo... (hip)
            cases = part[5:] or "LE"
            for c in cases:
                for st in (a.sstances if c == "E" else ["stand"]):      # every stance is run on the EMPTY case (magazine + cock)
                    R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                    sdemo(a.session, gun, c, ads=True, stance=st)
        elif part.startswith("shipdemo"):
            for c in (part[8:] or "LE"):
                R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
                sdemo(a.session, gun, c, ads=False)
        elif part == "tp":
            R.step(S.RELEASE + S.TO_STAND + S.give(A.GUNS[gun]), timeout=90)
            third_person(a.session, gun)
        elif part == "ai":
            ai_fire(a.session, a.aitik)


def cheats_on():
    """test-only: `spawn` (an AI to look at) needs the server started with cheats - put `+set cheats 1` on the command
    line of THIS harness's own client (the shared launcher builds the argument list; its window policy hook is wrapped)"""
    orig = R.hw.apply_policy

    def wrapped(args, **kw):
        a2, late = orig(args, **kw)
        return [a2[0], "+set", "cheats", "1"] + list(a2[1:]), late
    R.hw.apply_policy = wrapped
# ---- end of the SMG lane block ----


