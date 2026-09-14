/*
 * SEC2 filter self-test - security layer 2: openmohaa.exe filters every SERVER-origin command line when it
 * EXECUTES, with the origin carried per byte through the command buffer.
 *
 * Links the REAL qcommon/cmd.c (work tree, HEAD, or a planted mutant), the REAL qcommon/cmd_filter.c and
 * q_shared.c, the REAL cvar command handlers (cvar.c) and cl_cgame.cpp stufftext plumbing (pasted by
 * gen_sec2.py), and the REAL cgame reception filter (work or HEAD). Only the filesystem, the cvar store,
 * memory and the client/game command hooks are stubs, so every result comes from shipped code (TRAPS T14).
 *
 * One exe per arm (build.bat):
 *   ARM_L1    HEAD exe + HEAD cgame filter     the shipped layer-1-only pair        attacks must RUN
 *   ARM_L2    new exe, NO reception filter     layer 2 alone                         attacks drop with COVX
 *   ARM_L12   new exe + new cgame filter       the new pair                          attacks never run
 *   ARM_OLDCG new exe + HEAD cgame filter      previous cgame.dll on the new exe     attacks never run
 *   ARM_OLDCG153 new exe + v1.5.3 cgame filter  the cgame.dll players have today     attacks never run
 *   ARM_L1_153 HEAD exe + v1.5.3 cgame filter   that cgame.dll's shipped pair        corpus baseline only
 *   ARM_NEWCG HEAD exe + new cgame filter      new cgame.dll on the previous exe     layer 1 only, stated set runs
 *
 * Groups: coop (legit traffic must pass), corpus (every coop stufftext, traced), guard (every reached
 * server write to a guarded cvar validates), diff (cgame vs exe decisions), attack, origin.
 */
#include "q_shared.h"
#include "qcommon.h"

#if defined(ARM_L2) || defined(ARM_L12) || defined(ARM_OLDCG) || defined(ARM_OLDCG153)
#define HAS_L2 1 /* the new exe: origin-tagged command buffer + layer 2 */
#endif
#if defined(ARM_OLDCG) || defined(ARM_OLDCG153)
#define ARM_OLDCG_ANY 1 /* a previous cgame.dll relaying a stufftext through cgi.Cmd_Stuff */
#endif
#if defined(HAS_L2) || defined(ARM_NEWCG)
#include "cmd_filter.h"
#endif
#include "paths.inc"

#include <ctype.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(ARM_L1)
#define ARM_NAME "L1"
#elif defined(ARM_L2)
#define ARM_NAME "L2"
#elif defined(ARM_L12)
#define ARM_NAME "L12"
#elif defined(ARM_OLDCG)
#define ARM_NAME "OLDCG"
#elif defined(ARM_OLDCG153)
#define ARM_NAME "OLDCG153"
#elif defined(ARM_NEWCG)
#define ARM_NAME "NEWCG"
#elif defined(ARM_L1_153)
#define ARM_NAME "L1_153"
#else
#error define one ARM_*
#endif

cvar_t *com_cl_running;
cvar_t *com_sv_running;
int     cvar_modifiedFlags;

extern int             cmd_wait;
struct cmd_function_s *Cmd_FindCommand(const char *cmd_name);
void                   Cmd_Alias(const char *s, const char *cmd);

/* ===================================================================== log + trace */
#define LOG_CAP   (4 << 20)
#define TRACE_CAP (4 << 20)
static char   g_log[LOG_CAP];
static size_t g_logLen;
static char   g_trace[TRACE_CAP];
static size_t g_traceLen;
static int    g_verbose;

static void buf_add(char *buf, size_t *len, size_t cap, const char *s)
{
    size_t n = strlen(s);

    if (*len + 1 >= cap) {
        return;
    }
    if (*len + n + 1 > cap) {
        n = cap - *len - 1;
    }
    memcpy(buf + *len, s, n);
    *len += n;
    buf[*len] = 0;
}

static void trace_line(const char *fmt, ...)
{
    char    b[8192];
    va_list ap;

    va_start(ap, fmt);
    vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    buf_add(g_trace, &g_traceLen, TRACE_CAP, b);
    buf_add(g_trace, &g_traceLen, TRACE_CAP, "\n");
}

void QDECL Com_Printf(const char *fmt, ...)
{
    char    b[16384];
    va_list ap;

    va_start(ap, fmt);
    vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    buf_add(g_log, &g_logLen, LOG_CAP, b);
    if (strncmp(b, "^~^~^", 5)) {
        /* a non-marker print is an effect (echo, execing, usage) and belongs in the execution trace */
        buf_add(g_trace, &g_traceLen, TRACE_CAP, "P:");
        buf_add(g_trace, &g_traceLen, TRACE_CAP, b);
    }
    if (g_verbose) {
        fputs(b, stdout);
    }
}

void QDECL Com_DPrintf(const char *fmt, ...)
{
    (void)fmt;
}

void QDECL Com_Error(int code, const char *fmt, ...)
{
    char    b[4096];
    va_list ap;

    va_start(ap, fmt);
    vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    fprintf(stderr, "Com_Error(%d): %s\n", code, b);
    exit(3);
}

/* ===================================================================== memory, filesystem, hooks */
void *Z_TagMalloc(int size, int tag)
{
    (void)tag;
    return calloc(1, size > 0 ? size : 1);
}

void *Z_Malloc(int size)
{
    return calloc(1, size > 0 ? size : 1);
}

void Z_Free(void *ptr)
{
    free(ptr);
}

char *CopyString(const char *in)
{
    size_t n = strlen(in) + 1;
    char  *s = (char *)malloc(n);
    memcpy(s, in, n);
    return s;
}

typedef struct {
    const char *path;
    const char *text;
} vfile_t;

/* test-only cfgs under a server-exec'able prefix (ui/coop_*), never shipped */
static const vfile_t g_vfiles[] = {
    {"ui/coop_sec2t/tramp.cfg", "vstr coop_x\n"    },
    {"ui/coop_sec2t/d3.cfg",    "vstr coop_d4\n"   },
    {"ui/coop_sec2t/now.cfg",   "rec_nowfile\n"    },
    {"ui/coop_sec2t/nb.cfg",    "append name ,ga\n"},
    {NULL,                      NULL               }
};

typedef struct {
    char *path;
    char *data;
    long  len;
} fcache_t;

#define FC_MAX 8192
static fcache_t g_fc[FC_MAX];
static int      g_fcN;

long FS_ReadFile(const char *qpath, void **buffer)
{
    const vfile_t *v;
    char          *data = NULL;
    long           len  = -1;
    int            i;

    for (v = g_vfiles; v->path; v++) {
        if (!Q_stricmp(v->path, qpath)) {
            len  = (long)strlen(v->text);
            data = CopyString(v->text);
            break;
        }
    }
    if (!data) {
        for (i = 0; i < g_fcN; i++) {
            if (!Q_stricmp(g_fc[i].path, qpath)) {
                len  = g_fc[i].len;
                data = (char *)malloc(len + 1);
                memcpy(data, g_fc[i].data, len + 1);
                break;
            }
        }
    }
    if (!data) {
        char  full[1024];
        FILE *f;

        snprintf(full, sizeof(full), "%s/%s", MOD_ROOT, qpath);
        f = fopen(full, "rb");
        if (!f) {
            if (buffer) {
                *buffer = NULL;
            }
            return -1;
        }
        fseek(f, 0, SEEK_END);
        len = ftell(f);
        fseek(f, 0, SEEK_SET);
        data      = (char *)malloc(len + 1);
        len       = (long)fread(data, 1, len, f);
        data[len] = 0;
        fclose(f);
        if (g_fcN < FC_MAX) {
            g_fc[g_fcN].path = CopyString(qpath);
            g_fc[g_fcN].data = (char *)malloc(len + 1);
            memcpy(g_fc[g_fcN].data, data, len + 1);
            g_fc[g_fcN].len = len;
            g_fcN++;
        }
    }
    if (!buffer) {
        free(data);
        return len;
    }
    *buffer = data;
    return len;
}

