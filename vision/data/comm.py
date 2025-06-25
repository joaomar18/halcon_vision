###########EXTERNAL IMPORTS############

from typing import Dict, List, Optional, Any

#######################################

#############LOCAL IMPORTS#############

from vision.data.inputs import VisionInputs
from vision.data.outputs import VisionOutputs
from vision.data.variables import *

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

    def get_inputs_control_dict(self) -> Dict[str, bool]:

        return self._inputs.control

    def get_inputs_registers_list(self) -> List[Variable]:

        return self._inputs.inputs_register

    def get_outputs_status_dict(self) -> Dict[str, bool]:

        return self._outputs.status

    def get_outputs_register_list(self) -> List[Variable]:

        return self._outputs.outputs_register
