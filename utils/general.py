from utils.imports import *

WEB_DAV_PASSWORD = os.getenv("nextcloudAppPassword")

def readJSON(filename):
    with open(filename) as rfile:
        data = json.load(rfile)
    return data

def writeJSON(filename, data):
    with open(filename, "w") as wfile:
        json.dump(data, wfile, indent=4)

def writeTXT(filename, data):
    with open(filename, "w", encoding="utf-8") as wfile:
        wfile.write(data)

def readTXT(filename):
    with open(filename, "r", encoding="utf-8") as rfile:
        data = rfile.read()
    return data

def pathInfo(category):
    """
    Categories: jsonAuth, jsonService, jsonUtils, logs, custom, vbs
    """
    return readJSON("utils/jsonFiles/utils/filePath.json")[category]

class tableHandler:
    def __init__(self, fileName, tableName):
        tableMetaData = readJSON(pathInfo("jsonUtils")+"dbMetaData.json")
        self.fileName = fileName
        self.tableName = tableName

        connection = sqlite3.connect(self.fileName)
        cursor = connection.cursor()

        self.logger = setLogger(f"TableHandler: {tableName}")
        self.fields = []

        try:
            params = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            for field in tableMetaData[tableName]:
                args = tableMetaData[tableName][field]["params"]
                params.append(f"{field} {" ".join(args)}")
                self.fields.append(field)
            query = f"CREATE TABLE IF NOT EXISTS {tableName} (\n{",\n".join(params)}\n)"
            self.tableFieldInfo = tableMetaData[tableName]
            cursor.execute(query)
            self.logger.info(f"Executed Query: {query}")
            connection.commit()
        except Exception as e:
            self.logger.exception(str(e))
        finally:
            connection.close()

    def addRecord(self, record):
        connection = sqlite3.connect(self.fileName)
        cursor = connection.cursor()

        try:
            query = f"INSERT INTO {self.tableName} (\n{",\n".join(self.fields)}\n)\nVALUES ({", ".join(["?"]*len(self.fields))})"

            recordParams = []
            for field in self.fields:
                if field not in record:
                    continue
                mod = self.tableFieldInfo[field]["mods"]
                if mod == "None":
                    item = record[field]
                elif mod == "integer":
                    item = int(record[field])
                elif mod == "dict":
                    item = json.dumps(record[field])

                recordParams.append(item)

            cursor.execute(query, tuple(recordParams))
            connection.commit()
        except Exception as e:
            self.logger.exception(str(e))
        finally:
            connection.close()

    def getAnyRecord(self):
        connection = sqlite3.connect(self.fileName)
        cursor = connection.cursor()
        try:
            query = f"""
                    SELECT *
                    FROM {self.tableName}
                    ORDER BY priority DESC, id ASC
                    LIMIT 1
                """
            cursor.execute(query)

            record = cursor.fetchone()

            if not record:
                return None

            returnDict = {}
            
            for ind, field in enumerate(self.fields):
                mod = self.tableFieldInfo[field]["mods"]

                if mod == "None":
                    item = record[ind+1]
                elif mod == "integer":
                    item = str(record[ind+1])
                elif mod == "dict":
                    item = json.loads(record[ind+1])

                returnDict[field] = item

            return returnDict
        except Exception as e:
            self.logger.exception(str(e))
        finally:
            connection.close()

    def getRecordByVal(self, params, vals):
        connection = sqlite3.connect(self.fileName)
        cursor = connection.cursor()
        try:
            whereParams = []
            for param, val in zip(params, vals):
                if self.tableFieldInfo[param]["mods"] == "None":
                    val = f'"{val}"'
                whereParams.append(f"{param}={val}")

            query = f"""
                    SELECT *
                    FROM {self.tableName}
                    WHERE {" AND ".join(whereParams)}
                    ORDER BY id ASC
                    LIMIT 1
                """

            cursor.execute(query)

            record = cursor.fetchone()

            if not record:
                return None

            returnDict = {}
            
            for ind, field in enumerate(self.fields):
                mod = self.tableFieldInfo[field]["mods"]

                if mod == "None":
                    item = record[ind+1]
                elif mod == "integer":
                    item = str(record[ind+1])
                elif mod == "dict":
                    item = json.loads(record[ind+1])

                returnDict[field] = item

            return returnDict
        except Exception as e:
            self.logger.exception(str(e))
        finally:
            connection.close()

    def deleteRecord(self, requestID):
        connection = sqlite3.connect(self.fileName)
        cursor = connection.cursor()
        try:
            query = f"DELETE FROM {self.tableName} WHERE requestID = ?"
            cursor.execute(
                query,
                (requestID,)
            )
            connection.commit()
        except Exception as e:
            self.logger.exception(str(e))
        finally:
            connection.close()

    def clearTable(self):
        connection = sqlite3.connect(self.fileName)
        cursor = connection.cursor()
        try:
            cursor.execute(f"DELETE FROM {self.tableName}")
            self.logger.debug(f"Deleted table {self.tableName}")
        except Exception as e:
            self.logger.exception(str(e))
        finally:
            connection.close()

