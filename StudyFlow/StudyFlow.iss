#define MyAppName "StudyFlow"
#define MyAppVersion "1.0"
#define MyAppPublisher "Ayush Nelgi"
#define MyAppExeName "StudyFlow.exe"

[Setup]
AppId={{9E1F3D53-7E92-48A2-9A0F-9F8E8D7C5A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\StudyFlow
DefaultGroupName=StudyFlow

OutputDir=Installer
OutputBaseFilename=StudyFlow_Setup_v1.0

Compression=lzma2
SolidCompression=yes

WizardStyle=modern

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

PrivilegesRequired=admin

DisableProgramGroupPage=yes

SetupIconFile=app\assets\icons\logo.ico
UninstallDisplayIcon={app}\StudyFlow.exe

VersionInfoVersion=1.0.0.0
VersionInfoProductName=StudyFlow
VersionInfoCompany=Ayush Nelgi
VersionInfoDescription=StudyFlow Productivity Suite

ChangesAssociations=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startup"; Description: "Start StudyFlow automatically when Windows starts"; GroupDescription: "Startup options:"; Flags: unchecked

[Files]
Source: "dist\StudyFlow\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\StudyFlow"; Filename: "{app}\StudyFlow.exe"
Name: "{autodesktop}\StudyFlow"; Filename: "{app}\StudyFlow.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; \
Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
ValueType: string; \
ValueName: "StudyFlow"; \
ValueData: """{app}\StudyFlow.exe"""; \
Tasks: startup; \
Flags: uninsdeletevalue

[Run]
Filename: "{app}\StudyFlow.exe"; \
Description: "Launch StudyFlow"; \
Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]

function InitializeSetup(): Boolean;
begin
  Result := True;
end;