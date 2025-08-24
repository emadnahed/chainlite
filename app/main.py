from fastapi import FastAPI, HTTPException, Depends, status, Request, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uuid import uuid4
from typing import Dict, Any, Optional, List
import logging
import requests

from .blockchain import Blockchain
from .models import (
    Transaction, Block, ChainResponse, NodeRegistration, MiningResponse,
    TransactionResponse, BlockResponse, ChainListResponse, NodeListResponse,
    ErrorResponse, BaseResponse
)
from .database import get_database

# Get database instance
db = get_database()

# Instantiate the Node
app = FastAPI(
    title="ChainLite API",
    description="A minimal blockchain API built with FastAPI",
    version="0.1.0",
    on_shutdown=[db.close_connection]
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
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "bad_request",
                "message": str(exc) or "Invalid request data",
                "details": {}
            }
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {str(exc.detail)}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"http_{exc.status_code}",
                "message": str(exc.detail),
                "details": {}
            }
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
                "details": {}
            }
        }
    )

@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    tags=["Root"]
)
async def read_root():
    """
    Root endpoint that provides information about the API
    """
    return {
        "data": {
            "name": "ChainLite",
            "version": "1.0.0",
            "description": "A minimal blockchain implementation with RESTful API"
        },
        "code": "MSG_0001",
        "httpStatus": "OK",
        "description": "Welcome to ChainLite - A Minimal Blockchain API"
    }

@app.post(
    "/transactions",
    status_code=status.HTTP_201_CREATED,
    tags=["Transactions"]
)
async def create_transaction(transaction: Transaction):
    """Create a new transaction and return the transaction data in standard format."""
    try:
        blockchain.new_transaction(
            sender=transaction.sender,
            recipient=transaction.recipient,
            amount=transaction.amount,
            signature=transaction.signature,
            timestamp_ms=transaction.timestamp,
        )
        return {
            "data": transaction.dict(),
            "code": "MSG_0062",
            "httpStatus": "OK",
            "description": "Transaction created successfully"
        }
    except ValueError as e:
        return {
            "data": {},
            "code": "ERR_0040",
            "httpStatus": "BAD_REQUEST",
            "description": str(e)
        }