class nextCloudHandler:
    def __init__(self):
        self.logger = setLogger("nextCloudHandler")
        self.logger.setLevel(logging.INFO)

        if os.getenv("nextcloudAppPassword") is None:
            self.logger.critical("Environment Variable for App Password is None")
            quit()

        creds = {
            "webdav_hostname": "http://cloud.aetherlink.uk/remote.php/dav/files/darkForrest/",
            "webdav_login": "darkForrest",
            "webdav_password": WEB_DAV_PASSWORD
        }
        try:
            self.client = Client(creds)
        except Exception as e:
            self.logger.critical("Failed to connect to server")
            self.logger.exception(str(e))

        self.actionMap = {
            "WRITE": self.uploadFile,
            "MOD": self.updateFile,
            "READ": self.downloadFile,
            "DEL": self.deleteFile
        }

    def uploadFile(self, serverPath, localPath):
        try:
            self.client.upload_sync(remote_path=serverPath, local_path=localPath)
            self.logger.info(f"File {localPath} sent from client")
        except Exception as e:
            self.logger.exception(str(e))
            return False

        if not self.client.check(serverPath):
            self.logger.warning(f"Server failed to receive file {localPath}")
            return False
        else:
            self.logger.info(f"Server has received file {localPath}")
            return True

    def updateFile(self, serverPath, localPath):
        self.uploadFile(serverPath, localPath)

    def downloadFile(self, serverPath, localPath):
        try:
            self.client.download_sync(remote_path=serverPath, local_path=localPath)
            self.logger.info(f"File {localPath} has been downloaded from server")
        except Exception as e:
            self.logger.exception(str(e))
            return False

        if not os.path.exists(localPath):
            self.logger.warning(f"Client failed to add file {localPath}")
            return False
        else:
            self.logger.info(f"Client has added file {localPath}")
            return True

    def deleteFile(self, serverPath, localPath="None"):
        try:
            self.client.clean(remote_path=serverPath)
            self.logger.info(f"File {serverPath} has been deleted from client-side")
        except Exception as e:
            self.logger.exception(str(e))
            return False

        if self.client.check(remote_path=serverPath):
            self.logger.warning(f"Server has failed to delete file {serverPath}")
            return False
        else:
            self.logger.info(f"Server has deleted file {serverPath}")
            return True

    def action(self, operation, serverPath, localPath="None"):
        actionResult = self.actionMap[operation](serverPath, localPath)
        if actionResult is False:
            fileJob = {
                "localPath": localPath,
                "serverPath": serverPath,
                "operation": operation
            }
            writeJSON(pathInfo("jsonUtils")+"pendingNCFiles.json", fileJob)
            self.logger.info("fileJob has been appended to pending files")


def setLogger(name):
    return logging.getLogger(name)

def configureLogger(fileName, level="DEBUG"):
    levelMap = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "CRITICAL": logging.CRITICAL
    }
    levelThreshold = levelMap[level]
    
    logging.basicConfig(
        filename=f"utils/logs/{fileName}",
        level=levelThreshold,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )