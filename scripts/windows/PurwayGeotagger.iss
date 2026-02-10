; Inno Setup installer for Purway Geotagger (Windows).
; This installs the PyInstaller onedir output (PurwayGeotagger.exe + _internal/).
; Build expects:
;   dist\\windows\\PurwayGeotagger\\PurwayGeotagger.exe
;   dist\\windows\\PurwayGeotagger\\_internal\\...

#define MyAppName "PurwayGeotagger"
#define MyAppPublisher "ArchAerial"
#define MyAppURL "https://github.com/ArchAerialData/purway_geotagger_app"
#define MyAppExeName "PurwayGeotagger.exe"

; Prefer version provided by CI via env var, but fall back so local builds work.
#define MyAppVersion GetEnv("APP_VERSION")
#if MyAppVersion == ""
  #define MyAppVersion "0.0.0"
#endif

[Setup]
AppId={{52F7D0A1-EC98-40C3-9BB1-3F8F5E3F9B1B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\..\dist\windows-installer
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\\..\\dist\\windows\\PurwayGeotagger\\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\\..\\dist\\windows\\PurwayGeotagger\\_internal\\*"; DestDir: "{app}\\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"
Name: "{autodesktop}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
