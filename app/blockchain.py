import hashlib
import json
from time import time
from typing import List, Dict, Any, Optional
from uuid import uuid4
from urllib.parse import urlparse
import requests
from .database import db

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
            'timestamp': time(),
            'transactions': [dict(tx) for tx in self.current_transactions],  # Create deep copy
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
    
    def new_transaction(self, sender: str, recipient: str, amount: float) -> int:
        """
        Creates a new transaction to go into the next mined Block
        
        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
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
        
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """
        if not address:
            raise ValueError('Empty node address provided')
            
        parsed_url = urlparse(address)
        node_address = ''
        
        if parsed_url.netloc:
            node_address = parsed_url.netloc
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            node_address = parsed_url.path
        else:
            raise ValueError(f'Invalid URL: {address}')
            
        if not node_address:
            raise ValueError(f'Could not parse node address from: {address}')
            
        try:
            # Add to in-memory set
            self.nodes.add(node_address)
            
            # Add to database
            self.node_collection.update_one(
                {'address': node_address},
                {'$setOnInsert': {'address': node_address}},
                upsert=True
            )
        except Exception as e:
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
        neighbours = self.nodes
        new_chain = None
        
        # We're only looking for chains longer than ours
        max_length = len(self.chain)
        
        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                
                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        
        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True
        
        return False
