; HZM MOH Coop Trilogy installer
; Fully self-contained side-by-side install: NEVER writes to the user's GOG game or
; their own OpenMOHAA. Our engine exe + dlls live in {app} (engine finds cgame/game.dll
; and the renderer modules beside the exe - Sys_LoadDll searches the binary dir before
; fs_basepath), all mod/HD pk3s live under {app}\home\maintt which we pass as
; fs_homepath, and the vanilla game is only ever read through fs_basepath.

#ifndef ReportWebhook
#define ReportWebhook ""
#endif
#ifndef AppVer
#define AppVer "1.0.0"
#endif
#define Dev "C:\mohaa-coop-dev"
#define Bin Dev + "\openmohaa-hzm\.cmake"
#define Gog "G:\GOG\Medal of Honor - Allied Assault War Chest"
#define Mod Dev + "\hzm-mohaa-coop-mod"
#define Crt "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Redist\MSVC\14.51.36231\x64\Microsoft.VC145.CRT"

[Setup]
AppId={{7B7A1C64-HZMC-40OP-TRIL-OGY000000001}
AppName=MOH Coop Trilogy (HZM Extended)
AppVersion={#AppVer}
AppPublisher=HaZardModding / HZM Coop
; [2026-08-31] The destination page is SHOWN. DisableDirPage is left unset, which means Inno's
; default of `auto`: the page appears on a fresh install and is skipped only when a previous
; install of this AppId is found (then UsePreviousAppDir reuses that folder). The path below is
; therefore a DEFAULT the player can change, not a fixed location - said explicitly because the
; public README used to state it as a fact.
; localappdata is deliberate: PrivilegesRequired=lowest, so a non-admin install must land
; somewhere writable without elevation. A player who wants it elsewhere just browses.
DefaultDirName={localappdata}\MOH Coop Trilogy
; [2026-08-31] ALWAYS offer the folder choice. Inno's default here is `auto`, which HIDES
; the destination page whenever a previous install of this AppId is found - so anybody who
; already had the mod was silently given their old folder and never saw the option. Verified
; by screenshotting a demo build on a machine that had 1.4.6: the page did not appear at all.
; UsePreviousAppDir still pre-fills the previous location, so an upgrade stays one click,
; but moving the install somewhere else is now possible instead of impossible.
DisableDirPage=no
DirExistsWarning=auto
AppendDefaultDirName=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#Dev}\installer\dist
OutputBaseFilename=MOHCoopTrilogy-Setup-{#AppVer}
SetupIconFile={#Dev}\installer\mohcoop.ico
Compression=lzma2/fast
SolidCompression=no
; payload > 4.2GB Windows single-exe cap -> span into Setup.exe + .bin slices (keep together)
DiskSpanning=yes
DiskSliceSize=2100000000
WizardStyle=modern
UninstallDisplayIcon={app}\mohcoop.ico

[Files]
; --- engine (HZM fork) + libraries, loaded from beside the exe ---
Source: "{#Bin}\Release\openmohaa.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Bin}\code\client\cgame\Release\cgame.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Bin}\code\server\fgame\Release\game.dll"; DestDir: "{app}"; Flags: ignoreversion
; renderer modules (USE_RENDERER_DLOPEN=ON - the engine dlopens these from beside the exe)
Source: "{#Bin}\code\renderercommon\renderergl1\Release\renderer_opengl1.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Bin}\code\renderercommon\renderergl2\Release\renderer_opengl2.dll"; DestDir: "{app}"; Flags: ignoreversion
; [user 2026-08-10] dedicated server binary - keep in lockstep with package_installer.ps1
Source: "{#Bin}\Release\omohaaded.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Gog}\SDL2.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Gog}\OpenAL64.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Gog}\libcurl.dll"; DestDir: "{app}"; Flags: ignoreversion
; app-local MSVC runtime so clean machines without the VC++ redist still run (no UAC needed)
Source: "{#Crt}\vcruntime140.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Crt}\vcruntime140_1.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Crt}\msvcp140.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Dev}\installer\mohcoop.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Dev}\installer\report_problem.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Dev}\updater\updater.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Dev}\updater\launch_coop.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Dev}\installer\installed_manifest_seed.json"; DestDir: "{app}"; DestName: "installed_manifest.json"; Flags: ignoreversion
; --- mod + HD content -> our private homepath ---
Source: "{#Gog}\maintt\zzzzz-AA_HD_Project_Pak1.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzz-AA_HD_Project_Pak2.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzz-AA_HD_Project_Pak3.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzz-AA_HD_Project_Pak4.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzz-hd_gunsounds.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzz_geared_soldiers.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzz_hd_foliage.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz-HRRTM_Pak1_Models.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz-HRRTM_Pak2_Models_misc.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz-HRRTM_Pak3_Textures.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz-HRRTM_Pak4_Weapons.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz-HRRTM_Pak4c_WeaponTGA.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Mod}\zzzzzz_co-op_hzm_mod_assets_snd.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Mod}\zzzzzz_co-op_hzm_mod_assets_tex.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Mod}\zzzzzz_co-op_hzm_mod_code.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
; [2026-08-30] CC0 terrain pak (bug-2164, CC0 ground replacement). Built out-of-band by docs/tools/build_terrain_pack.py and deployed by build.ps1, but it reached NEITHER the release manifest NOR the installer, so it only ever existed on the dev machine.
; MUST stay in lockstep with $stage in package_installer.ps1 - that list seeds
; installed_manifest.json, so shipping a file the seed does not name makes the seed lie.
Source: "{#Mod}\zzzzzzzzz_coop_terrain.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz_hd_charskins.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz_hd_fx.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz_hd_skybox.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz_hd_world.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzzz-HRRTM_Blood_effects_Addon.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzzz_dds_override.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzzz_dds_hdmem.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Dev}\hzm-mohaa-coop-mod\autoexec.cfg"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
; ship the tuned default settings (dev config, sanitized: 1080p, no personal name/device)
Source: "{#Dev}\installer\omconfig_default.cfg"; DestDir: "{app}\home\maintt\configs"; DestName: "omconfig.cfg"; Flags: ignoreversion

[InstallDelete]
; upgrade hygiene: remove shortcuts created by earlier 1.0.0 builds (old name, and the
; misleading Spearhead entry that launched vanilla SH without the mod)
Type: files; Name: "{autodesktop}\MOH Coop Trilogy.lnk"
Type: files; Name: "{autoprograms}\MOH Coop Trilogy.lnk"
Type: files; Name: "{autoprograms}\MOH Coop Trilogy (Spearhead maps).lnk"
Type: files; Name: "{autoprograms}\MOH Trilogy Coop (Spearhead maps).lnk"
Type: files; Name: "{app}\home\maintt\zzzzzz_co-op_hzm_mod_mohaa.pk3"

[Icons]
Name: "{autodesktop}\MOH Trilogy Coop"; Filename: "{sys}\wscript.exe"; \
  Parameters: """{app}\launch_coop.vbs"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\mohcoop.ico"
Name: "{autoprograms}\MOH Trilogy Coop"; Filename: "{sys}\wscript.exe"; \
  Parameters: """{app}\launch_coop.vbs"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\mohcoop.ico"
Name: "{autoprograms}\MOH Trilogy Coop - Report a Problem"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\report_problem.ps1"""; WorkingDir: "{app}"; IconFilename: "{app}\mohcoop.ico"

[Code]
var
  GogPage: TInputDirWizardPage;

function DetectGogPath(): String;
var
  P: String;
begin
  Result := '';
  if RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\GOG.com\Games\1207659126', 'PATH', P) then
    Result := P
  else if RegQueryStringValue(HKLM, 'SOFTWARE\GOG.com\Games\1207659126', 'PATH', P) then
    Result := P;
end;

{ [2026-08-31] WAR CHEST means all three games, and the mod genuinely needs all three.
  The shortcut launches with com_target_game 2 (Breakthrough), and at that target the engine
  mounts main + mainta + maintt. Validation used to accept any folder holding main\Pak0.pk3,
  so a plain MOHAA install - or MOHAA + Spearhead without Breakthrough - passed setup happily
  and produced a broken game later, with nothing pointing back at the cause.
  MissingGameData returns the first missing piece by name so the player is told WHICH game is
  absent instead of "that folder does not look right". }
function MissingGameData(const P: String): String;
var
  B: String;
begin
  B := AddBackslash(P);
  Result := '';
  if not FileExists(B + 'main\Pak0.pk3') then
    Result := 'Medal of Honor: Allied Assault  (main\Pak0.pk3)'
  else if not DirExists(B + 'mainta') then
    Result := 'the Spearhead expansion  (mainta folder)'
  else if not DirExists(B + 'maintt') then
    Result := 'the Breakthrough expansion  (maintt folder)';
end;

function IsValidGogPath(const P: String): Boolean;
begin
  Result := (MissingGameData(P) = '');
end;

{ [2026-08-31] The game page is created after wpWelcome, i.e. BEFORE the destination page.
  It used to sit after wpSelectDir, which asked the player to choose an install folder before
  anything had told them the mod needs their retail game at all - and it made the
  "don't install inside your GOG folder" check impossible to run at wpSelectDir, because the
  GOG path was not known yet. That check had to bounce the player Back a page. Asking for the
  game first fixes both: the hard prerequisite fails early, and every destination rule can be
  answered the moment the folder is picked. }
procedure InitializeWizard();
var
  Detected: String;
begin
  GogPage := CreateInputDirPage(wpWelcome,
    'Locate Medal of Honor: Allied Assault War Chest',
    'Where is your MOHAA War Chest installed?',
    'MOH Coop Trilogy is a mod, not a standalone game - it needs the retail game data from a ' +
    'copy of MOHAA War Chest you already own (the GOG edition). That folder is only ever READ; ' +
    'nothing in it is modified, and you can keep playing the original campaign normally.' + #13#10 +
    'If the detected path is wrong or empty, browse to the folder containing MOHAA.exe and the ' +
    'main / mainta / maintt subfolders.',
    False, '');
  GogPage.Add('');
  Detected := DetectGogPath();
  if Detected <> '' then
    GogPage.Values[0] := Detected;
end;

{ Replace the stock "Setup will install into the following folder" text with something that
  actually tells the player what this folder is and what not to point it at. Inno still appends
  its own free-space line underneath. }
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpSelectDir then
  begin
    { SelectDirLabel is a fixed-height control and does NOT grow with its text - a long caption
      is silently clipped to the first line, which is what happened on the first attempt here.
      Grow the label and push the two controls below it down by the same amount, then keep the
      text short enough to fit. The detailed rules are not repeated here on purpose: they are
      enforced by the refusal dialogs, and nobody reads a wall of text on a wizard page. }
    WizardForm.SelectDirLabel.AutoSize := False;
    WizardForm.SelectDirLabel.Height := ScaleY(46);
    WizardForm.SelectDirBrowseLabel.Top := WizardForm.SelectDirLabel.Top + ScaleY(54);
    WizardForm.DirEdit.Top          := WizardForm.SelectDirBrowseLabel.Top + ScaleY(20);
    WizardForm.DirBrowseButton.Top  := WizardForm.DirEdit.Top - ScaleY(2);
    WizardForm.SelectDirLabel.Caption :=
      'Choose where to install MOH Coop Trilogy. This is a NEW, self-contained folder - ' +
      'the engine, the mod, and your saves and settings all live here, separate from the ' +
      'copy of the game you already own. Any folder you can write to will do.';
  end;
end;

{ [2026-08-31] Is the chosen destination somebody's EXISTING game or engine install?
  The player picks this folder freely, and Setup writes openmohaa.exe, cgame.dll, game.dll and
  both renderers straight into it. Dropped on an existing OpenMOHAA checkout or build, that
  silently replaces their binaries with ours; dropped inside the GOG folder, it breaks the one
  guarantee this installer makes - that your original game is only ever READ.
  IsOurInstall lets a re-install over our own folder through untouched. }
function IsOurInstall(const P: String): Boolean;
begin
  Result := FileExists(AddBackslash(P) + 'install_info.txt') or
            FileExists(AddBackslash(P) + 'updater.ini');
end;

function LooksLikeForeignEngine(const P: String): Boolean;
begin
  Result := (not IsOurInstall(P)) and
            (FileExists(AddBackslash(P) + 'openmohaa.exe') or
             FileExists(AddBackslash(P) + 'omohaaded.exe') or
             FileExists(AddBackslash(P) + 'launch_openmohaa_base.exe'));
end;

function LooksLikeRetailGame(const P: String): Boolean;
begin
  Result := FileExists(AddBackslash(P) + 'MOHAA.exe') or
            FileExists(AddBackslash(P) + 'main\Pak0.pk3');
end;

function IsInside(const Child, Parent: String): Boolean;
var
  C, R: String;
begin
  C := AddBackslash(Lowercase(Child));
  R := AddBackslash(Lowercase(Parent));
  Result := (R <> '\') and (Copy(C, 1, Length(R)) = R);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Dest: String;
begin
  Result := True;

  if CurPageID = wpSelectDir then
  begin
    Dest := WizardDirValue();

    if LooksLikeRetailGame(Dest) then
    begin
      MsgBox('That folder is a Medal of Honor game install.' + #13#10#13#10 +
             'MOH Coop Trilogy installs SIDE BY SIDE and only ever READS your original game. ' +
             'Installing into it would modify it, which is exactly what this installer avoids.' + #13#10#13#10 +
             'Please choose a different folder.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if LooksLikeForeignEngine(Dest) then
    begin
      MsgBox('That folder already contains an OpenMOHAA installation that was not put there ' +
             'by this installer.' + #13#10#13#10 +
             'Installing here would overwrite openmohaa.exe, cgame.dll, game.dll and the ' +
             'renderers with our builds, and break that installation.' + #13#10#13#10 +
             'Please choose a different folder.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    { The game folder is known by now - it is asked for on the page before this one. }
    if (GogPage <> nil) and (GogPage.Values[0] <> '') and IsInside(Dest, GogPage.Values[0]) then
    begin
      MsgBox('That folder is inside your Medal of Honor game folder.' + #13#10#13#10 +
             'The mod installs side by side with your game, never inside it, so that your ' +
             'original install stays exactly as it is.' + #13#10#13#10 +
             'Please choose a folder outside it.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;

  if (GogPage <> nil) and (CurPageID = GogPage.ID) then
  begin
    if not IsValidGogPath(GogPage.Values[0]) then
    begin
      MsgBox('That folder is missing ' + MissingGameData(GogPage.Values[0]) + '.' + #13#10#13#10 +
             'MOH Coop Trilogy covers all three games, so it needs a War Chest install ' +
             'containing main, mainta and maintt.' + #13#10#13#10 +
             'Please browse to the folder that contains MOHAA.exe and those three subfolders.',
             mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

function GetGogPath(Param: String): String;
begin
  Result := RemoveBackslashUnlessRoot(GogPage.Values[0]);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    SaveStringToFile(ExpandConstant('{app}') + '\install_info.txt',
      'Version=' + '{#AppVer}' + #13#10 +
      'GogPath=' + GetGogPath('') + #13#10 +
      'InstalledOn=' + GetDateTimeString('yyyy/mm/dd hh:nn', '-', ':') + #13#10, False);
    { updater config: launch args live here (not in the shortcut) so updates can adjust them }
    SaveStringToFile(ExpandConstant('{app}') + '\updater.ini',
      'Version=' + '{#AppVer}' + #13#10 +
      'GogPath=' + GetGogPath('') + #13#10 +
      'ManifestUrl=https://github.com/MOHCoopTrilogy/releases/releases/latest/download/manifest.json' + #13#10 +
      'ManifestUrlFallback=https://raw.githubusercontent.com/MOHCoopTrilogy/releases/main/manifests/latest.json' + #13#10 +
      'LaunchArgs=+set fs_basepath "' + GetGogPath('') + '" +set fs_homepath "' + ExpandConstant('{app}') + '\home" +set com_target_game 2' + #13#10 +
      'ReportWebhook=' + '{#ReportWebhook}' + #13#10, False);
  end;
end;
