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
        socket.send_json({"action": "get_list_contents", "list_id": list_id})

        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        if poller.poll(timeout=2000):  # Waiting for 2 seconds for a response
            response = socket.recv_json()

            if response and response.get("status") == "success":
                # Assuming the received list_contents is a list in the response
                received_contents = response.get("list_contents")
                # Populate the structure on the client side
                new_list = ShoppingList(response.get("name")) 
                shopping_lists.append(new_list)
                for item in received_contents:
                    new_item = LWWRegister()  
                    new_item.value = item["value"]
                    new_item.state = item["state"]
                    new_list.append(new_item)
                return new_list
        else:
            print("Server is unreachable. Unable to get list contents.")
            return None  # Return None if server is unreachable
    except zmq.error.ZMQError as e:
        # Handle connection-related errors
        print("Error: ", e)
        return None  # Return None if an error occurs

def print_list_contents(contents):
    print(f"List Name: {contents.name}")
    for lww_register in contents.list.list:
        print(f"Value: {lww_register.value}, State: {lww_register.state}")
        




# Function to periodically check server connectivity and synchronize data
def synchronize_with_server():
    while True:
        try:
            # Check server connectivity by attempting to connect
            context_check = zmq.Context()
            socket_check = context_check.socket(zmq.REQ)
            socket_check.connect("tcp://localhost:5556")
            socket_check.send_string("PING")  # Send a ping message to check connectivity
            response = socket_check.recv_string()

            if response == "PONG":  # Server responded, indicating connectivity
                # Perform data synchronization with the server
                # Implement logic to merge local data with server data here
                
                # For example:
                # Iterate through local shopping_lists and send changes to the server
                print("Connected!!!")
                for local_list in shopping_lists:
                    # Send updates to the server for each shopping list
                    # Modify this part based on your merging logic
                    print("Merging " + local_list.name)
                    '''socket_check.send_json({
                        "action": "merge_with_server",
                        "list_id": local_list.id,
                        "list_contents": local_list.list  # Sending local list contents to merge
                    })
                    _ = socket_check.recv_json()  # Receive acknowledgment from the server'''
                    
                # After synchronization, you can break the loop or add a delay before checking again
                # break  # Break the loop if synchronization is done
        except zmq.error.ZMQError as e:
            # Handle connection errors or any other exceptions here
            print("Connection error:", e)
        
        # Add a delay before the next check
        time.sleep(10)  # Check every 10 seconds

# Start the synchronization thread
sync_thread = threading.Thread(target=synchronize_with_server)
sync_thread.daemon = True  # Set the thread as daemon so it exits when the main thread exits
sync_thread.start()





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

            # Check if contents exist before entering the nested menu
            while True:
                print("\nOptions for the shopping list:")
                print("1. Add an item")
                print("2. Delete an item")
                print("3. Back to main menu")
                list_choice = input("Enter your choice (1/2/3): ")

                if list_choice == "1":
                    item_name = input("Enter the name of the item to add: ")
                    # TODO : add_item(list_id, item_name)
                    contents = get_list_contents(list_id)  # Update contents after adding item
                    print_list_contents(contents)
                elif list_choice == "2":
                    contents = get_list_contents(list_id)
                    print_list_contents(contents)
                    if contents:
                        index_to_delete = int(input("Enter the index of the item to delete: ")) - 1
                        # TODO : delete_item(list_id, index_to_delete)
                        contents = get_list_contents(list_id)  # Update contents after deletion
                        print_list_contents(contents)
                    else:
                        print("The list is empty.")
                elif list_choice == "3":
                    break
        else:
            print("List ID does not exist.")
    else:
        print("Invalid choice. Please enter 1 or 2.")
        
        
        
        
        
        
        
        
        
        
