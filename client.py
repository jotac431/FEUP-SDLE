import zmq
import uuid
import json
import time
import threading

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5556")  # Connect to the server

# Local data storage
shopping_lists = []
user_id = str(uuid.uuid4())

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
        
        
        
        
def create_shopping_list(list_name):
    try:
        socket.send_json({"action": "create", "list_name": list_name})
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        if poller.poll(timeout=2000):  # Waiting for 2 seconds for a response
            response = socket.recv_json()
            new_shopping_list = ShoppingList(list_name)
            new_shopping_list.id = response["list_id"]
            shopping_lists.append(new_shopping_list)
            return response.get("list_id", None)
        else:
            print("Server is unreachable. Creating shopping list locally.")
            new_shopping_list = ShoppingList(list_name)
            shopping_lists.append(new_shopping_list)
            return new_shopping_list.id  # Return the locally created ID
    except zmq.error.ZMQError as e:
        # Server is unreachable, simulate creating the shopping list locally
        print("Server is unreachable. Creating shopping list locally.")
        new_shopping_list = ShoppingList(list_name)
        shopping_lists.append(new_shopping_list)
        return new_shopping_list.id  # Return the locally created ID

def get_list_contents(list_id):
    # Check local shopping_lists first
    for shopping_list in shopping_lists:
        if shopping_list.id == list_id:
            return shopping_list

    try:
        print("List does not exist locally. Checking server storage...")
        socket.send_json({"action": "get_list_contents", "list_id": list_id})

        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        if poller.poll(timeout=2000):  # Waiting for 2 seconds for a response
            response = socket.recv_json()

            if response and response.get("status") == "success":
                print("List " + response.get("name") + " found.")
                # Assuming the received list_contents is a list in the response
                received_contents = response.get("list_contents")
                # Populate the structure on the client side
                new_list = ShoppingList(response.get("name"))
                new_list.id = list_id
                shopping_lists.append(new_list)
                for item in received_contents:
                    new_item = LWWRegister(
                        quantity=item["state"]["quantity"],
                        item_name=item["state"]["item_name"],
                        time=item["state"]["time"],
                        client_id=item["state"]["client_id"]
                    )
                    new_list.list.map_list[item["state"]["item_name"]] = new_item  # Update map_list structure
                return new_list
        else:
            print("Server is unreachable. Unable to get list contents.")
            return None  # Return None if server is unreachable
    except zmq.error.ZMQError as e:
        # Handle connection-related errors
        print("Error: ", e)
        return None  # Return None if an error occurs

def print_list_contents(contents):
    print(f"\n\n\nList Name: {contents.name}")
    for item_name, lww_register in contents.list.map_list.items():
        print(f"Item Name: {item_name}, Quantity: {lww_register.state['quantity']}, Time: {lww_register.state['time']}, Client ID: {lww_register.state['client_id']}")
def print_all_lists():
    for shopping_list in shopping_lists:
        print_list_contents(shopping_list)

        
def add_item(list_id, item_name):
    for shopping_list in shopping_lists:
        if shopping_list.id == list_id:
            # Check if the item already exists in the list
            if item_name in shopping_list.list.map_list:
                # Increment quantity if item exists
                shopping_list.list.map_list[item_name].state['quantity'] += 1
                shopping_list.list.map_list[item_name].state['time'] = int(time.time())
                shopping_list.list.map_list[item_name].state['client_id'] = user_id
                print("Item exists. Incremented quantity.")
                return True

            # If item doesn't exist, create a new LWWRegister for the item and add it to the list
            new_item = LWWRegister(quantity=1, item_name=item_name, time=int(time.time()), client_id=user_id)
            shopping_list.list.map_list[item_name] = new_item
            print("Item does not exist. Adding item.")
            return True
    
    print("List ID not found.")
    return False


def delete_item(list_id, item_name):
    for shopping_list in shopping_lists:
        if shopping_list.id == list_id:
            if item_name in shopping_list.list.map_list:
                item = shopping_list.list.map_list[item_name]
                if item.state['quantity'] > 0:
                    item.state['quantity'] -= 1
                    item.state['time'] = int(time.time())
                    item.state['client_id'] = user_id
                    return True
                return True
    return False  # Return False if list_id is not found or item not found in the list




def update_local_data(server_response):
    if server_response.get("status") == "success":
        updated_contents = server_response.get("updated_contents", [])

        for updated_list in updated_contents:
            list_id = updated_list["list_id"]
            list_name = updated_list["list_name"]
            list_contents = updated_list["list_contents"]

            # Find the shopping list or create a new one if it doesn't exist
            existing_list = next((lst for lst in shopping_lists if lst.id == list_id), None)
            if existing_list is None:
                new_list = ShoppingList(list_name)
                new_list.id = list_id
                shopping_lists.append(new_list)
                existing_list = new_list

            # Merge the received content with the existing list
            existing_list.list.merge(list_contents)

# Function to periodically check server connectivity and synchronize data
def synchronize_with_server():
    while True:
        try:
            # Check server connectivity by attempting to connect
            context_check = zmq.Context()
            socket_check = context_check.socket(zmq.REQ)
            socket_check.connect("tcp://localhost:5556")
            socket_check.send_string("PING")
            response = socket_check.recv_string()

            if response == "PONG":
                # Prepare data to send to the server
                all_lists_data = []
                for local_list in shopping_lists:
                    list_data = {
                        "list_id": local_list.id,
                        "list_name": local_list.name,
                        "list_contents": [
                            {
                                "item_name": item.state['item_name'],
                                "quantity": item.state['quantity'],
                                "time": item.state['time'],
                                "client_id": item.state['client_id']
                            }
                            for item in local_list.list.map_list.values()
                        ]
                    }
                    all_lists_data.append(list_data)

                # Send all shopping lists to the server for synchronization
                socket_check.send_json({
                    "action": "sync_with_server",
                    "all_lists_data": all_lists_data
                })
                
                # Receive updated contents from the server
                server_response = socket_check.recv_json()
                
                # Process and update the local data based on server response
                update_local_data(server_response)
                
        except zmq.error.ZMQError as e:
            # Handle connection errors or any other exceptions here
            print("Connection error:", e)
        
        # Add a delay before the next check
        time.sleep(10)


# Start the synchronization thread
sync_thread = threading.Thread(target=synchronize_with_server)
sync_thread.daemon = True  # Set the thread as daemon so it exits when the main thread exits
sync_thread.start()





# User Interaction
while True:
    print("\n\nUser ID: " + user_id)
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

            # Check if contents exist before entering the nested menu
            while True:
                print("\nOptions for the shopping list:")
                print("1. Add an item")
                print("2. Delete an item")
                print("3. Back to main menu")
                print("4. Refresh")
                list_choice = input("Enter your choice (1/2/3/4): ")

                if list_choice == "1":
                    item_name = input("Enter the name of the item to add: ")
                    add_item(list_id, item_name)
                    contents = get_list_contents(list_id)  # Update contents after adding item
                    print_list_contents(contents)
                elif list_choice == "2":
                    contents = get_list_contents(list_id)
                    print_list_contents(contents)
                    if contents:
                        item_name = input("Enter the name of the item to delete: ")
                        delete_item(list_id, item_name)
                        contents = get_list_contents(list_id)  # Update contents after deletion
                        print_list_contents(contents)
                    else:
                        print("The list is empty.")
                elif list_choice == "3":
                    break
                elif list_choice == "4":
                    print_list_contents(contents)
                    continue
        else:
            print("List ID does not exist.")
    else:
        print("Invalid choice. Please enter 1 or 2.")
        
        
        
        
        
        
        
        
        
        
