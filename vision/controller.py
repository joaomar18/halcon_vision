###########EXTERNAL IMPORTS############

import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

#######################################

#############LOCAL IMPORTS#############

from vision.camera import VisionCamera
from vision.data.comm import VisionCommunication
from vision.data.variables import *
from util.debug import LoggerManager

#######################################


class VisionController:
    """
    VisionController is responsible for managing the vision camera, handling input/output communication,
    and executing vision programs. It acts as the central point of control for the camera operations,
    including triggering captures, changing programs, and processing camera outputs.

    Attributes:
        name (str): Name of the vision controller.
        description (str): Description of the vision controller.
        program_path (str): Path to the camera program.
        output_path (str): Path to output the camera data.
        create_camera (function): Function to create the camera (open, trigger, program, display procedures).
        communication_data (VisionCommunication): Object managing the communication inputs and outputs.
        inputs (VisionInputs): Inputs communication data.
        outputs (VisionOutputs): Outputs communication data.
        executor (ThreadPoolExecutor): Thread pool for executing camera tasks asynchronously.
        camera (VisionCamera): Camera object created using the provided program path and procedures.
        lock (asyncio.Lock): Async lock for ensuring thread-safe access to camera operations.
    """

    def __init__(
        self,
        name: str,
        description: str,
        program_path: str,
        output_path: str,
        create_camera,
        communication_data: VisionCommunication,
    ):

        self.name = name
        self.description = description
        self.program_path = program_path
        self.output_path = output_path
        self.create_camera = create_camera
        self.communication_data = communication_data
        self.inputs = self.communication_data.inputs
        self.outputs = self.communication_data.outputs

        self.executor = ThreadPoolExecutor(max_workers=1)

        (
            self.open_camera,
            self.trigger_camera,
            self.programs_camera,
            self.displays_camera,
        ) = create_camera(program_path)
        self.camera = VisionCamera(
            name,
            description,
            output_path,
            self.open_camera,
            self.trigger_camera,
            self.programs_camera,
            self.displays_camera,
        )

        self.lock = asyncio.Lock()

    async def init(self) -> None:
        """
        Initialize the camera and start the necessary async tasks.
        """

        sucess = self.camera.init()
        if sucess:
            asyncio.gather(self.change_camera_program(self.inputs.program_number))
            asyncio.get_event_loop().create_task(self.camera_set_ready())

    def set_camera_input(self, index, value) -> None:
        """
        Set the input for the camera program.

        :param index: Input index
        :param value: Input value
        """

        self.camera.set_program_input(index, value)

    async def camera_set_ready(self) -> None:
        """
        Reset camera status and set it to ready.
        """

        async with self.lock:
            self.reset_camera_status()
            await self.outputs.send_status()

    async def camera_single_trigger(self) -> None:
        """
        Trigger the camera for a single capture.
        """

        logger = LoggerManager.get_logger(__name__)

        async with self.lock:
            if self.outputs.status[READY]:
                self.update_status(run=True, ready=False)
                await self.outputs.send_status()

                sucess = await asyncio.get_event_loop().run_in_executor(
                    self.executor, self.camera.execute_program
                )

                if sucess:
                    logger.debug("Camera display processing")

                    self.process_camera_outputs()
                    self.update_status(run=False, trigger_acknowledge=True)
                    await self.outputs.send_status()
                    await self.outputs.send_outputs()
                    self.update_statistics()
                    await self.outputs.send_statistics()

                    while not self.camera.is_display_complete():
                        await asyncio.sleep(0.01)

                    self.update_status(new_image=(not self.outputs.status[NEW_IMAGE]))
                    await self.outputs.send_status()

                    logger.debug("Finished camera display processing")

                else:
                    self.update_status(run=False, trigger_error=True)
                    await self.outputs.send_status()

    async def camera_program_change(self) -> None:
        """
        Change the camera program.
        """

        async with self.lock:
            if self.outputs.status[READY]:

                self.update_status(run=True, ready=False)
                await self.outputs.send_status()

                sucess = await self.change_camera_program(self.inputs.program_number)

                if sucess:
                    self.update_status(run=False, program_change_acknowledge=True)
                else:
                    self.update_status(run=False, program_change_error=True)
                    await self.outputs.send_program_number_acknowledge()

                await self.outputs.send_status()

    def process_camera_outputs(self) -> None:
        """
        Process the outputs received from the camera and update output registers.
        """

        program_output = self.camera.get_program_output()
        for i, output in enumerate(program_output):
            output = self.get_output_value(output, self.outputs.outputs_variables[i][1])
            self.outputs.outputs_register[i].set_value(output)

    def get_output_value(self, output, var_type: str):
        """
        Determine the correct output value based on its type.

        :param output: The output value from the camera program
        :param var_type: The type of the output variable (int, float, string)
        :return: Processed output value
        """

        if len(output) == 1:
            return output[0]
        elif len(output) == 0:
            if var_type == "int":
                return 0
            elif var_type == "float":
                return 0.0
            elif var_type == "string":
                return ""
            else:
                return None

    def update_status(self, **kwargs) -> None:
        """
        Update multiple status flags at once.

        :param kwargs: Status flags to update (e.g., run=True, ready=False)
        """

        for key, value in kwargs.items():
            self.outputs.status[key] = value

    def update_statistics(self) -> None:
        """
        Update camera run time statistics.
        """

        self.outputs.statistics[MIN_RUN_TIME] = self.camera.get_min_run_time()
        self.outputs.statistics[RUN_TIME] = self.camera.get_run_time()
        self.outputs.statistics[MAX_RUN_TIME] = self.camera.get_max_run_time()

    def reset_camera_status(self) -> None:
        """
        Reset all camera status flags to their initial values.
        """

        self.outputs.status[TRIGGER_ACKNOWLEDGE] = False
        self.outputs.status[PROGRAM_CHANGE_ACKNOWLEDGE] = False
        self.outputs.status[TRIGGER_ERROR] = False
        self.outputs.status[PROGRAM_CHANGE_ERROR] = False
        self.outputs.status[RUN] = False
        self.outputs.status[READY] = True

    def reset_variable_list(self, variable_list: list[list[str]]) -> None:
        """
        Reset the provided variable list to None.

        :param variable_list: List of variables to reset
        """

        for index in range(len(variable_list)):
            variable_list[index] = None

    def reset_register_values(self, register_list: list[Variable]) -> None:
        """
        Reset the values in the provided register list to 0.

        :param register_list: List of register variables
        """

        for value in register_list.copy():
            value.set_value(0)

    def reset_camera_variables(self) -> None:
        """
        Reset all input/output variables and statistics.
        """

        self.outputs.statistics[MIN_RUN_TIME] = 0
        self.outputs.statistics[RUN_TIME] = 0
        self.outputs.statistics[MAX_RUN_TIME] = 0

        self.reset_variable_list(self.inputs.inputs_variables)
        self.reset_register_values(self.inputs.inputs_register)
        self.reset_variable_list(self.outputs.outputs_variables)
        self.reset_register_values(self.outputs.outputs_register)

    async def change_camera_program(self, program_number: int) -> bool:
        """
        Change the camera program and reset related variables.

        :param program_number: The new program number to be set
        """

        if not self.camera.set_active_program(program_number):
            return False
        self.outputs.program_number_acknowledge = self.camera.get_program_number()

        self.reset_camera_variables()

        program_input_variables = self.camera.get_program_input_variables()
        for index, variable in program_input_variables.items():
            self.inputs.inputs_variables[index] = variable

        program_output_variables = self.camera.get_program_output_variables()
        for index, variable in program_output_variables.items():
            self.outputs.outputs_variables[index] = variable

        for i in range(len(program_input_variables)):
            self.camera.set_program_input(i, self.inputs.inputs_register[i].value)

        await self.outputs.send_program_number_acknowledge()
        await self.inputs.send_inputs_variables()
        await self.inputs.send_inputs()
        await self.outputs.send_outputs_variables()
        await self.outputs.send_outputs()
        await self.outputs.send_statistics()

        return True
