"""The settled aim's SWAY ENVELOPE - the reference an aimed reload is judged against AS PLAYED (aim sway + breath on).

Standard since 2026-10-13 (user): a reload may add under 2 % of the centre box (the middle 20 % of the screen) BEYOND
everything the settled aim itself covers through a whole sway / breath period, in every frame. Sway and breath move
the whole first-person rig, so a gun that sits close to the eye covers a different part of the box from one moment to
the next with nothing happening (Thompson: the settled aim alone reads up to 6 % against a six-frame mask of itself).

This is the heavy lane's measure (heavy/tools/boxeng.py --sway, written there inline: the `env` / `envg` / `exe` lines)
copied into ONE function so that every lane computes the same thing; boxeng.py itself is unchanged. The SMG lane's
reloadbox.py calls it. Capture side: a tail of one whole sway period (5.7 s = 357 game frames) of the settled aim after
the reload, sparsely captured (heavy: run_h.py --tail 360:4; SMG: run_smg.py --tail 360:4, mark `DEMO settle`).

    extra, cover = envelope_extra(mask_of, grow, clip_frames, settled_frames, aim_mask, also=None)

mask_of(i)      box cover of capture frame i (bool array; the frame against the model-less reference shifted to that
                frame's own background - smg/tools/reloadbox.py mask + make_shifter)
grow(m)         the mask grown as the lane's aim mask is (reloadbox.grow: 6 px)
clip_frames     capture frames of the reload
settled_frames  capture frames of the settled aim after it (the tail)
aim_mask        the aim's own mask, NOT grown (mean of the six settled frames before the lower > 0.3)
also            another un-grown mask that belongs to the reference (an emptied open-bolt gun's dry pose)
Returns the per-frame share of the box covered beyond the grown envelope, and the share the envelope itself covers.
"""
import numpy as np


def envelope(mask_of, settled_frames, aim_mask, also=None):
    env = np.array(aim_mask, dtype=bool).copy()
    for i in settled_frames:
        env |= mask_of(i)
    if also is not None:
        env |= also
    return env


def envelope_extra(mask_of, grow, clip_frames, settled_frames, aim_mask, also=None):
    env = envelope(mask_of, settled_frames, aim_mask, also)
    envg = grow(env)
    return [float((mask_of(i) & ~envg).mean()) for i in clip_frames], float(env.mean())
