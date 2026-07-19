/**
 * Stats JS - Logica para la vista de estadisticas
 * Usa Chart.js para renderizar graficos
 */

// Configuracion global de Chart.js
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif';
Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#98989d';

// Colores para graficos
const chartColors = {
    primary: '#0a84ff',
    secondary: '#5e5ce6',
    success: '#32d74b',
    warning: '#ff9f0a',
    error: '#ff453a',
    gradient: ['#0a84ff', '#5e5ce6', '#bf5af2', '#ff375f', '#ff9f0a']
};

// Referencias a los graficos
let trendChart = null;
let hourlyChart = null;
let dailyChart = null;
let artistsChart = null;
let usersChart = null;
let activeUsersChart = null;

// Rango actual seleccionado
let currentRange = 7;

// Servidor actual seleccionado (vacio = todos)
let currentServer = '';

// Guardar las fechas del grafico de tendencia para referencia
let trendDates = [];

// Datos guardados para los graficos con toggle
let hourlyData = null;
let dailyData = null;

// Fechas para el grafico de usuarios activos
let activeUsersDates = [];

/**
 * Obtiene el color de fondo del tema actual
 */
function getThemeColors() {
    const style = getComputedStyle(document.documentElement);
    return {
        text: style.getPropertyValue('--text-primary').trim() || '#f5f5f7',
        textSecondary: style.getPropertyValue('--text-secondary').trim() || '#98989d',
        grid: style.getPropertyValue('--divider').trim() || 'rgba(255, 255, 255, 0.12)',
        bg: style.getPropertyValue('--bg-secondary').trim() || '#1c1c1e'
    };
}

/**
 * Construye los query params para las API calls
 */
function buildQueryParams(extra = {}) {
    const params = new URLSearchParams();
    params.set('days', currentRange);
    if (currentServer) {
        params.set('guild_id', currentServer);
    }
    for (const [key, value] of Object.entries(extra)) {
        params.set(key, value);
    }
    return params.toString();
}

/**
 * Configuracion base para graficos de linea/barra
 */
function getBaseConfig() {
    const colors = getThemeColors();
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            }
        },
        scales: {
            x: {
                grid: {
                    color: colors.grid,
                    drawBorder: false
                },
                ticks: {
                    color: colors.textSecondary,
                    font: { size: 11 }
                }
            },
            y: {
                grid: {
                    color: colors.grid,
                    drawBorder: false
                },
                ticks: {
                    color: colors.textSecondary,
                    font: { size: 11 }
                },
                beginAtZero: true
            }
        }
    };
}

/**
 * Carga y renderiza el grafico de tendencia
 */
async function loadTrendChart() {
    try {
        const response = await fetch(`/api/stats/trend?${buildQueryParams()}`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading trend:', data.error);
            return;
        }

        // Usar fechas del backend para evitar desfases de zona horaria
        trendDates = data.dates || [];

        const ctx = document.getElementById('trend-chart').getContext('2d');
        const config = getBaseConfig();

        if (trendChart) {
            trendChart.destroy();
        }

        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Reproducciones',
                    data: data.values,
                    borderColor: chartColors.primary,
                    backgroundColor: chartColors.primary + '20',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointBackgroundColor: chartColors.primary,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                ...config,
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const date = trendDates[index];
                        const label = data.labels[index];
                        showDayDetail(date, label);
                    }
                },
                onHover: (event, elements) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                }
            }
        });
    } catch (error) {
        console.error('Error fetching trend data:', error);
    }
}

/**
 * Carga y renderiza el grafico por hora
 */
