import asyncio
import websockets
import json
import subprocess

# Global variables to retain the last known values for each metric as floats
last_bpm_value = 0.0
last_temperature_value = 0.0

# Function to start a specific systemd service
def start_service(service_name):
    try:
        subprocess.run(["sudo", "systemctl", "start", service_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting {service_name} service: {e}")

# Function to stop a specific systemd service
def stop_service(service_name):
    try:
        subprocess.run(["sudo", "systemctl", "stop", service_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error stopping {service_name} service: {e}")

# Function to send data based on the active monitoring page
async def send_data(websocket, active_page):
    global last_bpm_value, last_temperature_value
    while True:
        try:
            # Read and send data for BPM or Temperature based on the active page
            if active_page == "BPM":
                with open("/home/pi/PatientConditionProject/bpm_data.txt", "r") as f:
                    last_bpm_value = float(f.read().strip())
                data = {"BPM": round(last_bpm_value, 3)}  # Send as float with 3 decimal places
            elif active_page == "Temperature":
                with open("/home/pi/PatientConditionProject/temperature_data.txt", "r") as f:
                    last_temperature_value = float(f.read().strip())
                data = {"Temperature": round(last_temperature_value, 3)}  # Send as float with 3 decimal places
            else:
                # Send the last known values even if the monitoring is stopped
                if active_page == "BPM":
                    data = {"BPM": round(last_bpm_value, 3)}
                elif active_page == "Temperature":
                    data = {"Temperature": round(last_temperature_value, 3)}
                else:
                    data = {}  # No data if there's no active monitoring page

            await websocket.send(json.dumps(data))  # Send data to the client
            await asyncio.sleep(1)  # Adjust frequency as needed
        except (FileNotFoundError, ValueError):
            # Send the last known value if file read fails
            if active_page == "BPM":
                await websocket.send(json.dumps({"BPM": round(last_bpm_value, 3)}))
            elif active_page == "Temperature":
                await websocket.send(json.dumps({"Temperature": round(last_temperature_value, 3)}))

# WebSocket handler for managing incoming commands from the client
async def command_handler(websocket, _):
    active_service = None  # Track the currently active service
    data_task = None       # Task for streaming data
    active_page = None     # Track the active page

    try:
        async for message in websocket:
            # Parse JSON command from the client
            data = json.loads(message)
            command = data.get("command")
            page = data.get("page")

            # Map pages to systemd services
            service_map = {
                "BPM": "heart_rate_monitor.service",
                "Temperature": "temperature_monitor.service",
            }
            service_name = service_map.get(page)

            # Handle START_MONITORING command
            if command == "START_MONITORING" and service_name:
                # Stop any previously active service if different from the requested one
                if active_service and active_service != service_name:
                    stop_service(active_service)

                # Start the requested service and update active page/service
                start_service(service_name)
                active_service = service_name
                active_page = page

                # Start background task to send data to the client
                if data_task is None or data_task.done():
                    data_task = asyncio.create_task(send_data(websocket, active_page))

                await websocket.send(json.dumps({"status": f"Started monitoring for {page}"}))

            # Handle STOP_MONITORING command
            elif command == "STOP_MONITORING" and active_service == service_name:
                stop_service(service_name)
                active_service = None
                # Do not reset active_page so that the last value can still be displayed
                # Cancel data streaming task if it exists
                if data_task:
                    data_task.cancel()
                    # Restart the task to keep sending the last known value
                    data_task = asyncio.create_task(send_data(websocket, active_page))

                await websocket.send(json.dumps({"status": f"Stopped monitoring for {page}"}))

            # Handle EXIT_PAGE command to stop active service when exiting the page
            elif command == "EXIT_PAGE" and active_service:
                stop_service(active_service)
                active_service = None
                active_page = None

                # Cancel data streaming task if it exists
                if data_task:
                    data_task.cancel()

                await websocket.send(json.dumps({"status": "Exited page, stopped monitoring"}))

            else:
                # Send an error message for unknown command or page
                await websocket.send(json.dumps({"error": "Unknown command or page"}))

    except websockets.ConnectionClosedError:
        print("WebSocket connection closed unexpectedly.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Stop the active service and cancel the data task if WebSocket closes
        if active_service:
            stop_service(active_service)
        if data_task:
            data_task.cancel()

# Function to start the WebSocket server
async def start_server():
    async with websockets.serve(command_handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Keeps the server running indefinitely

# Entry point to run the WebSocket server
if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("Server stopped.")
