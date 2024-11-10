import asyncio
import websockets
import json
import subprocess
import os

# Store the process running `test_app.py`
test_app_process = None

async def command_handler(websocket, path):
    global test_app_process

    async for message in websocket:
        print(f"Received message: {message}")
        if not message:
            continue

        try:
            data = json.loads(message)
            command = data.get("command")

            if command == "START_MONITORING":
                print("Start monitoring command received")
                
                # Start `test_app.py` if it's not already running
                if test_app_process is None or test_app_process.poll() is not None:
                    test_app_process = subprocess.Popen(
                        ["python3", "test_app.py"],
                        cwd="/home/pi/PatientConditionProject"  # Make sure this path is correct
                    )
                    await websocket.send(json.dumps({"status": "Monitoring started"}))
                    print("test_app.py started.")
                else:
                    await websocket.send(json.dumps({"status": "Already running"}))
                    print("test_app.py is already running.")

            elif command == "STOP_MONITORING":
                print("Stop monitoring command received")
                
                # Terminate `test_app.py` if it’s running
                if test_app_process and test_app_process.poll() is None:
                    test_app_process.terminate()
                    test_app_process = None
                    await websocket.send(json.dumps({"status": "Monitoring stopped"}))
                    print("test_app.py stopped.")
                else:
                    await websocket.send(json.dumps({"status": "Not running"}))
                    print("test_app.py was not running.")

            else:
                print("Unknown command received")
                await websocket.send(json.dumps({"error": "Unknown command"}))

        except json.JSONDecodeError:
            print("Failed to decode JSON, invalid message received.")
            await websocket.send(json.dumps({"error": "Invalid JSON format"}))

async def start_server():
    async with websockets.serve(command_handler, "0.0.0.0", 8765):
        print("Command server started on ws://0.0.0.0:8765")
        await asyncio.Future()  # Run indefinitely

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("Server stopped.")
    finally:
        # Ensure `test_app.py` is terminated if the server stops
        if test_app_process:
            test_app_process.terminate()
            print("test_app.py terminated due to server shutdown.")
