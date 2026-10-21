import json
p = 'C:/mohaa-coop-dev/docs/tools/objx_points.json'
d = json.load(open(p, encoding='utf-8'))
d['m1l2b'] = {
 "note": "Sabotage the Motorpool. Radios replace the vanilla radio1/radio2 sound sources; a fuel depot in the southern courtyard; a hold at the exfiltration approach. Floors via droptofloor except the radios (on tables).",
 "objectives": [
  {"id": "radios", "type": "radio", "line": 3, "text": "Silence the two motorpool radio sets", "done": "The motorpool radios are silent", "when": "auto", "call_gap": 70,
   "items": [
    {"kind": "radio", "model": "models/miscobj/radio_military.tik", "pos": [1602.15, -2905.84, -131.77], "yaw": 90, "scale": 1.8, "nodrop": 1, "ref": "radio1", "loop": "m1l2b_radio1", "label": "the radio set"},
    {"kind": "radio", "model": "models/miscobj/radio_military.tik", "pos": [1956.15, -3741.84, -137.77], "yaw": 180, "scale": 1.8, "nodrop": 1, "ref": "radio2", "loop": "m1l2b_radio2", "label": "the radio set"}]},
  {"id": "fuel", "type": "charge", "line": 4, "text": "Blow the motorpool fuel depot", "done": "The fuel depot is destroyed",
   "when": "near", "near": {"pos": [1500.0, -1500.0, -304.0], "r": 700}, "fuse": 12, "chain": 1, "call_gap": 45,
   "items": [
    {"kind": "kit", "model": "models/static/exp_crate1.tik", "pos": [1016.0, -704.0, -304.0], "yaw": 0, "label": "the demolition charges"},
    {"kind": "target", "model": "models/static/fuel_tanks.tik", "aux": "models/static/fuel_tanks_d.tik", "pos": [1584.0, -1584.0, -304.0], "yaw": 0, "scale": 0.32, "label": "the fuel tanks"},
    {"kind": "target", "model": "models/static/fuel_tanks.tik", "aux": "models/static/fuel_tanks_d.tik", "pos": [1760.0, -1584.0, -304.0], "yaw": 90, "scale": 0.32, "label": "the fuel tanks"},
    {"kind": "target", "model": "models/static/fuel_tanks.tik", "aux": "models/static/fuel_tanks_d.tik", "pos": [1232.0, -1696.0, -304.0], "yaw": 45, "scale": 0.32, "label": "the fuel tanks"}],
   "zone": {"pos": [1500.0, -1650.0, -304.0], "r": 600, "name": "the motorpool courtyard", "spawns": []}},
  {"id": "exfil", "type": "hold", "line": 5, "text": "Hold the yard until the demolition fuses burn down", "done": "The fuses have burned down - the way out is clear", "when": "after", "arg": "radios", "secs": 150,
   "zone": {"pos": [1956.0, -3400.0, -240.0], "r": 420, "name": "the radio yard", "spawns": []}}
 ]}
json.dump(d, open(p, 'w', encoding='utf-8'), indent=1)
