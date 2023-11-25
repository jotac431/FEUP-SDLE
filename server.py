import zmq
import uuid
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5556")

shopping_lists = {}

def print_shopping_lists():
    logger.info("Current Shopping Lists:")
    for list_id, data in shopping_lists.items():
        logger.info(f"List ID: {list_id}, Name: {data['list_name']}")
        logger.info("Items:")
        for item in data['items']:
            logger.info(f"- {item['name']}: Quantity - {item['quantity']}")
        logger.info("")

def handle_create(message):
    new_list_id = str(uuid.uuid4())
    shopping_lists[new_list_id] = {"list_name": message.get("list_name"), "items": []}
    response = {"status": "success", "list_id": new_list_id}
    return response

def handle_add(message):
    list_id = message.get("list_id")
    item_name = message.get("item_name")
    response = {}
    
    if list_id in shopping_lists:
        shopping_lists[list_id]["items"].append({"name": item_name, "quantity": 1})
        response["status"] = "success"
    else:
        response["status"] = "error"
        response["message"] = "List not found"
    
    return response

def handle_get_list_contents(message):
    list_id = message.get("list_id")
    response = {}

    if list_id in shopping_lists:
        response["status"] = "success"
        response["list_contents"] = shopping_lists[list_id]["items"]
    else:
        response["status"] = "error"
        response["message"] = "List not found"
    
    return response

def handle_delete(message):
    list_id = message.get("list_id")
    item_index = message.get("item_index")
    response = {}

    if list_id in shopping_lists and 0 <= item_index < len(shopping_lists[list_id]["items"]):
        del shopping_lists[list_id]["items"][item_index]
        response["status"] = "success"
    else:
        response["status"] = "error"
        response["message"] = "Item not found or invalid index"
    
    return response


def handle_update_quantity(message):
    list_id = message.get("list_id")
    item_index = message.get("item_index")
    new_quantity = message.get("new_quantity")
    response = {}

    if list_id in shopping_lists and 0 <= item_index < len(shopping_lists[list_id]["items"]):
        shopping_lists[list_id]["items"][item_index]["quantity"] = new_quantity
        response["status"] = "success"
    else:
        response["status"] = "error"
        response["message"] = "Item not found or invalid index"
    
    return response

while True:
    message = socket.recv_json()
    action = message.get("action")
    response = {}

    try:
        if action == "create":
            response = handle_create(message)
        elif action == "add":
            response = handle_add(message)
        elif action == "get_list_contents":
            response = handle_get_list_contents(message)
        elif action == "delete":
            response = handle_delete(message)
        elif action == "update_quantity":
            response = handle_update_quantity(message)
        # Add more handlers for other actions

        socket.send_json(response)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        response["status"] = "error"
        response["message"] = "Internal server error"
        socket.send_json(response)
