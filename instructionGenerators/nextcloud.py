from utils import general
general.configureLogger("clientLog.log")

handler = general.nextCloudHandler()

handler.action("WRITE", "Documents/SameerProjectREADME.pdf", "C:/Users/meerc/Downloads/Sameer Project README.pdf")
