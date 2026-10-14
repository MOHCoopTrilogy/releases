"""Adds the sv_netProbe instrument (joinflood 2026-10-14) to an engine tree: once a second, per remote client,
reliable commands in flight / parked (current and max), snapshots sent (count, mean/max bytes, how many were over
FRAGMENT_SIZE), snapshots skipped by the fragment and rate gates, client packets received (complete / fragmented)
and the age of the last complete client packet. Silent unless sv_netProbe 1.

    python -I patch_netprobe.py <engine worktree>
"""
import os, sys

ROOT = sys.argv[1]


def edit(rel, old, new, count=1):
    p = os.path.join(ROOT, rel)
    s = open(p, 'rb').read().decode('latin-1')
    crlf = '\r\n' in s
    s = s.replace('\r\n', '\n')
    assert s.count(old) == count, (rel, s.count(old), old[:70])
    s = s.replace(old, new)
    if crlf:
        s = s.replace('\n', '\r\n')
    open(p, 'wb').write(s.encode('latin-1'))


# cvar
edit('code/server/server.h', 'extern\tcvar_t\t*sv_lagProbe;',
     'extern\tcvar_t\t*sv_netProbe;\t// HZM [joinflood 2026-10-14]: per-client reliable/snapshot/packet probe\n'
     'void SV_NetProbe_Snap( client_t *cl, int bytes );\n'
     'void SV_NetProbe_Skip( client_t *cl, int why );\n'
     'extern\tcvar_t\t*sv_lagProbe;')
edit('code/server/sv_init.c', '\tsv_lagProbe = Cvar_Get ("sv_lagProbe", "0", 0);',
     '\tsv_netProbe = Cvar_Get ("sv_netProbe", "0", 0);\t// HZM [joinflood]: per-client net probe\n'
     '\tsv_lagProbe = Cvar_Get ("sv_lagProbe", "0", 0);')
edit('code/server/sv_main.c', 'cvar_t\t*sv_lagProbe;',
     'cvar_t\t*sv_netProbe;\ncvar_t\t*sv_lagProbe;')

