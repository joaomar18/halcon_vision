from vision.data.comm import VisionCommunication
from vision.system import VisionSystem        
from vision.data.variables import *
import asyncio

class VisionManager():    
    """
    VisionManager is responsible for managing multiple VisionSystem instances and 
    handling incoming/outgoing messages via asynchronous queues.

    Attributes:
        _receiver_queue (asyncio.Queue): Queue for receiving incoming messages.
        _send_queue (asyncio.Queue): Queue for sending outgoing messages.
        _vision_systems (dict): A dictionary of VisionSystem instances.
        _vision_systems_name (set): A set of vision system names.
    """

    def __init__(self, receiver_queue: asyncio.Queue, send_queue: asyncio.Queue):
        """
        Initialize the VisionManager with receiver and send queues.

        Args:
            receiver_queue (asyncio.Queue): Queue for receiving incoming messages.
            send_queue (asyncio.Queue): Queue for sending outgoing messages.
        """

    ############################     P U B L I C     A T T R I B U T E S     ############################



    ###########################     P R I V A T E     A T T R I B U T E S     ###########################

        self._receiver_queue = receiver_queue
        self._send_queue = send_queue
        self._vision_systems: dict[str, VisionSystem] = dict()
        self._vision_systems_name: set[str] = set()
        asyncio.create_task(self._process_receiver_queue())
    
    ###############################     P U B L I C     M E T H O D S     ###############################

    async def add_vision_system(self, new_vision_system: VisionSystem):
        """
        Add a new VisionSystem to the manager.

        Args:
            new_vision_system (VisionSystem): The VisionSystem instance to add.
        """
        
        if new_vision_system.name not in self._vision_systems:
            self._vision_systems[new_vision_system.name] = new_vision_system
            new_vision_system.set_update_queue(self._send_queue)
            self._vision_systems_name.add(new_vision_system.name)
            new_vision_system.init()
    
    async def remove_vision_system(self, vision_system_name: str) -> None:
        """
        Remove a VisionSystem from the manager.

        Args:
            vision_system_name (str): The name of the VisionSystem to remove.
        """

        if vision_system_name in self._vision_systems:
            del self._vision_systems[vision_system_name]
            self._vision_systems_name.remove(vision_system_name)
    
    def get_vision_system_devices(self) -> list[str]:
        """
        Get the list of vision system devices.

        Returns:
            list[str]: A list of vision system names.
        """

        return list(self._vision_systems.keys())

    ##############################     P R I V A T E     M E T H O D S     ##############################

    async def _process_receiver_queue(self):
        """
        Continuously process messages from the receiver queue.
        """
        
        while True:
            try:
                message = await self._receiver_queue.get()
                await self._process_received_message(message)
            except Exception as e:
                print(f"Error processing message in Vision Manager: {e}")

    
    async def _process_received_message(self, message: dict):
        """
        Process a received message and route it to the appropriate handler.

        Args:
            message (dict): The received message to process.
        """

        try:
            peripheral = message.get(PERIPHERAL_KEY)
            if peripheral == 'frontend':
                await self._handle_frontend_message(message)
            elif peripheral in self._vision_systems_name:
                await self._handle_vision_system_message(peripheral, message)
            else:
                raise ValueError(f"Error in Vision Manager: Unknown peripheral: {peripheral}")
        except KeyError as e:
            print(f"Error in Vision Manager: Missing key in message: {e}")

    async def _handle_frontend_message(self, message: dict) -> None:
        """
        Handle messages coming from the frontend.

        Args:
            message (dict): The message from the frontend.
        """

        if message.get(TYPE_KEY) == 'status' and message.get(DATA_KEY) == 'connected':
            response = {
                PERIPHERAL_KEY: 'manager',
                TYPE_KEY: 'response',
                DATA_KEY: self.get_vision_system_devices()
            }
            await self._send_queue.put(response)

            for vision_system in self._vision_systems.values():
                await vision_system.process_incoming_messages(message)

    async def _handle_vision_system_message(self, vision_system_name: str, message: dict) -> None:
        """
        Handle messages coming to a vision system.

        Args:
            vision_system_name (str): The name of the vision system.
            message (dict): The message to process.
        """

        vision_system = self._vision_systems.get(vision_system_name)
        if vision_system:
            await vision_system.process_incoming_messages(message)