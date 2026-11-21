; Generated definitions come from scripts/branding_metadata.py.
#include "..\..\build\branding\windows-branding.iss"
[Setup]
; Legacy AppName was the implicit AppId. Keep it to recognize existing installs.
AppId={#LegacyAppId}
AppName={#ProductName}
AppVersion={#AppVersion}
VersionInfoVersion={#NumericVersion}
VersionInfoProductVersion={#NumericVersion}
VersionInfoProductTextVersion={#AppVersion}
ArchitecturesAllowed=x64compatible and not arm64
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
DefaultDirName={localappdata}\Programs\{#ProductName}
UsePreviousAppDir=yes
PrivilegesRequired=lowest
AppPublisherURL=https://github.com/drrrrigo/cactu-video-converter
AppSupportURL=https://github.com/drrrrigo/cactu-video-converter/issues
LicenseFile=..\..\LICENSE
OutputDir=..\..\dist
OutputBaseFilename={#ExecutableName}-Setup-{#AppVersion}
SetupIconFile=..\..\assets\branding\cactu-video-converter.ico
UninstallDisplayIcon={app}\{#ExecutableName}.exe
VersionInfoProductName={#ProductName}
VersionInfoDescription={#ProductName} Setup
Compression=lzma2
SolidCompression=yes

[InstallDelete]
Type: files; Name: "{app}\VideoConverter.exe"
Type: files; Name: "{autoprograms}\Video Converter.lnk"
Type: files; Name: "{autodesktop}\Video Converter.lnk"

[Files]
Source: "..\..\dist\{#ExecutableName}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
Source: "..\..\dist\{#ExecutableName}\{#ExecutableName}.exe"; DestName: "CactuPrerequisiteCheck.exe"; Flags: dontcopy

[Icons]
Name: "{autoprograms}\{#ProductName}"; Filename: "{app}\{#ExecutableName}.exe"
Name: "{autodesktop}\{#ProductName}"; Filename: "{app}\{#ExecutableName}.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  ExtractTemporaryFile('CactuPrerequisiteCheck.exe');
  if not Exec(ExpandConstant('{tmp}\CactuPrerequisiteCheck.exe'),
      '--check-prerequisites', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := 'Cactu could not check the Microsoft Visual C++ runtime prerequisite.'
  else if ResultCode <> 0 then
    Result := 'Install or repair Microsoft Visual C++ v14 Redistributable (X64), ' +
      '14.51.36247.0 or newer, then run Cactu Setup again. ' +
      'Official guidance: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist . ' +
      'No installer is downloaded or run automatically.';
end;
