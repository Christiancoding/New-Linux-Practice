// Global app functionality
document.addEventListener('DOMContentLoaded', function() {
    // Update active nav link
    updateActiveNavLink();
});

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

// Utility functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.insertBefore(alertDiv, document.body.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}
function exportHistory() {
    const link = document.createElement('a');
    link.href = '/api/export_history';
    link.download = `linux_plus_export_${new Date().toISOString().slice(0,10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showAlert('Study history export started', 'info');
}
function importHistory() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = function(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                fetch('/api/import_history', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                }).then(response => {
                    if (response.ok) {
                        showAlert('Study history imported successfully', 'success');
                    } else {
                        showAlert('Failed to import study history', 'danger');
                    }
                });
            } catch (error) {
                showAlert('Invalid file format', 'danger');
            }
        };
        
        reader.readAsText(file);
    };
    
    input.click();
}
function clearHistory() {
    if (confirm('Are you sure you want to clear your study history? This action cannot be undone.')) {
        fetch('/api/clear_history', { method: 'POST' })
            .then(response => {
                if (response.ok) {
                    showAlert('Study history cleared successfully', 'success');
                } else {
                    showAlert('Failed to clear study history', 'danger');
                }
            });
    }
}
function toggleDarkMode() {
    const body = document.body;
    body.classList.toggle('dark-mode');
    
    // Save preference in localStorage
    if (body.classList.contains('dark-mode')) {
        localStorage.setItem('darkMode', 'enabled');
    } else {
        localStorage.setItem('darkMode', 'disabled');
    }
}
// Check for saved dark mode preference
document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('darkMode') === 'enabled') {
        document.body.classList.add('dark-mode');
    }
});
// Toggle dark mode on button click
document.getElementById('darkModeToggle').addEventListener('click', toggleDarkMode);
// Add event listeners for export, import, and clear history buttons
document.getElementById('exportHistoryBtn').addEventListener('click', exportHistory);
document.getElementById('importHistoryBtn').addEventListener('click', importHistory);
document.getElementById('clearHistoryBtn').addEventListener('click', clearHistory);
// Add event listener for search functionality
document.getElementById('searchInput').addEventListener('input', function() {
    const query = this.value.toLowerCase();
    const items = document.querySelectorAll('.searchable-item');
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(query)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
});
// ADD these functions to handle missing web functionality:

// Settings management
function saveSettings() {
    const settings = {
        focusMode: document.getElementById('focusMode')?.checked || false,
        breakReminder: document.getElementById('breakReminder')?.value || 10
    };
    localStorage.setItem('studySettings', JSON.stringify(settings));
    showAlert('Settings saved', 'success');
}

function loadSettings() {
    const settings = JSON.parse(localStorage.getItem('studySettings') || '{}');
    if (document.getElementById('focusMode')) {
        document.getElementById('focusMode').checked = settings.focusMode || false;
    }
    if (document.getElementById('breakReminder')) {
        document.getElementById('breakReminder').value = settings.breakReminder || 10;
    }
}

// Enhanced navigation
function updateActiveNavigation() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// Auto-save quiz progress
function autoSaveQuizProgress() {
    // Implement auto-save functionality for web
    const quizState = {
        mode: currentMode,
        timestamp: Date.now()
    };
    sessionStorage.setItem('quizProgress', JSON.stringify(quizState));
}

// ADD to DOMContentLoaded:
document.addEventListener('DOMContentLoaded', function() {
    updateActiveNavigation();
    loadSettings();
    
    // Auto-save settings when changed
    document.getElementById('focusMode')?.addEventListener('change', saveSettings);
    document.getElementById('breakReminder')?.addEventListener('change', saveSettings);
});
// Settings management (fixed version)
function saveSettings() {
    const settings = {
        focusMode: document.getElementById('focusMode')?.checked || false,
        breakReminder: parseInt(document.getElementById('breakReminder')?.value) || 10,
        timestamp: Date.now()
    };
    
    try {
        localStorage.setItem('studySettings', JSON.stringify(settings));
        showAlert('Settings saved successfully!', 'success');
    } catch (error) {
        console.error('Failed to save settings:', error);
        showAlert('Failed to save settings', 'danger');
    }
}

function loadSettings() {
    try {
        const settings = JSON.parse(localStorage.getItem('studySettings') || '{}');
        
        if (document.getElementById('focusMode')) {
            document.getElementById('focusMode').checked = settings.focusMode || false;
        }
        if (document.getElementById('breakReminder')) {
            document.getElementById('breakReminder').value = settings.breakReminder || 10;
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

// Auto-save settings when changed
document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    
    // Add event listeners for auto-save
    const focusModeEl = document.getElementById('focusMode');
    const breakReminderEl = document.getElementById('breakReminder');
    
    if (focusModeEl) {
        focusModeEl.addEventListener('change', saveSettings);
    }
    if (breakReminderEl) {
        breakReminderEl.addEventListener('change', saveSettings);
    }
});

// Performance improvements
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

// Debounced status updates
const debouncedUpdateStatus = debounce(updateStatus, 250);
// Improved settings management
function saveSettings() {
    try {
        // Test localStorage availability
        if (typeof(Storage) === "undefined") {
            showAlert('Your browser does not support local storage. Settings cannot be saved.', 'warning');
            return;
        }
        
        const settings = {
            focusMode: document.getElementById('focusMode')?.checked || false,
            breakReminder: parseInt(document.getElementById('breakReminder')?.value) || 10,
            timestamp: Date.now(),
            version: '1.0'
        };
        
        // Test write access
        const testKey = 'test_' + Date.now();
        localStorage.setItem(testKey, 'test');
        localStorage.removeItem(testKey);
        
        // Save actual settings
        localStorage.setItem('studySettings', JSON.stringify(settings));
        showAlert('Settings saved successfully!', 'success');
        
    } catch (error) {
        console.error('Failed to save settings:', error);
        if (error.name === 'QuotaExceededError') {
            showAlert('Storage quota exceeded. Please clear some browser data.', 'danger');
        } else if (error.name === 'SecurityError') {
            showAlert('Settings cannot be saved in private/incognito mode.', 'warning');
        } else {
            showAlert('Failed to save settings: ' + error.message, 'danger');
        }
    }
}

function loadSettings() {
    try {
        if (typeof(Storage) === "undefined") {
            return; // Silently fail if no storage support
        }
        
        const settingsStr = localStorage.getItem('studySettings');
        if (!settingsStr) {
            return; // No settings saved yet
        }
        
        const settings = JSON.parse(settingsStr);
        
        if (document.getElementById('focusMode')) {
            document.getElementById('focusMode').checked = settings.focusMode || false;
        }
        if (document.getElementById('breakReminder')) {
            document.getElementById('breakReminder').value = settings.breakReminder || 10;
        }
        
    } catch (error) {
        console.error('Failed to load settings:', error);
        // Clear corrupted settings
        try {
            localStorage.removeItem('studySettings');
        } catch (e) {
            // Ignore cleanup errors
        }
    }
}

// Performance optimizations
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

// Optimize API calls
const debouncedStatusUpdate = debounce(function() {
    updateGameStatus();
}, 500);

// Improved error handling for showAlert
function showAlert(message, type = 'info') {
    try {
        // Remove any existing alerts first
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
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
        
    } catch (error) {
        console.error('Failed to show alert:', error);
        // Fallback to browser alert
        alert(message);
    }
}