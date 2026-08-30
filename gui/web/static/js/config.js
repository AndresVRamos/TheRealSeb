/**
 * Config JS - Logica para la vista de configuracion
 */

'use strict';

// Estado de la configuracion
let originalConfig = {};
let currentConfig = {};
let hasChanges = false;

// Elementos del DOM
const sectionsContainer = document.getElementById('config-sections');
const changesIndicator = document.getElementById('changes-indicator');
const btnCancel = document.getElementById('btn-cancel');
const btnSave = document.getElementById('btn-save');
const btnSaveRestart = document.getElementById('btn-save-restart');
const restartModal = document.getElementById('restart-modal');

/**
 * Carga la configuracion desde la API
 */
async function loadConfig() {
    try {
        const response = await fetchAPI('/api/config');
        if (response.success) {
            originalConfig = JSON.parse(JSON.stringify(response.config));
            currentConfig = JSON.parse(JSON.stringify(response.config));
            renderSections(currentConfig);
        } else {
            showError('Error al cargar configuracion: ' + response.error);
        }
    } catch (error) {
        showError('Error de conexion: ' + error.message);
    }
}

/**
 * Renderiza todas las secciones
 */
function renderSections(config) {
    sectionsContainer.innerHTML = '';

    for (const [sectionName, sectionData] of Object.entries(config)) {
        const section = createSectionElement(sectionName, sectionData);
        sectionsContainer.appendChild(section);
    }
}

/**
 * Crea el elemento HTML de una seccion
 */
function createSectionElement(name, data) {
    const section = document.createElement('section');
    section.className = 'config-section';

    const sectionId = name.replace(/[^a-zA-Z0-9]/g, '_');

    section.innerHTML = `
        <div class="section-header" data-section="${escapeHtml(sectionId)}">
            <h2 class="section-title">${escapeHtml(name.replace(/_/g, ' '))}</h2>
            <span class="section-toggle">▼</span>
        </div>
        <div class="section-content" id="section-${escapeHtml(sectionId)}">
            ${data.variables.map(v => createFieldHTML(v)).join('')}
        </div>
    `;

    // Event listener para colapsar/expandir
    const header = section.querySelector('.section-header');
    header.addEventListener('click', () => toggleSection(header));

    // Event listeners para cambios en campos
    section.querySelectorAll('input, select').forEach(input => {
        input.addEventListener('change', handleFieldChange);
        input.addEventListener('input', handleFieldChange);
    });

    return section;
}

/**
 * Colapsa/expande una seccion
 */
function toggleSection(header) {
    const sectionId = header.dataset.section;
    const content = document.getElementById(`section-${sectionId}`);

    header.classList.toggle('collapsed');
    content.classList.toggle('collapsed');
}

/**
 * Crea el HTML de un campo segun su tipo
 */
function createFieldHTML(variable) {
    const { name, value, type, comment } = variable;
    let inputHTML = '';

    switch (type) {
        case 'bool':
            inputHTML = createBoolInput(name, value);
            break;
        case 'int':
            inputHTML = createNumberInput(name, value, 1);
            break;
        case 'float':
            inputHTML = createNumberInput(name, value, 0.01);
            break;
        case 'tuple':
            inputHTML = createTupleInput(name, value);
            break;
        case 'none':
            inputHTML = createNullableInput(name, value);
            break;
        case 'str':
        default:
            if (value === null) {
                inputHTML = createNullableInput(name, value);
            } else {
                inputHTML = createTextInput(name, value);
            }
    }

    return `
        <div class="config-field" data-field="${escapeHtml(name)}">
            <div class="field-header">
                <label for="${escapeHtml(name)}">${escapeHtml(name)}</label>
                <span class="field-type">${escapeHtml(type)}</span>
            </div>
            ${inputHTML}
            ${comment ? `<p class="field-comment">${escapeHtml(comment)}</p>` : ''}
        </div>
    `;
}

/**
 * Crea input para booleanos (toggle)
 */
function createBoolInput(name, value) {
    const checked = value ? 'checked' : '';
    const label = value ? 'Activado' : 'Desactivado';

    return `
        <label class="toggle-control">
            <input type="checkbox" id="${escapeHtml(name)}" ${checked} data-original="${value}" data-type="bool">
            <span class="toggle-slider"></span>
            <span class="toggle-label">${label}</span>
        </label>
    `;
}

