###########EXTERNAL IMPORTS############

from enum import Enum

#######################################

#############LOCAL IMPORTS#############

#######################################

# Constants for sections
CONTROL_SECTION = "control"
PROGRAM_NUMBER_SECTION = "program_number"
INPUTS_SECTION = "inputs_register"
INPUTS_VARIABLES_SECTION = "inputs_variables"
STATUS_SECTION = "status"
PROGRAM_NUMBER_ACKNOWLEDGE_SECTION = "program_number_acknowledge"
STATISTICS_SECTION = "statistics"
OUTPUTS_SECTION = "outputs_register"
OUTPUTS_VARIABLES_SECTION = "outputs_variables"

# Control variables
TRIGGER = "trigger"
PROGRAM_CHANGE = "program_change"
RESET = "reset"

# Status variables
READY = "ready"
RUN = "run"
TRIGGER_ACKNOWLEDGE = "trigger_acknowledge"
PROGRAM_CHANGE_ACKNOWLEDGE = "program_change_acknowledge"
TRIGGER_ERROR = "trigger_error"
PROGRAM_CHANGE_ERROR = "program_change_error"
NEW_IMAGE = "new_image"

# Statistics variables
MIN_RUN_TIME = "min_run_time"
RUN_TIME = "run_time"
MAX_RUN_TIME = "max_run_time"

# Message fields
PERIPHERAL_KEY = "peripheral"
TYPE_KEY = "type"
SECTION_KEY = "section"
BATCH_KEY = "batch"
BATCH_VALUES_KEY = "batch_values"
DATA_KEY = "data"
VALUE_KEY = "value"
VALUE_TYPE_KEY = "value_type"
VALUE_INDEX_KEY = "index"


class VariableType(Enum):
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    


class Variable:
    """
    A class to represent a variable in the Halcon vision system.

    Attributes:
        value: The value of the Halcon variable.
    """

    def __init__(self, type: VariableType, value=None, external: bool = True):

        self.value = value
        self.type = type
        self.external = external

    def set_value(self, value):
        """
        Sets the value of the Variable.

        Args:
            value: The value to be set.
        """

        self.value = value

    def get_type(self):
        """
        Returns the type of the current value of the Variable.

        Returns:
            The type of the value.
        """

        return type(self.value)

    @staticmethod
    def serialize_list(list: list["Variable"]) -> list[str]:
        """
        Serializes a list of Variable objects into a list of strings.

        Args:
            variable_list (list[Variable]): The list of Variable objects to serialize.

        Returns:
            list[str]: A list of string representations of the Variable values
                    for variables marked as external.
        """

        output = []
        for variable in list:
            if variable.external:
                output.append(str(variable.value))
        return output
