import asyncio
from vision.data.comm import VisionCommunication
from vision.controller import VisionController

class VisionSystem():
    def __init__(self, name: str, description: str, program_path: str, output_path: str, camera_construct_function, register_size: int = 32, init_program: int = 0):
        
    ############################     P U B L I C     A T T R I B U T E S     ############################

        self.name = name
        self.description = description
        self.program_path = program_path
        self.output_path = output_path
        self.init_program = init_program

    ###########################     P R I V A T E     A T T R I B U T E S     ###########################

        self._communication = VisionCommunication(name, register_size, init_program)
        self._controller = VisionController(name, description, program_path, output_path, camera_construct_function, self._communication)
    
    ###############################     P U B L I C     M E T H O D S     ###############################

    def init(self):

        self._controller.init()

    async def process_incoming_messages(self, message):

        if message['type'] == 'status':
            if message['data'] == 'connected':
                await self._communication.inputs.send_all()
                await self._communication.outputs.send_all()          
        elif message['type'] == 'request':
            await self._process_request(message)

    def set_update_queue(self, queue: asyncio.Queue):

        self._communication.inputs.set_update_inputs_queue(queue)
        self._communication.outputs.set_update_outputs_queue(queue)

    ##############################     P R I V A T E     M E T H O D S     ##############################

    async def _process_request(self, message):

        value = None

        if message['section'] == 'control':
                
            if message['value'] == 'true':
                value = True
            elif message['value'] == 'false':
                value = False
                    
            self._communication.inputs.control[message['data']] = value

            if self._communication.inputs.control['trigger']:
                await self._controller.camera_single_trigger()
            elif self._communication.inputs.control['program_change']:
                await self._controller.camera_program_change()
            elif self._communication.inputs.control['reset']:
                await self._controller.camera_reset_error()
            elif not self._communication.outputs.status['trigger_error'] and not self._communication.outputs.status['program_change_error']:
                await self._controller.camera_set_ready()
            
        elif message['section'] == 'program_number':
                
            value = int(message['value'])

            self._communication.inputs.program_number = value
            
        elif message['section'] == 'inputs_register':

            index = int(message['index'])
            value = message['value']
            type = message['value_type']
            
            if type == 'float':
                value = float(value)
            elif type == 'int':
                value = int(value)
            elif type == 'string':
                value = str(value)

            self._communication.inputs.inputs_register[index] = value
            self._controller.set_camera_input(index, value)
 