/**
 * Crea input para numeros
 */
function createNumberInput(name, value, step) {
    const type = step === 1 ? 'int' : 'float';
    return `
        <input type="number"
               id="${escapeHtml(name)}"
               value="${value}"
               data-original="${value}"
               data-type="${type}"
               step="${step}">
    `;
}

/**
 * Crea input para texto
 */
function createTextInput(name, value) {
    return `
        <input type="text"
               id="${escapeHtml(name)}"
               value="${escapeHtml(String(value))}"
               data-original="${escapeHtml(String(value))}"
               data-type="str">
    `;
}

/**
 * Crea input para tuplas (RGB)
 */
function createTupleInput(name, value) {
    // Asumimos que es RGB por ahora
    const isRGB = name.includes('RGB') && Array.isArray(value) && value.length === 3;

    if (isRGB) {
        const [r, g, b] = value;
        return `
            <div class="tuple-input" data-field-name="${escapeHtml(name)}">
                <input type="number" class="rgb-input" data-index="0" min="0" max="255" value="${r}" data-type="tuple">
                <input type="number" class="rgb-input" data-index="1" min="0" max="255" value="${g}" data-type="tuple">
                <input type="number" class="rgb-input" data-index="2" min="0" max="255" value="${b}" data-type="tuple">
                <div class="color-preview" style="background: rgb(${r}, ${g}, ${b});"></div>
            </div>
            <input type="hidden" id="${escapeHtml(name)}" value='${JSON.stringify(value)}' data-original='${JSON.stringify(value)}' data-type="tuple">
        `;
    }

    // Para otras tuplas, usar input de texto
    return `
        <input type="text"
               id="${escapeHtml(name)}"
               value="${escapeHtml(JSON.stringify(value))}"
               data-original="${escapeHtml(JSON.stringify(value))}"
               data-type="tuple"
               placeholder="(valor1, valor2, ...)">
    `;
}

/**
 * Crea input para valores que pueden ser None
 */
function createNullableInput(name, value) {
    const isNull = value === null;
    const displayValue = isNull ? '' : String(value);

    return `
        <div class="nullable-input" data-field-name="${escapeHtml(name)}">
            <select id="${escapeHtml(name)}_toggle" data-target="${escapeHtml(name)}">
                <option value="none" ${isNull ? 'selected' : ''}>None (desactivado)</option>
                <option value="value" ${!isNull ? 'selected' : ''}>Valor personalizado</option>
            </select>
            <input type="text"
                   id="${escapeHtml(name)}"
                   value="${escapeHtml(displayValue)}"
                   data-original="${isNull ? 'null' : escapeHtml(displayValue)}"
                   data-type="nullable"
                   placeholder="Ingresa un valor..."
                   style="${isNull ? 'display: none;' : ''}">
        </div>
    `;
}

/**
 * Maneja cambios en los campos
 */
function handleFieldChange(event) {
    const target = event.target;
    const field = target.closest('.config-field');
    if (!field) return;

    const fieldName = field.dataset.field;

    // Manejar toggle de nullable
    if (target.tagName === 'SELECT' && target.id.endsWith('_toggle')) {
        const inputId = target.dataset.target;
        const input = document.getElementById(inputId);
        if (target.value === 'none') {
            input.style.display = 'none';
            input.value = '';
        } else {
            input.style.display = '';
            input.focus();
        }
    }

    // Manejar cambio de toggle bool
    if (target.type === 'checkbox') {
        const label = target.closest('.toggle-control').querySelector('.toggle-label');
        label.textContent = target.checked ? 'Activado' : 'Desactivado';
    }

    // Manejar cambio de RGB
    if (target.classList.contains('rgb-input')) {
        const tupleContainer = target.closest('.tuple-input');
        const fieldNameRGB = tupleContainer.dataset.fieldName;
        const inputs = tupleContainer.querySelectorAll('.rgb-input');
        const values = Array.from(inputs).map(i => parseInt(i.value) || 0);

        // Actualizar preview de color
        const preview = tupleContainer.querySelector('.color-preview');
        if (preview) {
            preview.style.background = `rgb(${values[0]}, ${values[1]}, ${values[2]})`;
        }

        // Actualizar input hidden
        const hiddenInput = document.getElementById(fieldNameRGB);
        if (hiddenInput) {
            hiddenInput.value = JSON.stringify(values);
        }
    }

    // Actualizar estado de currentConfig
    updateCurrentConfig(fieldName);

    // Verificar cambios
    checkForChanges();

    // Marcar campo como modificado
    updateFieldModifiedState(field, fieldName);
}

