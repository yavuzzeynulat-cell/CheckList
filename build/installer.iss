; CheckList kurulumu. Derleme: build/publish.py (elle: iscc build\installer.iss)
#define MyAppName "CheckList"
#define VerFile = FileOpen("..\src\version.txt")
#define MyAppVersion = Trim(FileRead(VerFile))
#expr FileClose(VerFile)
#define MyAppExe "CheckList.exe"

[Setup]
; AppId ASLA degismez (degisirse ikinci kurulum olusur; updater kayit
; anahtarini "CheckList_is1" olarak arar).
AppId=CheckList
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Yavuz Zeynula
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=out
OutputBaseFilename=CheckList-Setup
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Kullanici bazinda: admin gerekmez ve updater src/'ye yazabilir.
PrivilegesRequired=lowest
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[InstallDelete]
; Eski kurulumdan kalan geri donus kopyasi yeni EXE ile uyumsuz olabilir.
Type: filesandordirs; Name: "{app}\src_backup"

[Files]
Source: "..\dist\CheckList\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
