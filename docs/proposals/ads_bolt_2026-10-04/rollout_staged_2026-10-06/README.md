# ADS rollout attempt, 2026-10-06 - NOT SHIPPED

Goal: ship the already-reviewed ADS rows (garand_reload_ads, ppsh_reload_ads, springfield/enfield/mosin_rechamber_ads)
via the small fixes pak, on top of the v1.10.14-released fps_anims lists (so the 1.3 GB tex pak keeps its hash).
The override files and manifest here are exactly that (built, check passed, 5-member 236,093-byte pak).

In-game check with the exact release pak + the shipped cgame (33908110) in the private install (runs ab50 garand/ppsh
reloadA, ab51 springfield/mosin/enfield verify; 0 script errors): the "after" frames are identical to "before" - the
sights are LEFT in every stance (logcheck: sight dev max ~60 deg, "LEAVES THE SIGHTS"). So the rows alone do nothing in
the shipped build. The earlier passing runs (ab23/ab32) used test cgames/overlays that also carried uncommitted pieces
(overlay ov_k45b = reworked weapon tiks, coop_reload clips, the *_adsb braced clips, dip-rebaked *_reload_ads.skc that
differ from the ones in the shipped tex pak, e.g. ppsh_reload_ads 9f98e1ae vs shipped 3f1d8b3f).

Next agent: find which of those pieces make the ADS clip engage (CoopAdsClipFitsHeldGun / CG_AimingDownSights /
Anim_NumForName in cg_viewmodelanim.c ~l.950; the harness aims with +button13), commit them, re-verify with logcheck
on the shipped cgame, then ship via the fixes pak using these files as the starting point.
