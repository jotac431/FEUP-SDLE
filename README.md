# FEUP-SDLE
FEUP - Sistemas Distribuídos de Larga Escala

Concurrent shopping list Application

User Interface:
- In command line type "python3 client.py", it open an user interface to create or enter a shopping list with a shopping list ID.
It creates a new User ID when it starts application.
After entering a shopping list with the respective ID it has options to add an delete an item, and to refresh.
The application works offline and stores all changes to local storage.

Creating shopping list:
- The app checks if there is connection to server using a poller. If there is, the shopping list and the respective ID is created online and the contents are retreived back to the client. If there is not connection to the server within 2 seconds, the list is added to local storage, and will be updated to server when connection is restablished.

Addition and deletion of items:
- The client adds and deletes items with and without connection to the server. Each item entry has information of item name, quantity, time of modification and user ID of who did the modification.

Syncronization with the server and other clients:
- Every 2 seconds the app checks if there is connection to the server. If there is, the user shopping lists are sent to the server and it occurs a CRDT merge in server side to syncronize data. A response is sent by the server with the updated lists and it occurs also a CRDT merge in client side. In the merge is applied a Last Writer Wins proccess, which means the entry with highest timestamp proceds in the data.
