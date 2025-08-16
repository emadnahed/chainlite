import hashlib
import json
from time import time
from typing import List, Dict, Any, Optional
from uuid import uuid4
from urllib.parse import urlparse
import logging
import requests
from .database import db

logger = logging.getLogger(__name__)

class Blockchain:
    def __init__(self):
        self.chain: List[Dict[str, Any]] = []
        self.current_transactions: List[Dict[str, Any]] = []
        self.nodes = set()
        
        # Initialize database collections
        self.blocks = db.blocks
        self.transactions = db.transactions
        self.node_collection = db.nodes
        
        # Load existing data from database
        self._load_from_database()
        
        # Create the genesis block if chain is empty
        if len(self.chain) == 0:
            self.new_block(previous_hash='1', proof=100)
    
    def new_block(self, proof: int, previous_hash: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new Block in the Blockchain
        
        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """
        # Create a clean block dictionary
        block = {
            'index': len(self.chain) + 1,
            'timestamp': int(time() * 1000),
            'transactions': [dict(tx) for tx in self.current_transactions],
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]) if self.chain else None,
        }

        # Insert block into database and get the inserted ID
        result = self.blocks.insert_one(block)
        
        # Save transactions to database with block reference
        if self.current_transactions:
            transactions_to_insert = []
            for tx in self.current_transactions:
                tx_copy = dict(tx)  # Create a copy to avoid modifying the original
                tx_copy['block_index'] = block['index']
                tx_copy['block_id'] = result.inserted_id
                transactions_to_insert.append(tx_copy)
            
            if transactions_to_insert:
                self.transactions.insert_many(transactions_to_insert)

        # Reset the current list of transactions
        self.current_transactions = []
        
        # Get the complete block from database
        block_from_db = self.blocks.find_one({'_id': result.inserted_id})
        
        # Update in-memory chain with the database version
        if block_from_db:
            # Convert ObjectId to string for JSON serialization
            block_from_db['_id'] = str(block_from_db['_id'])
            self.chain.append(block_from_db)
            return block_from_db
            
        # Fallback to the original block if database retrieval fails
        self.chain.append(block)
        return block
    
    def new_transaction(
        self,
        sender: str,
        recipient: str,
        amount: float,
        signature: Optional[str] = None,
        timestamp_ms: Optional[int] = None,
    ) -> int:
        """
        Creates a new transaction to go into the next mined Block
        
        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """
        tx: Dict[str, Any] = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        }
        if signature is not None:
            tx['signature'] = signature
        if timestamp_ms is None:
            timestamp_ms = int(time() * 1000)
        tx['timestamp'] = timestamp_ms
        # Deterministic transaction hash
        try:
            tx_for_hash = {
                'sender': sender,
                'recipient': recipient,
                'amount': amount,
                'signature': signature or '',
                'timestamp': timestamp_ms,
            }
            tx_string = json.dumps(tx_for_hash, sort_keys=True)
            tx['hash'] = hashlib.sha256(tx_string.encode()).hexdigest()
        except Exception:
            pass
        self.current_transactions.append(tx)
        return self.last_block['index'] + 1
    
    @property
    def last_block(self) -> Dict[str, Any]:
        return self.chain[-1]
    
    @staticmethod
    def hash(block: Dict[str, Any]) -> str:
        """
        Creates a SHA-256 hash of a Block
        
        :param block: Block
        :return: str
        """
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    def proof_of_work(self, last_proof: int) -> int:
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        
        :param last_proof: <int>
        :return: <int>
        """
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof
    
    @staticmethod
    def valid_proof(last_proof: int, proof: int) -> bool:
        """
        Validates the Proof
        
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """
        guess = f"{last_proof}{proof}".encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
    
    def register_node(self, address: str) -> None:
        """
        Add a new node to the list of nodes
        
        :param address: Address of node. Eg. 'http://192.168.0.5:5000' or '192.168.0.5:5000'
        """
        try:
            # Handle case where scheme might be missing
            if not address.startswith(('http://', 'https://')):
                address = f'http://{address}'
                
            parsed_url = urlparse(address)
            if not parsed_url.netloc:
                logger.warning(f'Invalid node address format: {address}')
                return
                
            # Add both with and without scheme for flexibility
            node_address = parsed_url.netloc
            
            # Don't add self
            if node_address in self.nodes:
                return
                
            # Add to in-memory set
            self.nodes.add(node_address)
            
            # Add to database
            self.node_collection.update_one(
                {'address': node_address},
                {'$setOnInsert': {'address': node_address}},
                upsert=True
            )
            
            logger.info(f'Successfully registered node: {node_address}')
            
        except Exception as e:
            logger.error(f'Error registering node {address}: {str(e)}')
            # If database operation fails, remove from in-memory set
            if node_address in self.nodes:
                self.nodes.remove(node_address)
            raise ValueError(f'Failed to register node {node_address}: {str(e)}')
    
    def _load_from_database(self):
        """Load blockchain data from the database."""
        from bson import ObjectId
        
        def convert_mongo_doc(doc):
            if not doc:
                return doc
            doc = dict(doc)
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
            return doc
        
        try:
            # Load blocks and convert ObjectId to string
            self.chain = [convert_mongo_doc(block) for block in 
                         self.blocks.find().sort('index', 1)]
            
            # Load current transactions (those not yet in a block)
            self.current_transactions = [convert_mongo_doc(tx) for tx in 
                                       self.transactions.find({'block_index': {'$exists': False}})]
            
            # Load nodes - store as a set of addresses
            self.nodes = set()
            for node in self.node_collection.find():
                if 'address' in node:
                    self.nodes.add(node['address'])
            
        except Exception as e:
            print(f"Error loading from database: {e}")
            self.chain = []
            self.current_transactions = []
            self.nodes = set()

    def valid_chain(self, chain: List[Dict[str, Any]]) -> bool:
        """
        Determine if a given blockchain is valid
        
        :param chain: A blockchain
        :return: True if valid, False if not
        """
        if not chain:
            return False
            
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False
            
            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            
            last_block = block
            current_index += 1
        
        return True
    
    def resolve_conflicts(self) -> bool:
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        
        :return: True if our chain was replaced, False if not
        """
        import requests
        from requests.exceptions import RequestException
        
        if not self.nodes:
            print("No nodes registered to resolve conflicts with")
            return False
            
        neighbours = self.nodes
        new_chain = None
        
        # We're only looking for chains longer than ours
        max_length = len(self.chain)
        
        print(f"Resolving conflicts with {len(neighbours)} nodes")
        
        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            try:
                print(f"Checking node: {node}")
                response = requests.get(f'http://{node}/chain', timeout=5)
                
                if response.status_code == 200:
                    response_data = response.json()
                    if 'data' in response_data and 'chain' in response_data['data']:
                        chain_data = response_data['data']
                        length = chain_data.get('chain_length', 0)
                        chain = chain_data.get('chain', [])
                        
                        print(f"Node {node} chain length: {length}")
                        
                        # Check if the length is longer and the chain is valid
                        if length > max_length and self.valid_chain(chain):
                            print(f"Found longer valid chain from {node}")
                            max_length = length
                            new_chain = chain
            except RequestException as e:
                print(f"Error connecting to node {node}: {str(e)}")
                continue
        
        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            print(f"Replacing chain with new chain of length {len(new_chain)}")
            self.chain = new_chain
            # Save to database
            self.blocks.delete_many({})
            for block in new_chain:
                self.blocks.insert_one(block)
            return True
        
        print("No longer valid chain found")
        return False
