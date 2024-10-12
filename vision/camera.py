import halcon as ha
import concurrent.futures
from vision.procedure import VisionProcedure


class VisionCamera:
    """
    A class to control the vision camera and manage the execution of vision procedures.

    Attributes:
        name (str): The name of the camera.
        description (str): A description of the camera.
        output_path (str): The path where the output images are saved.
    """

    def __init__(self, name: str, description: str, output_path: str, open_procedure: VisionProcedure, trigger_procedure: VisionProcedure, process_procedures: list[VisionProcedure] = list(), display_procedures: list[VisionProcedure] = list()):
        """
        Initializes the VisionCamera class with the given parameters.

        Args:
            name (str): The name of the camera.
            description (str): The camera description.
            output_path (str): The path for saving output images.
            open_procedure (VisionProcedure): The procedure to open the camera.
            trigger_procedure (VisionProcedure): The procedure to trigger the camera.
            process_procedures (list[VisionProcedure], optional): Procedures for processing images. Defaults to [].
            display_procedures (list[VisionProcedure], optional): Procedures for displaying images. Defaults to [].
        """

    ############################     P U B L I C     A T T R I B U T E S     ############################

        self.name = name
        self.description = description
        self.output_path = output_path

    ###########################     P R I V A T E     A T T R I B U T E S     ###########################

        self._executor = concurrent.futures.ThreadPoolExecutor()
        self._open_procedure = open_procedure
        self._trigger_procedure = trigger_procedure
        self._camera_parameters = dict()
        self._process_procedures = process_procedures
        self._display_procedures = display_procedures
        self._workflow: list[VisionProcedure] = [self._trigger_procedure]
        self._displayflow: VisionProcedure = None
        self._program_number: int = 0
        self._run_time: float = 0
        self._min_run_time: float = 0
        self._max_run_time: float = 0

    ###############################     P U B L I C     M E T H O D S     ###############################

    def init(self):
        """Initializes the camera by running the open procedure and preparing the trigger."""

        self._open_procedure.run()
        self._prepare_trigger()

    def set_active_program(self, program_number: int):
        """Sets the active program and updates the workflow and display procedures."""

        if program_number > 0:
            self._workflow = [self._trigger_procedure, self._process_procedures[program_number-1]]
            self._displayflow = self._display_procedures[program_number-1]
            self._program_number = program_number
        else:
            self._workflow = [self._trigger_procedure]
            self._displayflow = None
            self._program_number = 0
        self._min_run_time = 0
        self._run_time = 0
        self._max_run_time = 0
    
    def execute_program(self):
        """Executes the current active program and returns a future for display execution."""

        display_iconic, display_control, elapsed_time = self._execute_workflow()
        self._get_statistics(elapsed_time)
        future = self._executor.submit(self._execute_display, display_iconic, display_control)
        return future
    
    def set_program_input(self, index: int, variable: int):
        """Sets the input variable for the active program."""

        if self._program_number > 0:
            self._workflow[1].set_input_control_by_index(index, variable)
    
    def get_program_output(self):
        """Gets the output of the active program."""

        if self._program_number > 0:
            output = self._workflow[1].get_output_control()
            return output
        return []

    def get_program_number(self):
        """Returns the current program number."""

        return self._program_number

    def get_run_time(self):
        """Returns the current runtime."""

        return self._run_time
    
    def get_min_run_time(self):
        """Returns the minimum runtime."""

        return self._min_run_time
    
    def get_max_run_time(self):
        """Returns the maximum runtime."""

        return self._max_run_time
    
    def get_program_input_variables(self) -> dict[int, list[str, str]]:
        """Gets the input variables for the active program."""

        if self._program_number > 0:
            output = self._workflow[1].get_input_control_variables()
            return output
        return {}
    
    def get_program_output_variables(self) -> dict[int, list[str, str]]:
        """Gets the output variables for the active program."""

        if self._program_number > 0:
            output = self._workflow[1].get_output_control_variables()
            return output
        return {}

    ##############################     P R I V A T E     M E T H O D S     ##############################

    def _prepare_trigger(self):
        """Prepares the trigger procedure by setting input controls based on camera parameters."""

        self._camera_parameters = self._open_procedure.get_output_control_dict()
        for parameter_name in self._camera_parameters.copy():
            if parameter_name in self._trigger_procedure._input_control_variables:
                self._trigger_procedure.set_input_control_by_name(parameter_name, self._camera_parameters[parameter_name])
    
    def _execute_workflow(self) -> tuple:
        """Executes the current workflow and returns the display input and elapsed time."""

        input_iconic = None
        input_control = None
        display_input_iconic = {}
        display_input_control = {}
        elapsed_time = 0.0

        for procedure in self._workflow:
            if input_iconic or input_control:
                self._set_procedure_inputs(procedure, input_iconic, input_control)

            procedure.run()
            input_iconic = procedure.get_output_iconic_dict()
            input_control = procedure.get_output_control_dict()
            display_input_iconic |= input_iconic
            display_input_control |= input_control
            elapsed_time += procedure.get_run_time()

        return display_input_iconic, display_input_control, elapsed_time

    def _set_procedure_inputs(self, procedure: VisionProcedure, iconic: dict, control: dict):
        """Sets the inputs for the procedure based on iconic and control variables."""
        
        if iconic:
            for var_name, value in iconic.items():
                if var_name in procedure._input_iconic_variables:
                    procedure.set_input_iconic_by_name(var_name, value)
        if control:
            for var_name, value in control.items():
                if var_name in procedure._input_control_variables:
                    procedure.set_input_control_by_name(var_name, value)

    def _execute_display(self, display_iconic: dict, display_control: dict):
        """Executes the display procedure or writes the image to disk."""

        if self._displayflow:
            self._set_procedure_inputs(self._displayflow, display_iconic, display_control)
            self._displayflow.run()
        elif 'Image' in display_iconic:
            ha.write_image(display_iconic['Image'], 'jpg', 0, self.output_path)
        
    def _get_statistics(self, elapsed_time:float):
        """Updates the runtime statistics based on the elapsed time."""

        self._run_time = elapsed_time
        if elapsed_time > self._max_run_time or self._max_run_time == 0:
            self._max_run_time = elapsed_time
        if elapsed_time < self._min_run_time or self._min_run_time == 0:
            self._min_run_time = elapsed_time

