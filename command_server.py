import asyncio
import websockets
import json
import subprocess

# Function to start a specific systemd service
def start_service(service_name):
    """
    Starts the specified systemd service using systemctl.
    """
    try:
        subprocess.run(["sudo", "systemctl", "start", service_name], check=True)
        print(f"Started {service_name} service.")  # Debugging: Confirm service start
    except subprocess.CalledProcessError as e:
        print(f"Error starting {service_name} service: {e}")

# Function to stop a specific systemd service
def stop_service(service_name):
    """
    Stops the specified systemd service using systemctl.
    """
    try:
        subprocess.run(["sudo", "systemctl", "stop", service_name], check=True)
        print(f"Stopped {service_name} service.")  # Debugging: Confirm service stop
    except subprocess.CalledProcessError as e:
        print(f"Error stopping {service_name} service: {e}")

# WebSocket handler to manage incoming commands from the client (Flutter app)
async def command_handler(websocket, _):
    """
    Handles incoming WebSocket messages from the client.
    Controls starting and stopping systemd services based on the commands
    received from the client.
    """
    active_service = None  # Track the currently active service

    try:
        async for message in websocket:
            data = json.loads(message)  # Decode the JSON message from the client
            command = data.get("command")  # Get the command (e.g., START_MONITORING)
            page = data.get("page")  # Get the page (e.g., BPM)

            # Debugging: Log received command and page for verification
            print(f"Received command: {command} for page: {page}")

            # Map page names to systemd service names
            service_map = {
                "BPM": "heart_rate_monitor.service",
                "Temperature": "temperature_monitor.service",
                "Stress": "gsr_monitor.service",
                "Continuous": "test_app.service"
            }
            service_name = service_map.get(page)  # Determine the service name based on page

            if command == "START_MONITORING" and service_name:
                # Start the requested service if not already active
                if active_service and active_service != service_name:
                    stop_service(active_service)  # Stop any previously running service
                start_service(service_name)
                active_service = service_name  # Track the newly active service
                print(f"Started monitoring service: {service_name}")  # Debugging: Confirm start
                await websocket.send(json.dumps({"status": f"Started monitoring for {page}"}))

            elif command == "STOP_MONITORING" and active_service == service_name:
                # Stop the currently active service if it matches the requested service
                stop_service(service_name)
                print(f"Stopped monitoring service: {service_name}")  # Debugging: Confirm stop
                await websocket.send(json.dumps({"status": f"Stopped monitoring for {page}"}))
                active_service = None  # Clear the active service tracker

            elif command == "EXIT_PAGE" and active_service:
                # Stop the active service if the user navigates away from the page
                stop_service(active_service)
                print(f"Exited page, stopped service: {active_service}")  # Debugging: Confirm exit
                await websocket.send(json.dumps({"status": "Exited page, stopped monitoring"}))
                active_service = None  # Clear the active service tracker

            else:
                # Handle unknown commands or unsupported pages
                await websocket.send(json.dumps({"error": "Unknown command or page"}))

    except websockets.ConnectionClosedError:
        print("WebSocket connection closed unexpectedly.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Ensure any active service is stopped if the connection is closed
        if active_service:
            stop_service(active_service)

# Function to start the WebSocket server
async def start_server():
    """
    Starts the WebSocket server, which listens for incoming connections from the Flutter app.
    """
    async with websockets.serve(command_handler, "0.0.0.0", 8765):
        print("Command server started on ws://0.0.0.0:8765")
        await asyncio.Future()  # Keeps the server running indefinitely

# Main entry point for the script
if __name__ == "__main__":
    try:
        asyncio.run(start_server())  # Start the WebSocket server
    except KeyboardInterrupt:
        print("Server stopped.")
