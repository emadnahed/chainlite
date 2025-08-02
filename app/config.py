import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # MongoDB Configuration
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/chainlite')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'chainlite')
    
    # Application Settings
    NODE_IDENTIFIER = os.getenv('NODE_IDENTIFIER', str(os.urandom(16).hex()))
    
    # Mining Settings
    MINING_REWARD = 1.0
    MINING_SENDER = "0"  # Special address for mining rewards
    
    # Network Settings
    NODE_PORT = int(os.getenv('PORT', 8000))
    NODE_HOST = os.getenv('HOST', '0.0.0.0')

# Create a configuration instance
config = Config()
