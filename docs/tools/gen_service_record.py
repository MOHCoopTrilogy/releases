import re, os, math
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont
os.chdir(r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod")
def lerp(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(len(a)))
def serif(sz):
    try: return ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf",sz)
    except: return ImageFont.load_default()
def sans(sz,b=False):
    try: return ImageFont.truetype("C:/Windows/Fonts/verdanab.ttf" if b else "C:/Windows/Fonts/verdana.ttf",sz)
    except: return ImageFont.load_default()

TW=TH=2048; RX,RY,RW,RH=80,8,480,462
SCALE=TW/640.0        # texture px per .urc unit - the two coordinate spaces this file juggles
BP_LABEL_RECT=None    # set by page_bg once the blueprint caption is laid out and verified
def sx(tx): return RX + tx*RW/TW
def sy(ty): return RY + ty*RH/TH
ROW0=362
BARX=1300; BARW=470; BARH=44; CNTX=BARX+BARW+22

# [user 08-07] friendly display name for a challenge's reward field (chal_def's 7th arg) -
# either a skin/helmet/weapon .tik path or a "perk_*" keyword. Verified all 180 reward values
# used across challenges.scr are unique (no duplicates), so this is a real curated table, not
# a mechanical guess - the earlier strip-prefix/title-case version produced unreadable results
# ("Ital Volhat", "American Assault Engineer2"). Keyed on the raw reward string exactly as it
# appears in chal_def. Falls back to the old mechanical transform ONLY for a reward value added
# later that hasn't been curated yet, so nothing silently goes blank.
REWARD_NAMES = {
    # [bug-2079] the three Elite rewards repointed off the free default uniform
    "models/player/american_28th_private.tik": "28th Infantry Rifleman",
    "models/player/34th_Infantery_Division_sniper.tik": "34th Infantry Marksman",
    "models/player/american_1st_rangers_captain.tik": "1st Rangers Captain",

    # [bug-2080] armory gloves. Curated here so the Service Record hover shows the display
    # name rather than the mechanical transform of the token id.
    "glv_leather": "Leather Gloves",
    "glv_wool": "Wool Knit Gloves",
    "glv_uswinter": "US Winter Gloves",
    "glv_mittens": "Wool Mittens",
    "glv_seaman": "Seaman's Gloves",
    "glv_alpine": "Alpine Hands",

    # weapon finishes (the armory strip - symbolic rewards probed from the unlock store)
    "finish_gold": "Gold Weapon Finish",
    "finish_chrome": "Chrome Weapon Finish",
    "finish_blued": "Blued Weapon Finish",
    "finish_bloody": "Bloody Weapon Finish",
    "finish_camo_woodland": "Woodland Camo Finish",
    "finish_camo_winter": "Winter Camo Finish",
    "finish_camo_desert": "Desert Camo Finish",
    # helmets
    # [user 2026-08-18] curated from the authoritative in-game tables (helmet.scr names,
    # armory roster names) - these 25 were falling back to the mechanical transform
    "models/coop_helmets/coop_helmet_avglasses.tik": "Aviator Glasses",
    "models/coop_helmets/coop_helmet_brit_mk2.tik": "British Mk II Helmet",
    "models/coop_helmets/coop_helmet_brit_offcap2.tik": "British Officer's Cap",
    "models/coop_helmets/coop_helmet_brit_paramask.tik": "Para Helmet + Mask",
    "models/coop_helmets/coop_helmet_brit_tankberet.tik": "Tanker Beret + Goggles",
    "models/coop_helmets/coop_helmet_eyeglasses.tik": "Eyeglasses",
    "models/coop_helmets/coop_helmet_gasmask.tik": "Gas Mask",
    "models/coop_helmets/coop_helmet_ger_crusher.tik": "German Crusher Cap",
    "models/coop_helmets/coop_helmet_ger_splinter.tik": "Splinter Camo Helmet",
    "models/coop_helmets/coop_helmet_ss_mutze.tik": "SS Field Cap",
    "models/coop_helmets/coop_helmet_ss_officerhat.tik": "SS Officer's Hat",
    "models/coop_helmets/coop_helmet_us_gasmask.tik": "US Gas Mask",
    "models/coop_helmets/coop_helmet_woolcap.tik": "Wool Cap",
    "models/weapons/30calportable.tik": "Browning M1919 (Deployable)",
    "models/weapons/bazooka.tik": "Bazooka",
    "models/weapons/delisle.tik": "DeLisle Carbine",
    "models/weapons/dp28.tik": "DP-28",
    "models/weapons/johnson_m1941.tik": "Johnson M1941",
    "models/weapons/m10_revolver.tik": "S&W M10 .38",
    "models/weapons/mauser_c96.tik": "Mauser C96",
    "models/weapons/mg42portable.tik": "MG42 (Deployable)",
    "models/weapons/mp40.tik": "MP40",
    "models/weapons/panzerschreck.tik": "Panzerschreck",
    "models/weapons/thompsonsmg_gold.tik": "Gold Thompson",
    "models/weapons/uk_w_piat.tik": "PIAT",
    "models/coop_helmets/coop_helmet_29th.tik": "29th Infantry Helmet",
    "models/coop_helmets/coop_helmet_29thnet.tik": "29th Infantry Netted Helmet",
    "models/coop_helmets/coop_helmet_brit_beret.tik": "British Beret",
    "models/coop_helmets/coop_helmet_brit_cmdhat.tik": "British Commando Cap",
    "models/coop_helmets/coop_helmet_brit_offhat.tik": "British Officer's Cap",
    "models/coop_helmets/coop_helmet_brit_plthat.tik": "British Pilot's Cap",
    "models/coop_helmets/coop_helmet_brit_tankhat.tik": "British Tanker's Beret",
    "models/coop_helmets/coop_helmet_captain.tik": "Captain's Cap",
    "models/coop_helmets/coop_helmet_dak_hat.tik": "Afrika Korps Cap",
    "models/coop_helmets/coop_helmet_engineer.tik": "Engineer's Helmet",
    "models/coop_helmets/coop_helmet_ger_beret.tik": "German Beret",
    "models/coop_helmets/coop_helmet_ger_covered.tik": "German Covered Helmet",
    "models/coop_helmets/coop_helmet_ger_creasecap.tik": "German Crusher Cap",
    "models/coop_helmets/coop_helmet_ger_hat.tik": "German Field Cap",
    "models/coop_helmets/coop_helmet_ger_helmet.tik": "German Helmet",
    "models/coop_helmets/coop_helmet_ger_helmet_sh.tik": "German Helmet (Winter)",
    "models/coop_helmets/coop_helmet_ger_offhat_sh.tik": "German Officer's Cap (Winter)",
    "models/coop_helmets/coop_helmet_ger_officercap.tik": "German Officer's Cap",
    "models/coop_helmets/coop_helmet_ger_tankhat.tik": "German Tanker's Beret",
    "models/coop_helmets/coop_helmet_ital_infhat.tik": "Italian Infantry Cap",
    "models/coop_helmets/coop_helmet_ital_para.tik": "Italian Paratrooper Helmet",
    "models/coop_helmets/coop_helmet_ital_volhat.tik": "Italian Volunteer Militia Cap",
    "models/coop_helmets/coop_helmet_ltnt.tik": "Lieutenant's Cap",
    "models/coop_helmets/coop_helmet_medic.tik": "Medic's Helmet",
    "models/coop_helmets/coop_helmet_net.tik": "Netted Helmet",
    "models/coop_helmets/coop_helmet_net_cig.tik": "Netted Helmet with Cigarette",
    "models/coop_helmets/coop_helmet_plain.tik": "Plain Helmet",
    "models/coop_helmets/coop_helmet_sergeant.tik": "Sergeant's Helmet",
    "models/coop_helmets/coop_helmet_soviet_hat.tik": "Soviet Field Cap",
    "models/coop_helmets/coop_helmet_ssncocap.tik": "SS NCO Cap",
    "models/coop_helmets/coop_helmet_uk_helmet.tik": "British Helmet",
    "models/coop_helmets/coop_helmet_us_tankhat.tik": "American Tanker's Cap",
    # British / misc allied skins
    "models/player/Allied_British_1_snow_RADIO.tik": "British Winter Radioman",
    "models/player/Allied_British_1_snow_helmet1.tik": "British Winter Soldier",
    "models/player/Allied_British_rifleman.tik": "British Rifleman",
    "models/player/allied_101st_captain.tik": "101st Airborne Captain",
    "models/player/allied_101st_infantry.tik": "101st Airborne Infantry",
    "models/player/allied_101st_scout.tik": "101st Airborne Scout",
    "models/player/allied_17thAirb_soldierbloody.tik": "17th Airborne Soldier (Wounded)",
    "models/player/allied_1st_manon.tik": "Manon",
    "models/player/allied_1st_sniper.tik": "1st Infantry Sniper",
    "models/player/allied_332nd_Fighter_Pilot.tik": "332nd Fighter Group Pilot",
    "models/player/allied_501st_pir_scout.tik": "501st PIR Scout",
    "models/player/allied_501st_pir_soldier.tik": "501st PIR Soldier",
    "models/player/allied_82ndair.tik": "82nd Airborne Trooper",
    "models/player/allied_Airborne_101E_Col_Sink.tik": "Col. Robert Sink",
    "models/player/allied_Airborne_101E_Corp_Liebgott.tik": "Cpl. Liebgott",
    "models/player/allied_Airborne_101E_Lt_Speirs.tik": "Lt. Speirs",
    "models/player/allied_British_Officer.tik": "British Officer",
    "models/player/allied_Commanding_Officer.tik": "Commanding Officer",
    "models/player/allied_british_cmd.tik": "Lt. Terry Lyndon",
    "models/player/ramsey.tik": "Captain Ramsey",
    "models/player/mcmartin.tik": "McMartin",
    "models/player/johnson_e2l1.tik": "Private Johnson",
    "models/player/hammon.tik": "Sergeant Hammon",
    "models/player/glenn.tik": "Medic Glenn",
    "models/player/campbell.tik": "Engineer Campbell",
    "models/player/cappy_sh.tik": "Cappy",
    "models/player/hildebrandt.tik": "Colonel Hildebrandt",
    "models/player/wilson_sh.tik": "Private Wilson",
    "models/player/captain_ike.tik": "Captain Ike",
    "models/player/captain_t2l4.tik": "The Captain",
    "models/player/claus.tik": "Claus",
    "models/player/burton.tik": "Captain Burton",
    "models/player/gobbs.tik": "Gobbs",
    "models/player/whittaker.tik": "Whittaker",
    "models/player/allied_airborne.tik": "Airborne Trooper",
    "models/player/allied_airborne_101st_1.tik": "101st Airborne Trooper I",
    "models/player/allied_airborne_101st_2.tik": "101st Airborne Trooper II",
    "models/player/allied_airborne_101st_sgt.tik": "101st Airborne Sergeant",
    "models/player/allied_airborne_82nd_1.tik": "82nd Airborne Trooper I",
    "models/player/allied_airborne_82nd_2.tik": "82nd Airborne Trooper II",
    "models/player/allied_airborne_82nd_3.tik": "82nd Airborne Trooper III",
    "models/player/allied_airborne_82nd_sgt.tik": "82nd Airborne Sergeant",
    "models/player/allied_airborne_elite.tik": "Elite Airborne Trooper",
    "models/player/allied_big_red_one.tik": "Big Red One Soldier",
    "models/player/allied_british_6th_airborne_captain.tik": "6th Airborne Captain",
    "models/player/allied_british_6th_airborne_paratrooper.tik": "6th Airborne Paratrooper",
    "models/player/allied_british_cmd.tik": "British Commando",
    "models/player/allied_british_general.tik": "British General",
    "models/player/allied_british_paratroops.tik": "British Paratrooper",
    "models/player/allied_british_paratroops_helmet.tik": "British Paratrooper (Helmet)",
    "models/player/allied_british_paratroops_officer.tik": "British Paratroop Officer",
    "models/player/allied_british_polish_para.tik": "Polish Paratrooper",
    "models/player/allied_british_tank.tik": "British Tank Crewman",
    "models/player/allied_british_tank_corporal.tik": "British Tank Corporal",
    "models/player/allied_camo_108thMGST.tik": "108th MG Support Trooper",
    "models/player/allied_capt_recon.tik": "Recon Captain",
    "models/player/allied_infantry.tik": "Infantryman",
    "models/player/allied_manon.tik": "Manon",
    "models/player/allied_medic.tik": "Combat Medic",
    "models/player/allied_norwegian_resistance.tik": "Norwegian Resistance Fighter",
    "models/player/allied_pilot.tik": "Allied Pilot",
    "models/player/allied_russian_Pvt.tik": "Soviet Private",
    "models/player/allied_russian_corporal.tik": "Soviet Corporal",
    "models/player/allied_russian_crazy_boris.tik": "Crazy Boris",
    "models/player/allied_russian_recon_scout.tik": "Soviet Recon Scout",
    "models/player/allied_russian_recon_soldier.tik": "Soviet Recon Soldier",
    "models/player/allied_russian_seaman.tik": "Soviet Seaman",
    "models/player/allied_sas.tik": "SAS Commando",
    "models/player/allied_sniper.tik": "Allied Sniper",
    "models/player/allied_tanker.tik": "Allied Tank Crewman",
    "models/player/allied_tanker2.tik": "Allied Tank Crewman II",
    "models/player/allied_technician.tik": "Allied Technician",
    "models/player/allied_us_mask.tik": "American Soldier (Gas Mask)",
    "models/player/allied_us_tank.tik": "American Tank Crewman",
    "models/player/allied_wheathers.tik": "Weathers",
    # American skins
    "models/player/american_army.tik": "American Soldier",
    "models/player/american_army2.tik": "American Soldier II",
    "models/player/american_army3.tik": "American Soldier III",
    "models/player/american_army_29id.tik": "29th Infantry Division Soldier",
    "models/player/american_army_29id_bar.tik": "29th Infantry BAR Gunner",
    "models/player/american_army_29id_radioman.tik": "29th Infantry Radioman",
    "models/player/american_army_29id_sgt.tik": "29th Infantry Sergeant",
    "models/player/american_army_bar.tik": "American BAR Gunner",
    "models/player/american_army_captain.tik": "American Captain",
    "models/player/american_army_hbt.tik": "American Soldier (HBT Fatigues)",
    "models/player/american_army_lieutenant.tik": "American Lieutenant",
    "models/player/american_army_m43.tik": "American Soldier (M43 Uniform)",
    "models/player/american_army_major.tik": "American Major",
    "models/player/american_army_medic.tik": "Army Medic",
    "models/player/american_army_sergeant.tik": "American Sergeant",
    "models/player/american_assault_engineer.tik": "American Assault Engineer",
    "models/player/american_assault_engineer2.tik": "American Assault Engineer II",
    "models/player/american_major.tik": "American Major (Alt.)",
    "models/player/american_medic.tik": "Combat Medic",
    "models/player/american_navy_beach_radioman.tik": "Navy Beach Radioman",
    "models/player/american_omaha_ranger.tik": "Omaha Beach Ranger",
    "models/player/american_ranger.tik": "Army Ranger",
    "models/player/american_ranger2.tik": "Army Ranger II",
    "models/player/american_ranger3_hbt.tik": "Army Ranger (HBT Fatigues)",
    "models/player/american_ranger_assault.tik": "Ranger Assault Trooper",
    "models/player/american_ranger_assault_captain.tik": "Ranger Assault Captain",
    "models/player/american_ranger_assault_sergeant.tik": "Ranger Assault Sergeant",
    "models/player/american_ranger_lieutenant.tik": "Ranger Lieutenant",
    "models/player/american_ranger_medic.tik": "Ranger Medic",
    "models/player/american_ranger_sergeant.tik": "Ranger Sergeant",
    "models/player/american_ranger_winter.tik": "Ranger (Winter)",
    "models/player/american_ranger_winter_m41.tik": "Ranger (Winter, M41)",
    "models/player/american_ranger_winter_m43.tik": "Ranger (Winter, M43)",
    "models/player/american_ranger_winter_m43_lt.tik": "Ranger Lieutenant (Winter, M43)",
    "models/player/american_ranger_winter_sgt.tik": "Ranger Sergeant (Winter)",
    "models/player/american_sniper.tik": "American Sniper",
    "models/player/american_winter_m41.tik": "American Soldier (Winter, M41)",
    "models/player/american_winter_m43.tik": "American Soldier (Winter, M43)",
    "models/player/american_winter_sgt.tik": "American Sergeant (Winter)",
    "models/player/american_winter_specengineer.tik": "Combat Engineer (Winter)",
    # generic role skins
    "models/player/rifleman.tik": "Rifleman",
    "models/player/riflemannohelm.tik": "Rifleman (No Helmet)",
    "models/player/submachine_gunner.tik": "SMG Gunner",
    "models/player/submachine_gunnernohelm.tik": "SMG Gunner (No Helmet)",
    "models/player/support_gunner.tik": "Support Gunner",
    "models/player/support_gunnernohelm.tik": "Support Gunner (No Helmet)",
    # weapon variants - MUST match ui/coop_loadout.urc's Armory tile titles exactly (same item,
    # same wording), just re-cased from ALL-CAPS to match Service Record's own Title Case style.
    # Verified against the Armory's actual title list, not guessed from the filename alone.
    "models/weapons/arisakasniper.tik": "Arisaka Sniper",
    "models/weapons/bar.tik": "BAR M1918",
    "models/weapons/berettasilenced.tik": "Beretta Silenced",
    "models/weapons/carcanosniper.tik": "Carcano Sniper",
    "models/weapons/colt_silenced.tik": "Colt M1911 Silenced",
    "models/weapons/enfieldsniper.tik": "Lee-Enfield Sniper",
    "models/weapons/g43sniper.tik": "G43 Sniper",
    "models/weapons/garand_scoped.tik": "M1 Garand Scoped",
    "models/weapons/garand_silenced.tik": "M1 Garand Silenced",
    "models/weapons/greasegun_silenced.tik": "M3 Grease Silenced",
    "models/weapons/it_w_breda.tik": "Breda M30",
    "models/weapons/kar98sniper.tik": "Kar98k Sniper",
    "models/weapons/kar98snipersilenced.tik": "Kar98k Sniper Silenced",
    "models/weapons/lugerp08silenced.tik": "Luger P08 Silenced",
    "models/weapons/mp40silenced.tik": "MP40 Silenced",
    "models/weapons/mp44.tik": "StG 44",
    "models/weapons/mp44scoped.tik": "StG 44 Scoped",
    "models/weapons/nagant_sniper.tik": "Mosin Sniper",
    "models/weapons/nagant_snipersilenced.tik": "Mosin Sniper Silenced",
    "models/weapons/p38silenced.tik": "Walther P38 Silenced",
    "models/weapons/ppsh43silenced.tik": "PPS-43 Silenced",
    "models/weapons/shotgun.tik": "Trench Gun",
    "models/weapons/springfield.tik": "Springfield Sniper",
    "models/weapons/thompson50.tik": "Thompson Drum",
    "models/weapons/tt33silenced.tik": "TT-33 Silenced",
    "models/weapons/uk_w_l42a1.tik": "Enfield L42A1",
    "models/weapons/uk_w_vickers.tik": "Vickers-Berthier",
    "models/weapons/welrod.tik": "Welrod Mk II",
    # perks
    "perk_ambusher": "Ambusher",
    "perk_demolition": "Demolition Expert",
    "perk_extrabinoc": "Extra Binoculars",
    "perk_extragrenade": "Extra Grenade",
    "perk_extrarocket": "Extra Rocket",
    "perk_extrasmoke": "Extra Smoke Grenade",
    "perk_fastrevive": "Fast Revive",
    "perk_lastditch": "Last Ditch Effort",
    "perk_objective_boost": "Objective Boost",
    "perk_officer_hunter": "Officer Hunter",
    "perk_overwatch": "Overwatch",
    "perk_penetrator": "Penetrator",
    "perk_quickbash": "Quick Bash",
    "perk_recon": "Recon",
    "perk_steadyblind": "Steady Blindfire",
}
def friendly_reward_name(raw):
    v = (raw or "").strip()
    if not v: return None
    if v in REWARD_NAMES: return REWARD_NAMES[v]
    # fallback for anything added later and not yet curated - mechanical, imperfect, but visible
    if v.lower().endswith(".tik"):
        base = v.rsplit("/",1)[-1][:-4]
        if base.startswith("coop_helmet_"): base = base[len("coop_helmet_"):]
        elif base.startswith("coop_"): base = base[len("coop_"):]
    elif v.startswith("perk_"):
        base = v[len("perk_"):]
    else:
        base = v
    words = [w.capitalize() for w in base.split("_") if w]
    return " ".join(words) if words else None

# [user 08-07] hover-reveal reward callouts: one small transparent PNG per reward-bearing
# challenge, shown via the pinbtn<gi> Button's hovershader (see the main row loop below) instead
# of ever being baked into the row itself. Sized to the SAME rect as that Button so no separate
# alignment math is needed at the .urc level - the whole button area IS the hover-image.
REWARD_HOVER_DIR = "textures/mohmenu/coop_sr_reward"
os.makedirs(REWARD_HOVER_DIR, exist_ok=True)
def bake_reward_hover(gi, reward, btnRect):
    bx,by,bw,bh = btnRect
    # [user 08-07] the engine stretches any shader image to fill its widget's declared rect (same
    # trick the 2048x2048 page backgrounds already rely on), so this doesn't need to match the
    # button's actual pixel size - S=4 supersampling on a ~440x19 screen rect baked ~480KB/image,
    # RGBA TGA (this engine's tr_image_tga.c has no RLE decode, so an RLE-compressed save - which
    # would have been ~100x smaller - isn't an option). S=2 is still comfortably crisp for hover
    # text at this size and quarters the footprint across 194 images.
    S = 2
    W,H = max(4,bw*S), max(4,bh*S)
    im = Image.new("RGBA",(W,H),(0,0,0,0))
    d = ImageDraw.Draw(im)
    text = "Unlocks: " + reward
    fsz = max(14, int(H*0.58))
    f = sans(fsz)
    tb = d.textbbox((0,0), text, font=f)
    tw = tb[2]-tb[0]
    # right-align ending where the progress bar starts - same spot the old inline text sat
    barFrac = (sx(BARX) - bx) / bw if bw else 1.0
    barFrac = max(0.15, min(0.95, barFrac))
    rightX = int(W*barFrac) - 6*S
    x = max(2*S, rightX-tw)
    y = (H-(tb[3]-tb[1]))//2 - tb[1]
    pad=4*S
    d.rounded_rectangle([max(0,x-pad), 2*S, min(W-2*S, x+tw+pad), H-2*S], radius=6*S, fill=(10,8,5,225))
    d.text((x,y), text, font=f, fill=(0xC9,0xA2,0x4b,255))
    path = "%s/r%d.tga" % (REWARD_HOVER_DIR, gi)
    im.save(path)
    return path

# ---- fill textures (transparent track + fill-only) ----
# Glossy brass-on-steel fill matching the rank-up (xpbar) bar: bright top gloss band -> mid brass ->
# dark bottom, plus a specular highlight streak near the top edge. Green variant when the challenge is done.
def barfill(pct, done=False):
    W,H=512,64; S=2
    im=Image.new("RGBA",(W*S,H*S),(0,0,0,0)); fw=int((W*S-12*S)*pct)
    if fw>4*S:
        r=11*S
        if done: top,mid,bot=(160,235,130),(95,180,72),(52,120,44)
        else:    top,mid,bot=(0xFF,0xEA,0xA6),(0xE4,0xC0,0x60),(0x7f,0x58,0x18)
        grad=Image.new("RGBA",(W*S,H*S),(0,0,0,0)); gd=grad.load()
        for y in range(H*S):
            t=y/(H*S-1)
            c=lerp(top,mid,t/0.42) if t<0.42 else lerp(mid,bot,(t-0.42)/0.58)
            for x in range(W*S): gd[x,y]=(c[0],c[1],c[2],255)
        # specular gloss streak across the top third
        hd=grad.load()
        for y in range(int(H*S*0.32)):
            a=1-(y/(H*S*0.32))
            for x in range(W*S):
                p=gd[x,y]; gd[x,y]=(min(255,int(p[0]+70*a)),min(255,int(p[1]+70*a)),min(255,int(p[2]+55*a)),255)
        m=Image.new("L",(W*S,H*S),0); ImageDraw.Draw(m).rounded_rectangle([6*S,6*S,6*S+fw,H*S-6*S], radius=r, fill=255)
        im.paste(grad,(0,0),m)
    return im.resize((W,H),Image.LANCZOS)
for i in range(11): barfill(i/10.0).save("textures/hud/coop_bf%d.tga"%i)
barfill(1.0,done=True).save("textures/hud/coop_bfd.tga")

# [user 08-07] CHECKBOX STATES - all three built on the SAME 32x32 canvas as the stock
# textures/OBJECTIVES/emptybox.tga, so empty / pinned-X / done-check land pixel-identical in the
# same 12x12 rect. Mixing assets of different canvases (a 16x16 mohmenu checkbox, a 128x128 HUD
# tick) is what made the markers drift out of their boxes and overlap neighbouring rows.
import zipfile as _zf, glob as _gl, io as _io
def _load_emptybox():
    for _b in ("main","mainta","maintt"):
        for _p in _gl.glob(r"G:\GOG\Medal of Honor - Allied Assault War Chest\%s\*.pk3"%_b):
            try: _z=_zf.ZipFile(_p)
            except Exception: continue
            for _n in _z.namelist():
                if _n.lower().endswith("objectives/emptybox.tga"):
                    return Image.open(_io.BytesIO(_z.read(_n))).convert("RGBA")
    return None
_EB=_load_emptybox()
if _EB is None:
    _EB=Image.new("RGBA",(32,32),(0,0,0,0))
    ImageDraw.Draw(_EB).rectangle([1,1,30,30],outline=(0xB0,0x9C,0x66,255),width=2)
os.makedirs("textures/hud/coop_sr", exist_ok=True)
_EB.save("textures/hud/coop_sr/box_empty.tga")

def _mark(kind):
    # transparent canvas, mark ONLY - box_empty supplies the outline underneath
    S=8; W=32*S
    im=Image.new("RGBA",(W,W),(0,0,0,0))
    d=ImageDraw.Draw(im)
    if kind=="pin":       # gold X = tracked/pinned
        c=(0xF2,0xC7,0x55,255); w=int(3.0*S)
        d.line([9*S,9*S,23*S,23*S],fill=c,width=w)
        d.line([23*S,9*S,9*S,23*S],fill=c,width=w)
    else:                 # green tick = completed
        c=(0x5C,0xD8,0x4E,255); w=int(3.4*S)
        d.line([8*S,17*S,14*S,23*S],fill=c,width=w)
        d.line([14*S,23*S,24*S,9*S],fill=c,width=w)
    return im.resize((32,32),Image.LANCZOS)
_mark("pin").save("textures/hud/coop_sr/box_pin.tga")
_mark("done").save("textures/hud/coop_sr/box_done.tga")

# ---- read challenges, group by category (file order = global export index) ----
src=open("coop_mod/challenges.scr",encoding="latin-1").read()
rx=re.compile(r'chal_def\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+(\d+)\s+"([^"]*)"')
rows=[m.groups() for m in rx.finditer(src)]
idx={r[0]:i for i,r in enumerate(rows)}
def cat(c): return [r for r in rows if r[1]==c]
def chunk(lst,n):
    k=math.ceil(len(lst)/n); return [lst[i*k:(i+1)*k] for i in range(n)]
# ---- NEW 10-category taxonomy (matches challenges.scr level.coop_chal_catOrder) ----
# Each category is sub-paginated into pages of at most RPP rows so no baked page overflows
# the ~18-row budget (campaign=48 -> 3 pages, rifles/pistols=27 -> 2, combat=24 -> 2, ...).
# GLOBAL bar index stays = file order via idx[cid]; each challenge lands on exactly one page,
# so coop_uiB0..coop_uiB210 come out contiguous with no gaps/dups regardless of the split.
# spec = (catKey, headerBase, tabBase, isWeapon)   -- isWeapon pages shorten the desc to the
# tail after "with the" (weapon-kill families); non-weapon pages keep the full desc.
RPP=18
# 5th field = TAB GROUP. [user 08-07] the 5 weapon-family categories (135 challenges combined)
# used to each get their own top-level tab; per the user's follow-up, they now share ONE
# "WEAPONS" tab and the SAME "< j/N >" pager already built for over-length categories steps
# through the 5 families' pages in sequence - no new mechanism needed, just a coarser grouping.
catspec=[("rifles",          "RIFLES",           "RIFLES",   True,  "WEAPONS"),
         ("snipers",         "MARKSMAN",         "MARKSMAN", True,  "WEAPONS"),
         ("smgs",            "SUBMACHINE GUNS",  "SMGS",     True,  "WEAPONS"),
         ("pistols",         "SIDEARMS",         "PISTOLS",  True,  "WEAPONS"),
         ("support_weapons", "SUPPORT WEAPONS",  "SUPPORT",  True,  "WEAPONS"),
         ("combat",          "COMBAT",           "COMBAT",   False, "COMBAT"),
         ("fireteam",        "FIRETEAM",         "FIRETEAM", False, "FIRETEAM"),
         ("vehicles",        "ARMOR & VEHICLES", "ARMOR",    False, "ARMOR"),
         ("campaign",        "CAMPAIGN",         "CAMPAIGN", False, "CAMPAIGN"),
         ("discovery",       "STEALTH & FEATS",  "STEALTH",  False, "STEALTH"),
         ("axis",            "AXIS FORCES",      "AXIS",     False, "AXIS"),   # [user 2026-08-04] faction kill tracking
         ("finishes",        "WEAPON FINISHES",  "STEALTH",  False, "STEALTH")]  # [user 2026-08-18] the finish strip's 7 unlock challenges - grouped under the STEALTH & FEATS tab (a 10th tab would wrap the button row)
# [user 08-07] REDESIGN: one tab per TAB GROUP (not per sub-page, not even per catspec category
# now that weapons share one tab) - the old scheme gave every sub-page its own tab (RIFLES /
# RIFLES 2 / CAMPAIGN 1-5 / ...), 23 buttons crammed into two rows once Medals was added. Now
# there are 7 group tabs (WEAPONS/COMBAT/FIRETEAM/ARMOR/CAMPAIGN/STEALTH/AXIS) + MEDALS + BACK = 9,
# one comfortable row. A group spanning more rows than fit on one page - either because its own
# category is long (campaign) or because it's several categories sharing a tab (weapons) - gets
# the in-page "< j/N >" pager instead of extra tabs. `pages` keeps its old per-sub-page shape
# (unchanged consumers below still work); `catGroups` records which page indices belong to which
# TAB GROUP, in display order, for the new nav to use.
# page = (tabLabel, headerLabel, items, isWeapon)
pages=[]
groupPageIdxs={}   # tabGroup -> [page indices], built in catspec order so weapon families stay in sequence
groupOrder=[]
for key,hdr,tab,isW,grp in catspec:
    items=cat(key)
    npg=max(1, math.ceil(len(items)/RPP))
    if grp not in groupPageIdxs:
        groupPageIdxs[grp]=[]; groupOrder.append(grp)
    for s in range(npg):
        chunk_items=items[s*RPP:(s+1)*RPP]
        # header no longer carries "(j/N)" - the pager widget shows that now
        groupPageIdxs[grp].append(len(pages))
        pages.append((tab,hdr,chunk_items,isW))
NT=len(pages)
catGroups=[(grp,grp,grp,groupPageIdxs[grp]) for grp in groupOrder]   # (key,tabLabel,headerBase,pageIdxs)

# dynamic row height so even a 22-row page fits ABOVE the two tab-button rows (which overlay the bottom
# of the texture at screen y~430/452 = texture y~1810+). Keep the last row well clear -> BOT=1760.
BOT=1760  # last usable texture y (rows must not extend under the tab buttons)
def rowh_for(n):
    if n<=0: return 84
    return int(min(84, (BOT-ROW0)/n))

def page_bg(header, items, isWeapon, rowh):
    im=Image.new("RGBA",(TW,TH),(0,0,0,255)); px=im.load()
    for y in range(TH):
        c=lerp((0x30,0x22,0x14),(0x15,0x0e,0x08), y/(TH-1))
        for x in range(TW): px[x,y]=(c[0],c[1],c[2],255)
    noise=Image.effect_noise((TW,TH),15).convert("L")
    im=ImageChops.overlay(im.convert("RGB"), Image.merge("RGB",(noise,noise,noise))).convert("RGBA")
    vig=Image.new("L",(TW,TH),0); ImageDraw.Draw(vig).ellipse([-300,-300,TW+300,TH+300],fill=255)
    im=Image.composite(im, Image.alpha_composite(im,Image.new("RGBA",(TW,TH),(0,0,0,150))), vig.filter(ImageFilter.GaussianBlur(300)))
    d=ImageDraw.Draw(im)
    d.rectangle([12,12,TW-13,TH-13], outline=(0x0c,0x08,0x04), width=12)
    for i in range(24): d.rectangle([26+i,26+i,TW-27-i,TH-27-i], outline=lerp((0xEA,0xC9,0x82),(0x6f,0x4c,0x18),i/23))
    d.rectangle([54,54,TW-55,TH-55], outline=(0x0c,0x08,0x04), width=5)
    for cx,cy in [(82,82),(TW-82,82),(82,TH-82),(TW-82,TH-82)]:
        d.ellipse([cx-15,cy-15,cx+15,cy+15],fill=(0x38,0x28,0x12)); d.ellipse([cx-11,cy-11,cx+11,cy+11],fill=(0xC9,0xA2,0x4b)); d.ellipse([cx-10,cy-13,cx+3,cy+1],fill=(0xF2,0xD8,0x8c))
    ny0,ny1=96,224
    for y in range(ny0,ny1): d.line([(240,y),(TW-240,y)],fill=lerp((0xE2,0xC0,0x72),(0x88,0x60,0x20),(y-ny0)/(ny1-ny0)))
    d.rectangle([236,ny0-5,TW-236,ny1+3],outline=(0x48,0x33,0x12),width=5)
    f=serif(130); t="SERVICE RECORD"; tb=d.textbbox((0,0),t,font=f)
    # [user 2026-08-14] The title is nudged LEFT to make room for the blueprint counter on the
    # right of the banner. Dead-centre leaves only 48 urc each side and the counter needs ~70;
    # shifting 26 urc opens the right side to ~74 while staying visually centred to the eye,
    # since the banner's own left margin absorbs it. The assert below is what proves it fits.
    _titleX=(TW-(tb[2]-tb[0]))//2-tb[0]-int(26*SCALE)
    d.text((_titleX,(ny0+ny1)//2-(tb[3]-tb[1])//2-tb[1]),t,font=f,fill=(0x33,0x22,0x0c))

    # [user 2026-08-14] "BLUEPRINTS n/31" in the TITLE BANNER, right of the title.
    #
    # It is here because nowhere else has room. The category header row was measured and is
    # full: the gap between the longest category name (SUPPORT WEAPONS) and the PINNED caption
    # is 37 urc, the caption alone needs 60, and the widgets right of it (pinSummary, clearPins
    # and the three pager parts) leave ~22 urc of total slack between them. A first attempt put
    # the caption on top of CLEAR PINS and the count on top of the pager.
    #
    # Font 24 rather than the header's 30: at 30 the caption plus its count needs 82 urc against
    # 74 free inside the banner, so it would not have fitted either.
    #
    # The ASSERTS below are the real fix. Coordinate arithmetic alone already shipped one
    # overlapping layout; now a bad layout stops the build instead of reaching a screenshot.
    # STACKED, not side by side. The title is 396 urc wide and the banner 492, so each side has
    # only 48 urc - the caption plus its count needs 70 on one line and the first attempt at this
    # tripped the assert below. The banner is 40 urc TALL though, so the caption sits above its
    # number and both fit in 48x40. Measured, not estimated: the assert is what caught it.
    global BP_LABEL_RECT
    _bf=sans(20,True); _bc="BLUEPRINTS"
    _bcb=d.textbbox((0,0),_bc,font=_bf)
    _bcw=_bcb[2]-_bcb[0]
    _right=(TW-236)-int(6*SCALE)             # inside the banner's right edge, small margin
    _capX=_right-_bcw
    _titleRight=_titleX+(tb[2]-tb[0])
    assert _capX > _titleRight+int(6*SCALE), (
        "BLUEPRINTS caption would collide with the SERVICE RECORD title "
        "(caption starts %d, title ends %d)"%(_capX,_titleRight))
    assert _right <= TW-236, "BLUEPRINTS block would overflow the banner"
    _capY=ny0+int(6*SCALE)
    d.text((_capX, _capY), _bc, font=_bf, fill=(0x33,0x22,0x0c))

    # The count Label sits directly UNDER the caption, centred on it.
    #
    # TEXTURE -> WIDGET COORDINATES. These are two different spaces and conflating them is what
    # put the count outside the banner, on the dark backing, in dark-on-dark text. The page
    # background is drawn into rect RX RY RW RH (80 8 480 462), so a texture pixel maps to:
    #     widget_x = RX + tex_x * RW/TW        widget_y = RY + tex_y * RH/TH
    # NOT tex/3.2, which is what the first version used - that has no origin offset and the
    # wrong scale on both axes. Checked against a known widget rather than assumed: pinSummary
    # sits at widget x 302, which back-maps to texture 947, and the baked PINNED caption ends at
    # texture 930. The two agree; the /3.2 version does not.
    def _t2ux(x): return RX + x*float(RW)/TW
    def _t2uy(y): return RY + y*float(RH)/TH
    _lx=_t2ux(_capX); _lw=_bcw*float(RW)/TW
    # +9 urc, not +26: the caption is a 20px font in texture space, so it occupies barely 20
    # texture pixels and the count only has to clear that. A 26-urc drop put the label's bottom
    # below the banner (the assert below reported 52.7-63.7 against a banner ending at 58.5).
    _ly=_t2uy(_capY+int(9*SCALE))
    _bTop,_bBot=_t2uy(ny0),_t2uy(ny1)
    assert _ly >= _bTop and _ly+11 <= _bBot, (
        "blueprint count would fall outside the banner (label y %.1f-%.1f, banner %.1f-%.1f)"
        %(_ly,_ly+11,_bTop,_bBot))
    assert _t2ux(_right) <= RX+RW, "blueprint block would overflow the panel"
    BP_LABEL_RECT=(int(_lx), int(_ly), int(_lw), 11)
    d.rectangle([120,272,TW-120,344], fill=(0x3a,0x2b,0x14)); d.rectangle([120,272,132,344],fill=(0xC9,0xA2,0x4b))
    d.text((160,286), header, font=sans(52,True), fill=(0xE8,0xCb,0x86))
    # [user 08-07] "PINNED" caption baked onto the header bar, with the live count Label
    # (linkcvar coop_pinCount) sitting immediately to its right in screen space. Baked rather than
    # carried in the cvar because an unquoted stufftext value stops at the first space, so the
    # count cvar has to stay a single token ("3/5").
    _pf=sans(30,True); _pt="PINNED"
    _ptb=d.textbbox((0,0),_pt,font=_pf)
    d.text((930-(_ptb[2]-_ptb[0]),300), _pt, font=_pf, fill=(0xC9,0xA2,0x4b))
    # fonts scale with the row height so dense pages stay legible & non-overlapping
    tf=max(28,min(44,int(rowh*0.52))); df=max(19,min(30,int(rowh*0.34))); doff=tf+3
    ft=sans(tf,True); fdc=sans(df); fcnt=sans(46,True)
    TITLEX=150; DESCX=170
    for i,(cid,c,ttl,desc,stat,tgt,rw) in enumerate(items):
        y=ROW0+i*rowh
        d.text((TITLEX,y), ttl, font=ft, fill=(0xE8,0xE0,0xCA))
        if isWeapon:
            # short "how earned" without the noisy 'Get N kills with' - just the tail after 'with the'
            m=re.search(r'with the (.*)$', desc); sub=m.group(1) if m else desc
        else:
            sub=desc
        # [user 08-07] the reward field (7th chal_def arg) went through three baked-inline
        # attempts tonight (hard truncate -> shrink description to fit -> stack reward on its
        # own line) and every one of them still made the row about the reward instead of the
        # challenge. Pulled the reward out of the baked image entirely - the description now
        # always gets its full natural width, same as a row with no reward at all. The reward is
        # revealed on HOVER instead (see the pinbtn<gi> Button below, which already covers this
        # row for click-to-pin - hovershader swaps in a small per-row "Unlocks: X" overlay baked
        # separately by bake_reward_hover(), so hovering the row/title shows it without the row
        # ever needing to reserve space for it).
        reward = friendly_reward_name(rw)
        maxDescW = 1260 - DESCX
        descFont = fdc; descSize = df
        DESC_MIN = 15
        while d.textlength(sub, font=descFont) > maxDescW and descSize > DESC_MIN:
            descSize -= 1
            descFont = sans(descSize)
        if d.textlength(sub, font=descFont) > maxDescW:
            ell = "..."
            while sub and d.textlength(sub+ell, font=descFont) > maxDescW:
                sub = sub[:-1]
            sub = sub + ell
        descY = y+doff + (df-descSize)//2
        d.text((DESCX,descY), sub, font=descFont, fill=(0x9c,0x8e,0x72))
        bx0,by0,bx1,by1=BARX,y+10,BARX+BARW,y+10+BARH
        # xpbar-style track: dark steel channel + brass bevel + a thin top gloss line
        d.rounded_rectangle([bx0,by0,bx1,by1], radius=12, fill=(22,17,10,255), outline=(0x6a,0x50,0x26,255), width=3)
        d.rounded_rectangle([bx0+3,by0+3,bx1-3,by1-3], radius=10, outline=(0x0c,0x08,0x04,255), width=2)
        d.line([bx0+10,by0+4,bx1-10,by0+4], fill=(0x5a,0x46,0x26), width=1)
        # NOTE: do NOT bake a "0 / <target>" number here. The live count Label (linkcvar coop_uiN<gi>,
        # verdana-12) draws the real "N/T" on top, and once persisted progress exists the two overlap
        # into a ghosted double (bug-534). The live label is the single source of the count now.
    return im

L=["// HZM coop - SERVICE RECORD (single paged/tabbed menu, generated by scratchpad/gen_sr4.py).",
   "// ONE menu; one tab PER PAGE laid out in TWO rows. Categories (rifles/snipers/smgs/pistols/support/",
   "// combat/fireteam/vehicles/campaign/discovery) are sub-paginated at 18 rows/page, so big categories",
   "// span multiple tabs (RIFLES + RIFLES 2, CAMPAIGN 1/2/3, ...). Tabs flip the coop_srP0..N-1 view cvars",
   "// (enabledcvar-gated bg + rows) - NO pushmenu/popmenu on tab switch (engine bug-461: PopMenu locks the",
   "// menu manager, so a same-frame popmenu;pushmenu drops the push). Each row: baked title/desc + baked",
   "// empty track; fill Label (linkcvar coop_uiB<i>+linkcvartoshader) overlays the fill and count Label",
   "// (linkcvar coop_uiN<i>) shows N/T - both SAVED by challenges.scr::chal_ui_export (i = global catalog",
   "// index = file order in challenges.scr). Page count / coop_srP range is printed by the generator.",
   'menu "coop_sr" 640 480 NONE 1',
   "borderstyle NONE","bgcolor 0 0 0 0","align centerx centery","virtualres 1","fullscreen 0","","direction from_top 0",""]
rowhs=[rowh_for(len(p[2])) for p in pages]
for pi,(tl,hdr,items,isW) in enumerate(pages):
    cv="coop_srP%d"%pi; rowh=rowhs[pi]
    L+=["resource","Label","{","ordernumber 50",'name "bg%d"'%pi,"rect %d %d %d %d"%(RX,RY,RW,RH),
        "fgcolor 1.00 1.00 1.00 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
        'enabledcvar "%s"'%cv,'shader "textures/mohmenu/coop_sr_p%d.tga"'%pi,"}",""]
    for i,(cid,c,ttl,desc,stat,tgt,rw) in enumerate(items):
        gi=idx[cid]; ty=ROW0+i*rowh
        bx=round(sx(BARX)); by=round(sy(ty+10)); bw=round(BARW*RW/TW); bh=max(6,round(BARH*RH/TH))
        L+=["resource","Label","{","ordernumber 20",'name "bar%d"'%gi,"rect %d %d %d %d"%(bx,by,bw,bh),
            "fgcolor 1.00 1.00 1.00 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
            'enabledcvar "%s"'%cv,'linkcvar "coop_uiB%d"'%gi,"linkcvartoshader","}",""]
        cx=round(sx(CNTX)); cy=round(sy(ty+3))
        L+=["resource","Label","{","ordernumber 10",'name "cnt%d"'%gi,"rect %d %d 62 14"%(cx,cy),
            "fgcolor 0.86 0.74 0.44 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
            "font \"verdana-12\"","dontlocalize",'enabledcvar "%s"'%cv,'linkcvar "coop_uiN%d"'%gi,"}",""]

        # ---- PIN HIT AREA [user 2026-08-04] -------------------------------------------------
        # The whole row (minus the marker gutter below) is an invisible Button that toggles a pin
        # on this challenge, so the menu matches the lobby ("what you can read, you can pin") with
        # no extra chrome over the baked page texture. It sends the CATALOGUE INDEX over the name
        # bus (',cp<gi>'), because a client-side .urc has no way to know challenge cids -
        # challenges.scr::chal_pin_byIndex resolves it server-side (dispatch already wired at
        # player.scr:614, arrayIndex 47, registered in variables.scr::getNameAppendCommands[47]).
        # ordernumber 5 puts it in FRONT of the bar (20) and count (10) so it actually receives the
        # click; bgcolor alpha 0 + borderstyle NONE keep it invisible.
        ry=round(sy(ty-4)); rh=max(10,round(rowh*RH/TW))

        # [user 08-07] PINX anchored in TEXTURE space (like TITLEX/DESCX) and converted with sx(),
        # not a raw RX+5 screen-space offset. RX is the panel's own left edge, so RX+5 sat inside
        # the baked ornamental border/frame - a column of checkboxes floating off the actual row
        # content instead of reading as part of each row. TX=96 sits in the gutter between that
        # border and TITLEX=150, clear of both.
        PINX=round(sx(96))

        # [bug-1362 gap, fixed 2026-08-06] this Button was DESCRIBED above but never actually
        # emitted - only the marker Label below existed, so every pinmk<gi> row was pure decoration
        # with nothing to click. Starts past the marker's PINX..PINX+17 gutter so it can never
        # overlap that Label - see the marker's own comment for why that overlap would matter.
        # [bug-1503, fixed 2026-08-06] target switched from "append name ,cp<gi>" (server-dependent -
        # silently did nothing from the disconnected main menu, since there is no script VM there to
        # read a name-bus token) to "coop_pintoggle <gi>", a client console command that works with
        # zero server connection and ALSO notifies a live server immediately if one is connected -
        # see CL_PinToggle_f in code/client/cl_main.cpp.
        # [user 08-07] HOVER-REVEAL for the reward: this Button already covers the whole row
        # (title included) for click-to-pin and is frontmost there (ordernumber 5), so it's the
        # widget that actually receives mouse-over too - reusing it avoids a second invisible
        # layer racing this one for the hover event. hovershader is transparent everywhere except
        # a small pre-baked "Unlocks: X" readout (bake_reward_hover below), positioned to land
        # just left of the progress bar - same spot the old inline text used to sit, but now only
        # visible on hover, so the description never has to share the row with it again.
        btnRect=(PINX+17, ry, (RX+RW)-(PINX+17), rh)
        reward = friendly_reward_name(rw)
        hoverAttr=[]
        if reward:
            hoverPath=bake_reward_hover(gi, reward, btnRect)
            hoverAttr=['hovershader "%s"'%hoverPath]
        L+=["resource","Button","{","ordernumber 5",'name "pinbtn%d"'%gi,
            "rect %d %d %d %d"%btnRect,
            "fgcolor 1.00 1.00 1.00 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
            'enabledcvar "%s"'%cv,"clicksound \"sound/menu/apply.wav\""]+hoverAttr+[
            'stuffcommand "coop_pintoggle %d"'%gi,"}",""]

        # [user 08-07] CHECKBOX HIT AREA - the title-row Button above deliberately excludes this
        # PINX..PINX+17 gutter (see its own comment: the pinmk Label below would swallow clicks once
        # pinned, since FindResponder makes an enabledcvar widget clickable whenever its gate is ON).
        # Rather than widen the title Button into that trap, this is a SEPARATE Button in the same
        # gutter with a LOWER ordernumber (2, vs pinmk's 3 and pinbox's 4) so it always wins the click
        # in its own rect regardless of pin state - same stuffcommand, so clicking the checkbox itself
        # now pins/unpins exactly like clicking the title does.
        L+=["resource","Button","{","ordernumber 2",'name "pincheck%d"'%gi,
            "rect %d %d 17 %d"%(PINX, ry, rh),
            "fgcolor 1.00 1.00 1.00 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
            'enabledcvar "%s"'%cv,"clicksound \"sound/menu/apply.wav\"",
            'stuffcommand "coop_pintoggle %d"'%gi,"}",""]

        # [user 08-07] REVERTED to the last state that actually worked in-game (recovered from
        # hzm-mohaa-coop-mod HEAD:ui/coop_sr.urc, the v1.2.1 snapshot). Two Labels sharing one
        # rect: an always-drawn empty box, and a filled marker gated on coop_uiP<gi>. Nothing
        # else. Every later architecture - coop_uiD tick, then the coop_uiC shader-path box -
        # regressed this: the tick appeared on every row, and the shader-path box drew nothing
        # at all until CLEAR PINS seeded it AND stopped repainting on click. Do not replace
        # this pair again without a way to see it render first.
        BOXY = ry+max(0,(rh-12)//2)
        L+=["resource","Label","{","ordernumber 4",'name "pinbox%d"'%gi,
            "rect %d %d 12 12"%(PINX,BOXY),
            "fgcolor 0.70 0.62 0.40 0.65","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
            'enabledcvar "%s"'%cv,'shader "textures/OBJECTIVES/emptybox.tga"',"}",""]
        L+=["resource","Label","{","ordernumber 3",'name "pinmk%d"'%gi,
            "rect %d %d 12 12"%(PINX,BOXY),
            "fgcolor 0.98 0.84 0.36 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
            'shader "textures/OBJECTIVES/filledbox.tga"','enabledcvar "coop_uiP%d"'%gi,"}",""]


# ---- MEDALS & BADGES page [user 08-07] ----------------------------------------------------
# Parsed from coop_mod/medals.scr the same way challenges are parsed above - one medal per
# Service Record category (12th is the "all" capstone) - so this file never hand-duplicates
# medals.scr's own data table. Each medal is derived state (challenges.scr's own coop_chalD_<cid>
# flags, see medals.scr::medal_checkAll), not a new tracked stat.
msrc = open("coop_mod/medals.scr", encoding="latin-1").read()
mrx = re.compile(r'medal_def\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"')
medals = [m.groups() for m in mrx.finditer(msrc)]   # (id, cat, name, desc)

# Themed ribbon colors per category - NOT a claim of historical accuracy (the real ribbon
# patterns need verified reference art this pass didn't source - see the buglog entry for this
# feature). Distinct hues so the 12 medals read apart from each other at a glance.
RIBBON_COLORS = {
    "rifles":(0x5a,0x6b,0x3a), "snipers":(0x35,0x45,0x28), "smgs":(0x6b,0x4a,0x24),
    "pistols":(0x4a,0x38,0x5a), "support_weapons":(0x5a,0x30,0x30), "vehicles":(0x30,0x38,0x50),
    "combat":(0x8a,0x28,0x24), "fireteam":(0x24,0x48,0x6a), "campaign":(0x6a,0x54,0x18),
    "discovery":(0x28,0x5a,0x54), "axis":(0x48,0x28,0x28), "all":(0x8a,0x66,0x18),
}

def draw_medal_icon(cat, size=200):
    S=3; W=size*S
    im=Image.new("RGBA",(W,W),(0,0,0,0)); d=ImageDraw.Draw(im)
    ribbon=RIBBON_COLORS.get(cat,(0x50,0x50,0x50))
    cx=W//2
    d.polygon([(cx-26*S,4*S),(cx+26*S,4*S),(cx+19*S,58*S),(cx,47*S),(cx-19*S,58*S)], fill=ribbon+(255,))
    d.polygon([(cx-26*S,4*S),(cx+26*S,4*S),(cx+19*S,58*S),(cx,47*S),(cx-19*S,58*S)], outline=(0,0,0,190), width=S)
    # a thin lighter stripe down the ribbon center for a touch of pattern
    d.polygon([(cx-4*S,4*S),(cx+4*S,4*S),(cx+3*S,50*S),(cx-3*S,50*S)], fill=lerp(ribbon,(255,255,255),0.35)+(255,))
    r=50*S; my=120*S
    gold = cat=="all"
    top,mid,bot=((0xF5,0xE0,0x90),(0xD4,0xA6,0x3C),(0x8a,0x5f,0x1a)) if gold else ((0xC8,0xB4,0x8c),(0x9c,0x82,0x54),(0x5a,0x46,0x28))
    for yy in range(-r,r):
        t=(yy+r)/(2*r)
        c=lerp(top,mid,t/0.5) if t<0.5 else lerp(mid,bot,(t-0.5)/0.5)
        w=int((r*r-yy*yy)**0.5) if abs(yy)<r else 0
        if w>0: d.line([(cx-w,my+yy),(cx+w,my+yy)],fill=c+(255,))
    d.ellipse([cx-r,my-r,cx+r,my+r],outline=(0x2a,0x1e,0x0c,255),width=int(3.5*S))
    pts=[]
    for k in range(10):
        ang=-math.pi/2+k*math.pi/5
        rr=r*0.62 if k%2==0 else r*0.26
        pts.append((cx+rr*math.cos(ang), my+rr*math.sin(ang)))
    d.polygon(pts, fill=(0x2a,0x1e,0x0c,225))
    return im.resize((size,size),Image.LANCZOS)

def medals_page_bg(medals):
    # reuse page_bg's frame/vignette/header painting by calling it with zero items, then draw the grid on top
    base=page_bg("MEDALS & BADGES", [], False, 84)
    d=ImageDraw.Draw(base)
    cols,rowsN=3,4
    gx0,gy0,gx1,gy1=150,360,TW-150,1750
    cw=(gx1-gx0)//cols; ch=(gy1-gy0)//rowsN
    icon_sz=min(cw,ch)//2
    for i,(mid,cat,name,desc) in enumerate(medals):
        col=i%cols; row=i//cols
        ccx=gx0+col*cw+cw//2; ccy=gy0+row*ch+ch//3
        icon=draw_medal_icon(cat, icon_sz)
        base.alpha_composite(icon, (ccx-icon_sz//2, ccy-icon_sz//2))
        nf=sans(30,True); df=sans(21)
        ntb=d.textbbox((0,0),name,font=nf)
        d.text((ccx-(ntb[2]-ntb[0])//2, ccy+icon_sz//2+14), name, font=nf, fill=(0xE8,0xE0,0xCA))
        # word-wrap the description into the cell width
        words=desc.split(); lines=[]; cur=""
        maxw=cw-40
        for wd in words:
            trial=(cur+" "+wd).strip()
            if d.textlength(trial,font=df)>maxw and cur:
                lines.append(cur); cur=wd
            else:
                cur=trial
        if cur: lines.append(cur)
        ly=ccy+icon_sz//2+52
        for ln in lines[:2]:
            ltb=d.textbbox((0,0),ln,font=df)
            d.text((ccx-(ltb[2]-ltb[0])//2, ly), ln, font=df, fill=(0x9c,0x8e,0x72))
            ly+=26
    return base

medals_page_bg(medals).save("textures/mohmenu/coop_sr_medals.tga")

# [user 08-07] per-medal cell art for the "earned" overlay (see medIcon<i> below). Same cell
# geometry as the grid drawn above, so an earned medal exactly replaces its locked scrim.
_mgx0,_mgy0,_mgx1,_mgy1=150,360,TW-150,1750
_mcw=(_mgx1-_mgx0)/3.0; _mch=(_mgy1-_mgy0)/4.0
for _i,(_mid,_cat,_name,_desc) in enumerate(medals):
    _col=_i%3; _row=_i//3
    _ccx=_mgx0+_col*_mcw+_mcw/2; _ccy=_mgy0+_row*_mch+_mch/3
    _bw=int(_mcw*0.8); _bh=int(_mch*0.6)
    _cell=Image.new("RGBA",(_bw,_bh),(0,0,0,0))
    _isz=min(_bw,_bh)//2
    _cell.alpha_composite(draw_medal_icon(_cat,_isz),((_bw-_isz)//2,(_bh-_isz)//2))
    _cell.save("textures/hud/coop_sr/medal%d.tga"%_i)

# ---- tab buttons: one per CATEGORY (not per sub-page) + MEDALS + BACK ----------------------
# [user 08-07] redesign - see catGroups comment above. NCAT (11) + MEDALS + BACK = 13 tabs, down
# from 23, comfortably two short rows instead of two packed ones. Clicking a category tab jumps to
# that category's FIRST sub-page; the pager below (only emitted for categories with >1 sub-page)
# handles moving within a category without needing more tabs.
NCAT=len(catGroups)
TABX0=4; ROWY=[430,452]
PERROW=math.ceil((NCAT+2)/2.0)          # NCAT category tabs + 1 MEDALS + 1 BACK, split across two rows
TABW=(640-2*TABX0)//PERROW
def catTabBtn(slotIdx,tl,bx,by,w,firstPageIdx):
    setcmd="; ".join(("set coop_srP%d %d"%(j,(1 if j==firstPageIdx else 0))) for j in range(NT))
    # [user 08-07] coop_srsync (CL_SyncSR_f, code/client/cl_main.cpp) republishes every coop_uiD<i>
    # done-flag from the archived coop_uiN<i> progress strings. Run on every tab click so the
    # done-checkmarks are correct the moment a page is shown - without it they only refreshed on
    # the server's 30s chal_flush, i.e. never at all when browsing disconnected.
    setcmd += "; set coop_srMedals 0; coop_srsync"
    return ["resource","Button","{",'name "tabCat%d"'%slotIdx,'title "%s"'%tl,"rect %d %d %d 18"%(bx,by,w),
        "fgcolor 0.92 0.86 0.66 1.00","bgcolor 0.16 0.11 0.06 0.92","borderstyle \"3D_BORDER\"",
        "font \"verdana-12\"","clicksound \"sound/menu/apply.wav\"",'stuffcommand "%s"'%setcmd,"}",""]
def slotxy(slot):
    return TABX0+(slot%PERROW)*TABW, ROWY[slot//PERROW]
for ci,(key,tab,hdr,pageIdxs) in enumerate(catGroups):
    bx,by=slotxy(ci)
    L+=catTabBtn(ci, tab, bx, by, TABW-2, pageIdxs[0])

# ---- in-page PAGER: "< j/N >" for any category with more than one sub-page -------------------
# One prev/next Button pair + one page-count Label PER sub-page, each gated on that sub-page's own
# coop_srP<pi> so only the active sub-page's set is ever visible/clickable - same stacked-widget-
# at-one-rect trick already used for the pin marker/checkbox. Parked to the right of the category
# header text (header row sits at screen y~72; the title banner above it runs through y~58, so
# this must sit BELOW that - first draft put it at y=10 and it landed on top of "SERVICE RECORD"
# itself). Clear of pinSummary too, which lives further right outside the panel entirely (x 565+).
PGX0=462; PGY=74
for key,tab,hdr,pageIdxs in catGroups:
    n=len(pageIdxs)
    if n<=1: continue
    for j,pi in enumerate(pageIdxs):
        gate='enabledcvar "coop_srP%d"'%pi
        # [user 08-07] BOTH arrows always, at fixed x, wrapping at the ends. Emitting "<" only when
        # j>0 left page 1 with a hole where the arrow should be, so the number and ">" sat at
        # different offsets than on every other page.
        prevPi = pageIdxs[(j-1) % n]
        nextPi = pageIdxs[(j+1) % n]
        prevSet="; ".join(("set coop_srP%d %d"%(k,(1 if k==prevPi else 0))) for k in range(NT))
        nextSet="; ".join(("set coop_srP%d %d"%(k,(1 if k==nextPi else 0))) for k in range(NT))
        L+=["resource","Button","{",'name "pgPrev%d"'%pi,"title \"<\"","rect %d %d 16 14"%(PGX0,PGY),
            "fgcolor 0.92 0.86 0.66 1.00","bgcolor 0.16 0.11 0.06 0.92","borderstyle \"3D_BORDER\"",
            "font \"verdana-12\"","clicksound \"sound/menu/scroll.wav\"",gate,
            'stuffcommand "%s"'%prevSet,"}",""]
        L+=["resource","Label","{",'name "pgNum%d"'%pi,"rect %d %d 34 14"%(PGX0+18,PGY),
            "fgcolor 0.86 0.74 0.44 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
            "font \"verdana-12\"","textalign centerx","textalign centery","dontlocalize",gate,
            'title "%d/%d"'%(j+1,n),"}",""]
        L+=["resource","Button","{",'name "pgNext%d"'%pi,"title \">\"","rect %d %d 16 14"%(PGX0+54,PGY),
            "fgcolor 0.92 0.86 0.66 1.00","bgcolor 0.16 0.11 0.06 0.92","borderstyle \"3D_BORDER\"",
            "font \"verdana-12\"","clicksound \"sound/menu/scroll.wav\"",gate,
            'stuffcommand "%s"'%nextSet,"}",""]

# MEDALS tab occupies the slot right after the last category tab
bx,by=slotxy(NCAT)
medalsSetcmd="; ".join(("set coop_srP%d 0"%j) for j in range(NT)) + "; set coop_srMedals 1; coop_srsync"
L+=["resource","Button","{",'name "tabMedals"','title "MEDALS"',"rect %d %d %d 18"%(bx,by,TABW-2),
    "fgcolor 0.92 0.86 0.66 1.00","bgcolor 0.16 0.11 0.06 0.92","borderstyle \"3D_BORDER\"",
    "font \"verdana-12\"","clicksound \"sound/menu/apply.wav\"",'stuffcommand "%s"'%medalsSetcmd,"}",""]
# BACK button occupies the slot right after MEDALS
bx,by=slotxy(NCAT+1)
# [user 08-07] bug: "end." (the menu block's own terminator) used to be appended right here, which
# silently dropped EVERYTHING declared after this point (bgMedals, the per-medal lock overlays, and
# even the earlier pinSummary Label) outside the "coop_sr" menu block - the parser just stops reading
# menu content at "end.", so none of it rendered (black Medals tab; pinSummary likely never worked
# either). "end." now moves to the true last write, after every remaining Label below.
# [user 08-07] CLEAR PINS - fixes a stale "n/5 pinned" with nothing actually marked.
L+=["resource","Button","{",'name "clearPins"','title "CLEAR PINS"',
    "rect %d %d %d 14"%(372, 74, 78),
    "fgcolor 0.92 0.86 0.66 1.00","bgcolor 0.16 0.11 0.06 0.92","borderstyle \"3D_BORDER\"",
    "font \"verdana-12\"","clicksound \"sound/menu/apply.wav\"",
    'stuffcommand "exec ui/coop_sr_pinreset.cfg"',"}",""]
L+=["resource","Button","{",'name "backBtn"','title "BACK"',"rect %d %d %d 18"%(bx,by,TABW-2),
    "fgcolor 0.90 0.84 0.66 1.00","bgcolor 0.14 0.10 0.06 0.94","borderstyle \"3D_BORDER\"","font \"verdana-12\"",
    "clicksound \"sound/menu/back.wav\"",'stuffcommand "popmenu 0"',"}",""]

# MEDALS page background, gated on coop_srMedals like every other bg%d is gated on coop_srP<pi>
L+=["resource","Label","{","ordernumber 50",'name "bgMedals"',"rect %d %d %d %d"%(RX,RY,RW,RH),
    "fgcolor 1.00 1.00 1.00 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
    'enabledcvar "coop_srMedals"','shader "textures/mohmenu/coop_sr_medals.tga"',"}",""]

# Per-medal LOCK SCRIM: a dark semi-opaque box + lock icon over that medal's grid cell, shown
# only while coop_uiML<i> (pushed by medals.scr::medal_ui_export) is 1 - i.e. not yet earned.
# Screen-space cell geometry mirrors medals_page_bg's texture-space grid via sx()/sy().
mgx0,mgy0,mgx1,mgy1=150,360,TW-150,1750
mcols,mrowsN=3,4
mcw=(mgx1-mgx0)/mcols; mch=(mgy1-mgy0)/mrowsN
for i,(mid,cat,name,desc) in enumerate(medals):
    col=i%mcols; row=i//mcols
    ccx=mgx0+col*mcw+mcw/2; ccy=mgy0+row*mch+mch/3
    boxw=sx(mcw*0.8)-sx(0); boxh=sy(mch*0.6)-sy(0)
    bx0=sx(ccx)-boxw/2; by0=sy(ccy)-boxh/2
    # [user 08-07] EXE-INDEPENDENT lock state. The previous version gated both overlays on
    # coop_uiMLv<i>, an AND of "on the medals page" and "still locked" that the client exe had to
    # compute - so if that computation did not run (older binary, or medals.scr had never pushed
    # coop_uiML<i> yet) no lock rendered at all. Now each overlay uses ONE plain cvar:
    #   scrim + padlock -> coop_srMedals  (drawn whenever the medals page is up = locked by default)
    #   bright icon     -> coop_uiM<i>    (earned; drawn IN FRONT, so it hides the scrim)
    # Locked is therefore the default with no engine involvement, and earning a medal reveals it.
    L+=["resource","Label","{","ordernumber 40",'name "medLock%d"'%i,
        "rect %d %d %d %d"%(round(bx0),round(by0),round(boxw),round(boxh)),
        "fgcolor 1.00 1.00 1.00 1.00","bgcolor 0.02 0.02 0.02 0.72","borderstyle \"NONE\"",
        'enabledcvar "coop_srMedals"',"}",""]
    lockw=20
    L+=["resource","Label","{","ordernumber 39",'name "medLockIcon%d"'%i,
        "rect %d %d %d %d"%(round(sx(ccx)-lockw/2),round(sy(ccy)-lockw/2),lockw,lockw),
        "fgcolor 1.00 1.00 1.00 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
        'enabledcvar "coop_srMedals"','shader "textures/mohmenu/coop_lo_lock.tga"',"}",""]
    # earned: the medal's own icon, baked per-medal, drawn over the scrim
    L+=["resource","Label","{","ordernumber 38",'name "medIcon%d"'%i,
        "rect %d %d %d %d"%(round(bx0),round(by0),round(boxw),round(boxh)),
        "fgcolor 1.00 1.00 1.00 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
        'enabledcvar "coop_uiM%d"'%i,'shader "textures/hud/coop_sr/medal%d.tga"'%i,"}",""]


# [user 08-07] "PINNED n/5" live count. The word PINNED itself is baked into the page texture
# (an unquoted stufftext value stops at the first space, so the cvar must stay a single token).
L+=["resource","Label","{",'name "pinSummary"',"rect 302 74 60 14",
    "fgcolor 0.98 0.84 0.36 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
    "font \"verdana-12\"","textalign left","dontlocalize",'linkcvar "coop_pinCount"',"}",""]

# [user 2026-08-14] BLUEPRINT TOTAL, under its caption in the title banner. Binds to the SAME
# cvar the top blueprint challenge row already publishes (coop_uiN<gi>, a ready-made "17/31"),
# so there is no second counter that can drift from the first. The index is resolved HERE at
# generation time from the generator's own cid->index map, because a global catalog index moves
# whenever challenges are added or reordered - a hard-coded one would silently come to point at
# some other challenge. The rect comes from page_bg, which is where the caption was actually
# laid out and asserted, so the Label cannot drift away from the word it belongs to.
if "bp_60" not in idx:
    raise SystemExit("gen_service_record: bp_60 not found - the blueprint header has nothing to bind to")
if BP_LABEL_RECT is None:
    raise SystemExit("gen_service_record: page_bg never laid out the blueprint caption")
_bx,_by,_bw,_bh=BP_LABEL_RECT
L+=["resource","Label","{",'name "bpSummary"',"rect %d %d %d %d"%(_bx,_by,_bw,_bh),
    "fgcolor 0.20 0.13 0.05 1.00","bgcolor 0.00 0.00 0.00 0.00","borderstyle \"NONE\"",
    "font \"verdana-12\"","textalign center","dontlocalize",'linkcvar "coop_uiN%d"'%idx["bp_60"],"}",""]


L+=["end.",""]

for pi,(tl,hdr,items,isW) in enumerate(pages):
    page_bg(hdr,items,isW,rowhs[pi]).save("textures/mohmenu/coop_sr_p%d.tga"%pi)
open("ui/coop_sr.urc","w",encoding="latin-1").write("\n".join(L))

# One-shot reset for the pinned-row markers AND the medal lock cvars. They are archived client
# cvars, so without this a different profile on the same machine would inherit stale state.
# challenges.scr execs it once at load and then pushes the real ones (the servercmd filter
# permits exec for ui/coop_* paths). Medals default LOCKED (coop_uiML<i>=1) until medal_ui_export
# proves otherwise - the safe default if this cfg is ever exec'd without a follow-up push.
_NL = chr(10)   # built, not escaped - a \n literal here has been collapsed by a heredoc twice (T2)
open("ui/coop_sr_pinclear.cfg","w",encoding="latin-1",newline="").write(
    "// GENERATED by docs/tools/gen_service_record.py - clears every pinned-row marker + medal lock state." + _NL
    + "".join("seta coop_uiP%d 0" % i + _NL for i in range(len(rows)))
    + "".join("seta coop_uiM%d 0" % i + _NL for i in range(len(medals)))
    + "".join("seta coop_uiML%d 1" % i + _NL for i in range(len(medals))))
# [user 08-07] CLEAR PINS reset. Deliberately built from nothing but `seta`, a BUILTIN: the
# custom coop_srsync command demonstrably never executes from a UI stuffcommand (the pin count
# stayed frozen at a stale value through five rewrites of the code that computes it), whereas
# `exec` + `seta` are used successfully all over ui/loadout/*.cfg. This wipes the five pin slots,
# every row marker, and the summary, so a stale pin state can always be cleared by hand.
open("ui/coop_sr_pinreset.cfg","w",encoding="latin-1",newline="").write(
    "// GENERATED by docs/tools/gen_service_record.py - CLEAR PINS (builtins only)." + _NL
    + "".join('seta coop_pin%d ""' % k + _NL for k in range(1,6))
    + "".join("seta coop_uiP%d 0" % i + _NL for i in range(len(rows)))
    + 'seta coop_pinCount "0/5"' + _NL)
# [user 2026-08-18] index->cid map for the CLIENT pin store. CL_PinToggle_f archived pins as
# raw catalogue indices, so every catalogue renumber silently repointed every player's pins at
# different challenges (the panzerfaust removal shifted every later row by 3). Pins now persist
# as cids; this map lets the client resolve a clicked row to its cid with no server. Emitted by
# the same generator as the pages, so it can never drift from them - and build.ps1 regenerates
# both on every build.
# `set`, NOT `seta`: an archived map would persist across updates and the lazy-load check
# ("is coop_srCid0 empty?") would never fire again - the map must die with the session so every
# session loads the CURRENT one. coop_srGen is a hash of the cid list: CL_SyncSR_f compares it
# to the archived coop_srGenSeen and wipes the archived per-row progress/done state on mismatch,
# because those rows were written for a different catalogue layout (self-heal; the next server
# join re-exports truth). [user 2026-08-18] "WE need to ensure this kind of stuff self heals."
import zlib as _zlib
_gen = "%08x" % (_zlib.crc32("|".join(r[0] for r in rows).encode()) & 0xffffffff)
open("ui/coop_sr_cids.cfg","w",encoding="latin-1",newline="").write(
    "// GENERATED by docs/tools/gen_service_record.py - row index -> cid map (pin store)." + _NL
    + "set coop_srGen " + _gen + _NL
    + "".join("set coop_srCid%d %s" % (i, r[0]) + _NL for i, r in enumerate(rows)))
# [user 2026-08-18] DEPLOYED-TRUTH STAMP: tree-level gates prove the TREE agrees with itself,
# but the running game mounts pk3s - a stale deploy or a shadowing pak can still serve old
# pages next to new scripts. This stamp is compiled INTO the script side; chal_init compares it
# against the live challenge count at every boot and prints a machine-parseable SELFTEST line.
open("coop_mod/gen_sr_stamp.scr","w",encoding="latin-1",newline="").write(
    "//GENERATED by docs/tools/gen_service_record.py - deployed-truth stamp. DO NOT EDIT." + _NL
    + "main:{" + _NL
    + "	level.coop_srRowsBaked = %d" % len(rows) + _NL
    + "	level.coop_srGenBaked = \"%s\"" % _gen + _NL
    + "}end" + _NL)
print("deploy stamp: coop_mod/gen_sr_stamp.scr")
print("pin cid map: ui/coop_sr_cids.cfg (%d rows, gen %s)" % (len(rows), _gen))
print("pin reset: ui/coop_sr_pinreset.cfg (%d markers)" % len(rows))
print("pin markers: %d rows + ui/coop_sr_pinclear.cfg" % len(rows))
print("medals: %d (textures/mohmenu/coop_sr_medals.tga)" % len(medals))
print("DONE: %d pages, %d challenges"%(NT,len(rows)))
print("view-state cvars: coop_srP0..coop_srP%d  (%d total) + coop_srMedals"%(NT-1,NT))
print("page list (tab -> header -> rows -> rowh):")
for i,p in enumerate(pages):
    print("  P%-2d  %-11s  %-18s  %2d rows  rowh=%d"%(i,p[0],p[1],len(p[2]),rowhs[i]))
