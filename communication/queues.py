###########EXTERNAL IMPORTS############

import asyncio

#######################################

#############LOCAL IMPORTS#############

#######################################

frontend_send_queue = asyncio.Queue(maxsize=10000)
frontend_receive_queue = asyncio.Queue(maxsize=10000)

modbus_tcp_send_queue = asyncio.Queue(maxsize=10000)
modbus_tcp_receive_queue = asyncio.Queue(maxsize=10000)

send_queues = [frontend_send_queue, modbus_tcp_send_queue]
receive_queues = [frontend_receive_queue, modbus_tcp_receive_queue]
