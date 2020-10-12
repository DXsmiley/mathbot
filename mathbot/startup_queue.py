from aiohttp import web
import time

QUEUE_INTERVAL = 6

next_time_slot = 0

async def request_spot_in_queue(request):
    global next_time_slot
    this_time_slot = next_time_slot
    next_time_slot = max(time.time(), next_time_slot) + QUEUE_INTERVAL
    return web.Response(text=str(this_time_slot))

app = web.Application()
app.add_routes([web.post('/', request_spot_in_queue)])

web.run_app(app, host='127.0.0.1', port=7023)
