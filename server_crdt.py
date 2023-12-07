import zmq
import json
from collections import defaultdict

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5556")  # Bind to the server address

# Server-side data storage using CRDT structures
shopping_lists = defaultdict(dict)
list_items = defaultdict(list)

def add_item_to_list(list_id, item_name):
    items = list_items[list_id]
    item = next((i for i in items if i['name'] == item_name), None)
    if item:
        item['quantity'] += 1
    else:
        list_items[list_id].append({'name': item_name, 'quantity': 1})

def delete_item_from_list(list_id, item_name):
    list_items[list_id] = [i for i in list_items[list_id] if i['name'] != item_name]

# Server loop to handle client requests
while True:
    # Wait for a request from a client
    message = socket.recv_json()
    
    # Process the received message from the client
    operation = message.get("operation")
    list_id = message.get("list_id")
    item_name = message.get("item_name")
    
    if operation == "add":
        add_item_to_list(list_id, item_name)
        response = f"Added {item_name} to list {list_id}"
    elif operation == "delete":
        delete_item_from_list(list_id, item_name)
        response = f"Deleted {item_name} from list {list_id}"
    else:
        response = "Invalid operation"
    
    # Send a response back to the client
    socket.send_string(response)
