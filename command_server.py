import asyncio
import websockets
import json
import subprocess
import os

# Define the path to the virtual environment Python interpreter
VENV_PYTHON = "/home/pi/PatientConditionProject/venv/bin/python3"

test_app_process = None

async def command_handler(websocket, _):
    global test_app_process

    try:
        async for message in websocket:
            print(f"Received message: {message}")
            if not message:
                continue

            try:
                data = json.loads(message)
                command = data.get("command")

                if command == "START_MONITORING":
                    print("Start monitoring command received")
                    # Start `test_app.py` with virtual environment's Python interpreter
                    if test_app_process is None or test_app_process.poll() is not None:
                        test_app_process = subprocess.Popen(
                            [VENV_PYTHON, "test_app.py"],
                            cwd="/home/pi/PatientConditionProject"
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

    except websockets.ConnectionClosedError:
        print("WebSocket connection closed unexpectedly.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Ensure `test_app.py` is terminated if the client disconnects
        if test_app_process and test_app_process.poll() is None:
            test_app_process.terminate()
            test_app_process = None
            print("test_app.py terminated due to client disconnection.")

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
        if test_app_process:
            test_app_process.terminate()
            print("test_app.py terminated due to server shutdown.")