void FS_FreeFile(void *buffer)
{
    free(buffer);
}

void QDECL FS_Printf(fileHandle_t f, const char *fmt, ...)
{
    (void)f;
    (void)fmt;
}

int Com_Filter(const char *filter, const char *name, int casesensitive)
{
    (void)filter;
    (void)name;
    (void)casesensitive;
    return 1;
}

void Field_CompleteFilename(const char *dir, const char *ext, qboolean stripExt, qboolean allowNonPureFilesOnDisk)
{
    (void)dir;
    (void)ext;
    (void)stripExt;
    (void)allowNonPureFilesOnDisk;
}

void Cvar_CompleteCvarName(const char *args, int argNum)
{
    (void)args;
    (void)argNum;
}

qboolean CL_GameCommand(void)
{
    return qfalse;
}

qboolean SV_GameCommand(void)
{
    return qfalse;
}

void CL_ForwardCommandToServer(const char *string)
{
    trace_line("FWD %s", string);
}

/* ===================================================================== cvar store with an undo journal */
#define CV_MAX   32768
#define CVH_SIZE 65536
static cvar_t g_cv[CV_MAX];
static int    g_cvN;
static int    g_cvHash[CVH_SIZE]; /* 0 empty, -1 tombstone, else index + 1 */

typedef struct {
    int   idx;
    int   created;
    int   oldFlags;
    char *oldString;
    int   hashSlot;
} jr_t;

static jr_t *g_jr;
static int   g_jrN, g_jrCap;
static int   g_journal;

static unsigned cv_hash(const char *s)
{
    unsigned h = 2166136261u;
    for (; *s; s++) {
        h ^= (unsigned char)tolower((unsigned char)*s);
        h *= 16777619u;
    }
    return h;
}

static void jr_push(int idx, int created, int oldFlags, char *oldString, int hashSlot)
{
    if (g_jrN == g_jrCap) {
        g_jrCap = g_jrCap ? g_jrCap * 2 : 4096;
        g_jr    = (jr_t *)realloc(g_jr, sizeof(jr_t) * g_jrCap);
    }
    g_jr[g_jrN].idx       = idx;
    g_jr[g_jrN].created   = created;
    g_jr[g_jrN].oldFlags  = oldFlags;
    g_jr[g_jrN].oldString = oldString;
    g_jr[g_jrN].hashSlot  = hashSlot;
    g_jrN++;
}

static void jr_rollback(void)
{
    while (g_jrN > 0) {
        jr_t   *j = &g_jr[--g_jrN];
        cvar_t *v = &g_cv[j->idx];

        if (j->created == 2) {
            /* a cv_delete: put the name back in the lookup table */
            g_cvHash[j->hashSlot] = j->idx + 1;
        } else if (j->created) {
            g_cvHash[j->hashSlot] = -1;
            free(v->name);
            free(v->string);
            memset(v, 0, sizeof(*v));
            if (j->idx == g_cvN - 1) {
                g_cvN--;
            }
        } else {
            free(v->string);
            v->string  = j->oldString;
            v->flags   = j->oldFlags;
            v->integer = atoi(v->string);
            v->value   = (float)atof(v->string);
        }
    }
}

cvar_t *Cvar_FindVar(const char *name)
{
    unsigned h = cv_hash(name) & (CVH_SIZE - 1);

    for (;;) {
        int e = g_cvHash[h];
        if (e == 0) {
            return NULL;
        }
        if (e > 0 && !Q_stricmp(g_cv[e - 1].name, name)) {
            return &g_cv[e - 1];
        }
        h = (h + 1) & (CVH_SIZE - 1);
    }
}

static cvar_t *cv_create(const char *name, const char *value, int flags)
{
    unsigned h    = cv_hash(name) & (CVH_SIZE - 1);
    int      tomb = -1;
    int      idx;
    cvar_t  *v;

    for (;;) {
        int e = g_cvHash[h];
        if (e == 0) {
            break;
        }
        if (e == -1 && tomb < 0) {
            tomb = (int)h;
        }
        h = (h + 1) & (CVH_SIZE - 1);
    }
    if (tomb >= 0) {
        h = (unsigned)tomb;
    }
    if (g_cvN >= CV_MAX) {
        Com_Error(ERR_FATAL, "harness cvar table full");
    }
    idx         = g_cvN++;
    v           = &g_cv[idx];
    v->name     = CopyString(name);
    v->string   = CopyString(value);
    v->flags    = flags;
    v->integer  = atoi(value);
    v->value    = (float)atof(value);
    g_cvHash[h] = idx + 1;
    if (g_journal) {
        jr_push(idx, 1, 0, NULL, (int)h);
    }
    return v;
}

/* drop a cvar from the lookup table: the state before the cfg that creates it has run */
static void cv_delete(const char *name)
{
    unsigned h = cv_hash(name) & (CVH_SIZE - 1);

    for (;;) {
        int e = g_cvHash[h];
        if (e == 0) {
            return;
        }
        if (e > 0 && !Q_stricmp(g_cv[e - 1].name, name)) {
            if (g_journal) {
                jr_push(e - 1, 2, 0, NULL, (int)h);
            }
            g_cvHash[h] = -1;
            return;
        }
        h = (h + 1) & (CVH_SIZE - 1);
    }
}

static void cv_assign(cvar_t *v, const char *value, int flags)
{
    char *nv = CopyString(value);

    if (g_journal) {
        jr_push((int)(v - g_cv), 0, v->flags, v->string, 0);
    } else {
        free(v->string);
    }
    v->string  = nv;
    v->flags   = flags;
    v->integer = atoi(nv);
    v->value   = (float)atof(nv);
}

cvar_t *Cvar_Get(const char *name, const char *value, int flags)
{
    cvar_t *v = Cvar_FindVar(name);

    if (!v) {
        return cv_create(name, value ? value : "", flags);
    }
    if (v->flags & CVAR_USER_CREATED) {
        /* cvar.c: an engine registration takes ownership of a user-created cvar */
        cv_assign(v, v->string, (v->flags & ~CVAR_USER_CREATED) | flags);
    }
    return v;
}

cvar_t *Cvar_Set2(const char *name, const char *value, qboolean force)
{
    cvar_t *v = Cvar_FindVar(name);

    (void)force;
    if (!v) {
        if (!value) {
            return NULL;
        }
        v = cv_create(name, value, CVAR_USER_CREATED);
    } else {
        if (!value) {
            value = "";
        }
        cv_assign(v, value, v->flags);
    }
    trace_line("SET %s=%s", name, value);
    return v;
}

char *Cvar_VariableString(const char *name)
{
    cvar_t *v = Cvar_FindVar(name);
    return v ? v->string : "";
}

int Cvar_VariableIntegerValue(const char *name)
{
    cvar_t *v = Cvar_FindVar(name);
    return v ? v->integer : 0;
}

