from utils.imports import *

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

class dbHandler:
    def __init__(self, fileName, type):
        self.fileName = fileName
        connection = sqlite3.connect(fileName)
        cursor = connection.cursor()
        self.type = type
        try:
            if self.type == "JOB":
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requestID TEXT,
                    timestamp TEXT,
                    priority INTEGER,
                    jobDescription TEXT,
                    endpoint TEXT,
                    params TEXT,
                    data TEXT
                )
                """)
            else:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requestID TEXT,
                    timestamp TEXT,
                    priority INTEGER,
                    jobDescription TEXT,
                    endpoint TEXT,
                    params TEXT,
                    data TEXT,
                    resultStatus TEXT,
                    result TEXT
                )
                """)

            connection.commit()
        finally:
            connection.close()

    def addRecord(self, record):
        connection = sqlite3.connect(self.fileName)
        cursor = connection.cursor()
        try:
            if self.type == "JOB":
                cursor.execute("""
                INSERT INTO jobs (
                    requestID,
                    timestamp,
                    priority,
                    jobDescription,
                    endpoint,
                    params,
                    data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record["requestID"],
                    record["timestamp"],
                    int(record["priority"]),
                    record["jobDescription"],
                    record["endpoint"],
                    json.dumps(record["params"]),
                    json.dumps(record["data"])
                ))

                connection.commit()
                return

            cursor.execute("""
            INSERT INTO results (
                requestID,
                timestamp,
                priority,
                jobDescription,
                endpoint,
                params,
                data,
                resultStatus,
                result
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["requestID"],
                record["timestamp"],
                int(record["priority"]),
                record["jobDescription"],
                record["endpoint"],
                json.dumps(record["params"]),
                json.dumps(record["data"]),
                record["resultStatus"],
                record["result"]
            ))

            connection.commit()
        finally:
            connection.close()

    def getRecord(self):
        connection = sqlite3.connect(self.fileName)
        cursor = connection.cursor()
        try:
            if self.type == "JOB":
                cursor.execute("""
                    SELECT *
                    FROM jobs
                    ORDER BY priority DESC, id ASC
                    LIMIT 1
                """)

                record = cursor.fetchone()

                if record is None:
                    return None

                return {
                    "id": record[0],
                    "requestID": record[1],
                    "timestamp": record[2],
                    "priority": str(record[3]),
                    "jobDescription": record[4],
                    "endpoint": record[5],
                    "params": json.loads(record[6]),
                    "data": json.loads(record[7])
                }

            cursor.execute("""
                SELECT *
                FROM results
                ORDER BY priority DESC, id ASC
                LIMIT 1
            """)

            record = cursor.fetchone()

            if record is None:
                return None

            return {
                "id": record[0],
                "requestID": record[1],
                "timestamp": record[2],
                "priority": str(record[3]),
                "jobDescription": record[4],
                "endpoint": record[5],
                "params": json.loads(record[6]),
                "data": json.loads(record[7]),
                "resultStatus": record[8],
                "result": record[9]
            }

        finally:
            connection.close()


    def deleteRecord(self, recordID):
        connection = sqlite3.connect(self.fileName)
        cursor = connection.cursor()
        try:
            if self.type == "JOB":
                table = "jobs"
            else:
                table = "results"
            cursor.execute(
                f"DELETE FROM {table} WHERE id = ?",
                (recordID,)
            )

            connection.commit()
        finally:
            connection.close()

    def clearDB(self):
        connection = sqlite3.connect(self.fileName)
        cursor = connection.cursor()
        if self.type == "JOB":
            table = "jobs"
        else:
            table = "results"
        try:
            cursor.execute(f"DELETE FROM {table}")
        finally:
            connection.close()

def setLogger(name):
    return logging.getLogger(name)