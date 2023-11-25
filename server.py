import zmq
import uuid
import json

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5556")  # Bind to all network interfaces on port 5556

# Simulated in-memory data storage for shopping lists
shopping_lists = {}

def print_shopping_lists():
    print("Current Shopping Lists:")
    for list_id, data in shopping_lists.items():
        print(f"List ID: {list_id}, Name: {data['list_name']}")
        print("Items:")
        for item in data['items']:
            print(f"- {item['name']}: Quantity - {item['quantity']}")
        print("")

while True:
    message = socket.recv_json()  # Receive JSON message from the client
    action = message.get("action")
    response = {}

    if action == "create":
        new_list_id = str(uuid.uuid4())
        shopping_lists[new_list_id] = {"list_name": message.get("list_name"), "items": []}
        response["status"] = "success"
        response["list_id"] = new_list_id
    elif action == "add":
        list_id = message.get("list_id")
        item_name = message.get("item_name")
        if list_id in shopping_lists:
            shopping_lists[list_id]["items"].append({"name": item_name, "quantity": 1})  # Default quantity
            response["status"] = "success"
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
        if list_id in shopping_lists and 0 <= item_index < len(shopping_lists[list_id]["items"]):
            del shopping_lists[list_id]["items"][item_index]
            response["status"] = "success"
        else:
            response["status"] = "error"
            response["message"] = "Item not found or invalid index"
    # Implement other actions like delete, check, etc.

    socket.send_json(response)  # Send JSON response back to the client
