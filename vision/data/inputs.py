import asyncio
from vision.data.variables import *

class VisionInputs:
    """
    A class to manage and send vision input data to the peripheral device.
    
    Attributes:
        device_name (str): Name of the camera.
        control (dict): Control flags for the camera.
        program_number (int): Current input program number.
        inputs_variables (List[List[str]]): A list of input variables and their types.
        inputs_register (List[HalconVariable]): A list of register variables to get camera output.
    """

    def __init__(self, device_name: str, register_size: int, init_program: int):
        """
        Initializes the VisionInputs class with the specified device name, register size, and initial program.

        Args:
            device_name (str): The name of the camera.
            register_size (int): The size of the register for input variables.
            init_program (int): The initial program number to load.
        """

    ############################     P U B L I C     A T T R I B U T E S     ############################

        self.device_name = device_name

        self.control = {
            TRIGGER: False,
            PROGRAM_CHANGE: False,
            RESET: False,
        }
        
        self.program_number = init_program
        self.inputs_variables: list[list[str]] = [None for _ in range(register_size)]
        self.inputs_register: list[HalconVariable] = list(HalconVariable() for _ in range(register_size))

    ###########################     P R I V A T E     A T T R I B U T E S     ###########################

        self._update_inputs_queue: asyncio.Queue = None

    ###############################     P U B L I C     M E T H O D S     ###############################
    
    def set_update_inputs_queue(self, queue: asyncio.Queue):
        """
        Sets the queue for sending update messages asynchronously.
        
        Args:
            queue (asyncio.Queue): An asyncio queue to send messages to.
        
        Raises:
            ValueError: If the provided queue is None.
        """

        if not isinstance(queue, asyncio.Queue):
            raise ValueError("queue must be a valid asyncio.Queue")
        self._update_inputs_queue = queue

    async def send_control(self):
        """Sends the current control status to the queue."""

        await self._send_message(type='status',
                                 section='control',
                                 value=self.control)
    
    async def send_program_number(self):
        """Sends the current program number to the queue."""

        await self._send_message(type='status',
                                 section='program_number',
                                 value=self.program_number)

    async def send_inputs_variables(self):
        """Sends the current input variables to the queue."""

        await self._send_message(type='status', 
                                 section='inputs_variables', 
                                 value=self.inputs_variables)

    async def send_inputs(self):
        """Sends the current input register values to the queue."""

        await self._send_message(type='status', 
                                 section='inputs_register', 
                                 value=HalconVariable.serialize_list(self.inputs_register))
        
    async def send_all(self):
        """Sends all data (control, program number, input variables, input register) to the queue."""

        await self.send_control()
        await self.send_program_number()
        await self.send_inputs_variables()
        await self.send_inputs()

    ##############################     P R I V A T E     M E T H O D S     ##############################
       
    async def _send_message(self, type: str, section: str, value):
        """
        Sends a message to the update inputs queue.
        
        Args:
            type (str): The type of the message (e.g., 'status').
            section (str): The section of the message (e.g., 'control').
            value: The value to be sent.
        
        Raises:
            RuntimeError: If the update outputs queue is not set.
        """

        if self._update_inputs_queue is None:
            raise RuntimeError("Update inputs queue is not set.")
            
        message = {PERIPHERAL_KEY:self.device_name,
                   TYPE_KEY:type,
                   SECTION_KEY:section,
                   VALUE_KEY:value}
            
        await self._update_inputs_queue.put(message)