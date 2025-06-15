###########EXTERNAL IMPORTS############

import asyncio

#######################################

#############LOCAL IMPORTS#############

from vision.data.variables import *

#######################################


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

        self.device_name = device_name

        self.control = {
            TRIGGER: False,
            PROGRAM_CHANGE: False,
            RESET: False,
        }

        self.program_number = init_program
        self.inputs_variables: list[list[str]] = [None for _ in range(register_size)]
        self.inputs_register: list[HalconVariable] = list(
            HalconVariable() for _ in range(register_size)
        )
        self.update_inputs_queues: list[asyncio.Queue] = []

    def set_update_inputs_queues(self, queues: list[asyncio.Queue]) -> None:
        """
        Sets the queue for sending update messages asynchronously.

        Args:
            queue (asyncio.Queue): An asyncio queue to send messages to.

        Raises:
            ValueError: If the provided queue is None.
        """

        for queue in queues:
            if not isinstance(queue, asyncio.Queue):
                raise ValueError("queue must be a valid asyncio.Queue")
            self.update_inputs_queues.append(queue)

    async def send_control(self) -> None:
        """Sends the current control status to the queue."""

        await self.send_message(type="status", section="control", value=self.control)

    async def send_program_number(self) -> None:
        """Sends the current program number to the queue."""

        await self.send_message(
            type="status", section="program_number", value=self.program_number
        )

    async def send_inputs_variables(self) -> None:
        """Sends the current input variables to the queue."""

        await self.send_message(
            type="status", section="inputs_variables", value=self.inputs_variables
        )

    async def send_inputs(self) -> None:
        """Sends the current input register values to the queue."""

        await self.send_message(
            type="status",
            section="inputs_register",
            value=HalconVariable.serialize_list(self.inputs_register),
        )

    async def send_all(self) -> None:
        """Sends all data (control, program number, input variables, input register) to the queue."""

        await self.send_control()
        await self.send_program_number()
        await self.send_inputs_variables()
        await self.send_inputs()

    async def send_message(self, type: str, section: str, value) -> None:
        """
        Sends a message to the update inputs queue.

        Args:
            type (str): The type of the message (e.g., 'status').
            section (str): The section of the message (e.g., 'control').
            value: The value to be sent.

        Raises:
            RuntimeError: If the update outputs queue is not set.
        """

        if len(self.update_inputs_queues) == 0:
            raise RuntimeError("Update inputs queues are not set.")

        message = {
            PERIPHERAL_KEY: self.device_name,
            TYPE_KEY: type,
            SECTION_KEY: section,
            VALUE_KEY: value,
        }

        for queue in self.update_inputs_queues:
            await queue.put(message)
