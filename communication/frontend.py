import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed

class WebSocketServer:
    def __init__(self, host: str, port: int, receive_queue: asyncio.Queue, send_queue: asyncio.Queue):
        self._host = host
        self._port = port
        self._client = None
        self._receive_queue = receive_queue
        self._send_queue = send_queue
        asyncio.create_task(self.process_send_messages())

    async def handle_client(self, websocket, path):

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
        while True:
            if self._client:
                message = await self._send_queue.get()
                await self.send_message(message)
            else:
                await asyncio.sleep(1)

    async def send_message(self, message):
        if self._client:
            try:
                message = json.dumps(message)
                await self._client.send(message)
            except Exception as e:
                print(f"Exception while sending to client: {e}")
        else:
            print("No client is connected.")

    async def start_server(self):
        async with websockets.serve(self.handle_client, self._host, self._port):
            print(f'Serving WebSocket server on {self._host}:{self._port}')
            await asyncio.Future()