; Inno Setup script for Cortex Cleaner
; ------------------------------------
; Prerequisites:
;   1. Build the app:  pyinstaller CortexCleaner.spec --noconfirm
;      -> produces dist\CortexCleaner\ (onedir)
;   2. Sign every PE (see installer\sign.ps1) BEFORE wrapping:
;      unsigned-then-installed files keep the "unsigned" reputation penalty.
;   3. ISCC.exe cortex_cleaner.iss
;
; Design notes (from the distribution research runbook):
;   - onedir, never onefile: onefile self-extracts to %TEMP% at every launch
;     and is shaped like malware to AV heuristics.
;   - The installer itself does NOT require admin for a per-user install;
;     "privilegesrequired=lowest" keeps UAC quiet for standard users. The app
;     elevates individual privileged operations itself.
;   - Do NOT name the output setup.exe - that name is a DLL-injection vector
;     via the compatibility layer (NSIS/Inno best practice).

#define MyAppName "Cortex Cleaner"
#define MyAppVersion GetFileVersion("..\dist\CortexCleaner\CortexCleaner.exe")
#define MyAppPublisher "Cortex Cleaner Project"
#define MyAppExeName "CortexCleaner.exe"

[Setup]
AppId={{7C1E4BB2-6F3A-4B8E-9A55-CORTEXCLEANR}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Per-user fallback: non-admins install to their own profile instead.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=CortexCleaner-{#MyAppVersion}-setup
OutputDir=installer_output
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Signed uninstaller keeps its signature after updates.
Uninstallable=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\CortexCleaner\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove runtime logs/backups the app wrote inside its own folder only.
Type: filesandordirs; Name: "{app}\logs"