@app.get(
    "/mine",
    status_code=status.HTTP_200_OK,
    tags=["Mining"]
)
async def mine_block(miner_address: Optional[str] = Query(None)):
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

        # Validate miner address if provided
        reward_recipient = miner_address or node_identifier
        if miner_address is not None:
            import re
            if not re.match(r'^0x[a-fA-F0-9]{6,}$', miner_address):
                return {
                    "data": {},
                    "code": "ERR_0041",
                    "httpStatus": "BAD_REQUEST",
                    "description": "Invalid miner address format"
                }
        
        # Create a reward transaction for the miner
        blockchain.new_transaction(
            sender="0",
            recipient=reward_recipient,
            amount=1.0,
            signature="",
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
        block_hash = blockchain.hash(block)
        block_for_response['hash'] = block_hash
        
        response_data = {
            "index": block_for_response.get("index"),
            "transactions": block_for_response.get("transactions", []),
            "nonce": block_for_response.get("proof"),
            "hash": block_hash,
            "previous_hash": block_for_response.get("previous_hash"),
        }
        
        return {
            "data": response_data,
            "code": "MSG_0063",
            "httpStatus": "OK",
            "description": "New block forged successfully"
        }
        
    except Exception as e:
        logger.error(f"Error mining block: {str(e)}")
        return {
            "data": {},
            "code": "ERR_0050",
            "httpStatus": "INTERNAL_SERVER_ERROR",
            "description": f"Error mining block: {str(e)}"
        }

@app.get(
    "/chain",
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
        
        # Convert blocks to include their hashes and mapped nonce
        chain_with_hashes = []
        for block in blockchain.chain:
            # Create a clean copy of the block
            block_dict = dict(block)
            # Remove _id from transactions if they have it
            if 'transactions' in block_dict and isinstance(block_dict['transactions'], list):
                block_dict['transactions'] = [
                    {k: v for k, v in tx.items() if k != '_id'}
                    for tx in block_dict['transactions']
                ]
            # Remove _id from the block itself
            block_dict.pop('_id', None)
            # Ensure proof is mapped to nonce for consistency
            if 'proof' in block_dict:
                block_dict['nonce'] = block_dict.pop('proof')
            chain_with_hashes.append(block_dict)
            
        return {
            "data": {
                "chain": chain_with_hashes,
                "chain_length": len(chain_with_hashes),
                "total_transactions": sum(len(block.get('transactions', [])) for block in chain_with_hashes)
            },
            "code": "MSG_0064",
            "httpStatus": "OK",
            "description": "Blockchain retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving blockchain: {str(e)}")
        return {
            "data": {},
            "code": "ERR_0051",
            "httpStatus": "INTERNAL_SERVER_ERROR",
            "description": "Failed to retrieve blockchain"
        }

@app.post(
    "/nodes/register",
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
                            f"http://{peer}/nodes/register",
                            json={"nodes": [node]},
                            timeout=2
                        )
                    except requests.RequestException:
                        continue
            
        except Exception as e:
            logger.error(f"Error registering node {node}: {str(e)}")
            continue
    
    if not registered_nodes:
        return {
            "data": {},
            "code": "ERR_0060",
            "httpStatus": "BAD_REQUEST",
            "description": "No valid nodes were registered"
        }
    
    # Format node addresses consistently
    formatted_nodes = [f"http://{addr}" if not str(addr).startswith("http") else str(addr) 
                      for addr in list(blockchain.nodes)]
    
    return {
        "data": {
            "registered_nodes": registered_nodes,
            "total_nodes": formatted_nodes,
            "total_count": len(formatted_nodes)
        },
        "code": "MSG_0065",
        "httpStatus": "CREATED",
        "description": "Nodes registered successfully"
    }

@app.get(
    "/nodes",
    status_code=status.HTTP_200_OK,
    tags=["Nodes"]
)
async def list_nodes():
    """
    List all registered nodes
    
    Returns a list of all nodes currently registered in the network
    """
    try:
        # Format node addresses consistently
        formatted_nodes = [
            f"http://{addr}" if not str(addr).startswith("http") else str(addr) 
            for addr in list(blockchain.nodes)
        ]
        
        return {
            "data": {
                "nodes": formatted_nodes,
                "total_nodes": len(formatted_nodes)
            },
            "code": "MSG_0068",
            "httpStatus": "OK",
            "description": "List of registered nodes retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error retrieving node list: {str(e)}")
        return {
            "data": {},
            "code": "ERR_0062",
            "httpStatus": "INTERNAL_SERVER_ERROR",
            "description": "Failed to retrieve node list"
        }

@app.get(
    "/nodes/resolve",
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
            "total_transactions": sum(len(block.get('transactions', [])) for block in chain_data),
            "consensus_reached": not replaced,
            "action_taken": "Chain was replaced" if replaced else "Local chain is authoritative"
        }
        
        return {
            "data": response_data,
            "code": "MSG_0066" if not replaced else "MSG_0067",
            "httpStatus": "OK",
            "description": "Local chain is authoritative" if not replaced else "Chain was replaced with a longer valid chain"
        }
            
    except Exception as e:
        logger.error(f"Error resolving conflicts: {str(e)}", exc_info=True)
        return {
            "data": {},
            "code": "ERR_0061",
            "httpStatus": "INTERNAL_SERVER_ERROR",
            "description": f"Error resolving blockchain conflicts: {str(e)}"
        }

# New endpoints
@app.get("/pending_tx", tags=["Transactions"])
async def get_pending_transactions():
    """
    Get all pending transactions that are waiting to be included in a block.
    
    Returns:
        A list of pending transactions with standardized response format
    """
    return {
        "data": {
            "transactions": blockchain.current_transactions,
            "total_count": len(blockchain.current_transactions)
        },
        "code": "MSG_0068",
        "httpStatus": "OK",
        "description": "List of pending transactions retrieved successfully"
    }

@app.get("/balance/{address}", tags=["Wallet"])
async def get_balance(address: str = Path(..., regex=r"^0x[a-fA-F0-9]{6,}$")):
    sent = 0.0
    received = 0.0
    for block in blockchain.chain:
        for tx in block.get("transactions", []):
            if tx.get("sender") == address:
                sent += float(tx.get("amount", 0))
            if tx.get("recipient") == address:
                received += float(tx.get("amount", 0))
    for tx in blockchain.current_transactions:
        if tx.get("sender") == address:
            sent += float(tx.get("amount", 0))
    return {"balance": max(received - sent, 0.0)}

@app.get("/blocks/latest", tags=["Blockchain"])
async def get_latest_blocks(limit: int = Query(10, ge=1, le=100)):
    blocks = blockchain.chain[-limit:][::-1]
    resp: List[Dict[str, Any]] = []
    for b in blocks:
        bd = dict(b)
        if 'proof' in bd:
            bd['nonce'] = bd.pop('proof')
        bd['hash'] = blockchain.hash(b)
        bd.pop('_id', None)
        resp.append(bd)
    return {"data": {"blocks": resp}}

@app.get("/blocks/{height}", tags=["Blockchain"])
async def get_block_by_height(height: int = Path(..., ge=1)):
    for b in blockchain.chain:
        if b.get('index') == height:
            bd = dict(b)
            if 'proof' in bd:
                bd['nonce'] = bd.pop('proof')
            bd['hash'] = blockchain.hash(b)
            bd.pop('_id', None)
            return {"data": {"block": bd}}
    raise HTTPException(status_code=404, detail="Block not found")

@app.get("/transactions/latest", tags=["Transactions"])
async def get_latest_transactions(limit: int = Query(20, ge=1, le=100)):
    # Pull the latest mined transactions from the DB
    cursor = blockchain.transactions.find().sort([("timestamp", -1)]).limit(limit)
    txs = []
    for tx in cursor:
        tx = {k: (str(v) if k == '_id' else v) for k, v in dict(tx).items()}
        tx.pop('_id', None)
        txs.append(tx)
    return {"data": {"transactions": txs}}

@app.get("/transactions/{hash}", tags=["Transactions"])
async def get_transaction_by_hash(hash: str):
    # Search pending
    for tx in blockchain.current_transactions:
        if tx.get('hash') == hash:
            return {"data": {"transaction": tx}}
    # Search confirmed
    found = blockchain.transactions.find_one({"hash": hash})
    if found:
        found = {k: (str(v) if k == '_id' else v) for k, v in dict(found).items()}
        found.pop('_id', None)
        return {"data": {"transaction": found}}
    raise HTTPException(status_code=404, detail="Transaction not found")

@app.get("/address/{address}/transactions", tags=["Transactions"])
async def get_transactions_by_address(
    address: str = Path(..., regex=r"^0x[a-fA-F0-9]{6,}$"),
    limit: int = Query(20, ge=1, le=100),
    before: Optional[int] = Query(None, description="Return txs before this timestamp (ms)"),
):
    query: Dict[str, Any] = {"$or": [{"sender": address}, {"recipient": address}]}
    if before is not None:
        query["timestamp"] = {"$lt": before}
    cursor = blockchain.transactions.find(query).sort([("timestamp", -1)]).limit(limit)
    txs: List[Dict[str, Any]] = []
    for tx in cursor:
        tx = {k: (str(v) if k == '_id' else v) for k, v in dict(tx).items()}
        tx.pop('_id', None)
        txs.append(tx)
    return {"data": {"transactions": txs}}

@app.get(
    "/mining/status",
    status_code=status.HTTP_200_OK,
    tags=["Mining"]
)
async def mining_status():
    """
    Get the current mining status
    
    Returns information about the current mining state including:
    - Current hash rate
    - Mining difficulty
    - Current target
    - Number of nonce attempts
    - Whether mining is in progress
    - Details about the last mined block
    """
    try:
        last = blockchain.last_block if blockchain.chain else None
        
        return {
            "data": {
                "hashRate": 0,  # Could be enhanced to track actual hash rate
                "difficulty": 4,  # Matches the proof of work difficulty
                "currentTarget": "0000" + "f" * 60,  # Leading 4 zeros target
                "nonceAttempts": 0,  # Could be enhanced to track actual attempts
                "inProgress": False,  # Could be enhanced to track actual mining state
                "lastBlock": {
                    "index": last.get("index") if last else 0,
                    "hash": blockchain.hash(last) if last else "",
                    "timestamp": last.get("timestamp") if last else 0,
                    "transactions_count": len(last.get("transactions", [])) if last else 0
                }
            },
            "code": "MSG_0070",
            "httpStatus": "OK",
            "description": "Mining status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting mining status: {str(e)}")
        return {
            "data": {},
            "code": "ERR_0053",
            "httpStatus": "INTERNAL_SERVER_ERROR",
            "description": "Failed to retrieve mining status"
        }

@app.delete("/nodes/{node_id}", tags=["Nodes"])
async def unregister_node(node_id: str = Path(..., description="URL-safe identifier of a node (host:port or full URL)")):
    # Normalize to netloc (host:port)
    from urllib.parse import urlparse
    parsed = urlparse(node_id if node_id.startswith(('http://', 'https://')) else f"http://{node_id}")
    netloc = parsed.netloc
    if netloc in blockchain.nodes:
        blockchain.nodes.remove(netloc)
        try:
            blockchain.node_collection.delete_one({"address": netloc})
        except Exception:
            pass
    return {"message": "Node(s) removed", "total_nodes": [f"http://{addr}" for addr in list(blockchain.nodes)]}

@app.post("/nodes/unregister", tags=["Nodes"])
async def unregister_nodes(body: Dict[str, List[str]]):
    nodes = body.get("nodes", []) if isinstance(body, dict) else []
    from urllib.parse import urlparse
    removed: List[str] = []
    for node in nodes:
        parsed = urlparse(node if node.startswith(('http://', 'https://')) else f"http://{node}")
        netloc = parsed.netloc
        if netloc in blockchain.nodes:
            blockchain.nodes.remove(netloc)
            removed.append(netloc)
            try:
                blockchain.node_collection.delete_one({"address": netloc})
            except Exception:
                pass
    return {"message": "Node(s) removed", "total_nodes": [f"http://{addr}" for addr in list(blockchain.nodes)]}

@app.get("/blocks/hash/{hash}", tags=["Blockchain"])
async def get_block_by_hash(hash: str):
    for b in blockchain.chain:
        if blockchain.hash(b) == hash:
            bd = dict(b)
            if 'proof' in bd:
                bd['nonce'] = bd.pop('proof')
            bd['hash'] = hash
            bd.pop('_id', None)
            return {"data": {"block": bd}}
    raise HTTPException(status_code=404, detail="Block not found")

@app.get(
    "/status",
    status_code=status.HTTP_200_OK,
    tags=["Blockchain"]
)
async def get_blockchain_status():
    """
    Get the current status of the blockchain
    
    Returns key metrics about the blockchain including:
    - Chain length
    - Number of pending transactions
    - Number of connected nodes
    - Mining difficulty
    - Timestamp of the last block
    """
    try:
        last_block = blockchain.last_block if blockchain.chain else None
        
        # Calculate total transactions across all blocks
        total_transactions = sum(len(block.get('transactions', [])) for block in blockchain.chain)
        
        return {
            "data": {
                "chain_length": len(blockchain.chain),
                "pending_transactions": len(blockchain.current_transactions),
                "connected_nodes": len(blockchain.nodes),
                "difficulty": 4,  # Matches the mining difficulty in mining_status
                "last_block": {
                    "index": last_block.get("index") if last_block else 0,
                    "timestamp": last_block.get("timestamp") if last_block else 0,
                    "transactions_count": len(last_block.get("transactions", [])) if last_block else 0
                },
                "total_transactions": total_transactions
            },
            "code": "MSG_0069",
            "httpStatus": "OK",
            "description": "Blockchain status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting blockchain status: {str(e)}")
        return {
            "data": {},
            "code": "ERR_0052",
            "httpStatus": "INTERNAL_SERVER_ERROR",
            "description": "Failed to retrieve blockchain status"
        }
