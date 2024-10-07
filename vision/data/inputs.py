import asyncio

class VisionInputs:

    def __init__(self, device_name: str, register_size: int, init_program: int):

    ############################     P U B L I C     A T T R I B U T E S     ############################

        self.device_name = device_name

        self.control = {
            'trigger': False,
            'program_change': False,
            'reset': False,
        }
        
        self.program_number = init_program
        self.inputs_variables = list([None] * register_size)
        self.inputs_register = list([0] * register_size)

    ###########################     P R I V A T E     A T T R I B U T E S     ###########################

        self._update_inputs_queue: asyncio.Queue = None

    ###############################     P U B L I C     M E T H O D S     ###############################
    
    def set_update_inputs_queue(self, queue: asyncio.Queue):

        self._update_inputs_queue = queue

    async def send_control(self):
        
        await self._send_message(type='status',
                                 section='control',
                                 value=self.control)
    
    async def send_program_number(self):

        await self._send_message(type='status',
                                 section='program_number',
                                 value=self.program_number)

    async def send_inputs_variables(self):

        await self._send_message(type='status', 
                                 section='inputs_variables', 
                                 value=self.inputs_variables)

    async def send_inputs(self):

        await self._send_message(type='status', 
                                 section='inputs_register', 
                                 value=self.inputs_register)
        
    async def send_all(self):

        await self.send_control()
        await self.send_program_number()
        await self.send_inputs_variables()
        await self.send_inputs()

    ##############################     P R I V A T E     M E T H O D S     ##############################
       
    async def _send_message(self, type: str, section: str, value):
        
        if self._update_inputs_queue != None:
            
            message = {'peripheral':self.device_name,
                       'type':type,
                       'section':section,
                       'value':value}
            
            await self._update_inputs_queue.put(message)