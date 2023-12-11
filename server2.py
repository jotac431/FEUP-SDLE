import zmq
import json
from common_server import *

if __name__ == "__main__":
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5557")

    shopping_lists = []  # Server 2's shopping_lists storage

    while True:
        message = socket.recv_string()  # Receive string message from the client
        response = {}
        
        try:
            if message == "PING":  # Handle the "PING" message separately
                # Respond to the client to confirm server connectivity
                socket.send_string("PONG")
                continue  # Skip JSON deserialization for "PING" messages
            
            try:
                received_json = json.loads(message)  # Attempt JSON deserialization
                if isinstance(received_json, dict):
                    action = received_json.get("action")
            
                    if action == "create":
                        response = handle_create(received_json, shopping_lists)
                    elif action == "get_list_contents":
                        response = handle_get_list_contents(received_json, shopping_lists)
                    elif action == "sync_with_server":
                        response = handle_sync(received_json, shopping_lists)
                    
                    socket.send_json(response)
                else:
                    logger.error("Received message is not a dictionary")
                    response["status"] = "error"
                    response["message"] = "Invalid message format"
                    socket.send_json(response)
            except json.JSONDecodeError:
                logger.error("Received invalid JSON message")
                response["status"] = "error"
                response["message"] = "Invalid JSON format"
                socket.send_json(response)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            response["status"] = "error"
            response["message"] = "Internal server error"
            socket.send_json(response)