int Cvar_Flags(const char *name)
{
    cvar_t *v = Cvar_FindVar(name);
    return v ? v->flags : CVAR_NONEXISTENT;
}

void Cvar_Set(const char *name, const char *value)
{
    Cvar_Set2(name, value, qtrue);
}

qboolean FS_CheckDirTraversal(const char *checkdir)
{
    return strstr(checkdir, "..") ? qtrue : qfalse;
}

static void Cvar_Print(cvar_t *v)
{
    Com_Printf("\"%s\" is:\"%s^7\"\n", v->name, v->string);
}

static void Cvar_Print_f(void)
{
    cvar_t *v = Cvar_FindVar(Cmd_Argv(1));
    if (v) {
        Cvar_Print(v);
    }
}

#include "real_cvarcmds.inc"

/* the real CS_SYSTEMINFO cvar scan: this arm's exe, so the previous one still creates what it created */
#if defined(ARM_L1) || defined(ARM_NEWCG) || defined(ARM_L1_153)
#include "real_sysinfo_head.inc"
#else
#include "real_sysinfo_work.inc"
#endif

/* ===================================================================== cgame + client plumbing */
#ifndef ARM_L2
static struct {
    void (*Printf)(const char *fmt, ...);
    cvar_t *(*Cvar_Get)(const char *name, const char *value, int flags);
    cvar_t *(*Cvar_Find)(const char *name);
} cgi;

static struct {
    int localServer;
} cgs;

#if defined(ARM_L1) || defined(ARM_OLDCG)
#include "cgf_head.inc"
#elif defined(ARM_OLDCG153) || defined(ARM_L1_153)
#include "cgf_153.inc"
#else
#include "cgf_work.inc"
#endif
#endif

#ifdef HAS_L2
#include "real_clcg.inc"
#endif

/* ===================================================================== commands */
static void rec_cmd(void)
{
    char b[4096];
    int  i;

    b[0] = 0;
    for (i = 0; i < Cmd_Argc(); i++) {
        if (i) {
            Q_strcat(b, sizeof(b), " ");
        }
        Q_strcat(b, sizeof(b), Cmd_Argv(i));
    }
    trace_line("RUN %s", b);
}

/* cg_consolecmds.c CG_PushMenuTeamSelect_f: runs engine-hardcoded text through EXEC_NOW */
static void teamselect_f(void)
{
    trace_line("RUN pushmenu_teamselect");
    Cbuf_ExecuteText(EXEC_NOW, "ui_getplayermodel\n");
}

/* cl_main.cpp coop_srsync shape: an EXEC_NOW exec of a hardcoded cfg, triggered by a server-whitelisted verb */
static void pushmenu_f(void)
{
    rec_cmd();
    if (!Q_stricmp(Cmd_Argv(1), "sec2now")) {
        Cbuf_ExecuteText(EXEC_NOW, "exec ui/coop_sec2t/now.cfg\n");
    }
}

static const char *g_recNames[] = {
    "rec_srv1", "rec_loc1", "rec_inner", "rec_l2", "rec_l3", "rec_s3", "rec_after", "rec_srv_after", "rec_leaf",
    "rec_w", "rec_wl", "rec_now7", "rec_nowfile", "rec_al", "rec_ov_l", "rec_ov_s", "rec_cglocal", "rec_mod2",
    "rec_ns", "rec_nl", "rec_mA", "rec_mB", "ui_getplayermodel", "writeconfig", "quit", "coop_join", "map",
    "spmap", "cinematic", "disconnect", NULL
};

static void init_world(void)
{
    int i;

    Cbuf_Init();
    Cmd_Init();
    Cmd_AddCommand("set", Cvar_Set_f);
    Cmd_AddCommand("seta", Cvar_Set_f);
    Cmd_AddCommand("sets", Cvar_Set_f);
    Cmd_AddCommand("setu", Cvar_Set_f);
    Cmd_AddCommand("append", Cvar_Append_f);
    Cmd_AddCommand("pushmenu_teamselect", teamselect_f);
    Cmd_AddCommand("pushmenu", pushmenu_f);
    for (i = 0; g_recNames[i]; i++) {
        if (!Cmd_FindCommand(g_recNames[i])) {
            Cmd_AddCommand(g_recNames[i], rec_cmd);
        }
    }
#define ENG_CMD(n) if (!Cmd_FindCommand(n)) Cmd_AddCommand(n, rec_cmd);
#include "engcmds.inc"
#undef ENG_CMD

#define ENG_CVAR(n) Cvar_Get(n, "", 0);
#include "engcvars.inc"
#undef ENG_CVAR
#define BASE_CVAR(n, v) Cvar_Set2(n, v, qfalse);
#include "basecvars.inc"
#undef BASE_CVAR
#define INV_SETUP(c, v) Cvar_Set2(c, v, qfalse);
#define INV_PAIR(c, v)
#include "../sec1_filter_selftest/inv_pairs.inc"
#undef INV_SETUP
#undef INV_PAIR

    com_cl_running = Cvar_Get("cl_running", "1", 0);
    cv_assign(com_cl_running, "1", com_cl_running->flags);
    com_sv_running = Cvar_Get("sv_running", "0", 0);
    cv_assign(com_sv_running, "0", com_sv_running->flags);
    {
        cvar_t *c = Cvar_Get("coop_covtrace", "1", 0);
        cv_assign(c, "1", c->flags);
        c = Cvar_Get("name", "Player", CVAR_USERINFO | CVAR_ARCHIVE);
        cv_assign(c, "Player", c->flags);
    }
#ifndef ARM_L2
    cgi.Printf    = Com_Printf;
    cgi.Cvar_Get  = Cvar_Get;
    cgi.Cvar_Find = Cvar_FindVar;
#endif
    g_journal = 1;
}

/* ===================================================================== test plumbing */
static int         g_pass, g_fail, g_gpass, g_gfail;
static const char *g_only;

static int want(const char *group)
{
    return !g_only || !strcmp(g_only, group);
}

static void begin(int ls)
{
    jr_rollback();
    g_logLen = 0;
    g_log[0] = 0;
    Cbuf_Init();
    cmd_wait = 0;
    cv_assign(com_sv_running, ls ? "1" : "0", com_sv_running->flags);
#ifndef ARM_L2
    cgs.localServer = ls;
#endif
#ifdef HAS_L2
    cl_cgPendingStuff   = qfalse;
    cl_cgPendingNewline = qfalse;
#endif
    g_traceLen = 0;
    g_trace[0] = 0;
}

static int trace_has(const char *s)
{
    return strstr(g_trace, s) != NULL;
}

static int log_has(const char *s)
{
    return strstr(g_log, s) != NULL;
}

static void show_markers(void)
{
    const char *p = g_log;
    int         n = 0;

    while ((p = strstr(p, "^~^~^")) != NULL && n < 6) {
        const char *e   = strchr(p, '\n');
        int         len = e ? (int)(e - p) : (int)strlen(p);
        printf("        | %.*s\n", len > 160 ? 160 : len, p);
        p += 5;
        n++;
    }
}

static void expect(int cond, const char *group, const char *name, const char *what)
{
    if (cond) {
        g_pass++;
        g_gpass++;
        return;
    }
    g_fail++;
    g_gfail++;
    printf("  FAIL %-7s %-26s %s\n", group, name, what);
    show_markers();
}

static void group_begin(const char *name)
{
    g_gpass = g_gfail = 0;
    printf("== %s ==\n", name);
}

