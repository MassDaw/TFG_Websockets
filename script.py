import asyncio
import websockets

async def test_client():
    uri = "wss://tfg-websockets.onrender.com/ws"  # Cambia por tu URL real
    async with websockets.connect(uri) as websocket:
        message = await websocket.recv()
        print(f"Received: {message}")

asyncio.run(test_client())