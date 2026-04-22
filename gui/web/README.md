# Web Dashboard

Dashboard web para monitoreo y administración remota del bot Discord Music Maniac.

## Estructura

```
gui/web/
├── dashboard.py       # Servidor Flask
├── views/            # Vistas HTML (Jinja2)
│   ├── base.html     # Template base
│   └── logs.html     # Vista de logs
└── static/           # Archivos estáticos
    ├── css/
    │   ├── base.css  # Estilos compartidos
    │   └── logs.css  # Estilos específicos de logs
    └── js/
        ├── common.js # Utilidades compartidas
        └── logs.js   # Lógica específica de logs
```

## Uso

### Iniciar el servidor

```bash
python gui/web/dashboard.py
```

### Acceso

- **Local**: http://localhost:5000
- **Remoto**: http://<IP_PUBLICA>:5000

### Endpoints disponibles

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Dashboard de logs |
| `/api/logs/initial` | GET | Últimas 1000 líneas de logs |
| `/api/logs/stream` | GET | Stream en tiempo real (SSE) |
| `/api/stats` | GET | Estadísticas del archivo de logs |
| `/api/clear` | GET | Limpia el archivo de logs |
| `/health` | GET | Health check |

## Características

- **Logs en tiempo real**: Streaming mediante Server-Sent Events (SSE)
- **Filtros por nivel**: ERROR, WARNING, INFO, DEBUG
- **Auto-scroll**: Opción para seguir automáticamente nuevos logs
- **Estadísticas**: Total de líneas, errores, warnings, tamaño del archivo
- **Diseño Apple-style**: Glassmorphism, dark/light mode automático
- **Responsive**: Optimizado para desktop y móvil

## Arquitectura

### Views (Jinja2)

Las vistas extienden `base.html` usando bloques:

```html
{% extends "base.html" %}
{% block title %}Título{% endblock %}
{% block styles %}<!-- CSS específico -->{% endblock %}
{% block header %}<!-- Header personalizado -->{% endblock %}
{% block content %}<!-- Contenido principal -->{% endblock %}
{% block scripts %}<!-- JavaScript específico -->{% endblock %}
```

### CSS

- **base.css**: Variables CSS, componentes compartidos, glassmorphism
- **{view}.css**: Estilos específicos de cada vista

### JavaScript

- **common.js**: Funciones reutilizables (fetchAPI, formatters, etc.)
- **{view}.js**: Lógica específica de cada vista

## Agregar nuevas vistas

Usa el skill `/new-view` para crear automáticamente una nueva vista:

```bash
/new-view metrics --include-css=true --include-js=true --description="Dashboard de métricas"
```

Esto crea:
- `views/metrics.html`
- `static/css/metrics.css`
- `static/js/metrics.js`
- Actualiza `dashboard.py` con la nueva ruta

## Seguridad

Para producción, configura:

1. **SSH con clave pública** (deshabilitar password auth)
2. **Puerto no estándar** para SSH
3. **Firewall** (solo puertos necesarios)
4. **Cloudflare Tunnel** (opcional, para HTTPS)
5. **Rate limiting** en Flask
6. **Autenticación** para endpoints sensibles

Ver documentación completa en el archivo raíz del proyecto.
