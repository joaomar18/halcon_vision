###########EXTERNAL IMPORTS############

import halcon as ha
import time

#######################################

#############LOCAL IMPORTS#############

#######################################


def create_vision_procedure(
    program_directory,
    name,
    input_control: dict[str, str] = None,
    output_control: dict[str, str] = None,
    input_iconic: list[str] = None,
    output_iconic: list[str] = None,
):
    """
    Create a VisionProcedure with input/output control and iconic variables.

    :param program_directory: Path to the directory of the program
    :param name: Name of the vision procedure
    :param input_control: Control inputs for the procedure
    :param output_control: Control outputs for the procedure
    :param input_iconic: Iconic inputs for the procedure
    :param output_iconic: Iconic outputs for the procedure
    :return: A VisionProcedure instance
    """

    input_control_variables: list[str] = []
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
        output_iconic_variables=output_iconic if output_iconic else [],
    )


def initialize_procedure(
    program_directory: str, procedure_name: str
) -> ha.HDevProcedureCall:
    """
    Initialize a Halcon procedure from the given directory and name.

    :param program_directory: Path to the procedure directory
    :param procedure_name: Name of the procedure
    :return: A Halcon procedure call
    """

    procedure_proc = ha.HDevProcedure.load_local(program_directory, procedure_name)
    procedure = ha.HDevProcedureCall(procedure_proc)
    return procedure


class VisionProcedure:
    """
    VisionProcedure handles the execution of a vision program and manages its inputs and outputs.

    Attributes:
        program_directory (str): The directory where the procedure resides
        name (str): The name of the procedure
        input_iconic (dict): Dictionary of iconic input variables
        output_iconic (dict): Dictionary of iconic output variables
        input_control (dict): Dictionary of control input variables
        output_control (dict): Dictionary of control output variables
    """

    def __init__(
        self,
        program_directory: str,
        name: str,
        input_iconic_variables: list,
        output_iconic_variables: list,
        input_control_variables: list,
        input_control_types: list,
        output_control_variables: list,
        output_control_types: list,
    ):

        self.program_directory = program_directory
        self.name = name
        self.input_iconic_variables = input_iconic_variables
        self.output_iconic_variables = output_iconic_variables
        self.input_control_variables = input_control_variables
        self.input_control_types = input_control_types
        self.output_control_variables = output_control_variables
        self.output_control_types = output_control_types

        self.input_iconic = {key: None for key in input_iconic_variables}
        self.output_iconic = {key: None for key in output_iconic_variables}
        self.input_control = {key: None for key in input_control_variables}
        self.output_control = {key: None for key in output_control_variables}

        self.procedure = initialize_procedure(self.program_directory, self.name)

        self.run_time: float = 0
        self.min_run_time: float = 0
        self.max_run_time: float = 0

    def set_input_iconic_by_name(self, variable_name: str, value: ha.HObject):
        """Set iconic input by its name."""

        if variable_name in self.input_iconic:
            self.input_iconic[variable_name] = value
            self.procedure.set_input_iconic_param_by_name(variable_name, value)

    def set_input_iconic_by_index(self, index: int, value: ha.HObject):
        """Set iconic input by its index."""

        for variable_index, variable_name in enumerate(self.input_iconic.copy()):
            if index == variable_index:
                self.input_iconic[variable_name] = value
                self.procedure.set_input_iconic_param_by_name(variable_name, value)

    def get_output_iconic_by_name(self, variable_name: str) -> ha.HObject:
        """Get iconic output by its name."""

        if variable_name in self.output_iconic:
            return self.output_iconic[variable_name]

    def get_output_iconic_by_index(self, index: int) -> ha.HObject:
        """Get iconic output by its index."""

        for variable_index, variable_name in enumerate(self.output_iconic.copy()):
            if index == variable_index:
                return self.output_iconic[variable_name]

    def set_input_control_by_name(self, variable_name: str, value: ha.HTupleType):
        """Set control input by its name."""

        if variable_name in self.input_control:
            self.input_control[variable_name] = value
            self.procedure.set_input_control_param_by_name(variable_name, value)

    def set_input_control_by_index(self, index: int, value: ha.HTupleType):
        """Set control input by its index."""

        for variable_index, variable_name in enumerate(self.input_control.copy()):
            if index == variable_index:
                self.input_control[variable_name] = value
                self.procedure.set_input_control_param_by_name(variable_name, value)

    def get_output_control_by_name(self, variable_name: str) -> ha.HTupleType:
        """Get control output by its name."""

        if variable_name in self.output_control:
            return self.output_control[variable_name]

    def get_output_control_by_index(self, index: int) -> ha.HTupleType:
        """Get control output by its index."""

        for variable_index, variable_name in enumerate(self.output_control.copy()):
            if index == variable_index:
                return self.output_control[variable_name]

    def get_output_control(self) -> list[ha.HTupleType]:
        """Get all control output values as a list."""

        output = []
        for variable_name in self.output_control.copy():
            output.append(self.output_control[variable_name])
        return output

    def get_input_control_variables(self) -> dict[int, list[str]]:
        """Return a dictionary of input control variables and their types."""

        output = {}
        for i, variable in enumerate(self.input_control_variables):
            output[i] = [variable, self.input_control_types[i]]
        return output

    def get_output_control_variables(self) -> dict[int, list[str]]:
        """Return a dictionary of output control variables and their types."""

        output = {}
        for i, variable in enumerate(self.output_control_variables):
            output[i] = [variable, self.output_control_types[i]]
        return output

    def get_output_iconic_dict(self) -> dict[str, ha.HObject]:
        """Return the dictionary of iconic output variables."""

        return self.output_iconic

    def get_output_control_dict(self) -> dict[str, ha.HTupleType]:
        """Return the dictionary of control output variables."""

        return self.output_control

    def get_run_time(self) -> float:
        """Return the runtime of the procedure."""

        return self.run_time

    def get_min_run_time(self) -> float:
        """Return the minimum runtime."""

        return self.min_run_time

    def get_max_run_time(self) -> float:
        """Return the maximum runtime."""

        return self.max_run_time

    def run(self):
        """Run the vision procedure and calculate the execution time."""

        start_time = time.time()
        self.procedure.execute()
        self.get_output_variables()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.get_statistics(elapsed_time)

    def set_input_variables(self):
        """Helper method to set procedure input parameters from the class dictionaries."""

        for iconic_variable in self.input_iconic.copy():
            self.procedure.set_input_iconic_param_by_name(
                iconic_variable, self.input_iconic[iconic_variable]
            )
        for control_variable in self.input_control.copy():
            self.procedure.set_input_control_param_by_name(
                control_variable, self.input_control[control_variable]
            )

    def get_output_variables(self):
        """Retrieve output variables from the procedure and update internal state."""

        for iconic_variable in self.output_iconic.copy():
            self.output_iconic[iconic_variable] = (
                self.procedure.get_output_iconic_param_by_name(iconic_variable)
            )
        for control_variable in self.output_control.copy():
            self.output_control[control_variable] = (
                self.procedure.get_output_control_param_by_name(control_variable)
            )

    def get_statistics(self, elapsed_time: float):
        """Update the runtime statistics for the procedure."""

        self.run_time = elapsed_time
        if elapsed_time > self.max_run_time or self.max_run_time == 0:
            self.max_run_time = elapsed_time
        if elapsed_time < self.min_run_time or self.min_run_time == 0:
            self.min_run_time = elapsed_time
