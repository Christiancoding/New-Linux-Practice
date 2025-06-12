// Global app functionality
document.addEventListener('DOMContentLoaded', function() {
    // Update active nav link on every page
    updateActiveNavLink();

    // If we are on the settings page, load the settings from the server
    if (window.location.pathname.includes('settings')) {
        loadSettings();
    }
});

/**
 * Updates the active state of the main navigation links based on the current URL path.
 */
function updateActiveNavLink() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

/**
 * Displays a dismissible alert message to the user.
 * @param {string} message - The message to display.
 * @param {string} type - The alert type (e.g., 'success', 'danger', 'info').
 */
function showAlert(message, type = 'info') {
    try {
        // Remove any existing alerts to prevent stacking
        const existingAlerts = document.querySelectorAll('.alert.position-fixed');
        existingAlerts.forEach(alert => alert.remove());

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        `;

        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        document.body.appendChild(alertDiv);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                const bsAlert = new bootstrap.Alert(alertDiv);
                if (bsAlert) {
                    bsAlert.close();
                } else {
                    alertDiv.remove();
                }
            }
        }, 5000);

    } catch (error) {
        console.error('Failed to show alert:', error);
        // Fallback to browser alert if the custom one fails
        alert(message);
    }
}

// --- Settings Management (API-driven) ---

/**
 * Saves settings to the backend by calling the /api/save_settings endpoint.
 */
function saveSettings() {
    const focusModeEl = document.getElementById('focusMode');
    const breakReminderEl = document.getElementById('breakReminder');

    if (!focusModeEl || !breakReminderEl) {
        console.error('Settings elements not found on this page.');
        return;
    }

    const settings = {
        focusMode: focusModeEl.checked,
        breakReminder: parseInt(breakReminderEl.value) || 10
    };

    fetch('/api/save_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Settings saved successfully!', 'success');
        } else {
            showAlert('Failed to save settings: ' + (data.error || 'Unknown server error'), 'danger');
        }
    })
    .catch(error => {
        console.error('Error saving settings:', error);
        showAlert('An error occurred while saving settings.', 'danger');
    });
}

/**
 * Loads settings from the backend and populates the form on the settings page.
 */
function loadSettings() {
    const focusModeEl = document.getElementById('focusMode');
    const breakReminderEl = document.getElementById('breakReminder');

    // Only run if the settings elements exist on the page
    if (!focusModeEl || !breakReminderEl) {
        return;
    }

    fetch('/api/load_settings')
    .then(response => response.json())
    .then(data => {
        if (data.success && data.settings) {
            focusModeEl.checked = data.settings.focusMode || false;
            breakReminderEl.value = data.settings.breakReminder || 10;
        } else {
             showAlert('Could not load current settings from server.', 'warning');
        }
    })
    .catch(error => {
        console.error('Error loading settings:', error);
        showAlert('An error occurred while loading settings.', 'danger');
    });
}

/**
 * Initiates the export of study history by redirecting to the API endpoint.
 */
function exportHistory() {
    // This creates a link and clicks it to trigger the download from the backend endpoint
    const link = document.createElement('a');
    link.href = '/api/export_history';
    link.download = `linux_plus_export_${new Date().toISOString().slice(0,10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showAlert('Study history export started.', 'info');
}

/**
 * Initiates clearing of all statistics after user confirmation.
 */
function clearHistory() {
    if (confirm('Are you sure you want to clear ALL study history? This action cannot be undone.')) {
        fetch('/api/clear_statistics', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Study history cleared successfully!', 'success');
                } else {
                    showAlert('Failed to clear study history: ' + (data.error || 'Unknown error'), 'danger');
                }
            })
            .catch(error => {
                showAlert('Failed to clear study history', 'danger');
            });
    }
}