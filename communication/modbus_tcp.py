###########EXTERNAL IMPORTS############

import asyncio
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import logging

#######################################

#############LOCAL IMPORTS#############

from util.debug import LoggerManager
from vision.manager import VisionManager, VisionSystem
from vision.controller import VisionController
from vision.data.comm import VisionCommunication, VisionInputs, VisionOutputs

#######################################

LoggerManager.get_logger(__name__).setLevel(logging.DEBUG)


class RegisterType(Enum):
    """Type of register in the modbus mapping"""

    INPUT = "input"
    OUTPUT = "output"


@dataclass
class ModbusAddressMapping:
    """
    Maps a device's registers to specific addresses in the Modbus server

    Attributes:
        device_name: Name of the vision system device
        register_type: Whether this maps to inputs or outputs
        first_coil_address: Starting address for coils (bit values)
        coil_count: Number of coils allocated
        first_register_address: Starting address for holding registers (word values)
        register_count: Number of registers allocated
    """

    device_name: str
    register_type: RegisterType
    first_coil_address: int
    coil_count: int
    first_register_address: int
    register_count: int


class ModbusTCPServer:
    """
    ModbusTCPServer manages a Modbus TCP server with configurable data blocks for coils,
    discrete inputs, holding registers and input registers.

    Attributes:
        host (str): The host address for the Modbus TCP server
        port (int): The port for the Modbus TCP server
        context (ModbusServerContext): The Modbus server context containing all data blocks
        running (bool): Flag indicating if server is running
    """

    def __init__(self, host: str, port: int, vision_manager: VisionManager):
        self.host = host
        self.port = port
        self.vision_manager = vision_manager
        self.server = None
        self.running = False

        # Initialize mappings for device address spaces
        self.address_mappings: List[ModbusAddressMapping] = []

        # Initialize data blocks
        self.context = ModbusServerContext(slaves=self.init_context(), single=True)

    def init_context(self) -> ModbusSlaveContext:
        """
        Initialize the Modbus server context with address mappings for all vision systems.

        This method:
        1. Iterates through all vision systems to calculate address space requirements
        2. Creates mappings for both INPUT and OUTPUT registers/coils for each device
        3. Pads address spaces to ensure each device ends on an address that is a multiple of 10
        4. Adds a buffer of 10 additional addresses at the end
        5. Creates and returns a ModbusSlaveContext with the calculated address spaces

        The addressing approach ensures:
        - Each vision system's inputs and outputs are clearly separated
        - Addresses end on multiples of 10 for easier identification and expansion
        - Adequate space is allocated for all required coils and registers

        Returns:
            ModbusSlaveContext: The initialized Modbus slave context with all data blocks
        """

        logger = LoggerManager.get_logger(__name__)

        total_coils = 0
        total_registers = 0

        for name, vision_system in self.vision_manager.vision_systems.items():

            input_coils = vision_system.communication.get_inputs_coil_size()
            input_registers = vision_system.communication.get_inputs_holdreg_size()

            self.address_mappings.append(
                ModbusAddressMapping(
                    device_name=name,
                    register_type=RegisterType.INPUT,
                    first_coil_address=total_coils + 1,
                    coil_count=input_coils,
                    first_register_address=total_registers + 1,
                    register_count=input_registers,
                )
            )
            logger.debug(
                f"{name}, {RegisterType.INPUT}, {total_coils + 1}, {input_coils}, {total_registers + 1}. {input_registers}"
            )

            total_coils += input_coils
            total_registers += input_registers

            output_coils = vision_system.communication.get_outputs_coil_size()
            output_registers = vision_system.communication.get_outputs_holdreg_size()

            self.address_mappings.append(
                ModbusAddressMapping(
                    device_name=name,
                    register_type=RegisterType.OUTPUT,
                    first_coil_address=total_coils + 1,
                    coil_count=output_coils,
                    first_register_address=total_registers + 1,
                    register_count=output_registers,
                )
            )
            logger.debug(
                f"{name}, {RegisterType.OUTPUT}, {total_coils + 1}, {output_coils}, {total_registers + 1}. {output_registers}"
            )

            total_coils += output_coils
            total_registers += output_registers

            if total_coils % 10 != 0:
                padding = 10 - (total_coils % 10)
                total_coils += padding

            if total_registers % 10 != 0:
                padding = 10 - (total_registers % 10)
                total_registers += padding

        total_coils += 10
        total_registers += 10

        store = ModbusSlaveContext(
            co=ModbusSequentialDataBlock(1, [0] * total_coils),
            hr=ModbusSequentialDataBlock(1, [0] * total_registers),
        )
        return store

    async def start_server(self) -> None:
        """
        Start the Modbus TCP server and listen for incoming connections.
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            logger.info(f"Modbus TCP Server - Starting on {self.host}:{self.port}")
            self.running = True

            # Start polling task for synchronizing vision system data
            self.update_task = asyncio.create_task(self.polling_loop())

            self.server = await StartAsyncTcpServer(
                context=self.context, address=(self.host, self.port)
            )

        except Exception as e:
            logger.error(f"Modbus TCP Server - Failed to start: {e}")
            self.running = False

    async def polling_loop(self) -> None:
        """
        Continuously poll vision systems and update Modbus registers.
        This keeps the Modbus server in sync with all vision systems.
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            logger.info("Starting Modbus Update Process")
            while self.running:
                self.sync_all_vision_systems()
                await asyncio.sleep(0.05)  # Poll every 50ms

        except Exception as e:
            logger.error(f"Error in Modbus polling loop: {e}", exc_info=True)
        finally:
            logger.info("Modbus polling loop stopped")

    def sync_all_vision_systems(self) -> None:
        """
        Synchronize all vision systems' state to Modbus registers.
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            for name, vision_system in self.vision_manager.vision_systems.items():

                input_mapping = next(
                    (
                        m
                        for m in self.address_mappings
                        if m.device_name == name
                        and m.register_type == RegisterType.INPUT
                    ),
                    None,
                )

                output_mapping = next(
                    (
                        m
                        for m in self.address_mappings
                        if m.device_name == name
                        and m.register_type == RegisterType.OUTPUT
                    ),
                    None,
                )

                if input_mapping:
                    self.sync_inputs(vision_system, input_mapping)

                if output_mapping:
                    self.sync_outputs(vision_system, output_mapping)

        except Exception as e:
            logger.error(f"Error syncing vision systems: {e}")

    def sync_inputs(
        self, vision_system: VisionSystem, mapping: ModbusAddressMapping
    ) -> None:
        """
        Synchronize input data from a vision system to Modbus registers.

        Args:
            vision_system: The vision system to sync from
            mapping: The address mapping for this vision system
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            # Get the controller from the vision system
            controller: VisionController = vision_system.controller

            control_bits = []
            for key, value in controller.inputs.control.items():
                control_bits.append(1 if value else 0)

            # Pad to required size
            while len(control_bits) < mapping.coil_count:
                control_bits.append(0)

            self.context[0].setValues(
                1, mapping.first_coil_address, control_bits[: mapping.coil_count]
            )

            registers = [controller.inputs.program_number]

            for reg in controller.inputs.inputs_register:
                if hasattr(reg, "value") and reg.value is not None:
                    if isinstance(reg.value, float):
                        # Multiply floats by 100 and convert to int
                        registers.append(int(reg.value * 100))
                    elif isinstance(reg.value, int):
                        registers.append(reg.value)
                    else:
                        registers.append(0)  # Default for non-numeric values
                else:
                    registers.append(0)

            # Trim or pad to match register count
            if len(registers) > mapping.register_count:
                registers = registers[: mapping.register_count]
            while len(registers) < mapping.register_count:
                registers.append(0)

            self.context[0].setValues(3, mapping.first_register_address, registers)

        except Exception as e:
            logger.error(f"Error syncing inputs for {vision_system.name}: {e}")

    def sync_outputs(
        self, vision_system: VisionSystem, mapping: ModbusAddressMapping
    ) -> None:
        """
        Synchronize output data from a vision system to Modbus registers.

        Args:
            vision_system: The vision system to sync from
            mapping: The address mapping for this vision system
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            controller: VisionController = vision_system.controller
            status_bits = []
            for value in controller.outputs.status.values():
                status_bits.append(1 if value else 0)

            # Pad to required size
            while len(status_bits) < mapping.coil_count:
                status_bits.append(0)

            # Update the coils in Modbus
            self.context[0].setValues(
                1, mapping.first_coil_address, status_bits[: mapping.coil_count]
            )

            # Sync output registers
            registers = [controller.outputs.program_number_acknowledge]

            # Add output register values
            for reg in controller.outputs.outputs_register:
                if hasattr(reg, "value") and reg.value is not None:
                    if isinstance(reg.value, float):
                        # Multiply floats by 100 and convert to int
                        registers.append(int(reg.value * 100))
                    elif isinstance(reg.value, int):
                        registers.append(reg.value)
                    else:
                        registers.append(0)
                else:
                    registers.append(0)

            # Trim or pad to match register count
            if len(registers) > mapping.register_count:
                registers = registers[: mapping.register_count]
            while len(registers) < mapping.register_count:
                registers.append(0)

            # Update registers in Modbus
            self.context[0].setValues(3, mapping.first_register_address, registers)

        except Exception as e:
            logger.error(f"Error syncing outputs for {vision_system.name}: {e}")

    async def stop_server(self) -> None:
        """
        Gracefully stop the Modbus TCP server.
        """

        logger = LoggerManager.get_logger(__name__)
        logger.info("Modbus TCP Server - Stopping server...")
        self.running = False

        if hasattr(self, "update_task") and self.update_task:
            try:
                self.update_task.cancel()
                await asyncio.gather(self.update_task, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error canceling polling task: {e}")

        if self.server is not None:
            try:
                self.server.server_close()
            except Exception as e:
                logger.error(f"Error closing server: {e}")
