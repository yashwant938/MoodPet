[Setup]
AppId={{EEDC6678-72C1-4C3E-A6F1-73ACF5763F9A}
AppName=MoodPet
AppVersion=0.2.0
AppPublisher=Yashwant Singh Rana
DefaultDirName={localappdata}\Programs\MoodPet
DefaultGroupName=MoodPet
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=MoodPet-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\MoodPet.exe

[Files]
Source: "..\dist\MoodPet\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MoodPet"; Filename: "{app}\MoodPet.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall MoodPet"; Filename: "{uninstallexe}"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "MoodPet"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\MoodPet.exe"; Description: "Open MoodPet"; Flags: nowait postinstall skipifsilent unchecked
