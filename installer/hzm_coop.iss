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
DefaultDirName={localappdata}\MOH Coop Trilogy
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
Source: "{#Gog}\maintt\zzzzzz_hd_charskins.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz_hd_fx.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz_hd_skybox.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzz_hd_world.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzzz-HRRTM_Blood_effects_Addon.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
Source: "{#Gog}\maintt\zzzzzzz_dds_override.pk3"; DestDir: "{app}\home\maintt"; Flags: ignoreversion
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

function IsValidGogPath(const P: String): Boolean;
begin
  Result := FileExists(AddBackslash(P) + 'main\Pak0.pk3');
end;

procedure InitializeWizard();
var
  Detected: String;
begin
  GogPage := CreateInputDirPage(wpSelectDir,
    'Locate Medal of Honor: Allied Assault War Chest',
    'Where is your MOHAA War Chest installed?',
    'Setup needs your existing game (GOG "War Chest" edition). It is only READ - ' +
    'nothing in that folder is ever modified. If the detected path is wrong, browse to ' +
    'the folder that contains MOHAA.exe and the main/mainta/maintt folders.',
    False, '');
  GogPage.Add('');
  Detected := DetectGogPath();
  if Detected <> '' then
    GogPage.Values[0] := Detected;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (GogPage <> nil) and (CurPageID = GogPage.ID) then
  begin
    if not IsValidGogPath(GogPage.Values[0]) then
    begin
      MsgBox('That folder does not look like a MOHAA War Chest install ' +
             '(main\Pak0.pk3 not found). Please pick the game''s root folder.', mbError, MB_OK);
      Result := False;
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
