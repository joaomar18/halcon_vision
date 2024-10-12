import asyncio
from vision.data.comm import VisionCommunication
from vision.controller import VisionController
from vision.data.variables import *

class VisionSystem():
    """
    VisionSystem manages the vision controller and communication between the input and output queues.
    It processes incoming messages and coordinates actions within the vision system.

    Attributes:
        name (str): The name of the vision system.
        description (str): A description of the vision system.
        program_path (str): Path to the vision program.
        output_path (str): Path where the output data will be stored.
        init_program (int): Initial program to load.
    """

    def __init__(self, name: str, description: str, program_path: str, output_path: str, camera_construct_function, register_size: int = 32, init_program: int = 0):
        """
        Initialize the VisionSystem with the given parameters.

        Args:
            name (str): Name of the vision system.
            description (str): Description of the vision system.
            program_path (str): Path to the program.
            output_path (str): Path for output.
            camera_construct_function (function): Function to construct the camera.
            register_size (int, optional): Size of the register. Defaults to 32.
            init_program (int, optional): Initial program number. Defaults to 0.
        """
                
    ############################     P U B L I C     A T T R I B U T E S     ############################

        self.name = name
        self.description = description
        self.program_path = program_path
        self.output_path = output_path
        self.init_program = init_program

    ###########################     P R I V A T E     A T T R I B U T E S     ###########################

        self._communication = VisionCommunication(name, register_size, init_program)
        self._controller = VisionController(name, description, program_path, output_path, camera_construct_function, self._communication)
    
    ###############################     P U B L I C     M E T H O D S     ###############################

    def init(self):
        """
        Initialize the vision controller.
        """

        self._controller.init()

    async def process_incoming_messages(self, message):
        """
        Process incoming messages and route them accordingly.

        Args:
            message (dict): The incoming message.
        """

        try:
            if message[TYPE_KEY] == 'status':
                await self._process_status_message(message)
            elif message[TYPE_KEY] == 'request':
                await self._process_request(message)
        except KeyError as e:
            print(f"Error in Vision System: Missing key in message: {e}")

    def set_update_queue(self, queue: asyncio.Queue):
        """
        Set the update queue for input and output communication.

        Args:
            queue (asyncio.Queue): The queue for sending updates.
        """

        self._communication.inputs.set_update_inputs_queue(queue)
        self._communication.outputs.set_update_outputs_queue(queue)

    ##############################     P R I V A T E     M E T H O D S     ##############################

    async def _process_status_message(self, message: dict):
        """
        Handle status messages.

        Args:
            message (dict): The status message to process.
        """

        if message[DATA_KEY] == 'connected':
            await self._communication.inputs.send_all()
            await self._communication.outputs.send_all()

    async def _process_request(self, message: dict):
        """
        Handle request messages and update the system accordingly.

        Args:
            message (dict): The request message to process.
        """

        section = message.get(SECTION_KEY)

        if section == CONTROL_SECTION:
            await self._handle_control_section(message)
        elif section == PROGRAM_NUMBER_SECTION:
            self._communication.inputs.program_number = int(message[VALUE_KEY])
        elif section == INPUTS_SECTION:
            await self._handle_inputs_section(message)
 
    async def _handle_control_section(self, message: dict):
        """
        Handle control section updates from the request message.

        Args:
            message (dict): The control section message to process.
        """

        value = self._convert_string_to_bool(message[VALUE_KEY])
        self._communication.inputs.control[message[DATA_KEY]] = value

        if self._communication.inputs.control[TRIGGER]:
            await self._controller.camera_single_trigger()
        elif self._communication.inputs.control[PROGRAM_CHANGE]:
            await self._controller.camera_program_change()
        elif self._communication.inputs.control[RESET]:
            pass
        else:
            await self._handle_ready_state()

    async def _handle_ready_state(self):
        """
        Handle the ready state by checking for errors and setting the camera to ready.
        """

        if not self._communication.outputs.status[TRIGGER_ERROR] and not self._communication.outputs.status[PROGRAM_CHANGE_ERROR]:
            await self._controller.camera_set_ready()

    async def _handle_inputs_section(self, message: dict):
        """
        Handle input section updates from the request message.

        Args:
            message (dict): The inputs section message to process.
        """

        value = self._convert_value_based_on_type(message[VALUE_KEY], message[VALUE_TYPE_KEY])
        index = int(message[VALUE_INDEX_KEY])

        self._communication.inputs.inputs_register[index].set_value(value)
        self._controller.set_camera_input(index, value)

    def _convert_string_to_bool(self, value: str) -> bool:
        """
        Convert the string message value into a boolean.

        Args:
            value (str): The value to convert.

        Returns:
            bool: The converted value.
        """

        return value == 'true'
    
    def _convert_value_based_on_type(self, value: str, value_type: str):
        """
        Convert a message value to the appropriate type.

        Args:
            value (str): The value to convert.
            value_type (str): The type to convert the value to.

        Returns:
            The converted value in the specified type.
        """

        try:
            if value_type == 'float':
                return float(value)
            elif value_type == 'int':
                return int(value)
            elif value_type == 'string':
                return str(value)
        except ValueError:
            print(f"Invalid value type: expected {value_type}, got {value}")
            return None
