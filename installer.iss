; Inno Setup script for Metafrasi
#define AppName "Metafrasi"
#define AppVersion "1.0"
#define AppExe "Metafrasi.exe"

[Setup]
AppId={{B8C4F2D5-7E36-4A29-8D1B-6F3C9E5A82B7}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Metafrasi
DefaultDirName={localappdata}\Metafrasi
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=Metafrasi-Setup
SetupIconFile=metafrasi.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\metafrasi.ico
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Εικονίδιο στην επιφάνεια εργασίας"; GroupDescription: "Επιπλέον εικονίδια:"; Flags: checkedonce

[Files]
Source: "dist\Metafrasi\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "metafrasi.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\metafrasi.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\metafrasi.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Άνοιγμα του Metafrasi"; Flags: nowait postinstall skipifsilent
