"""joinflood fix E2 (server exe): bound the reliable commands IN FLIGHT to a remote client by BYTES, not only by count.

Every unacknowledged server command is re-sent in every snapshot (SV_UpdateServerCommandsToClient). With 256 in
flight a snapshot measured 21.5 KB (a1: after the progression merge, 318 seta + 5 coopsave) = 17 fragments of 1300
bytes, re-sent whole every 25 ms until the client acks - one lost fragment loses the whole snapshot, and a client
that cannot keep up never acks, so the backlog (and the snapshot) only grows. Now a non-loopback client gets at most
sv_cmdParkBytes (default 2400 = <= 2 fragments) of commands in flight; the rest waits in the existing park (FIFO,
nothing dropped, order exact) and is fed in as acks arrive - one window per round trip. A single command larger than
the window still goes out alone. The listen host's own (loopback) client is exempt - unchanged.

    python -I patch_parkbytes.py <engine worktree>
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


edit('code/server/sv_init.c', '\tsv_cmdPark = Cvar_Get ("sv_cmdPark", "1", 0);',
     '\tsv_cmdPark = Cvar_Get ("sv_cmdPark", "1", 0);\n'
     '\tsv_cmdParkBytes = Cvar_Get ("sv_cmdParkBytes", "2400", 0);\t// HZM coop [joinflood bug-3910] 0 = count window only')
edit('code/server/server.h', 'extern\tcvar_t\t*sv_cmdPark;',
     'extern\tcvar_t\t*sv_cmdPark;\nextern\tcvar_t\t*sv_cmdParkBytes;')
edit('code/server/sv_main.c', 'cvar_t\t*sv_cmdPark;',
     'cvar_t\t*sv_cmdParkBytes;\t\t// HZM coop [joinflood bug-3910] max bytes of reliable commands in flight to a remote client\n'
     'cvar_t\t*sv_cmdPark;')

edit('code/server/sv_main.c', r'''/*
======================
SV_ParkDrain
''', r'''/*
======================
SV_ParkWindowFull

HZM coop [joinflood 2026-10-14, bug-3910] the in-flight window, by count (SV_PARK_WINDOW) and, for a remote client,
by bytes (sv_cmdParkBytes): every unacknowledged command rides in every snapshot, so the bytes in flight ARE the
snapshot's overhead. Over ~1300 bytes a snapshot fragments; at 256 commands it was 17 fragments, re-sent whole
every frame until acked. A command that alone exceeds the window is still let out when nothing else is in flight.
======================
*/
static qboolean SV_ParkWindowFull( client_t *client, int addLen ) {
	int inflight = client->reliableSequence - client->reliableAcknowledge;
	int limit, bytes, i;

	if ( inflight >= SV_PARK_WINDOW ) {
		return qtrue;
	}
	if ( inflight <= 0 || !sv_cmdParkBytes || sv_cmdParkBytes->integer <= 0
		|| client->netchan.remoteAddress.type == NA_LOOPBACK || client->netchan.remoteAddress.type == NA_BOT ) {
		return qfalse;
	}
	limit = sv_cmdParkBytes->integer;
	bytes = addLen + 6;
	for ( i = client->reliableAcknowledge + 1 ; i <= client->reliableSequence ; i++ ) {
		bytes += (int)strlen( client->reliableCommands[ i & ( MAX_RELIABLE_COMMANDS - 1 ) ] ) + 6;
		if ( bytes > limit ) {
			return qtrue;
		}
	}
	return qfalse;
}

/*
======================
SV_ParkDrain
''')
edit('code/server/sv_main.c',
     '''	while ( pk->head && client->reliableSequence - client->reliableAcknowledge < SV_PARK_WINDOW ) {''',
     '''	while ( pk->head && !SV_ParkWindowFull( client, (int)strlen( pk->head->cmd ) ) ) {''')
edit('code/server/sv_main.c', '''		&& ( pk->head || ( sv_cmdPark->integer
			&& client->reliableSequence - client->reliableAcknowledge >= SV_PARK_WINDOW ) ) ) {''',
     '''		&& ( pk->head || ( sv_cmdPark->integer
			&& SV_ParkWindowFull( client, (int)strlen( cmd ) ) ) ) ) {''')
print('park bytes window patched')
