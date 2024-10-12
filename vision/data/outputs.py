import asyncio
from vision.data.variables import *

class VisionOutputs:
    """
    A class to manage and send vision output data from the camera device.
    
    Attributes:
        device_name (str): The name of the camera.
        status (dict): Status flags for the camera.
        statistics (dict): Runtime statistics.
        program_number_acknowledge (int): Acknowledged program number.
        outputs_variables (List[List[str]]): A list of output variables.
        outputs_register (List[HalconVariable]): A list of register variables to handle camera output.
    """

    def __init__(self, device_name:str, register_size: int):
        """
        Initializes the VisionOutputs class with the specified device name and register size.

        Args:
            device_name (str): The name of the peripheral device.
            register_size (int): The size of the register for output variables.
        """

    ############################     P U B L I C     A T T R I B U T E S     ############################
        
        self.device_name = device_name

        self.status = {READY: False,
                       RUN: False,
                       TRIGGER_ACKNOWLEDGE: False,
                       PROGRAM_CHANGE_ACKNOWLEDGE: False,
                       TRIGGER_ERROR: False,
                       PROGRAM_CHANGE_ERROR: False,
                       NEW_IMAGE:False}
        
        self.statistics = {MIN_RUN_TIME: 0.0,
                           RUN_TIME: 0.0,
                           MAX_RUN_TIME: 0.0}

        self.program_number_acknowledge = 0
        self.outputs_variables: list[list[str]] = [None for _ in range(register_size)]
        self.outputs_register: list[HalconVariable] = list(HalconVariable() for _ in range(register_size))

    ###########################     P R I V A T E     A T T R I B U T E S     ###########################
        
        self._update_outputs_queue: asyncio.Queue = None

    ###############################     P U B L I C     M E T H O D S     ###############################

    def set_update_outputs_queue(self, queue: asyncio.Queue):
        """
        Sets the queue for sending update messages asynchronously.

        Args:
            queue (asyncio.Queue): An asyncio queue to send messages to.

        Raises:
            ValueError: If the provided queue is not valid.
        """

        if not isinstance(queue, asyncio.Queue):
            raise ValueError("queue must be a valid asyncio.Queue")
        self._update_outputs_queue = queue
    
    async def send_status(self):
        """Sends the current status to the queue."""

        await self._send_message(type='status',
                                 section='status',
                                 value=self.status)        

    async def send_statistics(self):
        """Sends the current statistics to the queue."""

        await self._send_message(type='status',
                                 section='statistics',
                                 value=self.statistics)  
    
    async def send_program_number_acknowledge(self):
        """Sends the acknowledged program number to the queue."""

        await self._send_message(type='status',
                                 section='program_number_acknowledge',
                                 value=self.program_number_acknowledge)         
    
    async def send_outputs_variables(self):
        """Sends the output variables to the queue."""

        await self._send_message(type='status',
                                 section='outputs_variables',
                                 value=self.outputs_variables)       

    async def send_outputs(self):
        """Sends the current output register values to the queue."""

        await self._send_message(type='status',
                                 section='outputs_register',
                                 value=HalconVariable.serialize_list(self.outputs_register))

    async def send_all(self):
        """Sends all data (status, statistics, program number, output variables, output register) to the queue."""

        await self.send_status()
        await self.send_statistics()
        await self.send_program_number_acknowledge()
        await self.send_outputs_variables()
        await self.send_outputs()

    ##############################     P R I V A T E     M E T H O D S     ##############################
       
    async def _send_message(self, type: str, section: str, value):
        """
        Sends a message to the update outputs queue.

        Args:
            type (str): The type of the message (e.g., 'status').
            section (str): The section of the message (e.g., 'status', 'statistics').
            value: The value to be sent.

        Raises:
            RuntimeError: If the update outputs queue is not set.
        """

        if self._update_outputs_queue is None:
            raise RuntimeError("Update outputs queue is not set.")
                
        message = {PERIPHERAL_KEY:self.device_name,
                   TYPE_KEY:type,
                   SECTION_KEY:section,
                   VALUE_KEY:value}
            
        await self._update_outputs_queue.put(message)