static void group_end(const char *name)
{
    printf("  group %-7s pass=%d fail=%d\n", name, g_gpass, g_gfail);
}

/* receive one server stufftext the way this arm's cgame + exe pair would */
static void recv_stufftext(const char *text)
{
    char copy[BIG_INFO_STRING];

    Q_strncpyz(copy, text, sizeof(copy));
#if defined(ARM_L1) || defined(ARM_NEWCG) || defined(ARM_L1_153)
    /* the previous exe: cgi->Cmd_Stuff = Cbuf_AddText, and a new cgame falls back to it (apiversion 0) */
    if (CG_IsStatementAllowed(copy)) {
        Cbuf_AddText(text);
        Cbuf_AddText("\n");
    }
#elif defined(ARM_L2)
    (void)copy;
    CL_CG_StuffServer(text); /* no reception filter: layer 2 on its own */
#elif defined(ARM_L12)
    if (CG_IsStatementAllowed(copy)) {
        CL_CG_StuffServer(text); /* cg_servercmds.c with apiversion >= 4 */
    }
#elif defined(ARM_OLDCG_ANY)
    {
        /* the wire + a previous cgame.dll (HEAD, or v1.5.3 = what players have today): CL_GetServerCommand
         * tokenizes, cgame filters Argv(1) and relays it through cgi.Cmd_Stuff(cmd) + cgi.Cmd_Stuff("\n") */
        char  s[BIG_INFO_STRING];
        char *cmd;

        (void)copy;
        Com_sprintf(s, sizeof(s), "stufftext \"%s\"", text);
        Cmd_TokenizeString(s);
        clcg_after_tokenize();
        cmd = Cmd_Argv(1);
        if (CG_IsStatementAllowed(cmd)) {
            CL_CG_Stuff(cmd);
            CL_CG_Stuff("\n");
        }
    }
#endif
}

static void frame(void)
{
    Cbuf_Execute(0);
}

static unsigned fnv(const char *s)
{
    unsigned h = 2166136261u;
    for (; *s; s++) {
        h ^= (unsigned char)*s;
        h *= 16777619u;
    }
    return h;
}

/* ===================================================================== group: coop (legit traffic) */
static void inv_one(const char *cv, const char *val)
{
    char text[512];

    begin(0);
    Cvar_Set2(cv, val, qfalse);
    Com_sprintf(text, sizeof(text), "vstr %s", cv);
    recv_stufftext(text);
    frame();
    frame();
    expect(!log_has("VDROP") && !log_has("COVX DROP"), "coop", "inventory-replay", text);
}

typedef struct {
    int         ls;
    const char *pre;    /* local cvar setup "name=value" or NULL */
    const char *text;   /* server stufftext */
    const char *effect; /* trace needle the legit traffic must produce */
} shape_t;

static const shape_t g_shapes[] = {
    {0, NULL,                          "set g_m2l2 90;set g_m2l1 append name ,190",           "SET g_m2l1=append name ,190"                },
    {0, NULL,                          "set name Player",                                     "SET name=Player"                            },
    {0, NULL,                          "set coop_isCoopSession 1",                            "SET coop_isCoopSession=1"                   },
    {0, NULL,                          "exec coop_mod/cfg/detect.cfg",                        "SET name=Player ,0203"                      },
    {0, NULL,                          "exec ui/loadout/open.cfg",                            "SET name=Player ,w0o"                       },
    {0, NULL,                          "exec ui/loadout/open.cfg",                            "RUN pushmenu coop_loadout"                  },
    {0, "g_m2l1=append name ,180",     "dm_playermodel german_wehrmacht_soldier;vstr g_m2l1", "SET name=Player ,180"                       },
    {0, "g_m1l3=append name ,5aBcDeF", "vstr g_m1l3",                                         "SET name=Player ,5aBcDeF"                   },
    {0, NULL,                          "set g_m1l3 append name ,5aBcDeF",                     "SET g_m1l3=append name ,5aBcDeF"            },
    {0, NULL,                          "pushmenu_teamselect",                                 "RUN ui_getplayermodel"                      },
    {0, NULL,                          "exec ui/coop_objectives/obj_setup.cfg",               "P:execing ui/coop_objectives/obj_setup.cfg" },
    {1, NULL,                          "map m5l3",                                            "RUN map m5l3"                               },
    {1, NULL,                          "spmap m1l1",                                          "RUN spmap m1l1"                             },
    {1, NULL,                          "cinematic briefinge1.roq",                            "RUN cinematic briefinge1.roq"               },
    {1, NULL,                          "disconnect",                                          "RUN disconnect"                             },
    {1, NULL,                          "exec ui/loadout/open.cfg",                            "SET name=Player ,w0o"                       },
    {0, NULL,                          NULL,                                                  NULL                                         }
};

static void group_coop(void)
{
    const shape_t *s;

    group_begin("coop: legitimate server traffic must pass unchanged");

#define INV_SETUP(c, v)
#define INV_PAIR(c, v) inv_one(c, v);
#include "../sec1_filter_selftest/inv_pairs.inc"
#undef INV_SETUP
#undef INV_PAIR

    for (s = g_shapes; s->text; s++) {
        begin(s->ls);
        if (s->pre) {
            char        nm[128];
            const char *eq = strchr(s->pre, '=');
            Q_strncpyz(nm, s->pre, (int)(eq - s->pre) + 1);
            Cvar_Set2(nm, eq + 1, qfalse);
        }
        recv_stufftext(s->text);
        frame();
        frame();
        expect(trace_has(s->effect), "coop", s->text, s->effect);
        expect(!log_has("VDROP") && !log_has("COVX DROP"), "coop", s->text, "no drop of any kind");
    }

    /* the armory tile click (coop_loadout.urc stuffcommand, CLIENT origin): nothing may be filtered */
    begin(0);
    Cvar_Set2("coop_loCmt01", "vstr coop_loCcur", qfalse);
    Cvar_Set2("coop_loCcur", "vstr coop_loC1", qfalse);
    Cvar_Set2("coop_loC1", "exec ui/loadout/w01_s1.cfg", qfalse);
    Cbuf_AddText("exec ui/loadout/t01.cfg\n");
    frame();
    frame();
    expect(trace_has("SET name=Player ,w101"), "coop", "tile-click-local", "armory chain applied the w101 pick");
    expect(!log_has("COVX") && !log_has("VDROP"), "coop", "tile-click-local", "client-origin chain never filtered");

    group_end("coop");
}

/* ===================================================================== group: corpus (traced) */
typedef struct {
    const char *text;
    const char *where;
} corpus_t;

static const corpus_t g_corpus[] = {
#define CORPUS(t, w) {t, w},
#include "corpus.inc"
#undef CORPUS
    {NULL, NULL}
};