# stats + hooks, placed before SV_PacketEvent
edit('code/server/sv_main.c', 'void SV_PacketEvent( netadr_t from, msg_t *msg ) {',
r'''/*
======================
HZM [joinflood 2026-10-14] NET PROBE (sv_netProbe 1)
======================
*/
typedef struct {
	int snaps, snapBytes, snapMax, snapFrag, skipFrag, skipRate;
	int inPk, inFragPk, maxInflight, maxParked;
} svNetProbe_t;
static svNetProbe_t sv_np[MAX_CLIENTS];

static svNetProbe_t *SV_NP( client_t *cl ) {
	int n = (int)( cl - svs.clients );
	if ( !sv_netProbe || !sv_netProbe->integer || !svs.clients || n < 0 || n >= MAX_CLIENTS ) {
		return NULL;
	}
	return &sv_np[n];
}

void SV_NetProbe_Snap( client_t *cl, int bytes ) {
	svNetProbe_t *p = SV_NP( cl );
	if ( !p ) {
		return;
	}
	p->snaps++;
	p->snapBytes += bytes;
	if ( bytes > p->snapMax ) {
		p->snapMax = bytes;
	}
	if ( cl->netchan.remoteAddress.type != NA_LOOPBACK && bytes >= 1300 ) {
		p->snapFrag++;
	}
}

void SV_NetProbe_Skip( client_t *cl, int why ) {
	svNetProbe_t *p = SV_NP( cl );
	if ( !p ) {
		return;
	}
	if ( why ) {
		p->skipRate++;
	} else {
		p->skipFrag++;
	}
}

static void SV_NetProbe_Frame( void ) {
	static int s_npStart = 0;
	int i;

	if ( !sv_netProbe || !sv_netProbe->integer || !svs.clients ) {
		return;
	}
	for ( i = 0 ; i < sv_maxclients->integer && i < MAX_CLIENTS ; i++ ) {
		client_t *cl = &svs.clients[i];
		svPark_t *pk = &sv_park[i];
		int inflight;
		if ( cl->state < CS_CONNECTED || cl->netchan.remoteAddress.type == NA_BOT ) {
			continue;
		}
		inflight = cl->reliableSequence - cl->reliableAcknowledge;
		if ( inflight > sv_np[i].maxInflight ) {
			sv_np[i].maxInflight = inflight;
		}
		if ( pk->count > sv_np[i].maxParked ) {
			sv_np[i].maxParked = pk->count;
		}
	}
	if ( svs.time - s_npStart < 1000 ) {
		return;
	}
	s_npStart = svs.time;
	for ( i = 0 ; i < sv_maxclients->integer && i < MAX_CLIENTS ; i++ ) {
		client_t *cl = &svs.clients[i];
		svNetProbe_t *p = &sv_np[i];
		if ( cl->state < CS_CONNECTED || cl->netchan.remoteAddress.type == NA_BOT
			|| cl->netchan.remoteAddress.type == NA_LOOPBACK ) {
			Com_Memset( p, 0, sizeof( *p ) );
			continue;
		}
		Com_Printf( "^~^~^ SVNET cl=%d st=%d inflight=%d max=%d parked=%d max=%d snaps=%d avg=%d max=%d over1300=%d "
			"skipfrag=%d skiprate=%d in=%d infrag=%d lastin=%d ping=%d rate=%d\n",
			i, (int)cl->state, cl->reliableSequence - cl->reliableAcknowledge, p->maxInflight,
			sv_park[i].count, p->maxParked, p->snaps, p->snaps ? p->snapBytes / p->snaps : 0, p->snapMax,
			p->snapFrag, p->skipFrag, p->skipRate, p->inPk, p->inFragPk, svs.time - cl->lastPacketTime,
			cl->ping, cl->rate );
		Com_Memset( p, 0, sizeof( *p ) );
	}
}

void SV_PacketEvent( netadr_t from, msg_t *msg ) {''')

# count incoming packets: fragmented ones and complete processed ones
edit('code/server/sv_main.c', '''		// make sure it is a valid, in sequence packet
		if (SV_Netchan_Process(cl, msg)) {''',
'''		if ( SV_NP( cl ) && msg->cursize >= 4 && ( ( (unsigned int)*(int *)msg->data ) & 0x80000000u ) ) {
			SV_NP( cl )->inFragPk++; // HZM [joinflood] probe
		}
		// make sure it is a valid, in sequence packet
		if (SV_Netchan_Process(cl, msg)) {
			if ( SV_NP( cl ) ) {
				SV_NP( cl )->inPk++; // HZM [joinflood] probe
			}''')

# periodic report next to the lag probe
edit('code/server/sv_main.c', '''	// update ping based on the all received frames
	SV_CalcPings();''', '''	SV_NetProbe_Frame(); // HZM [joinflood 2026-10-14]

	// update ping based on the all received frames
	SV_CalcPings();''')

# snapshot size + skips
edit('code/server/sv_snapshot.c', '''	SV_SendMessageToClient( &msg, client );
}''', '''	SV_NetProbe_Snap( client, msg.cursize ); // HZM [joinflood] probe
	SV_SendMessageToClient( &msg, client );
}''')
edit('code/server/sv_snapshot.c', '''			c->rateDelayed = qtrue;
			continue;		// Drop this snapshot if the packet queue is still full or delta compression will break''',
'''			c->rateDelayed = qtrue;
			SV_NetProbe_Skip( c, 0 ); // HZM [joinflood] probe
			continue;		// Drop this snapshot if the packet queue is still full or delta compression will break''')
edit('code/server/sv_snapshot.c', '''				// Not enough time since last packet passed through the line
				c->rateDelayed = qtrue;
				continue;''', '''				// Not enough time since last packet passed through the line
				c->rateDelayed = qtrue;
				SV_NetProbe_Skip( c, 1 ); // HZM [joinflood] probe
				continue;''')
print('netprobe patched into', ROOT)
