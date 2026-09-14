/*
 * SEC1 filter self-test.  Compiles the REAL engine tokenizer (real_qshared.inc / real_cmd.inc,
 * pasted verbatim by gen.py from openmohaa-hzm/code/qcommon) against the REAL filter source
 * (real_filter_work.inc = the working-tree patched filter, or real_filter_head.inc = the committed
 * pre-SEC1 filter), so every pass/fail below is produced by the same parser and the same filter code
 * that ship in cgame.dll - not a transcription (docs/TRAPS.md T14).
 *
 * Build twice (see build.bat):
 *   patched:  cl /DIS_PATCHED  ... -> includes real_filter_work.inc; attacks MUST drop.
 *   head:     cl /DFILTER_HEAD ... -> includes real_filter_head.inc; attacks MUST admit (delta arm).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <ctype.h>

typedef int qboolean;
#define qtrue  1
#define qfalse 0
#define MAX_TOKEN_CHARS   1024
#define MAX_STRING_CHARS  2048
#define MAX_STRING_TOKENS 1024
#define BIG_INFO_STRING   8192
#define CVAR_USER_CREATED 0x0080
#define ARRAY_LEN(x)      (sizeof(x) / sizeof(*(x)))
#define ERR_FATAL         0

static void Com_Error(int lvl, const char *fmt, ...)
{
    (void)lvl;
    fprintf(stderr, "FATAL %s\n", fmt);
    exit(2);
}

/* ---- globals COM_ParseExt / the tokenizer need ---- */
char com_token[MAX_TOKEN_CHARS + 1];
int  com_lines = 0;

int   cmd_argc = 0;
char *cmd_argv[MAX_STRING_TOKENS];
char  cmd_tokenized[BIG_INFO_STRING + MAX_STRING_TOKENS];
char  cmd_cmd[BIG_INFO_STRING];

/* real engine helpers (verbatim) */
#include "real_qshared.inc"

/* Com_sprintf shim (the filter uses it to build the append value) */
size_t Com_sprintf(char *dest, size_t size, const char *fmt, ...)
{
    int     ret;
    va_list ap;
    va_start(ap, fmt);
    ret = vsnprintf(dest, size, fmt, ap);
    va_end(ap);
    return (size_t)ret;
}

/* real engine tokenizer + arg join (verbatim), used by the differential arm */
#include "real_cmd.inc"

static const char *Cmd_Argv(int i)
{
    return (i >= 0 && i < cmd_argc) ? cmd_argv[i] : "";
}
static int Cmd_Argc(void)
{
    return cmd_argc;
}

/* ---- cvar + cgi shims the filter links against ---- */
typedef struct cvar_s {
    char name[64];
    char string[512];
    int  flags;
    int  integer;
} cvar_t;

#define MAXCV 512
static cvar_t cvtab[MAXCV];
static int    ncv = 0;

static cvar_t *setcv(const char *n, const char *v, int f)
{
    int i;
    for (i = 0; i < ncv; i++) {
        if (!Q_stricmp(cvtab[i].name, n)) {
            Q_strncpyz(cvtab[i].string, v, sizeof(cvtab[i].string));
            cvtab[i].flags   = f;
            cvtab[i].integer = atoi(v);
            return &cvtab[i];
        }
    }
    Q_strncpyz(cvtab[ncv].name, n, sizeof(cvtab[0].name));
    Q_strncpyz(cvtab[ncv].string, v, sizeof(cvtab[0].string));
    cvtab[ncv].flags   = f;
    cvtab[ncv].integer = atoi(v);
    return &cvtab[ncv++];
}

static cvar_t *my_Cvar_Find(const char *n)
{
    int i;
    for (i = 0; i < ncv; i++) {
        if (!Q_stricmp(cvtab[i].name, n)) {
            return &cvtab[i];
        }
    }
    return NULL;
}
static cvar_t *my_Cvar_Get(const char *n, const char *v, int f)
{
    cvar_t *c = my_Cvar_Find(n);
    if (c) {
        return c;
    }
    return setcv(n, v, f);
}

