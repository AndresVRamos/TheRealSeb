/**
 * Logs JS - Lógica específica para la vista de logs
 * @requires common.js
 */

'use strict';

// Elementos del DOM
const viewport = document.getElementById('main-viewport');
const logList = document.getElementById('log-list');
const autoscrollCheckbox = document.getElementById('autoscroll');

// Estado
let currentFilter = 'all';
let evtSource = null;

/**
 * Carga los logs iniciales del servidor
 */
async function loadInitialLogs() {
    try {
        const data = await fetchAPI('/api/logs/initial');
        logList.innerHTML = '';
        data.lines.forEach(line => appendLogLine(line));
        scrollToBottom();
        updateStats();
    } catch (error) {
        console.error('Error cargando logs iniciales:', error);
        logList.innerHTML = `<div class="loading" style="color: var(--error);">Error de conexión: ${error.message}</div>`;
    }
}

/**
 * Conecta al stream de logs en tiempo real
 */
function connectToStream() {
    if (evtSource) {
        evtSource.close();
    }

    evtSource = new EventSource('/api/logs/stream');

    evtSource.onmessage = (event) => {
        appendLogLine(event.data);
        if (autoscrollCheckbox.checked) {
            scrollToBottom();
        }
        updateStats();
    };

    evtSource.onerror = (error) => {
        console.error('Error en stream de logs:', error);
        evtSource.close();
        setTimeout(connectToStream, 5000);
    };
}

// Estado para tracking de tracebacks multi-línea
let lastLevel = 'DEBUG';
let inTraceback = false;
let currentErrorBlock = null;  // Referencia al div contenedor del error actual

/**
 * Detecta si una línea es parte de un traceback
 * @param {string} line - Línea a analizar
 * @returns {boolean}
 */
function isTracebackLine(line) {
    const trimmed = line.trim();

    // Patrones comunes de traceback
    return (
        trimmed.startsWith('Traceback') ||
        trimmed.startsWith('File "') ||
        trimmed.startsWith('raise ') ||
        trimmed.startsWith('future:') ||
        line.startsWith('  ') ||  // Indentación de traceback
        line.startsWith('    ') ||
        trimmed.startsWith('^') ||
        trimmed.startsWith('~~~') ||
        trimmed.startsWith('...') ||  // "...<6 lines>..."
        /^[\s]{2,}[a-zA-Z_]/.test(line) ||  // Líneas indentadas con código
        /^[\.\s]{2,}/.test(line) ||  // Líneas con puntos de continuación
        // Líneas de excepción (Error/Exception en cualquier parte)
        /^[A-Z][a-zA-Z]+Error:/.test(trimmed) ||
        /^[A-Z][a-zA-Z]+Exception:/.test(trimmed) ||
        // Excepciones con módulo (socket.gaierror:, aiohttp.ClientError:, etc.)
        /^[a-z_][a-zA-Z0-9_.]*\.[a-zA-Z]+Error/.test(trimmed) ||
        /^[a-z_][a-zA-Z0-9_.]*\.[a-zA-Z]+Exception/.test(trimmed) ||
        /^[a-z_][a-zA-Z0-9_.]*error:/.test(trimmed.toLowerCase()) ||
        // discord.py exceptions
        /^discord\.[a-zA-Z.]+:/.test(trimmed) ||
        // Mensajes de excepción encadenada
        trimmed.startsWith('The above exception') ||
        trimmed.startsWith('During handling')
    );
}

/**
 * Detecta si una línea es la última de un traceback (el mensaje de excepción)
 * @param {string} line - Línea a analizar
 * @returns {boolean}
 */
function isExceptionMessage(line) {
    const trimmed = line.trim();
    return (
        /^[A-Z][a-zA-Z_.]+Error:/.test(trimmed) ||
        /^[A-Z][a-zA-Z_.]+Exception:/.test(trimmed)
    );
}

/**
 * Agrega una línea de log al DOM
 * @param {string} line - Línea de log a agregar
 */
