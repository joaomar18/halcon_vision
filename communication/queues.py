###########EXTERNAL IMPORTS############

import asyncio

#######################################

#############LOCAL IMPORTS#############

#######################################

frontend_send_queue = asyncio.Queue(maxsize=10000)
frontend_receive_queue = asyncio.Queue(maxsize=10000)