' MOH Coop Trilogy launcher shim: runs the updater with no console window.
' The updater checks for updates (fast, silent when up to date) and then starts the game.
Dim sh, fso, here
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & here & "\updater.ps1""", 0, False
