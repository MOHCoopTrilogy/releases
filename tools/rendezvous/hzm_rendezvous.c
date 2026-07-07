/*
 * hzm_rendezvous - MOH Coop Trilogy UDP rendezvous / hole-punch signaler.
 *
 * One tiny UDP service. Hosts register a memorable code; joiners ask for it; the
 * daemon tells BOTH sides the other's public endpoint so their punches cross.
 * Speaks the Quake3 out-of-band framing: FF FF FF FF <text line>.
 *
 * Messages (all OOB text):
 *   host  -> daemon : hzm_rdv_reg <code> <protover>          (repeats every ~20s = keepalive)
 *   daemon-> host   : hzm_rdv_regok <pubip> <pubport> <nonce>
 *   client-> daemon : hzm_rdv_join <code>
 *   daemon-> client : hzm_rdv_peer <hostip> <hostport>
 *   daemon-> host   : hzm_rdv_punchreq <clientip> <clientport> <nonce>
 *
 * Build (Linux/Oracle):  cc -O2 -o hzm_rendezvous hzm_rendezvous.c
 * Build (Windows test):  cl /O2 hzm_rendezvous.c ws2_32.lib
 * Run:                   ./hzm_rendezvous [port]        (default 12301/udp)
 *
 * Codes expire 60s after the last keepalive. Per-IP rate limit: 20 msgs / 10s.
 * No auth beyond the code itself - it is a weak shared secret for friends.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#  include <winsock2.h>
#  include <ws2tcpip.h>
#  pragma comment(lib, "ws2_32.lib")
#  define strtok_r strtok_s
typedef int socklen_t;
#else
#  include <sys/socket.h>
#  include <netinet/in.h>
#  include <arpa/inet.h>
#  include <unistd.h>
#  include <errno.h>
#endif

#define RDV_PORT_DEFAULT 12301
#define MAX_CODES        256
#define CODE_LEN         32
#define CODE_TTL         60   /* seconds since last keepalive */
#define RATE_WINDOW      10   /* seconds */
#define RATE_MAX         20   /* messages per window per IP */
#define RATE_SLOTS       512

typedef struct {
    char               code[CODE_LEN];
    struct sockaddr_in addr;
    unsigned int       nonce;
    time_t             last;
    int                used;
} host_entry_t;

typedef struct {
    unsigned int ip;
    time_t       window;
    int          count;
} rate_entry_t;

static host_entry_t g_hosts[MAX_CODES];
static rate_entry_t g_rates[RATE_SLOTS];

static const unsigned char OOB[4] = {0xff, 0xff, 0xff, 0xff};

static int rate_ok(struct sockaddr_in *from)
{
    unsigned int  ip  = from->sin_addr.s_addr;
    time_t        now = time(NULL);
    rate_entry_t *r   = &g_rates[(ip ^ (ip >> 16)) % RATE_SLOTS];

    if (r->ip != ip || now - r->window >= RATE_WINDOW) {
        r->ip     = ip;
        r->window = now;
        r->count  = 0;
    }
    r->count++;
    return r->count <= RATE_MAX;
}

static host_entry_t *find_code(const char *code)
{
    int i;
    for (i = 0; i < MAX_CODES; i++) {
        if (g_hosts[i].used && !strcmp(g_hosts[i].code, code)) {
            return &g_hosts[i];
        }
    }
    return NULL;
}

static void expire_codes(void)
{
    time_t now = time(NULL);
    int    i;
    for (i = 0; i < MAX_CODES; i++) {
        if (g_hosts[i].used && now - g_hosts[i].last > CODE_TTL) {
            printf("expire: %s\n", g_hosts[i].code);
            g_hosts[i].used = 0;
        }
    }
}

/* MOHAA OOB framing: FF FF FF FF <direction byte> <text>. The direction byte is skipped
 * blindly by both engine readers; 2 = "from a client" which suits a signaling peer. */
static void send_oob(int sock, struct sockaddr_in *to, const char *text)
{
    char buf[512];
    int  len = (int)strlen(text);
    if (len > 500) {
        len = 500;
    }
    memcpy(buf, OOB, 4);
    buf[4] = 2;
    memcpy(buf + 5, text, len);
    sendto(sock, buf, 5 + len, 0, (struct sockaddr *)to, sizeof(*to));
}

/* lowercase + strip anything but [a-z0-9_-]; returns 0 if empty/too long */
static int clean_code(const char *in, char *out)
{
    int n = 0;
    for (; *in && n < CODE_LEN - 1; in++) {
        char c = *in;
        if (c >= 'A' && c <= 'Z') {
            c = (char)(c - 'A' + 'a');
        }
        if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '-') {
            out[n++] = c;
        }
    }
    out[n] = 0;
    return n > 0;
}

