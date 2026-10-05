# phase B polish run rb4: every hand-keyed reload (keyclip.py) - Thompson 50rd (knob + drum), 1928 Tommy (drum), MP18
# (drum + right-hand cock, gun no longer dipped), Lewis (pan lift-off / turn-on), C96 + Trench (stripper clip), MG42 and
# M1919 (cover, belt prop - no ammo box on the M1919, charging handle). Every frame captured; a look at each belt gun
# after its reload (cover must be shut).
EVERY = 1
GUNLIST = ["b_t50", "b_t1928", "b_mp18", "b_lewis", "b_c96", "b_c96t", "b_mg42", "b_m1919"]
_look = lambda tag: ["wait 800", "screenshotJPEG ra__rb4__%s__after" % tag, "wait 1", "wait 1"]
POST = {"b_mg42": _look("b_mg42"), "b_m1919": _look("b_m1919")}
