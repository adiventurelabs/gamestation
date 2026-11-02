' Silent Background Launcher for PlayStation Console Service
' Starts pythonw without exposing any console window or terminal.

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get project root folder
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strProjectRoot = objFSO.GetParentFolderName(strScriptDir)

' Change directory to project root
objShell.CurrentDirectory = strProjectRoot

' Launch pythonw.exe in hidden window mode (0)
strCommand = "pythonw.exe -m psconsole.service"
objShell.Run strCommand, 0, False
