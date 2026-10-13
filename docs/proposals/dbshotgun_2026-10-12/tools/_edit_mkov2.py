"""one-off editor (2026-10-13 b): mkov_dbs.py test hooks - the test AI is killed with `kill` (the 5000 damage event did
not kill it, run a2), the player can be made mortal again (the harness `give` sets nodamage: `kill` then does nothing,
run a2). Already applied."""
import sys
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
if 'coop_dbsMortal' in s:
    print('already applied'); sys.exit(0)
old = "    '\\t\\t\\t\\t\\tlevel.coop_dbsAI damage local.p 5000 local.p level.coop_dbsAI.origin ( 0 0 0 ) ( 0 0 1 ) 0 0 18 5\\n'\n"
assert s.count(old) == 1, s.count(old)
s = s.replace(old, "    '\\t\\t\\t\\t\\tlevel.coop_dbsAI takedamage\\n'\n    '\\t\\t\\t\\t\\tlevel.coop_dbsAI kill\\n'\n")
anchor = "    '\\t\\tlocal.a = getcvar( \"coop_dbsAI\" )\\n'\n"
assert s.count(anchor) == 1
mortal = ("    '\\t\\tlocal.m = getcvar( \"coop_dbsMortal\" )\\n'\n"
          "    '\\t\\tif( local.m != \"\" && local.m != local.lastM && $player != NULL && $player.size >= 1 ){\\n'\n"
          "    '\\t\\t\\tlocal.lastM = local.m\\n'\n"
          "    '\\t\\t\\t$player[1] takedamage\\n'\n"
          "    '\\t\\t\\tprintln( \"^~^~^ DBSMORTAL \" + local.m )\\n'\n"
          "    '\\t\\t}\\n'\n")
s = s.replace(anchor, mortal + anchor)
b = "\\tlocal.lastA = \"\"\\n')\n"
assert s.count(b) == 1
s = s.replace(b, "\\tlocal.lastA = \"\"\\n\\tlocal.lastM = \"\"\\n')\n")
open(p, 'w', encoding='utf-8', newline='').write(s)
print('edited', p)
