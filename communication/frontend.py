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
        _lock (asyncio.Lock): The lock for managing access to the client connection.
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
            self._client = None  # Single client connection
            self._receive_queue = receive_queue
            self._send_queue = send_queue
            self._db_client = db_client
            self._logger = logger
            self._lock = asyncio.Lock()  # Concurrency control for client access
            self._db_client.create_table('frontend_error', [
                'id INTEGER PRIMARY KEY',
                'message TEXT',
                'date TEXT'
            ])
            self._running = False
            asyncio.create_task(self.process_send_messages())
        except Exception as e:
            self._log_and_store_error(f"Error initializing WebSocket server: {e}")

    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """
        Handle incoming WebSocket client connection and message reception.

        Args:
            websocket (websockets.WebSocketServerProtocol): The WebSocket connection instance.
            path (str): The WebSocket connection path.
        """
        async with self._lock:
            if self._client:
                self._logger.warning("WebSocket Server - A client is already connected. Rejecting new connection...")
                await websocket.close()
                return

            self._client = websocket
            client_address = websocket.remote_address
            self._logger.info(f"WebSocket Server - Connection established from {client_address}")

        try:
            async for message in websocket:
                try:
                    message = json.loads(message)
                    await self._receive_queue.put(message)
                except json.JSONDecodeError as e:
                    self._log_and_store_error(f"WebSocket Server - Error decoding message: {e}")
        except ConnectionClosed:
            self._logger.warning(f"WebSocket Server - Connection closed by client: {client_address}")
        except Exception as e:
            self._log_and_store_error(f"WebSocket Server - Error occurred: {e}")
        finally:
            self._logger.info(f"WebSocket Server - Closing connection from {client_address}")
            async with self._lock:
                self._client = None

    async def process_send_messages(self):
        """
        Continuously send messages from the send queue to the connected client.
        """

        while self._running:
            if self._client:
                try:
                    message = await self._send_queue.get()
                    await self._send_message(message)
                except Exception as e:
                    self._log_and_store_error(f"WebSocket Server - Error processing messages to send: {e}")
            else:
                await asyncio.sleep(0.5)

    async def _send_message(self, message: dict):
        """
        Send a message to the connected WebSocket client.

        Args:
            message (dict): The message to send.
        """

        async with self._lock:
            if self._client:
                try:
                    message = json.dumps(message)
                    await self._client.send(message)
                except Exception as e:
                    self._log_and_store_error(f"WebSocket Server - Failed to send message: {e}")
            else:
                self._logger.warning("WebSocket Server - No client is connected.")

    async def start_server(self):
        """
        Start the WebSocket server and listen for incoming connections.
        """

        try:
            self._logger.info(f"WebSocket Server - Starting on {self._host}:{self._port}")
            async with websockets.serve(self.handle_client, self._host, self._port):
                self._running = True
                await asyncio.Future()
        except Exception as e:
            self._log_and_store_error(f"WebSocket Server - Failed to start: {e}")

    async def stop_server(self):
        """
        Gracefully stop the WebSocket server.
        """

        self._logger.info("WebSocket Server - Stopping server...")
        self._running = False
        async with self._lock:
            if self._client:
                await self._client.close()
                self._client = None

    def _log_and_store_error(self, message: str):
        """
        Helper method to log and store errors in the database.

        Args:
            message (str): The error message to log and store.
        """

        self._logger.error(f"{message}")
        self._db_client.insert_entry('frontend_error', ['message', 'date'], [message, str(datetime.datetime.now())])