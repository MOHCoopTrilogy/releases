import io, re
p = "C:/mohaa-coop-dev/hzm-mod-smokec/coop_mod/officer.scr"
t = io.open(p, "r", encoding="utf-8", newline="").read()
crlf = "\r\n" in t
a = t.index("// Full ammo for every pool.")
b = t.index("// Health to the coop maximum.")
new = """// Full ammo: every pool the player HAS (an ammo entry exists, getammo >= 0) is topped up to its loadout default - the
// amounts the kit hands out at spawn (measured: rifle 80, smg 120, mg 100, pistol 81). A pool already above the default
// (picked-up ammo) is left alone; a pool the player does not carry is not created.
coop_cache_restock local.player:{
	local.t[1] = "pistol"
	local.t[2] = "rifle"
	local.t[3] = "smg"
	local.t[4] = "mg"
	local.t[5] = "heavy"
	local.t[6] = "grenade"
	local.t[7] = "shotgun"
	local.full[1] = 81
	local.full[2] = 80
	local.full[3] = 120
	local.full[4] = 100
	local.full[5] = 6
	local.full[6] = 4
	local.full[7] = 24
	local.i = 1
	while( local.i <= 7 ){
		local.ty = local.t[local.i]
		local.have = local.player getammo local.ty
		local.fa = local.full[local.i]
		if( local.have >= 0 && local.have < local.fa ){ local.player setammo local.ty local.fa }
		local.i++
	}
}end

"""
if crlf:
    new = new.replace("\n", "\r\n")
t = t[:a] + new + t[b:]
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("ok")
