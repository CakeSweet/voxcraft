; Script do Inno Setup 6 para gerar o instalador Windows (VoxCraftStudio_Setup.exe)
; Execute build_installer.bat ou abra este arquivo no Inno Setup Compiler.

#define MyAppName "VoxCraft Studio"
#ifndef MyAppVersion
  #define MyAppVersion "2.1.0"
#endif
#define MyAppPublisher "CakeSweet"
#define MyAppExeName "VoxCraftStudio.exe"

[Setup]
AppId={{8F4C2D1B-7E9A-4B63-A82C-9D5E6F103A21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=Output
OutputBaseFilename=VoxCraftStudio_Setup
SetupIconFile=assets\voxcraft.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
ShowLanguageDialog=yes
LanguageDetectionMethod=none
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
english.UninstallApp=Uninstall {#MyAppName}
portuguese.UninstallApp=Desinstalar {#MyAppName}
spanish.UninstallApp=Desinstalar {#MyAppName}

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\VoxCraftStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\voxcraft.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallApp}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  CfgDir, CfgFile, LangCode: string;
begin
  if CurStep = ssPostInstall then
  begin
    CfgDir := ExpandConstant('{userappdata}\VoxCraftStudio');
    CfgFile := CfgDir + '\voxcraft_config.json';
    if not FileExists(CfgFile) then
    begin
      ForceDirectories(CfgDir);
      if ActiveLanguage = 'portuguese' then
        LangCode := 'pt'
      else if ActiveLanguage = 'spanish' then
        LangCode := 'es'
      else
        LangCode := 'en';
      SaveStringToFile(CfgFile, '{"language": "' + LangCode + '"}', False);
    end;
  end;
end;
