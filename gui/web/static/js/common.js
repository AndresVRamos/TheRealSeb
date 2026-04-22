/**
 * Common JS - Utilidades compartidas entre vistas
 * @module common
 */

'use strict';

/**
 * Realiza una petición a la API del servidor
 * @param {string} endpoint - Endpoint de la API (ej: '/api/stats')
 * @param {Object} options - Opciones de fetch
 * @returns {Promise<Object>} - Respuesta JSON
 */
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`Error fetching ${endpoint}:`, error);
        throw error;
    }
}

/**
 * Muestra un toast/notificación (futura implementación)
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo de toast (success, error, warning, info)
 */
function showToast(message, type = 'info') {
    // TODO: Implementar sistema de toasts
    console.log(`[${type.toUpperCase()}] ${message}`);
}

/**
 * Formatea un timestamp a formato legible
 * @param {Date|string|number} date - Fecha a formatear
 * @param {Object} options - Opciones de formato
 * @returns {string} - Fecha formateada
 */
function formatTimestamp(date, options = {}) {
    const defaultOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        ...options
    };

    return new Intl.DateTimeFormat('es-ES', defaultOptions).format(new Date(date));
}

/**
 * Formatea bytes a tamaño legible
 * @param {number} bytes - Cantidad de bytes
 * @param {number} decimals - Decimales a mostrar
 * @returns {string} - Tamaño formateado (ej: "1.5 MB")
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Debounce - Limita la frecuencia de ejecución de una función
 * @param {Function} func - Función a ejecutar
 * @param {number} wait - Milisegundos de espera
 * @returns {Function} - Función debounced
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle - Limita la ejecución de una función a una vez por intervalo
 * @param {Function} func - Función a ejecutar
 * @param {number} limit - Milisegundos de límite
 * @returns {Function} - Función throttled
 */
function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Escapa HTML para prevenir XSS
 * @param {string} text - Texto a escapar
 * @returns {string} - Texto escapado
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Copia texto al portapapeles
 * @param {string} text - Texto a copiar
 * @returns {Promise<boolean>} - true si se copió correctamente
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (error) {
        console.error('Error copiando al portapapeles:', error);
        return false;
    }
}

/**
 * Detecta si el usuario prefiere dark mode
 * @returns {boolean} - true si prefiere dark mode
 */
function prefersDarkMode() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

/**
 * Scroll suave a un elemento
 * @param {HTMLElement|string} element - Elemento o selector
 * @param {Object} options - Opciones de scroll
 */
function smoothScrollTo(element, options = {}) {
    const target = typeof element === 'string' ? document.querySelector(element) : element;
    if (target) {
        target.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
            ...options
        });
    }
}

/**
 * Marca el enlace de navegación activo según la ruta actual
 */
function setActiveNavLink() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        const linkPath = new URL(link.href).pathname;
        if (linkPath === currentPath) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// Inicializar navegación cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setActiveNavLink);
} else {
    setActiveNavLink();
}

// Exportar funciones si se usa como módulo
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        fetchAPI,
        showToast,
        formatTimestamp,
        formatBytes,
        debounce,
        throttle,
        escapeHtml,
        copyToClipboard,
        prefersDarkMode,
        smoothScrollTo,
        setActiveNavLink
    };
}
