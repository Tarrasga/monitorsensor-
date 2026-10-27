Set oWS = CreateObject("WScript.Shell")
oWS.CurrentDirectory = "E:\Gravi"
oWS.Run "cmd.exe /c ""E:\Gravi\INICIAR_APP_SMARTCOOL.bat""", 0, False
