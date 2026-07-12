/**
 * Servers JS - Logica para la vista de servidores
 */

// Servidor seleccionado actual
let currentServerId = null;

/**
 * Carga la lista de servidores
 */
async function loadServers() {
    const grid = document.getElementById('servers-grid');
    const countValue = document.querySelector('.count-value');

    try {
        const response = await fetch('/api/servers');
        const data = await response.json();

        if (data.error) {
            grid.innerHTML = '<div class="loading-state">Error al cargar servidores</div>';
            return;
        }

        // Actualizar contador
        countValue.textContent = data.servers.length;

        if (data.servers.length === 0) {
            grid.innerHTML = '<div class="loading-state">No hay servidores registrados</div>';
            return;
        }

        // Renderizar cards
        grid.innerHTML = data.servers.map(server => {
            const iconHtml = server.icon_url
                ? `<img src="${escapeHtml(server.icon_url)}" alt="${escapeHtml(server.name)}">`
                : server.name.charAt(0).toUpperCase();

            return `
                <div class="server-card" data-id="${server.id}" data-discord-id="${server.discord_id}">
                    <div class="server-header">
                        <div class="server-icon">${iconHtml}</div>
                        <div class="server-name" title="${escapeHtml(server.name)}">${escapeHtml(server.name)}</div>
                    </div>
                    <div class="server-stats">
                        <div class="server-stat">
                            <span class="stat-value">${formatNumber(server.total_plays)}</span>
                            <span class="stat-label">Plays</span>
                        </div>
                        <div class="server-stat">
                            <span class="stat-value">${formatNumber(server.total_users)}</span>
                            <span class="stat-label">Usuarios</span>
                        </div>
                        <div class="server-stat">
                            <span class="stat-value">${formatTime(server.total_time)}</span>
                            <span class="stat-label">Tiempo</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Event listeners para las cards
        document.querySelectorAll('.server-card').forEach(card => {
            card.addEventListener('click', () => {
                const id = card.dataset.id;
                showServerDetail(id);
            });
        });

    } catch (error) {
        console.error('Error loading servers:', error);
        grid.innerHTML = '<div class="loading-state">Error de conexion</div>';
    }
}

/**
 * Muestra el modal con detalles del servidor
 */
async function showServerDetail(serverId) {
    currentServerId = serverId;
    const modal = document.getElementById('server-detail-modal');

    // Mostrar modal
    modal.style.display = 'flex';

    // Cargar info basica
    try {
        const response = await fetch(`/api/servers/${serverId}`);
        const data = await response.json();

        if (data.error) {
            closeModal();
            return;
        }

        // Actualizar header
        const iconImg = document.getElementById('modal-server-icon');
        if (data.icon_url) {
            iconImg.src = data.icon_url;
            iconImg.style.display = 'block';
        } else {
            iconImg.style.display = 'none';
        }
        document.getElementById('modal-server-name').textContent = data.name;

        // Actualizar stats
        document.getElementById('modal-plays').textContent = formatNumber(data.total_plays);
        document.getElementById('modal-users').textContent = formatNumber(data.total_users);
        document.getElementById('modal-time').textContent = formatTime(data.total_time);

        // Cargar tab activo
        loadTabData('songs');

    } catch (error) {
        console.error('Error loading server detail:', error);
        closeModal();
    }
}

/**
 * Carga datos del tab seleccionado
 */
async function loadTabData(tab) {
    if (!currentServerId) return;

    const tabContent = document.getElementById(`tab-${tab}`);
    const tableBody = tabContent.querySelector('tbody');
    const loading = tabContent.querySelector('.tab-loading');
    const empty = tabContent.querySelector('.tab-empty');

    // Mostrar loading
    tableBody.innerHTML = '';
    loading.style.display = 'block';
    empty.style.display = 'none';

    try {
        const response = await fetch(`/api/servers/${currentServerId}/${tab}`);
        const data = await response.json();

        loading.style.display = 'none';

        if (data.error || !data.items || data.items.length === 0) {
            empty.style.display = 'block';
            return;
        }

        // Renderizar segun el tab
        if (tab === 'songs') {
            tableBody.innerHTML = data.items.map((item, i) => `
                <tr>
                    <td>${i + 1}</td>
                    <td class="truncate" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</td>
                    <td class="artist-col" title="${escapeHtml(item.artist || 'Desconocido')}">${escapeHtml(item.artist || 'Desconocido')}</td>
                    <td>${item.plays}</td>
                </tr>
            `).join('');
        } else if (tab === 'artists') {
            tableBody.innerHTML = data.items.map((item, i) => `
                <tr>
                    <td>${i + 1}</td>
                    <td class="truncate" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</td>
                    <td>${item.plays}</td>
                </tr>
            `).join('');
        } else if (tab === 'users') {
            tableBody.innerHTML = data.items.map((item, i) => `
                <tr>
                    <td>${i + 1}</td>
                    <td class="truncate"><span class="user-link" data-user="${escapeHtml(item.name)}" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span></td>
                    <td>${item.plays}</td>
                </tr>
            `).join('');

            // Agregar click handlers para usuarios
            tableBody.querySelectorAll('.user-link').forEach(link => {
                link.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const userName = link.dataset.user;
                    showUserProfile(userName);
                });
            });
        }

    } catch (error) {
        console.error(`Error loading ${tab}:`, error);
        loading.style.display = 'none';
        empty.textContent = 'Error de conexion';
        empty.style.display = 'block';
    }
}

/**
 * Cierra el modal
 */
function closeModal() {
    const modal = document.getElementById('server-detail-modal');
    modal.style.display = 'none';
    currentServerId = null;
}

/**
 * Formatea numero con separador de miles
 */
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return num.toLocaleString('es-ES');
}

/**
 * Formatea tiempo en segundos a formato legible
 */
function formatTime(seconds) {
    if (!seconds) return '0m';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
}

/**
 * Escapa HTML para evitar XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Maneja cambio de tab
 */
function handleTabChange(event) {
    const btn = event.target;
    if (!btn.classList.contains('tab-btn')) return;

    const tab = btn.dataset.tab;

    // Actualizar botones activos
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Actualizar contenido visible
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(`tab-${tab}`).classList.add('active');

    // Cargar datos del tab
    loadTabData(tab);
}

// Inicializar
document.addEventListener('DOMContentLoaded', () => {
    // Cargar servidores
    loadServers();

    // Event listener para tabs
    document.querySelector('.detail-tabs')?.addEventListener('click', handleTabChange);

    // Event listeners para cerrar modal
    document.getElementById('modal-close')?.addEventListener('click', closeModal);
    document.getElementById('server-detail-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'server-detail-modal') {
            closeModal();
        }
    });

    // Inicializar modal de perfil (componente compartido)
    ProfileModal.init();

    // Cerrar con Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
});
