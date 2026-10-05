# phase B run rb2: group 4 re-test (Lewis pan-only prop, DP-28) + group 6 drums (Thompson 50rd, 1928 Tommy, MP18)
# + the stock Thompson (stick reference) + revolver spent cases (Webley Mk VI, Webley, Nagant, M10), each followed by
# a look at the floor. Every frame captured (pop review).
EVERY = 1
GUNLIST = ["b_lewis", "b_dp28", "b_t50", "b_t1928", "b_mp18", "b_thompson", "b_webley6r", "b_webley", "b_nagant", "b_m10"]
_look = lambda tag: R.face(65) + ["wait 3000", "screenshotJPEG ra__rb2__%s__floor" % tag, "wait 1", "wait 1"] + R.face(0) + ["wait 1000"]
POST = {g: _look(g) for g in ["b_webley6r", "b_webley", "b_nagant", "b_m10"]}
