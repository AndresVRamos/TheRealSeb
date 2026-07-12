/**
 * Home JS - Logica para la vista principal del dashboard
 */

// Formatear tiempo en horas/minutos
function formatDuration(seconds) {
    if (!seconds || seconds === 0) return '0h';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
}

// Formatear numero con separadores
function formatNumber(num) {
    if (num === null || num === undefined) return '--';
    return num.toLocaleString('es-ES');
}

// Formatear fecha relativa
function formatRelativeTime(dateString) {
    if (!dateString) return '--';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Ahora';
    if (diffMins < 60) return `Hace ${diffMins}m`;
    if (diffHours < 24) return `Hace ${diffHours}h`;
    if (diffDays < 7) return `Hace ${diffDays}d`;
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
}

// Formatear fecha corta
function formatShortDate(dateString) {
    if (!dateString) return '--';
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
    });
}

// Cargar estadisticas globales
async function loadGlobalStats() {
    try {
        const response = await fetch('/api/home/stats');
        const data = await response.json();

        if (data.error) {
            console.error('Error loading stats:', data.error);
            return;
        }

        // Actualizar stats cards
        document.getElementById('total-plays').textContent = formatNumber(data.total_plays);
        document.getElementById('unique-tracks').textContent = formatNumber(data.unique_tracks);
        document.getElementById('unique-artists').textContent = formatNumber(data.unique_artists);
        document.getElementById('total-time').textContent = formatDuration(data.total_time);

        // Actualizar bot info
        document.getElementById('guild-count').textContent = formatNumber(data.guild_count);
        document.getElementById('first-play').textContent = formatShortDate(data.first_play);
        document.getElementById('last-play').textContent = formatRelativeTime(data.last_play);
        document.getElementById('uptime').textContent = data.uptime || '--';

        // Actualizar estado del bot
        updateBotStatus(data.bot_online);

    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

// Actualizar estado del bot
function updateBotStatus(isOnline) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');

    if (isOnline) {
        statusDot.classList.add('online');
        statusDot.classList.remove('offline');
        statusText.textContent = 'Online';
    } else {
        statusDot.classList.add('offline');
        statusDot.classList.remove('online');
        statusText.textContent = 'Offline';
    }
}

// Cargar actividad reciente
async function loadRecentActivity() {
    const container = document.getElementById('recent-plays');
    try {
        const response = await fetch('/api/home/recent');
        const data = await response.json();

        if (data.error || !data.plays || data.plays.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎵</div>
                    <div>No hay actividad reciente</div>
                </div>
            `;
            return;
        }

        container.innerHTML = data.plays.map(play => `
            <div class="activity-item">
                <span class="song-title" title="${escapeHtml(play.title)}">${escapeHtml(play.title)}</span>
                <span class="song-artist" title="${escapeHtml(play.artist || 'Desconocido')}">${escapeHtml(play.artist || 'Desconocido')}</span>
                <span class="play-time">${formatRelativeTime(play.played_at)}</span>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error fetching recent activity:', error);
        container.innerHTML = '<div class="loading">Error al cargar</div>';
    }
}

// Cargar top canciones
async function loadTopSongs() {
    const container = document.getElementById('top-songs');
    try {
        const response = await fetch('/api/home/top-songs');
        const data = await response.json();

        if (data.error || !data.songs || data.songs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎸</div>
                    <div>No hay canciones</div>
                </div>
            `;
            return;
        }

        container.innerHTML = data.songs.map((song, index) => `
            <div class="top-item">
                <span class="rank">#${index + 1}</span>
                <span class="item-name" title="${escapeHtml(song.title)}">${escapeHtml(song.title)}</span>
                <span class="item-count">${song.plays} plays</span>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error fetching top songs:', error);
        container.innerHTML = '<div class="loading">Error al cargar</div>';
    }
}

// Cargar top artistas
async function loadTopArtists() {
    const container = document.getElementById('top-artists');
    try {
        const response = await fetch('/api/home/top-artists');
        const data = await response.json();

        if (data.error || !data.artists || data.artists.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎤</div>
                    <div>No hay artistas</div>
                </div>
            `;
            return;
        }

        container.innerHTML = data.artists.map((artist, index) => `
            <div class="top-item">
                <span class="rank">#${index + 1}</span>
                <span class="item-name" title="${escapeHtml(artist.name)}">${escapeHtml(artist.name)}</span>
                <span class="item-count">${artist.plays} plays</span>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error fetching top artists:', error);
        container.innerHTML = '<div class="loading">Error al cargar</div>';
    }
}

// Escapar HTML para evitar XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Inicializar pagina
document.addEventListener('DOMContentLoaded', () => {
    // Marcar nav link activo
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === '/' || link.getAttribute('data-page') === 'home') {
            link.classList.add('active');
        }
    });

    // Cargar todos los datos
    loadGlobalStats();
    loadRecentActivity();
    loadTopSongs();
    loadTopArtists();

    // Refrescar stats cada 30 segundos
    setInterval(() => {
        loadGlobalStats();
        loadRecentActivity();
    }, 30000);
});
