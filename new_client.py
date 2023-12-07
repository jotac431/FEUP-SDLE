import zmq
import uuid
import json

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5556")  # Connect to the server

# Local data storage
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
        
def create_shopping_list(list_name):
    socket.send_json({"action": "create", "list_name": list_name})
    response = socket.recv_json()
    new_shopping_list = ShoppingList(list_name)
    new_shopping_list.id = response["list_id"]
    shopping_lists.append(new_shopping_list)
    return response.get("list_id", None)

def get_list_contents(list_id):
    for shopping_list in shopping_lists:
        if shopping_list.id == list_id:
            return shopping_list
        
    socket.send_json({"action": "get_list_contents", "list_id": list_id})
    
    response = socket.recv_json()

    if response and response.get("status") == "success":
        # Assuming the received list_contents is a list in the response
        received_contents = response.get("list_contents")
        # Populate the structure in the client side
        new_list = ShoppingList(response.get("name")) 
        for item in received_contents:
            new_item = LWWRegister()  
            new_item.value = item["value"]
            new_item.state = item["state"]
            new_list.append(new_item)
        return new_list
    return None  # Return None if the list_id is not found

def print_list_contents(contents):
    print(f"List Name: {contents.name}")
    for lww_register in contents.list.list:
        print(f"Value: {lww_register.value}, State: {lww_register.state}")

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
        if contents is not None:
            print_list_contents(contents)
        else:
            print("List ID does not exist.")
        
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
                if contents:
                    index_to_delete = int(input("Enter the index of the item to delete: ")) - 1
                    delete_item(list_id, index_to_delete)
                    contents = get_list_contents(list_id)  # Update contents after deletion
                    print_list_contents(contents)
                else:
                    print("The list is empty.")
            elif list_choice == "3":
                break
    else:
        print("Invalid choice. Please enter 1 or 2.")
        
        
        
        
        
        
        
        
        
        
