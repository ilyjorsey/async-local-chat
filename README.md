# Python async chat

An application for receiving and processing messages from clients.

## Description

### `Server`

Handles incoming requests from clients. A connected client is added to the "general" chat, where previously connected clients are located. The server starts on the localhost (127.0.0.1) and on port 8000.

To run the server, use the command:
```
python server.py
```

### `Client`

A service that can connect to the server to exchange messages with other clients.

To run the client, use the command:

```
python client.py
```
After connecting, the client can send messages to the "general" chat.
The client can also send private messages to any participant from the general chat.

To send a private message:

```
/private name message
```
To disconnect from the chat, the client needs to enter the command:
```
/disconnect
```
For reconnection:
```
/reconnect
```
## Further Details:
Install dependencies from the requirements.txt file:
```
pip install -r requirements.txt
```
Also, the user can connect from two or more clients simultaneously. States are synchronized between clients.

