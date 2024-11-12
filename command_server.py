import asyncio
import websockets
import json
import subprocess

# Global variables to retain the last known BPM and Temperature values
last_bpm_value = 0.0
last_temperature_value = 0.0

# Function to start a specific systemd service
def start_service(service_name):
    """
    Starts the specified systemd service using systemctl.
    """
    try:
        subprocess.run(["sudo", "systemctl", "start", service_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting {service_name} service: {e}")

# Function to stop a specific systemd service
def stop_service(service_name):
    """
    Stops the specified systemd service using systemctl.
    """
    try:
        subprocess.run(["sudo", "systemctl", "stop", service_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error stopping {service_name} service: {e}")

# Function to send real-time data to the Flutter app
async def send_data(websocket, page):
    """
    Continuously reads data from respective files and sends it to the client.
    Falls back to the last known values if file read fails.
    """
    global last_bpm_value, last_temperature_value
    while True:
        try:
            if page == "BPM":
                with open("/home/pi/PatientConditionProject/bpm_data.txt", "r") as f:
                    bpm_value = f.read().strip()
                last_bpm_value = float(bpm_value)  # Update the last known BPM value
                data = {"BPM": last_bpm_value}
            elif page == "Temperature":
                with open("/home/pi/PatientConditionProject/temperature_data.txt", "r") as f:
                    temperature_value = f.read().strip()
                last_temperature_value = float(temperature_value)  # Update the last known Temperature value
                data = {"Temperature": last_temperature_value}
            else:
                data = {}

        except (FileNotFoundError, ValueError):
            # Use the last known value if file read fails
            data = {"BPM": last_bpm_value} if page == "BPM" else {"Temperature": last_temperature_value}

        await websocket.send(json.dumps(data))  # Send data to Flutter app
        await asyncio.sleep(1)  # Frequency of data updates; adjust as needed
        
# WebSocket handler for managing incoming commands from the client
async def command_handler(websocket, _):
    """
    Handles WebSocket commands from the Flutter app to start/stop monitoring.
    Controls systemd services and manages real-time data streaming tasks.
    """
    active_service = None  # Track the currently active service
    data_task = None  # Task for sending data to the client

    try:
        async for message in websocket:
            # Parse the JSON command from the client
            data = json.loads(message)
            command = data.get("command")
            page = data.get("page")

            # Map pages to systemd services
            service_map = {
                "BPM": "heart_rate_monitor.service",
                "Temperature": "temperature_monitor.service",
                "Stress": "gsr_monitor.service",
                "Continuous": "test_app.service"
            }
            service_name = service_map.get(page)

            if command == "START_MONITORING" and service_name:
                # Stop the previously active service if it’s different from the requested one
                if active_service and active_service != service_name:
                    stop_service(active_service)
                # Start the requested service
                start_service(service_name)
                active_service = service_name  # Update the active service tracker
                await websocket.send(json.dumps({"status": f"Started monitoring for {page}"}))
                
                # Start a background task to send data continuously to the Flutter app
                if data_task is None or data_task.done():
                    data_task = asyncio.create_task(send_data(websocket))

            elif command == "STOP_MONITORING" and active_service == service_name:
                # Stop the active monitoring service
                stop_service(service_name)
                await websocket.send(json.dumps({"status": f"Stopped monitoring for {page}"}))
                active_service = None  # Clear the active service tracker

            elif command == "EXIT_PAGE" and active_service:
                # If the user navigates away, stop the active service
                stop_service(active_service)
                await websocket.send(json.dumps({"status": "Exited page, stopped monitoring"}))
                active_service = None  # Clear the active service tracker

            else:
                # Send an error message if an unknown command or page is received
                await websocket.send(json.dumps({"error": "Unknown command or page"}))

    except websockets.ConnectionClosedError:
        print("WebSocket connection closed unexpectedly.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Ensure any active service is stopped if the connection is closed
        if active_service:
            stop_service(active_service)
        # Cancel the data streaming task if the WebSocket connection closes
        if data_task:
            data_task.cancel()

# Function to start the WebSocket server
async def start_server():
    """
    Starts the WebSocket server to listen for connections from the Flutter app.
    """
    async with websockets.serve(command_handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Keeps the server running indefinitely

# Entry point to run the WebSocket server
if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("Server stopped.")
