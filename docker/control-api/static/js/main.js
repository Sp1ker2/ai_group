// Main JavaScript for Telegram Farm Control Panel

// Utility functions
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    try {
        const date = new Date(dateString);
        return date.toLocaleString('ru-RU');
    } catch {
        return dateString;
    }
}

function showNotification(message, type = 'info') {
    // Простое уведомление через alert
    // Можно заменить на более красивое решение
    alert(message);
}

// API helpers
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Auto-refresh functionality
let autoRefreshIntervals = {};

function startAutoRefresh(key, callback, interval = 30000) {
    if (autoRefreshIntervals[key]) {
        clearInterval(autoRefreshIntervals[key]);
    }
    
    autoRefreshIntervals[key] = setInterval(callback, interval);
    callback(); // Call immediately
}

function stopAutoRefresh(key) {
    if (autoRefreshIntervals[key]) {
        clearInterval(autoRefreshIntervals[key]);
        delete autoRefreshIntervals[key];
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Telegram Farm Control Panel loaded');
    
    // Add any global initialization here
});





