import asyncio
import websockets
import subprocess
import json

# Function to execute a Python script and stream its output
async def run_script(script_name):
    try:
        # Start the script as a subprocess
        process = subprocess.Popen(['python3', script_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Continuously read the output and send it to the client
        while True:
            output = process.stdout.readline().decode().strip()
            if output:
                yield output  # Send data back to the WebSocket
            if process.poll() is not None:
                break

        # Ensure any remaining output is processed
        remaining_output = process.stdout.read().decode().strip()
        if remaining_output:
            yield remaining_output

    except Exception as e:
        yield str(e)  # Send error message if script fails

# WebSocket handler for incoming messages
async def command_handler(websocket, path):
    async for message in websocket:
        # Parse the command from the mobile app
        data = json.loads(message)
        command = data.get('command')

        # Determine the script to run based on the command
        if command == "start_continuous_monitoring":
            script_name = 'test_app.py'
        elif command == "start_bpm_monitoring":
            script_name = 'heart_rate_monitor.py'
        elif command == "start_temperature_monitoring":
            script_name = 'temperature.py'
        elif command == "start_stress_monitoring":
            script_name = 'gsr.py'
        else:
            await websocket.send(json.dumps({"error": "Invalid command"}))
            continue

        # Execute the chosen script and send output back to the client
        async for output in run_script(script_name):
            await websocket.send(json.dumps({"data": output}))

# Start WebSocket server
async def start_server():
    async with websockets.serve(command_handler, "0.0.0.0", 8765):
        print("WebSocket server started on ws://0.0.0.0:8765")
        await asyncio.Future()  # Run indefinitely

# Run the server
asyncio.run(start_server())
