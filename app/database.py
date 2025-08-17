from typing import Optional, Dict, Any, List
from urllib.parse import quote_plus
from pymongo import MongoClient
from pymongo.database import Database
from .config import config

class MongoDB:
    _instance = None
    _client: MongoClient = None
    _db: Database = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
        return cls._instance

    def _initialize(self):
        """Initialize MongoDB connection if not already initialized."""
        if not self._initialized:
            try:
                # Get the MongoDB URI from config
                mongo_uri = config.MONGODB_URI
                
                # For logging purposes - don't log the actual password
                safe_uri = mongo_uri
                if '@' in mongo_uri:
                    safe_uri = mongo_uri[:mongo_uri.find('@')+1] + '*****'
                print(f"Connecting to MongoDB with URI: {safe_uri}")
                
                # Connect with the original URI
                self._client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=10000,
                    retryWrites=True,
                    w='majority',
                    tls=True,
                    tlsAllowInvalidCertificates=True,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=45000
                )
                # Test the connection
                self._client.server_info()
                self._db = self._client[config.MONGODB_DB_NAME]
                print("Successfully connected to MongoDB")
                self._initialized = True
            except Exception as e:
                print(f"Failed to connect to MongoDB: {str(e)}")
                raise
            
            # Create indexes for better query performance
            self.blocks = self._db.blocks
            self.transactions = self._db.transactions
            self.nodes = self._db.nodes
            
            # Create indexes
            self.blocks.create_index([("index", 1)], unique=True)
            self.transactions.create_index([("block_index", 1)])
            self.nodes.create_index([("address", 1)], unique=True)
            
            self._initialized = True

    def get_db(self) -> Database:
        """Get the database instance, initializing if necessary."""
        if not self._initialized:
            self._initialize()
        return self._db

    def close_connection(self):
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._initialized = False

def get_database() -> Database:
    """Get the database instance (for dependency injection)."""
    return MongoDB().get_db()
