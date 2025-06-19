###########EXTERNAL IMPORTS############

import asyncio
import logging

#######################################

#############LOCAL IMPORTS#############

from vision.data.comm import VisionCommunication
from vision.controller import VisionController
from vision.data.variables import *
from util.debug import LoggerManager

#######################################


class VisionSystem:
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

    def __init__(
        self,
        name: str,
        description: str,
        program_path: str,
        output_path: str,
        camera_construct_function,
        register_size: int = 32,
        init_program: int = 0,
    ):

        logger = LoggerManager.get_logger(__name__)

        try:

            self.name = name
            self.description = description
            self.program_path = program_path
            self.output_path = output_path
            self.init_program = init_program
            self.communication = VisionCommunication(name, register_size, init_program)
            self.controller = VisionController(
                name,
                description,
                program_path,
                output_path,
                camera_construct_function,
                self.communication,
            )

        except Exception as e:
            logger.error(f"{self.name}- Error initializing: {e}")

    async def init(self) -> None:
        """
        Initialize the vision controller.

        This method prepares the vision controller for operation by initializing any required
        resources asynchronously.
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            await self.controller.init()

        except Exception as e:
            logger.error(f"{self.name}- Error initializing controller: {e}")

    async def process_incoming_messages(self, message: dict) -> None:
        """
        Process incoming messages and route them based on their type.

        Args:
            message (dict): The incoming message, expected to contain a type key and associated data.

        Raises:
            ValueError: If the message type is invalid.
            KeyError: If the message type key is missing.
        """

        logger = LoggerManager.get_logger(__name__)

        try:

            message_type = message.get(TYPE_KEY)

            if message_type == "status":
                await self.process_status_message(message)
            elif message_type == "request":
                await self.process_request(message)
            else:
                if message_type:
                    raise ValueError(f"Invalid message type in {self.name}: {type}")
                else:
                    raise KeyError(f"Message type not found in {self.name}")
        except ValueError as e:
            logger.error(f"{self.name}- Value Error when processing incoming message: {e}")
        except KeyError as e:
            logger.error(f"{self.name}- Key Error when processing incoming message: {e}")
        except Exception as e:
            logger.error(f"{self.name}- Error processing incoming message: {e}")

    def set_update_queues(self, queues: list[asyncio.Queue]) -> None:
        """
        Set the queue for updating input and output communication.

        Args:
            queue (asyncio.Queue): The queue used for sending updates related to inputs and outputs.
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            self.communication.inputs.set_update_inputs_queues(queues)
            self.communication.outputs.set_update_outputs_queues(queues)

        except Exception as e:
            logger.error(f"{self.name}- Error setting update queue: {e}")

    async def process_status_message(self, message: dict) -> None:
        """
        Handle and process status messages received by the system.

        Args:
            message (dict): The status message, containing information about system status.

        Raises:
            ValueError: If the status message contains invalid data.
            KeyError: If data is missing from the status message.
        """

        logger = LoggerManager.get_logger(__name__)

        try:

            data = message.get(DATA_KEY)

            if data == "connected":
                await self.communication.inputs.send_all()
                await self.communication.outputs.send_all()
            else:
                if data:
                    raise ValueError(f"Invalid data in status message: {data}")
                else:
                    raise KeyError(f"Data not found in status message")

        except ValueError as e:
            logger.error(f"{self.name}- Value Error when processing status message: {e}")
        except KeyError as e:
            logger.error(f"{self.name}- Key Error when processing status message: {e}")
        except Exception as e:
            logger.error(f"{self.name}- Error processing status message: {e}")

    async def process_request(self, message: dict) -> None:
        """
        Process request messages and perform necessary updates to the system.

        Args:
            message (dict): The request message, containing a section and value to update.

        Raises:
            ValueError: If the section or value is invalid.
            KeyError: If the required keys are missing from the request message.
        """

        logger = LoggerManager.get_logger(__name__)

        logger.debug(f"Message in Processed Request: {message}")

        try:
            section = message.get(SECTION_KEY)

            if section == CONTROL_SECTION:
                await self.handle_control_section(message)
            elif section == PROGRAM_NUMBER_SECTION:
                self.communication.inputs.program_number = int(message[VALUE_KEY])
            elif section == INPUTS_SECTION:
                await self.handle_inputs_section(message)
            else:
                if section:
                    raise ValueError(f"Invalid section in request message: {section}")
                else:
                    raise KeyError(f"Section not found in request message")

        except ValueError as e:
            logger.error(f"{self.name}- Value Error when processing request message: {e}")
        except KeyError as e:
            logger.error(f"{self.name}- Key Error when processing request message: {e}")
        except Exception as e:
            logger.error(f"{self.name}- Error processing request message: {e}")

    async def handle_control_section(self, message: dict) -> None:
        """
        Handle control section updates from the request message.
        Supports both individual control updates and batch updates for multiple controls.

        Args:
            message (dict): The control section message, containing the control data and value to update.
                For single updates: Contains DATA_KEY and VALUE_KEY
                For batch updates: Contains BATCH_KEY and BATCH_VALUES_KEY with multiple control values

        Raises:
            ValueError: If the control data or value is invalid.
        """

        logger = LoggerManager.get_logger(__name__)

        try:

            batch_update = message.get(BATCH_KEY)

            if batch_update:

                values_keys: dict = message.get(BATCH_VALUES_KEY)
                if not values_keys:
                    raise ValueError(f"Didn't received any values to update from batch request")

                for control_key, control_value in values_keys.items():
                    if control_key not in self.communication.inputs.control:
                        logger.warning(f"Invalid control key in batch update: {control_key}")
                        continue

                    if isinstance(control_value, str):
                        value = self.convert_string_to_bool(control_value)
                    else:
                        value = bool(control_value)

                    self.communication.inputs.control[control_key] = value

            else:

                value_key = message.get(VALUE_KEY)
                data_key = message.get(DATA_KEY)

                if not data_key in self.communication.inputs.control:
                    raise ValueError(f"Invalid data key in control section: {data_key}")

                if isinstance(value_key, str):
                    value = self.convert_string_to_bool(value_key)
                else:
                    value = bool(value_key)

                self.communication.inputs.control[data_key] = value

            if self.communication.inputs.control[TRIGGER]:
                await self.controller.camera_single_trigger()
            elif self.communication.inputs.control[PROGRAM_CHANGE]:
                await self.controller.camera_program_change()
            elif self.communication.inputs.control[RESET]:
                await self.controller.camera_set_ready()
            else:
                await self.handle_ready_state()

        except ValueError as e:
            logger.error(f"{self.name}- Value Error when processing control section: {e}")
        except Exception as e:
            logger.error(f"{self.name}- Error processing control section: {e}")

    async def handle_ready_state(self) -> None:
        """
        Handle the ready state by checking for errors and setting the camera to a ready state.

        This method ensures that the system is in a valid state to perform actions by
        checking for errors in the communication outputs.
        """

        logger = LoggerManager.get_logger(__name__)

        try:

            if (
                not self.communication.outputs.status[TRIGGER_ERROR]
                and not self.communication.outputs.status[PROGRAM_CHANGE_ERROR]
            ):
                await self.controller.camera_set_ready()

        except Exception as e:
            logger.error(f"{self.name}- Error handling ready state", e)

    async def handle_inputs_section(self, message: dict) -> None:
        """
        Handle input section updates from the request message.
        Supports both individual register updates and batch updates for multiple registers.

        Args:
            message (dict): The inputs section message, containing the data for input update.
                For single updates: Contains VALUE_KEY, VALUE_TYPE_KEY, VALUE_INDEX_KEY
                For batch updates: Contains BATCH_KEY and BATCH_VALUES_KEY with multiple register values

        Raises:
            ValueError: If the input index or value is invalid.
            KeyError: If keys required for processing inputs are missing.
        """

        logger = LoggerManager.get_logger(__name__)

        try:

            batch_update = message.get(BATCH_KEY)

            if batch_update:
                values_keys: dict = message.get(BATCH_VALUES_KEY)

                if not values_keys:
                    raise ValueError(f"Didn't received any values to update from batch request")

                for index, value_info in values_keys.items():
                    try:
                        index = int(index)

                        if index < 0 or index >= len(self.communication.inputs.inputs_register):
                            logger.warning(f"Invalid index in batch inputs update: {index}")
                            continue

                        if isinstance(value_info, dict):
                            value_str = value_info.get("value")
                            value_type = value_info.get("type", "int")  # Default to int if type not specified
                        else:
                            # If only value is provided, assume int type
                            value_str = str(value_info)
                            value_type = "int"

                        value = self.convert_value_based_on_type(value_str, value_type)

                        # Update register and camera
                        self.communication.inputs.inputs_register[index].set_value(value)
                        self.controller.set_camera_input(index, value)

                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error processing input at index {index}: {e}")

                logger.debug(f"Updated multiple input registers in batch: {len(values_keys)} registers")

            else:

                value_key = message.get(VALUE_KEY)
                value_type_key = message.get(VALUE_TYPE_KEY)
                value_index_key = message.get(VALUE_INDEX_KEY)

                if value_key is None or value_type_key is None or value_index_key is None:
                    raise KeyError(f"Missing key in inputs section message: {message}")

                index = int(value_index_key)

                if index < 0 or index >= len(self.communication.inputs.inputs_register):
                    raise ValueError(f"Invalid index in inputs section message: {index}")

                value = self.convert_value_based_on_type(value_key, value_type_key)

                self.communication.inputs.inputs_register[index].set_value(value)
                self.controller.set_camera_input(index, value)

                logger.debug(f"Updated single input register: index={index}, value={value}")

        except KeyError as e:
            logger.error(f"{self.name}- Key Error when processing inputs section: {e}")
        except ValueError as e:
            logger.error(f"{self.name}- Value Error when processing inputs section: {e}")
        except Exception as e:
            logger.error(f"{self.name}- Error processing inputs section: {e}")

    def convert_string_to_bool(self, value: str) -> bool:
        """
        Convert a string representation of a boolean value to a boolean.

        Args:
            value (str): The string value to convert. Should be either 'true' or 'false'.

        Returns:
            bool: The converted boolean value.

        Raises:
            ValueError: If the value is not 'true' or 'false'.
        """

        if value.lower() != "true" and value.lower() != "false":
            raise ValueError(f"Invalid boolean value: {value}")

        return value == "true"

    def convert_value_based_on_type(self, value: str, value_type: str):
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

        if value_type == "float":
            return float(value)
        elif value_type == "int":
            return int(value)
        elif value_type == "string":
            return str(value)
        else:
            raise ValueError(f"Invalid value type: {value_type}")
