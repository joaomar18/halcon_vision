import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed
from db.client import DBClient
import logging
import datetime

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

    def __init__(self, host: str, port: int, receive_queue: asyncio.Queue, send_queue: asyncio.Queue, db_client: DBClient, logger: logging.Logger):
        """
        Initialize the WebSocketServer.

        Args:
            host (str): The host address.
            port (int): The port number.
            receive_queue (asyncio.Queue): Queue for receiving messages.
            send_queue (asyncio.Queue): Queue for sending messages.
        """
        try:

            self._host = host
            self._port = port
            self._client = None
            self._receive_queue = receive_queue
            self._send_queue = send_queue
            self._db_client = db_client
            self._logger = logger
            self._db_client.create_table('frontend_error', [
                                        'id INTEGER PRIMARY KEY', 
                                        'message TEXT',
                                        'date TEXT'])
            asyncio.create_task(self.process_send_messages())
        except Exception as e:
            self._logger.error(f"WebSocket Server - Error initializing WebSocket server: {e}")

    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """
        Handle incoming WebSocket client connection and message reception.

        Args:
            websocket (websockets.WebSocketServerProtocol): The WebSocket connection instance.
            path (str): The WebSocket connection path.
        """

        if self._client:
            self._logger.warning("WebSocket Server - A client is already connected. Rejecting new connection...")
            await websocket.close()
            return

        self._client = websocket
        client_address = websocket.remote_address
        self._logger.info(f"WebSocket Server - Connection established to frontend from {client_address}")

        try:
            async for message in websocket:
                try:
                    message = json.loads(message)
                    await self._receive_queue.put(message)
                except json.JSONDecodeError as e:
                    self._logger.error(f"WebSocket Server - Error decoding message: {e}")
                    self._db_client.insert_entry('frontend_error', ['message', 'date'], [str(e), str(datetime.datetime.now())])
        except ConnectionClosed:
            self._logger.warning(f"WebsSocket Server - Connection closed by client: {client_address}")
        except Exception as e:
            self._logger.error(f"WebSocket Server - Error occurred: {e}")
            self._db_client.insert_entry('frontend_error', ['message', 'date'], [str(e), str(datetime.datetime.now())])
        finally:
            self._logger.warning(f"WebSocket Server - Closing connection from {client_address}")
            self._client = None

    async def process_send_messages(self):
        """
        Continuously send messages from the send queue to the connected client.
        """

        while True:
            if self._client:
                try:
                    message = await self._send_queue.get()
                    await self._send_message(message)
                except Exception as e:
                    self._logger.error(f"WebSocket Server - Error processing messages to send: {e}")
                    self._db_client.insert_entry('frontend_error', ['message', 'date'], [str(e), str(datetime.datetime.now())])
            else:
                await asyncio.sleep(0.1)

    async def _send_message(self, message: dict):
        """
        Send a message to the connected WebSocket client.

        Args:
            message (dict): The message to send.
        """

        if self._client:
            message = json.dumps(message)
            await self._client.send(message)
        else:
            self._logger.warning("WebSocket Server - Trying to send message but no client is connected.")

    async def start_server(self):
        """
        Start the WebSocket server and listen for incoming connections.
        """

        try:
            async with websockets.serve(self.handle_client, self._host, self._port):
                self._logger.info(f"WebSocket Server - Running on {self._host}:{self._port}")
                await asyncio.Future()
        except Exception as e:
            self._logger.error(f"WebSocket Server - Failed to start: {e}")
            self._db_client.insert_entry('frontend_error', ['message', 'date'], [str(e), str(datetime.datetime.now())])