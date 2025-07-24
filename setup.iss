; ————————————————————————————
; Instalador Script para Tech RioStore
; Fecha: 17-Jul-2025
; ————————————————————————————

[Setup]
AppName=Tech RioStore
AppVersion=1.0.0
DefaultDirName={commonpf}\Tech RioStore
DefaultGroupName=Tech RioStore
LicenseFile=EULA.txt
InfoBeforeFile=DISCLAIMER.txt
OutputBaseFilename=TechRioStore-Installer
Compression=lzma
SolidCompression=yes
; Detecta el idioma del sistema y carga el correspondiente
LanguageDetectionMethod=locale

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\TechRioStore.exe";        DestDir: "{app}"; Flags: ignoreversion
Source: "resources\*";                  DestDir: "{app}\resources"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Tech RioStore";         Filename: "{app}\TechRioStore.exe"
Name: "{commondesktop}\Tech RioStore"; Filename: "{app}\TechRioStore.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Tareas opcionales:"; Flags: unchecked

[Run]
Filename: "{app}\TechRioStore.exe"; Description: "Iniciar Tech RioStore"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\resources"

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\TechRioStore"
Type: filesandordirs; Name: "{userappdata}\data"
Type: filesandordirs; Name: "{userappdata}\Tech RioStore"
Type: filesandordirs; Name: "{userappdata}\pdf_backups"
