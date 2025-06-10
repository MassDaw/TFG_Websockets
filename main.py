from gevent import monkey
monkey.patch_all()

import os
from flask import Flask, jsonify
from flask_sock import Sock
import requests
import json
import time
from datetime import datetime
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
import asyncio
import websockets

app = Flask(__name__)
sock = Sock(app)

# Configuración para API pública
COINGECKO_API = "https://api.coingecko.com/api/v3"
UPDATE_INTERVAL = 30  # segundos

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
    print("WebSocket connection established")  # Add this line
    while True:
        data = get_crypto_data()
        if data:
            print("Sending data:", data)  # Add this line
            ws.send(json.dumps(data))
        time.sleep(UPDATE_INTERVAL)

@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200

async def test_client():
    uri = "ws://localhost:8001/ws"  # Replace with your local address
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                print(f"Received: {message}")
            except websockets.exceptions.ConnectionClosedOK:
                break
            except Exception as e:
                print(f"Error: {e}")
                break

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8001))
    # Usa WSGIServer para servir la app con soporte WebSocket y HTTP
    server = WSGIServer(('0.0.0.0', port), app, handler_class=WebSocketHandler)
    server.serve_forever()
#    asyncio.run(test_client())  # No ejecutes el cliente aquí