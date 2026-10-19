/*
 * hzm_cbt.c - the in-process guard for BACKGROUND TEST CLIENTS (docs/proposals/test_window_policy_2026-09-27, bug-3147).
 *
 * harness_window.py loads this DLL and installs HzmCbtProc as a WH_CBT hook on the TEST CLIENT'S MAIN THREAD only
 * (never desktop-wide: a global hook would inject into the user's game). Windows then runs it inside the test client,
 * in the thread that owns the game window, synchronously - so unlike anything a watcher in another process can do,
 * it acts BEFORE the event takes effect:
 *
 *   HCBT_CREATEWND  every top-level window is created ON THE TEST DISPLAY (CREATESTRUCT x/y rewritten, centred in
 *                   HZM_CBT_RECT="l,t,r,b"): no window is ever positioned on the user's screen, so there is no
 *                   placement race to lose (the engine centres new windows on the primary, bug-3112).
 *   HCBT_ACTIVATE   returns 1 = the activation is PREVENTED. Whatever asks for it - SW_SHOW, SetForegroundWindow,
 *                   SDL_RaiseWindow, a user's click landing on the window, or Windows handing activation to the
 *                   next window in the z-order when the foreground window closes or minimizes - the test window
 *                   can never become active, so it can never take the foreground from the user's game.
 *
 * Optional HZM_CBT_LOG=<path> appends one line per decision. Build: harness_window.ensure_cbt_dll() (MSVC, /MT).
 */
#define WIN32_LEAN_AND_MEAN
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <stdarg.h>
#include <stdio.h>

static RECT g_rect;
static int g_have = -1;
static HANDLE g_log = INVALID_HANDLE_VALUE;

static void cbt_config( void )
{
	char buf[ MAX_PATH ];

	if( g_have >= 0 )
		return;
	g_have = 0;
	if( GetEnvironmentVariableA( "HZM_CBT_RECT", buf, sizeof( buf ) ) &&
		sscanf( buf, "%ld,%ld,%ld,%ld", &g_rect.left, &g_rect.top, &g_rect.right, &g_rect.bottom ) == 4 &&
		g_rect.right > g_rect.left && g_rect.bottom > g_rect.top )
		g_have = 1;
	if( GetEnvironmentVariableA( "HZM_CBT_LOG", buf, sizeof( buf ) ) )
		g_log = CreateFileA( buf, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_ALWAYS, 0, NULL );
}

static void cbt_log( const char *fmt, ... )
{
	char b[ 320 ];
	int n;
	DWORD w;
	va_list ap;

	if( g_log == INVALID_HANDLE_VALUE )
		return;
	n = sprintf( b, "%lu ", GetTickCount( ) );
	va_start( ap, fmt );
	n += _vsnprintf( b + n, sizeof( b ) - n - 2, fmt, ap );
	va_end( ap );
	if( n < 0 || n > (int)sizeof( b ) - 2 )
		n = (int)sizeof( b ) - 2;
	b[ n++ ] = '\n';
	WriteFile( g_log, b, (DWORD)n, &w, NULL );
}

__declspec( dllexport ) LRESULT CALLBACK HzmCbtProc( int code, WPARAM wp, LPARAM lp )
{
	cbt_config( );

	if( code == HCBT_ACTIVATE )
	{
		char cls[ 64 ] = "";
		GetClassNameA( (HWND)wp, cls, sizeof( cls ) );
		cbt_log( "BLOCK_ACTIVATE hwnd=%p class=%s", (void *)wp, cls );
		return 1;   // prevent it
	}

	if( code == HCBT_CREATEWND && g_have == 1 )
	{
		CBT_CREATEWNDW *cw = (CBT_CREATEWNDW *)lp;
		CREATESTRUCTW *cs = cw->lpcs;

		if( !( cs->style & WS_CHILD ) && cs->hwndParent == NULL && cs->cx > 0 && cs->cy > 0 &&
			cs->x != CW_USEDEFAULT )
		{
			int dw = g_rect.right - g_rect.left, dh = g_rect.bottom - g_rect.top;
			int x = cs->cx <= dw ? g_rect.left + ( dw - cs->cx ) / 2 : g_rect.left;
			int y = cs->cy <= dh ? g_rect.top + ( dh - cs->cy ) / 2 : g_rect.top;
			char cls[ 64 ] = "";
			GetClassNameA( (HWND)wp, cls, sizeof( cls ) );
			cbt_log( "CREATE hwnd=%p class=%s %d,%d %dx%d -> %d,%d", (void *)wp, cls, cs->x, cs->y, cs->cx, cs->cy, x, y );
			cs->x = x;
			cs->y = y;
		}
	}
	return CallNextHookEx( NULL, code, wp, lp );
}

BOOL WINAPI DllMain( HINSTANCE h, DWORD reason, LPVOID r )
{
	(void)h; (void)r;
	if( reason == DLL_PROCESS_DETACH && g_log != INVALID_HANDLE_VALUE )
		CloseHandle( g_log );
	return TRUE;
}