async function loadHourlyChart() {
    try {
        const response = await fetch(`/api/stats/hourly?${buildQueryParams()}`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading hourly:', data.error);
            return;
        }

        // Guardar datos para el toggle
        hourlyData = data;

        const ctx = document.getElementById('hourly-chart').getContext('2d');
        const config = getBaseConfig();
        const showAverage = document.getElementById('hourly-avg-toggle')?.checked || false;
        const values = showAverage ? data.averages : data.totals;

        if (hourlyChart) {
            hourlyChart.destroy();
        }

        hourlyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: showAverage ? 'Promedio' : 'Reproducciones',
                    data: values,
                    backgroundColor: chartColors.primary + '80',
                    borderColor: chartColors.primary,
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: config
        });
    } catch (error) {
        console.error('Error fetching hourly data:', error);
    }
}

/**
 * Actualiza el grafico por hora sin recargar datos
 */
function updateHourlyChart() {
    if (!hourlyData) return;

    const showAverage = document.getElementById('hourly-avg-toggle')?.checked || false;
    const values = showAverage ? hourlyData.averages : hourlyData.totals;

    // Actualizar labels del toggle
    const toggleContainer = document.getElementById('hourly-avg-toggle')?.closest('.toggle-switch');
    if (toggleContainer) {
        const labels = toggleContainer.querySelectorAll('.toggle-label');
        labels[0].dataset.active = !showAverage;
        labels[1].dataset.active = showAverage;
    }

    if (hourlyChart) {
        hourlyChart.data.datasets[0].data = values;
        hourlyChart.data.datasets[0].label = showAverage ? 'Promedio' : 'Reproducciones';
        hourlyChart.update();
    }
}

/**
 * Carga y renderiza el grafico por dia de la semana
 */
async function loadDailyChart() {
    try {
        const response = await fetch(`/api/stats/daily?${buildQueryParams()}`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading daily:', data.error);
            return;
        }

        // Guardar datos para el toggle
        dailyData = data;

        const ctx = document.getElementById('daily-chart').getContext('2d');
        const config = getBaseConfig();
        const showAverage = document.getElementById('daily-avg-toggle')?.checked || false;
        const values = showAverage ? data.averages : data.totals;

        if (dailyChart) {
            dailyChart.destroy();
        }

        dailyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: showAverage ? 'Promedio' : 'Reproducciones',
                    data: values,
                    backgroundColor: chartColors.gradient.map(c => c + '80'),
                    borderColor: chartColors.gradient,
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: config
        });
    } catch (error) {
        console.error('Error fetching daily data:', error);
    }
}

/**
 * Actualiza el grafico por dia sin recargar datos
 */
function updateDailyChart() {
    if (!dailyData) return;

    const showAverage = document.getElementById('daily-avg-toggle')?.checked || false;
    const values = showAverage ? dailyData.averages : dailyData.totals;

    // Actualizar labels del toggle
    const toggleContainer = document.getElementById('daily-avg-toggle')?.closest('.toggle-switch');
    if (toggleContainer) {
        const labels = toggleContainer.querySelectorAll('.toggle-label');
        labels[0].dataset.active = !showAverage;
        labels[1].dataset.active = showAverage;
    }

    if (dailyChart) {
        dailyChart.data.datasets[0].data = values;
        dailyChart.data.datasets[0].label = showAverage ? 'Promedio' : 'Reproducciones';
        dailyChart.update();
    }
}

/**
 * Carga y renderiza el grafico de top artistas
 */
async function loadArtistsChart() {
    try {
        const response = await fetch(`/api/stats/top-artists?${buildQueryParams({ limit: 5 })}`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading artists:', data.error);
            return;
        }

        const ctx = document.getElementById('artists-chart').getContext('2d');
        const colors = getThemeColors();

        if (artistsChart) {
            artistsChart.destroy();
        }

        artistsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: chartColors.gradient,
                    borderColor: colors.bg,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'right',
                        labels: {
                            color: colors.textSecondary,
                            font: { size: 11 },
                            padding: 12,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    }
                },
                cutout: '60%'
            }
        });
    } catch (error) {
        console.error('Error fetching artists data:', error);
    }
}

// Guardar nombres de usuarios del grafico
let topUsersNames = [];

