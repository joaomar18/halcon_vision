###########EXTERNAL IMPORTS############

import asyncio
from pymodbus.server import StartAsyncTcpServer, ServerAsyncStop
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from dataclasses import dataclass
from enum import Enum
from typing import (
    Dict,
    List,
    Tuple,
    Sequence,
    Callable,
    Awaitable,
    Optional,
    Any,
)
import logging

#######################################

#############LOCAL IMPORTS#############

from util.debug import LoggerManager
import util.functions as functions
from vision.manager import VisionManager, VisionSystem
from vision.data.variables import *

#######################################

LoggerManager.get_logger(__name__).setLevel(logging.DEBUG)


class VariableDirection(Enum):
    """Direction of the variable in the modbus mapping"""

    INPUT = "input"
    OUTPUT = "output"


@dataclass
class ModbusRegister:
    """
    Represents a Modbus register with metadata for device identification and addressing.

    This dataclass encapsulates all necessary information to identify and interact with
    a Modbus register in the system. It includes information about which device the
    register belongs to, its section/purpose, address, data flow direction, and an
    optional descriptive name.

    Attributes:
        device_name (str): Name of the device/peripheral this register belongs to.
        register_section (str): Section or category of the register (e.g., "outputs", "inputs").
        register_adress (int): The Modbus address of this register within the server context.
        register_direction (VariableDirection): Indicates if this is an input or output register.
        register_name (Optional[str]): Optional human-readable name for the register.
    """

    device_name: str
    register_section: str
    register_adress: int
    register_direction: VariableDirection
    register_name: Optional[str] = None


@dataclass
class ModbusCoil:
    """
    Represents a Modbus coil with metadata for device identification and addressing.

    This dataclass encapsulates all necessary information to identify and interact with
    a Modbus coil in the system. It includes information about which device the
    coil belongs to, its section/purpose, address, data flow direction, and an
    optional descriptive name.

    Attributes:
        device_name (str): Name of the device/peripheral this coil belongs to.
        coil_section (str): Section or category of the coil (e.g., "status", "control").
        coil_address (int): The Modbus address of this coil within the server context.
        coil_direction (VariableDirection): Indicates if this is an input or output coil.
        coil_name (Optional[str]): Optional human-readable name for the coil.
    """

    device_name: str
    coil_section: str
    coil_address: int
    coil_direction: VariableDirection
    coil_name: Optional[str] = None


"""
Type definition for Modbus server callbacks.

Represents an async function that processes Modbus value changes with parameters:
- function_code: int - The Modbus function code
- address: int - The starting Modbus address that was changed
- values: Sequence[int | bool] - The new values (booleans for coils, integers for registers)

The callback must be an async function that returns None.
"""
CallbackType = Callable[[int, int, Sequence[int | bool]], Awaitable[None]]


