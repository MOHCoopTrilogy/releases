# Engine hunks for the HUD declutter (cgame event feed + game.dll re-join hiding). See hudops.py.
E = "eng"
OPS = [
    # ---- new file: the feed itself
    (E, "code/cgame/cg_coopfeed.c", None, r"C:\mohaa-coop-dev\openmohaa-hzm\code\cgame\cg_coopfeed.c", 0),

    # ---- cgame: route ~f-tagged prints to the feed
    (E, "code/cgame/cg_servercmds.c",
     '#include "cg_servercmds_filter.h"\n',
     '#include "cg_servercmds_filter.h"\n'
     'qboolean CG_CoopFeedIntercept(const char *msg); // HZM coop [user 2026-10-05] event feed (cg_coopfeed.c)\n', 1),
    (E, "code/cgame/cg_servercmds.c",
     '    if (!strcmp(cmd, "print") || !strcmp(cmd, "hudprint")) {\n'
     '        cgi.Printf("%s", cgi.Argv(1));\n',
     '    if (!strcmp(cmd, "print") || !strcmp(cmd, "hudprint")) {\n'
     '        // HZM coop [user 2026-10-05] HUD declutter: a ~f-tagged coop print belongs to the event feed\n'
     '        // (cg_coopfeed.c), which echoes it to the console itself - never to the old message box.\n'
     '        if (CG_CoopFeedIntercept(cgi.Argv(1))) {\n'
     '            return;\n'
     '        }\n'
     '        cgi.Printf("%s", cgi.Argv(1));\n', 1),

    # ---- cgame: init with the module (cvars + the cg_hzmFeed capability exist before the first server print)
    (E, "code/cgame/cg_main.c",
     '#include "cg_local.h"\n',
     '#include "cg_local.h"\n'
     'void CG_CoopFeedInit(void); // HZM coop [user 2026-10-05] event feed (cg_coopfeed.c)\n', 1),
    (E, "code/cgame/cg_main.c",
     '        CG_HzmLt_Init();\n',
     '        CG_HzmLt_Init();\n'
     '        CG_CoopFeedInit(); // HZM coop [user 2026-10-05] event feed: cvars + the cg_hzmFeed userinfo capability\n', 1),

    # ---- cgame: draw it beside the stamina arc
    (E, "code/cgame/cg_drawtools.cpp",
     'static void CG_DrawStaminaArc(void)\n{\n',
     'extern "C" void CG_DrawCoopFeed(qboolean cineHide); // HZM coop [user 2026-10-05] event feed (cg_coopfeed.c)\n\n'
     'static void CG_DrawStaminaArc(void)\n{\n', 1),
    (E, "code/cgame/cg_drawtools.cpp",
     '    CG_DrawStaminaArc();\n',
     '    CG_DrawStaminaArc();\n'
     '    CG_DrawCoopFeed(CG_CoopCineHudActive()); // HZM coop [user 2026-10-05] event feed, bottom-left above health\n', 1),

    # ---- game.dll: remember which clients were carried over from the previous map
    (E, "code/fgame/g_client.cpp",
     '    G_ClientUserinfoChanged(ent, userinfo);\n\n#if 0\n',
     '    G_ClientUserinfoChanged(ent, userinfo);\n\n'
     '    // HZM coop [user 2026-10-05] HUD declutter: a client reconnected by a map change (firstTime == qfalse) is\n'
     '    // "carried over" - Player::Join_DM_Team does not re-announce it in a coop session.\n'
     '    g_hzmCarriedClient[clientNum] = firstTime ? qfalse : qtrue;\n\n#if 0\n', 1),
    (E, "code/fgame/g_client.cpp",
     'const char *G_ClientConnect(int clientNum, qboolean firstTime, qboolean differentMap)\n{\n',
     '// HZM coop [user 2026-10-05] see G_ClientConnect / Player::Join_DM_Team\n'
     'qboolean g_hzmCarriedClient[MAX_CLIENTS];\n\n'
     'const char *G_ClientConnect(int clientNum, qboolean firstTime, qboolean differentMap)\n{\n', 1),

    # ---- game.dll: the health pickup line -> quiet personal feed line in coop (feed-capable client)
    (E, "code/fgame/health.cpp",
     '    gi.SendServerCommand(\n'
     '        player->edict - g_entities,\n'
     '        "print \\"" HUD_MESSAGE_YELLOW "%s\\n\\"",\n'
     '        gi.LV_ConvertString(va("Recovered %d Health", amount))\n'
     '    );\n',
     '    // HZM coop [user 2026-10-05] HUD declutter: in a coop session a feed-capable client (cgame/cg_coopfeed.c advertises\n'
     '    // cg_hzmFeed in its userinfo) gets this as a quiet personal event-feed line (category 2) instead of the old box.\n'
     '    {\n'
     '        ScriptVariable *pCoop = level.vars ? level.vars->GetVariable("coop_mainScriptLoaded") : NULL;\n'
     '        char            ui[MAX_INFO_STRING];\n'
     '        int             cn = player->edict - g_entities;\n'
     '        gi.GetUserinfo(cn, ui, sizeof(ui));\n'
     '        if (g_gametype->integer != GT_SINGLE_PLAYER && pCoop && pCoop->GetType() != VARIABLE_NONE\n'
     '            && Info_ValueForKey(ui, "cg_hzmFeed")[0] == \'1\') {\n'
     '            gi.SendServerCommand(\n'
     '                cn, "print \\"" HUD_MESSAGE_YELLOW "~f2:hp~%s\\n\\"", gi.LV_ConvertString(va("Recovered %d Health", amount))\n'
     '            );\n'
     '            return;\n'
     '        }\n'
     '    }\n'
     '    gi.SendServerCommand(\n'
     '        player->edict - g_entities,\n'
     '        "print \\"" HUD_MESSAGE_YELLOW "%s\\n\\"",\n'
     '        gi.LV_ConvertString(va("Recovered %d Health", amount))\n'
     '    );\n', 1),

    # ---- game.dll: the join broadcast
    (E, "code/fgame/player.cpp",
     'void Player::Join_DM_Team(Event *ev)\n{\n',
     '// HZM coop [user 2026-10-05] HUD declutter - join announcements in a COOP session.\n'
     '// Coop = the coop framework loaded this map (level var coop_mainScriptLoaded, tested by TYPE never value, as\n'
     '// CoopMpPlayerHit does). The MP framework refuses to start when coop is loaded, so an MP session never has it.\n'
     'extern qboolean g_hzmCarriedClient[MAX_CLIENTS];\n\n'
     'static bool HZM_CoopJoinSession(void)\n'
     '{\n'
     '    ScriptVariable *pCoop;\n\n'
     '    if (g_gametype->integer == GT_SINGLE_PLAYER || !level.vars) {\n'
     '        return false;\n'
     '    }\n'
     '    pCoop = level.vars->GetVariable("coop_mainScriptLoaded");\n'
     '    return (pCoop && pCoop->GetType() != VARIABLE_NONE) ? true : false;\n'
     '}\n\n'
     '// A genuinely new player: the event feed for a client whose cgame advertises cg_hzmFeed (cgame/cg_coopfeed.c),\n'
     '// the vanilla chat-white line for any other.\n'
     'static void HZM_CoopJoinAnnounce(const char *text)\n'
     '{\n'
     '    int  i;\n'
     '    char ui[MAX_INFO_STRING];\n\n'
     '    if (g_protocol < protocol_e::PROTOCOL_MOHTA_MIN) {\n'
     '        G_PrintToAllClients(va("%s\\n", text), 2);\n'
     '        return;\n'
     '    }\n'
     '    for (i = 0; i < game.maxclients; i++) {\n'
     '        gentity_t *ent = &g_entities[i];\n'
     '        if (!ent->inuse || !ent->entity || !ent->client) {\n'
     '            continue;\n'
     '        }\n'
     '        gi.GetUserinfo(i, ui, sizeof(ui));\n'
     '        if (Info_ValueForKey(ui, "cg_hzmFeed")[0] == \'1\') {\n'
     '            gi.SendServerCommand(i, "print \\"" HUD_MESSAGE_WHITE "~f1:join~%s\\n\\"", text);\n'
     '        } else {\n'
     '            gi.SendServerCommand(i, "print \\"" HUD_MESSAGE_CHAT_WHITE "%s\\n\\"", text);\n'
     '        }\n'
     '    }\n'
     '}\n\n'
     'void Player::Join_DM_Team(Event *ev)\n{\n', 1),
    (E, "code/fgame/player.cpp",
     '        G_PrintToAllClients(va("%s %s\\n", client->pers.netname, join_message), 2);\n',
     '        // HZM coop [user 2026-10-05] in coop every player re-joins a team on every map load, so this broadcast\n'
     '        // fired once per player per map. A client carried over from the previous map is not news; a new one goes\n'
     '        // to the event feed. Non-coop servers keep the vanilla line.\n'
     '        if (HZM_CoopJoinSession()) {\n'
     '            if (!g_hzmCarriedClient[edict - g_entities]) {\n'
     '                HZM_CoopJoinAnnounce(va("%s %s", client->pers.netname, join_message));\n'
     '            }\n'
     '        } else {\n'
     '            G_PrintToAllClients(va("%s %s\\n", client->pers.netname, join_message), 2);\n'
     '        }\n', 1),
]
