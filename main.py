import os
from flask import Flask
from flask_sock import Sock
import requests
import json
import time
from datetime import datetime

app = Flask(__name__)
sock = Sock(app)

# Configuración para API pública CON TU API KEY
COINGECKO_API = "https://api.coingecko.com/api/v3"
API_KEY = "CG-nPHmygxuwAQJZav58uztr463"  # Tu API key
UPDATE_INTERVAL = 30  # Puedes reducirlo ahora que tienes API key

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
        print("🔄 Obteniendo datos de CoinGecko con API key...")
        
        # Headers con tu API key
        headers = {
            'Accept': 'application/json',
            'x-cg-demo-api-key': API_KEY  # Tu API key aquí
        }
        
        print("📡 Solicitando datos globales...")
        global_response = requests.get(
            f"{COINGECKO_API}/global", 
            headers=headers, 
            timeout=15
        )
        print(f"🌐 Status global: {global_response.status_code}")
        global_response.raise_for_status()
        global_data = global_response.json()

        print("📡 Solicitando datos de monedas...")
        coins_response = requests.get(
            f"{COINGECKO_API}/coins/markets",
            params={
                "vs_currency": "eur",
                "order": "market_cap_desc",
                "per_page": 20,  # Ahora puedes usar 20 sin problemas
                "sparkline": False
            },
            headers=headers,
            timeout=15
        )
        print(f"💰 Status monedas: {coins_response.status_code}")
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

        result = {
            "type": "crypto",
            "market": market_data,
            "assets": assets
        }
        
        print(f"✅ Datos obtenidos con API key: {len(assets)} criptomonedas")
        return result
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error HTTP: {e}")
        if e.response:
            print(f"🔍 Status: {e.response.status_code}")
            print(f"🔍 Response: {e.response.text[:200]}...")
        return None
    except Exception as e:
        print(f"❌ Error general: {e}")
        return None

@sock.route('/ws')
def handle_websocket(ws):
    print("🔌 Cliente WebSocket conectado")
    try:
        while True:
            data = get_crypto_data()
            if data:
                ws.send(json.dumps(data))
                print(f"📤 Datos enviados: {len(data['assets'])} activos")
            else:
                error_msg = {"error": "No se pudieron obtener datos"}
                ws.send(json.dumps(error_msg))
                print("📤 Mensaje de error enviado")
            
            time.sleep(UPDATE_INTERVAL)
    except Exception as e:
        print(f"❌ Error en WebSocket: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🔌 Cliente WebSocket desconectado")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8001))
    print(f"🚀 Iniciando servidor WebSocket en puerto {port}...")
    print(f"🔑 Usando API key: CG-***{API_KEY[-10:]}")  # Mostrar solo los últimos caracteres
    app.run(host='0.0.0.0', port=port, debug=False)
