import halcon as ha
import concurrent.futures
from vision.procedure import VisionProcedure


class VisionCamera:

    def __init__(self, name: str, description: str, output_path: str, open_procedure: VisionProcedure, trigger_procedure: VisionProcedure, process_procedures: list[VisionProcedure] = list(), display_procedures: list[VisionProcedure] = list()):
    
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
        
        self._open_procedure.run()
        self._prepare_trigger()

    def set_active_program(self, program_number: int):
        
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

        display_iconic, display_control, elapsed_time = self._execute_workflow()
        self._get_statistics(elapsed_time)
        future = self._executor.submit(self._execute_display, display_iconic, display_control)
        return future
    
    def set_program_input(self, index: int, variable: int):
        
        if self._program_number > 0:
            self._workflow[1].set_input_control_by_index(index, variable)
    
    def get_program_output(self):
        
        if self._program_number > 0:
            output = self._workflow[1].get_output_control()
            return output
        return []

    def get_program_number(self):

        return self._program_number

    def get_run_time(self):

        return self._run_time
    
    def get_min_run_time(self):

        return self._min_run_time
    
    def get_max_run_time(self):

        return self._max_run_time
    
    def get_program_input_variables(self) -> dict[int, list[str, str]]:
        
        if self._program_number > 0:
            output = self._workflow[1].get_input_control_variables()
            return output
        return {}
    
    def get_program_output_variables(self) -> dict[int, list[str, str]]:

        if self._program_number > 0:
            output = self._workflow[1].get_output_control_variables()
            return output
        return {}

    ##############################     P R I V A T E     M E T H O D S     ##############################

    def _prepare_trigger(self):

        self._camera_parameters = self._open_procedure.get_output_control_dict()
        for parameter_name in self._camera_parameters.copy():
            if parameter_name in self._trigger_procedure._input_control_variables:
                self._trigger_procedure.set_input_control_by_name(parameter_name, self._camera_parameters[parameter_name])
    
    def _execute_workflow(self):

        input_iconic: dict = None
        input_control: dict = None
        display_input_iconic: dict = dict()
        display_input_control: dict = dict()
        elapsed_time = 0
        for index, procedure in enumerate(self._workflow):
            if index > 0:
                for variable in input_iconic.copy():
                    if variable in procedure._input_iconic_variables:
                        procedure.set_input_iconic_by_name(variable, input_iconic[variable])
                for variable in input_control.copy():
                    if variable in procedure._input_control_variables:
                        procedure.set_input_control_by_name(variable, input_control[variable])
            procedure.run()
            input_iconic = procedure.get_output_iconic_dict()
            input_control = procedure.get_output_control_dict()
            display_input_iconic = display_input_iconic | input_iconic
            display_input_control = display_input_control | input_control   
            elapsed_time += procedure.get_run_time()  
        return display_input_iconic, display_input_control, elapsed_time  

    def _execute_display(self, display_iconic: dict, display_control: dict):

        if self._displayflow != None:
            for variable in display_iconic.copy():
                if variable in self._displayflow._input_iconic_variables:
                    self._displayflow.set_input_iconic_by_name(variable, display_iconic[variable])
            for variable in display_control.copy():
                if variable in self._displayflow._input_control_variables:
                    self._displayflow.set_input_control_by_name(variable, display_control[variable])
            self._displayflow.run()
        else:
            if 'Image' in display_iconic:
                ha.write_image(display_iconic['Image'], 'jpg', 0, self.output_path)
        
    def _get_statistics(self, elapsed_time:float):

        self._run_time = elapsed_time
        if elapsed_time > self._max_run_time or self._max_run_time == 0:
            self._max_run_time = elapsed_time
        if elapsed_time < self._min_run_time or self._min_run_time == 0:
            self._min_run_time = elapsed_time

