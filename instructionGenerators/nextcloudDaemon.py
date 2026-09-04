from utils import general
from utils.imports import *

handler = general.nextCloudHandler()
logger = general.setLogger("nextCloudDaemon")

def checkHandler(handler: general.nextCloudHandler):
    while handler is None or handler.client is None:
        if handler.client is None:
            logger.warning("Problem with nextCloud API call")
            logger.warning("Retrying...")
        handler = general.nextCloudHandler()
        time.sleep()

    return handler

def actOnFile(handler: general.nextCloudHandler, fileJob: dict[str: str, str:str, str:str]):
    """
    fileJob Schema:
    [
        {
            localPath: str,
            serverPath: str,
            action: str
        }
    ]

    fileJobs are added chronologically as a queue
    """

    handler.action(fileJob["action"], fileJob["serverPath"], fileJob["localPath"])

def run():
    handler = None
    while True:
        handler = checkHandler(handler)

        pendingFiles = general.readJSON(general.pathInfo("jsonUtils")+"pendingNCFiles.json")
        while pendingFiles:
            actOnFile(handler, pendingFiles.pop(0))
            general.writeJSON(general.pathInfo("jsonUtils")+"pendingNCFiles.json", pendingFiles)
