from vision.data.inputs import VisionInputs
from vision.data.outputs import VisionOutputs
from db.client import DBClient
import logging
    
class VisionCommunication():
    """
    A class to manage vision inputs and outputs for a camera.
    
    Attributes:
        inputs (VisionInputs): Handles the vision input data.
        outputs (VisionOutputs): Handles the vision output data.
    """

    def __init__(self, device_name: str, reg_size: int, init_program: int):
        """
        Initializes the VisionCommunication class with the given camera parameters.

        Args:
            device_name (str): The name of the camera.
            reg_size (int): The size of the register.
            init_program (int): The initial program to load.
        """      

        if not isinstance(device_name, str) or not device_name:
            raise ValueError(f"Invalid device_name {device_name}. device_name must be a non-empty string.")
        if not isinstance(reg_size, int) or reg_size <= 0:
            raise ValueError(f"Invalid reg_size {reg_size}. reg_size must be an integer greather than 0.")
        if not isinstance(init_program, int) or init_program < 0:
            raise ValueError(f"Invalid init_program {init_program}. init_program must be a positive integer.")

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