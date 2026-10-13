# applied by build_scr.py: a trooper the path graph cannot move (he came down in a map cell without a pathnode) walks
# out in a straight line over traced ground instead of standing there until the rescue teleport.


def apply(out):
    out = sub(out, """						if( local.slot != NIL ){
							local.ds = waitthread flatDist local.a.origin local.slot
							if( local.ds > 120 ){
								local.a.movedoneradius = 64
								local.a runto local.slot
							}
						}
""", """						if( local.slot != NIL ){
							local.ds = waitthread flatDist local.a.origin local.slot
							if( local.ds > 120 ){
								local.a.movedoneradius = 64
								// A man standing in a map cell that holds no pathnode has no path to anywhere
								// (PathSearch::NearestStartNode looks in his own 256u cell only): that is the
								// trooper who came down in a bad spot and never moves. Two orders that got him
								// nowhere and he walks out in a straight line, as far as the ground was traced.
								local.so = local.a.coop_psqOrdO
								local.a.coop_psqOrdO = local.a.origin
								if( local.so != NIL ){
									if( vector_length( local.a.origin - local.so ) < 24 && local.a.pathdist == 0 ){
										local.a.coop_psqNoPath++
									} else {
										local.a.coop_psqNoPath = 0
									}
								}
								if( local.a.coop_psqNoPath >= 2 ){
									local.a.coop_psqNoPath = 0
									thread walkOut local.a local.slot
								} else {
									local.a runto local.slot
								}
							}
						}
""")
    out = sub(out, """	self.coop_psqNadeT = 0
""", """	self.coop_psqNadeT = 0
	self.coop_psqNoPath = 0
""")
    out = out.rstrip("\\n") + """


// (see the brain, FOLLOW) a straight walk toward local.to for a man the path graph cannot move: all
// the way when the line is good (mgLine: his hull, and ground every 32u), else as far as it is in
// steps of 96u, up to 480u. The enemy think is off for the walk and always comes back on.
walkOut local.a local.to:{
	if( !( waitthread usable local.a ) ){ end }
	local.a.coop_psqBusy = 1
	local.a.enableEnemy = 0
	local.goal = NIL
	if( waitthread mgLine local.a.origin local.to ){
		local.goal = local.to
	} else {
		local.v = local.to - local.a.origin
		local.v[2] = 0
		local.len = vector_length local.v
		if( local.len > 1 ){
			local.dir = vector_normalize local.v
			for( local.r = 96; local.r <= 480; local.r = local.r + 96 ){
				if( local.r >= local.len ){ break }
				local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.a.origin + ( vector_scale local.dir local.r ) + ( 0 0 40 ) )
				if( local.g == NIL ){ break }
				if( !( waitthread mgLine local.a.origin local.g ) ){ break }
				local.goal = local.g
			}
		}
	}
	local.left = 0 - 1
	if( local.goal != NIL ){ local.left = waitthread mgLeg local.a local.goal 1 40 8 }
	if( local.a == NULL ){ end }
	if( isAlive local.a ){
		local.a.enableEnemy = 1
		local.a forceactivate
		local.a resetleash
	}
	local.a.coop_psqBusy = 0
	waitthread dbg ( "walkout k=" + local.a.coop_psqK + " goal=" + ( local.goal != NIL ) + " left=" + local.left )
}end
"""
    return out
