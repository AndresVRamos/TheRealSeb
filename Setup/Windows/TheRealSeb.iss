; ============================================================
;   THE REAL SEB - Script de Inno Setup 6.x
;   Para compilar: https://jrsoftware.org/isinfo.php
; ============================================================

#define MyAppName      "The Real Seb"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "AndresVRamos"
#define MyAppURL       "https://github.com/AndresVRamos/TheRealSeb"

[Setup]
AppId={{8F4A2B1C-3D5E-4F6A-B7C8-9D0E1F2A3B4C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

DefaultDirName=C:\TheRealSeb
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

OutputDir=..\..\dist
OutputBaseFilename=TheRealSeb-Setup-{#MyAppVersion}

SetupIconFile=icon.ico
UninstallDisplayIcon={app}\icon.ico

Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no

PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "startup";   Description: "Iniciar {#MyAppName} automáticamente con Windows"; GroupDescription: "Opciones adicionales:"; Flags: unchecked
Name: "launchbot"; Description: "Iniciar el bot al finalizar la instalación";        GroupDescription: "Opciones adicionales:"; Flags: unchecked

[Files]
Source: "icon.ico";                DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\maniac.py";         DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\main.pyw";          DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\requirements.txt";  DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\*.example";         DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\commands\*";        DestDir: "{app}\commands"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\core\*";            DestDir: "{app}\core";     Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\gui\*";             DestDir: "{app}\gui";      Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\views\*";           DestDir: "{app}\views";    Flags: ignoreversion recursesubdirs createallsubdirs
Source: "start.bat";               DestDir: "{app}\Setup\Windows"; Flags: ignoreversion
Source: "add-to-startup.bat";      DestDir: "{app}\Setup\Windows"; Flags: ignoreversion
Source: "remove-from-startup.bat"; DestDir: "{app}\Setup\Windows"; Flags: ignoreversion

[Icons]
Name: "{group}\Iniciar {#MyAppName}";          Filename: "{app}\Setup\Windows\start.bat";               IconFilename: "{app}\icon.ico"; WorkingDir: "{app}"
Name: "{group}\Agregar al inicio de Windows";  Filename: "{app}\Setup\Windows\add-to-startup.bat";      IconFilename: "{app}\icon.ico"; WorkingDir: "{app}"
Name: "{group}\Remover del inicio de Windows"; Filename: "{app}\Setup\Windows\remove-from-startup.bat"; IconFilename: "{app}\icon.ico"; WorkingDir: "{app}"
Name: "{group}\Configuración (.env)";          Filename: "{app}\.env";                                  WorkingDir: "{app}"
Name: "{group}\Desinstalar {#MyAppName}";      Filename: "{uninstallexe}";                              IconFilename: "{app}\icon.ico"

[Run]
Filename: "cmd.exe"; \
    Parameters: "/c python -m pip install -r ""{app}\requirements.txt"" --quiet"; \
    StatusMsg: "Instalando dependencias de Python (puede tardar 1-2 minutos)..."; \
    Flags: runhidden waituntilterminated

[UninstallRun]
RunOnceId: "removestartup"; Filename: "{app}\Setup\Windows\remove-from-startup.bat"; Parameters: "/silent"; Flags: runhidden waituntilterminated

; ============================================================
;  PASCAL SCRIPT
; ============================================================
[Code]

var
  PrereqPage:   TWizardPage;
  PyStatusLbl:  TLabel;
  FfStatusLbl:  TLabel;
  PyBtn:        TNewButton;
  FfBtn:        TNewButton;
  RefreshBtn:   TNewButton;

  // Pagina de configuracion de tokens
  ConfigPage:          TWizardPage;
  DiscordTokenEdit:    TNewEdit;
  SpotifyIdEdit:       TNewEdit;
  SpotifySecretEdit:   TNewEdit;
  GeniusKeyEdit:       TNewEdit;
  ConfigPageInitialized: Boolean;

// ------------------------------------------------------------------
//  Detección de dependencias
// ------------------------------------------------------------------

function IsPythonInstalled(): Boolean;
var
  RegPath: String;
  Code: Integer;
begin
  // Buscar en el registro primero (funciona sin reiniciar tras winget)
  Result :=
    RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.12\InstallPath', '', RegPath) or
    RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.12\InstallPath', '', RegPath) or
    RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.11\InstallPath', '', RegPath) or
    RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.11\InstallPath', '', RegPath) or
    RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.10\InstallPath', '', RegPath) or
    RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.10\InstallPath', '', RegPath) or
    RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.9\InstallPath',  '', RegPath) or
    RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.9\InstallPath',  '', RegPath) or
    RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.8\InstallPath',  '', RegPath) or
    RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.8\InstallPath',  '', RegPath);
  // Fallback: intentar correr python
  if not Result then
    Result := Exec('cmd.exe', '/c python --version', '', SW_HIDE, ewWaitUntilTerminated, Code)
              and (Code = 0);
end;

function IsFFmpegInstalled(): Boolean;
var
  Code: Integer;
begin
  // Ruta típica de winget Gyan.FFmpeg
  if FileExists('C:\Program Files\FFmpeg\bin\ffmpeg.exe') then
  begin
    Result := True;
    Exit;
  end;
  // Fallback: intentar correr ffmpeg
  Result := Exec('cmd.exe', '/c ffmpeg -version', '', SW_HIDE, ewWaitUntilTerminated, Code)
            and (Code = 0);
end;

// ------------------------------------------------------------------
//  Actualizar estado visual de la página de requisitos
// ------------------------------------------------------------------

procedure UpdateStatus();
var
  PyOk, FfOk: Boolean;
begin
  PyOk := IsPythonInstalled();
  FfOk := IsFFmpegInstalled();

  if PyOk then
  begin
    PyStatusLbl.Caption    := '✓  Instalado';
    PyStatusLbl.Font.Color := clGreen;
    PyBtn.Caption          := 'Ya instalado';
    PyBtn.Enabled          := False;
  end
  else
  begin
    PyStatusLbl.Caption    := '✗  No encontrado';
    PyStatusLbl.Font.Color := clRed;
    PyBtn.Caption          := 'Instalar con winget';
    PyBtn.Enabled          := True;
  end;

  if FfOk then
  begin
    FfStatusLbl.Caption    := '✓  Instalado';
    FfStatusLbl.Font.Color := clGreen;
    FfBtn.Caption          := 'Ya instalado';
    FfBtn.Enabled          := False;
  end
  else
  begin
    FfStatusLbl.Caption    := '✗  No encontrado';
    FfStatusLbl.Font.Color := clRed;
    FfBtn.Caption          := 'Instalar con winget';
    FfBtn.Enabled          := True;
  end;

  // Bloquear "Siguiente" si Python no está instalado
  WizardForm.NextButton.Enabled := PyOk;
end;

// ------------------------------------------------------------------
//  Handlers de botones de instalación
// ------------------------------------------------------------------

procedure PyBtnClick(Sender: TObject);
var
  Code: Integer;
begin
  MsgBox(
    'Se abrirá una ventana de terminal para instalar Python.' + #13#10 +
    'Esperá a que termine y cerrá la ventana.' + #13#10 +
    'Después hacé click en "Verificar de nuevo".',
    mbInformation, MB_OK
  );
  Exec('cmd.exe',
    '/k winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements',
    '', SW_SHOW, ewWaitUntilTerminated, Code);
  UpdateStatus();
end;

procedure FfBtnClick(Sender: TObject);
var
  Code: Integer;
begin
  MsgBox(
    'Se abrirá una ventana de terminal para instalar FFmpeg.' + #13#10 +
    'Esperá a que termine y cerrá la ventana.' + #13#10 +
    'Después hacé click en "Verificar de nuevo".' + #13#10 + #13#10 +
    'Nota: puede ser necesario reiniciar Windows para que FFmpeg quede en el PATH.',
    mbInformation, MB_OK
  );
  Exec('cmd.exe',
    '/k winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements',
    '', SW_SHOW, ewWaitUntilTerminated, Code);
  UpdateStatus();
end;

procedure RefreshBtnClick(Sender: TObject);
begin
  UpdateStatus();
end;

// ------------------------------------------------------------------
//  Leer valor de una variable del archivo .env existente
// ------------------------------------------------------------------

function ReadEnvValue(EnvFile, VarName: String): String;
var
  Lines: TArrayOfString;
  i: Integer;
  Line, Prefix: String;
begin
  Result := '';
  if not FileExists(EnvFile) then Exit;

  if LoadStringsFromFile(EnvFile, Lines) then
  begin
    Prefix := VarName + '=';
    for i := 0 to GetArrayLength(Lines) - 1 do
    begin
      Line := Trim(Lines[i]);
      // Ignorar comentarios y lineas vacias
      if (Length(Line) > 0) and (Line[1] <> '#') then
      begin
        if Pos(Prefix, Line) = 1 then
        begin
          Result := Copy(Line, Length(Prefix) + 1, Length(Line));
          // No devolver placeholders
          if (Pos('YOUR_', Result) = 1) or (Pos('_HERE', Result) > 0) then
            Result := '';
          Exit;
        end;
      end;
    end;
  end;
end;

// ------------------------------------------------------------------
//  Crear página de configuración de tokens
// ------------------------------------------------------------------

procedure CreateConfigPage();
var
  Lbl: TLabel;
  y: Integer;
begin
  // Crear despues de wpSelectDir para que {app} este disponible
  ConfigPage := CreateCustomPage(
    wpSelectDir,
    'Configuración de credenciales',
    'Ingresá tus tokens y claves de API. Solo el Token de Discord es obligatorio.'
  );

  y := 8;

  // ---- Discord Token ----
  Lbl := TLabel.Create(ConfigPage);
  Lbl.Parent := ConfigPage.Surface;
  Lbl.Caption := 'Token de Discord (OBLIGATORIO)';
  Lbl.Font.Style := [fsBold];
  Lbl.SetBounds(0, y, 417, 18);

  y := y + 18;
  Lbl := TLabel.Create(ConfigPage);
  Lbl.Parent := ConfigPage.Surface;
  Lbl.Caption := 'discord.com/developers/applications > Bot > Reset Token';
  Lbl.Font.Color := $606060;
  Lbl.SetBounds(0, y, 417, 16);

  y := y + 20;
  DiscordTokenEdit := TNewEdit.Create(ConfigPage);
  DiscordTokenEdit.Parent := ConfigPage.Surface;
  DiscordTokenEdit.SetBounds(0, y, 417, 23);

  y := y + 32;

  // ---- Spotify ----
  Lbl := TLabel.Create(ConfigPage);
  Lbl.Parent := ConfigPage.Surface;
  Lbl.Caption := 'Spotify (opcional - para links de Spotify)';
  Lbl.Font.Style := [fsBold];
  Lbl.SetBounds(0, y, 417, 18);

  y := y + 18;
  Lbl := TLabel.Create(ConfigPage);
  Lbl.Parent := ConfigPage.Surface;
  Lbl.Caption := 'developer.spotify.com/dashboard';
  Lbl.Font.Color := $606060;
  Lbl.SetBounds(0, y, 417, 16);

  y := y + 20;
  Lbl := TLabel.Create(ConfigPage);
  Lbl.Parent := ConfigPage.Surface;
  Lbl.Caption := 'Client ID:';
  Lbl.SetBounds(0, y + 3, 60, 18);

  SpotifyIdEdit := TNewEdit.Create(ConfigPage);
  SpotifyIdEdit.Parent := ConfigPage.Surface;
  SpotifyIdEdit.SetBounds(65, y, 352, 23);

  y := y + 28;
  Lbl := TLabel.Create(ConfigPage);
  Lbl.Parent := ConfigPage.Surface;
  Lbl.Caption := 'Secret:';
  Lbl.SetBounds(0, y + 3, 60, 18);

  SpotifySecretEdit := TNewEdit.Create(ConfigPage);
  SpotifySecretEdit.Parent := ConfigPage.Surface;
  SpotifySecretEdit.SetBounds(65, y, 352, 23);

  y := y + 32;

  // ---- Genius ----
  Lbl := TLabel.Create(ConfigPage);
  Lbl.Parent := ConfigPage.Surface;
  Lbl.Caption := 'Genius API Key (opcional - para letras)';
  Lbl.Font.Style := [fsBold];
  Lbl.SetBounds(0, y, 417, 18);

  y := y + 18;
  Lbl := TLabel.Create(ConfigPage);
  Lbl.Parent := ConfigPage.Surface;
  Lbl.Caption := 'genius.com/api-clients';
  Lbl.Font.Color := $606060;
  Lbl.SetBounds(0, y, 417, 16);

  y := y + 20;
  GeniusKeyEdit := TNewEdit.Create(ConfigPage);
  GeniusKeyEdit.Parent := ConfigPage.Surface;
  GeniusKeyEdit.SetBounds(0, y, 417, 23);

  y := y + 32;

  // ---- Nota ----
  Lbl := TLabel.Create(ConfigPage);
  Lbl.Parent := ConfigPage.Surface;
  Lbl.Caption := 'Podes modificar estos valores en el archivo .env';
  Lbl.Font.Color := $606060;
  Lbl.SetBounds(0, y, 417, 18);
end;

// ------------------------------------------------------------------
//  Crear página personalizada de requisitos previos
// ------------------------------------------------------------------

procedure CreatePrereqPage();
var
  Lbl:  TLabel;
  Sep:  TBevel;
  y:    Integer;
begin
  PrereqPage := CreateCustomPage(
    wpWelcome,
    'Requisitos previos',
    'Verificá que los componentes necesarios estén instalados antes de continuar.'
  );

  y := 8;

  // ---- Python ----
  Lbl := TLabel.Create(PrereqPage);
  Lbl.Parent := PrereqPage.Surface;
  Lbl.Caption := 'Python 3.8+  —  Obligatorio';
  Lbl.Font.Style := [fsBold];
  Lbl.SetBounds(0, y, 280, 18);

  PyStatusLbl := TLabel.Create(PrereqPage);
  PyStatusLbl.Parent := PrereqPage.Surface;
  PyStatusLbl.Caption := 'Verificando...';
  PyStatusLbl.Font.Style := [fsBold];
  PyStatusLbl.SetBounds(295, y, 180, 18);

  y := y + 22;
  Lbl := TLabel.Create(PrereqPage);
  Lbl.Parent := PrereqPage.Surface;
  Lbl.Caption := 'Necesario para ejecutar el bot. Instalalo con "Add Python to PATH" activado.';
  Lbl.SetBounds(0, y, PrereqPage.SurfaceWidth, 18);

  y := y + 26;
  PyBtn := TNewButton.Create(PrereqPage);
  PyBtn.Parent := PrereqPage.Surface;
  PyBtn.Caption := 'Instalar con winget';
  PyBtn.SetBounds(0, y, 170, 26);
  PyBtn.OnClick := @PyBtnClick;

  y := y + 42;

  // Separador
  Sep := TBevel.Create(PrereqPage);
  Sep.Parent := PrereqPage.Surface;
  Sep.Style := bsLowered;
  Sep.SetBounds(0, y, PrereqPage.SurfaceWidth, 2);

  y := y + 12;

  // ---- FFmpeg ----
  Lbl := TLabel.Create(PrereqPage);
  Lbl.Parent := PrereqPage.Surface;
  Lbl.Caption := 'FFmpeg  —  Necesario para audio';
  Lbl.Font.Style := [fsBold];
  Lbl.SetBounds(0, y, 280, 18);

  FfStatusLbl := TLabel.Create(PrereqPage);
  FfStatusLbl.Parent := PrereqPage.Surface;
  FfStatusLbl.Caption := 'Verificando...';
  FfStatusLbl.Font.Style := [fsBold];
  FfStatusLbl.SetBounds(295, y, 180, 18);

  y := y + 22;
  Lbl := TLabel.Create(PrereqPage);
  Lbl.Parent := PrereqPage.Surface;
  Lbl.Caption := 'Sin FFmpeg el bot no reproducirá audio. Reiniciá Windows después de instalarlo.';
  Lbl.SetBounds(0, y, PrereqPage.SurfaceWidth, 18);

  y := y + 26;
  FfBtn := TNewButton.Create(PrereqPage);
  FfBtn.Parent := PrereqPage.Surface;
  FfBtn.Caption := 'Instalar con winget';
  FfBtn.SetBounds(0, y, 170, 26);
  FfBtn.OnClick := @FfBtnClick;

  y := y + 46;

  // ---- Botón verificar ----
  RefreshBtn := TNewButton.Create(PrereqPage);
  RefreshBtn.Parent := PrereqPage.Surface;
  RefreshBtn.Caption := 'Verificar de nuevo';
  RefreshBtn.SetBounds(0, y, 170, 26);
  RefreshBtn.OnClick := @RefreshBtnClick;

  y := y + 34;

  Lbl := TLabel.Create(PrereqPage);
  Lbl.Parent := PrereqPage.Surface;
  Lbl.Caption := 'Después de instalar algo, hacé click en "Verificar de nuevo" para actualizar el estado.';
  Lbl.Font.Color := $606060;
  Lbl.SetBounds(0, y, PrereqPage.SurfaceWidth, 18);
end;

// ------------------------------------------------------------------
//  Eventos del wizard
// ------------------------------------------------------------------

procedure InitializeWizard();
begin
  ConfigPageInitialized := False;
  CreatePrereqPage();
  CreateConfigPage();
end;

procedure CurPageChanged(CurPageID: Integer);
var
  EnvFile: String;
begin
  if CurPageID = PrereqPage.ID then
    UpdateStatus()
  else if CurPageID = ConfigPage.ID then
  begin
    // Pre-llenar con valores existentes si hay un .env previo (solo la primera vez)
    if not ConfigPageInitialized then
    begin
      ConfigPageInitialized := True;
      EnvFile := ExpandConstant('{app}\.env');
      if FileExists(EnvFile) then
      begin
        DiscordTokenEdit.Text := ReadEnvValue(EnvFile, 'discord_token');
        SpotifyIdEdit.Text := ReadEnvValue(EnvFile, 'SPOTIPY_CLIENT_ID');
        SpotifySecretEdit.Text := ReadEnvValue(EnvFile, 'SPOTIPY_CLIENT_SECRET');
        GeniusKeyEdit.Text := ReadEnvValue(EnvFile, 'GENIUS_API_KEY');
      end;
    end;
    WizardForm.NextButton.Enabled := True;
  end
  else
    WizardForm.NextButton.Enabled := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ConfigPage.ID then
  begin
    if Trim(DiscordTokenEdit.Text) = '' then
    begin
      MsgBox('El Token de Discord es obligatorio para que el bot funcione.' + #13#10 +
             'Por favor ingresá tu token antes de continuar.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvFile: String;
  EnvContent: String;
  Code: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    EnvFile := ExpandConstant('{app}\.env');

    // En modo silencioso (actualizacion), preservar el .env existente
    // Solo generar nuevo .env si no existe o si es instalacion interactiva
    if not WizardSilent then
    begin
      // Generar contenido del .env con los valores ingresados
      EnvContent :=
        '# ============================================================================' + #13#10 +
        '#                    THE REAL SEB - CONFIGURACION' + #13#10 +
        '# ============================================================================' + #13#10 +
        '# Generado automaticamente por el instalador' + #13#10 +
        '# Podes editar este archivo manualmente si necesitas cambiar los valores' + #13#10 +
        '# ============================================================================' + #13#10 + #13#10 +
        '# Discord Bot Token (OBLIGATORIO)' + #13#10 +
        'discord_token=' + DiscordTokenEdit.Text + #13#10 + #13#10 +
        '# Spotify API (opcional)' + #13#10 +
        'SPOTIPY_CLIENT_ID=' + SpotifyIdEdit.Text + #13#10 +
        'SPOTIPY_CLIENT_SECRET=' + SpotifySecretEdit.Text + #13#10 + #13#10 +
        '# Genius API (opcional)' + #13#10 +
        'GENIUS_API_KEY=' + GeniusKeyEdit.Text + #13#10;

      // Guardar el archivo .env
      SaveStringToFile(EnvFile, EnvContent, False);
    end;

    if WizardIsTaskSelected('startup') then
      Exec(ExpandConstant('{app}\Setup\Windows\add-to-startup.bat'), '',
           ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, Code);

    if WizardIsTaskSelected('launchbot') then
    begin
      // En modo silencioso usar SW_HIDE, en interactivo SW_SHOW
      if WizardSilent then
        Exec(ExpandConstant('{app}\Setup\Windows\start.bat'), '',
             ExpandConstant('{app}'), SW_HIDE, ewNoWait, Code)
      else
        Exec(ExpandConstant('{app}\Setup\Windows\start.bat'), '',
             ExpandConstant('{app}'), SW_SHOW, ewNoWait, Code);
    end;
  end;
end;
