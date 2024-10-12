# Constants for sections
CONTROL_SECTION = 'control'
PROGRAM_NUMBER_SECTION = 'program_number'
INPUTS_SECTION = 'inputs_register'
INPUTS_VARIABLES_SECTION = 'inputs_variables'
STATUS_SECTION = 'status'
PROGRAM_NUMBER_ACKNOWLEDGE_SECTION = 'program_number_acknowledge'
STATISTICS_SECTION = 'statistics'
OUTPUTS_SECTION = 'outputs_register'
OUTPUTS_VARIABLES_SECTION = 'outputs_variables'

# Control variables
TRIGGER = 'trigger'
PROGRAM_CHANGE = 'program_change'
RESET = 'reset'

# Status variables
READY = 'ready'
RUN = 'run'
TRIGGER_ACKNOWLEDGE = 'trigger_acknowledge'
PROGRAM_CHANGE_ACKNOWLEDGE = 'program_change_acknowledge'
TRIGGER_ERROR = 'trigger_error'
PROGRAM_CHANGE_ERROR = 'program_change_error'
NEW_IMAGE = 'new_image'

# Statistics variables
MIN_RUN_TIME = 'min_run_time'
RUN_TIME = 'run_time'
MAX_RUN_TIME = 'max_run_time'

# Message fields
PERIPHERAL_KEY = 'peripheral'
TYPE_KEY = 'type'
SECTION_KEY = 'section'
DATA_KEY = 'data'
VALUE_KEY = 'value'
VALUE_TYPE_KEY = 'value_type'
VALUE_INDEX_KEY = 'index'

class HalconVariable():
    """
    A class to represent a variable in the Halcon vision system.

    Attributes:
        value: The value of the Halcon variable.
    """

    def __init__(self, value = None):
        """
        Initializes a HalconVariable with an optional value.

        Args:
            value: The initial value for the HalconVariable. Defaults to None.
        """

    ############################     P U B L I C     A T T R I B U T E S     ############################

        self.value = value

    ###########################     P R I V A T E     A T T R I B U T E S     ###########################


    
    ###############################     P U B L I C     M E T H O D S     ###############################

    def set_value(self, value):
        """
        Sets the value of the HalconVariable.

        Args:
            value: The value to be set.
        """

        self.value = value
    
    def get_type(self):
        """
        Returns the type of the current value of the HalconVariable.

        Returns:
            The type of the value.
        """

        return type(self.value)
    
    @staticmethod
    def serialize_list(list: list['HalconVariable']) -> list[str]:
        """
        Serializes a list of HalconVariables into a list of strings.

        Args:
            variable_list (list[HalconVariable]): The list of HalconVariable objects to serialize.

        Returns:
            list[str]: A list of string representations of the HalconVariable values.
        """
        
        output = []
        for variable in list:
            output.append(str(variable.value))
        return output
    
    ##############################     P R I V A T E     M E T H O D S     ##############################
