from vision.data.comm import VisionCommunication
from vision.system import VisionSystem        
import asyncio


class VisionManager():
    def __init__(self, receiver_queue: asyncio.Queue, send_queue: asyncio.Queue):
    
    ############################     P U B L I C     A T T R I B U T E S     ############################



    ###########################     P R I V A T E     A T T R I B U T E S     ###########################

        self._receiver_queue = receiver_queue
        self._send_queue = send_queue
        self._vision_systems: dict[str, VisionSystem] = dict()
        self._vision_systems_name: set[str] = set()
        asyncio.create_task(self._process_receiver_queue())
    
    ###############################     P U B L I C     M E T H O D S     ###############################

    async def add_vision_system(self, new_vision_system: VisionSystem):

        if new_vision_system.name not in self._vision_systems:
            self._vision_systems[new_vision_system.name] = new_vision_system
            self._vision_systems[new_vision_system.name].set_update_queue(self._send_queue)
            self._vision_systems_name.add(new_vision_system.name)
            new_vision_system.init()
    
    def get_vision_system_devices(self) -> list[str]:

        output = []
        for vision_system in self._vision_systems.copy():
            output.append(vision_system)
        return output

    ##############################     P R I V A T E     M E T H O D S     ##############################

    async def _process_receiver_queue(self):

        while True:
            message = await self._receiver_queue.get()
            await self._process_received_message(message)
    
    async def _process_received_message(self, message):
        if message['peripheral'] == 'frontend':
            if message['type'] == 'status':
                if message['data'] == 'connected':
                    response = {'peripheral': 'manager',
                               'type': 'response',
                               'data': self.get_vision_system_devices()}
                    await self._send_queue.put(response)
                    for device in self._vision_systems:
                        await self._vision_systems[device].process_incoming_messages(message)
        
        if message['peripheral'] in self._vision_systems_name:
            device = message['peripheral']
            await self._vision_systems[device].process_incoming_messages(message)