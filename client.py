from utils.imports import *
from utils import general

def getAuthHeaders():
    deviceID = os.getenv("hsDeviceID")
    deviceKey = os.getenv("hsDeviceKey")

    if not deviceID or not deviceKey:
        return None

    return deviceID, deviceKey


def configureLogger():
    logging.basicConfig(
        filename="utils/logFiles/clientLog.log",
        level=logging.DEBUG
    )

class Connection:
    def __init__(self, uri):
        self.logger = general.setLogger("client.py-Connection")
        self.uri = uri
        self.isConnected = False

    async def initiateConnection(self):
        headers = getAuthHeaders()
        if not headers:
            self.logger.critical("Environment variables pointing to None, restart process")
            return
        self.logger.debug("Environment variables not None")
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
        except Exception as e:
            self.isConnected = False
            self.logger.critical("Connection Failed")
            self.logger.exception(e)

    def setComponents(self):
        self.jobHandler = general.dbHandler(general.pathInfo("db")+"jobQueue.db", "JOB")
        self.resultHandler = general.dbHandler(general.pathInfo("db")+"resultQueue.db", "RESULT")

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
            self.logger.debug(task)
            await self.sender.send(task)
            self.jobHandler.deleteRecord(task["id"])

    async def processResults(self):
        while True:
            result = self.resultSelector.getTask()

            if result is None:
                await asyncio.sleep(0.1)
                continue

            self.dumbRouter.route(result)
            self.resultHandler.deleteRecord(result["id"])

class Selector:
    def __init__(self, dbHandler: general.dbHandler):
        self.dbHandler = dbHandler
        self.logger = general.setLogger("client.py-Selector")

    def getTask(self):
        return self.dbHandler.getRecord()

class Sender:
    def __init__(self, websocket):
        self.websocket = websocket
        self.logger = general.setLogger("client.py-Sender")

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
        self.logger = general.setLogger("client.py-Listener")

    async def listen(self):
        message = await self.websocket.recv()
        return json.loads(message)

class DumbRouter:
    def __init__(self, router, handler):
        self.logger = general.setLogger("client.py-DumbRouter")
        self.smartRouter = router
        self.errorHandler = handler

    def route(self, task):
        if task["resultStatus"] == "SUCCESS":
            self.smartRouter.route(task)
        else:
            self.errorHandler.handle(task)

class ErrorHandler:
    def __init__(self):
        self.logger = general.setLogger("client.py-ErrorHandler")
    def handle(self, task):
        print(task["resultStatus"])
        print(task["result"])

class SmartRouter:
    def __init__(self):
        self.routingTable = {}
        self.logger = general.setLogger("client.py-SmartRouter")

    def route(self, task):
        print(task["resultStatus"])
        print(task["result"])

async def run():
    conn = Connection("ws://home.aetherlink.uk/initWSS")
    await conn.initiateConnection()
    await conn.startLoop()

if __name__ == "__main__":
    configureLogger()
    logger = general.setLogger("client.py-main")
    logger.info("Server is starting")
    asyncio.run(run())