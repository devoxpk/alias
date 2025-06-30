from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import os
import json
from bot import PopMartBot
import threading

# Global bot instance
bot = None
bot_lock = threading.Lock()

# Get the absolute path to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__,
            template_folder=os.path.join(PROJECT_ROOT, 'templates'),
            static_folder=os.path.join(PROJECT_ROOT, 'static'))
socketio = SocketIO(app)

# Config path - now using proper path joining
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config', 'config.json')

@app.route('/')
def home():
    """Render the main page"""
    return render_template('index.html')  # Let Flask handle the path automatically

@app.route('/add_account', methods=['POST'])
def add_account():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"})

    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)

        accounts = config.get('accounts', [])
        # Check if account already exists
        if any(acc['email'] == email for acc in accounts):
            return jsonify({"success": False, "message": "Account already exists"})

        accounts.append({"email": email, "password": password})
        config['accounts'] = accounts

        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)

        return jsonify({"success": True, "message": "Account added successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to add account: {str(e)}"})

@app.route('/stop', methods=['POST'])
def stop_bot():
    global bot
    with bot_lock:
        if bot:
            bot.stop()
            bot = None
            return jsonify({"success": True, "message": "Bot stopped"})
        return jsonify({"success": False, "message": "No bot running"})

@app.route('/start', methods=['POST'])
def start_bot():
    global bot
    data = request.get_json()

    # Check if bot is already running
    with bot_lock:
        if bot:
            return jsonify({"success": False, "message": "Bot is already running"})

    # Validate input
    product_url = data.get('product_url')
    quantity = data.get('quantity')
    action = data.get('action')

    if not all([product_url, quantity, action]):
        return jsonify({"success": False, "message": "Missing required parameters"})

    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        accounts = config.get('accounts', [])
        if not accounts:
            return jsonify({"success": False, "message": "No accounts configured"})
        email = accounts[0].get('email')
        password = accounts[0].get('password')
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to load accounts: {str(e)}"})

    bot = PopMartBot(socketio=socketio)

    def run_bot():
        global bot
        try:
            bot.run(product_url, action, quantity, email=email, password=password)
        except Exception as e:
            bot.log(f"Bot error: {str(e)}")
        finally:
                with bot_lock:
                    bot = None

    threading.Thread(target=run_bot).start()

    return jsonify({"success": True, "message": "Bot started"})

if __name__ == '__main__':
    print(f"Template folder: {app.template_folder}")
    print(f"Static folder: {app.static_folder}")
    socketio.run(app, debug=True, port=5000)
