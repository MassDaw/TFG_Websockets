from gevent import monkey
monkey.patch_all()

import os
from flask import Flask
from flask_sock import Sock
import requests
import json
import time
from datetime import datetime

app = Flask(__name__)
sock = Sock(app)

# Configuración para API pública
COINGECKO_API = "https://api.coingecko.com/api/v3"
UPDATE_INTERVAL = 30  # segundos

print("Starting WebSocket Crypto Server...")
print(f"Port: {os.environ.get('PORT', 8001)}")

@app.route('/')
def index():
    print("Index route accessed")
    return {
        'status': 'WebSocket Crypto Server Running',
        'endpoints': {
            'websocket': '/ws',
            'health': '/health'
        },
        'timestamp': datetime.now().isoformat()
    }

@app.route('/health')
def health():
    print("Health route accessed")
    return {
        'status': 'ok', 
        'timestamp': datetime.now().isoformat(),
        'websocket_endpoint': '/ws'
    }

def format_number(number):
    if number is None:
        return "€0.00"
    try:
        number = float(number)
        if number >= 1_000_000_000:
            return f"€{number/1_000_000_000:.2f}B"
        elif number >= 1_000_000:
            return f"€{number/1_000_000:.2f}M"
        else:
            return f"€{number:,.2f}"
    except (TypeError, ValueError):
        return "€0.00"

def get_crypto_data():
    try:
        global_response = requests.get(f"{COINGECKO_API}/global")
        global_response.raise_for_status()
        global_data = global_response.json()

        coins_response = requests.get(
            f"{COINGECKO_API}/coins/markets",
            params={
                "vs_currency": "eur",
                "order": "market_cap_desc",
                "per_page": 50,
                "sparkline": False
            }
        )
        coins_response.raise_for_status()
        coins = coins_response.json()

        # Validación de datos globales
        market_cap = global_data.get("data", {}).get("total_market_cap", {}).get("eur", 0)
        volume_24h = global_data.get("data", {}).get("total_volume", {}).get("eur", 0)

        market_data = {
            "marketCap": format_number(market_cap),
            "volume24h": format_number(volume_24h),
            "lastUpdated": datetime.now().strftime("%H:%M:%S")
        }

        assets = [{
            "id": coin.get("id", ""),
            "name": coin.get("name", ""),
            "symbol": coin.get("symbol", "").upper(),
            "price": format_number(coin.get("current_price")),
            "volume": format_number(coin.get("total_volume")),
            "isFavorite": False
        } for coin in coins if coin]

        return {
            "type": "crypto",
            "market": market_data,
            "assets": assets
        }
    except Exception as e:
        print(f"Error obteniendo datos: {e}")
        return None

@sock.route('/ws')
def handle_websocket(ws):
    print("WebSocket connection established")
    try:
        while True:
            data = get_crypto_data()
            if data:
                ws.send(json.dumps(data))
                print("Data sent to WebSocket client")
            time.sleep(UPDATE_INTERVAL)
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8001))
    print(f"Starting Flask server on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)