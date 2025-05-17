[Setup]
AppName=YouTube下载器
AppVersion=1.0.0
DefaultDirName={autopf}\YouTube下载器
DefaultGroupName=YouTube下载器
UninstallDisplayIcon={app}\YouTube下载器.exe
OutputDir=Output
OutputBaseFilename=YouTube下载器_安装程序
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\YouTube下载器\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\YouTube下载器"; Filename: "{app}\YouTube下载器.exe"
Name: "{commondesktop}\YouTube下载器"; Filename: "{app}\YouTube下载器.exe"

[Run]
Filename: "{app}\YouTube下载器.exe"; Description: "立即运行YouTube下载器"; Flags: nowait postinstall skipifsilent 