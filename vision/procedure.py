import halcon as ha
import time

def create_vision_procedure(program_directory, name, 
                            input_control:dict[str, str] = None, 
                            output_control:dict[str, str] = None, 
                            input_iconic:list[str] = None, 
                            output_iconic:list[str] = None):
    
    input_control_variables: list[str] =  []
    input_control_types: list[str] = []

    output_control_variables: list[str] = []
    output_control_types: list[str] = []

    if input_control != None:
        for variable, type in input_control.items():
            input_control_variables.append(variable)
            input_control_types.append(type)
    
    if output_control != None:
        for variable, type in output_control.items():
            output_control_variables.append(variable)
            output_control_types.append(type)

    return VisionProcedure(
        program_directory=program_directory,
        name=name,
        input_control_variables=input_control_variables,
        input_control_types=input_control_types,
        output_control_variables=output_control_variables,
        output_control_types=output_control_types,
        input_iconic_variables=input_iconic if input_iconic else [],
        output_iconic_variables=output_iconic if output_iconic else []
    )

def initialize_procedure(program_directory: str, procedure_name: str) -> ha.HDevProcedureCall:

    procedure_proc = ha.HDevProcedure.load_local(program_directory, procedure_name)
    procedure = ha.HDevProcedureCall(procedure_proc)
    return procedure



class VisionProcedure():

    def __init__(self, program_directory: str, name: str, input_iconic_variables: list, output_iconic_variables: list, 
                 input_control_variables: list, input_control_types: list, 
                 output_control_variables: list, output_control_types: list):
        
    ############################     P U B L I C     A T T R I B U T E S     ############################
    


    ###########################     P R I V A T E     A T T R I B U T E S     ###########################

        self._program_directory = program_directory
        self._name = name
        self._input_iconic_variables = input_iconic_variables
        self._output_iconic_variables = output_iconic_variables
        self._input_control_variables = input_control_variables
        self._input_control_types = input_control_types
        self._output_control_variables = output_control_variables
        self._output_control_types = output_control_types

        self.input_iconic = {key: None for key in input_iconic_variables}
        self.output_iconic = {key: None for key in output_iconic_variables}
        self.input_control = {key: None for key in input_control_variables}
        self.output_control = {key: None for key in output_control_variables}


        self._procedure = initialize_procedure(self._program_directory, self._name)

        self._run_time: float = 0
        self._min_run_time: float = 0
        self._max_run_time: float = 0

    ###############################     P U B L I C     M E T H O D S     ###############################
    
    def set_input_iconic_by_name(self, variable_name: str, value: ha.HObject):
        if variable_name in self.input_iconic:
            self.input_iconic[variable_name] = value
            self._procedure.set_input_iconic_param_by_name(variable_name, value)

    def set_input_iconic_by_index(self, index: int, value: ha.HObject):
        for variable_index, variable_name in enumerate(self.input_iconic.copy()):
            if index == variable_index:
                self.input_iconic[variable_name] = value
                self._procedure.set_input_iconic_param_by_name(variable_name, value)
    
    def get_output_iconic_by_name(self, variable_name: str) -> ha.HObject:
        if variable_name in self.output_iconic:
            return self.output_iconic[variable_name]
        
    def get_output_iconic_by_index(self, index: int) -> ha.HObject:
        for variable_index, variable_name in enumerate(self.output_iconic.copy()):
            if index == variable_index:
                return self.output_iconic[variable_name]
    
    def set_input_control_by_name(self, variable_name: str, value: ha.HTupleType):
        if variable_name in self.input_control:
            self.input_control[variable_name] = value
            self._procedure.set_input_control_param_by_name(variable_name, value)

    def set_input_control_by_index(self, index: int, value: ha.HTupleType):
        for variable_index, variable_name in enumerate(self.input_control.copy()):
            if index == variable_index:
                self.input_control[variable_name] = value
                self._procedure.set_input_control_param_by_name(variable_name, value)
        
    def get_output_control_by_name(self, variable_name: str) -> ha.HTupleType:
        if variable_name in self.output_control:
            return self.output_control[variable_name]
        
    def get_output_control_by_index(self, index: int) -> ha.HTupleType:
        for variable_index, variable_name in enumerate(self.output_control.copy()):
            if index == variable_index:
                return self.output_control[variable_name]
    
    def get_output_control(self) -> list[ha.HTupleType]:
        output = []
        for variable_name in self.output_control.copy():
            output.append(self.output_control[variable_name])
        return output
    
    def get_input_control_variables(self) -> dict[int, list[str]]:
        output = {}                    
        for i, variable in enumerate(self._input_control_variables):
            output[i] = [variable, self._input_control_types[i]]
        return output

    def get_output_control_variables(self) -> dict[int, list[str]]:
        output = {}
        for i, variable in enumerate(self._output_control_variables):
            output[i] = [variable, self._output_control_types[i]]
        return output

    def get_output_iconic_dict(self):
        return self.output_iconic

    def get_output_control_dict(self):
        return self.output_control
    
    def get_run_time(self):
        return self._run_time
    
    def get_min_run_time(self):
        return self._min_run_time
    
    def get_max_run_time(self):
        return self._max_run_time

    def run(self):

        start_time = time.time()
        self._procedure.execute()
        self._get_output_variables()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self._get_statistics(elapsed_time)

    ##############################     P R I V A T E     M E T H O D S     ##############################

    def _set_input_variables(self):
        
        for iconic_variable in self.input_iconic.copy():
            self._procedure.set_input_iconic_param_by_name(iconic_variable, self.input_iconic[iconic_variable])
        for control_variable in self.input_control.copy():
            self._procedure.set_input_control_param_by_name(control_variable, self.input_control[control_variable])

    def _get_output_variables(self):

        for iconic_variable in self.output_iconic.copy():
            self.output_iconic[iconic_variable] = self._procedure.get_output_iconic_param_by_name(iconic_variable)
        for control_variable in self.output_control.copy():
            self.output_control[control_variable] = self._procedure.get_output_control_param_by_name(control_variable)

    def _get_statistics(self, elapsed_time:float):

        self._run_time = elapsed_time
        if elapsed_time > self._max_run_time or self._max_run_time == 0:
            self._max_run_time = elapsed_time
        if elapsed_time < self._min_run_time or self._min_run_time == 0:
            self._min_run_time = elapsed_time