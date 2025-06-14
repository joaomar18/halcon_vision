###########EXTERNAL IMPORTS############

import asyncio

#######################################

#############LOCAL IMPORTS#############

from vision.system import VisionSystem
from vision.manager import VisionManager
from communication.websockets import WebSocketServer
import communication.queues as queues
from db.client import DBClient
import vision.construct
from util.debug import LoggerManager

#######################################

PULLEY_CAMERA_PROGRAM_PATH = "/home/joao/Desktop/halcon-vision/halcon_vision/hdevelop/PulleyCamera/inspect_pulleys.hdev"
PULLEY_CAMERA_OUTPUT_PATH = "/home/joao/Desktop/halcon-vision/halcon_vision/hdevelop/PulleyCamera/output/output_image"
FINAL_INSPECTION_CAMERA_PROGRAM_PATH = "/home/joao/Desktop/halcon-vision/halcon_vision/hdevelop/FinalInspCamera/fic_hdev.hdev"
FINAL_INSPECTION_CAMERA_OUTPUT_PATH = "/home/joao/Desktop/halcon-vision/halcon_vision/hdevelop/FinalInspCamera/output/output_image"


async def async_main():
    """
    Main asynchronous function to initialize and run the vision system.

    This function sets up the core components of the HALCON vision system including:
    - Database client for data persistence
    - WebSocket server for frontend communication
    - Vision manager to handle multiple camera systems
    - Two vision systems: PulleyCamera and FinalInspCamera

    The function initializes all components and starts the WebSocket server to handle
    incoming connections and commands from the frontend interface.

    Raises:
        Exception: Any exception that occurs during system initialization or runtime
                  will propagate up and cause the application to exit.
    """

    # Initialize global logger
    LoggerManager.init()

    # Initialize database client for storing application data and errors
    db_client = DBClient(db_file="db/vision_app.db")

    # Initialize WebSocket server for frontend communication on port 8080
    websockets_server = WebSocketServer(
        host="0.0.0.0",
        port=8080,
        receive_queue=queues.frontend_receive_queue,
        send_queue=queues.frontend_send_queue,
    )

    # Initialize vision manager to coordinate multiple camera systems
    vision_manager = VisionManager(
        receiver_queue=queues.frontend_receive_queue,
        send_queue=queues.frontend_send_queue,
    )

    # Add Pulley Camera vision system for pulley picking operations
    await vision_manager.add_vision_system(
        VisionSystem(
            name="PulleyCamera",
            description="Pulley Picking Camera",
            program_path=PULLEY_CAMERA_PROGRAM_PATH,
            output_path=PULLEY_CAMERA_OUTPUT_PATH,
            camera_construct_function=vision.construct.create_pulley_camera,
            register_size=32,
            init_program=0,
        )
    )

    # Add Final Inspection Camera vision system for quality control
    await vision_manager.add_vision_system(
        VisionSystem(
            "FinalInspCamera",
            "Final Inspection Camera",
            FINAL_INSPECTION_CAMERA_PROGRAM_PATH,
            FINAL_INSPECTION_CAMERA_OUTPUT_PATH,
            vision.construct.create_final_inspection_camera,
            register_size=32,
            init_program=1,
        )
    )

    # Start the WebSocket server and keep the application running
    await asyncio.gather(
        websockets_server.start_server(),
    )


if __name__ == "__main__":
    """
    Application entry point.

    Runs the main asynchronous function using asyncio.run() which handles
    the event loop creation and cleanup. This is the standard way to run
    asyncio applications in Python 3.7+.
    """

    asyncio.run(async_main())