class ObservableModbusSlaveContext(ModbusSlaveContext):
    """
    An extended ModbusSlaveContext that provides callbacks for value changes.

    This class extends the standard ModbusSlaveContext to allow registering callbacks
    that will be triggered whenever client devices write to the Modbus server. The callbacks
    are executed asynchronously to prevent blocking the Modbus communication.

    Callbacks receive the function code, address, and new values whenever a Modbus client
    changes register or coil values.
    """

    def __init__(
        self,
        *_args,
        di: ModbusSequentialDataBlock | None = None,
        co: ModbusSequentialDataBlock | None = None,
        ir: ModbusSequentialDataBlock | None = None,
        hr: ModbusSequentialDataBlock | None = None,
    ):
        super().__init__(*_args, di, co, ir, hr)
        self.callbacks: List[CallbackType] = []

    def register_callback(self, callback: CallbackType):
        """
        Register an async callback function to be called when values change.

        The callback should accept function code, address, and values parameters
        and must be an async function.

        Args:
            callback: An async function to call when values change

        Raises:
            ValueError: If the provided callback is not valid
        """

        if callback:
            self.callbacks.append(callback)
        else:
            raise ValueError(f"The callback {callback} is not valid")

    def run_callbacks(self, fc_has_hex: int, address: int, values: Sequence[int | bool]) -> None:
        """
        Schedule execution of all registered callbacks.

        This method creates a background task to run all registered callbacks
        asynchronously, without blocking the main Modbus server.

        Args:
            fc_has_hex: Function code of the Modbus operation
            address: Starting address of the affected registers/coils
            values: New values that were written
        """

        if not self.callbacks:
            return

        coroutines = [callback(fc_has_hex, address, values) for callback in self.callbacks]

        if coroutines:
            asyncio.create_task(self.process_callbacks(coroutines))

    async def process_callbacks(self, coroutines: List[CallbackType]) -> None:
        """
        Process all callback coroutines concurrently.

        This method awaits all the callback coroutines using asyncio.gather()
        to run them concurrently, and handles any exceptions that might occur.

        Args:
            coroutines: List of coroutine objects from callbacks
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            await asyncio.gather(*coroutines)
        except Exception as e:
            logger.error(f"Error processing callbacks in modbus server: {e}")

    def setValues(self, fc_as_hex: int, address: int, values: Sequence[int | bool]):
        """
        Override the setValues method to trigger callbacks after value changes.

        This method is called when Modbus clients write new values to the server.
        It updates the values in the data store and then triggers all registered callbacks.

        Args:
            fc_as_hex: Function code of the Modbus operation
            address: Starting address to update
            values: New values to set
        """

        super().setValues(fc_as_hex, address, values)
        self.run_callbacks(fc_as_hex, address, values)

    def setValuesInternal(self, fc_as_hex: int, address: int, values: Sequence[int | bool]):
        """
        Set values without triggering callbacks.

        This method allows internal code to update values without triggering
        the callbacks that are meant for external client changes.

        Args:
            fc_as_hex: Function code of the Modbus operation
            address: Starting address to update
            values: New values to set
        """

        super().setValues(fc_as_hex, address, values)


class ModbusTCPServer:

    def __init__(
        self,
        host: str,
        port: int,
        receive_queue: asyncio.Queue,
        send_queue: asyncio.Queue,
        vision_manager: VisionManager,
    ):
        self.host = host
        self.port = port
        self.receive_queue = receive_queue
        self.send_queue = send_queue
        self.vision_manager = vision_manager
        self.server = None
        self.running = False

        self.coils: List[ModbusCoil] = []
        self.registers: List[ModbusRegister] = []

        # Initialize data blocks
        self.context = ModbusServerContext(slaves=self.init_context(), single=True)

    def init_inputs(
        self,
        vision_system: VisionSystem,
        initial_coil_addr: int,
        initial_register_addr: int,
    ) -> Tuple[int, int]:
        """
        Initialize Modbus input coils and registers for a vision system.

        This method maps a vision system's input control flags to Modbus coils and
        maps the program number acknowledgment and input registers to Modbus holding registers.
        It automatically assigns sequential addresses starting from the provided
        initial addresses.

        Args:
            vision_system (VisionSystem): The vision system to initialize inputs for.
            initial_coil_addr (int): The starting Modbus address for input coils.
            initial_register_addr (int): The starting Modbus address for input registers.

        Returns:
            Tuple[int, int]: A tuple containing the next available coil address and
                            the next available register address after initialization.
                            These values can be used for initializing the next vision system.

        Note:
            This method populates the self.coils and self.registers lists with
            ModbusCoil and ModbusRegister objects with VariableDirection.INPUT direction.
        """

        current_coil = initial_coil_addr
        current_register = initial_register_addr

        # Control coils
        for key in vision_system.communication.get_inputs_control_dict().keys():

            self.coils.append(
                ModbusCoil(
                    device_name=vision_system.name,
                    coil_section=CONTROL_SECTION,
                    coil_name=key,
                    coil_address=current_coil,
                    coil_direction=VariableDirection.INPUT,
                )
            )

            # Increment current coil
            current_coil += 1

        # Program number acknowledge
        self.registers.append(
            ModbusRegister(
                device_name=vision_system.name,
                register_section=PROGRAM_NUMBER_SECTION,
                register_adress=current_register,
                register_direction=VariableDirection.INPUT,
            )
        )

        # Increment current register
        current_register += 1

        # Input Registers
        for i in range(0, len(vision_system.communication.get_inputs_registers_list())):

            self.registers.append(
                ModbusRegister(
                    device_name=vision_system.name,
                    register_section=INPUTS_SECTION,
                    register_adress=(current_register),
                    register_direction=VariableDirection.INPUT,
                )
            )

            # Increment current register
            current_register += 1

        return (current_coil, current_register)

    def init_outputs(
        self,
        vision_system: VisionSystem,
        initial_coil_addr: int,
        initial_register_addr: int,
    ) -> Tuple[int, int]:
        """
        Initialize Modbus output coils and registers for a vision system.

        This method maps a vision system's output status flags to Modbus coils and
        maps the program number and output registers to Modbus holding registers.
        It automatically assigns sequential addresses starting from the provided
        initial addresses.

        Args:
            vision_system (VisionSystem): The vision system to initialize outputs for.
            initial_coil_addr (int): The starting Modbus address for output coils.
            initial_register_addr (int): The starting Modbus address for output registers.

        Returns:
            Tuple[int, int]: A tuple containing the next available coil address and
                            the next available register address after initialization.
                            These values can be used for initializing the next vision system.

        Note:
            This method populates the self.coils and self.registers lists with
            ModbusCoil and ModbusRegister objects respectively.
        """

        current_coil = initial_coil_addr
        current_register = initial_register_addr

        # Control coils
        for key in vision_system.communication.get_outputs_status_dict().keys():

            self.coils.append(
                ModbusCoil(
                    device_name=vision_system.name,
                    coil_section=STATUS_SECTION,
                    coil_name=key,
                    coil_address=current_coil,
                    coil_direction=VariableDirection.OUTPUT,
                )
            )

            # Increment current coil
            current_coil += 1

        # Program number
        self.registers.append(
            ModbusRegister(
                device_name=vision_system.name,
                register_section=PROGRAM_NUMBER_ACKNOWLEDGE_SECTION,
                register_adress=current_register,
                register_direction=VariableDirection.OUTPUT,
            )
        )

        # Increment current register
        current_register += 1

        # Output Registers
        for i in range(0, len(vision_system.communication.get_outputs_register_list())):

            self.registers.append(
                ModbusRegister(
                    device_name=vision_system.name,
                    register_section=OUTPUTS_SECTION,
                    register_adress=(current_register),
                    register_direction=VariableDirection.OUTPUT,
                )
            )

            # Increment current register
            current_register += 1

        return (current_coil, current_register)

    def init_context(self) -> ObservableModbusSlaveContext:
        """
        Initialize the Modbus slave context with coils and registers for all vision systems.

        This method creates the Modbus data context by:
        1. Iterating through all vision systems registered with the vision manager
        2. Initializing input and output coils and registers for each system
        3. Padding addresses to nice boundaries (multiples of 100) for readability
        4. Creating a ModbusSlaveContext with appropriate data blocks

        The initialized context includes all control coils, status coils, program numbers,
        input registers, and output registers for all vision systems, with sufficient
        address space allocated.

        Returns:
            ModbusSlaveContext: A fully initialized Modbus slave context that can be
                            used with a Modbus server to handle register read/write operations.

        Note:
            This method depends on the init_inputs and init_outputs methods to populate
            the coils and registers lists, and on the round_to_nearest_100 utility function
            to ensure clean address boundaries between vision systems.
        """

        logger = LoggerManager.get_logger(__name__)

        current_coil = 1
        current_reg = 1

        for name, vision_system in self.vision_manager.vision_systems.items():

            (current_coil, current_reg) = self.init_inputs(vision_system, current_coil, current_reg)
            (current_coil, current_reg) = self.init_outputs(vision_system, current_coil, current_reg)

            current_coil = functions.round_to_nearest_10(current_coil)
            current_reg = functions.round_to_nearest_10(current_reg)

        store = ObservableModbusSlaveContext(
            co=ModbusSequentialDataBlock(1, [0] * current_coil),
            hr=ModbusSequentialDataBlock(1, [0] * current_reg),
        )

        store.register_callback(self.receive_client_updates)

        return store

    async def receive_client_updates(self, fc_has_hex: int, address: int, values: Sequence[int | bool]) -> None:

        logger = LoggerManager.get_logger(__name__)

        if fc_has_hex == 5:  # Coil Update:
            initial_coil = next(coil for coil in self.coils if coil.coil_address == address)
            if not initial_coil:
                logger.warning(f"Received coil update with unknown address: {address}")
                return

            message = {
                PERIPHERAL_KEY: initial_coil.device_name,
                TYPE_KEY: "request",
                SECTION_KEY: initial_coil.coil_section,
                DATA_KEY: initial_coil.coil_name,
                VALUE_KEY: values[0],
            }

            await self.receive_queue.put(message)

        elif fc_has_hex == 6:  # Register Update:
            initial_reg = next(reg for reg in self.registers if reg.register_adress == address)
            if not initial_reg:
                logger.warning(f"Received register update with unknown address: {address}")
                return

        elif fc_has_hex == 15:  # Multiple Coil updates

            initial_coil: ModbusCoil = None
            values_dict: Dict[str, bool] = {}

            for i, value in enumerate(values):

                coil = next(coil for coil in self.coils if coil.coil_address == address + i)
                if not coil:
                    logger.warning(f"Tried to write unknown coil address: {address + i}")
                    return

                if not initial_coil:
                    initial_coil = coil

                values_dict[coil.coil_name] = value

            if not initial_coil:
                logger.warning(f"Tried to write no coil addresses in the request")
                return

            message = {
                PERIPHERAL_KEY: initial_coil.device_name,
                TYPE_KEY: "request",
                BATCH_KEY: True,
                SECTION_KEY: initial_coil.coil_section,
                BATCH_VALUES_KEY: values_dict,
            }

            await self.receive_queue.put(message)

        elif fc_has_hex == 16:  # Multiple Register Updates:
            print(f"Received multiple registers update: Address: {address}, Values: {values}")

    async def start_server(self) -> bool:
        """
        Start the Modbus TCP server and related background tasks.

        This method initializes and starts the Modbus TCP server using PyModbus's
        StartAsyncTcpServer function. It also creates and starts two background tasks:
        one for processing update requests and another for processing receive requests.

        Returns:
            bool: True if the server was successfully started, False otherwise.
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            logger.info(f"Modbus TCP Server - Starting on {self.host}:{self.port}")
            self.running = True

            self.update_task = asyncio.create_task(self.process_update_requests())

            self.server = await StartAsyncTcpServer(context=self.context, address=(self.host, self.port))
            return True

        except Exception as e:
            logger.error(f"Modbus TCP Server - Failed to start: {e}")
            self.running = False
            return False

    async def process_update_requests(self) -> None:
        """
        Process incoming update requests from the queue and update the Modbus context.

        This method continuously monitors the send_queue for messages to update the
        Modbus server context. When a message is received, it concurrently processes
        updates for coils, program number acknowledgments, and output registers.

        The method runs as a background task as long as self.running is True,
        and handles any exceptions that occur during message processing to ensure
        the update loop continues running.

        Returns:
            None
        """

        logger = LoggerManager.get_logger(__name__)

        while self.running:
            try:
                message: dict[str, Any] = await self.send_queue.get()
                peripheral: str = message.get(PERIPHERAL_KEY)
                section: str = message.get(SECTION_KEY)
                value: Any = message.get(VALUE_KEY)

                asyncio.gather(
                    self.update_coils(peripheral, section, value),
                    self.update_program_number_ack(peripheral, section, value),
                    self.update_outputs_registers(peripheral, section, value),
                )
            except Exception as e:
                logger.error(f"WebSocket Server - Error processing update request", e)

    async def update_coils(self, peripheral: str, section: str, input_value: Any) -> None:
        """
        Update Modbus coils based on a message received from a vision system.

        This method processes status messages and updates the corresponding status coils
        in the Modbus server context. It specifically handles the STATUS_SECTION messages,
        extracting boolean values from the input dictionary and writing them to the
        appropriate coils in batch.

        Args:
            peripheral (str): The name of the peripheral/vision system
            section (str): The section of the message (e.g., "status")
            input_value (Any): The value to set, expected to be a dictionary for status coils

        Returns:
            None
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            if section in [STATUS_SECTION]:
                matching_coils: List[ModbusCoil] = [
                    coil for coil in self.coils if coil.device_name == peripheral and coil.coil_section == section
                ]

                if isinstance(input_value, Dict):
                    matching_coils.sort(key=lambda c: c.coil_address)

                    values: List[bool] = []

                    for key, value in input_value.items():
                        coil = next((c for c in matching_coils if c.coil_name == key), None)
                        if coil:
                            values.append(bool(value))

                    await self.write_batch_coils(32, matching_coils, values)

        except Exception as e:
            logger.error(f"Failed to update coils on the modbus server: {e}")

    async def update_program_number_ack(self, peripheral: str, section: str, input_value: Any) -> None:
        """
        Update the program number acknowledgment register in the Modbus server.

        This method processes program number acknowledgment messages and updates
        the corresponding register in the Modbus server context. It specifically
        handles PROGRAM_NUMBER_ACKNOWLEDGE_SECTION messages, setting the provided
        value in the appropriate register.

        Args:
            peripheral (str): The name of the peripheral/vision system
            section (str): The section of the message (e.g., "program_number_acknowledge")
            input_value (Any): The value to set in the program number acknowledge register,
                            expected to be an integer

        Returns:
            None
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            if section in [PROGRAM_NUMBER_ACKNOWLEDGE_SECTION]:
                matching_register: ModbusRegister = next(
                    reg
                    for reg in self.registers
                    if reg.device_name == peripheral and reg.register_section == PROGRAM_NUMBER_ACKNOWLEDGE_SECTION
                )
                if matching_register:
                    slave_context: ObservableModbusSlaveContext = self.context[0]
                    slave_context.setValuesInternal(3, matching_register.register_adress, [input_value])

        except Exception as e:
            logger.error(f"Failed to update program number acknowledge on the modbus server: {e}")

    async def update_outputs_registers(self, peripheral: str, section: str, input_value: Any):
        """
        Update output registers in the Modbus server based on vision system data.

        This method processes output register messages and updates the corresponding
        registers in the Modbus server context. It specifically handles OUTPUTS_SECTION
        messages, converting values as needed (multiplying float values by 100) and
        writing them in batch to the appropriate registers.

        Args:
            peripheral (str): The name of the peripheral/vision system
            section (str): The section of the message (e.g., "outputs_register")
            input_value (Any): The values to set, expected to be a list of numeric values
                            that can be converted to integers or floats

        Returns:
            None
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            if section in [OUTPUTS_SECTION]:
                matching_registers = [
                    reg
                    for reg in self.registers
                    if reg.device_name == peripheral and reg.register_section == OUTPUTS_SECTION
                ]

                if matching_registers and len(matching_registers) == len(input_value):
                    matching_registers.sort(key=lambda r: r.register_adress)

                    converted_values: List[int] = []

                    for reg_value in input_value:
                        current_value = 0
                        if functions.is_float(reg_value):
                            current_value = int(float(reg_value) * 100)
                        else:
                            current_value = int(reg_value)

                        converted_values.append(current_value)

                    await self.write_batch_hreg(32, matching_registers, converted_values)

                else:
                    if len(matching_registers) != len(input_value):
                        raise ValueError(
                            f"The length of the matching registers {len(matching_registers)} is not equal to the length of the values {len(input_value)}"
                        )

        except Exception as e:
            logger.error(f"Failed to update outputs registers on the modbus server: {e}")

    async def write_batch_coils(self, batch_size: int, list: List[ModbusCoil], values: List[bool]) -> None:
        """
        Write boolean values to Modbus coils in batches.

        This method writes a list of boolean values to Modbus coils, either in batches
        (if the coils have contiguous addresses) or individually. It prevents writing to
        coils configured as inputs by checking their direction before attempting to write.

        Args:
            batch_size (int): Maximum number of coils to update in a single operation
            list (List[ModbusCoil]): The coils to update
            values (List[bool]): The boolean values to write to the coils

        Returns:
            None

        Raises:
            ValueError: If any coil in the list has VariableDirection.INPUT
        """

        # Check if any coils have VariableDirection.INPUT
        input_coils = [coil for coil in list if coil.coil_direction == VariableDirection.INPUT]
        if input_coils:
            input_addresses = [coil.coil_address for coil in input_coils]
            raise ValueError(error_msg=f"Cannot write to INPUT coils at addresses: {input_addresses}")

        # Check if registers are contiguous
        if all(list[i].coil_address == list[0].coil_address + i for i in range(1, min(len(list), len(values)))):
            slave_context: ObservableModbusSlaveContext = self.context[0]
            for start_idx in range(0, len(values), batch_size):
                end_idx = min(start_idx + batch_size, len(values))
                batch_values = values[start_idx:end_idx]
                batch_address = list[start_idx].coil_address
                slave_context.setValuesInternal(1, batch_address, batch_values)
        else:
            slave_context: ObservableModbusSlaveContext = self.context[0]
            for i, value in enumerate(values):
                if i < len(list):
                    coil = list[i]
                    slave_context.setValuesInternal(1, coil.coil_address, [value])

    async def write_batch_hreg(self, batch_size: int, list: List[ModbusRegister], values: List[int]) -> None:
        """
        Write integer values to Modbus holding registers in batches.

        This method writes a list of integer values to Modbus holding registers, either
        in batches (if the registers have contiguous addresses) or individually. It
        prevents writing to registers configured as inputs by checking their direction
        before attempting to write.

        Args:
            batch_size (int): Maximum number of registers to update in a single operation
            list (List[ModbusRegister]): The registers to update
            values (List[int]): The integer values to write to the registers

        Returns:
            None

        Raises:
            ValueError: If any register in the list has VariableDirection.INPUT
        """

        # Check if any registers have VariableDirection.INPUT
        input_regs = [reg for reg in list if reg.register_direction == VariableDirection.INPUT]
        if input_regs:
            input_addresses = [reg.register_adress for reg in input_regs]
            raise ValueError(f"Cannot write to INPUT registers at addresses: {input_addresses}")

        # Check if registers are contiguous
        if all(list[i].register_adress == list[0].register_adress + i for i in range(1, min(len(list), len(values)))):
            slave_context: ObservableModbusSlaveContext = self.context[0]
            for start_idx in range(0, len(values), batch_size):
                end_idx = min(start_idx + batch_size, len(values))
                batch_values = values[start_idx:end_idx]
                batch_address = list[start_idx].register_adress
                slave_context.setValuesInternal(3, batch_address, batch_values)
        else:
            slave_context: ObservableModbusSlaveContext = self.context[0]
            for i, value in enumerate(values):
                if i < len(list):
                    reg = list[i]
                    slave_context.setValuesInternal(3, reg.register_adress, [value])

    async def stop_server(self) -> bool:
        """
        Stop the Modbus TCP server.

        This method stops the running Modbus server by setting the running flag to False
        and using the PyModbus ServerAsyncStop function to shut down the server.

        Returns:
            bool: True if the server was successfully stopped, False otherwise.
        """

        logger = LoggerManager.get_logger(__name__)
        logger.info("Modbus TCP Server - Stopping server...")
        self.running = False

        if self.update_task:
            try:
                self.update_task.cancel()
                await asyncio.gather(self.update_task, return_exceptions=True)
                self.update_task = None
            except Exception as e:
                logger.error(f"Error canceling update process: {e}")
                return False

        if self.server is not None:
            try:
                await ServerAsyncStop()
                self.server = None
            except Exception as e:
                logger.error(f"Error closing server: {e}")
                return False

        return True
