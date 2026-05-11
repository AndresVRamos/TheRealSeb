# 🌐 Log Server - Monitoreo Remoto del Bot

Sistema de visualización de logs en tiempo real vía web para monitoreo remoto del bot The Real Seb.

## 📋 Características

- ✅ **Logs en tiempo real** con Server-Sent Events (SSE)
- ✅ **Interfaz web moderna** con diseño oscuro estilo GitHub
- ✅ **Filtros por nivel** (ERROR, WARNING, INFO, DEBUG)
- ✅ **Estadísticas en vivo** (total de líneas, errores, warnings, tamaño de archivo)
- ✅ **Auto-scroll configurable**
- ✅ **Limpieza de logs** (vista y archivo)
- ✅ **Accesible desde cualquier dispositivo** (PC, móvil, tablet)

## 🚀 Inicio Rápido

### 1. Instalación de Dependencias

```bash
pip install -r requirements.txt
```

Esto instalará Flask y todas las dependencias necesarias.

### 2. Ejecutar el Servidor

```bash
python log_server.py
```

Verás algo como:

```
============================================================
🎵 The Real Seb - Log Server
============================================================
📁 Archivo de logs: C:\path\to\data\bot.log
🌐 Servidor local: http://localhost:5000
🌐 Acceso remoto: http://<IP_PUBLICA>:5000
============================================================

Presiona Ctrl+C para detener el servidor
```

### 3. Acceder a los Logs

- **Localmente**: Abre `http://localhost:5000` en tu navegador
- **Remotamente**: Usa `http://<IP_PUBLICA>:5000` desde cualquier dispositivo

---

## 🖥️ Configuración para Hosting Remoto

### Configuración en Windows Server (Servidor del Amigo)

#### 1. Usuario No-Administrador

El amigo debe crear un usuario estándar para ti:

```powershell
# PowerShell como Administrador
New-LocalUser -Name "tu_nombre" -Description "Usuario para bot Discord" -PasswordNeverExpires
# Establecer contraseña cuando se solicite

# Agregar a grupo de acceso remoto
Add-LocalGroupMember -Group "Remote Desktop Users" -Member "tu_nombre"
```

#### 2. Activar OpenSSH Server

```powershell
# Instalar OpenSSH Server
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Iniciar servicio
Start-Service sshd

# Configurar inicio automático
Set-Service -Name sshd -StartupType 'Automatic'

# Verificar que está corriendo
Get-Service sshd
```

#### 3. Configurar Firewall en Windows

```powershell
# Permitir SSH (puerto 22)
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22

# Permitir Log Server (puerto 5000)
New-NetFirewallRule -Name flask_logs -DisplayName 'The Real Seb Log Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 5000
```

#### 4. Port Forwarding en Router

El amigo debe acceder a la configuración del router (generalmente `192.168.1.1` o `192.168.0.1`):

1. **IP Estática Local**:
   - Asignar IP fija al servidor (ej: `192.168.1.100`)

2. **Port Forwarding**:
   - **Puerto 22** (SSH) → IP local del servidor
   - **Puerto 5000** (Log Server) → IP local del servidor

3. **Obtener IP Pública**:
   - Visitar https://www.whatismyip.com/
   - O ejecutar: `curl ifconfig.me`

### Desde tu Computadora (Cliente)

#### 1. Conectar por SSH

```bash
# Primera conexión
ssh tu_nombre@<IP_PUBLICA_AMIGO>

# Si el amigo cambió el puerto SSH (recomendado para seguridad)
ssh -p 2222 tu_nombre@<IP_PUBLICA_AMIGO>
```

#### 2. Autenticación con Clave SSH (Más Seguro)

```bash
# Generar clave SSH (en tu PC)
ssh-keygen -t ed25519 -C "tu_email@example.com"

# Copiar clave al servidor
ssh-copy-id tu_nombre@<IP_PUBLICA_AMIGO>

# Ahora puedes conectar sin contraseña
ssh tu_nombre@<IP_PUBLICA_AMIGO>
```

#### 3. Workflow de Actualización