/**
 * Carga y renderiza el grafico de top usuarios
 */
async function loadUsersChart() {
    try {
        const response = await fetch(`/api/stats/top-users?${buildQueryParams({ limit: 5 })}`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading users:', data.error);
            return;
        }

        // Guardar nombres para referencia
        topUsersNames = data.labels;

        const ctx = document.getElementById('users-chart').getContext('2d');
        const config = getBaseConfig();

        if (usersChart) {
            usersChart.destroy();
        }

        // Grafico de barras horizontales con click
        usersChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Reproducciones',
                    data: data.values,
                    backgroundColor: chartColors.gradient.map(c => c + '80'),
                    borderColor: chartColors.gradient,
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                ...config,
                indexAxis: 'y',
                scales: {
                    ...config.scales,
                    x: {
                        ...config.scales.x,
                        beginAtZero: true
                    }
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const userName = topUsersNames[index];
                        showUserProfile(userName);
                    }
                },
                onHover: (event, elements) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                }
            }
        });
    } catch (error) {
        console.error('Error fetching users data:', error);
    }
}

/**
 * Carga y renderiza el grafico de usuarios activos por dia
 */
async function loadActiveUsersChart() {
    try {
        const response = await fetch(`/api/stats/active-users?${buildQueryParams()}`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading active users:', data.error);
            return;
        }

        // Usar fechas del backend para evitar desfases de zona horaria
        activeUsersDates = data.dates || [];

        const ctx = document.getElementById('active-users-chart').getContext('2d');
        const config = getBaseConfig();

        if (activeUsersChart) {
            activeUsersChart.destroy();
        }

        activeUsersChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Usuarios',
                    data: data.values,
                    borderColor: chartColors.success,
                    backgroundColor: chartColors.success + '20',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointBackgroundColor: chartColors.success,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                ...config,
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const date = activeUsersDates[index];
                        const label = data.labels[index];
                        showActiveUsersDetail(date, label);
                    }
                },
                onHover: (event, elements) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                }
            }
        });
    } catch (error) {
        console.error('Error fetching active users data:', error);
    }
}

// Tooltip del heatmap
let heatmapTooltip = null;

/**
 * Crea o obtiene el tooltip del heatmap
 */
function getHeatmapTooltip() {
    if (!heatmapTooltip) {
        heatmapTooltip = document.createElement('div');
        heatmapTooltip.className = 'heatmap-tooltip';
        heatmapTooltip.innerHTML = `
            <div class="heatmap-tooltip-title"></div>
            <div class="heatmap-tooltip-value">
                <span class="heatmap-tooltip-dot"></span>
                <span class="heatmap-tooltip-text"></span>
            </div>
        `;
        document.body.appendChild(heatmapTooltip);
    }
    return heatmapTooltip;
}

/**
 * Muestra el tooltip del heatmap
 */
function showHeatmapTooltip(event, dayName, hour, value) {
    const tooltip = getHeatmapTooltip();
    const title = tooltip.querySelector('.heatmap-tooltip-title');
    const text = tooltip.querySelector('.heatmap-tooltip-text');

    title.textContent = `${dayName} ${hour}:00`;
    text.textContent = `Reproducciones: ${value}`;

    // Posicionar tooltip
    const rect = event.target.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();

    let left = rect.left + rect.width / 2;
    let top = rect.top - 8;

    // Mostrar temporalmente para obtener dimensiones
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
    tooltip.style.transform = 'translate(-50%, -100%)';
    tooltip.classList.add('visible');
}

/**
 * Oculta el tooltip del heatmap
 */
function hideHeatmapTooltip() {
    const tooltip = getHeatmapTooltip();
    tooltip.classList.remove('visible');
}

/**
 * Carga y renderiza el heatmap de actividad
 */
