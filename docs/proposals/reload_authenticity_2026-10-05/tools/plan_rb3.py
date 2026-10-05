# phase B run rb3: drum re-test (overlap timing, MP18 dip) + group 7 C96 stripper clip (both C96s) + group 8 belts
# (MG42, M1919 - opening top cover), plus a look at each belt gun idle after the reload (cover must be shut).
EVERY = 1
GUNLIST = ["b_t50", "b_t1928", "b_mp18", "b_c96", "b_c96t", "b_mg42", "b_m1919"]
_look = lambda tag: ["wait 800", "screenshotJPEG ra__rb3__%s__after" % tag, "wait 1", "wait 1"]
POST = {"b_mg42": _look("b_mg42"), "b_m1919": _look("b_m1919")}
