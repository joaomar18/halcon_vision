###########EXTERNAL IMPORTS############

import asyncio

#######################################

#############LOCAL IMPORTS#############

from vision.system import VisionSystem
from vision.data.variables import *
from util.debug import LoggerManager

#######################################


class VisionManager:
    """
    VisionManager is responsible for managing multiple VisionSystem instances and
    handling incoming/outgoing messages via asynchronous queues.

    Attributes:
        receiver_queue (asyncio.Queue): Queue for receiving incoming messages.
        send_queue (asyncio.Queue): Queue for sending outgoing messages.
        vision_systems (Dict[str, VisionSystem]): A dictionary of VisionSystem instances.
        vision_systems_name (Set[str]): A set of vision system names.
    """

    def __init__(
        self, receiver_queues: list[asyncio.Queue], send_queues: list[asyncio.Queue]
    ):

        logger = LoggerManager.get_logger(__name__)

        try:
            self.receiver_queues = receiver_queues
            self.send_queues = send_queues
            self.vision_systems: dict[str, VisionSystem] = {}
            self.vision_systems_name: set[str] = set()

            # Store queue processing tasks
            self.queue_tasks: list[asyncio.Task] = []

            # Initiate Receiver Queues Tasks
            self.init_queue_tasks()

        except Exception as e:
            logger.error(f"Vision Manager - Error initializing", e)

    def init_queue_tasks(self):

        for queue in self.receiver_queues:
            task = asyncio.create_task(self.process_receiver_queue(queue))
            self.queue_tasks.append(task)

    async def add_vision_system(self, new_vision_system: VisionSystem):
        """
        Add a new VisionSystem to the manager asynchronously.

        Args:
            new_vision_system (VisionSystem): The VisionSystem instance to add.
        """

        logger = LoggerManager.get_logger(__name__)

        if new_vision_system.name in self.vision_systems:
            logger.warning(
                f"Vision Manager - VisionSystem {new_vision_system.name} already exists, skipping."
            )
            return

        try:
            self.vision_systems[new_vision_system.name] = new_vision_system
            new_vision_system.set_update_queues(self.send_queues)
            self.vision_systems_name.add(new_vision_system.name)

            await new_vision_system.init()

        except Exception as e:
            logger.error(
                f"Vision Manager - Error adding Vision System {new_vision_system.name}: {e}"
            )

    async def remove_vision_system(self, vision_system_name: str):
        """
        Remove a VisionSystem from the manager.

        Args:
            vision_system_name (str): The name of the VisionSystem to remove.
        """

        logger = LoggerManager.get_logger(__name__)

        if vision_system_name not in self.vision_systems:
            logger.warning(
                f"Vision Manager - Vision System {vision_system_name} does not exist"
            )
            return

        try:
            del self.vision_systems[vision_system_name]
            self.vision_systems_name.remove(vision_system_name)
        except KeyError as e:
            logger.error(
                f"Vision Manager - KeyError while removing Vision System {vision_system_name}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Vision Manager - Error removing Vision System {vision_system_name}: {e}"
            )

    def get_vision_system_devices(self) -> list[str]:
        """
        Get the list of vision system devices.

        Returns:
            List[str]: A list of vision system names.
        """

        return list(self.vision_systems.keys())

    async def process_receiver_queue(self, queue: asyncio.Queue):
        """
        Continuously process messages from the receiver queue.
        """

        logger = LoggerManager.get_logger(__name__)

        while True:
            try:
                message = await queue.get()
                await self.process_received_message(message)
            except Exception as e:
                logger.error(f"Vision Manager - Error processing received message: {e}")

    async def process_received_message(self, message: dict):
        """
        Process a received message and route it to the appropriate handler.

        Args:
            message (Dict[str, Any]): The received message to process.
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            peripheral = message.get(PERIPHERAL_KEY)
            if not peripheral:
                raise KeyError("peripheral key is not in message")

            if peripheral == "frontend":
                await self.handle_frontend_message(message)
            elif peripheral in self.vision_systems_name:
                await self.handle_vision_system_message(peripheral, message)
            else:
                raise ValueError(f"Unknown peripheral: {peripheral}")

        except KeyError as e:
            logger.warning(f"Vision Manager - Missing key in message: {e}")
        except ValueError as e:
            logger.warning(f"Vision Manager - ValueError: {e}")
        except Exception as e:
            logger.error(
                f"Vision Manager - General error in process_received_message: {e}"
            )

    async def handle_frontend_message(self, message: dict):
        """
        Handle messages coming from the frontend.

        Args:
            message (Dict[str, Any]): The message from the frontend.
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            if (
                message.get(TYPE_KEY) == "status"
                and message.get(DATA_KEY) == "connected"
            ):
                response = {
                    PERIPHERAL_KEY: "manager",
                    TYPE_KEY: "response",
                    DATA_KEY: self.get_vision_system_devices(),
                }
                
                # Response message to frontend
                await self.send_queues[0].put(response)

                for vision_system in self.vision_systems.values():
                    await vision_system.process_incoming_messages(message)

            else:
                raise ValueError(f"Invalid message from frontend: {message}")
        except Exception as e:
            logger.error(f"Vision Manager - Error processing frontend message: {e}")

    async def handle_vision_system_message(
        self, vision_system_name: str, message: dict
    ):
        """
        Handle messages coming to a vision system.

        Args:
            vision_system_name (str): The name of the vision system.
            message (Dict[str, Any]): The message to process.
        """

        logger = LoggerManager.get_logger(__name__)

        vision_system = self.vision_systems.get(vision_system_name)
        if vision_system:
            try:
                await vision_system.process_incoming_messages(message)
            except Exception as e:
                logger.error(
                    f"Vision Manager - Error processing vision system {vision_system_name} message: {e}"
                )
        else:
            logger.warning(
                f"Vision Manager - Unknown vision system: {vision_system_name}"
            )
