"""models.py <label> : spawn candidate props in a row in the south hall and screenshot them. Inside a harness_turn turn."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
ROW1 = ["models/miscobj/crane.tik", "models/miscobj/subcrane.tik", "models/miscobj/crane_grey.tik", "models/static/Af_P_Crane.tik",
        "models/items/torpedo.tik", "models/static/static_torpedo.tik"]
ROW2 = ["models/animate/alarmswitch.tik", "models/animate/electrical_switch_pulse.tik", "models/animate/trainswitch.tik",
        "models/miscobj/radio_military.tik", "models/miscobj/radio_military_pulse.tik", "models/static/exp_crate1.tik",
        "models/static/nazi_crate.tik", "models/static/static_cablespool_full.tik", "models/coop_build/shape_post_iron.tik"]
MODELS = ["models/items/torpedo.tik","models/static/static_torpedo.tik","models/static/exp_crate1.tik","models/static/exp_crate2.tik","models/static/exp_crate3.tik",
  "models/static/fragcrate1.tik","models/static/30cal_crate.tik","models/static/50cal_crate.tik","models/static/88shell.tik","models/static/nazi_crate.tik",
  "models/static/supplydropcrate.tik","models/miscobj/crate_carry.tik","models/miscobj/ammocrate.tik","models/coop_build/shape_cube_crate.tik",
  "models/coop_build/box_crate_explosive.tik","models/coop_build/box_crate_nazi.tik","models/coop_build/box_crate_reinforced.tik","models/coop_build/box_foodcrate1.tik",
  "models/static/fuel_tanks.tik","models/animate/fx_cratedebris_0.tik"]
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c")
    G.cmd("god")
    time.sleep(2)
    G.cmd("tp", x=748, y=-4050, z=-505, yaw=90, pitch=-20)
    for i, m in enumerate(MODELS):
        G.cmd("mkmodel", s=m, x=748, y=-3900, z=-300, yaw=0, k=0)
        time.sleep(0.5)
        R.step(["screenshotJPEG mdl_%02d" % i, "wait 250"], timeout=20)
        log("model", i, m)
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)
