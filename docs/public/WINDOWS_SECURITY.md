# Windows says the installer or game is blocked - what this means

The HZM Coop Mod installer and the OpenMOHAA game files (`openmohaa.exe`, `omohaaded.exe` and the `.dll` files) are
**not code-signed yet**. Code-signing certificates cost money each year and this is a free community project. Windows
therefore treats the files as "unknown", even though the full source code is public on GitHub.

**Only download the mod from the official GitHub releases page.** Every release lists a SHA-256 checksum for each
download. To check yours, open PowerShell in your Downloads folder and run:

```
Get-FileHash .\<file you downloaded> -Algorithm SHA256
```

The value must match the one listed on the release page exactly. If it doesn't, delete the file and download it again.

## "Windows protected your PC" (SmartScreen)

This is the common warning, and it can be bypassed per file:

1. Click **More info**.
2. Click **Run anyway**.

If the button is missing, right-click the downloaded file, choose **Properties**, tick **Unblock** at the bottom of the
General tab, click **OK**, then run it again.

## Smart App Control blocked it (Windows 11)

Smart App Control is stricter. It has **no "Run anyway" button**, and it cannot allow one single program. Your options:

- **Use the zip download instead of the installer.** Unzip it into your game folder as the release notes describe. If
  Windows then blocks `openmohaa.exe`, the only option is the next one.
- **Turn Smart App Control off:** **Settings > Privacy & security > Windows Security > App & browser control >
  Smart App control settings > Off**.
  - **Read this first:** on many Windows 11 versions this switch is **one-way**. Smart App Control may not turn back on
    without resetting or reinstalling Windows; check what your Windows version says on that screen before you switch
    it off.
  - Microsoft Defender antivirus keeps protecting your PC either way.
  - Only do this if you are comfortable with that trade-off.

We are working on getting the files signed so that this step is no longer needed.

## Antivirus warnings

Some antivirus tools flag unsigned game engines by reputation alone. If yours quarantines `openmohaa.exe`:

1. Check the file's checksum against the release page first.
2. Then restore the file and add the game folder as an exclusion in that antivirus.