```bash
# 1. Conectar al servidor
ssh tu_nombre@<IP_SERVIDOR>

# 2. Navegar al directorio del bot
cd "C:\Users\tu_nombre\music-bot"

# 3. Actualizar código
git pull origin main

# 4. Instalar nuevas dependencias (si hay)
pip install -r requirements.txt --user

# 5. Reiniciar el bot (depende de cómo esté configurado)
# Ver sección "Mantener el Bot Corriendo"
```

---

## 🔄 Mantener el Bot Corriendo (Sin cerrar SSH)

### Opción 1: Task Scheduler de Windows (Recomendado)

El amigo configura una tarea programada que ejecuta el bot al iniciar Windows:

1. Abrir **Task Scheduler** (`taskschd.msc`)
2. Crear tarea básica:
   - Nombre: "The Real Seb Bot"
   - Trigger: Al iniciar el sistema
   - Acción: Iniciar programa
     - Programa: `python`
     - Argumentos: `C:\path\to\maniac.py`
     - Directorio: `C:\path\to\bot`
3. Configuración adicional:
   - ✅ Ejecutar con los privilegios más altos
   - ✅ Ejecutar aunque el usuario no haya iniciado sesión

### Opción 2: NSSM (Non-Sucking Service Manager)

```powershell
# Descargar NSSM desde https://nssm.cc/download
# Instalar como servicio
nssm install TheRealSebBot "C:\Python\python.exe" "C:\path\to\maniac.py"
nssm start TheRealSebBot

# Ver logs del servicio
nssm set TheRealSebBot AppStdout "C:\path\to\logs\stdout.log"
nssm set TheRealSebBot AppStderr "C:\path\to\logs\stderr.log"
```

### Opción 3: PM2 (Requiere Node.js)

```bash
# Instalar PM2
npm install -g pm2

# Iniciar bot
pm2 start maniac.py --interpreter python --name the-real-seb

# Guardar configuración
pm2 save

# Iniciar PM2 al arrancar Windows
pm2 startup
```

---

## 📊 Endpoints de la API

### `GET /`
Página principal con interfaz de logs.

### `GET /api/logs/initial`
Obtiene las últimas 1000 líneas del archivo de logs.

**Respuesta**:
```json
{
  "lines": ["2024-01-20 10:30:45 - INFO - Bot iniciado", ...],
  "total": 5420
}
```

### `GET /api/logs/stream`
Stream de logs en tiempo real (Server-Sent Events).

### `GET /api/stats`
Estadísticas del archivo de logs.

**Respuesta**:
```json
{
  "file_size": 2048576,
  "file_size_mb": 1.95,
  "total_lines": 5420,
  "errors": 12,
  "warnings": 45,
  "info": 5363,
  "last_modified": "2024-01-20T10:35:22"
}
```

### `GET /api/clear`
Limpia el archivo de logs en el servidor.

### `GET /health`
Health check del servidor.

---

## 🔒 Seguridad

### Recomendaciones

1. **Cambiar puerto SSH del 22 al 2222+**:
   ```powershell
   # Editar C:\ProgramData\ssh\sshd_config
   Port 2222

   # Reiniciar servicio
   Restart-Service sshd
   ```

2. **Deshabilitar autenticación por contraseña** (solo claves SSH):
   ```powershell
   # En sshd_config
   PasswordAuthentication no
   PubkeyAuthentication yes
   ```

3. **Instalar IPBan** (fail2ban para Windows):
   - Descarga: https://github.com/DigitalRuby/IPBan
   - Bloquea IPs después de X intentos fallidos

4. **Usar HTTPS** (con certificado SSL):
   - Para producción, usar nginx + Let's Encrypt
   - O usar Cloudflare Tunnel (gratis)

5. **Firewall restrictivo**:
   - Solo abrir puertos SSH y Log Server
   - Whitelist de IPs si es posible

### Acceso con Cloudflare Tunnel (Sin exponer IP)

**Ventajas**:
- ✅ No necesitas port forwarding
- ✅ No expones tu IP pública
- ✅ HTTPS automático
- ✅ Gratis

