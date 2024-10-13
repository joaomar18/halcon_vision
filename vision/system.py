import asyncio
from vision.data.comm import VisionCommunication
from vision.controller import VisionController
from vision.data.variables import *
from db.client import DBClient
import logging
import datetime

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

    def __init__(self, name: str, description: str, program_path: str, output_path: str, camera_construct_function, 
                 db_client: DBClient, logger: logging.Logger, register_size: int = 32, init_program: int = 0):
        """
        Initialize the VisionSystem with the given parameters.

        Args:
            name (str): Name of the vision system.
            description (str): Description of the vision system.
            program_path (str): Path to the vision program.
            output_path (str): Path for output data storage.
            camera_construct_function (function): Function to construct the camera.
            db_client (DBClient): Database client for storing logs and errors.
            logger (logging.Logger): Logger for logging system events and errors.
            register_size (int, optional): Size of the communication register. Defaults to 32.
            init_program (int, optional): Initial program number to load. Defaults to 0.
        """

        try:

            self.name = name
            self.description = description
            self.program_path = program_path
            self.output_path = output_path
            self.init_program = init_program
        
            self._db_client = db_client
            self._logger = logger
            self._communication = VisionCommunication(name, register_size, init_program)
            self._controller = VisionController(name, description, program_path, output_path, camera_construct_function, self._communication)
            self._db_client.create_table(f'{self.name}_error', [
                                         'id INTEGER PRIMARY KEY',
                                         'message TEXT',
                                         'date TEXT'])

        except Exception as e:           

            self._log_and_store_error(f"{self.name}- Error initializing", e)
    
    async def init(self):
        """
        Initialize the vision controller.

        This method prepares the vision controller for operation by initializing any required
        resources asynchronously.
        """

        try:

            await self._controller.init()
        
        except Exception as e:

            self._log_and_store_error(f"{self.name}- Error initializing controller", e)

    async def process_incoming_messages(self, message: dict):
        """
        Process incoming messages and route them based on their type.

        Args:
            message (dict): The incoming message, expected to contain a type key and associated data.

        Raises:
            ValueError: If the message type is invalid.
            KeyError: If the message type key is missing.
        """

        try:

            message_type = message.get(TYPE_KEY)

            if message_type == 'status':
                await self._process_status_message(message)
            elif message_type == 'request':
                await self._process_request(message)
            else:
                if message_type:
                    raise ValueError(f"Invalid message type in {self.name}: {type}")
                else:
                    raise KeyError(f"Message type not found in {self.name}")
        except ValueError as e:
            self._log_and_store_error(f"{self.name}- Value Error when processing incoming message", e)
        except KeyError as e:
            self._log_and_store_error(f"{self.name}- Key Error when processing incoming message", e)
        except Exception as e:
            self._log_and_store_error(f"{self.name}- Error processing incoming message", e)

    def set_update_queue(self, queue: asyncio.Queue):
        """
        Set the queue for updating input and output communication.

        Args:
            queue (asyncio.Queue): The queue used for sending updates related to inputs and outputs.
        """

        try:
            self._communication.inputs.set_update_inputs_queue(queue)
            self._communication.outputs.set_update_outputs_queue(queue)

        except Exception as e:
            self._log_and_store_error(f"{self.name}- Error setting update queue", e)

    async def _process_status_message(self, message: dict):
        """
        Handle and process status messages received by the system.

        Args:
            message (dict): The status message, containing information about system status.

        Raises:
            ValueError: If the status message contains invalid data.
            KeyError: If data is missing from the status message.
        """
        
        try:

            data = message.get(DATA_KEY)
            
            if data == 'connected':
                await self._communication.inputs.send_all()
                await self._communication.outputs.send_all()
            else:
                if data:
                    raise ValueError(f"Invalid data in status message: {data}")
                else:
                    raise KeyError(f"Data not found in status message")
        
        except ValueError as e:
            self._log_and_store_error(f"{self.name}- Value Error when processing status message", e)
        except KeyError as e:
            self._log_and_store_error(f"{self.name}- Key Error when processing status message", e)
        except Exception as e:
            self._log_and_store_error(f"{self.name}- Error processing status message", e)

    async def _process_request(self, message: dict):
        """
        Process request messages and perform necessary updates to the system.

        Args:
            message (dict): The request message, containing a section and value to update.

        Raises:
            ValueError: If the section or value is invalid.
            KeyError: If the required keys are missing from the request message.
        """

        try:
            
            section = message.get(SECTION_KEY)

            if section == CONTROL_SECTION:
                await self._handle_control_section(message)
            elif section == PROGRAM_NUMBER_SECTION:
                self._communication.inputs.program_number = int(message[VALUE_KEY])
            elif section == INPUTS_SECTION:
                await self._handle_inputs_section(message)
            else:
                if section:
                    raise ValueError(f"Invalid section in request message: {section}")
                else:
                    raise KeyError(f"Section not found in request message")
        
        except ValueError as e:
            self._log_and_store_error(f"{self.name}- Value Error when processing request message", e)
        except KeyError as e:
            self._log_and_store_error(f"{self.name}- Key Error when processing request message", e)
        except Exception as e:
            self._log_and_store_error(f"{self.name}- Error processing request message", e)
 
    async def _handle_control_section(self, message: dict):
        """
        Handle control section updates from the request message.

        Args:
            message (dict): The control section message, containing the control data and value to update.

        Raises:
            ValueError: If the control data or value is invalid.
        """

        try:
            
            value_key = message.get(VALUE_KEY)
            data_key = message.get(DATA_KEY)

            if not data_key in self._communication.inputs.control:
                raise ValueError(f"Invalid data key in control section: {data_key}")

            value = self._convert_string_to_bool(value_key)
            self._communication.inputs.control[data_key] = value

            if self._communication.inputs.control[TRIGGER]:
                await self._controller.camera_single_trigger()
            elif self._communication.inputs.control[PROGRAM_CHANGE]:
                await self._controller.camera_program_change()
            elif self._communication.inputs.control[RESET]:
                pass
            else:
                await self._handle_ready_state()
        
        except ValueError as e:
            self._log_and_store_error(f"{self.name}- Value Error when processing control section", e)
        except Exception as e:
            self._log_and_store_error(f"{self.name}- Error processing control section", e)

    async def _handle_ready_state(self):
        """
        Handle the ready state by checking for errors and setting the camera to a ready state.

        This method ensures that the system is in a valid state to perform actions by
        checking for errors in the communication outputs.
        """

        try:

            if not self._communication.outputs.status[TRIGGER_ERROR] and not self._communication.outputs.status[PROGRAM_CHANGE_ERROR]:
                await self._controller.camera_set_ready()

        except Exception as e:
            self._log_and_store_error(f"{self.name}- Error handling ready state", e)

    async def _handle_inputs_section(self, message: dict):
        """
        Handle input section updates from the request message.

        Args:
            message (dict): The inputs section message, containing the data for input update.

        Raises:
            ValueError: If the input index or value is invalid.
            KeyError: If keys required for processing inputs are missing.
        """

        try:
            
            value_key = message.get(VALUE_KEY)
            value_type_key = message.get(VALUE_TYPE_KEY)
            value_index_key = message.get(VALUE_INDEX_KEY)

            if value_key is None or value_type_key is None or value_index_key is None:
                raise KeyError(f"Missing key in inputs section message: {message}")
            
            index = int(value_index_key)

            if index < 0 or index >= len(self._communication.inputs.inputs_register):
                raise ValueError(f"Invalid index in inputs section message: {index}")
            
            value = self._convert_value_based_on_type(value_key, value_type_key)

            self._communication.inputs.inputs_register[index].set_value(value)
            self._controller.set_camera_input(index, value)
        
        except KeyError as e:
            self._log_and_store_error(f"{self.name}- Key Error when processing inputs section", e)
        except ValueError as e:
            self._log_and_store_error(f"{self.name}- Value Error when processing inputs section", e)
        except Exception as e:
            self._log_and_store_error(f"{self.name}- Error processing inputs section", e)

    def _convert_string_to_bool(self, value: str) -> bool:
        """
        Convert a string representation of a boolean value to a boolean.

        Args:
            value (str): The string value to convert. Should be either 'true' or 'false'.

        Returns:
            bool: The converted boolean value.

        Raises:
            ValueError: If the value is not 'true' or 'false'.
        """

        if value != 'true' and value != 'false':
            raise ValueError(f"Invalid boolean value: {value}")
        
        return value == 'true'
    
    def _convert_value_based_on_type(self, value: str, value_type: str):
        """
        Convert a string message value to its appropriate type.

        Args:
            value (str): The value to be converted.
            value_type (str): The type of the value ('float', 'int', or 'string').

        Returns:
            The converted value in the specified type.

        Raises:
            ValueError: If the value type is not supported.
        """
        
        if value_type == 'float':
            return float(value)
        elif value_type == 'int':
            return int(value)
        elif value_type == 'string':
            return str(value)
        else:
            raise ValueError(f"Invalid value type: {value_type}")

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
            self._db_client.insert_entry(f'{self.name}_error', ['message', 'date'], [full_message, str(datetime.datetime.now())])

        except Exception as e:
            self._logger.error(f"{self.name}- Error logging and storing error: {e}")