/**
 * Actualiza el valor en currentConfig
 */
function updateCurrentConfig(fieldName) {
    // Buscar la variable en currentConfig
    for (const sectionData of Object.values(currentConfig)) {
        const variable = sectionData.variables.find(v => v.name === fieldName);
        if (variable) {
            variable.value = getCurrentValue(fieldName, variable.type);
            break;
        }
    }
}

/**
 * Obtiene el valor actual de un campo
 */
function getCurrentValue(fieldName, type) {
    const input = document.getElementById(fieldName);
    if (!input) return null;

    // Verificar si es nullable
    const toggle = document.getElementById(`${fieldName}_toggle`);
    if (toggle && toggle.value === 'none') {
        return null;
    }

    switch (type) {
        case 'bool':
            return input.checked;
        case 'int':
            return parseInt(input.value) || 0;
        case 'float':
            return parseFloat(input.value) || 0;
        case 'tuple':
            try {
                const parsed = JSON.parse(input.value);
                return Array.isArray(parsed) ? parsed : null;
            } catch {
                return null;
            }
        case 'nullable':
        case 'none':
            if (toggle && toggle.value === 'none') return null;
            return input.value || null;
        case 'str':
        default:
            return input.value;
    }
}

/**
 * Obtiene el valor original de un campo
 */
function getOriginalValue(fieldName) {
    for (const sectionData of Object.values(originalConfig)) {
        const variable = sectionData.variables.find(v => v.name === fieldName);
        if (variable) {
            return variable.value;
        }
    }
    return null;
}

/**
 * Actualiza el estado visual de campo modificado
 */
function updateFieldModifiedState(field, fieldName) {
    const originalValue = getOriginalValue(fieldName);

    // Buscar valor actual
    let currentValue = null;
    for (const sectionData of Object.values(currentConfig)) {
        const variable = sectionData.variables.find(v => v.name === fieldName);
        if (variable) {
            currentValue = variable.value;
            break;
        }
    }

    const isModified = JSON.stringify(originalValue) !== JSON.stringify(currentValue);

    if (isModified) {
        field.classList.add('modified');
    } else {
        field.classList.remove('modified');
    }
}

/**
 * Verifica si hay cambios pendientes
 */
function checkForChanges() {
    hasChanges = JSON.stringify(originalConfig) !== JSON.stringify(currentConfig);

    if (hasChanges) {
        changesIndicator.classList.add('visible');
    } else {
        changesIndicator.classList.remove('visible');
    }

    btnCancel.disabled = !hasChanges;
    btnSave.disabled = !hasChanges;
    btnSaveRestart.disabled = !hasChanges;
}

/**
 * Obtiene los cambios respecto al original
 */
function getChangedValues() {
    const changes = {};

    for (const sectionData of Object.values(currentConfig)) {
        for (const variable of sectionData.variables) {
            const original = getOriginalValue(variable.name);
            if (JSON.stringify(original) !== JSON.stringify(variable.value)) {
                changes[variable.name] = variable.value;
            }
        }
    }

    return changes;
}

/**
 * Descarta todos los cambios
 */
function cancelChanges() {
    if (!confirm('¿Deseas descartar todos los cambios?')) return;

    currentConfig = JSON.parse(JSON.stringify(originalConfig));
    renderSections(currentConfig);
    checkForChanges();
}

/**
 * Guarda los cambios sin reiniciar
 */