static void group_corpus(const char *tracePath)
{
    FILE *f = tracePath ? fopen(tracePath, "w") : NULL;
    int   ls, i, covx = 0, n = 0;

    group_begin("corpus: every coop script stufftext, reception + execution traced");
    for (ls = 0; ls <= 1; ls++) {
        for (i = 0; g_corpus[i].text; i++) {
            begin(ls);
            recv_stufftext(g_corpus[i].text);
            frame();
            frame();
            n++;
            if (log_has("COVX DROP")) {
                covx++;
#if defined(ARM_L12) || defined(ARM_OLDCG_ANY)
                printf("  INFO corpus COVX drop ls=%d %s :: %.100s\n", ls, g_corpus[i].where, g_corpus[i].text);
                show_markers();
#endif
            }
            if (f) {
                char        esc[640];
                int         k = 0;
                const char *p;
                for (p = g_trace; *p && k < (int)sizeof(esc) - 4; p++) {
                    esc[k++] = (*p == '\n' || *p == '\t' || *p == '\r') ? '|' : *p;
                }
                esc[k] = 0;
                fprintf(f, "%d\t%d\t%08x\t%s\t%s\n", ls, i, fnv(g_trace), g_corpus[i].where, esc);
            }
        }
    }
    if (f) {
        fclose(f);
    }
    printf("  corpus runs=%d (%d stufftexts x 2 localServer), runs with a COVX drop=%d\n", n, n / 2, covx);
#if defined(ARM_L12) || defined(ARM_OLDCG_ANY)
    expect(covx == 0, "corpus", "no-covx-on-legit", "a legitimate coop stufftext was dropped by layer 2");
#endif
    group_end("corpus");
}

/* ===================================================================== group: guard corpus */
#ifdef HAS_L2
static const char *g_guardw[] = {
#define GUARDW(s) s,
#include "guardw.inc"
#undef GUARDW
    NULL
};

static void group_guard(void)
{
    int i;

    group_begin("guard: every reached server write to a guard-list cvar validates");
    for (i = 0; g_guardw[i]; i++) {
        begin(0);
        Cmd_TokenizeString(g_guardw[i]);
        expect(Cmd_IsServerLineAllowed(0), "guard", "reached-guarded-write", g_guardw[i]);
    }
    printf("  guarded writes checked=%d\n", i);
    group_end("guard");
}
#endif

/* ===================================================================== group: differential */
#ifdef ARM_L12
static const char *g_reached[] = {
#define REACHED(s, e) s,
#include "reached.inc"
#undef REACHED
    NULL
};

/* is the statement reached THROUGH a server-origin exec or vstr (so it runs at depth >= 1)? */
static const int g_reachedExpanded[] = {
#define REACHED(s, e) e,
#include "reached.inc"
#undef REACHED
    0
};

static const char *g_planted[] = {
    /* the localServer-gated allow-lists: the planted mut_lsforced must be caught here */
    "map m1l1", "spmap m1l1", "cinematic briefinge1.roq", "disconnect", "showmenu x", "hidemenu x", "cg_marks_add 1",
    "ui_hidemouse 1", "set ui_showmouse 1",
    /* registered commands admitted by cgame only through an implicit clause (the SHADOW class) */
    "coop_join evil.host 12203", "coop_srsync", "writeconfig x.cfg",
    NULL
};

enum { ST_BASE, ST_USER, ST_ENGINE };

static int diff_target(const char *stmt, char *out, int outSize)
{
    const char *v;

    Cmd_TokenizeString(stmt);
    if (Cmd_Argc() < 1) {
        return 0;
    }
    v = Cmd_Argv(0);
    if (!Q_stricmp(v, "set") || !Q_stricmp(v, "seta") || !Q_stricmp(v, "sets") || !Q_stricmp(v, "setu")
        || !Q_stricmp(v, "append") || !Q_stricmp(v, "vstr")) {
        if (Cmd_Argc() < 2) {
            return 0;
        }
        Q_strncpyz(out, Cmd_Argv(1), outSize);
        return 1;
    }
    if (!Q_stricmp(v, "exec")) {
        return 0;
    }
    Q_strncpyz(out, v, outSize);
    return 1;
}

static void diff_state(const char *name, int st)
{
    cvar_t *c = Cvar_FindVar(name);

    if (st == ST_USER) {
        if (!c) {
            cv_create(name, "", CVAR_USER_CREATED);
        } else {
            cv_assign(c, c->string, c->flags | CVAR_USER_CREATED);
        }
    } else if (st == ST_ENGINE) {
        if (!c) {
            cv_create(name, "", 0);
        } else {
            cv_assign(c, c->string, c->flags & ~CVAR_USER_CREATED);
        }
    }
}

static void group_diff(void)
{
    static const char *shadowSeen[128];
    int                nShadowSeen = 0;
    int                set, i, ls, st;
    int                agreeAllow = 0, agreeDeny = 0, shadow = 0, bad = 0, runs = 0, nExpanded = 0;

    group_begin("diff: cgame (layer 1) vs exe (layer 2) decisions on the same statement and state");
    for (set = 0; set < 2; set++) {
        const char **list = set ? g_planted : g_reached;

        for (i = 0; list[i]; i++) {
            char target[256];
            int  hasTarget = diff_target(list[i], target, sizeof(target));

            for (ls = 0; ls <= 1; ls++) {
                for (st = ST_BASE; st <= (hasTarget ? ST_ENGINE : ST_BASE); st++) {
                    char     copy[BIG_INFO_STRING];
                    qboolean cg, exeDrop, isShadow;

                    begin(ls);
                    if (st != ST_BASE) {
                        diff_state(target, st);
                    }
                    Q_strncpyz(copy, list[i], sizeof(copy));
                    cg       = CG_IsStatementAllowed(copy);
                    g_logLen = 0;
                    g_log[0] = 0;
                    CL_CG_StuffServer(list[i]);
                    frame();
                    frame();
                    exeDrop  = log_has("COVX DROP") ? qtrue : qfalse;
                    isShadow = log_has("COVX VDROP shadow") ? qtrue : qfalse;
                    runs++;

                    if (cg && !exeDrop) {
                        agreeAllow++;
                    } else if (!cg && exeDrop) {
                        agreeDeny++;
                    } else if (cg && exeDrop && isShadow) {
                        int k, dup = 0;

                        /* reviewed class: exe stricter, a registered command behind an implicit clause. A SHIPPED
                         * statement in its real (base) state landing here would be a coop regression. */
                        shadow++;
                        expect(set == 1 || st != ST_BASE, "diff", "shadow-on-shipped-statement", list[i]);
                        for (k = 0; k < nShadowSeen; k++) {
                            dup |= !strcmp(shadowSeen[k], list[i]);
                        }
                        if (!dup && nShadowSeen < 128) {
                            shadowSeen[nShadowSeen++] = list[i];
                        }
                    } else {
                        char what[400];
                        bad++;
                        Com_sprintf(what, sizeof(what), "ls=%d state=%d cgame=%s exe=%s :: %.200s", ls, st,
                                    cg ? "allow" : "deny", exeDrop ? "drop" : "allow", list[i]);
                        expect(0, "diff", cg ? "exe-stricter-unreviewed" : "exe-looser-than-cgame", what);
                    }
                }
            }
        }
    }
    /* TRAPS T14 gap: a statement a server-origin exec or vstr EXPANDS into is one layer 1 never sees, so only
     * layer 2 judges it - and a denial there silently eats a line of a shipped cfg or cvar value instead of
     * failing a test. Every such statement must be allowed on its own, in its real (base) state. */
    for (i = 0; g_reached[i]; i++) {
        if (!g_reachedExpanded[i]) {
            continue;
        }
        for (ls = 0; ls <= 1; ls++) {
            char what[400];

            begin(ls);
            Cmd_TokenizeString(g_reached[i]);
            nExpanded++;
            Com_sprintf(what, sizeof(what), "ls=%d :: %.200s", ls, g_reached[i]);
            expect(Cmd_IsServerLineAllowed(1), "diff", "expanded-line-denied", what);
        }
    }

    printf("  diff runs=%d  agree-allow=%d agree-deny=%d shadow(reviewed, exe stricter)=%d divergent=%d\n", runs,
           agreeAllow, agreeDeny, shadow, bad);
    printf("  exec/vstr-expanded statements checked=%d\n", nExpanded);
    for (i = 0; i < nShadowSeen; i++) {
        printf("  shadow-class statement: %s\n", shadowSeen[i]);
    }
    expect(bad == 0, "diff", "no-unreviewed-divergence", "cgame and exe disagree outside the SHADOW class");
    expect(shadow > 0, "diff", "shadow-class-exercised", "the SHADOW planted statements never reached the exe rule");
    group_end("diff");
}
#endif

