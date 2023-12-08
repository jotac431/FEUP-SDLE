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
    def __init__(self, value=0, type='', time=0, client_id=''):
        self.value = value
        self.state = {'type': type, 'value': self.value, 'time': time, 'client_id': client_id}
    
    def merge(self, remote):
        if self.state['time'] < remote['time']:
            self.state = remote
        if self.state['time'] == remote['time']:
            if self.state['client_id'] < remote['client_id']:
                self.state = remote
        
class LWWMap:
    def __init__(self):
        self.value = 0
        self.list = []
    def merge(self, remote):
        for k in remote.list:
            if self.list[k]:
                self.list[k].merge(self.list[k], remote.list[k])
            else:
                self.list[k] = remote.list[k]
        
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
    print("Retreiving list with id " + list_id)
    
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
            "value": item.value,
            "state": item.state
        } for item in found_list.list.list]
        print("Sending list " + found_list.name)
    else:
        response["status"] = "error"
        response["message"] = "List not found"

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
                elif action == "add":
                    response = handle_add(received_json) # TODO
                elif action == "get_list_contents":
                    response = handle_get_list_contents(received_json)
                elif action == "delete":
                    response = handle_delete(received_json) # TODO
                elif action == "update_quantity":
                    response = handle_update_quantity(received_json) # TODO
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

    """if action == "create":
        new_list_id = str(uuid.uuid4())
        shopping_lists[new_list_id] = {"list_name": message.get("list_name"), "items": []}
        response["status"] = "success"
        response["list_id"] = new_list_id
    elif action == "add":
        list_id = message.get("list_id")
        item_name = message.get("item_name")
        if list_id in shopping_lists:
            if add_or_increment_item(list_id, item_name):
                response["status"] = "success"
            else:
                response["status"] = "error"
                response["message"] = "Item not found"
        else:
            response["status"] = "error"
            response["message"] = "List not found"
    elif action == "get_list_contents":
        list_id = message.get("list_id")
        if list_id in shopping_lists:
            response["status"] = "success"
            response["list_contents"] = shopping_lists[list_id]["items"]
        else:
            response["status"] = "error"
            response["message"] = "List not found"
    elif action == "delete":
        list_id = message.get("list_id")
        item_index = message.get("item_index")
        if list_id in shopping_lists:
            if delete_or_decrement_item(list_id, item_index):
                response["status"] = "success"
            else:
                response["status"] = "error"
                response["message"] = "Item not found or invalid index"
        else:
            response["status"] = "error"
            response["message"] = "List not found"

    socket.send_json(response)  # Send JSON response back to the client"""