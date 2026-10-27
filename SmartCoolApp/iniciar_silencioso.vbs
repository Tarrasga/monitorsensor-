Set oWS = CreateObject("WScript.Shell")
oWS.CurrentDirectory = "E:\Gravi"
oWS.Run "cmd.exe /c ""E:\Gravi\INICIAR_MONSTER_TELEMETRIA.bat""", 0, False