/* ===================================================================== group: attack */
typedef struct {
    char        kind; /* S server stufftext, F frame, L local text, N engine runs nextmap (cl_cin.cpp),
                         I server CS_SYSTEMINFO configstring, D drop a cvar (the state before its cfg ran) */
    const char *text;
} step_t;

typedef struct {
    const char *name;
    step_t      steps[8];
    const char *payload;   /* trace needle proving the attack RAN (NULL: judged by the depth drop) */
    int         l1Closed;  /* layer 1 (SEC1) already drops it at reception */
    int         l1Skip;    /* would never terminate on an exe without layer 2 */
    int         newcgRuns; /* new cgame on the previous exe (layer 1 only): does the payload still run */
    const char *covx;      /* the COVX-only needle layer 2 must print (TRAPS T14: never a COVC line) */
} attack_t;

static const attack_t g_attacks[] = {
    {"split-same-snapshot",      {{'S', "seta coop_x writeconfig l2a1.cfg"}, {'S', "vstr coop_x"}, {'F'}},
     "RUN writeconfig l2a1.cfg",      0, 0, 1, "COVX DROP origin=server depth=1 writeconfig l2a1.cfg"},
    {"split-nested",             {{'S', "seta coop_a vstr coop_b"}, {'S', "seta coop_b writeconfig l2a2.cfg"}, {'S', "vstr coop_a"}, {'F'}},
     "RUN writeconfig l2a2.cfg",      0, 0, 1, "COVX DROP origin=server depth=2 writeconfig l2a2.cfg"},
    {"wait-deferred",            {{'S', "wait;seta coop_w writeconfig l2a3.cfg"}, {'F'}, {'S', "vstr coop_w"}, {'F'}, {'F'}},
     "RUN writeconfig l2a3.cfg",      0, 0, 1, "COVX DROP origin=server depth=1 writeconfig l2a3.cfg"},
    {"exec-trampoline-t01",      {{'S', "seta coop_loCmt01 writeconfig l2a4.cfg"}, {'S', "exec ui/loadout/t01.cfg"}, {'F'}},
     "RUN writeconfig l2a4.cfg",      0, 0, 0, "COVX VDROP guard coop_loCmt01"},
    {"exec-trampoline-expand",   {{'S', "seta coop_x writeconfig l2a5.cfg"}, {'S', "exec ui/coop_sec2t/tramp.cfg"}, {'F'}},
     "RUN writeconfig l2a5.cfg",      0, 0, 1, "COVX DROP origin=server depth=2 writeconfig l2a5.cfg"},
    {"parser-comment",           {{'S', "echo /**/writeconfig l2a6.cfg"}, {'F'}},
     "RUN writeconfig l2a6.cfg",      1, 0, 0, "COVX DROP origin=server depth=0 writeconfig l2a6.cfg"},
    {"parser-cr",                {{'S', "echo x\rwriteconfig l2a6b.cfg"}, {'F'}},
     "RUN writeconfig l2a6b.cfg",     1, 0, 0, "COVX DROP origin=server depth=0 writeconfig l2a6b.cfg"},
    {"seta-vstr-one-text",       {{'S', "seta coop_x writeconfig l2a7.cfg;vstr coop_x"}, {'F'}},
     "RUN writeconfig l2a7.cfg",      1, 0, 0, "COVX DROP origin=server depth=1 writeconfig l2a7.cfg"},
    {"boot-laundering",          {{'S', "seta coop_fxPoolStep writeconfig l2a8.cfg"}, {'F'}, {'L', "vstr coop_fxPoolStep\n"}, {'F'}},
     "RUN writeconfig l2a8.cfg",      0, 0, 0, "COVX VDROP refuse coop_fxPoolStep"},
    {"boot-laundering-shadowup", {{'S', "seta coop_shadowUpStep writeconfig l2a8b.cfg"}, {'F'}, {'L', "vstr coop_shadowUpStep\n"}, {'F'}},
     "RUN writeconfig l2a8b.cfg",     0, 0, 0, "COVX VDROP refuse coop_shadowUpStep"},
    {"tile-click-laundering",    {{'S', "seta coop_loCmt01 writeconfig l2a9.cfg"}, {'F'}, {'L', "exec ui/loadout/t01.cfg\n"}, {'F'}},
     "RUN writeconfig l2a9.cfg",      0, 0, 0, "COVX VDROP guard coop_loCmt01"},
    {"menumusic-laundering",     {{'S', "set ui_menuMusicNext writeconfig l2a10.cfg"}, {'F'}, {'L', "vstr ui_menuMusicNext\n"}, {'F'}},
     "RUN writeconfig l2a10.cfg",     0, 0, 0, "COVX VDROP refuse ui_menuMusicNext"},
    {"shadow-user-cvar",         {{'S', "set writeconfig 1"}, {'F'}, {'S', "writeconfig l2a11.cfg"}, {'F'}},
     "RUN writeconfig l2a11.cfg",     0, 0, 1, "COVX VDROP shadow writeconfig"},
    {"shadow-coop-command",      {{'S', "coop_join evil.host 12203"}, {'F'}},
     "RUN coop_join evil.host 12203", 0, 0, 1, "COVX VDROP shadow coop_join"},
    {"runaway-vstr",             {{'S', "seta coop_loop vstr coop_loop"}, {'S', "vstr coop_loop"}, {'F'}},
     NULL,                            0, 1, 0, "COVX VDROP depth"},
    {"namebus-via-exec",         {{'S', "exec ui/coop_sec2t/nb.cfg"}, {'F'}},
     "SET name=Player ,ga",           0, 0, 1, "COVX VDROP namebus ,ga"},
    {"nextmap-laundering",       {{'S', "set nextmap writeconfig l2a15.cfg"}, {'F'}, {'N'}, {'F'}},
     "RUN writeconfig l2a15.cfg",     0, 0, 0, "COVX VDROP refuse nextmap"},
    /* the systeminfo configstring is the third writer of a client cvar, and neither command filter sees it:
     * plant a guarded cvar before the armory's init.cfg has created it, then let a tile click vstr it */
    {"sysinfo-guarded-plant",
     {{'D', "coop_loCmt01"},
      {'I', "\\sv_serverid\\7\\coop_loCmt01\\echo I16;writeconfig l2a16.cfg"},
      {'L', "exec ui/loadout/t01.cfg\n"},
      {'F'}},
     "RUN writeconfig l2a16.cfg",     0, 0, 1, "COVX SYSINFO skip coop_loCmt01"},
    {NULL}
};

