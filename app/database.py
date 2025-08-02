from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from pymongo.database import Database
from .config import config

class MongoDB:
    _instance = None
    _client: MongoClient = None
    _db: Database = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize MongoDB connection."""
        self._client = MongoClient(config.MONGODB_URI)
        self._db = self._client[config.MONGODB_DB_NAME]
        
        # Create indexes for better query performance
        self.blocks = self._db.blocks
        self.transactions = self._db.transactions
        self.nodes = self._db.nodes
        
        # Create indexes
        self.blocks.create_index([("index", 1)], unique=True)
        self.transactions.create_index([("block_index", 1)])
        self.nodes.create_index([("address", 1)], unique=True)

    def get_db(self) -> Database:
        """Get the database instance."""
        return self._db

    def close_connection(self):
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()

# Singleton instance
db = MongoDB().get_db()

def get_database() -> Database:
    """Get the database instance (for dependency injection)."""
    return MongoDB().get_db()
