; -----------------------------------------------------------------------------
; setup.iss — Inno Setup script for Vibe Protect (Windows)
;
; Build locally:
;   python installer\build_windows.py
; or in CI via .github/workflows/release-windows.yml
;
; Output: dist\VibeProtect-Setup-{version}.exe
; -----------------------------------------------------------------------------

#define MyAppName "Vibe Protect"
#define MyAppPublisher "Vibe Protect contributors"
#define MyAppURL "https://github.com/vibeprotect/vibe-protect"
#define MyAppExeName "vibe_desktop.exe"

; VP_VERSION is passed on the ISCC command line (/DVP_VERSION=2.0.0) so we
; stay in lock-step with /app/VERSION without duplicating it here.
#ifndef VP_VERSION
  #define VP_VERSION "0.0.0-dev"
#endif

[Setup]
AppId={{9A9C1BDE-7C24-4F5C-9E5C-7D13AF8E4E2A}
AppName={#MyAppName}
AppVersion={#VP_VERSION}
AppVerName={#MyAppName} {#VP_VERSION}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

DefaultDirName={userpf}\VibeProtect
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

OutputDir=..\dist
OutputBaseFilename=VibeProtect-Setup-{#VP_VERSION}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
SetupIconFile=icon.ico

; Don't bother if Windows is ancient
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startupicon"; Description: "Start Vibe Protect when Windows starts"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\dist\vibe_desktop\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\vibe_desktop\*";               DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "patterns.json";                         DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico";                              DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE";                            DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "..\README.md";                          DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}";            Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}";             Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}";             Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon
Name: "{group}\Uninstall {#MyAppName}";         Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
; Leave user config (~/.vibeprotect) untouched unless asked — helpful on upgrade reinstalls
Type: files; Name: "{app}\patterns.json"