static void group_attack(void)
{
    const attack_t *a;

    group_begin("attack: layer-1-only build RUNS it, layer 2 drops it with COVX");
    for (a = g_attacks; a->name; a++) {
        const step_t *s;
        int           ran;

#if defined(ARM_L1) || defined(ARM_NEWCG) || defined(ARM_L1_153)
        if (a->l1Skip) {
            printf("  skip  %-26s (would never terminate on an exe without layer 2)\n", a->name);
            continue;
        }
#endif
        begin(0);
        for (s = a->steps; s->kind; s++) {
            switch (s->kind) {
            case 'S':
                recv_stufftext(s->text);
                break;
            case 'F':
                frame();
                break;
            case 'L':
                Cbuf_AddText(s->text);
                break;
            case 'N':
                Cbuf_ExecuteText(EXEC_APPEND, va("%s\n", Cvar_VariableString("nextmap")));
                break;
            case 'I':
                CL_SystemInfoSetCvars(s->text);
                break;
            case 'D':
                cv_delete(s->text);
                break;
            }
        }
        ran = a->payload ? trace_has(a->payload) : 0;
#if defined(ARM_L1)
        if (a->l1Closed) {
            expect(!ran, "attack", a->name, "layer 1 already refuses this at reception");
        } else {
            expect(ran, "attack", a->name, "the layer-1-only build must RUN the payload (the hole is real)");
        }
#elif defined(ARM_NEWCG)
        expect(ran == a->newcgRuns, "attack", a->name,
               a->newcgRuns ? "new cgame on the previous exe: stated residual must still RUN (no layer 2 there)"
                            : "new cgame on the previous exe: the new layer 1 must refuse it");
#elif defined(ARM_L1_153)
        /* corpus-trace baseline arm only (build.bat runs it with --only corpus): the v1.5.3 pair's attack
         * behaviour is not this test's subject, and asserting it here would just restate the L1 arm. */
        (void)ran;
#elif defined(ARM_L2)
        expect(!ran, "attack", a->name, "layer 2 alone must not run the payload");
        expect(log_has(a->covx), "attack", a->name, a->covx);
#else
        expect(!ran, "attack", a->name, "the new pair must not run the payload");
        if (!a->payload) {
            expect(log_has("VDROP depth"), "attack", a->name, "runaway vstr terminated by a depth drop");
        }
#endif
    }
    group_end("attack");
}

