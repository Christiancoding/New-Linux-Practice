// Global app functionality
document.addEventListener('DOMContentLoaded', function() {
    // Update active nav link on every page
    updateActiveNavLink();

    // If we are on the settings page, load the settings from the server
    if (window.location.pathname.includes('settings')) {
        loadSettings();
        // Add event listeners for auto-saving settings on change
        const focusModeEl = document.getElementById('focusMode');
        const breakReminderEl = document.getElementById('breakReminder');

        if (focusModeEl) {
            focusModeEl.addEventListener('change', saveSettings);
        }
        if (breakReminderEl) {
            breakReminderEl.addEventListener('change', saveSettings);
        }
    }

    // Check for saved dark mode preference
    if (localStorage.getItem('darkMode') === 'enabled') {
        document.body.classList.add('dark-mode');
    }

    // Add event listeners for buttons if they exist
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', toggleDarkMode);
    }

    const exportHistoryBtn = document.getElementById('exportHistoryBtn');
    if (exportHistoryBtn) {
        exportHistoryBtn.addEventListener('click', exportHistory);
    }

    const importHistoryBtn = document.getElementById('importHistoryBtn');
    if (importHistoryBtn) {
        importHistoryBtn.addEventListener('click', importHistory);
    }

    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearHistory);
    }
    
    // Add event listener for search functionality if it exists
    const searchInput = document.getElementById('searchInput');
    if(searchInput) {
        searchInput.addEventListener('input', function() {
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
    }
});
function getNextQuestion() {
    fetch('/api/get_question')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert('Error: ' + data.error, 'danger');
                return;
            }

            if (data.quiz_complete) {
                endQuiz();
                return;
            }

            // Check for break reminder
            if (data.break_reminder) {
                showBreakReminder(data.questions_since_break, data.break_interval);
                return;
            }

            // Normal question display
            displayQuestion(data);
        })
        .catch(error => {
            console.error('Error getting next question:', error);
            showAlert('Failed to get next question', 'danger');
        });
}
function showBreakReminder(questionsSinceBreak, breakInterval) {
    // Create break reminder modal
    const modalHtml = `
        <div class="modal fade" id="breakReminderModal" tabindex="-1" aria-labelledby="breakReminderModalLabel" aria-hidden="true" data-bs-backdrop="static" data-bs-keyboard="false">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content bg-dark">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title text-info" id="breakReminderModalLabel">
                            <i class="fas fa-coffee"></i> Time for a Break!
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <div class="mb-3">
                            <i class="fas fa-clock text-warning" style="font-size: 3rem;"></i>
                        </div>
                        <p class="mb-3">You've answered <strong>${questionsSinceBreak}</strong> questions.</p>
                        <p class="mb-3">Take a moment to rest your eyes and stretch!</p>
                        <div id="breakTimer" class="mb-3">
                            <div class="h4 text-info" id="timerDisplay">02:00</div>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar bg-info" role="progressbar" style="width: 100%" id="timerProgress"></div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary justify-content-center">
                        <button type="button" class="btn btn-primary" onclick="skipBreak()">
                            <i class="fas fa-forward"></i> Skip Break
                        </button>
                        <button type="button" class="btn btn-success" onclick="takeBreak()" id="takeBreakBtn">
                            <i class="fas fa-play"></i> Start Break
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('breakReminderModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('breakReminderModal'));
    modal.show();
}

function takeBreak() {
    const takeBreakBtn = document.getElementById('takeBreakBtn');
    const timerDisplay = document.getElementById('timerDisplay');
    const timerProgress = document.getElementById('timerProgress');
    
    takeBreakBtn.disabled = true;
    takeBreakBtn.innerHTML = '<i class="fas fa-pause"></i> Taking Break...';
    
    let breakDuration = 120; // 2 minutes in seconds
    let remainingTime = breakDuration;
    
    const countdown = setInterval(() => {
        const minutes = Math.floor(remainingTime / 60);
        const seconds = remainingTime % 60;
        
        timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        const progress = ((breakDuration - remainingTime) / breakDuration) * 100;
        timerProgress.style.width = progress + '%';
        
        remainingTime--;
        
        if (remainingTime < 0) {
            clearInterval(countdown);
            endBreak();
        }
    }, 1000);
}

function skipBreak() {
    acknowledgeBreak();
}

function endBreak() {
    showAlert('Break time is over! Ready to continue?', 'success');
    acknowledgeBreak();
}

function acknowledgeBreak() {
    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('breakReminderModal'));
    if (modal) {
        modal.hide();
    }
    
    // Remove modal from DOM
    setTimeout(() => {
        const modalElement = document.getElementById('breakReminderModal');
        if (modalElement) {
            modalElement.remove();
        }
    }, 300);
    
    // Notify backend that break was acknowledged
    fetch('/api/acknowledge_break', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Continue with next question
            getNextQuestion();
        } else {
            showAlert('Error acknowledging break', 'danger');
        }
    })
    .catch(error => {
        console.error('Error acknowledging break:', error);
        // Continue anyway
        getNextQuestion();
    });
}

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

// --- History Management (Import/Export/Clear) ---

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
 * Handles the import of study history from a JSON file.
 */
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
                         // Optionally, refresh the page or statistics view
                    } else {
                        showAlert('Failed to import study history', 'danger');
                    }
                });
            } catch (error) {
                showAlert('Invalid file format. Please select a valid JSON file.', 'danger');
            }
        };
        
        reader.readAsText(file);
    };
    
    input.click();
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
                console.error('Error clearing history:', error);
                showAlert('Failed to clear study history', 'danger');
            });
    }
}

/**
 * Toggles dark mode for the application and saves the user's preference.
 */
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

// --- Performance Utilities ---

/**
 * Creates a debounced function that delays invoking `func` until after `wait` milliseconds have elapsed
 * since the last time the debounced function was invoked.
 * @param {Function} func - The function to debounce.
 * @param {number} wait - The number of milliseconds to delay.
 * @returns {Function} The new debounced function.
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