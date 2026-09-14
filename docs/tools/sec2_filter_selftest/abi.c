/*
 * SEC2 cgame import ABI check. Compiled twice by build.bat: once against the HEAD cg_public.h (the previous exe's
 * clientGameImport_t) and once against the working tree (the new cgame.dll's). The new member must sit exactly
 * where the previous struct ENDED, so a new cgame copying offsetof(clientGameImport_t, Cmd_StuffServer) bytes
 * from a previous exe reads only what that exe wrote, and every earlier member keeps its offset.
 */
/* cg_local.h's prerequisite chain, then whichever cg_public.h the include path selects (head/ first for ABI_HEAD) */
#include "q_shared.h"
#include "tr_types.h"
#include "../fgame/bg_public.h"
#include "cm_public.h"
#include "cg_public.h"

#include <stddef.h>
#include <stdio.h>

int main(void)
{
#ifdef ABI_HEAD
    printf("HEAD sizeof=%u apiversion_off=%u Cmd_Stuff_off=%u R_ClearAllRagdolls_off=%u version=%d\n",
           (unsigned)sizeof(clientGameImport_t), (unsigned)offsetof(clientGameImport_t, apiversion),
           (unsigned)offsetof(clientGameImport_t, Cmd_Stuff), (unsigned)offsetof(clientGameImport_t, R_ClearAllRagdolls),
           CGAME_IMPORT_API_VERSION);
#else
    printf("WORK sizeof=%u apiversion_off=%u Cmd_Stuff_off=%u R_ClearAllRagdolls_off=%u Cmd_StuffServer_off=%u version=%d\n",
           (unsigned)sizeof(clientGameImport_t), (unsigned)offsetof(clientGameImport_t, apiversion),
           (unsigned)offsetof(clientGameImport_t, Cmd_Stuff), (unsigned)offsetof(clientGameImport_t, R_ClearAllRagdolls),
           (unsigned)offsetof(clientGameImport_t, Cmd_StuffServer), CGAME_IMPORT_API_VERSION);
#endif
    return 0;
}
