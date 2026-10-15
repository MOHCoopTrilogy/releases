import re
p = r"C:\mohaa-coop-dev\.wolf\buglog.json"
b = open(p, "rb").read().decode("utf-8")
i = b.index('"id": "bug-3917"')
head, tail = b[:i], b[i:]
nl = "\r\n" if "\r\n" in tail[:400] else "\n"
rc_old = re.search(r'"root_cause": "[^\n]*",', tail).group(0)
fx_old = re.search(r'"fix": "[^\n]*",', tail).group(0)
rc = ('"root_cause": "VERIFIED in code: coop_mirrorSlideSend (menumirror.scr) ran a forced pass every 4th 0.5 s tick (2 s) that '
      're-sent ui_addhud <current slide> to every remote player even when unchanged; UI_AddHud_f (cl_ui.cpp) calls hud->ShowMenu() on every add, '
      'which restarts the full-screen card, so the briefing blinked black every 2 s (worse at 200 ms ping). The slide-change order was also '
      'remove-old then add-new, leaving a black gap between cards.",')
fx = ('"fix": "menumirror.scr coop_mirrorSlideSend: slide change now sends ui_addhud NEW first, then ui_removehud OLD; an unchanged slide is never '
      're-sent (the forced pass only repeats ui_removehud of the previous slide, a no-op when it is already down). Host/listen path untouched. '
      'Commit 6e53cbd6 on hzm-mod-brieffix (brieffix-next). Proof: docs/proposals/brieffix_2026-10-14/README.md. Ship: code pak only.",')
tail = tail.replace(rc_old, rc, 1).replace(fx_old, fx, 1)
tail = tail.replace('"open"\n', '"fixed"\n', 1).replace('"open"\r\n', '"fixed"\r\n', 1)
open(p, "wb").write((head + tail).encode("utf-8"))
print("ok")
