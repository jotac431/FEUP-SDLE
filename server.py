import zmq
import uuid
import json
import logging
import sys

script_name = sys.argv[0]

port = sys.argv[1]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:" + str(port))  # Bind to all network interfaces on port 5556

def replicate(t_port, list_name):
    print("entrei")
    try:
        
        context2 = zmq.Context()
        socket2 = context2.socket(zmq.PUSH)
        socket2.connect("tcp://127.0.0.1:" + str(t_port))
        
        message = {"list_name": list_name}
        socket2.send_json(message)
        
        print(f"Message sent to port {t_port} with list_name: {list_name}")

        socket2.disconnect("tcp://127.0.0.1:" + str(t_port))
        
        socket2.close()
        context2.term()

    except Exception as e:
        print(f"Error: {e}")

def receive_replicate(t_port):
    try:
        context3 = zmq.Context()
        socket3 = context3.socket(zmq.PULL)
        socket3.connect("tcp://127.0.0.1:" + str(t_port))

        # Receive the message from the sender
        received_message = socket3.recv_json()
        received_list_name = received_message.get("list_name", None)

        if received_list_name is not None:
            print(f"Received message on port {t_port} with list_name: {received_list_name}")

        else:
            print("Error: No list_name in the received message")

        socket3.disconnect("tcp://127.0.0.1:" + str(t_port))
        
        socket3.close()
        context3.term()

    except Exception as e:
        print(f"Error: {e}")

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
                self.map_list[item_name].merge(k)
            else:
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
    
    print(port)
    
    if port == "5001":
        print("foi")
        replicate(5002, list_name)
    if port == "5002":
        print("foi no segundo")
        receive_replicate(5001)
    
    #for i in range(5001, 5003):
    #    if(i != port):
    #        replicate(i, list_name)
    #    else:
    #        receive_replicate(i)
    
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
    print("Synchronizing...")
    # Extract data sent by the client
    all_lists_data = data.get("all_lists_data", [])
    
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

def print_list_contents(contents):
    print(f"\n\n\nList Name: {contents.name}")
    for item_name, lww_register in contents.list.map_list.items():
        print(f"Item Name: {item_name}, Quantity: {lww_register.state['quantity']}, Time: {lww_register.state['time']}, Client ID: {lww_register.state['client_id']}")

def print_all_lists():
    for shopping_list in shopping_lists:
        print_list_contents(shopping_list)




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