/* Printf shim that RECORDS output, so each must-drop case can assert its exact COVC VDROP reason. */
static char g_log[4096];
static void my_Printf(const char *fmt, ...)
{
    char    buf[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    strncat(g_log, buf, sizeof(g_log) - strlen(g_log) - 1);
}

struct {
    void (*Printf)(const char *, ...);
    cvar_t *(*Cvar_Get)(const char *, const char *, int);
    cvar_t *(*Cvar_Find)(const char *);
} cgi = {my_Printf, my_Cvar_Get, my_Cvar_Find};

struct {
    int localServer;
} cgs = {0};

/* ---- the real filter under test ---- */
#ifdef FILTER_HEAD
#include "real_filter_head.inc"
#else
/* SEC2: the patched filter calls the statement rules shared with the exe (qcommon/cmd_filter.c, verbatim) */
#include "real_srvfilter.inc"
#include "real_filter_work.inc"
#endif

/* ===================================================================== */
/*  TEST DRIVER                                                          */
/* ===================================================================== */
static int  pass = 0, fail = 0;
static char scratch[1024];

#include "inv.inc"

static qboolean run(const char *s)
{
    g_log[0] = 0;
    Q_strncpyz(scratch, s, sizeof(scratch));
    return CG_IsStatementAllowed(scratch);
}

/* must-PASS in every build */
static void mustpass(const char *label, const char *s)
{
    if (run(s)) {
        pass++;
    } else {
        fail++;
        printf("  FAIL(pass) %-10s :: %s  [log:%s]\n", label, s, g_log);
    }
}

/* attack: patched build must DROP with `reason` in the log; head build must ADMIT (delta proof that
 * the fix is load-bearing - the attack was previously reachable). */
static void attack(const char *label, const char *s, const char *reason)
{
    qboolean got = run(s);
#ifdef IS_PATCHED
    if (!got && (reason == NULL || strstr(g_log, reason))) {
        pass++;
    } else {
        fail++;
        printf("  FAIL(drop) %-10s got=%d want reason='%s' :: %s  [log:%s]\n",
               label, got, reason ? reason : "(any)", s, g_log);
    }
#else
    if (got) {
        pass++; /* HEAD admits the hole - proves the fix is load-bearing */
    } else {
        fail++;
        printf("  FAIL(head-should-admit) %-10s :: %s\n", label, s);
    }
#endif
}

/* must DROP in BOTH builds (a hazard the stock filter already blocks; not a SEC1 delta). */
static void mustdrop(const char *label, const char *s, const char *reason)
{
    qboolean got = run(s);
    if (!got && (reason == NULL || strstr(g_log, reason))) {
        pass++;
    } else {
        fail++;
        printf("  FAIL(drop-both) %-10s got=%d :: %s  [log:%s]\n", label, got, s, g_log);
    }
}

/* differential: the value the REAL engine would store for a write statement. */
static void diff_engine_value(const char *base, const char *stmt, const char *cvar, char *out, int outsize)
{
    const char *kw;
    setcv(cvar, base, CVAR_USER_CREATED);
    Cmd_TokenizeString2(stmt, qfalse);
    if (Cmd_Argc() < 2) {
        out[0] = 0;
        return;
    }
    kw = Cmd_Argv(0);
    if (!Q_stricmp(kw, "set") || !Q_stricmp(kw, "seta") || !Q_stricmp(kw, "sets") || !Q_stricmp(kw, "setu")) {
        Q_strncpyz(out, Cmd_ArgsFrom(2), outsize);
    } else if (!Q_stricmp(kw, "append")) {
        Com_sprintf(out, outsize, "%s %s", base, Cmd_Argv(2)); /* Cvar_Append_f: old + " " + Argv(2) */
    } else {
        Q_strncpyz(out, Cmd_ArgsFrom(1), outsize); /* bare Cvar_Command: Cmd_Args() */
    }
}

/* Assert the filter's decision on the in-walk STAGED write equals its decision on the value the
 * engine actually stores.  A divergence (e.g. append modeled as overwrite) is caught here. */
static void differential(const char *label, const char *base, const char *stmt, const char *cvar)
{
    char eng[512], textA[1024], textB[512];
    qboolean dA, dB;

    diff_engine_value(base, stmt, cvar, eng, sizeof(eng));

    /* form A: single text - the write stages, then vstr reads the staged model value */
    setcv(cvar, base, CVAR_USER_CREATED);
    Com_sprintf(textA, sizeof(textA), "%s;vstr %s", stmt, cvar);
    dA = run(textA);

    /* form B: the engine value is already live, then vstr reads it */
    setcv(cvar, eng, CVAR_USER_CREATED);
    Com_sprintf(textB, sizeof(textB), "vstr %s", cvar);
    dB = run(textB);

    if (dA == dB) {
        pass++;
    } else {
        fail++;
        printf("  FAIL(diff)  %-10s model=%d engine=%d engVal='%s' :: %s\n", label, dA, dB, eng, cvar);
    }
}

#ifdef IS_PATCHED
/* byte-for-byte: the value the filter MODELS for a write must equal what the real engine tokenizer
 * + Cmd_ArgsFrom store, especially for quoted args where the old raw-substring model was wrong. */
static void bytemodel(const char *label, const char *stmt, const char *cvar)
{
    char eng[512], mdl[512];

    (void)cvar;
    Cmd_TokenizeString2(stmt, qfalse);
    Q_strncpyz(eng, Cmd_ArgsFrom(2), sizeof(eng)); /* set-family value = ArgsFrom(2) */
    CG_Test_ModelValue(stmt, mdl, sizeof(mdl));
    if (!strcmp(eng, mdl)) {
        pass++;
    } else {
        fail++;
        printf("  FAIL(bytemodel) %-10s eng='%s' mdl='%s' :: %s\n", label, eng, mdl, stmt);
    }
}
#endif

int main(void)
{
    /* covtrace on, so the recorded log carries the VDROP sub-reasons the attack arm asserts */
    setcv("coop_covtrace", "1", 0);

    /* --- baseline inventory the crafted cases lean on --- */
    setcv("coop_x", "", CVAR_USER_CREATED);
    setcv("coop_evil", "", CVAR_USER_CREATED);
    setcv("quit", "", 0);        /* an engine command masquerading as a cvar: NOT user-created */
    cvtab[ncv - 1].flags = 0;

    /* g_m2l1 exists before the server ever vstr's it in-game (the fov system creates it) */
    setcv("g_m2l1", "append name ,180", CVAR_USER_CREATED);

    printf("== LEGIT multi-statement + name-bus (must PASS) ==\n");
    mustpass("uniform", "dm_playermodel german_waffenss_officer;vstr g_m2l1");
    mustpass("fov-store", "set g_m2l2 80;set g_m2l1 append name ,180");
    mustpass("nb-nomark", "seta coop_x \"append name pwned\";vstr coop_x"); /* no marker -> benign name */
    mustpass("gate", "set coop_gate_tally Squad ready: 2 / 3");
    mustpass("name-clean", "set name Player");
    mustpass("name-clean2", "set name John Smith");
    mustpass("name-bare", "name John Smith");
    mustpass("name-w", "append name ,w101");
    mustpass("name-sn", "append name ,sn07");
    mustpass("name-hn", "append name ,hn12");
    mustpass("name-gn", "append name ,gn3");
    mustpass("name-f", "append name ,f10");
    mustpass("name-fov", "append name ,190");
    mustpass("name-auth", "append name ,5aBcDeF");
    mustpass("name-admkey", "append name ,5:my-admin-token");
    mustpass("nested-store", "seta coop_loFcmtA1 set coop_loFcmt1 vstr coop_loFgo1");
    mustpass("cleared", "set coop_loASkin 0;vstr coop_loASkin");
    /* real multi-statement shapes the .scr producers emit (must not regress) */
    mustpass("fov-2stmt", "set g_m2l2 90;set g_m2l1 append name ,190");    /* player.scr:827 */
    mustpass("uniform-fov", "dm_playermodel german_wehrmacht_soldier;vstr g_m2l1"); /* itemhandler.scr:902 */
    mustpass("auth-1stmt", "set g_m1l3 append name ,5aBcDeF");             /* developer.scr:121 */
    mustpass("name-seta", "seta name Player");
    mustpass("name-bare2", "name Player");

    printf("== ATTACK (a): all writer verbs, single text (must DROP) ==\n");
    attack("seta", "seta coop_x quit;vstr coop_x", "vstr coop_x");
    attack("set", "set coop_x quit;vstr coop_x", "vstr coop_x");
    attack("seta-q", "seta coop_evil \"quit\";vstr coop_evil", "vstr coop_evil");
    attack("connect", "seta coop_x connect evil.host:12203;vstr coop_x", "vstr coop_x");
    attack("writecfg", "seta coop_x writeconfig hack.dat;vstr coop_x", "vstr coop_x");
    attack("bare", "coop_x connect evil:12203;vstr coop_x", "vstr coop_x");
    /* SEC2: coop_loDeny is on the generated guard list (the client vstr's it), so the hostile bare write
     * is now refused at the write itself, before the vstr is reached */
    attack("bare-deny", "coop_loDeny quit;vstr coop_loDeny", "guard coop_loDeny");
    attack("append-new", "append coop_x quit;vstr coop_x", "vstr coop_x");
    attack("ovr-append", "seta coop_x quit;append coop_x echo;vstr coop_x", "vstr coop_x");

    printf("== ATTACK via name bus markers (must DROP) ==\n");
    attack("nb-dev", "seta coop_x \"append name ,3\";vstr coop_x", "namebus");
    attack("nb-admin", "seta coop_x \"append name ,6\";vstr coop_x", "namebus");
    attack("nb-noclip", "seta coop_x \"append name ,nc\";vstr coop_x", "namebus");
    attack("nb-giveall", "seta coop_x \"append name ,ga\";vstr coop_x", "namebus");
    attack("nb-tele", "seta coop_x \"append name ,2\";vstr coop_x", "namebus");
    attack("nb-ping", "seta coop_x \"append name ,pg\";vstr coop_x", "namebus");
    attack("nb-bare", "seta coop_x \"append name ,\";vstr coop_x", "namebus");
    attack("nb-setname", "set name Foo ,ga", "namebus");
    attack("nb-setaname", "seta name Player ,nc", "namebus");
    attack("nb-barename", "name Foo ,ga1", "namebus");
    attack("nb-viavstr", "seta coop_x set name Player ,ga;vstr coop_x", "namebus");

    printf("== glued ';' / comment / CR statement-hiding (HEAD admits, patched drops) ==\n");
    /* COM_ParseExt kept ';' inside the token and RemoveEndToken truncated it, so the filter never
     * saw the second statement while Cbuf_Execute runs it. The faithful splitter fixes this. */
    attack("glue-echoq", "echo;quit", NULL);
    attack("glue-seta", "seta coop_x quit;echo;vstr coop_x", "vstr coop_x");
    attack("glue-set", "seta coop_x quit;set;vstr coop_x", "vstr coop_x");
    attack("glue-nb", "echo;append name ,ga", "namebus");
    attack("glue-qsemi", "seta coop_x \"echo;echo;quit\";vstr coop_x", "vstr coop_x");
    /* Cbuf_Execute also ends a line after a closing */ /* and on a bare CR (cmd.c:216-247). */
    attack("comment", "echo /**/quit", NULL);
    attack("cr", "echo x\rquit", NULL);
    /* an unterminated star comment would carry into the NEXT buffered stufftext (the stuffed newline
     * does not end it), where a closing star-slash would expose a hidden statement: refuse the opener. */
    attack("open-comment", "echo /*", "comment");
    attack("open-comment-vstr", "seta coop_x \"echo /*\";vstr coop_x", "comment");
    /* live-value variant: no write in the text, the hostile value is already resident */
    setcv("coop_x", "quit", CVAR_USER_CREATED);
    attack("glue-live", "tmstop;vstr coop_x", "vstr coop_x");
    setcv("coop_x", "", CVAR_USER_CREATED); /* restore benign live value for later cases */

    printf("== LF statement break (drops in BOTH - HEAD's skip loop already breaks on '\\n') ==\n");
    mustdrop("lf", "echo x\nquit", NULL);

    printf("== length fail-closed: over-long name / value must DROP (patched), reason 'length' ==\n");
    {
        char longname[128], longval[700];
        int  k;
        for (k = 0; k < 70; k++) {
            longname[k] = 'a';
        }
        longname[70] = 0;
        {
            char s[256];
            sprintf(s, "seta coop_%s 1", longname); /* name >= 64 -> DROP length */
            attack("len-name", s, "length");
        }
        for (k = 0; k < 600; k++) {
            longval[k] = 'a';
        }
        longval[600] = 0;
        {
            char s[800];
            sprintf(s, "seta coop_x %s", longval); /* value >= 512 -> DROP length */
            attack("len-value", s, "length");
        }
    }

    printf("== BYTE-FOR-BYTE model vs real tokenizer (quoted-arg exactness) ==\n");
#ifdef IS_PATCHED
    bytemodel("bm-empty", "seta coop_x \"\" quit", "coop_x");   /* engine stores ' quit', not '' */
    bytemodel("bm-two", "seta coop_x \"a\" \"quit\"", "coop_x"); /* -> 'a quit' */
    bytemodel("bm-glued", "seta coop_x \"\"quit", "coop_x");     /* -> ' quit' */
#else
    pass += 3; /* accessor only exists in the patched build */
#endif

    printf("== exec trampoline outside allowed paths (must DROP in both - stock bug-597 guard) ==\n");
    mustdrop("ex-bad", "exec configs/omconfig.cfg", NULL);

    printf("== ATTACK overflow + recursion (must DROP / terminate) ==\n");
    {
        /* 33 padding sets then a hostile set+vstr: the 33rd write overflows the stage table */
        char big[2048];
        int  i, off = 0;
        for (i = 0; i < 33; i++) {
            off += sprintf(big + off, "seta coop_pad%d 1;", i);
        }
        sprintf(big + off, "seta coop_x quit;vstr coop_x");
        attack("overflow", big, "overflow");
    }
    setcv("coop_loop", "vstr coop_loop", CVAR_USER_CREATED);
    attack("selfref", "vstr coop_loop", "depth");

    printf("== flush-on-pass: a dropped hostile text must not poison a later legit resend ==\n");
    setcv("coop_loA1", "append name ,w101", CVAR_USER_CREATED);
    {
        qboolean dropped = !run("seta coop_loA1 quit;quit"); /* hostile: dropped, stages nothing live */
        qboolean legit   = run("vstr coop_loA1");            /* legit resend still passes */
#ifdef IS_PATCHED
        if (dropped && legit) {
            pass++;
        } else {
            fail++;
            printf("  FAIL flush-on-pass dropped=%d legit=%d\n", dropped, legit);
        }
#else
        (void)dropped;
        (void)legit;
        pass++;
#endif
    }

    printf("== DIFFERENTIAL: staged model vs real engine store (append/bare exactness) ==\n");
    differential("d-appd-safe", "exec ui/loadout/w01_s1.cfg", "append coop_x extra", "coop_x");
    differential("d-appd-bad", "quit", "append coop_x echo", "coop_x");
    differential("d-bare", "", "coop_x connect evil", "coop_x");
    differential("d-set", "echo hi", "seta coop_x play sound/x", "coop_x");
    differential("d-appd-w", "", "append coop_x quit", "coop_x");

    printf("== INVENTORY REPLAY: every archived + script-built value (must PASS) ==\n");
    inv_setup();
    {
        int n = inv_run();
        printf("  replayed %d (cvar,value) pairs\n", n);
    }

    printf("\nRESULT pass=%d fail=%d\n", pass, fail);
    return fail ? 1 : 0;
}
