from vision.system import VisionSystem
from vision.manager import VisionManager
from communication.frontend import WebSocketServer
import communication.queues as queues
from db.client import DBClient
import vision.construct
import vision.data.comm
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PULLEY_CAMERA_PROGRAM_PATH = '/home/joao/Desktop/halcon_pulleys/hdevelop/PulleyCamera/inspect_pulleys.hdev'
PULLEY_CAMERA_OUTPUT_PATH = '/home/joao/Desktop/halcon_pulleys/hdevelop/PulleyCamera/output/output_image'
FINAL_INSPECTION_CAMERA_PROGRAM_PATH = '/home/joao/Desktop/halcon_pulleys/hdevelop/FinalInspCamera/fic_hdev.hdev'
FINAL_INSPECTION_CAMERA_OUTPUT_PATH = '/home/joao/Desktop/halcon_pulleys/hdevelop/FinalInspCamera/output/output_image'


async def async_main():

    db_client = DBClient(db_file='db/vision_app.db', 
                         logger=logger)
    
    frontend_server = WebSocketServer(host='localhost', 
                                      port=9999, 
                                      receive_queue=queues.frontend_receive_queue, 
                                      send_queue=queues.frontend_send_queue,
                                      db_client=db_client,
                                      logger=logger)
    
    vision_manager = VisionManager(receiver_queue=queues.frontend_receive_queue, 
                                   send_queue=queues.frontend_send_queue,
                                   db_client=db_client,
                                   logger=logger)

    await vision_manager.add_vision_system(VisionSystem('PulleyCamera', 'Pulley Picking Camera', PULLEY_CAMERA_PROGRAM_PATH, PULLEY_CAMERA_OUTPUT_PATH, 
                                                        vision.construct.create_pulley_camera, 32, 1))
    await vision_manager.add_vision_system(VisionSystem('FinalInspCamera', 'Final Inspection Camera', FINAL_INSPECTION_CAMERA_PROGRAM_PATH, 
                                                        FINAL_INSPECTION_CAMERA_OUTPUT_PATH, vision.construct.create_final_inspection_camera, 32, 1))
    await asyncio.gather(
        frontend_server.start_server(),
    )

if __name__ == '__main__':
    asyncio.run(async_main())