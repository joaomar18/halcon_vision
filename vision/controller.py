import asyncio
from concurrent.futures import ThreadPoolExecutor
from vision.camera import VisionCamera
from vision.data.comm import VisionCommunication


class VisionController():

    def __init__(self, name:str, description: str, program_path: str, output_path: str, create_camera, communication_data: VisionCommunication):

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
    
    ###############################     P U B L I C     M E T H O D S     ###############################

    def init(self):

        self._camera.init()
        asyncio.gather(self._change_camera_program(self._inputs.program_number))
        asyncio.get_event_loop().create_task(self.camera_set_ready())
    
    def set_camera_input(self, index, value):

        self._camera.set_program_input(index, value)

    async def camera_set_ready(self):

        self._outputs.status['trigger_acknowledge'] = False
        self._outputs.status['program_change_acknowledge'] = False
        self._outputs.status['trigger_error'] = False
        self._outputs.status['program_change_error'] = False
        self._outputs.status['run'] = False
        self._outputs.status['new_image'] = False
        self._outputs.status['ready'] = True
        await self._outputs.send_status()

    async def camera_reset_error(self):
        
        pass

    async def camera_single_trigger(self):

        if self._outputs.status['ready']:

            self._outputs.status['ready'] = False
            self._outputs.status['run'] = True
            await self._outputs.send_status()

            future = await asyncio.get_event_loop().run_in_executor(
                self._executor, self._camera.execute_program
            )

            program_output = self._camera.get_program_output()
            for i, output in enumerate(program_output):
                if len(output) == 1:
                    output = output[0]
                elif len(output) == 0:
                    output = None                    
                self._outputs.outputs_register[i].set_value(output)
            self._outputs.status['run'] = False
            self._outputs.status['trigger_acknowledge'] = True
            await self._outputs.send_status()
            await self._outputs.send_outputs()
            self._outputs.statistics['min_run_time'] = self._camera.get_min_run_time()
            self._outputs.statistics['run_time'] = self._camera.get_run_time()
            self._outputs.statistics['max_run_time'] = self._camera.get_max_run_time()
            await self._outputs.send_statistics()
            future.result(None)
            self._outputs.status['new_image'] = True
            await self._outputs.send_status()
    
    async def camera_program_change(self):

        if self._outputs.status['ready']:
            print("Starting to change program")
            self._outputs.status['ready'] = False
            self._outputs.status['run'] = True
            await self._outputs.send_status()

            await self._change_camera_program(self._inputs.program_number)

            self._outputs.status['run'] = False
            self._outputs.status['program_change_acknowledge'] = True

            await self._outputs.send_status()

    ##############################     P R I V A T E     M E T H O D S     ##############################

    def _clean_camera_variables(self):

        self._outputs.statistics['min_run_time'] = 0
        self._outputs.statistics['run_time'] = 0
        self._outputs.statistics['max_run_time'] = 0

        for index, variable in enumerate(list(self._inputs.inputs_variables)):
            self._inputs.inputs_variables[index] = None

        for i, input in enumerate(list(self._inputs.inputs_register).copy()):
            self._inputs.inputs_register[i].set_value(0)
        
        for index, variable in enumerate(list(self._outputs.outputs_variables)):
            self._outputs.outputs_variables[index] = None
            
        for i, output in enumerate(list(self._outputs.outputs_register).copy()):
            self._outputs.outputs_register[i].set_value(0)
    
    async def _change_camera_program(self, program_number: int):
            
        self._camera.set_active_program(program_number)
        self._outputs.program_number_acknowledge = self._camera.get_program_number()
    
        self._clean_camera_variables()

        program_input_variables = self._camera.get_program_input_variables()
        for index, variable in program_input_variables.items():
            self._inputs.inputs_variables[index] = variable
            
        program_output_variables = self._camera.get_program_output_variables()
        for index, variable in program_output_variables.items():
            self._outputs.outputs_variables[index] = variable

        for i, input_variable in enumerate(program_input_variables):
            self._camera.set_program_input(i, self._inputs.inputs_register[i].value)

        await self._outputs.send_program_number_acknowledge()
        await self._inputs.send_inputs_variables()
        await self._inputs.send_inputs()
        await self._outputs.send_outputs_variables()
        await self._outputs.send_outputs()
        await self._outputs.send_statistics()


        