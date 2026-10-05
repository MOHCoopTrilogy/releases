# phase B run rb1: groups 1-4 (scoped single-round rifles, Webley Mk VI, M1 Carbine, Lewis + DP-28 pan) + Beretta M38 hold A/B +
# magazine rest A/B. Every frame captured (pop review).
EVERY = 1
GUNLIST = ["b_arisakasn", "b_mosinsn", "b_mosinsnsil", "b_enfieldsn", "b_webley6", "b_carbine", "b_lewis", "b_dp28",
           "b_m38", "b_m38@mp40", "b_m38@thompson", "b_moschetto", "b_mp40", "b_mp40@flat0"]
PRE = {"b_m38@mp40": ["set coop_vmPrefixTest \"Beretta M38=mp40\"", "wait 100"],
       "b_m38@thompson": ["set coop_vmPrefixTest \"Beretta M38=thompson\"", "wait 100"],
       "b_moschetto": ["set coop_vmPrefixTest \"\"", "wait 100"],
       "b_mp40": ["set coop_magRestFlat 1", "wait 100"],
       "b_mp40@flat0": ["set coop_magRestFlat 0", "wait 100"]}
_look = lambda tag: R.face(65) + ["wait 3500", "screenshotJPEG ra__rb1__%s__floor" % tag, "wait 1", "wait 1"] + R.face(0) + ["wait 1500"]
POST = {"b_mp40": _look("magflat1"), "b_mp40@flat0": _look("magflat0")}
