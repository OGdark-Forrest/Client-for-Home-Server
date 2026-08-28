from utils.imports import *
from utils import general

import os

deviceID = os.getenv("hsDeviceID")
deviceKey = os.getenv("hsDevicekey")

class Connection:
    def __init__(self, uri):
        self.uri = uri
        self.websocket = None

    async def connect(self):
        self.websocket = await websockets.connect(
            self.uri, 
            additional_headers={
                "deviceID": deviceID,
                "deviceKey": deviceKey
        })

        asyncio.create_task(self.listen())

    async def listen(self):
        try:
            while True:
                message = "\n" + await self.websocket.recv() + "\n"
                result = json.loads(message)
                resultStatus = result["resultStatus"]
                output = result["result"]
                print(f"\n{resultStatus}\n{output}")

        except websockets.ConnectionClosed:
            print("Disconnected from socket")

    async def send(self, message):
        await self.websocket.send(message)

requestID = str(uuid.uuid4())
timestamp = datetime.datetime.now().isoformat()

job1 = {
    "requestID": requestID,
    "timestamp": timestamp,
    "priority": "1",
    "jobDescription": "Get tool Schema",
    "endpoint": "toolinfo/getSchema",
    "params": {
        "endpoint": "filetransfer/copysingle"
    },
    "data": {}
}

requestID = str(uuid.uuid4())
timestamp = datetime.datetime.now().isoformat()

job2 = {
    "requestID": requestID,
    "timestamp": timestamp,
    "priority": "1",
    "jobDescription": "Get all available tools",
    "endpoint": "toolinfo/getall",
    "params": {
        "type": "AVAILABLE"
    },
    "data": {}
}

async def main():
    conn = Connection("ws://10.0.0.229:8005/initWSS")

    await conn.connect()

    while True:
        user_input = await asyncio.to_thread(input, "\nJob 1 or Job 2: ")

        if not user_input:
            break

        if user_input == "1":
            await conn.send(json.dumps(job1))
        else:
            await conn.send(json.dumps(job2))            


asyncio.run(main())