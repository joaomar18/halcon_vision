###########EXTERNAL IMPORTS############

import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed
from websockets.legacy.server import WebSocketServerProtocol
import logging

#######################################

#############LOCAL IMPORTS#############

from util.debug import LoggerManager

#######################################


class WebSocketServer:
    """
    WebSocketServer manages a single WebSocket client connection and allows sending and receiving messages
    through asynchronous queues.

    Attributes:
        host (str): The host address for the WebSocket server.
        port (int): The port for the WebSocket server.
        client (websockets.WebSocketServerProtocol): The current connected WebSocket client.
        receive_queue (asyncio.Queue): The queue for receiving messages from the client.
        send_queue (asyncio.Queue): The queue for sending messages to the client.
        lock (asyncio.Lock): The lock for managing access to the client connection.
    """

    def __init__(
        self,
        host: str,
        port: int,
        receive_queue: asyncio.Queue,
        send_queue: asyncio.Queue,
    ):

        logger = LoggerManager.get_logger(__name__)

        try:
            self.host = host
            self.port = port
            self.client = None  # Single client connection
            self.receive_queue = receive_queue
            self.send_queue = send_queue
            self.lock = asyncio.Lock()  # Concurrency control for client access
            self.running = False

        except Exception as e:
            logger.error(f"WebSocket Server - Error initializing", e)

    async def handle_client(self, websocket: WebSocketServerProtocol) -> None:
        """
        Handle incoming WebSocket client connection and message reception.

        Args:
            websocket (websockets.WebSocketServerProtocol): The WebSocket connection instance.
        """

        logger = LoggerManager.get_logger(__name__)

        async with self.lock:
            if self.client:
                logger.warning("WebSocket Server - A client is already connected. Rejecting new connection...")
                await websocket.close()
                return

            self.client = websocket
            client_address = websocket.remote_address
            logger.info(f"WebSocket Server - Connection established from {client_address}")

        try:
            async for message in websocket:
                try:
                    message = json.loads(message)
                    logger.debug(f"Message received: {message}")
                    await self.receive_queue.put(message)
                except json.JSONDecodeError as e:
                    logger.error(f"WebSocket Server - Error decoding message", e)
        except ConnectionClosed:
            logger.warning(f"WebSocket Server - Connection closed by client: {client_address}")
        except Exception as e:
            logger.error(f"WebSocket Server - Error occurred", e)
        finally:
            logger.info(f"WebSocket Server - Closing connection from {client_address}")
            async with self.lock:
                self.client = None

    async def process_send_messages(self) -> None:
        """
        Continuously send messages from the send queue to the connected client.
        """

        logger = LoggerManager.get_logger(__name__)

        while self.running:
            if self.client:
                try:
                    message = await self.send_queue.get()
                    await self.send_message(message)
                except Exception as e:
                    logger.error(f"WebSocket Server - Error processing messages to send", e)
            else:
                await asyncio.sleep(0.5)

    async def send_message(self, message: dict) -> None:
        """
        Send a message to the connected WebSocket client.

        Args:
            message (dict): The message to send.
        """

        logger = LoggerManager.get_logger(__name__)

        async with self.lock:
            if self.client:
                try:
                    message = json.dumps(message)
                    logger.debug(f"Message sent: {message}")
                    await self.client.send(message)
                except Exception as e:
                    logger.error(f"WebSocket Server - Failed to send message", e)
            else:
                logger.warning("WebSocket Server - No client is connected.")

    async def start_server(self) -> None:
        """
        Start the WebSocket server and listen for incoming connections.
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            logger.info(f"WebSocket Server - Starting on {self.host}:{self.port}")

            async def connection_handler(websocket):
                await self.handle_client(websocket)

            async with websockets.serve(connection_handler, self.host, self.port):
                self.running = True
                asyncio.create_task(self.process_send_messages())
                await asyncio.Future()
        except Exception as e:
            logger.error(f"WebSocket Server - Failed to start", e)

    async def stop_server(self) -> None:
        """
        Gracefully stop the WebSocket server.
        """

        logger = LoggerManager.get_logger(__name__)

        logger.info("WebSocket Server - Stopping server...")
        self.running = False
        async with self.lock:
            if self.client:
                await self.client.close()
                self.client = None