**Instalación**:
```bash
# Descargar cloudflared
# Windows: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

# Autenticar
cloudflared tunnel login

# Crear túnel
cloudflared tunnel create music-logs

# Configurar
cloudflared tunnel route dns music-logs logs.tudominio.com

# Correr túnel
cloudflared tunnel --url http://localhost:5000 run music-logs
```

Ahora accedes con: `https://logs.tudominio.com`

---

## 🛠️ Troubleshooting

### Problema: No puedo conectar por SSH

**Solución**:
1. Verificar que el servicio SSH esté corriendo:
   ```powershell
   Get-Service sshd
   ```
2. Verificar firewall de Windows
3. Verificar port forwarding en el router
4. Ping a la IP pública para verificar conectividad

### Problema: Los logs no se actualizan en tiempo real

**Solución**:
1. Verificar que el bot esté escribiendo a `data/bot.log`
2. Revisar la consola de JavaScript (F12 en el navegador)
3. Verificar que el EventSource esté conectado

### Problema: El servidor Flask no arranca

**Solución**:
```bash
# Verificar que Flask esté instalado
pip list | findstr Flask

# Reinstalar si es necesario
pip install flask --upgrade

# Verificar que el puerto 5000 no esté en uso
netstat -ano | findstr :5000
```

### Problema: "Permission Denied" al hacer git pull

**Solución**:
1. Verificar que tu usuario tenga permisos en la carpeta:
   ```powershell
   icacls "C:\path\to\bot" /grant tu_nombre:(OI)(CI)F /T
   ```
2. Configurar Git con tus credenciales:
   ```bash
   git config --global user.name "Tu Nombre"
   git config --global user.email "tu@email.com"
   ```

---

## 📝 Alternativas al Log Server Flask

### 1. Discord Webhook (Más Simple)

Solo enviar errores críticos a un canal de Discord:

```python
# En maniac.py
import requests

WEBHOOK_URL = "https://discord.com/api/webhooks/..."

class DiscordHandler(logging.Handler):
    def emit(self, record):
        if record.levelname in ['ERROR', 'CRITICAL']:
            payload = {
                "content": f"🚨 **{record.levelname}**\n```{record.getMessage()[:1900]}```"
            }
            requests.post(WEBHOOK_URL, json=payload)

# Agregar al logger
discord_handler = DiscordHandler()
logging.getLogger().addHandler(discord_handler)
```

### 2. Servicios de Logging en la Nube

- **Logtail** (gratis hasta 1GB/mes): https://betterstack.com/logtail
- **Papertrail** (gratis hasta 50MB/mes): https://papertrailapp.com/
- **Grafana Cloud** (free tier): https://grafana.com/products/cloud/

### 3. Tail vía SSH

Simplemente leer los logs remotamente:

```bash
ssh tu_usuario@IP_SERVIDOR "tail -f C:\Users\tu_nombre\music-bot\data\bot.log"
```

---

## 🎯 Resumen del Workflow

1. **Desarrollo Local**:
   - Escribes código en tu PC
   - Pruebas localmente
   - Push a GitHub: `git push origin main`

2. **Actualización Remota**:
   - SSH al servidor: `ssh tu_usuario@IP_SERVIDOR`
   - Pull cambios: `cd music-bot && git pull`
   - (Opcional) Reiniciar bot si es necesario

3. **Monitoreo**:
   - Abrir navegador: `http://IP_SERVIDOR:5000`
   - Ver logs en tiempo real
   - Filtrar por nivel de log (ERROR, WARNING, etc.)

4. **Solución de Problemas**:
   - Revisar logs en el dashboard
   - SSH al servidor si es necesario
   - Investigar/parchear problema
   - Push fix → Pull en servidor

---

## 📞 Contacto y Soporte

Si tienes problemas con la configuración, revisa primero:
1. Firewall de Windows (puertos 22 y 5000 abiertos)
2. Port forwarding en el router
3. Servicio SSH corriendo: `Get-Service sshd`
4. Logs del servidor Flask en la consola

Para más ayuda, consulta:
- Documentación de OpenSSH: https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse
- Flask documentation: https://flask.palletsprojects.com/
- Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
