import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5556")  # Connect to the server

def create_shopping_list(list_name):
    socket.send_json({"action": "create", "list_name": list_name})
    response = socket.recv_json()
    return response.get("list_id", None)

def get_list_contents(list_id):
    socket.send_json({"action": "get_list_contents", "list_id": list_id})
    response = socket.recv_json()
    return response.get("list_contents", [])

def add_item(list_id, item_name):
    socket.send_json({"action": "add", "list_id": list_id, "item_name": item_name})
    response = socket.recv_json()
    return response["status"]

def delete_item(list_id, item_index):
    socket.send_json({"action": "delete", "list_id": list_id, "item_index": item_index})
    response = socket.recv_json()
    return response["status"]

def check_item(list_id, item_index):
    socket.send_json({"action": "check", "list_id": list_id, "item_index": item_index})
    response = socket.recv_json()
    return response["status"]

def update_quantity(list_id, item_index, new_quantity):
    socket.send_json({"action": "update_quantity", "list_id": list_id, "item_index": item_index, "new_quantity": new_quantity})
    response = socket.recv_json()
    return response["status"]

def print_list_contents(contents):
    print("Shopping List Contents:")
    if not contents:
        print("The list is empty.")
    else:
        for index, item in enumerate(contents, start=1):
            checked_status = "Checked" if item.get("checked") else "Unchecked"
            print(f"{index}. {item['name']} - Quantity: {item['quantity']} - {checked_status}")

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
            print("3. Check an item")
            print("4. Update quantity of an item")
            print("5. Back to main menu")
            list_choice = input("Enter your choice (1/2/3/4/5): ")

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
                contents = get_list_contents(list_id)
                print_list_contents(contents)
                if contents:
                    index_to_check = int(input("Enter the index of the item to check: ")) - 1
                    check_item(list_id, index_to_check)
                    contents = get_list_contents(list_id)  # Update contents after checking item
                    print_list_contents(contents)
                else:
                    print("The list is empty.")
            elif list_choice == "4":
                contents = get_list_contents(list_id)
                print_list_contents(contents)
                if contents:
                    index_to_update = int(input("Enter the index of the item to update: ")) - 1
                    new_quantity = int(input("Enter the new quantity: "))
                    update_quantity(list_id, index_to_update, new_quantity)
                    contents = get_list_contents(list_id)  # Update contents after updating item
                    print_list_contents(contents)
                else:
                    print("The list is empty.")
            elif list_choice == "5":
                break
            else:
                print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
