from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import os
import json
from bot import PopMartBot
import threading

# Global bot management
active_bots = []
bot_lock = threading.Lock()

# Project setup
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__,
            template_folder=os.path.join(PROJECT_ROOT, 'templates'),
            static_folder=os.path.join(PROJECT_ROOT, 'static'))
socketio = SocketIO(app)
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config', 'config.json')

@app.route('/')
def home():
    """Render main page"""
    return render_template('index.html')

@app.route('/add_account', methods=['POST'])
def add_account():
    """Add new account to config"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    payment = data.get('payment')

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"})

    if not payment:
        return jsonify({"success": False, "message": "Payment details are required"})

    required_payment_fields = ['card_number', 'expiry_month', 'expiry_year', 'holder_name', 'cvv']
    if not all(field in payment and payment[field] for field in required_payment_fields):
        return jsonify({"success": False, "message": "All payment fields are required"})

    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)

        accounts = config.get('accounts', [])
        if any(acc['email'] == email for acc in accounts):
            return jsonify({"success": False, "message": "Account already exists"})

        new_account = {
            "email": email,
            "password": password,
            "payment": {
                "card_number": payment['card_number'],
                "expiry_month": payment['expiry_month'],
                "expiry_year": payment['expiry_year'],
                "holder_name": payment['holder_name'],
                "cvv": payment['cvv']
            }
        }

        accounts.append(new_account)
        config['accounts'] = accounts

        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)

        return jsonify({"success": True, "message": "Account added successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to add account: {str(e)}"})

@app.route('/stop', methods=['POST'])
def stop_bot():
    """Stop all active bot instances"""
    global active_bots
    with bot_lock:
        if not active_bots:
            return jsonify({"success": False, "message": "No bots running"})
        
        for bot in active_bots:
            try:
                bot._running = False
                if bot.driver:
                    bot.driver.quit()
            except Exception as e:
                print(f"Error stopping bot: {e}")
        
        active_bots = []
        return jsonify({"success": True, "message": "All bots stopped"})

@app.route('/start', methods=['POST'])
def start_bot():
    """Start new bot instance"""
    print('request received to backend')
    global active_bots
    data = request.get_json()

    # Validate input
    product_url = data.get('product_url')
    quantity = data.get('quantity')
    action = data.get('action')

    if not all([product_url, quantity, action]):
        return jsonify({"success": False, "message": "Missing required parameters"})

    try:
        # Create new bot instance with first account
        bot = PopMartBot(socketio=socketio, account_index=0)

        def run_bot():
            global active_bots
            try:
                with bot_lock:
                    active_bots.append(bot)
                
                bot.run(product_url, action, quantity)
            except Exception as e:
                bot.log(f"Bot error: {str(e)}")
            finally:
                with bot_lock:
                    if bot in active_bots:
                        active_bots.remove(bot)
                    if bot.driver:
                        bot.driver.quit()

        # Start in new thread
        threading.Thread(target=run_bot).start()
        return jsonify({"success": True, "message": "Bot started"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to start bot: {str(e)}"})

if __name__ == '__main__':
    print(f"Template folder: {app.template_folder}")
    print(f"Static folder: {app.static_folder}")
    socketio.run(app, debug=True, host='0.0.0.0', port=9899)