import zmq
import uuid
import json
from collections import defaultdict

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5556")  # Connect to the server

class LWWRegisterCRDT:
    def __init__(self):
        self.value = None
        self.state = {'time': 0, 'client_id': 0, 'data': None}

    def merge(self, local, remote):
        if local['time'] > remote['time']:
            return local
        elif local['time'] == remote['time']:
            if local['client_id'] > remote['client_id']:
                return local
        return remote

class LWWMapCRDT:
    def __init__(self):
        self.value = {}
        self.state = {}

    def merge(self, local, remote):
        for key in remote.keys():
            if key in local:
                local[key] = local[key].merge(local[key].state, remote[key].state)
            else:
                local[key] = remote[key]

class ShoppingList:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.list = LWWMapCRDT()

# JSON file paths
SHOPPING_LISTS_FILE = "shopping_lists.json"

# Custom JSON Encoder to handle serialization of LWWRegisterCRDT objects
class CRDTJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, LWWRegisterCRDT):
            return obj.state
        return json.JSONEncoder.default(self, obj)

# Load existing data from JSON files
try:
    with open(SHOPPING_LISTS_FILE, "r") as file:
        shopping_lists_data = json.load(file)
except FileNotFoundError:
    shopping_lists_data = {}

# Local storage using CRDTs
shopping_lists = defaultdict(ShoppingList)

def save_shopping_lists():
    with open(SHOPPING_LISTS_FILE, "w") as file:
        json.dump(shopping_lists_data, file, cls=CRDTJSONEncoder)

def create_shopping_list(list_name):
    shopping_list = ShoppingList()
    shopping_list.list.value = {}
    list_id = str(uuid.uuid4())
    shopping_lists_data[list_id] = {
        'list_name': list_name,
        'list': {}
    }
    shopping_lists[list_id] = shopping_list
    save_shopping_lists()
    return list_id

def get_list_contents(list_id):
    return shopping_lists_data.get(list_id, {}).get('list', {})

def add_item(list_id, item_name):
    list_obj = shopping_lists[list_id].list
    if item_name in list_obj.value:
        list_obj.value[item_name].state['time'] += 1
    else:
        lww_register = LWWRegisterCRDT()
        lww_register.state['time'] += 1
        list_obj.value[item_name] = lww_register
    shopping_lists_data[list_id]['list'] = list_obj.value
    save_shopping_lists()

def delete_item(list_id, item_name):
    list_obj = shopping_lists[list_id].list
    if item_name in list_obj.value:
        del list_obj.value[item_name]
    shopping_lists_data[list_id]['list'] = list_obj.value
    save_shopping_lists()   
    
def print_list_contents(contents):
    print("Shopping List Contents:")
    if not contents:
        print("The list is empty.")
    else:
        for index, (item, lww_register) in enumerate(contents.items(), start=1):
            print(f"{index}. {item} - Timestamp: {lww_register.state['time']}")


# User Interaction
while True:
    print("Options:")
    print("1. Create a new shopping list")
    print("2. Enter an existing shopping list")
    choice = input("Enter your choice (1/2): ")

    if choice == "1":
        list_name = input("Enter the name for the new shopping list: ")
        list_id = create_shopping_list(list_name)
        print(f"Created new shopping list with ID: {list_id}")
    elif choice == "2":
        list_id = input("Enter the ID of the existing shopping list: ")
        contents = get_list_contents(list_id)
        print_list_contents(contents)

        while True:
            print("\nOptions for the shopping list:")
            print("1. Add an item")
            print("2. Delete an item")
            print("3. Back to main menu")
            list_choice = input("Enter your choice (1/2/3): ")

            if list_choice == "1":
                item_name = input("Enter the name of the item to add: ")
                add_item(list_id, item_name)
                contents = get_list_contents(list_id)  # Update contents after adding item
                print_list_contents(contents)
            elif list_choice == "2":
                contents = get_list_contents(list_id)
                print_list_contents(contents)
                item_name = input("Enter the name of the item to delete: ")
                delete_item(list_id, item_name)
                contents = get_list_contents(list_id)  # Update contents after deletion
                print_list_contents(contents)
            elif list_choice == "3":
                break
    else:
        print("Invalid choice. Please enter 1 or 2.")

"""
CRDT<T>{
    Value
    State
    Merge
}

LWWRegister CRDT<T>{
    Value
    State:{time, client_id, T}
    merge(local, remote)
        if local.time > remote.time
            local
        if local.time == remote.time
            if local.client_id > remote.client_id
                local
        else
            remote
        
}

LWWMap <T>{
    Value
    State: %{"onions" => LWWRegister<Integer>}
    merge(local, remote){
        for k in keys remote{
            if local[k]
                merge(local[k], remote[k])
            else
                local[k] = remote[k]
        }
    }
}

struct ShoppingList{
    id: UUID client
    list: LWWMap<T>
}



"""