async function loadHeatmap() {
    try {
        const response = await fetch(`/api/stats/heatmap?${buildQueryParams()}`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading heatmap:', data.error);
            return;
        }

        const hoursContainer = document.getElementById('heatmap-hours');
        const grid = document.getElementById('heatmap-grid');
        if (!grid || !hoursContainer) return;

        // Limpiar contenedores
        hoursContainer.innerHTML = '';
        grid.innerHTML = '';

        // Generar fila de labels de hora (alineados con las celdas)
        const hoursSpacer = document.createElement('div');
        hoursSpacer.className = 'heatmap-hours-spacer';
        hoursContainer.appendChild(hoursSpacer);

        const hoursCells = document.createElement('div');
        hoursCells.className = 'heatmap-hours-cells';
        for (let hour = 0; hour < 24; hour++) {
            const hourLabel = document.createElement('div');
            hourLabel.className = 'hour-label';
            // Mostrar label cada 3 horas
            if (hour % 3 === 0) {
                hourLabel.textContent = hour.toString().padStart(2, '0');
            }
            hoursCells.appendChild(hourLabel);
        }
        hoursContainer.appendChild(hoursCells);

        // Calcular niveles (0-4) basados en max_value
        const maxValue = data.max_value || 1;
        const getLevel = (value) => {
            if (value === 0) return 0;
            const ratio = value / maxValue;
            if (ratio <= 0.25) return 1;
            if (ratio <= 0.50) return 2;
            if (ratio <= 0.75) return 3;
            return 4;
        };

        // Generar filas (una por dia)
        data.days.forEach((dayName, dayIndex) => {
            const row = document.createElement('div');
            row.className = 'heatmap-row';

            // Label del dia
            const dayLabel = document.createElement('div');
            dayLabel.className = 'heatmap-day-label';
            dayLabel.textContent = dayName;
            row.appendChild(dayLabel);

            // Contenedor de celdas
            const cellsContainer = document.createElement('div');
            cellsContainer.className = 'heatmap-cells';

            // Generar 24 celdas (una por hora)
            for (let hour = 0; hour < 24; hour++) {
                const value = data.matrix[dayIndex][hour];
                const level = getLevel(value);

                const cell = document.createElement('div');
                cell.className = 'heatmap-cell';
                cell.dataset.level = level;
                cell.dataset.day = dayName;
                cell.dataset.hour = hour;
                cell.dataset.value = value;

                // Event listeners para tooltip
                cell.addEventListener('mouseenter', (e) => {
                    showHeatmapTooltip(e, dayName, hour, value);
                });
                cell.addEventListener('mouseleave', hideHeatmapTooltip);

                cellsContainer.appendChild(cell);
            }

            row.appendChild(cellsContainer);
            grid.appendChild(row);
        });

    } catch (error) {
        console.error('Error fetching heatmap data:', error);
    }
}

/**
 * Carga todos los graficos
 */
function loadAllCharts() {
    loadTrendChart();
    loadHourlyChart();
    loadDailyChart();
    loadArtistsChart();
    loadUsersChart();
    loadActiveUsersChart();
    loadHeatmap();
}

// ============================================
// COMPARADOR DE USUARIOS
// ============================================

/**
 * Carga la lista de usuarios para el comparador
 */
async function loadCompareUsers() {
    try {
        const response = await fetch('/api/users?limit=100');
        const data = await response.json();

        if (data.error || !data.users) return;

        const select1 = document.getElementById('compare-user1');
        const select2 = document.getElementById('compare-user2');

        if (!select1 || !select2) return;

        // Agregar opciones
        data.users.forEach(user => {
            const option1 = document.createElement('option');
            option1.value = user.id;
            option1.textContent = user.name;
            select1.appendChild(option1);

            const option2 = document.createElement('option');
            option2.value = user.id;
            option2.textContent = user.name;
            select2.appendChild(option2);
        });
    } catch (error) {
        console.error('Error loading users for compare:', error);
    }
}

