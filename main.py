import asyncio
import json
import os
import requests
from datetime import datetime
import websockets

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
        global_response = requests.get(f"{COINGECKO_API}/global", timeout=10)
        global_response.raise_for_status()
        global_data = global_response.json()

        coins_response = requests.get(
            f"{COINGECKO_API}/coins/markets",
            params={
                "vs_currency": "eur",
                "order": "market_cap_desc",
                "per_page": 50,
                "sparkline": False
            },
            timeout=10
        )
        coins_response.raise_for_status()
        coins = coins_response.json()

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

async def handler(websocket, path):
    while True:
        data = get_crypto_data()
        if data:
            await websocket.send(json.dumps(data))
        await asyncio.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    print(f"Servidor WebSocket escuchando en el puerto {port}")
    
    asyncio.run(websockets.serve(handler, "0.0.0.0", port))