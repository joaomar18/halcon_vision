from vision.data.comm import VisionCommunication
from vision.system import VisionSystem        
from vision.data.variables import *
from db.client import DBClient
import logging
import asyncio
import datetime

class VisionManager:
    """
    VisionManager is responsible for managing multiple VisionSystem instances and 
    handling incoming/outgoing messages via asynchronous queues.

    Attributes:
        _receiver_queue (asyncio.Queue): Queue for receiving incoming messages.
        _send_queue (asyncio.Queue): Queue for sending outgoing messages.
        _vision_systems (Dict[str, VisionSystem]): A dictionary of VisionSystem instances.
        _vision_systems_name (Set[str]): A set of vision system names.
        _db_client (DBClient): Database client for logging errors.
        _logger (logging.Logger): Logger for logging events and errors.
    """

    def __init__(self, receiver_queue: asyncio.Queue, send_queue: asyncio.Queue, db_client: DBClient, logger: logging.Logger):
        """
        Initialize the VisionManager with receiver and send queues.

        Args:
            receiver_queue (asyncio.Queue): Queue for receiving incoming messages.
            send_queue (asyncio.Queue): Queue for sending outgoing messages.
            db_client (DBClient): Database client for error logging.
            logger (logging.Logger): Logger for logging events and errors.
        """
        try:
            self._receiver_queue = receiver_queue
            self._send_queue = send_queue
            self._db_client = db_client
            self._logger = logger
            self._vision_systems: dict[str, VisionSystem] = {}
            self._vision_systems_name: set[str] = set()
            self._db_client.create_table('vision_manager_error', [
                                        'id INTEGER PRIMARY KEY',
                                        'message TEXT',
                                        'date TEXT'])
            asyncio.create_task(self._process_receiver_queue())
        except Exception as e:
            self._log_and_store_error(f"Vision Manager - Error initializing", e)

    async def add_vision_system(self, new_vision_system: VisionSystem):
        """
        Add a new VisionSystem to the manager asynchronously.

        Args:
            new_vision_system (VisionSystem): The VisionSystem instance to add.
        """

        if new_vision_system.name in self._vision_systems:
            self._logger.warning(f"Vision Manager - VisionSystem {new_vision_system.name} already exists, skipping.")
            return
        
        try:
            self._vision_systems[new_vision_system.name] = new_vision_system
            new_vision_system.set_update_queue(self._send_queue)
            self._vision_systems_name.add(new_vision_system.name)
            
            await new_vision_system.init()

        except Exception as e:
            self._log_and_store_error(f"Vision Manager - Error adding VisionSystem {new_vision_system.name}", e)

    async def remove_vision_system(self, vision_system_name: str):
        """
        Remove a VisionSystem from the manager.

        Args:
            vision_system_name (str): The name of the VisionSystem to remove.
        """

        if vision_system_name not in self._vision_systems:
            self._logger.warning(f"Vision Manager - VisionSystem {vision_system_name} does not exist")
            return
        
        try:
            del self._vision_systems[vision_system_name]
            self._vision_systems_name.remove(vision_system_name)
        except KeyError as e:
            self._log_and_store_error(f"Vision Manager - KeyError while removing VisionSystem {vision_system_name}", e)
        except Exception as e:
            self._log_and_store_error(f"Vision Manager - Error removing VisionSystem {vision_system_name}", e)
    
    def get_vision_system_devices(self) -> list[str]:
        """
        Get the list of vision system devices.

        Returns:
            List[str]: A list of vision system names.
        """

        return list(self._vision_systems.keys())

    async def _process_receiver_queue(self):
        """
        Continuously process messages from the receiver queue.
        """

        while True:
            try:
                message = await self._receiver_queue.get()
                await self._process_received_message(message)
            except Exception as e:
                self._log_and_store_error(f"Vision Manager - Error processing received message", e)

    async def _process_received_message(self, message: dict):
        """
        Process a received message and route it to the appropriate handler.

        Args:
            message (Dict[str, Any]): The received message to process.
        """

        try:
            peripheral = message.get(PERIPHERAL_KEY)
            if not peripheral:
                raise ValueError("peripheral key is not in message")
            
            if peripheral == 'frontend':
                await self._handle_frontend_message(message)
            elif peripheral in self._vision_systems_name:
                await self._handle_vision_system_message(peripheral, message)
            else:
                raise ValueError(f"Unknown peripheral: {peripheral}")

        except KeyError as e:
            self._log_and_store_error(f"Vision Manager - Missing key in message", e)
        except ValueError as e:
            self._log_and_store_error(f"Vision Manager - ValueError", e)
        except Exception as e:
            self._log_and_store_error(f"Vision Manager - General error in _process_received_message", e)

    async def _handle_frontend_message(self, message: dict):
        """
        Handle messages coming from the frontend.

        Args:
            message (Dict[str, Any]): The message from the frontend.
        """

        try:
            if message.get(TYPE_KEY) == 'status' and message.get(DATA_KEY) == 'connected':
                response = {
                    PERIPHERAL_KEY: 'manager',
                    TYPE_KEY: 'response',
                    DATA_KEY: self.get_vision_system_devices()
                }
                await self._send_queue.put(response)

                for vision_system in self._vision_systems.values():
                    await vision_system.process_incoming_messages(message)

            else:
                raise ValueError(f"Invalid message from frontend: {message}")
        except Exception as e:
            self._log_and_store_error(f"Vision Manager - Error processing frontend message", e)

    async def _handle_vision_system_message(self, vision_system_name: str, message: dict):
        """
        Handle messages coming to a vision system.

        Args:
            vision_system_name (str): The name of the vision system.
            message (Dict[str, Any]): The message to process.
        """

        vision_system = self._vision_systems.get(vision_system_name)
        if vision_system:
            try:
                await vision_system.process_incoming_messages(message)
            except Exception as e:
                self._log_and_store_error(f"Vision Manager - Error processing vision system {vision_system_name} message", e)
        else:
            self._log_and_store_error(f"Vision Manager - Unknown vision system: {vision_system_name}", None)

    def _log_and_store_error(self, message: str, exception: Exception = None):
        """
        Log and store error messages in the database.

        Args:
            message (str): The error message to log and store.
            exception (Exception, optional): The exception that triggered the error, if any.
        """
        try:
            if exception:
                full_message = f"{message} | Exception: {repr(exception)}"
            else:
                full_message = message
            self._logger.error(full_message)
            self._db_client.insert_entry(f'vision_manager_error', ['message', 'date'], [full_message, str(datetime.datetime.now())])

        except Exception as e:
            self._logger.error(f"Vision Manager - Error logging and storing error: {e}")