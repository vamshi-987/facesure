
from pymongo import MongoClient
from config import Config

# Optimize connection pool for 10k users
client = MongoClient(
	Config.MONGO_URI,
	maxPoolSize=100,  # Max concurrent connections
	minPoolSize=10,   # Keep connections warm
	maxIdleTimeMS=45000,  # Close idle connections after 45s
	serverSelectionTimeoutMS=5000,  # Fail fast on network issues
	connectTimeoutMS=10000,
	socketTimeoutMS=20000,
	retryWrites=True,
	w="majority",  # Write concern for durability
	readPreference="primary"  # Read from primary, fallback to secondary
)

db = client["faceAuthDB"]

# Health check function
def check_db_connection():
	try:
		client.admin.command('ping')
		return True
	except Exception:
		return False
