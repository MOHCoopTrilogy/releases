"""Client-side cl_netProbe (joinflood 2026-10-14, test tool): when a client->server packet's unacknowledged
reliable commands reach 1000 bytes, print (at most once a second) every one of them with its length. Those packets
are the ones that end up fragmented - and the client exe only ever sends the first fragment (bug-3905).

    python -I patch_clprobe.py <engine worktree>
"""
import os, sys
ROOT = sys.argv[1]
p = os.path.join(ROOT, 'code', 'client', 'cl_input.cpp')
s = open(p, 'rb').read().decode('latin-1')
crlf = '\r\n' in s
s = s.replace('\r\n', '\n')
old = '''	// write any unacknowledged clientCommands
	for ( i = clc.reliableAcknowledge + 1 ; i <= clc.reliableSequence ; i++ ) {
		MSG_WriteByte( &buf, clc_clientCommand );
		MSG_WriteLong( &buf, i );
		MSG_WriteScrambledString( &buf, clc.reliableCommands[ i & (MAX_RELIABLE_COMMANDS-1) ] );
	}
'''
new = old + r'''	// HZM [joinflood 2026-10-14] cl_netProbe: who fills a client packet
	{
		static cvar_t *cl_netProbe;
		static int s_lastProbe;
		int bytes = 0;
		if ( !cl_netProbe ) {
			cl_netProbe = Cvar_Get( "cl_netProbe", "0", 0 );
		}
		if ( cl_netProbe->integer ) {
			for ( i = clc.reliableAcknowledge + 1 ; i <= clc.reliableSequence ; i++ ) {
				bytes += (int)strlen( clc.reliableCommands[ i & (MAX_RELIABLE_COMMANDS-1) ] ) + 6;
			}
			if ( bytes >= 1000 && cls.realtime - s_lastProbe >= 1000 ) {
				s_lastProbe = cls.realtime;
				Com_Printf( "^~^~^ CLNET unacked=%d bytes=%d state=%d srvcmd=%d\n", clc.reliableSequence - clc.reliableAcknowledge,
					bytes, (int)clc.state, clc.serverCommandSequence );
				for ( i = clc.reliableAcknowledge + 1 ; i <= clc.reliableSequence ; i++ ) {
					const char *c = clc.reliableCommands[ i & (MAX_RELIABLE_COMMANDS-1) ];
					Com_Printf( "^~^~^ CLNET   #%d len=%d %.70s\n", i, (int)strlen( c ), c );
				}
			}
		}
	}
'''
assert s.count(old) == 1
s = s.replace(old, new)
if crlf:
    s = s.replace('\n', '\r\n')
open(p, 'wb').write(s.encode('latin-1'))
print('cl_netProbe patched')
