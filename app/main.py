from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uuid import uuid4
from typing import Dict, Any
import logging

from .blockchain import Blockchain
from .models import (
    Transaction, Block, ChainResponse, NodeRegistration, MiningResponse,
    TransactionResponse, BlockResponse, ChainListResponse, NodeListResponse,
    ErrorResponse, BaseResponse
)
from .database import MongoDB

# Initialize MongoDB connection
mongo_db = MongoDB()

# Instantiate the Node
app = FastAPI(
    title="ChainLite API",
    description="A minimal blockchain API built with FastAPI",
    version="0.1.0",
    on_shutdown=[mongo_db.close_connection]
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React web
        "http://localhost:19006",  # Expo web
        "exp://*",                # All Expo apps
        "http://*",               # Any HTTP origin (for development)
        "https://*"               # Any HTTPS origin (for production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()

# Exception Handlers
@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError):
    logger.error(f"ValueError: {str(exc)}")
    error_response = ErrorResponse.error(
        description=str(exc) or "Invalid request data",
        code="ERR_400",
        http_status="BAD_REQUEST"
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.dict()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {str(exc.detail)}")
    error_response = ErrorResponse.error(
        description=str(exc.detail),
        code=f"HTTP_{exc.status_code}",
        http_status=exc.status_code
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    error_response = ErrorResponse.error(
        description="An unexpected error occurred",
        code="ERR_500",
        http_status="INTERNAL_SERVER_ERROR"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )

@app.get(
    "/",
    response_model=BaseResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    tags=["Root"]
)
async def read_root():
    """
    Root endpoint that provides information about the API and available endpoints
    """
    return BaseResponse.success(
        description="Welcome to ChainLite - A Minimal Blockchain API",
        data={
            "name": "ChainLite",
            "version": "1.0.0",
            "description": "A minimal blockchain implementation with RESTful API"
        },
        meta={
            "endpoints": [
                {"method": "GET", "path": "/", "description": "API information"},
                {"method": "GET", "path": "/chain", "description": "View the entire blockchain"},
                {"method": "POST", "path": "/transactions", "description": "Create a new transaction"},
                {"method": "GET", "path": "/mine", "description": "Mine a new block"},
                {"method": "POST", "path": "/nodes/register", "description": "Register new nodes"},
                {"method": "GET", "path": "/nodes/resolve", "description": "Resolve chain conflicts"}
            ]
        },
        code="MSG_0001"
    )

@app.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Transactions"]
)
async def create_transaction(transaction: Transaction):
    """
    Create a new transaction to be added to the next mined Block
    
    - **sender**: Address of the sender
    - **recipient**: Address of the recipient
    - **amount**: Amount to transfer (must be positive)
    """
    try:
        # Create a new transaction
        index = blockchain.new_transaction(
            sender=transaction.sender,
            recipient=transaction.recipient,
            amount=transaction.amount
        )
        
        return TransactionResponse.success(
            description=f"Transaction will be added to Block {index}",
            data={"transaction": transaction.dict(), "block_index": index},
            code="MSG_0027"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.get(
    "/mine",
    response_model=BlockResponse,
    status_code=status.HTTP_200_OK,
    tags=["Mining"]
)
async def mine_block():
    """
    Mine a new block by performing proof of work
    
    This endpoint will:
    1. Calculate the proof of work
    2. Reward the miner (this node) with 1 coin
    3. Add the new block to the chain
    """
    try:
        # Run the proof of work algorithm to get the next proof
        last_block = blockchain.last_block
        last_proof = last_block['proof']
        proof = blockchain.proof_of_work(last_proof)

        # Create a reward transaction for the miner
        blockchain.new_transaction(
            sender="0",  # This represents that this node has mined a new coin
            recipient=node_identifier,
            amount=1.0,  # Mining reward
        )

        # Forge the new Block by adding it to the chain
        previous_hash = blockchain.hash(last_block)
        block = blockchain.new_block(proof, previous_hash)
        
        # Convert ObjectId to string for JSON serialization
        def serialize_doc(doc):
            if isinstance(doc, dict):
                return {k: str(v) if k == '_id' else serialize_doc(v) for k, v in doc.items()}
            elif isinstance(doc, list):
                return [serialize_doc(item) for item in doc]
            elif hasattr(doc, 'isoformat'):  # Handle datetime objects
                return doc.isoformat()
            else:
                return doc
        
        # Get the block from database to ensure we have the latest version
        from bson import ObjectId
        block_id = block.get('_id')
        if block_id and isinstance(block_id, ObjectId):
            block = blockchain.blocks.find_one({'_id': block_id})
        
        # Prepare block for response
        block_for_response = serialize_doc(block)
        block_for_response['hash'] = blockchain.hash(block)
        
        return BlockResponse.success(
            description="New block successfully mined",
            data={
                "block": block_for_response,
                "miner": node_identifier,
                "reward": 1.0
            },
            code="MSG_0028"
        )
        
    except Exception as e:
        logger.error(f"Error mining block: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get(
    "/chain",
    response_model=ChainListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Blockchain"]
)
async def get_blockchain():
    """
    Retrieve the full blockchain
    
    Returns the complete blockchain with all blocks and transactions
    """
    try:
        # Reload the chain from database to ensure we have the latest data
        blockchain._load_from_database()
        
        # Convert blocks to include their hashes
        chain_with_hashes = []
        for block in blockchain.chain:
            # Create a clean copy of the block
            block_dict = dict(block)
            # Add the hash
            block_dict['hash'] = blockchain.hash(block)
            # Ensure transactions are properly serialized
            if 'transactions' in block_dict and block_dict['transactions']:
                block_dict['transactions'] = [
                    {k: v for k, v in tx.items() if k != '_id'}
                    for tx in block_dict['transactions']
                ]
            # Remove _id from the block itself
            block_dict.pop('_id', None)
            chain_with_hashes.append(block_dict)
            
        return ChainListResponse.success(
            description="Blockchain retrieved successfully",
            data={
                "chain": chain_with_hashes,
                "chain_length": len(chain_with_hashes),
                "total_transactions": sum(len(block.get('transactions', [])) for block in chain_with_hashes)
            },
            code="MSG_0029"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving blockchain: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve blockchain"
        )

@app.post(
    "/nodes/register",
    response_model=NodeListResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Nodes"]
)
async def register_nodes(nodes: NodeRegistration, request: Request):
    """
    Register new nodes with the network
    
    - **nodes**: List of node addresses (e.g., ['http://192.168.0.5:5000'])
    """
    if not nodes.nodes:
        # If no nodes provided, auto-register the requesting node
        client_host = request.client.host
        client_port = request.url.port or 8000
        
        # Get the server's actual IP address for mobile access
        import socket
        hostname = socket.gethostname()
        server_ip = socket.gethostbyname(hostname)
        
        # Use the server's IP instead of client's IP for mobile access
        nodes.nodes = [f"http://{server_ip}:{client_port}"]
    
    registered_nodes = []
    for node in nodes.nodes:
        try:
            # Basic URL formatting
            if not node.startswith(('http://', 'https://')):
                node = f"http://{node}"
                
            # Register the node
            blockchain.register_node(node)
            registered_nodes.append(node)
            logger.info(f"Registered new node: {node}")
            
            # Broadcast the new node to other nodes
            for peer in blockchain.nodes:
                if peer != node:  # Don't broadcast to self
                    try:
                        requests.post(
                            f"{peer}/nodes/register",
                            json={"nodes": [node]},
                            timeout=2
                        )
                    except requests.RequestException:
                        continue
            
        except Exception as e:
            logger.error(f"Error registering node {node}: {str(e)}")
            continue
    
    if not registered_nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid nodes were registered"
        )
    
    return NodeListResponse.success(
        description=f"Successfully registered {len(registered_nodes)} node(s)",
        data={
            "nodes": registered_nodes,
            "total_nodes": len(blockchain.nodes)
        },
        code="MSG_0030"
    )

@app.get(
    "/nodes",
    response_model=NodeListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Nodes"]
)
async def list_nodes():
    """
    List all registered nodes
    """
    return NodeListResponse.success(
        description="List of registered nodes",
        data={
            "nodes": list(blockchain.nodes),
            "total_nodes": len(blockchain.nodes)
        },
        code="MSG_0031"
    )

@app.get(
    "/nodes/resolve",
    response_model=ChainListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Consensus"]
)
async def resolve_conflicts():
    """
    Resolve any blockchain conflicts by replacing with the longest valid chain
    
    This endpoint will query all registered nodes and update the blockchain
    if a longer valid chain is found.
    """
    try:
        # Reload the chain to ensure we have the latest data
        blockchain._load_from_database()
        
        # Resolve conflicts with other nodes
        replaced = blockchain.resolve_conflicts()
        
        # Prepare the chain data for response
        chain_data = []
        for block in blockchain.chain:
            block_copy = dict(block)
            # Remove MongoDB _id if present
            block_copy.pop('_id', None)
            # Ensure transactions are properly formatted
            if 'transactions' in block_copy and block_copy['transactions']:
                block_copy['transactions'] = [
                    {k: v for k, v in tx.items() if k != '_id'}
                    for tx in block_copy['transactions']
                ]
            chain_data.append(block_copy)
        
        # Create the response data
        response_data = {
            "chain": chain_data,
            "chain_length": len(chain_data),
            "total_transactions": sum(len(block.get('transactions', [])) for block in chain_data)
        }
        
        if replaced:
            return ChainListResponse.success(
                description="Chain was replaced with a longer valid chain",
                data=response_data,
                code="MSG_0031"
            )
        else:
            return ChainListResponse.success(
                description="Local chain is authoritative (no longer chain found)",
                data=response_data,
                code="MSG_0032"
            )
            
    except Exception as e:
        logger.error(f"Error resolving conflicts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resolving blockchain conflicts: {str(e)}"
        )
