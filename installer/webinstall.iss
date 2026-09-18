; MOH Coop Trilogy WEB installer - a small stub that downloads the current release from GitHub.
; Reuses the full installer's GOG detection + side-by-side safety verbatim, but ships ONLY the
; small bootstrap files (updater, launcher, config seed, MSVC runtime). The ~7.35 GB payload
; (engine, DLLs, all pk3s) is pulled by updater.ps1 on first run: with no installed_manifest.json
; present, the updater treats every file in the release manifest as missing and downloads them all.

#ifndef ReportWebhook
#define ReportWebhook ""
#endif
#ifndef AppVer
#define AppVer "1.0.0"
#endif
#define Dev "C:\mohaa-coop-dev"
#define Crt "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Redist\MSVC\14.51.36231\x64\Microsoft.VC145.CRT"

[Setup]
AppId={{7B7A1C64-HZMC-40OP-TRIL-OGY000000001}
AppName=MOH Coop Trilogy (HZM Extended)
AppVersion={#AppVer}
AppPublisher=HaZardModding / HZM Coop
DefaultDirName={localappdata}\MOH Coop Trilogy
DisableDirPage=no
DirExistsWarning=auto
AppendDefaultDirName=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#Dev}\installer\dist
OutputBaseFilename=MOHCoopTrilogy-WebSetup-{#AppVer}
SetupIconFile={#Dev}\installer\mohcoop.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\mohcoop.ico

[Messages]
WelcomeLabel2=This small setup installs MOH Coop Trilogy side by side with your GOG copy of Medal of Honor: Allied Assault War Chest - it never modifies your game.%n%nThe game files (about 7 GB) download automatically from GitHub the first time you launch, with a progress bar. You need your GOG game installed and an internet connection.

[Files]
; MSVC runtime (app-local; NOT in the update manifest, so the stub must carry it)
Source: "{#Crt}\vcruntime140.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Crt}\vcruntime140_1.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Crt}\msvcp140.dll"; DestDir: "{app}"; Flags: ignoreversion
; bootstrap: icon, problem reporter, the updater + its launcher, and the tuned default settings
Source: "{#Dev}\installer\mohcoop.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Dev}\installer\report_problem.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Dev}\updater\updater.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Dev}\updater\launch_coop.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Dev}\installer\omconfig_default.cfg"; DestDir: "{app}\home\maintt\configs"; DestName: "omconfig.cfg"; Flags: ignoreversion
; NOTE: no installed_manifest.json is shipped on purpose - its absence is what makes the first
; updater run download the entire manifest instead of diffing against a seed.

[InstallDelete]
Type: files; Name: "{autodesktop}\MOH Coop Trilogy.lnk"
Type: files; Name: "{autoprograms}\MOH Coop Trilogy.lnk"

[Icons]
Name: "{autodesktop}\MOH Trilogy Coop"; Filename: "{sys}\wscript.exe"; \
  Parameters: """{app}\launch_coop.vbs"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\mohcoop.ico"
Name: "{autoprograms}\MOH Trilogy Coop"; Filename: "{sys}\wscript.exe"; \
  Parameters: """{app}\launch_coop.vbs"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\mohcoop.ico"
Name: "{autoprograms}\MOH Trilogy Coop - Report a Problem"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\report_problem.ps1"""; WorkingDir: "{app}"; IconFilename: "{app}\mohcoop.ico"

[Run]
; On finish (checkbox, checked by default): run the launcher, which runs the updater. On this
; first run there is nothing installed, so the updater downloads the whole game with its own
; progress window and then starts it.
Filename: "{sys}\wscript.exe"; Parameters: """{app}\launch_coop.vbs"""; WorkingDir: "{app}"; Description: "Download the game files and start MOH Coop Trilogy now (~7 GB)"; Flags: nowait postinstall skipifsilent

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

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpSelectDir then
  begin
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
      'LaunchArgs=+set fs_basepath "' + GetGogPath('') + '" +set fs_homepath "' + ExpandConstant('{app}') + '\home" +set com_target_game 2 +set cl_renderer opengl2' + #13#10 +
      'ReportWebhook=' + '{#ReportWebhook}' + #13#10, False);
  end;
end;
