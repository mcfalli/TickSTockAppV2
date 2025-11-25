/**
 * Admin WebSocket Monitor
 *
 * Real-time dashboard for monitoring multi-connection WebSocket architecture.
 * Displays connection status, configuration, and live tick streams for all
 * three WebSocket connections.
 *
 * Features:
 * - Real-time tick updates via Socket.IO
 * - Connection status monitoring
 * - Pause/resume controls
 * - Metrics updates every 5 seconds
 * - Memory management (max 50 ticks per stream)
 */

class AdminWebSocketMonitor {
    constructor() {
        this.socket = null;
        this.isPaused = false;
        this.tickBuffer = [];
        this.maxTicksPerStream = 50;
    }

    initialize() {
        this.socket = io('/admin-ws');

        this.setupSocketHandlers();
        this.setupUIControls();

        console.log('Admin WebSocket Monitor initialized');
    }

    setupSocketHandlers() {
        this.socket.on('connect', () => {
            this.updateConnectionStatus(true);
            console.log('Connected to /admin-ws');
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus(false);
            console.log('Disconnected from /admin-ws');
        });

        this.socket.on('connection_status_update', (data) => {
            this.handleConnectionStatusUpdate(data);
        });

        this.socket.on('tick_update', (tick) => {
            if (!this.isPaused) {
                this.handleTickUpdate(tick);
            } else {
                this.tickBuffer.push(tick);
            }
        });

        this.socket.on('metrics_update', (metrics) => {
            this.handleMetricsUpdate(metrics);
        });

        this.socket.on('error', (error) => {
            console.error('WebSocket error:', error);
        });
    }

    setupUIControls() {
        const pauseBtn = document.getElementById('pauseBtn');
        pauseBtn.addEventListener('click', () => {
            this.togglePause();
        });

        const refreshBtn = document.getElementById('refreshBtn');
        refreshBtn.addEventListener('click', () => {
            this.socket.emit('request_metrics');
        });
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');

        if (connected) {
            indicator.style.color = '#28a745';
            statusText.textContent = 'Connected to WebSocket';
        } else {
            indicator.style.color = '#dc3545';
            statusText.textContent = 'Disconnected from WebSocket';
        }
    }

    handleConnectionStatusUpdate(data) {
        const connections = data.connections || {};

        ['connection_1', 'connection_2', 'connection_3'].forEach((connId, index) => {
            const suffix = index + 1;
            const conn = connections[connId] || {};

            this.updateStatusBadge(suffix, conn.status);

            document.getElementById(`name${suffix}`).textContent = conn.name || '-';
            document.getElementById(`universe${suffix}`).textContent =
                conn.universe_key || conn.symbols?.join(', ') || '-';
            document.getElementById(`tickerCount${suffix}`).textContent =
                conn.assigned_tickers || 0;

            document.getElementById(`msgCount${suffix}`).textContent =
                conn.message_count || 0;
            document.getElementById(`errors${suffix}`).textContent =
                conn.error_count || 0;

            this.updateUptime(suffix, conn.last_message_time);
        });
    }

    updateStatusBadge(suffix, status) {
        const badge = document.getElementById(`status${suffix}`);

        badge.className = 'badge rounded-pill';

        if (status === 'connected') {
            badge.classList.add('text-bg-success');
            badge.textContent = 'Connected';
        } else if (status === 'disconnected') {
            badge.classList.add('text-bg-danger');
            badge.textContent = 'Disconnected';
        } else if (status === 'error') {
            badge.classList.add('text-bg-warning');
            badge.textContent = 'Error';
        } else {
            badge.classList.add('text-bg-secondary');
            badge.textContent = 'Disabled';
        }
    }

    handleTickUpdate(tick) {
        const connId = tick.connection_id || 'connection_1';
        const suffix = connId.replace('connection_', '');
        const stream = document.getElementById(`tickerStream${suffix}`);

        if (!stream) return;

        const tickEl = document.createElement('div');
        tickEl.className = 'ticker-item';

        const timestamp = new Date(tick.timestamp * 1000).toLocaleTimeString();
        const price = typeof tick.price === 'number' ? tick.price.toFixed(2) : tick.price;

        tickEl.innerHTML = `
            <strong>${tick.symbol}</strong>
            <span class="float-end text-muted">${timestamp}</span><br>
            <span>$${price}</span>
            <span class="text-muted ms-2">Vol: ${tick.volume || 0}</span>
        `;

        if (stream.firstChild) {
            stream.insertBefore(tickEl, stream.firstChild);
        } else {
            stream.appendChild(tickEl);
        }

        while (stream.children.length > this.maxTicksPerStream) {
            stream.removeChild(stream.lastChild);
        }

        const waitingMsg = stream.querySelector('.text-muted.py-4');
        if (waitingMsg) {
            waitingMsg.remove();
        }
    }

    handleMetricsUpdate(metrics) {
        Object.keys(metrics).forEach(connId => {
            const suffix = connId.replace('connection_', '');
            const conn = metrics[connId];

            document.getElementById(`throughput${suffix}`).textContent =
                conn.messages_per_second?.toFixed(1) || '0';

            document.getElementById(`msgCount${suffix}`).textContent =
                conn.message_count || 0;

            document.getElementById(`errors${suffix}`).textContent =
                conn.error_count || 0;
        });
    }

    updateUptime(suffix, lastMessageTime) {
        if (!lastMessageTime) {
            document.getElementById(`uptime${suffix}`).textContent = '-';
            return;
        }

        const now = Date.now() / 1000;
        const uptimeSeconds = now - lastMessageTime;

        if (uptimeSeconds < 60) {
            document.getElementById(`uptime${suffix}`).textContent = `${Math.floor(uptimeSeconds)}s`;
        } else if (uptimeSeconds < 3600) {
            document.getElementById(`uptime${suffix}`).textContent = `${Math.floor(uptimeSeconds / 60)}m`;
        } else {
            document.getElementById(`uptime${suffix}`).textContent =
                `${Math.floor(uptimeSeconds / 3600)}h ${Math.floor((uptimeSeconds % 3600) / 60)}m`;
        }
    }

    togglePause() {
        this.isPaused = !this.isPaused;
        const pauseBtn = document.getElementById('pauseBtn');

        if (this.isPaused) {
            pauseBtn.innerHTML = '<i class="fas fa-play"></i> Resume Updates';
            pauseBtn.classList.remove('btn-warning');
            pauseBtn.classList.add('btn-success');
        } else {
            pauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause Updates';
            pauseBtn.classList.remove('btn-success');
            pauseBtn.classList.add('btn-warning');

            this.tickBuffer.forEach(tick => this.handleTickUpdate(tick));
            this.tickBuffer = [];
        }
    }
}
