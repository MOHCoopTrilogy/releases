"""cl_netProbe v2 (joinflood stage 2, test tool): once a second on the client, what came in from the server -
sequenced packets, of which fragments, of which out-of-order/duplicates, complete messages handed to the parser, the
newest message / command sequence, how far the incoming sequence jumped (packets the client never saw) and the
longest gap between two client frames.

    python -I patch_clprobe2.py <engine worktree>
"""
import os, sys
ROOT = sys.argv[1]
p = os.path.join(ROOT, 'code', 'client', 'cl_main.cpp')
s = open(p, 'rb').read().decode('latin-1')
crlf = '\r\n' in s
s = s.replace('\r\n', '\n')

old1 = '''	// HZM coop [bug-3486] duplicated / out-of-order packet: the same test Netchan_Process makes, counted here because its
	// qfalse also covers "a fragment, more to come"
	if ( ( LittleLong( *(int *)msg->data ) & 0x7fffffff ) <= clc.netchan.incomingSequence ) {
		CL_HzmNet( 1, 1 );
	}

	if (!CL_Netchan_Process( &clc.netchan, msg) ) {
		return;		// out of order, duplicated, etc
	}
'''
new1 = r'''	// HZM coop [bug-3486] duplicated / out-of-order packet: the same test Netchan_Process makes, counted here because its
	// qfalse also covers "a fragment, more to come"
	if ( ( LittleLong( *(int *)msg->data ) & 0x7fffffff ) <= clc.netchan.incomingSequence ) {
		CL_HzmNet( 1, 1 );
		CL_NetProbe2( 2, 0 );
	}
	CL_NetProbe2( 0, ( LittleLong( *(int *)msg->data ) & 0x80000000 ) ? 1 : 0 );

	if (!CL_Netchan_Process( &clc.netchan, msg) ) {
		return;		// out of order, duplicated, etc
	}
	CL_NetProbe2( 3, clc.netchan.dropped );
'''
assert s.count(old1) == 1
s = s.replace(old1, new1)

old2 = '''/*
=================
CL_PacketEvent
'''
new2 = r'''/*
=================
CL_NetProbe2

HZM [joinflood stage 2, test tool] cl_netProbe 2: per-second receive counters (see patch_clprobe2.py)
=================
*/
static struct { int pk, frag, ooo, done, jumped, start, frames, worst, lastFrame; } s_np2;

void CL_NetProbe2( int what, int v ) {
	static cvar_t *probe;
	int now = Sys_Milliseconds();
	if ( !probe ) {
		probe = Cvar_Get( "cl_netProbe", "0", 0 );
	}
	if ( probe->integer < 2 ) {
		return;
	}
	switch ( what ) {
	case 0: s_np2.pk++; s_np2.frag += v; break;
	case 2: s_np2.ooo++; break;
	case 3: s_np2.done++; if ( v > 0 ) { s_np2.jumped += v; } break;
	case 4:
		s_np2.frames++;
		if ( s_np2.lastFrame && now - s_np2.lastFrame > s_np2.worst ) {
			s_np2.worst = now - s_np2.lastFrame;
		}
		s_np2.lastFrame = now;
		break;
	}
	if ( now - s_np2.start >= 1000 ) {
		Com_Printf( "^~^~^ CLNET2 pk=%d frag=%d ooo=%d done=%d jumped=%d frames=%d worstgap=%dms msgseq=%d cmdseq=%d "
			"inseq=%d fragseq=%d fraglen=%d unacked=%d\n",
			s_np2.pk, s_np2.frag, s_np2.ooo, s_np2.done, s_np2.jumped, s_np2.frames, s_np2.worst,
			clc.serverMessageSequence, clc.serverCommandSequence, clc.netchan.incomingSequence,
			clc.netchan.fragmentSequence, clc.netchan.fragmentLength, clc.reliableSequence - clc.reliableAcknowledge );
		Com_Memset( &s_np2, 0, sizeof( s_np2 ) );
		s_np2.start = now;
		s_np2.lastFrame = now;
	}
}

/*
=================
CL_PacketEvent
'''
assert s.count(old2) == 1
s = s.replace(old2, new2)

# frame tick
old3 = '''void CL_Frame ( int msec ) {'''
assert s.count(old3) == 1, s.count(old3)
s = s.replace(old3, '''void CL_Frame ( int msec ) {
	CL_NetProbe2( 4, 0 ); // HZM [joinflood stage 2] probe''')
if crlf:
    s = s.replace('\n', '\r\n')
open(p, 'wb').write(s.encode('latin-1'))
print('cl_netProbe 2 patched')