/* ===================================================================== group: origin scoping */
#ifdef HAS_L2
static void group_origin(void)
{
    char pad[256];
    int  k;

    group_begin("origin: per-byte tag through InsertText shift, Execute memmove, nesting, EXEC_NOW");

    /* O1 one pass, server then local */
    begin(0);
    Cbuf_AddTextOrigin("rec_srv1\n", CMD_ORIGIN_SERVER);
    Cbuf_AddText("rec_loc1\n");
    frame();
    expect(!trace_has("RUN rec_srv1") && log_has("COVX DROP origin=server depth=0 rec_srv1"), "origin", "O1-server-line", "dropped at depth 0");
    expect(trace_has("RUN rec_loc1"), "origin", "O1-local-line", "the following local line runs");

    /* O2 Cbuf_InsertText shift: a long server vstr line leaves stale SERVER tags where the local line lands */
    begin(0);
    Cvar_Set2("coop_v", "rec_inner;echo INNER_OK", qfalse);
    for (k = 0; k < 60; k++) {
        pad[k] = ' ';
    }
    pad[60] = 0;
    Cbuf_AddTextOrigin(va("vstr coop_v%s\n", pad), CMD_ORIGIN_SERVER);
    Cbuf_AddText("rec_l2\n");
    frame();
    expect(log_has("COVX DROP origin=server depth=1 rec_inner"), "origin", "O2-expansion-depth1", "vstr expansion inherits server origin");
    expect(trace_has("P:INNER_OK"), "origin", "O2-expansion-allowed", "an allowed statement of the expansion runs");
    expect(trace_has("RUN rec_l2"), "origin", "O2-shifted-local", "the local line moved by the insert stays local");

    /* O3 Cbuf_Execute memmove: the server line slides into bytes a local line owned */
    begin(0);
    Cbuf_AddText("rec_l3\n");
    Cbuf_AddTextOrigin("rec_s3\n", CMD_ORIGIN_SERVER);
    frame();
    expect(trace_has("RUN rec_l3"), "origin", "O3-local-first", "local line runs");
    expect(!trace_has("RUN rec_s3") && log_has("COVX DROP origin=server depth=0 rec_s3"), "origin", "O3-moved-server", "the moved server line keeps its origin");

    /* O4 the armory resend chain under SERVER origin: vstr -> vstr -> exec -> vstr (real files) */
    begin(0);
    Cvar_Set2("coop_loCcur", "vstr coop_loC1", qfalse);
    Cvar_Set2("coop_loC1", "exec ui/loadout/w01_s1.cfg", qfalse);
    Cbuf_AddTextOrigin("vstr coop_loCcur\n", CMD_ORIGIN_SERVER);
    Cbuf_AddText("rec_after\n");
    Cbuf_AddTextOrigin("rec_srv_after\n", CMD_ORIGIN_SERVER);
    frame();
    frame();
    expect(trace_has("SET name=Player ,w101"), "origin", "O4-armory-chain", "depth-3 server chain applies the pick");
    expect(trace_has("RUN rec_after"), "origin", "O4-local-after", "local line after the chain does not inherit");
    expect(log_has("COVX DROP origin=server depth=0 rec_srv_after"), "origin", "O4-server-after", "a later server line is depth 0, not the chain's depth");
    {
        const char *p = strstr(g_log, "COVX DROP");
        expect(p && strstr(p, "rec_srv_after") && !strstr(p + 9, "COVX DROP"), "origin", "O4-no-other-drop",
               "the only COVX drop is the planted server line");
    }

    /* O5 depth is counted through vstr and exec: leaf at depth 4 */
    begin(0);
    Cvar_Set2("coop_d1", "vstr coop_d2", qfalse);
    Cvar_Set2("coop_d2", "exec ui/coop_sec2t/d3.cfg", qfalse);
    Cvar_Set2("coop_d4", "rec_leaf", qfalse);
    Cbuf_AddTextOrigin("vstr coop_d1\n", CMD_ORIGIN_SERVER);
    frame();
    expect(!trace_has("RUN rec_leaf") && log_has("COVX DROP origin=server depth=4 rec_leaf"), "origin", "O5-depth4-leaf", "vstr->exec->vstr leaf keeps server origin at depth 4");

    /* O6 a server wait straddling two Execute calls with local text queued between */
    begin(0);
    Cbuf_AddTextOrigin("wait;rec_w\n", CMD_ORIGIN_SERVER);
    frame();
    Cbuf_AddText("rec_wl\n");
    frame();
    expect(!trace_has("RUN rec_w\n") && log_has("COVX DROP origin=server depth=0 rec_w"), "origin", "O6-deferred-server", "wait-deferred server remainder still filtered");
    expect(trace_has("RUN rec_wl"), "origin", "O6-local-between", "local text queued during the wait runs");

    /* O7 EXEC_NOW inside a server line runs engine-hardcoded text as LOCAL */
    begin(0);
    Cbuf_AddTextOrigin("pushmenu_teamselect\n", CMD_ORIGIN_SERVER);
    Cbuf_AddTextOrigin("pushmenu sec2now\n", CMD_ORIGIN_SERVER);
    frame();
    Cbuf_AddTextOrigin("echo S7\n", CMD_ORIGIN_SERVER);
    frame();
    Cbuf_ExecuteText(EXEC_NOW, "rec_now7\n");
    expect(trace_has("RUN ui_getplayermodel"), "origin", "O7-teamselect-execnow", "EXEC_NOW under a server command is local");
    expect(trace_has("RUN rec_nowfile"), "origin", "O7-execnow-exec-cfg", "an EXEC_NOW exec's file is local");
    expect(trace_has("RUN rec_now7"), "origin", "O7-execnow-after-server", "EXEC_NOW right after a server line is local");
    expect(!log_has("COVX DROP"), "origin", "O7-no-drop", "nothing in the EXEC_NOW paths was filtered");

    /* O8 alias expansion inherits the line's origin */
    begin(0);
    Cmd_Alias("subtitle3", "rec_al\n");
    Cbuf_AddTextOrigin("subtitle3\n", CMD_ORIGIN_SERVER);
    frame();
    expect(!trace_has("RUN rec_al") && log_has("COVX DROP origin=server depth=1 rec_al"), "origin", "O8-alias-server", "alias expansion of a server line is server depth 1");
    begin(0);
    Cbuf_AddText("subtitle3\n");
    frame();
    expect(trace_has("RUN rec_al"), "origin", "O8-alias-local", "the same alias run locally is not filtered");

    /* O9 a rejected insert (overflow) leaves every remaining tag intact */
    begin(0);
    Cvar_Set2("coop_big", va("echo %0200d", 0), qfalse);
    Cbuf_AddTextOrigin("vstr coop_big\n", CMD_ORIGIN_SERVER);
    {
        static char fill[131072];
        int         n = 131072 - 14 - 9 - 9 - 120;
        memset(fill, '\n', n);
        fill[n] = 0;
        Cbuf_AddText(fill);
    }
    Cbuf_AddText("rec_ov_l\n");
    Cbuf_AddTextOrigin("rec_ov_s\n", CMD_ORIGIN_SERVER);
    frame();
    expect(log_has("Cbuf_InsertText overflowed"), "origin", "O9-overflow-hit", "the expansion was refused for size");
    expect(trace_has("RUN rec_ov_l"), "origin", "O9-local-after-overflow", "local line intact");
    expect(log_has("COVX DROP origin=server depth=0 rec_ov_s"), "origin", "O9-server-after-overflow", "server line intact");

    /* O11 a server fragment with no newline cannot shed its origin by merging into local text */
    begin(0);
    Cbuf_AddTextOrigin("rec_mA", CMD_ORIGIN_SERVER);
    Cbuf_AddText("rec_mB\n");
    frame();
    expect(log_has("COVX DROP origin=server depth=0 rec_mArec_mB"), "origin", "O11-merge-drop", "merged line is server origin and dropped");

    /* O12 Cmd_StuffServer terminates its own line */
    begin(0);
    CL_CG_StuffServer("rec_ns");
    Cbuf_AddText("rec_nl\n");
    frame();
    expect(log_has("COVX DROP origin=server depth=0 rec_ns"), "origin", "O12-stuffserver", "server text dropped");
    expect(trace_has("RUN rec_nl"), "origin", "O12-own-newline", "the next local line is separate and local");

    /* O13 leaving a server drops the bytes it queued; the local text around them survives, in order */
    begin(0);
    Cbuf_AddText("rec_l3\n");
    Cbuf_AddTextOrigin("rec_s3\n", CMD_ORIGIN_SERVER);
    Cbuf_AddText("echo LOC_A\n");
    Cbuf_AddTextOrigin("wait;rec_srv1", CMD_ORIGIN_SERVER); /* unterminated: would merge with the next local text */
    Cbuf_AddText("echo LOC_B\n");
    Cbuf_RemoveServerText();
    frame();
    {
        const char *a = strstr(g_trace, "RUN rec_l3");
        const char *b = strstr(g_trace, "P:LOC_A");
        const char *c = strstr(g_trace, "P:LOC_B");

        expect(a && b && c && a < b && b < c, "origin", "O13-strip-local-order",
               "every local line still ran, in its original order");
    }
    expect(!trace_has("RUN rec_s3") && !trace_has("RUN rec_srv1"), "origin", "O13-strip-server",
           "the server-tagged lines are gone");
    expect(!log_has("COVX DROP"), "origin", "O13-strip-clean", "nothing server-origin was left to drop");

    /* O14 a stufftext whose newline does not fit is not added at all: half a line would stay open and swallow
     * the next local text into a server-origin line */
    begin(0);
    {
        static char fill[131072];
        int         n = 131072 - (int)strlen("rec_ns2") - 1;

        memset(fill, '\n', n);
        memcpy(fill + n - 5, "wait\n", 5); /* stop the frame with the server text still pending */
        fill[n] = 0;
        Cbuf_AddText(fill);
    }
    CL_CG_StuffServer("rec_ns2");
    frame();
    Cbuf_AddText("rec_nl\n");
    frame();
    frame();
    expect(log_has("COVX DROP overflow stufftext rec_ns2"), "origin", "O14-overflow-atomic",
           "the text was refused whole, not added without its newline");
    expect(trace_has("RUN rec_nl") && !trace_has("RUN rec_ns2"), "origin", "O14-no-merge",
           "the local text queued behind it is not swallowed");

#ifdef ARM_OLDCG_ANY
    /* O10 previous cgame.dll on the new exe. coop_join passes the previous cgame's layer 1 (coop_ prefix), so
     * only layer 2 can drop it - and only if the relayed text was identified as SERVER origin. */
    begin(0);
    recv_stufftext("coop_join evil.host 12203");
    CL_CG_Stuff("rec_cglocal\n"); /* cgame's own text */
    frame();
    expect(!trace_has("RUN coop_join") && log_has("COVX VDROP shadow coop_join"), "origin", "O10-oldcgame-tagged",
           "a previous cgame's relay is identified as server origin");
    expect(trace_has("RUN rec_cglocal"), "origin", "O10-oldcgame-own-text", "cgame's own Cmd_Stuff text stays local");
    begin(0);
    Cmd_TokenizeString("stufftext \"rec_mod1\"");
    clcg_after_tokenize();
    CL_CG_Stuff("rec_mod2");
    CL_CG_Stuff("\n");
    frame();
    expect(trace_has("RUN rec_mod2"), "origin", "O10-oldcgame-rewritten", "documented: text a cgame rewrote is unidentifiable and runs local");
#endif

    group_end("origin");
}
#endif

/* ===================================================================== main */
int main(int argc, char **argv)
{
    const char *tracePath = NULL;
    int         i;

    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--only") && i + 1 < argc) {
            g_only = argv[++i];
        } else if (!strcmp(argv[i], "--trace") && i + 1 < argc) {
            tracePath = argv[++i];
        } else if (!strcmp(argv[i], "-v")) {
            g_verbose = 1;
        }
    }

    init_world();
    printf("SEC2 SELFTEST arm=%s\n", ARM_NAME);

    if (want("coop")) {
        group_coop();
    }
    if (want("corpus")) {
        group_corpus(tracePath);
    }
#ifdef HAS_L2
    if (want("guard")) {
        group_guard();
    }
#endif
#ifdef ARM_L12
    if (want("diff")) {
        group_diff();
    }
#endif
    if (want("attack")) {
        group_attack();
    }
#ifdef HAS_L2
    if (want("origin")) {
        group_origin();
    }
#endif

    printf("RESULT arm=%s pass=%d fail=%d\n", ARM_NAME, g_pass, g_fail);
    return g_fail ? 1 : 0;
}
