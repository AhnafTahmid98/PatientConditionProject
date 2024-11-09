import asyncio
import websockets
import json

async def command_handler(websocket, path):
    async for message in websocket:
        if not message:
            print("Received an empty message, skipping...")
            continue
        try:
            data = json.loads(message)
            command = data.get("command")

            if command == "START_MONITORING":
                print("Start monitoring command received")
                await websocket.send(json.dumps({"status": "Monitoring started"}))
            elif command == "STOP_MONITORING":
                print("Stop monitoring command received")
                await websocket.send(json.dumps({"status": "Monitoring stopped"}))
            else:
                print("Unknown command received")
                await websocket.send(json.dumps({"error": "Unknown command"}))

        except json.JSONDecodeError:
            print("Failed to decode JSON, invalid message received.")
            await websocket.send(json.dumps({"error": "Invalid JSON format"}))

async def start_server():
    async with websockets.serve(command_handler, "0.0.0.0", 8765):
        print("WebSocket server started on ws://0.0.0.0:8765")
        await asyncio.Future()  # Run forever

try:
    asyncio.run(start_server())
except KeyboardInterrupt:
    print("Server stopped.")
