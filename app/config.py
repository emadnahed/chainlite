import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # MongoDB Configuration
    MONGODB_URI = os.getenv('MONGODB_URI')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'chainlite')
    
    # Application Settings
    NODE_IDENTIFIER = os.getenv('NODE_IDENTIFIER', str(os.urandom(16).hex()))
    
    # Mining Settings
    MINING_REWARD = 1.0
    MINING_SENDER = "0"  # Special address for mining rewards
    
    # Network Settings
    NODE_PORT = int(os.getenv('PORT', 8000))
    NODE_HOST = os.getenv('HOST', '0.0.0.0')
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI environment variable is not set")
        if not cls.MONGODB_URI.startswith(('mongodb://', 'mongodb+srv://')):
            raise ValueError("MONGODB_URI must start with 'mongodb://' or 'mongodb+srv://'")

# Create and validate configuration
config = Config()
try:
    config.validate()
except ValueError as e:
    print(f"Configuration error: {e}")
    raise
