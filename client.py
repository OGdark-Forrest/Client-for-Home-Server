from utils.imports import *
from utils import general

def getAuthHeaders():
    deviceID = os.getenv("hsDeviceID")
    deviceKey = os.getenv("hsDeviceKey")

    if not deviceID or not deviceKey:
        return None

    return deviceID, deviceKey

class Connection:
    def __init__(self, uri):
        self.logger = general.setLogger("client.py: Connection")
        self.uri = uri
        self.isConnected = False

    async def initiateConnection(self):
        headers = getAuthHeaders()
        if not headers:
            self.logger.critical("Environment variables pointing to None, restart process")
            return
        self.logger.debug("Environment variables set")
        while True:
            try:
                self.websocket = await websockets.connect(
                    uri=self.uri,
                    additional_headers={
                        "deviceID": headers[0], 
                        "deviceKey": headers[1]
                        }
                )
                self.isConnected = True
                self.setComponents()
                break
            except Exception as e:
                self.isConnected = False
                self.logger.critical("Connection Failed")
                self.logger.exception(e)
                self.logger.info("RETRYING CONNECTION")
                await asyncio.sleep(10)

    def setComponents(self):
        self.jobHandler = general.tableHandler(general.pathInfo("db")+"jobQueue.db", "jobs")
        self.resultHandler = general.tableHandler(general.pathInfo("db")+"resultQueue.db", "results")

        self.sender = Sender(self.websocket)
        self.jobSelector = Selector(self.jobHandler)

        self.listener = Listener(self.websocket)
        self.resultSelector = Selector(self.resultHandler)

        self.errorHandler = ErrorHandler()
        self.smartRouter = SmartRouter()
        self.dumbRouter = DumbRouter(self.smartRouter, self.errorHandler)

        self.logger.debug("Client components set")

    async def startLoop(self):
        await asyncio.gather(
            self.startListen(),
            self.getJobs(),
            self.processResults()
        )
        self.logger.debug("Main Loop started")

    async def startListen(self):
        while self.isConnected:
            message = await self.listener.listen()
            self.logger.info("Message Received")
            self.logger.debug(message)
            self.resultHandler.addRecord(message)
            self.logger.debug("Added result to db file")

    async def getJobs(self):
        while self.isConnected:
            task = self.jobSelector.getTask()
            if task is None:
                await asyncio.sleep(1)
                continue
            self.logger.info("Job received")
            await self.sender.send(task)
            self.jobHandler.deleteRecord(task["requestID"])

    async def processResults(self):
        while True:
            result = self.resultSelector.getTask()

            if result is None:
                await asyncio.sleep(0.1)
                continue

            self.dumbRouter.route(result)
            self.resultHandler.deleteRecord(result["requestID"])

class Selector:
    def __init__(self, tableHandler: general.tableHandler):
        self.tableHandler = tableHandler
        self.logger = general.setLogger("client.py: Selector")

    def getTask(self):
        for i in range(1, 5):
            job = self.tableHandler.getRecordByVal(["priority"], [i])
            if job is not None:
                break
        return job

class Sender:
    def __init__(self, websocket):
        self.websocket = websocket
        self.logger = general.setLogger("client.py: Sender")

    async def send(self, data):
        if type(data) is dict:
            message = json.dumps(data)
        else:
            message = data
        await self.websocket.send(message)
        # print(message)

class Listener:
    def __init__(self, websocket):
        self.websocket = websocket
        self.logger = general.setLogger("client.py: Listener")

    async def listen(self):
        message = await self.websocket.recv()
        return json.loads(message)

class DumbRouter:
    def __init__(self, router, handler):
        self.logger = general.setLogger("client.py: DumbRouter")
        self.smartRouter = router
        self.errorHandler = handler

    def route(self, task):
        if task["resultStatus"] == "SUCCESS":
            self.smartRouter.route(task)
        else:
            self.errorHandler.handle(task)

class ErrorHandler:
    def __init__(self):
        self.logger = general.setLogger("client.py: ErrorHandler")
    def handle(self, task):
        print(task["resultStatus"])
        print(task["result"])

class SmartRouter:
    def __init__(self):
        self.routingTable = {}
        self.logger = general.setLogger("client.py: SmartRouter")

    def route(self, task):
        print(task["resultStatus"])
        print(task["result"])

async def run():
    conn = Connection("ws://home.aetherlink.uk/initWSS")
    await conn.initiateConnection()
    await conn.startLoop()

if __name__ == "__main__":
    general.configureLogger("clientLog.log", "INFO")
    logger = general.setLogger("client.py: main")
    logger.info("Connecting to server")
    asyncio.run(run())