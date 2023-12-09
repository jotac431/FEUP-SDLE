import zmq
import uuid
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5556")  # Bind to all network interfaces on port 5556

# Data storage
shopping_lists = []

class LWWRegister:
    def __init__(self, quantity=0, item_name='', time=0, client_id=''):
        self.state = {'item_name': item_name, 'quantity': quantity, 'time': time, 'client_id': client_id}
    
    
    def merge(self, remote):
        if self.state['time'] < remote['time']:
            self.state = remote
        if self.state['time'] == remote['time']:
            if self.state['client_id'] < remote['client_id']:
                self.state = remote
        
class LWWMap:
    def __init__(self):
        self.map_list = {}

    def merge(self, remote):
        for k in remote:
            item_name = k['item_name']
            if self.map_list.get(item_name):
                print("Existent item. Merging...")
                self.map_list[item_name].merge(k)
            else:
                print("Found new item. Adding instance...")
                # Create a new LWWRegister instance and assign it to the item_name key
                self.map_list[item_name] = LWWRegister(**k)

        
class ShoppingList:
    def __init__(self, name):
        self.id = str(uuid.uuid4())
        self.name = name
        self.list = LWWMap()
        
def handle_create(message):
    list_name = message.get("list_name")
    print("Creating store named " + list_name)
    response = {}
    
    new_list = ShoppingList(list_name)
    shopping_lists.append(new_list)
    response["success"] = True
    response["message"] = "Shopping list created successfully."
    response["list_id"] = new_list.id
        
    return response

def handle_get_list_contents(message):
    list_id = message.get("list_id")
    response = {}
    print("Retrieving list with id " + list_id)
    
    found_list = None
    for shopping_list in shopping_lists:
        if shopping_list.id == list_id:
            found_list = shopping_list
            print("Found list with name " + found_list.name)
            break
    
    if found_list:
        response["status"] = "success"
        response["name"] = found_list.name
        response["list_contents"] = [{
            "state": {
                "item_name": item.state["item_name"],
                "quantity": item.state["quantity"],
                "time": item.state["time"],
                "client_id": item.state["client_id"]
            }
        } for item in found_list.list.map_list.values()]  # Update list_contents structure
        print("Sending list " + found_list.name)
    else:
        response["status"] = "error"
        response["message"] = "List not found"

    return response

# Function to handle synchronization with the server
def handle_sync(data):
    # Extract data sent by the client
    all_lists_data = data.get("all_lists_data", [])
    print(all_lists_data)
    
    # Create a set of received list IDs
    received_list_ids = {list_data["list_id"] for list_data in all_lists_data}

    # Merge received data with server data
    for received_list_data in all_lists_data:
        list_id = received_list_data["list_id"]
        list_name = received_list_data["list_name"]
        list_contents = received_list_data["list_contents"]

        # Check if the shopping list exists, otherwise create a new one
        existing_list = next((lst for lst in shopping_lists if lst.id == list_id), None)
        if existing_list is None:
            new_list = ShoppingList(list_name)
            new_list.id = list_id
            shopping_lists.append(new_list)
            existing_list = new_list

        # Merge contents with the existing list
        print(f"Merging contents for list: {list_name}")
        print(list_contents)
        existing_list.list.merge(list_contents)

    # Filter the shopping lists to include only the received ones
    updated_contents = []
    for lst in shopping_lists:
        if lst.id in received_list_ids:
            list_data = {
                "list_id": lst.id,
                "list_name": lst.name,
                "list_contents": [
                    {
                        "item_name": item.state['item_name'],
                        "quantity": item.state['quantity'],
                        "time": item.state['time'],
                        "client_id": item.state['client_id']
                    }
                    for item in lst.list.map_list.values()
                ]
            }
            updated_contents.append(list_data)

    response = {"status": "success", "updated_contents": updated_contents}
    return response




while True:
    message = socket.recv_string()  # Receive string message from the client
    print(message)
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
                    response = handle_create(received_json)
                elif action == "get_list_contents":
                    response = handle_get_list_contents(received_json)
                elif action == "sync_with_server":
                    response = handle_sync(received_json)
                # Add more handlers for other actions
                
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
