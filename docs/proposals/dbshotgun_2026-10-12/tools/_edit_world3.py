"""one-off edit of tools/dbs_world.scr after run w1:
 * the test AI is killed by a damage event whose ATTACKER is the player (the mod's pain handler ignores an attacker-less
   hit - global/bullethit.scr passes NULL - and keeps the actor's health in a 5000 buffer; run w1: still alive);
 * the player is made invulnerable again right before the AI is switched on (the mod's spawn protection ends with
   `takedamage`; run w1: the AI shot the player dead with the double barrel);
 * mode 2 starts at the AI part (A / E / B are proven by run w1): `set coop_dbsW 2`.
"""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dbs_world.scr')
s = open(p, encoding='latin-1').read()
assert 'local.mode == "1"' not in s

a = '\t// ---- A. the death drop, seen; touched by a player who does not hold the gun\n'
b = '\t// ---- D. an AI armed with it through the mod\'s AI weapon path, killed: the Use prompt with our picture; TAP = the gun\n'
i, j = s.index(a), s.index(b)
s = (s[:i] + '\tif( local.mode == "1" ){\n' + s[i:j] + '\t}\n'
     '\tif( local.mode != "1" ){\n\t\t//mode 2: straight to the AI part, with a pump gun in the kit (what part B leaves the player with)\n'
     '\t\tlocal.p give level.dbsw_pump\n\t\twait 1.5\n\t}\n' + s[j:])

a = '\tsetcvar "g_ai" "1"\n'
assert s.count(a) == 1
s = s.replace(a, '\tlocal.p nodamage\n' + a)

a = '\tlocal.g exec global/bullethit.scr ( 0 0 250 ) 5000 0 1\n\twait 4.5\n'
assert s.count(a) == 1
s = s.replace(a, '''	//a bullet hit whose attacker is the player: the event a real shot makes (aihandler.scr::actorPainHandler)
	local.k = 0
	while( local.k < 5 && local.g != NULL && ( isalive local.g ) ){
		local.g damage local.p 5000 local.p ( 0 0 0 ) local.fw ( 0 0 0 ) 0 16 17 3
		local.k++
		wait 0.5
	}
	println ( "^~^~^ DBSW ai hits=" + local.k )
	wait 4.5
''')
# running-depth brace scan
d = 0
for n, l in enumerate(s.split('\n')):
    c = l.split('//')[0]
    d += c.count('{') - c.count('}')
    assert d >= 0, (n + 1, l)
assert d == 0
assert '(-' not in s
open(p, 'w', encoding='latin-1', newline='\n').write(s)
print('dbs_world.scr edited')
