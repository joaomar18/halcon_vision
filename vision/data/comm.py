###########EXTERNAL IMPORTS############

#######################################

#############LOCAL IMPORTS#############

from vision.data.inputs import VisionInputs
from vision.data.outputs import VisionOutputs

#######################################


class VisionCommunication:
    """
    A class to manage vision inputs and outputs for a camera.

    Attributes:
        inputs (VisionInputs): Handles the vision input data.
        outputs (VisionOutputs): Handles the vision output data.
    """

    def __init__(self, device_name: str, reg_size: int, init_program: int):

        if not isinstance(device_name, str) or not device_name:
            raise ValueError(
                f"Invalid device_name {device_name}. device_name must be a non-empty string."
            )
        if not isinstance(reg_size, int) or reg_size <= 0:
            raise ValueError(
                f"Invalid reg_size {reg_size}. reg_size must be an integer greather than 0."
            )
        if not isinstance(init_program, int) or init_program < 0:
            raise ValueError(
                f"Invalid init_program {init_program}. init_program must be a positive integer."
            )

        self._inputs = VisionInputs(device_name, reg_size, init_program)
        self._outputs = VisionOutputs(device_name, reg_size)

    @property
    def inputs(self) -> VisionInputs:
        """Returns the vision inputs."""

        return self._inputs

    @property
    def outputs(self) -> VisionOutputs:
        """Returns the vision outputs."""

        return self._outputs

    def get_inputs_coil_size(self) -> int:

        num_bits = len(self._inputs.control)
        num_words = 0
        if num_bits <= 16:
            num_words = 1
        else:
            num_words = (num_bits + 15) // 16

        return num_words * 16

    def get_inputs_holdreg_size(self) -> int:

        # Get number of program words
        num_words_program = 1

        # Get number of input register words
        register_size = len(self._inputs.inputs_register)

        return num_words_program + register_size

    def get_outputs_coil_size(self) -> int:

        num_bits = len(self._outputs.status)
        num_words = 0
        if num_bits <= 16:
            num_words = 1
        else:
            num_words = (num_bits + 15) // 16

        return num_words * 16

    def get_outputs_holdreg_size(self) -> int:

        # Get number of program acknowledge bytes
        num_words_program_ack = 1

        # Get number of output register bytes
        register_size = len(self._outputs.outputs_register)

        return num_words_program_ack + register_size
