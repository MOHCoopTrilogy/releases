/* Offline self-test of the bug-3903 merge + wire encoding (fgame/bg_coopsync.h). Build:
   cl /nologo /W3 merge_selftest.c /I <engine>\code\fgame  -> merge_selftest.exe ; exit code 0 = all pass */
#include "bg_coopsync.h"

static char out[COOPSYNC_MAXLEN + 1];
static int  fails = 0;

static void expect(int rule, const char *a, const char *b, const char *want)
{
    int n = CoopSync_Merge(rule, a, b, out);
    if (n < 0 || strcmp(out, want)) {
        printf("FAIL rule=%d a=[%s] b=[%s] got=[%s] (%d) want=[%s]\n", rule, a, b, n < 0 ? "<overflow>" : out, n, want);
        fails++;
    } else {
        printf("ok   rule=%d [%s] + [%s] = [%s]\n", rule, a, b, out);
    }
}

int main(void)
{
    static char enc[COOPSYNC_MAXLEN * 3 + 1], dec[COOPSYNC_MAXLEN + 1];
    const char *raw = "models/weapons/kar98.tik|a b\"c;d$e%f//g~h!i";
    int         n;

    expect(COOPSYNC_MERGE_MAX, "1200", "900", "1200");
    expect(COOPSYNC_MERGE_MAX, "900", "1200", "1200");
    expect(COOPSYNC_MERGE_MAX, "", "77", "77");
    expect(COOPSYNC_MERGE_MAX, "77", "", "77");
    expect(COOPSYNC_MERGE_MAX, "", "", "");
    expect(COOPSYNC_MERGE_MAX, "0", "", "0");
    expect(COOPSYNC_MERGE_CHAL, "k_10:5|q_500:250", "k_10:7|med_1:1", "k_10:7|q_500:250|med_1:1");
    expect(COOPSYNC_MERGE_CHAL, "k_10:9", "k_10:7", "k_10:9");
    expect(COOPSYNC_MERGE_CHAL, "", "a:1", "a:1");
    expect(COOPSYNC_MERGE_CHAL, "ab:1", "a:5", "ab:1|a:5");
    expect(COOPSYNC_MERGE_UNION, "x.tik|perk_a", "perk_a|y.tik", "x.tik|perk_a|y.tik");
    expect(COOPSYNC_MERGE_UNION, "", "", "");
    expect(COOPSYNC_MERGE_UNION_TRAIL, "m1l1_1|m1l1_2|", "m1l1_2|m2l1_3|", "m1l1_1|m1l1_2|m2l1_3|");
    expect(COOPSYNC_MERGE_UNION_TRAIL, "", "m1l1_1|", "m1l1_1|");
    expect(COOPSYNC_MERGE_NEWEST, "old~pend", "", "");
    expect(COOPSYNC_MERGE_NEWEST, "a|b", "c", "c");

    CoopSync_Encode(raw, (int)strlen(raw), enc);
    n = CoopSync_Decode(enc, dec, sizeof(dec));
    if (n != (int)strlen(raw) || strcmp(dec, raw) || strpbrk(enc, " \";$\\%") || strstr(enc, "//")) {
        printf("FAIL encode/decode [%s] -> [%s] -> [%s]\n", raw, enc, dec);
        fails++;
    } else {
        printf("ok   encode [%s]\n", enc);
    }
    if (CoopSync_Decode("!G1", dec, sizeof(dec)) != -1 || CoopSync_Decode("!4", dec, sizeof(dec)) != -1) {
        printf("FAIL malformed decode accepted\n");
        fails++;
    }
    if (CoopSync_ValidId("../x") || CoopSync_ValidId("") || !CoopSync_ValidId("0123456789abcdef0123456789abcdef")) {
        printf("FAIL id validation\n");
        fails++;
    }
    if (CoopSync_ValidContent("a\nb", 3) || !CoopSync_ValidContent("a b~c", 5)) {
        printf("FAIL content validation\n");
        fails++;
    }
    {
        char d1[16], d2[16], d3[16];
        CoopSync_DigestHex(COOPSYNC_MERGE_UNION, "b|a|c", d1);
        CoopSync_DigestHex(COOPSYNC_MERGE_UNION, "a|c|b|a", d2);
        CoopSync_DigestHex(COOPSYNC_MERGE_UNION, "a|c", d3);
        if (strcmp(d1, d2) || !strcmp(d1, d3)) {
            printf("FAIL digest order-independence %s %s %s\n", d1, d2, d3);
            fails++;
        } else {
            printf("ok   digest %s == %s != %s\n", d1, d2, d3);
        }
        CoopSync_DigestHex(COOPSYNC_MERGE_MAX, "", d1);
        CoopSync_DigestHex(COOPSYNC_MERGE_MAX, "5000", d2);
        CoopSync_DigestHex(COOPSYNC_MERGE_UNION_TRAIL, "m1_1|m2_2|", d3);
        if (!strcmp(d1, d2)) {
            printf("FAIL digest xp\n");
            fails++;
        }
        CoopSync_DigestHex(COOPSYNC_MERGE_UNION_TRAIL, "m2_2|m1_1", d1);
        if (strcmp(d1, d3)) {
            printf("FAIL digest trailing bar\n");
            fails++;
        }
    }
    {
        /* '/' travels raw except in "//"; the encoding never contains "//" or '%' */
        const char *p2 = "models/weapons/a.tik|x//y|/";
        CoopSync_Encode(p2, (int)strlen(p2), enc);
        n = CoopSync_Decode(enc, dec, sizeof(dec));
        if (strstr(enc, "//") || strchr(enc, '%') || n != (int)strlen(p2) || strcmp(dec, p2)) {
            printf("FAIL slash encoding [%s]\n", enc);
            fails++;
        } else {
            printf("ok   slash encoding [%s]\n", enc);
        }
    }
    printf("%s (%d failures)\n", fails ? "FAILED" : "ALL PASS", fails);
    return fails ? 1 : 0;
}
