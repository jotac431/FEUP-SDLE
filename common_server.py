import zmq
import uuid
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
def handle_create(message, shopping_lists):
    list_name = message.get("list_name")
    print("Creating store named " + list_name)
    response = {}
    
    new_list = ShoppingList(list_name)
    shopping_lists.append(new_list)
    response["success"] = True
    response["message"] = "Shopping list created successfully."
    response["list_id"] = new_list.id
        
    return response

def handle_get_list_contents(message, shopping_lists):
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
def handle_sync(data, shopping_lists):
    print("Synchronizing...")
    
    # Extract data sent by the client
    all_lists_data = data.get("list_data", {})  # Changed from "all_lists_data"

    list_id = all_lists_data.get("list_id")
    list_name = all_lists_data.get("list_name")
    list_contents = all_lists_data.get("list_contents", [])

    # Check if the shopping list exists, otherwise create a new one
    existing_list = next((lst for lst in shopping_lists if lst.id == list_id), None)
    if existing_list is None:
        new_list = ShoppingList(list_name)
        new_list.id = list_id
        shopping_lists.append(new_list)
        existing_list = new_list

    # Merge contents with the existing list
    existing_list.list.merge(list_contents)

    # Prepare updated contents
    updated_contents = {
        "list_id": existing_list.id,
        "list_name": existing_list.name,
        "list_contents": [
            {
                "item_name": item.state['item_name'],
                "quantity": item.state['quantity'],
                "time": item.state['time'],
                "client_id": item.state['client_id']
            }
            for item in existing_list.list.map_list.values()
        ]
    }

    response = {"status": "success", "updated_contents": updated_contents}
    return response


def print_list_contents(contents):
    print(f"\n\n\nList Name: {contents.name}")
    for item_name, lww_register in contents.list.map_list.items():
        print(f"Item Name: {item_name}, Quantity: {lww_register.state['quantity']}, Time: {lww_register.state['time']}, Client ID: {lww_register.state['client_id']}")

def print_all_lists(shopping_lists):
    for shopping_list in shopping_lists:
        print_list_contents(shopping_list)

