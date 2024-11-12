import asyncio
import websockets
import json
import subprocess

# Function to start a specific systemd service
def start_service(service_name):
    """
    Starts the specified systemd service.
    """
    try:
        subprocess.run(["sudo", "systemctl", "start", service_name], check=True)
        print(f"Started {service_name} service.")
    except subprocess.CalledProcessError as e:
        print(f"Error starting {service_name} service: {e}")

# Function to stop a specific systemd service
def stop_service(service_name):
    """
    Stops the specified systemd service.
    """
    try:
        subprocess.run(["sudo", "systemctl", "stop", service_name], check=True)
        print(f"Stopped {service_name} service.")
    except subprocess.CalledProcessError as e:
        print(f"Error stopping {service_name} service: {e}")

# Function to simulate sending data to the client
async def send_data(websocket, service_name):
    """
    Sends mock data to the client through the WebSocket connection.
    Replace with real data streaming in production.
    """
    last_data = {"status": f"Last data from {service_name}"}  # Placeholder for real data
    while True:
        await websocket.send(json.dumps(last_data))  # Send data to the client
        await asyncio.sleep(1)  # Adjust frequency of data updates

# WebSocket handler to manage incoming commands from the client (Flutter app)
async def command_handler(websocket, _):
    """
    Manages WebSocket commands from the client. Handles starting and stopping
    systemd services based on commands and active page in the app.
    """
    active_service = None  # Track the currently active service
    try:
        async for message in websocket:
            data = json.loads(message)  # Decode the JSON message from the client
            command = data.get("command")  # Get the command (START/STOP)
            page = data.get("page")  # Get the page, which specifies the service to control

            # Map page names from the client to systemd service names
            service_map = {
                "BPM": "heart_rate_monitor.service",
                "Temperature": "temperature_monitor.service",
                "Stress": "gsr_monitor.service",
                "Continuous": "test_app.service"
            }
            service_name = service_map.get(page)  # Get the service name based on the page

            if command == "START_MONITORING" and service_name:
                # Start the requested service and send confirmation to the client
                if active_service:
                    stop_service(active_service)  # Stop any previously running service
                start_service(service_name)  # Start the requested service
                active_service = service_name  # Update active service tracker
                await websocket.send(json.dumps({"status": f"Started monitoring for {page}"}))
                await send_data(websocket, service_name)  # Start sending data to the client

            elif command == "STOP_MONITORING" and service_name:
                # Stop the currently running service and confirm to the client
                stop_service(service_name)
                active_service = None  # Clear active service tracker
                await websocket.send(json.dumps({"status": f"Stopped monitoring for {page}"}))

            elif command == "EXIT_PAGE" and active_service:
                # If user navigates away, stop the currently active service
                stop_service(active_service)
                active_service = None  # Clear active service tracker
                await websocket.send(json.dumps({"status": "Exited page, stopped monitoring"}))

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