/**
 * Compara dos usuarios
 */
async function compareUsers() {
    const user1 = document.getElementById('compare-user1')?.value;
    const user2 = document.getElementById('compare-user2')?.value;
    const content = document.getElementById('compare-content');

    if (!user1 || !user2) {
        content.innerHTML = '<div class="compare-placeholder">Selecciona dos usuarios para comparar</div>';
        return;
    }

    if (user1 === user2) {
        content.innerHTML = '<div class="compare-placeholder">Selecciona dos usuarios diferentes</div>';
        return;
    }

    content.innerHTML = '<div class="compare-loading">Cargando comparacion...</div>';

    try {
        const response = await fetch(`/api/compare/users?user1=${user1}&user2=${user2}&days=${currentRange}`);
        const data = await response.json();

        if (data.error) {
            content.innerHTML = `<div class="compare-placeholder">Error: ${data.error}</div>`;
            return;
        }

        // Determinar ganadores
        const u1 = data.user1;
        const u2 = data.user2;

        const renderUser = (user, isLeft) => {
            const avatarHtml = user.avatar_url
                ? `<img src="${escapeHtml(user.avatar_url)}" alt="${escapeHtml(user.name)}">`
                : user.name.charAt(0).toUpperCase();

            const playsWinner = user.total_plays > (isLeft ? u2 : u1).total_plays ? 'winner' : '';
            const timeWinner = user.total_time > (isLeft ? u2 : u1).total_time ? 'winner' : '';
            const tracksWinner = user.unique_tracks > (isLeft ? u2 : u1).unique_tracks ? 'winner' : '';
            const artistsWinner = user.unique_artists > (isLeft ? u2 : u1).unique_artists ? 'winner' : '';

            return `
                <div class="compare-user">
                    <div class="compare-user-header user-link" data-user="${escapeHtml(user.name)}">
                        <div class="compare-avatar">${avatarHtml}</div>
                        <div class="compare-user-name">${escapeHtml(user.name)}</div>
                    </div>
                    <div class="compare-stats">
                        <div class="compare-stat-row">
                            <span class="compare-stat-label">Reproducciones</span>
                            <span class="compare-stat-value ${playsWinner}">${formatNumber(user.total_plays)}</span>
                        </div>
                        <div class="compare-stat-row">
                            <span class="compare-stat-label">Tiempo</span>
                            <span class="compare-stat-value ${timeWinner}">${formatTime(user.total_time)}</span>
                        </div>
                        <div class="compare-stat-row">
                            <span class="compare-stat-label">Canciones unicas</span>
                            <span class="compare-stat-value ${tracksWinner}">${formatNumber(user.unique_tracks)}</span>
                        </div>
                        <div class="compare-stat-row">
                            <span class="compare-stat-label">Artistas</span>
                            <span class="compare-stat-value ${artistsWinner}">${formatNumber(user.unique_artists)}</span>
                        </div>
                        <div class="compare-stat-row">
                            <span class="compare-stat-label">Top Artista</span>
                            <span class="compare-stat-value">${escapeHtml(user.top_artist || '--')}</span>
                        </div>
                        <div class="compare-stat-row">
                            <span class="compare-stat-label">Top Cancion</span>
                            <span class="compare-stat-value">${escapeHtml(user.top_song || '--')}</span>
                        </div>
                        <div class="compare-stat-row">
                            <span class="compare-stat-label">Hora pico</span>
                            <span class="compare-stat-value">${user.peak_hour !== null ? user.peak_hour + ':00' : '--'}</span>
                        </div>
                    </div>
                </div>
            `;
        };

        // Texto del periodo
        const periodText = currentRange >= 365 ? 'Todo el tiempo' : `Ultimos ${currentRange} dias`;

        content.innerHTML = `
            <div class="compare-period-badge">Estadisticas de: ${periodText}</div>
            <div class="compare-results">
                ${renderUser(u1, true)}
                <div class="compare-center-vs">
                    <span class="vs-text">VS</span>
                </div>
                ${renderUser(u2, false)}
            </div>
        `;

        // Agregar click handlers para abrir perfil
        content.querySelectorAll('.compare-user-header.user-link').forEach(header => {
            header.addEventListener('click', () => {
                const userName = header.dataset.user;
                showUserProfile(userName);
            });
        });

    } catch (error) {
        console.error('Error comparing users:', error);
        content.innerHTML = '<div class="compare-placeholder">Error de conexion</div>';
    }
}

