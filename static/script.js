// WebSocket connection for real-time logs
const socket = io('http://127.0.0.1:5000');

// DOM Elements
const addAccountBtn = document.getElementById('add-account-btn');
const startBotBtn = document.getElementById('start-bot-btn');
const logContainer = document.getElementById('log-output');

// Add new account
addAccountBtn.addEventListener('click', async () => {
    const email = document.getElementById('new-email').value;
    const password = document.getElementById('new-password').value;

    if (!email || !password) {
        addLog('Error: Email and password are required');
        return;
    }

    try {
        const response = await fetch('http://127.0.0.1:5000/add_account', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const result = await response.json();
        if (result.success) {
            addLog(`Account added: ${email}`);
            // Clear form
            document.getElementById('new-email').value = '';
            document.getElementById('new-password').value = '';
        } else {
            addLog(`Error: ${result.message || 'Failed to add account'}`);
        }
    } catch (error) {
        addLog(`Network error: ${error.message}`);
    }
});

// Start the bot
startBotBtn.addEventListener('click', async () => {
    const productUrl = document.getElementById('product-url').value;
    const quantity = parseInt(document.getElementById('quantity').value);
    const action = document.getElementById('action').value;

    if (!productUrl || !quantity) {
        addLog('Error: Product URL and quantity are required');
        return;
    }

    try {
        addLog('Starting bot...');
        console.log('Attempting to send fetch request to /start');
        const response = await fetch('http://127.0.0.1:5000/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                product_url: productUrl, 
                quantity, 
                action 
            })
        });
        console.log('Fetch request sent, waiting for JSON response.');
        const result = await response.json();
        if (result.success) {
            addLog('Bot completed successfully');
        } else {
            addLog(`Error: ${result.message || 'Bot failed to complete'}`);
        }
    } catch (error) {
        addLog(`Network error: ${error.message}`);
    }
});

// Stop the bot
const stopBotBtn = document.getElementById('stop-bot-btn');
if (stopBotBtn) {  // Check if stop button exists
    stopBotBtn.addEventListener('click', async () => {
        try {
            addLog('Stopping bot...');
            const response = await fetch('http://127.0.0.1:5000/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const result = await response.json();
            if (result.success) {
                addLog('Bot stopped successfully');
            } else {
                addLog(`Error: ${result.message || 'Failed to stop bot'}`);
            }
        } catch (error) {
            addLog(`Network error: ${error.message}`);
        }
    });
}

// WebSocket message handler
socket.on('log', (message) => {
    addLog(message);
});

// Helper function to add logs
function addLog(message) {
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.textContent = message;
    logContainer.appendChild(logEntry);
    // Auto-scroll to bottom
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    addLog('System initialized. Ready to start.');
});