async function saveChanges() {
    const changes = getChangedValues();

    if (Object.keys(changes).length === 0) {
        showToast('No hay cambios que guardar', 'info');
        return;
    }

    try {
        btnSave.disabled = true;
        btnSave.textContent = 'Guardando...';

        const response = await fetchAPI('/api/config', {
            method: 'POST',
            body: JSON.stringify({ changes })
        });

        if (response.success) {
            showToast('Configuracion guardada correctamente', 'success');
            originalConfig = JSON.parse(JSON.stringify(currentConfig));
            checkForChanges();

            // Quitar clase modified de todos los campos
            document.querySelectorAll('.config-field.modified').forEach(f => {
                f.classList.remove('modified');
            });
        } else {
            showToast('Error: ' + response.error, 'error');
        }
    } catch (error) {
        showToast('Error de conexion: ' + error.message, 'error');
    } finally {
        btnSave.disabled = false;
        btnSave.textContent = 'Guardar';
        checkForChanges();
    }
}

/**
 * Muestra modal de confirmacion de reinicio
 */
function showRestartModal() {
    restartModal.classList.add('visible');
}

/**
 * Oculta modal de reinicio
 */
function hideRestartModal() {
    restartModal.classList.remove('visible');
}

/**
 * Confirma y ejecuta el reinicio
 */
async function confirmRestart() {
    const changes = getChangedValues();

    try {
        btnSaveRestart.disabled = true;
        btnSaveRestart.textContent = 'Reiniciando...';
        hideRestartModal();

        const response = await fetchAPI('/api/config/restart', {
            method: 'POST',
            body: JSON.stringify({ changes })
        });

        if (response.success) {
            showToast('Bot reiniciandose...', 'success');

            // Mostrar mensaje de espera
            sectionsContainer.innerHTML = `
                <div class="restart-message">
                    <h2>Reiniciando bot...</h2>
                    <div class="loading-spinner"></div>
                    <p>La pagina se recargara automaticamente cuando el bot este listo.</p>
                </div>
            `;

            // Deshabilitar botones
            btnCancel.disabled = true;
            btnSave.disabled = true;
            btnSaveRestart.disabled = true;

            // Intentar reconectar cada 3 segundos
            setTimeout(checkBotReady, 3000);
        } else {
            showToast('Error: ' + response.error, 'error');
            btnSaveRestart.disabled = false;
            btnSaveRestart.textContent = 'Guardar y Reiniciar';
        }
    } catch (error) {
        showToast('Error de conexion: ' + error.message, 'error');
        btnSaveRestart.disabled = false;
        btnSaveRestart.textContent = 'Guardar y Reiniciar';
    }
}

/**
 * Verifica si el bot esta listo despues del reinicio
 */
async function checkBotReady() {
    try {
        const response = await fetch('/health');
        if (response.ok) {
            // Bot listo, recargar pagina
            window.location.reload();
        } else {
            // Seguir esperando
            setTimeout(checkBotReady, 2000);
        }
    } catch {
        // Error de conexion, seguir esperando
        setTimeout(checkBotReady, 2000);
    }
}

/**
 * Muestra un mensaje de error
 */
function showError(message) {
    sectionsContainer.innerHTML = `
        <div class="error-message">
            <h3>Error</h3>
            <p>${escapeHtml(message)}</p>
            <button class="btn primary" onclick="loadConfig()">Reintentar</button>
        </div>
    `;
}

/**
 * Muestra un toast/notificacion
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // Animar entrada
    requestAnimationFrame(() => {
        toast.classList.add('visible');
    });

    // Remover despues de 3 segundos
    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Inicializacion
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();

    // Event listeners de botones principales
    btnCancel.addEventListener('click', cancelChanges);
    btnSave.addEventListener('click', saveChanges);
    btnSaveRestart.addEventListener('click', showRestartModal);

    // Event listeners del modal
    document.getElementById('restart-confirm').addEventListener('click', confirmRestart);
    document.getElementById('restart-cancel').addEventListener('click', hideRestartModal);
    document.getElementById('restart-modal-close').addEventListener('click', hideRestartModal);

    // Cerrar modal al hacer click en overlay
    restartModal.addEventListener('click', (e) => {
        if (e.target === restartModal) {
            hideRestartModal();
        }
    });

    // Prevenir cierre accidental con cambios pendientes
    window.addEventListener('beforeunload', (e) => {
        if (hasChanges) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
});
