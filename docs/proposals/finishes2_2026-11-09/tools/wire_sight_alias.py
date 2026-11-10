"""bug-10724: the cgame sight lookups fall back through the generated alias table (cg_adssights_alias.h, gen_sight_alias.py).
    python wire_sight_alias.py <engine tree> [--apply]        binary-safe (CRLF kept), count-asserted

Both lookups map their key FIRST: a finish skin with no iron-sight row of its own is looked up as its base gun - in the iron table and
in the scope table (scopes1025), so a scoped rifle's finish keeps its scope row too. An exact row always wins.
"""
import os
import sys

ENG = sys.argv[1]
APPLY = "--apply" in sys.argv


def edit(rel, pairs):
    p = os.path.join(ENG, *rel.split("/"))
    b = open(p, "rb").read()
    assert b.count(b"\r\n") == b.count(b"\n"), rel
    t = b.decode("latin-1").replace("\r\n", "\n")
    for old, new in pairs:
        assert t.count(old) == 1, (rel, t.count(old), old[:60])
        t = t.replace(old, new)
    out = t.replace("\n", "\r\n").encode("latin-1")
    print("%s: %+d bytes" % (rel, len(out) - len(b)))
    if APPLY:
        open(p, "wb").write(out)


edit("code/cgame/cg_modelanim.c", [("""#include "cg_adssights_scope.h" // [scopes1025]
""", """#include "cg_adssights_scope.h" // [scopes1025]
#include "cg_adssights_alias.h" // [bug-10724]

// HZM coop [bug-10724] a finish SKIN with no row of its own aims as its base gun (cg_adssights_alias.h, docs/tools/gen_sight_alias.py:
// an alias exists only when the variant tik is proven to be the base gun with other shaders). One hop, exact strings - never a
// suffix strip, which would hand a model variant (another mesh) the wrong sights. An exact iron row always wins.
static const char *CG_AdsSightAliasTiki(const char *tikiName)
{
    int i;

    for (i = 0; i < (int)(sizeof(s_adsSights) / sizeof(s_adsSights[0])); i++) {
        if (!Q_stricmp(tikiName, s_adsSights[i].tiki)) {
            return tikiName;
        }
    }
    for (i = 0; i < (int)(sizeof(s_adsSightAlias) / sizeof(s_adsSightAlias[0])); i++) {
        if (!Q_stricmp(tikiName, s_adsSightAlias[i].tiki)) {
            return s_adsSightAlias[i].baseTiki;
        }
    }
    return tikiName;
}
"""), ("""static const adsSight_t *CG_FindAdsSight(const char *tikiName)
{
    int i;

    if (!tikiName || !*tikiName) {
        return NULL;
    }
""", """static const adsSight_t *CG_FindAdsSight(const char *tikiName)
{
    int i;

    if (!tikiName || !*tikiName) {
        return NULL;
    }
    tikiName = CG_AdsSightAliasTiki(tikiName); // [bug-10724]
""")])

edit("code/cgame/cg_view.c", [("""#include "cg_adssights_scope.h" // [scopes1025] scoped rifles (F = objective, R = ocular)
""", """#include "cg_adssights_scope.h" // [scopes1025] scoped rifles (F = objective, R = ocular)
#include "cg_adssights_alias.h" // [bug-10724] finish skins -> their base gun (gen_sight_alias.py)

// HZM coop [bug-10724] the name form of CG_AdsSightAliasTiki (cg_modelanim.c): a finish skin's weapon name with no iron row of its own
// is looked up as its base gun's name. Exact strings, one hop, generated and proven same-mesh - not a suffix strip.
static const char *CG_AdsSightAliasName(const char *wpn)
{
    int i;

    for (i = 0; i < (int)(sizeof(s_adsSights) / sizeof(s_adsSights[0])); i++) {
        if (s_adsSights[i].name && !Q_stricmp(wpn, s_adsSights[i].name)) {
            return wpn;
        }
    }
    for (i = 0; i < (int)(sizeof(s_adsSightAlias) / sizeof(s_adsSightAlias[0])); i++) {
        if (s_adsSightAlias[i].name && s_adsSightAlias[i].baseName && !Q_stricmp(wpn, s_adsSightAlias[i].name)) {
            return s_adsSightAlias[i].baseName;
        }
    }
    return wpn;
}
"""), ("""static const adsSight_t *CG_FindAdsSightByName(const char *wpn)
{
    int i;

    if (!wpn || !*wpn) {
        return NULL;
    }
""", """static const adsSight_t *CG_FindAdsSightByName(const char *wpn)
{
    int i;

    if (!wpn || !*wpn) {
        return NULL;
    }
    wpn = CG_AdsSightAliasName(wpn); // [bug-10724]
""")])
