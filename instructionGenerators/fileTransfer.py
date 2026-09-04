from utils.imports import *
from utils import general

class ChunkifierSingle:
    def __init__(self, filePath: str, chunkSize: int, directory: str, fileName: str, priority, dbPath):
        """
            Directory: the one in BackupLaptops,
            FileName: the one in BackupLaptops.
            filePath: actual file path in transferring system
        """
        self.logger = general.setLogger("fileTransfer.py-ChunkifierSingle")
        self.filePath = filePath
        self.chunkSize = chunkSize
        self.priority = priority

        self.setNumberOfChunks()

        self.fileName = fileName
        self.dir = "C:/Users/meerc/LaptopBackups/"+directory+"/"
        self.chunkList = []
        self.chunkPackets = []

        self.jobHandler = general.dbHandler(dbPath, "JOB")

        self.generateChunkList()
        self.createStartFilePacket()
        self.createChunkPackets()

    def encode(self, byteData):
        encodedMessage = base64.b64encode(byteData).decode("ascii")
        return encodedMessage

    def setNumberOfChunks(self):
        try:
            fileSize = os.path.getsize(self.filePath)
            self.numberOfChunks = math.ceil(fileSize / self.chunkSize)
        except Exception as e:
            raise e

    def generateChunkList(self):
        with open(self.filePath, "rb") as rfile:
            data = rfile.read()

        for i in range(0, len(data), self.chunkSize):
            self.chunkList.append(data[i:i+self.chunkSize])

    def createStartFilePacket(self):
        requestID = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        self.startPacket = {
            "requestID": requestID,
            "timestamp": timestamp,
            "priority": str(self.priority),
            "jobDescription": f"Transferring File at {self.dir+self.fileName}",
            "endpoint": "files/copysingle",
            "params": {
                "fileID": str(self.filePath),
                "fileName": self.fileName,
                "numberOfChunks": self.numberOfChunks,
                "directory": self.dir
            },
            "data": {}
        }

    def createChunkPackets(self):
        requestID = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()        
        currChunk = 1
        for chunk in self.chunkList:
            chunkPacket = {
            "requestID": requestID,
            "timestamp": timestamp,
            "priority": str(self.priority),
            "jobDescription": f"Transfer File Packets for {self.dir+self.fileName}",
            "endpoint": "files/copysingle",
            "params": {
                "fileID": str(self.filePath),
                'chunkNumber': None
            },
            "data": {
                "chunkData": None
            }
        }
            chunkPacket["params"]["chunkNumber"] = currChunk
            chunkPacket["data"]["chunkData"] = self.encode(chunk)
            self.chunkPackets.append(chunkPacket)
            currChunk += 1

    def sendPackets(self):
        self.jobHandler.addRecord(self.startPacket)
        for chunkPacket in self.chunkPackets:
            self.jobHandler.addRecord(chunkPacket)


class ChunkifierDirectory:
    def __init__(self, directoryPath, excludedDirectories, chunkSize):
        self.logger = general.setLogger("fileTransfer.py-ChunkifierDirectory")
        self.directoryPath = Path(directoryPath)
        self.excluded = excludedDirectories
        self.chunkSize = chunkSize

        self.filePaths = []
        self.buildFilePaths()

    def buildFilePaths(self):
        if not self.directoryPath.is_dir():
            self.filePaths.append(self.directoryPath)
            return

        for path in self.directoryPath.rglob("*"):
            if path.is_file() and not any(part in self.excluded for part in path.parts):
                self.filePaths.append(path)

    def startTransfer(self, nextcloud=False, handler:general.nextCloudHandler = None):
        rootDirectory = self.directoryPath.name

        for path in self.filePaths:
            relativePath = path.relative_to(self.directoryPath)

            directory = Path(rootDirectory) / relativePath.parent
            fileName = relativePath.name

            if not nextcloud:
                chunkifyObj = ChunkifierSingle(
                    path,
                    self.chunkSize,
                    str(directory),
                    fileName,
                    1,
                    general.pathInfo("db")+"jobQueue.db"
                )
                chunkifyObj.sendPackets()
            else:
                handler.action("WRITE", f"LaptopBackups/{str(directory)}", path)

def tryConnect():
    return general.nextCloudHandler()

IMPORTANT_EXTENSIONS = {".py", ".json", ".txt", ".db", ".pdf", ".md", ".ppt", ".config",  ".env", ".c", ".cpp", ".java", ".csv", ".ico", ".png", ".jpeg", ".jpg"}
excludedFolders = {".venv", "__pycache__"}
chunkSize = 64 * 1024

def getContents(path):
    files = []
    directories = []

    for entry in os.scandir(path):
        if entry.is_file():
            files.append(entry)
        elif entry.is_dir():
            directories.append(entry)

    return files, directories

def transferDir(uploadingPath):
    fileList, dirList = getContents(uploadingPath)

    handler = tryConnect()
    attempt = 1
    nextcloudAvailable = False
    while not handler.client:
        if attempt == 5:
            break
        handler = tryConnect()
        if handler.client:
            nextcloudAvailable = True
            break
        attempt += 1

    for filePath in fileList:
        if Path(filePath.path).suffix not in IMPORTANT_EXTENSIONS:
            continue

        if nextcloudAvailable:
            handler.action("WRITE", "LaptopBackups/", filePath.path)
        else:
            ChunkifierSingle(filePath.path, chunkSize, "", filePath.name, 1, general.pathInfo("db")+"jobQueue.db").sendPackets()

    for dirPath in dirList:
        obj = ChunkifierDirectory(dirPath.path, excludedFolders, chunkSize)
        obj.startTransfer(nextcloudAvailable, handler)