int main(int argc, char **argv)
{
    int                port = (argc > 1) ? atoi(argv[1]) : RDV_PORT_DEFAULT;
    int                sock;
    struct sockaddr_in bind_addr;
    unsigned int       nonce_seed;

#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif

    sock = (int)socket(AF_INET, SOCK_DGRAM, 0);
    memset(&bind_addr, 0, sizeof(bind_addr));
    bind_addr.sin_family      = AF_INET;
    bind_addr.sin_addr.s_addr = INADDR_ANY;
    bind_addr.sin_port        = htons((unsigned short)port);
    if (bind(sock, (struct sockaddr *)&bind_addr, sizeof(bind_addr)) != 0) {
        fprintf(stderr, "bind failed on udp/%d\n", port);
        return 1;
    }
    nonce_seed = (unsigned int)time(NULL) ^ 0x5bd1e995u;
    printf("hzm_rendezvous listening on udp/%d\n", port);
    fflush(stdout);

    for (;;) {
        char               pkt[600];
        struct sockaddr_in from;
        socklen_t          fromlen = sizeof(from);
        int                n = (int)recvfrom(sock, pkt, sizeof(pkt) - 1, 0, (struct sockaddr *)&from, &fromlen);
        char              *text, *cmd, *a1, *a2, *save = NULL;

        if (n <= 5 || memcmp(pkt, OOB, 4) != 0) {
            continue;
        }
        if (!rate_ok(&from)) {
            continue;
        }
        expire_codes();

        pkt[n] = 0;
        text   = pkt + 5; /* skip 4-byte marker + MOHAA direction byte */
        /* strip trailing newline(s) */
        while (n > 4 && (pkt[n - 1] == '\n' || pkt[n - 1] == '\r')) {
            pkt[--n] = 0;
        }

        cmd = strtok_r(text, " ", &save);
        if (!cmd) {
            continue;
        }

        if (!strcmp(cmd, "hzm_rdv_reg")) {
            char          code[CODE_LEN];
            host_entry_t *h;
            char          reply[128];

            a1 = strtok_r(NULL, " ", &save);
            if (!a1 || !clean_code(a1, code)) {
                continue;
            }
            h = find_code(code);
            if (h && memcmp(&h->addr.sin_addr, &from.sin_addr, sizeof(from.sin_addr)) != 0) {
                /* someone else owns this code and it has not expired */
                send_oob(sock, &from, "hzm_rdv_err code_taken");
                continue;
            }
            if (!h) {
                int i;
                for (i = 0; i < MAX_CODES; i++) {
                    if (!g_hosts[i].used) {
                        h = &g_hosts[i];
                        break;
                    }
                }
                if (!h) {
                    continue; /* table full */
                }
                memset(h, 0, sizeof(*h));
                strcpy(h->code, code);
                nonce_seed = nonce_seed * 1664525u + 1013904223u;
                h->nonce   = nonce_seed;
                h->used    = 1;
                printf("register: %s -> %s:%d\n", code, inet_ntoa(from.sin_addr), ntohs(from.sin_port));
                fflush(stdout);
            }
            h->addr = from;
            h->last = time(NULL);
            snprintf(reply, sizeof(reply), "hzm_rdv_regok %s %d %u",
                     inet_ntoa(from.sin_addr), ntohs(from.sin_port), h->nonce);
            send_oob(sock, &from, reply);
        } else if (!strcmp(cmd, "hzm_rdv_join")) {
            char          code[CODE_LEN];
            host_entry_t *h;
            char          msg[128];

            a1 = strtok_r(NULL, " ", &save);
            if (!a1 || !clean_code(a1, code)) {
                continue;
            }
            h = find_code(code);
            if (!h) {
                send_oob(sock, &from, "hzm_rdv_err no_such_code");
                continue;
            }
            printf("join: %s from %s:%d\n", code, inet_ntoa(from.sin_addr), ntohs(from.sin_port));
            fflush(stdout);
            /* tell the client where the host is */
            snprintf(msg, sizeof(msg), "hzm_rdv_peer %s %d",
                     inet_ntoa(h->addr.sin_addr), ntohs(h->addr.sin_port));
            send_oob(sock, &from, msg);
            /* tell the host to punch toward the client */
            snprintf(msg, sizeof(msg), "hzm_rdv_punchreq %s %d %u",
                     inet_ntoa(from.sin_addr), ntohs(from.sin_port), h->nonce);
            send_oob(sock, &h->addr, msg);
        }
        (void)a2;
    }
}
