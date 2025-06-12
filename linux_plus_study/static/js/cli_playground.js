class CLIPlayground {
    constructor() {
        this.commandHistory = [];
        this.historyIndex = -1;
        this.isProcessing = false;
        this.suggestions = [];
        this.currentSuggestionIndex = -1;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadAvailableCommands();
        this.focusInput();
        this.addWelcomeMessage();
    }
    
    bindEvents() {
        const input = document.getElementById('cliInput');
        if (!input) return;
        
        // Main input events
        input.addEventListener('keydown', (e) => this.handleKeyDown(e));
        input.addEventListener('input', (e) => this.handleInput(e));
        
        // Terminal click to focus
        const terminal = document.getElementById('cliTerminal');
        if (terminal) {
            terminal.addEventListener('click', () => this.focusInput());
        }
        
        // Global shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'l':
                        e.preventDefault();
                        this.clearTerminal();
                        break;
                    case 'r':
                        e.preventDefault();
                        this.resetPlayground();
                        break;
                }
            }
        });
    }
    
    handleKeyDown(e) {
        const input = e.target;
        
        switch(e.key) {
            case 'Enter':
                e.preventDefault();
                this.executeCommand();
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.navigateHistory('up');
                break;
                
            case 'ArrowDown':
                e.preventDefault();
                this.navigateHistory('down');
                break;
                
            case 'Tab':
                e.preventDefault();
                this.handleTabCompletion();
                break;
                
            case 'Escape':
                e.preventDefault();
                input.value = '';
                this.hideSuggestions();
                break;
        }
    }
    
    handleInput(e) {
        const input = e.target.value;
        this.showSuggestions(input);
    }
    
    executeCommand() {
        if (this.isProcessing) return;
        
        const input = document.getElementById('cliInput');
        const command = input.value.trim();
        
        if (!command) return;
        
        this.isProcessing = true;
        this.commandHistory.push(command);
        this.historyIndex = this.commandHistory.length;
        
        // Display command
        this.addToTerminal(`student@linux-study:~/sandbox$ ${command}`, 'command');
        this.showLoading(true);
        
        // Clear input
        input.value = '';
        this.hideSuggestions();
        
        // Execute command
        this.callAPI('/api/cli/execute', 'POST', { command })
            .then(data => {
                if (data.success) {
                    this.handleCommandResult(data);
                } else {
                    this.addToTerminal(data.error || 'Unknown error occurred', 'error');
                }
            })
            .catch(error => {
                this.addToTerminal(`Network error: ${error.message}`, 'error');
            })
            .finally(() => {
                this.showLoading(false);
                this.isProcessing = false;
                this.scrollToBottom();
                this.focusInput();
            });
    }
    
    handleCommandResult(data) {
        if (data.output === 'CLEAR_SCREEN') {
            this.clearTerminal();
        } else {
            if (data.output) {
                this.addToTerminal(data.output, 'result');
            }
            if (data.error) {
                this.addToTerminal(data.error, 'error');
            }
        }
    }
    
    addToTerminal(text, type) {
        const terminal = document.getElementById('cliTerminal');
        const inputLine = terminal.querySelector('.cli-input-line');
        
        const output = document.createElement('div');
        output.className = 'cli-output';
        
        // Format output based on type
        const formattedText = this.formatOutput(text, type);
        
        if (type === 'command') {
            output.innerHTML = `<div class="cli-command">${formattedText}</div>`;
        } else if (type === 'error') {
            output.innerHTML = `<div class="cli-error">${formattedText}</div>`;
        } else {
            output.innerHTML = `<div class="cli-result">${formattedText}</div>`;
        }
        
        terminal.insertBefore(output, inputLine);
    }
    
    formatOutput(text, type) {
        // Basic syntax highlighting for file listings
        if (type === 'result' && text.includes('  ')) {
            // Possible ls output
            return text.replace(/(\S+\.(txt|csv|md|log|json))/g, '<span class="cli-file-highlight">$1</span>');
        }
        
        // Escape HTML
        return text.replace(/&/g, '&amp;')
                  .replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;')
                  .replace(/"/g, '&quot;')
                  .replace(/'/g, '&#039;');
    }
    
    navigateHistory(direction) {
        const input = document.getElementById('cliInput');
        
        if (direction === 'up' && this.historyIndex > 0) {
            this.historyIndex--;
            input.value = this.commandHistory[this.historyIndex];
        } else if (direction === 'down') {
            if (this.historyIndex < this.commandHistory.length - 1) {
                this.historyIndex++;
                input.value = this.commandHistory[this.historyIndex];
            } else {
                this.historyIndex = this.commandHistory.length;
                input.value = '';
            }
        }
        
        // Move cursor to end
        input.setSelectionRange(input.value.length, input.value.length);
    }
    
    handleTabCompletion() {
        const input = document.getElementById('cliInput');
        const currentValue = input.value;
        const words = currentValue.split(' ');
        const lastWord = words[words.length - 1];
        
        // Simple command completion
        const matches = this.suggestions.filter(cmd => 
            cmd.toLowerCase().startsWith(lastWord.toLowerCase())
        );
        
        if (matches.length === 1) {
            words[words.length - 1] = matches[0];
            input.value = words.join(' ');
        } else if (matches.length > 1) {
            this.addToTerminal(`Possible completions: ${matches.join(', ')}`, 'result');
            this.scrollToBottom();
        }
    }
    
    showSuggestions(input) {
        // Simple suggestion system
        if (input.length > 0) {
            const matches = this.suggestions.filter(cmd => 
                cmd.toLowerCase().startsWith(input.toLowerCase())
            );
            
            if (matches.length > 0 && matches.length < 6) {
                // Could implement suggestion dropdown here
            }
        }
    }
    
    hideSuggestions() {
        // Hide any suggestion UI
    }
    
    clearTerminal() {
        const terminal = document.getElementById('cliTerminal');
        const outputs = terminal.querySelectorAll('.cli-output');
        outputs.forEach(output => output.remove());
        
        this.addWelcomeMessage();
        this.focusInput();
    }
    
    addWelcomeMessage() {
        this.addToTerminal('Terminal cleared.', 'result');
        this.addToTerminal('Type "help" to see available commands.', 'result');
    }
    
    showHistory() {
        this.callAPI('/api/cli/history')
            .then(data => {
                if (data.success) {
                    const content = document.getElementById('historyContent');
                    if (data.history.length === 0) {
                        content.innerHTML = '<em>No commands in history</em>';
                    } else {
                        content.innerHTML = data.history.map((cmd, index) => 
                            `<div style="margin: 5px 0; cursor: pointer; padding: 5px; border-radius: 3px;" 
                                  onclick="cliPlayground.insertCommand('${cmd.replace(/'/g, "\\'")}')"
                                  onmouseover="this.style.background='#e9ecef'"
                                  onmouseout="this.style.background='transparent'">
                                ${index + 1}. ${cmd}
                             </div>`
                        ).join('');
                    }
                    
                    const modal = new bootstrap.Modal(document.getElementById('historyModal'));
                    modal.show();
                }
            })
            .catch(error => {
                this.addToTerminal(`Error loading history: ${error.message}`, 'error');
            });
    }
    
    clearHistory() {
        this.callAPI('/api/cli/clear', 'POST')
            .then(data => {
                if (data.success) {
                    this.commandHistory = [];
                    this.historyIndex = -1;
                    document.getElementById('historyContent').innerHTML = '<em>History cleared</em>';
                    this.addToTerminal('Command history cleared.', 'result');
                }
            })
            .catch(error => {
                this.addToTerminal(`Error clearing history: ${error.message}`, 'error');
            });
    }
    
    resetPlayground() {
        if (confirm('Reset playground? This will clear the terminal and command history.')) {
            this.clearTerminal();
            this.clearHistory();
            this.addToTerminal('Playground reset. Welcome back!', 'result');
            this.addToTerminal('Type "help" to see available commands.', 'result');
        }
    }
    
    loadAvailableCommands() {
        this.callAPI('/api/cli/commands')
            .then(data => {
                if (data.success) {
                    this.suggestions = data.commands.map(cmd => cmd.command);
                    this.renderCommandGrid(data.commands);
                }
            })
            .catch(error => {
                console.error('Error loading commands:', error);
            });
    }
    
    renderCommandGrid(commands) {
        const grid = document.getElementById('commandGrid');
        if (!grid) return;
        
        grid.innerHTML = commands.map(cmd => `
            <div class="command-item" onclick="cliPlayground.insertCommand('${cmd.command}')">
                <div class="command-name">${cmd.command}</div>
                <div class="command-desc">${cmd.description}</div>
            </div>
        `).join('');
    }
    
    insertCommand(command) {
        const input = document.getElementById('cliInput');
        input.value = command;
        this.focusInput();
    }
    
    executeCommandDirect(command) {
        const input = document.getElementById('cliInput');
        input.value = command;
        this.executeCommand();
    }
    
    showHelp() {
        this.executeCommandDirect('help');
    }
    
    focusInput() {
        const input = document.getElementById('cliInput');
        if (input) {
            input.focus();
        }
    }
    
    scrollToBottom() {
        const terminal = document.getElementById('cliTerminal');
        if (terminal) {
            terminal.scrollTop = terminal.scrollHeight;
        }
    }
    
    showLoading(show) {
        const indicator = document.getElementById('loadingIndicator');
        if (indicator) {
            indicator.style.display = show ? 'block' : 'none';
        }
    }
    
    async callAPI(url, method = 'GET', data = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        return await response.json();
    }
}

// Global functions for backward compatibility
function clearTerminal() { if (window.cliPlayground) window.cliPlayground.clearTerminal(); }
function showHistory() { if (window.cliPlayground) window.cliPlayground.showHistory(); }
function showHelp() { if (window.cliPlayground) window.cliPlayground.showHelp(); }
function resetPlayground() { if (window.cliPlayground) window.cliPlayground.resetPlayground(); }
function clearHistory() { if (window.cliPlayground) window.cliPlayground.clearHistory(); }
function insertCommand(cmd) { if (window.cliPlayground) window.cliPlayground.insertCommand(cmd); }

// Initialize CLI Playground when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('cliTerminal')) {
        window.cliPlayground = new CLIPlayground();
    }
});