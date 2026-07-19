/**
 * Profile Modal - Componente reutilizable para mostrar perfiles de usuario
 *
 * Dependencias:
 * - Chart.js (para el grafico de actividad)
 * - CSS: profile modal styles en stats.css o servers.css
 *
 * Uso:
 * 1. Incluir el HTML del modal en la pagina
 * 2. Incluir este script despues de Chart.js
 * 3. Llamar a ProfileModal.show(userName) para mostrar el perfil
 */

const ProfileModal = (function() {
    // Referencia al grafico de actividad del perfil
    let profileActivityChart = null;

    /**
     * Muestra el perfil de un usuario
     * @param {string} userName - Nombre del usuario a mostrar
     */
    async function show(userName) {
        const modal = document.getElementById('user-profile-modal');
        const loading = document.getElementById('profile-loading');
        const content = document.getElementById('profile-content');

        if (!modal || !loading || !content) {
            console.error('ProfileModal: Missing required DOM elements');
            return;
        }

        // Mostrar modal con loading
        modal.style.display = 'flex';
        loading.style.display = 'block';
        loading.textContent = 'Cargando...';
        content.style.display = 'none';

        try {
            // Primero buscar el ID del usuario por nombre
            const searchResponse = await fetch(`/api/users/by-name/${encodeURIComponent(userName)}`);
            const searchData = await searchResponse.json();

            if (searchData.error) {
                loading.textContent = 'Usuario no encontrado';
                return;
            }

            // Obtener perfil completo
            const response = await fetch(`/api/users/${searchData.id}`);
            const data = await response.json();

            if (data.error) {
                loading.textContent = 'Error al cargar perfil';
                return;
            }

            // Ocultar loading y mostrar contenido
            loading.style.display = 'none';
            content.style.display = 'block';

            // Avatar
            const avatarEl = document.getElementById('profile-avatar');
            if (data.avatar_url) {
                avatarEl.innerHTML = `<img src="${escapeHtml(data.avatar_url)}" alt="${escapeHtml(data.name)}">`;
            } else {
                avatarEl.innerHTML = '';
                avatarEl.textContent = data.name.charAt(0).toUpperCase();
            }

            // Nombre
            document.getElementById('profile-name').textContent = data.name;

            // Miembro desde
            const memberSince = document.getElementById('profile-member-since');
            if (data.stats.first_play) {
                const date = new Date(data.stats.first_play);
                memberSince.textContent = `Escuchando desde ${date.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}`;
            } else {
                memberSince.textContent = '';
            }

            // Stats
            document.getElementById('profile-plays').textContent = formatNumber(data.stats.total_plays);
            document.getElementById('profile-time').textContent = formatTime(data.stats.total_time);
            document.getElementById('profile-tracks').textContent = formatNumber(data.stats.unique_tracks);
            document.getElementById('profile-artists').textContent = formatNumber(data.stats.unique_artists);

            // Favoritos
            document.getElementById('profile-fav-hour').textContent =
                data.stats.favorite_hour !== null ? `${data.stats.favorite_hour}:00 - ${data.stats.favorite_hour + 1}:00` : '--';
            document.getElementById('profile-fav-day').textContent =
                data.stats.favorite_day || '--';

            // Top canciones
            const topSongsEl = document.getElementById('profile-top-songs');
            if (data.top_songs.length > 0) {
                topSongsEl.innerHTML = data.top_songs.map(song =>
                    `<li>${escapeHtml(song.title)} <span class="plays-count">(${song.plays})</span></li>`
                ).join('');
            } else {
                topSongsEl.innerHTML = '<li class="empty">Sin datos</li>';
            }

            // Top artistas
            const topArtistsEl = document.getElementById('profile-top-artists');
            if (data.top_artists.length > 0) {
                topArtistsEl.innerHTML = data.top_artists.map(artist =>
                    `<li>${escapeHtml(artist.name)} <span class="plays-count">(${artist.plays})</span></li>`
                ).join('');
            } else {
                topArtistsEl.innerHTML = '<li class="empty">Sin datos</li>';
            }

            // Grafico de actividad reciente
            renderActivityChart(data.recent_activity);

        } catch (error) {
            console.error('Error loading user profile:', error);
            loading.textContent = 'Error de conexion';
        }
    }

    /**
     * Renderiza el mini grafico de actividad del perfil
     * @param {Array} activityData - Datos de actividad [{date, plays}, ...]
     */
    function renderActivityChart(activityData) {
        const ctx = document.getElementById('profile-activity-chart');
        if (!ctx) return;

        if (profileActivityChart) {
            profileActivityChart.destroy();
        }

        // Crear array de los ultimos 7 dias
        const labels = [];
        const values = [];
        const activityMap = {};

        // Crear mapa de actividad
        activityData.forEach(item => {
            activityMap[item.date] = item.plays;
        });

        // Generar ultimos 7 dias (usando fecha local, no UTC)
        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            // Usar formato local en lugar de toISOString() que convierte a UTC
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const dateStr = `${year}-${month}-${day}`;
            const dayName = date.toLocaleDateString('es-ES', { weekday: 'short' });
            labels.push(dayName);
            values.push(activityMap[dateStr] || 0);
        }

        // Obtener colores del tema si estan disponibles
        const primaryColor = typeof chartColors !== 'undefined' ? chartColors.primary : '#0a84ff';
        const textColor = '#98989d';

        profileActivityChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: primaryColor + '60',
                    borderColor: primaryColor,
                    borderWidth: 1,
                    borderRadius: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: textColor,
                            font: { size: 10 }
                        }
                    },
                    y: {
                        display: false,
                        beginAtZero: true
                    }
                }
            }
        });
    }

    /**
     * Cierra el modal de perfil
     */
    function close() {
        const modal = document.getElementById('user-profile-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * Inicializa los event listeners del modal
     * Debe llamarse en DOMContentLoaded
     */
    function init() {
        // Boton de cerrar
        document.getElementById('profile-modal-close')?.addEventListener('click', close);

        // Click fuera del modal
        document.getElementById('user-profile-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'user-profile-modal') {
                close();
            }
        });

        // Tecla Escape (agregar al listener existente si hay uno)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                close();
            }
        });
    }

    // Funciones de utilidad (usar las globales si existen, sino definir locales)
    function formatNumber(num) {
        if (typeof window.formatNumber === 'function') {
            return window.formatNumber(num);
        }
        if (num === null || num === undefined) return '0';
        return num.toLocaleString('es-ES');
    }

    function formatTime(seconds) {
        if (typeof window.formatTime === 'function') {
            return window.formatTime(seconds);
        }
        if (!seconds) return '0m';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    }

    function escapeHtml(text) {
        if (typeof window.escapeHtml === 'function') {
            return window.escapeHtml(text);
        }
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // API publica
    return {
        show: show,
        close: close,
        init: init
    };
})();

// Alias global para facilitar uso
function showUserProfile(userName) {
    ProfileModal.show(userName);
}

function closeProfileModal() {
    ProfileModal.close();
}
