import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed

class WebSocketServer:
    """
    WebSocketServer manages a single WebSocket client connection and allows sending and receiving messages
    through asynchronous queues.

    Attributes:
        _host (str): The host address for the WebSocket server.
        _port (int): The port for the WebSocket server.
        _client (websockets.WebSocketServerProtocol): The current connected WebSocket client.
        _receive_queue (asyncio.Queue): The queue for receiving messages from the client.
        _send_queue (asyncio.Queue): The queue for sending messages to the client.
    """

    def __init__(self, host: str, port: int, receive_queue: asyncio.Queue, send_queue: asyncio.Queue):
        """
        Initialize the WebSocketServer.

        Args:
            host (str): The host address.
            port (int): The port number.
            receive_queue (asyncio.Queue): Queue for receiving messages.
            send_queue (asyncio.Queue): Queue for sending messages.
        """
                
        self._host = host
        self._port = port
        self._client = None
        self._receive_queue = receive_queue
        self._send_queue = send_queue
        asyncio.create_task(self.process_send_messages())

    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """
        Handle incoming WebSocket client connection and message reception.

        Args:
            websocket (websockets.WebSocketServerProtocol): The WebSocket connection instance.
            path (str): The WebSocket connection path.
        """

        if self._client:
            print("A client is already connected. Rejecting new connection...")
            await websocket.close()
            return

        self._client = websocket
        client_address = websocket.remote_address
        print(f"Connection from {client_address}")

        try:
            async for message in websocket:
                await self._receive_queue.put(json.loads(message))
        except ConnectionClosed:
            print(f"Connection closed by client: {client_address}")
        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            print(f"Closing connection from {client_address}")
            self._client = None

    async def process_send_messages(self):
        """
        Continuously send messages from the send queue to the connected client.
        """

        while True:
            if self._client:
                try:
                    message = await self._send_queue.get()
                    await self.send_message(message)
                except Exception as e:
                    print(f"Frontend server: Error sending message: {e}")
            else:
                await asyncio.sleep(0.1)

    async def send_message(self, message: dict):
        """
        Send a message to the connected WebSocket client.

        Args:
            message (dict): The message to send.
        """

        if self._client:
            try:
                message = json.dumps(message)
                await self._client.send(message)
            except Exception as e:
                print(f"Exception while sending to client: {e}")
        else:
            print("No client is connected.")

    async def start_server(self):
        """
        Start the WebSocket server and listen for incoming connections.
        """

        try:
            async with websockets.serve(self.handle_client, self._host, self._port):
                print(f"WebSocket server running on {self._host}:{self._port}")
                await asyncio.Future()
        except Exception as e:
            print(f"Failed to start WebSocket server: {e}")