// WebSocket connection for real-time logs
const socket = io('http://65.1.64.161:9899');

// DOM Elements
const addAccountBtn = document.getElementById('add-account-btn');
const startBotBtn = document.getElementById('start-bot-btn');
const logContainer = document.getElementById('log-output');

// Add new account
addAccountBtn.addEventListener('click', async () => {
    const email = document.getElementById('new-email').value;
    const password = document.getElementById('new-password').value;
    const card_number = document.getElementById('card_number').value;
    const expiry_month = parseInt(document.getElementById('expiry_month').value);
    const expiry_year = parseInt(document.getElementById('expiry_year').value);
    const holder_name = document.getElementById('holder_name').value;
    const cvv = document.getElementById('cvv').value;

    if (!email || !password) {
        addLog('Error: Email and password are required');
        return;
    }

    if (!card_number || !expiry_month || !expiry_year || !holder_name || !cvv) {
        addLog('Error: All payment details are required');
        return;
    }

    try {
        const response = await fetch('http://65.1.64.161:9899/add_account', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                email, 
                password,
                payment: {
                    card_number,
                    expiry_month,
                    expiry_year,
                    holder_name,
                    cvv
                }
            })
        });
        
        const result = await response.json();
        if (result.success) {
            addLog(`Account added: ${email}`);
            // Clear form
            document.getElementById('new-email').value = '';
            document.getElementById('new-password').value = '';
            document.getElementById('card_number').value = '';
            document.getElementById('expiry_month').value = '';
            document.getElementById('expiry_year').value = '';
            document.getElementById('holder_name').value = '';
            document.getElementById('cvv').value = '';
        } else {
            addLog(`Error: ${result.message || 'Failed to add account'}`);
        }
    } catch (error) {
        addLog(`Network error: ${error.message}`);
    }
});

// Start the bot
startBotBtn.addEventListener('click', async (event) => {
    event.preventDefault();
    console.log("start button called")
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

  // timeout helper
  const fetchWithTimeout = (url, options = {}, timeout = 9899) =>
    Promise.race([
      fetch(url, options),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Request timed out')), timeout)
      )
    ]);

  const response = await fetchWithTimeout('http://65.1.64.161:9899/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_url: productUrl,
      quantity,
      action
    })
  }, 10000); // 10s timeout

  console.log('Fetch request sent, waiting for JSON response.');

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const result = await response.json();

  if (result.success) {
    addLog('Initializing Bot............');
  } else {
    addLog(`Error: ${result.message || 'Bot failed to initialize'}`);
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
            const response = await fetch('http://65.1.64.161:9899/stop', {
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

// Clear logs button
document.getElementById('clear-logs-btn').addEventListener('click', () => {
    document.getElementById('log-output').innerHTML = '';
    addLog('Logs cleared');
});

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    addLog('System initialized. Ready to start.');
});