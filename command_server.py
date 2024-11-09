import asyncio
import websockets
import subprocess
import json

# Function to execute `test_app.py` as a subprocess
async def start_test_app():
    process = subprocess.Popen(['python3', 'test_app.py'])
    return process

# WebSocket handler for incoming messages
async def command_handler(websocket, path):
    global process
    async for message in websocket:
        # Parse the command from the app
        data = json.loads(message)
        command = data.get("command")

        if command == "START_MONITORING":
            process = await start_test_app()
            await websocket.send(json.dumps({"status": "Monitoring started"}))
        elif command == "STOP_MONITORING":
            if process:
                process.terminate()  # Stop the process
                await websocket.send(json.dumps({"status": "Monitoring stopped"}))
        else:
            await websocket.send(json.dumps({"error": "Invalid command"}))

# Start WebSocket server
async def start_server():
    async with websockets.serve(command_handler, "0.0.0.0", 8765):
        print("WebSocket server started on ws://0.0.0.0:8765")
        await asyncio.Future()  # Run indefinitely

# Run the server
try:
    asyncio.run(start_server())
except KeyboardInterrupt:
    print("Server stopped.")
