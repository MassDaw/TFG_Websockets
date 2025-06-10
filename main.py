from gevent import monkey
monkey.patch_all()

import os
from flask import Flask
from flask_socketio import SocketIO, emit
import requests
import json
import time
from datetime import datetime
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuración para API pública
COINGECKO_API = "https://api.coingecko.com/api/v3"
UPDATE_INTERVAL = 30  # segundos

print("Starting WebSocket Crypto Server...")
print(f"Port: {os.environ.get('PORT', 8001)}")

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Crypto WebSocket Test</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .connected { background-color: #d4edda; color: #155724; }
            .disconnected { background-color: #f8d7da; color: #721c24; }
            pre { background-color: #f8f9fa; padding: 10px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>Crypto WebSocket Server</h1>
        <div id="status" class="status disconnected">Desconectado</div>
        <button onclick="connect()">Conectar</button>
        <button onclick="disconnect()">Desconectar</button>
        <h2>Datos en tiempo real:</h2>
        <div id="data"></div>
        
        <script>
            let socket;
            
            function connect() {
                socket = io();
                
                socket.on('connect', function() {
                    document.getElementById('status').innerHTML = 'Conectado - Recibiendo datos cada 30 segundos';
                    document.getElementById('status').className = 'status connected';
                    console.log('Conectado al servidor');
                });
                
                socket.on('crypto_update', function(data) {
                    document.getElementById('data').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    console.log('Datos recibidos:', data);
                });
                
                socket.on('disconnect', function() {
                    document.getElementById('status').innerHTML = 'Conexión cerrada';
                    document.getElementById('status').className = 'status disconnected';
                    console.log('Desconectado del servidor');
                });
            }
            
            function disconnect() {
                if (socket) {
                    socket.disconnect();
                }
            }
            
            // Auto conectar al cargar la página
            connect();
        </script>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return {
        'status': 'ok', 
        'timestamp': datetime.now().isoformat(),
        'websocket_endpoint': '/socket.io'
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

def send_crypto_updates():
    """Función que envía actualizaciones periódicas"""
    while True:
        try:
            data = get_crypto_data()
            if data:
                socketio.emit('crypto_update', data)
                print("Data sent to all clients")
            time.sleep(UPDATE_INTERVAL)
        except Exception as e:
            print(f"Error en send_crypto_updates: {e}")
            time.sleep(5)

@socketio.on('connect')
def handle_connect():
    print('Cliente conectado')
    # Enviar datos inmediatamente al conectar
    data = get_crypto_data()
    if data:
        emit('crypto_update', data)

@socketio.on('disconnect')
def handle_disconnect():
    print('Cliente desconectado')

if __name__ == '__main__':
    # Iniciar el hilo para envío periódico de datos
    update_thread = threading.Thread(target=send_crypto_updates, daemon=True)
    update_thread.start()
    
    port = int(os.environ.get("PORT", 8001))
    print(f"Starting SocketIO server on 0.0.0.0:{port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)