from pymongo import MongoClient

MONGO_URI = "mongodb+srv://nivedithathangavel7:pgs123mongo@cluster0.uotjlvz.mongodb.net/?appName=Cluster0"

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

client.admin.command("ping")
print("✅ MongoDB Atlas connected successfully")
