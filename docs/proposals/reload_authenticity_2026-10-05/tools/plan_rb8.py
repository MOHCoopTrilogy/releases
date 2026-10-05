# phase B polish run rb8 (after the rb7 review): belt guns' right hand grips the charging handle and is back on the grip
# before the clip ends (rb7: snap at the end of the M1919), Lewis held 1.5 u higher. Only the changed guns.
EVERY = 1
GUNLIST = ["b_m1919", "b_mg42", "b_lewis"]
_look = lambda tag: ["wait 800", "screenshotJPEG ra__rb8__%s__after" % tag, "wait 1", "wait 1"]
POST = {"b_mg42": _look("b_mg42"), "b_m1919": _look("b_m1919")}
