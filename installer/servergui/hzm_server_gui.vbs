' MOH Coop Trilogy - "MOH Coop Server" shortcut shim: opens the server host window (hzm_server_gui.ps1) with no
' console window. Arguments pass through (start-with-Windows uses: -Supervise "<profile>").
Dim sh, fso, here, a, i
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
a = ""
For i = 0 To WScript.Arguments.Count - 1
    a = a & " """ & Replace(WScript.Arguments(i), """", "") & """"
Next
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File """ & here & "\hzm_server_gui.ps1""" & a, 0, False
