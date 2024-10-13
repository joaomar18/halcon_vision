import asyncio
from concurrent.futures import ThreadPoolExecutor
from vision.camera import VisionCamera
from vision.data.comm import VisionCommunication
from vision.data.variables import *

class VisionController():
    """
    VisionController is responsible for managing the vision camera, handling input/output communication, 
    and executing vision programs. It acts as the central point of control for the camera operations, 
    including triggering captures, changing programs, and processing camera outputs.

    Attributes:
        name (str): Name of the vision controller.
        description (str): Description of the vision controller.
        _program_path (str): Path to the camera program.
        _output_path (str): Path to output the camera data.
        _create_camera (function): Function to create the camera (open, trigger, program, display procedures).
        _communication_data (VisionCommunication): Object managing the communication inputs and outputs.
        _inputs (VisionInputs): Inputs communication data.
        _outputs (VisionOutputs): Outputs communication data.
        _executor (ThreadPoolExecutor): Thread pool for executing camera tasks asynchronously.
        _camera (VisionCamera): Camera object created using the provided program path and procedures.
        _lock (asyncio.Lock): Async lock for ensuring thread-safe access to camera operations.
    """

    def __init__(self, name:str, description: str, program_path: str, output_path: str, create_camera, communication_data: VisionCommunication):
        """
        Initialize the VisionController with camera and communication data.
        
        :param name: Name of the vision controller
        :param description: Description of the vision controller
        :param program_path: Path to the camera program
        :param output_path: Path to output the camera data
        :param create_camera: Function to create the camera
        :param communication_data: Communication object to manage inputs and outputs
        """

    ############################     P U B L I C     A T T R I B U T E S     ############################
    
        self.name = name
        self.description = description

    ###########################     P R I V A T E     A T T R I B U T E S     ###########################

        self._program_path = program_path
        self._output_path = output_path
        self._create_camera = create_camera
        self._communication_data = communication_data
        self._inputs = self._communication_data.inputs
        self._outputs = self._communication_data.outputs

        self._executor = ThreadPoolExecutor(max_workers=1)

        self._open_camera, self._trigger_camera, self._programs_camera, self._displays_camera = create_camera(program_path)
        self._camera = VisionCamera(name, description, output_path, self._open_camera, self._trigger_camera, self._programs_camera, self._displays_camera)
    
        self._lock = asyncio.Lock()

    ###############################     P U B L I C     M E T H O D S     ###############################

    async def init(self):
        """
        Initialize the camera and start the necessary async tasks.
        """

        self._camera.init()
        asyncio.gather(self._change_camera_program(self._inputs.program_number))
        asyncio.get_event_loop().create_task(self.camera_set_ready())
    
    def set_camera_input(self, index, value):
        """
        Set the input for the camera program.
        
        :param index: Input index
        :param value: Input value
        """

        self._camera.set_program_input(index, value)

    async def camera_set_ready(self):
        """
        Reset camera status and set it to ready.
        """

        async with self._lock:
            self._reset_camera_status()
            await self._outputs.send_status()

    async def camera_single_trigger(self):
        """
        Trigger the camera for a single capture.
        """

        async with self._lock:
            if self._outputs.status[READY]:

                self._update_status(run=True, ready=False)
                await self._outputs.send_status()

                future = await asyncio.get_event_loop().run_in_executor(
                    self._executor, self._camera.execute_program
                )

                self._process_camera_outputs()

                self._update_status(run=False, trigger_acknowledge=True)
                await self._outputs.send_status()
                await self._outputs.send_outputs()

                self._update_statistics()
                await self._outputs.send_statistics()

                future.result(None)
                self._update_status(new_image=True)
                await self._outputs.send_status()
    
    async def camera_program_change(self):
        """
        Change the camera program.
        """

        async with self._lock:
            if self._outputs.status[READY]:

                self._update_status(run=True, ready=False)
                await self._outputs.send_status()

                await self._change_camera_program(self._inputs.program_number)

                self._update_status(run=False, program_change_acknowledge=True)
                await self._outputs.send_status()

    ##############################     P R I V A T E     M E T H O D S     ##############################

    def _process_camera_outputs(self):
        """
        Process the outputs received from the camera and update output registers.
        """

        program_output = self._camera.get_program_output()
        for i, output in enumerate(program_output):
            output = self._get_output_value(output, self._outputs.outputs_variables[i][1])                  
            self._outputs.outputs_register[i].set_value(output)
    
    def _get_output_value(self, output, var_type: str):
        """
        Determine the correct output value based on its type.
        
        :param output: The output value from the camera program
        :param var_type: The type of the output variable (int, float, string)
        :return: Processed output value
        """

        if len(output) == 1:
            return output[0]
        elif len(output) == 0:
            if var_type == 'int':
                return 0
            elif var_type == 'float':
                return 0.0
            elif var_type == 'string':
                return ''
            else:
                return None
    
    def _update_status(self, **kwargs):
        """
        Update multiple status flags at once.
        
        :param kwargs: Status flags to update (e.g., run=True, ready=False)
        """

        for key, value in kwargs.items():
            self._outputs.status[key] = value

    def _update_statistics(self):
        """
        Update camera run time statistics.
        """

        self._outputs.statistics[MIN_RUN_TIME] = self._camera.get_min_run_time()
        self._outputs.statistics[RUN_TIME] = self._camera.get_run_time()
        self._outputs.statistics[MAX_RUN_TIME] = self._camera.get_max_run_time()

    def _reset_camera_status(self):
        """
        Reset all camera status flags to their initial values.
        """

        self._outputs.status[TRIGGER_ACKNOWLEDGE] = False
        self._outputs.status[PROGRAM_CHANGE_ACKNOWLEDGE] = False
        self._outputs.status[TRIGGER_ERROR] = False
        self._outputs.status[PROGRAM_CHANGE_ERROR] = False
        self._outputs.status[RUN] = False
        self._outputs.status[NEW_IMAGE] = False
        self._outputs.status[READY] = True
                
    def _reset_variable_list(self, variable_list: list[list[str]]):
        """
        Reset the provided variable list to None.
        
        :param variable_list: List of variables to reset
        """

        for index in range(len(variable_list)):
            variable_list[index] = None

    def _reset_register_values(self, register_list: list[HalconVariable]):
        """
        Reset the values in the provided register list to 0.
        
        :param register_list: List of register variables
        """

        for value in register_list.copy():
            value.set_value(0)

    def _reset_camera_variables(self):
        """
        Reset all input/output variables and statistics.
        """

        self._outputs.statistics[MIN_RUN_TIME] = 0
        self._outputs.statistics[RUN_TIME] = 0
        self._outputs.statistics[MAX_RUN_TIME] = 0

        self._reset_variable_list(self._inputs.inputs_variables)
        self._reset_register_values(self._inputs.inputs_register)
        self._reset_variable_list(self._outputs.outputs_variables)
        self._reset_register_values(self._outputs.outputs_register)            
    
    async def _change_camera_program(self, program_number: int):
        """
        Change the camera program and reset related variables.
        
        :param program_number: The new program number to be set
        """            

        self._camera.set_active_program(program_number)
        self._outputs.program_number_acknowledge = self._camera.get_program_number()
    
        self._reset_camera_variables()

        program_input_variables = self._camera.get_program_input_variables()
        for index, variable in program_input_variables.items():
            self._inputs.inputs_variables[index] = variable
            
        program_output_variables = self._camera.get_program_output_variables()
        for index, variable in program_output_variables.items():
            self._outputs.outputs_variables[index] = variable

        for i in range(len(program_input_variables)):
            self._camera.set_program_input(i, self._inputs.inputs_register[i].value)

        await self._outputs.send_program_number_acknowledge()
        await self._inputs.send_inputs_variables()
        await self._inputs.send_inputs()
        await self._outputs.send_outputs_variables()
        await self._outputs.send_outputs()
        await self._outputs.send_statistics()