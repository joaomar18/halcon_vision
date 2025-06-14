###########EXTERNAL IMPORTS############

import halcon as ha
import concurrent.futures

#######################################

#############LOCAL IMPORTS#############

from vision.procedure import VisionProcedure
from util.debug import LoggerManager

#######################################


class VisionCamera:
    """
    A class to control the vision camera and manage the execution of vision procedures.

    Attributes:
        name (str): The name of the camera.
        description (str): A description of the camera.
        output_path (str): The path where the output images are saved.
    """

    def __init__(
        self,
        name: str,
        description: str,
        output_path: str,
        open_procedure: VisionProcedure,
        trigger_procedure: VisionProcedure,
        process_procedures: list[VisionProcedure] = list(),
        display_procedures: list[VisionProcedure] = list(),
    ):

        self.name = name
        self.description = description
        self.output_path = output_path
        self.executor = concurrent.futures.ThreadPoolExecutor()
        self.open_procedure = open_procedure
        self.trigger_procedure = trigger_procedure
        self.camera_parameters = dict()
        self.process_procedures = process_procedures
        self.display_procedures = display_procedures
        self.workflow: list[VisionProcedure] = [self.trigger_procedure]
        self.displayflow: VisionProcedure = None
        self.display_future: concurrent.futures.Future = None
        self.program_number: int = 0
        self.run_time: float = 0
        self.min_run_time: float = 0
        self.max_run_time: float = 0

    def init(self) -> bool:
        """Initializes the camera by running the open procedure and preparing the trigger.

        This method performs two main steps:
        1. Executes the camera's open procedure to establish connection
        2. Prepares the trigger settings based on camera parameters

        Returns:
            bool: True if initialization succeeds, False if any errors occur

        Raises:
            Exception: Any exceptions from open_procedure.run() or prepare_trigger()
            are caught and logged
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            self.open_procedure.run()
            self.prepare_trigger()
            return True
        except Exception as e:
            logger.error(f"Error initializing camera {self.name}: {e}")

        return False

    def set_active_program(self, program_number: int) -> bool:
        """Sets the active program and updates the workflow and display procedures.

        This method updates the camera's workflow by:
        1. Setting the workflow to [trigger_procedure, selected process_procedure]
        2. Setting the display procedure for the selected program
        3. Resetting all runtime statistics

        Args:
            program_number (int): Index of the program to activate (must be > 0)

        Returns:
            bool: True if program was successfully set, False if any errors occur

        Raises:
            ValueError: If program_number is negative
            Exception: Other exceptions during workflow setup are caught and logged
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            if program_number < 0:
                raise ValueError("Program Number is Invalid")

            if program_number > 0:
                self.workflow = [
                    self.trigger_procedure,
                    self.process_procedures[program_number - 1],
                ]
                self.displayflow = self.display_procedures[program_number - 1]
            else:
                self.workflow = [self.trigger_procedure]
                self.displayflow = []

            self.program_number = program_number
            self.min_run_time = 0
            self.run_time = 0
            self.max_run_time = 0
            return True

        except Exception as e:
            logger.error(
                f"Error changing camera {self.name} program to {program_number}: {e}"
            )
            if self.program_number > 0:
                self.workflow = [
                    self.trigger_procedure,
                    self.process_procedures[self.program_number - 1],
                ]
                self.displayflow = self.display_procedures[self.program_number - 1]
            else:
                self.workflow = [self.trigger_procedure]
                self.displayflow = []

        return False

    def execute_program(self) -> bool:
        """Executes the current active program and handles display asynchronously.

        This method:
        1. Executes the workflow and collects display data
        2. Updates runtime statistics
        3. Submits display execution to a thread pool executor
        4. Sets up callback for handling display results

        Returns:
            bool: True if program execution succeeds, False if any errors occur

        Raises:
            Exception: Any exceptions during execution are caught and logged

        Note:
            Display execution happens asynchronously in a separate thread
        """

        logger = LoggerManager.get_logger(__name__)

        try:

            display_iconic, display_control, elapsed_time = self.execute_workflow()
            self.get_statistics(elapsed_time)
            self.display_future = self.executor.submit(
                self.execute_display, display_iconic, display_control
            )
            self.display_future.add_done_callback(self.handle_display_result)
            return True
        except Exception as e:
            logger.error(
                f"Failed to execute program number {self.program_number} in camera {self.name}: {e}"
            )

        return False

    def handle_display_result(self, future: concurrent.futures.Future) -> None:
        """Callback to handle the result of asynchronous display execution.

        This method is called when the display execution future completes.
        It checks for any exceptions that occurred during display execution
        and logs errors if they occur.

        Args:
            future (concurrent.futures.Future): The completed future object
                containing the display execution result

        Raises:
            Exception: Any exceptions during display execution are caught and logged
        """

        logger = LoggerManager.get_logger(__name__)

        try:
            future.result()
        except Exception as e:
            logger.error(
                f"Failed to execute display program number {self.program_number} in camera {self.name}: {e}"
            )

    def is_display_complete(self) -> bool:
        """Check if the most recent display operation has completed.

        Returns:
            bool: True if no display is pending or if display has completed,
                False if display is still in progress
        """

        if self.display_future is None:
            return True
        return self.display_future.done()

    def set_program_input(self, index: int, variable: int) -> None:
        """Sets the input variable for the active program."""

        logger = LoggerManager.get_logger(__name__)

        try:
            if self.program_number > 0:
                self.workflow[1].set_input_control_by_index(index, variable)
        except Exception as e:
            logger.error(
                f"Failed to set input on program number {self.program_number} in camera {self.name}: {e}"
            )

    def get_program_output(self) -> list[ha.HTupleType]:
        """Gets the output of the active program."""

        if self.program_number > 0:
            output = self.workflow[1].get_output_control()
            return output
        return []

    def get_program_number(self) -> int:
        """Returns the current program number."""

        return self.program_number

    def get_run_time(self) -> float:
        """Returns the current runtime."""

        return self.run_time

    def get_min_run_time(self) -> float:
        """Returns the minimum runtime."""

        return self.min_run_time

    def get_max_run_time(self) -> float:
        """Returns the maximum runtime."""

        return self.max_run_time

    def get_program_input_variables(self) -> dict[int, list[str, str]]:
        """Gets the input variables for the active program."""

        if self.program_number > 0:
            output = self.workflow[1].get_input_control_variables()
            return output
        return {}

    def get_program_output_variables(self) -> dict[int, list[str, str]]:
        """Gets the output variables for the active program."""

        if self.program_number > 0:
            output = self.workflow[1].get_output_control_variables()
            return output
        return {}

    def prepare_trigger(self) -> None:
        """Prepares the trigger procedure by setting input controls based on camera parameters."""

        self.camera_parameters = self.open_procedure.get_output_control_dict()
        for parameter_name in self.camera_parameters.copy():
            if parameter_name in self.trigger_procedure.input_control_variables:
                self.trigger_procedure.set_input_control_by_name(
                    parameter_name, self.camera_parameters[parameter_name]
                )

    def execute_workflow(self) -> tuple:
        """Executes the current workflow and returns the display input and elapsed time."""

        input_iconic = None
        input_control = None
        display_input_iconic = {}
        display_input_control = {}
        elapsed_time = 0.0

        for procedure in self.workflow:
            if input_iconic or input_control:
                self.set_procedure_inputs(procedure, input_iconic, input_control)

            procedure.run()
            input_iconic = procedure.get_output_iconic_dict()
            input_control = procedure.get_output_control_dict()
            display_input_iconic |= input_iconic
            display_input_control |= input_control
            elapsed_time += procedure.get_run_time()

        return display_input_iconic, display_input_control, elapsed_time

    def set_procedure_inputs(
        self, procedure: VisionProcedure, iconic: dict, control: dict
    ) -> None:
        """Sets the inputs for the procedure based on iconic and control variables."""

        if iconic:
            for var_name, value in iconic.items():
                if var_name in procedure.input_iconic_variables:
                    procedure.set_input_iconic_by_name(var_name, value)
        if control:
            for var_name, value in control.items():
                if var_name in procedure.input_control_variables:
                    procedure.set_input_control_by_name(var_name, value)

    def execute_display(self, display_iconic: dict, display_control: dict) -> None:
        """Executes the display procedure or writes the image to disk."""

        if self.displayflow:
            self.set_procedure_inputs(self.displayflow, display_iconic, display_control)
            self.displayflow.run()
        elif "Image" in display_iconic:
            ha.write_image(display_iconic["Image"], "jpg", 0, self.output_path)

    def get_statistics(self, elapsed_time: float) -> None:
        """Updates the runtime statistics based on the elapsed time."""

        self.run_time = elapsed_time
        if elapsed_time > self.max_run_time or self.max_run_time == 0:
            self.max_run_time = elapsed_time
        if elapsed_time < self.min_run_time or self.min_run_time == 0:
            self.min_run_time = elapsed_time