/**
 * Carga la lista de servidores para el filtro
 */
async function loadServerFilter() {
    try {
        const response = await fetch('/api/servers');
        const data = await response.json();

        if (data.error || !data.servers) return;

        const select = document.getElementById('server-filter');
        if (!select) return;

        // Agregar opciones de servidores
        data.servers.forEach(server => {
            const option = document.createElement('option');
            option.value = server.id;
            option.textContent = server.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading servers:', error);
    }
}

/**
 * Maneja el cambio de servidor
 */
function handleServerChange(event) {
    currentServer = event.target.value;
    loadAllCharts();
}

/**
 * Maneja el cambio de rango de tiempo general
 */
function handleRangeChange(event) {
    const btn = event.target;
    if (!btn.classList.contains('filter-btn')) return;

    // Actualizar botones activos
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Actualizar rango y recargar todos los graficos
    const range = btn.dataset.range;
    currentRange = range === 'all' ? 365 : parseInt(range);
    loadAllCharts();
}

// ============================================
// MODAL DE DETALLES DEL DIA
// ============================================

/**
 * Muestra el modal con detalles del dia
 */
async function showDayDetail(date, label) {
    const modal = document.getElementById('day-detail-modal');
    const title = document.getElementById('modal-title');
    const tableBody = document.getElementById('plays-table-body');
    const loading = document.getElementById('plays-loading');
    const empty = document.getElementById('plays-empty');

    // Mostrar modal
    modal.style.display = 'flex';
    title.textContent = `Reproducciones del ${label}`;
    tableBody.innerHTML = '';
    loading.style.display = 'block';
    empty.style.display = 'none';

    try {
        let url = `/api/stats/day-detail?date=${date}`;
        if (currentServer) {
            url += `&guild_id=${currentServer}`;
        }
        const response = await fetch(url);
        const data = await response.json();

        loading.style.display = 'none';

        if (data.error) {
            empty.textContent = 'Error al cargar datos';
            empty.style.display = 'block';
            return;
        }

        if (!data.plays || data.plays.length === 0) {
            empty.textContent = 'No hay reproducciones este dia';
            empty.style.display = 'block';
            return;
        }

        // Renderizar tabla con nombres clickeables
        tableBody.innerHTML = data.plays.map(play => {
            const listenersHtml = play.listeners_count > 0
                ? `<span class="listeners-tooltip" data-names="${play.listeners_names.join('\n')}">${play.listeners_count} oyente${play.listeners_count > 1 ? 's' : ''}</span>`
                : '<span class="listeners">-</span>';

            return `
                <tr>
                    <td class="time-col">${escapeHtml(play.time)}</td>
                    <td class="song-title" title="${escapeHtml(play.title)}">${escapeHtml(play.title)}</td>
                    <td class="artist-name" title="${escapeHtml(play.artist)}">${escapeHtml(play.artist)}</td>
                    <td class="requester"><span class="user-link" data-user="${escapeHtml(play.requester)}">${escapeHtml(play.requester)}</span></td>
                    <td class="listeners">${listenersHtml}</td>
                </tr>
            `;
        }).join('');

        // Agregar click handlers para usuarios
        tableBody.querySelectorAll('.user-link').forEach(link => {
            link.addEventListener('click', () => {
                const userName = link.dataset.user;
                closeModal();
                showUserProfile(userName);
            });
        });

    } catch (error) {
        console.error('Error loading day detail:', error);
        loading.style.display = 'none';
        empty.textContent = 'Error de conexion';
        empty.style.display = 'block';
    }
}

/**
 * Cierra el modal de reproducciones
 */
function closeModal() {
    const modal = document.getElementById('day-detail-modal');
    modal.style.display = 'none';
}

/**
 * Muestra el modal con usuarios activos del dia
 */
async function showActiveUsersDetail(date, label) {
    const modal = document.getElementById('users-detail-modal');
    const title = document.getElementById('users-modal-title');
    const tableBody = document.getElementById('users-table-body');
    const loading = document.getElementById('users-loading');
    const empty = document.getElementById('users-empty');

    // Mostrar modal
    modal.style.display = 'flex';
    title.textContent = `Usuarios activos - ${label}`;
    tableBody.innerHTML = '';
    loading.style.display = 'block';
    empty.style.display = 'none';

    try {
        let url = `/api/stats/active-users-detail?date=${date}`;
        if (currentServer) {
            url += `&guild_id=${currentServer}`;
        }
        const response = await fetch(url);
        const data = await response.json();

        loading.style.display = 'none';

        if (data.error) {
            empty.textContent = 'Error al cargar datos';
            empty.style.display = 'block';
            return;
        }

        if (!data.users || data.users.length === 0) {
            empty.textContent = 'No hay usuarios activos este dia';
            empty.style.display = 'block';
            return;
        }

        // Renderizar tabla con nombres clickeables
        tableBody.innerHTML = data.users.map(user => `
            <tr>
                <td><span class="user-link" data-user="${escapeHtml(user.name)}">${escapeHtml(user.name)}</span></td>
                <td>${user.plays}</td>
            </tr>
        `).join('');

        // Agregar click handlers
        tableBody.querySelectorAll('.user-link').forEach(link => {
            link.addEventListener('click', () => {
                const userName = link.dataset.user;
                closeUsersModal();
                showUserProfile(userName);
            });
        });

    } catch (error) {
        console.error('Error loading active users detail:', error);
        loading.style.display = 'none';
        empty.textContent = 'Error de conexion';
        empty.style.display = 'block';
    }
}

/**
 * Cierra el modal de usuarios
 */
function closeUsersModal() {
    const modal = document.getElementById('users-detail-modal');
    modal.style.display = 'none';
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

// Inicializar
document.addEventListener('DOMContentLoaded', () => {
    // Cargar lista de servidores, usuarios y graficos
    loadServerFilter();
    loadCompareUsers();
    loadAllCharts();

    // Event listener para filtro de servidor
    document.getElementById('server-filter')?.addEventListener('change', handleServerChange);

    // Event listener para filtro de tiempo
    document.querySelector('.time-filter')?.addEventListener('click', handleRangeChange);

    // Event listener para comparador
    document.getElementById('compare-btn')?.addEventListener('click', compareUsers);

    // Event listeners para toggles de promedio
    document.getElementById('hourly-avg-toggle')?.addEventListener('change', updateHourlyChart);
    document.getElementById('daily-avg-toggle')?.addEventListener('change', updateDailyChart);

    // Event listeners para el modal de reproducciones
    document.getElementById('modal-close')?.addEventListener('click', closeModal);
    document.getElementById('day-detail-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'day-detail-modal') {
            closeModal();
        }
    });

    // Event listeners para el modal de usuarios activos
    document.getElementById('users-modal-close')?.addEventListener('click', closeUsersModal);
    document.getElementById('users-detail-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'users-detail-modal') {
            closeUsersModal();
        }
    });

    // Inicializar modal de perfil (componente compartido)
    ProfileModal.init();

    // Cerrar modales con Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            closeUsersModal();
        }
    });

    // Detectar cambio de tema del sistema
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        // Recargar graficos para actualizar colores
        loadAllCharts();
    });
});
