import asyncio

class VisionOutputs:
    def __init__(self, device_name:str, register_size: int):

    ############################     P U B L I C     A T T R I B U T E S     ############################
        
        self.device_name = device_name

        self.status = {'ready': False,
                       'run': False,
                       'trigger_acknowledge': False,
                       'program_change_acknowledge': False,
                       'trigger_error': False,
                       'program_change_error': False,
                       'new_image':False}
        
        self.statistics = {'min_run_time': 0.0,
                           'run_time': 0.0,
                           'max_run_time': 0.0}

        self.program_number_acknowledge = 0
        self.outputs_variables = list([None] * register_size)
        self.outputs_register = list([0] * register_size)

    ###########################     P R I V A T E     A T T R I B U T E S     ###########################
        
        self._update_outputs_queue: asyncio.Queue = None

    ###############################     P U B L I C     M E T H O D S     ###############################

    def set_update_outputs_queue(self, queue: asyncio.Queue):

        self._update_outputs_queue = queue
    
    async def send_status(self):

        await self._send_message(type='status',
                                 section='status',
                                 value=self.status)        

    async def send_statistics(self):

        await self._send_message(type='status',
                                 section='statistics',
                                 value=self.statistics)  
    
    async def send_program_number_acknowledge(self):

        await self._send_message(type='status',
                                 section='program_number_acknowledge',
                                 value=self.program_number_acknowledge)         
    
    async def send_outputs_variables(self):

        await self._send_message(type='status',
                                 section='outputs_variables',
                                 value=self.outputs_variables)       

    async def send_outputs(self):

        await self._send_message(type='status',
                                 section='outputs_register',
                                 value=self.outputs_register)   

    async def send_all(self):

        await self.send_status()
        await self.send_statistics()
        await self.send_program_number_acknowledge()
        await self.send_outputs_variables()
        await self.send_outputs()

    ##############################     P R I V A T E     M E T H O D S     ##############################
       
    async def _send_message(self, type: str, section: str, value):
        
        if self._update_outputs_queue != None:
            
            message = {'peripheral':self.device_name,
                       'type':type,
                       'section':section,
                       'value':value}
            
            await self._update_outputs_queue.put(message)