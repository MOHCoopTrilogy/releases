"""joinflood stage 2b (bug-3912): give the UDP sockets room for a burst. A map's gamestate goes out as one message of
~66+ KB = ~51 fragments sent back to back (the server's rate gate is off: sv_hzmClientRate 10 M); the Windows default
socket receive buffer is 64 KB, so the tail of the burst is dropped, the client can never complete the gamestate,
acks the small message after it, the server sees "gamestate dropped" and resends the whole burst - 20 times a second,
forever (harness p1: CS_PRIMED for the whole mission, 1020 fragments/s received, 0 gamestates completed).

    python -I patch_sockbuf.py <engine worktree>
"""
import os, sys

ROOT = sys.argv[1]
p = os.path.join(ROOT, 'code', 'qcommon', 'net_ip.c')
s = open(p, 'rb').read().decode('latin-1')
crlf = '\r\n' in s
s = s.replace('\r\n', '\n')

helper = r'''/*
====================
NET_SetSocketBuffers

HZM coop [joinflood 2026-10-14, bug-3912] a map's gamestate arrives as ~50 back-to-back 1300-byte fragments; the
Windows default 64 KB receive buffer drops the tail, the gamestate never completes and the server resends it
forever. 4 MB each way (the OS may grant less; the result is printed once per socket).
====================
*/
static void NET_SetSocketBuffers( SOCKET s, const char *what ) {
	int			want = 4 * 1024 * 1024;
	int			got = 0, gotSnd = 0;
	socklen_t	len = sizeof( got );

	if ( setsockopt( s, SOL_SOCKET, SO_RCVBUF, (char *)&want, sizeof( want ) ) == SOCKET_ERROR ) {
		Com_Printf( "WARNING: %s: setsockopt SO_RCVBUF: %s\n", what, NET_ErrorString() );
	}
	if ( setsockopt( s, SOL_SOCKET, SO_SNDBUF, (char *)&want, sizeof( want ) ) == SOCKET_ERROR ) {
		Com_Printf( "WARNING: %s: setsockopt SO_SNDBUF: %s\n", what, NET_ErrorString() );
	}
	getsockopt( s, SOL_SOCKET, SO_RCVBUF, (char *)&got, &len );
	len = sizeof( gotSnd );
	getsockopt( s, SOL_SOCKET, SO_SNDBUF, (char *)&gotSnd, &len );
	Com_Printf( "%s: socket buffers receive %d KB, send %d KB\n", what, got / 1024, gotSnd / 1024 );
}

'''
anchor = 'SOCKET NET_IPSocket('
assert s.count(anchor) == 1
i = s.index(anchor)
j = s.rfind('/*', 0, i)  # put the helper before NET_IPSocket's comment block
s = s[:j] + helper + s[j:]

old4 = '''	// make it broadcast capable
	if( setsockopt( newsocket, SOL_SOCKET, SO_BROADCAST, (char *) &i, sizeof(i) ) == SOCKET_ERROR ) {
		Com_Printf( "WARNING: NET_IPSocket: setsockopt SO_BROADCAST: %s\\n", NET_ErrorString() );
	}
'''
assert s.count(old4) == 1, s.count(old4)
s = s.replace(old4, old4 + '''	NET_SetSocketBuffers( newsocket, "NET_IPSocket" ); // HZM coop [bug-3912]
''')

old6 = '''	if( ioctlsocket( newsocket, FIONBIO, &_true ) == SOCKET_ERROR ) {
		Com_Printf( "WARNING: NET_IP6Socket: ioctl FIONBIO: %s\\n", NET_ErrorString() );'''
assert s.count(old6) == 1
k = s.index(old6)
end = s.index('\n\t}\n', k) + len('\n\t}\n')
s = s[:end] + '''	NET_SetSocketBuffers( newsocket, "NET_IP6Socket" ); // HZM coop [bug-3912]
''' + s[end:]
if crlf:
    s = s.replace('\n', '\r\n')
open(p, 'wb').write(s.encode('latin-1'))
print('socket buffers patched')