function appendLogLine(line) {
    if (!line) return;

    // Si la línea está vacía pero estamos en traceback, tratarla como parte del traceback
    if (!line.trim() && !inTraceback) return;

    // Detectar nivel de log
    let level = 'DEBUG';
    let isPartOfTraceback = false;

    if (line.includes('ERROR') || line.includes('CRITICAL')) {
        level = 'ERROR';
        inTraceback = true;
        // Cerrar bloque anterior si existe
        currentErrorBlock = null;
    } else if (line.includes('WARNING')) {
        level = 'WARNING';
        inTraceback = false;
        currentErrorBlock = null;
    } else if (line.includes('INFO')) {
        level = 'INFO';
        inTraceback = false;
        currentErrorBlock = null;
    } else if (inTraceback && isTracebackLine(line)) {
        // Esta línea es parte del traceback actual
        level = 'ERROR';
        isPartOfTraceback = true;

        // Si es el mensaje final de excepción, cerrar el traceback
        if (isExceptionMessage(line) && !line.trim().startsWith('The above')) {
            // Verificar si es una excepción encadenada
            // No cerrar si es parte de una cadena de excepciones
        }
    } else {
        // Línea normal - fin del traceback
        inTraceback = false;
        currentErrorBlock = null;
    }

    lastLevel = level;

    // Si es parte de un traceback, agregar al bloque existente
    if (isPartOfTraceback && currentErrorBlock) {
        currentErrorBlock.textContent += '\n' + line;
        return;
    }

    // Crear nuevo div
    const div = document.createElement('div');
    div.className = 'log-line';
    div.dataset.level = level;
    div.textContent = line || ' ';

    // Si es un ERROR, guardarlo como bloque actual para agregar traceback
    if (level === 'ERROR' && !isPartOfTraceback) {
        currentErrorBlock = div;
    }

    // Aplicar filtro actual
    if (currentFilter !== 'all' && level !== currentFilter) {
        div.style.display = 'none';
    }

    logList.appendChild(div);
}

/**
 * Hace scroll al final del viewport
 */
function scrollToBottom() {
    viewport.scrollTo({
        top: viewport.scrollHeight,
        behavior: 'smooth'
    });
}

/**
 * Limpia la vista de logs (no afecta el archivo)
 */
function clearLogs() {
    if (confirm('¿Limpiar la vista actual de logs?\n\nEsto no afectará el archivo en el servidor.')) {
        logList.innerHTML = '';
    }
}

/**
 * Borra el archivo de logs en el servidor
 */
async function clearServerLogs() {
    if (!confirm('⚠️ ¿Borrar permanentemente el archivo de logs en el servidor?\n\nEsta acción NO se puede deshacer.')) {
        return;
    }

    try {
        const data = await fetchAPI('/api/clear');

        if (data.success) {
            logList.innerHTML = '';
            updateStats();
            alert('✅ Archivo de logs limpiado correctamente');
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error limpiando logs del servidor:', error);
        alert(`❌ Error: ${error.message}`);
    }
}

/**
 * Cambia el filtro de nivel de logs
 * @param {string} level - Nivel de log a filtrar ('all', 'ERROR', 'WARNING', 'INFO', 'DEBUG')
 */
function toggleFilter(level) {
    currentFilter = level;

    // Actualizar botones
    document.querySelectorAll('.filter-btn').forEach(btn => {
        const isActive = btn.dataset.level === level;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-pressed', isActive);
    });

    // Mostrar/ocultar líneas
    document.querySelectorAll('.log-line').forEach(line => {
        const shouldShow = level === 'all' || line.dataset.level === level;
        line.style.display = shouldShow ? 'block' : 'none';
    });

    scrollToBottom();
}

/**
 * Actualiza las estadísticas mostradas
 */
async function updateStats() {
    try {
        const data = await fetchAPI('/api/stats');

        document.getElementById('stat-total').textContent = data.total_lines || 0;
        document.getElementById('stat-errors').textContent = data.errors || 0;
        document.getElementById('stat-warnings').textContent = data.warnings || 0;
        document.getElementById('stat-info').textContent = data.info || 0;
        document.getElementById('stat-size').textContent = `${data.file_size_mb || 0} MB`;
    } catch (error) {
        console.error('Error actualizando estadísticas:', error);
    }
}

/**
 * Inicialización de la página
 */
function init() {
    // Event listeners
    autoscrollCheckbox.addEventListener('change', (e) => {
        e.target.setAttribute('aria-checked', e.target.checked);
    });

    // Cargar datos iniciales
    loadInitialLogs();
    connectToStream();

    // Actualizar stats cada 30 segundos
    setInterval(updateStats, 30000);

    // Cleanup al cerrar
    window.addEventListener('beforeunload', () => {
        if (evtSource) {
            evtSource.close();
        }
    });
}

// Iniciar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
