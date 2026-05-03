Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
releaseExeA = projectDir & "\src-tauri\target\release\topjobs-auto-mailer-shell.exe"
releaseExeB = projectDir & "\src-tauri\target\release\TopJobs Auto Mailer.exe"
launcherBat = projectDir & "\run_desktop_app.bat"
args = ""

If WScript.Arguments.Count > 0 Then
    args = " "
    For i = 0 To WScript.Arguments.Count - 1
        If i > 0 Then
            args = args & " "
        End If
        args = args & WScript.Arguments(i)
    Next
End If

shell.CurrentDirectory = projectDir

If fso.FileExists(releaseExeA) Then
    shell.Run Chr(34) & releaseExeA & Chr(34) & args, 0, False
ElseIf fso.FileExists(releaseExeB) Then
    shell.Run Chr(34) & releaseExeB & Chr(34) & args, 0, False
ElseIf fso.FileExists(launcherBat) Then
    shell.Run "cmd /c " & Chr(34) & launcherBat & Chr(34) & args, 0, False
Else
    MsgBox "TopJobs Auto Mailer launcher was not found.", 16, "TopJobs Auto Mailer"
End If
