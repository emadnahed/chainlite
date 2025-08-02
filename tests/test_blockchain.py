import pytest
from app.blockchain import Blockchain
from app.models import Transaction

def test_new_block():
    """Test that a new block is created correctly"""
    blockchain = Blockchain()
    proof = 12345
    previous_hash = "previous_hash"
    
    block = blockchain.new_block(proof, previous_hash)
    
    assert block['index'] == 2  # 2 because genesis block is created in __init__
    assert block['proof'] == proof
    assert block['previous_hash'] == previous_hash
    assert len(block['transactions']) == 0  # No transactions added

def test_new_transaction():
    """Test that a new transaction is added to the transaction pool"""
    blockchain = Blockchain()
    
    # Add a transaction
    index = blockchain.new_transaction(
        sender="sender_address",
        recipient="recipient_address",
        amount=10.0
    )
    
    assert index == 2  # Next block to be mined will be #2
    assert len(blockchain.current_transactions) == 1
    assert blockchain.current_transactions[0]['sender'] == "sender_address"
    assert blockchain.current_transactions[0]['recipient'] == "recipient_address"
    assert blockchain.current_transactions[0]['amount'] == 10.0

def test_hash():
    """Test that the hash function works correctly"""
    blockchain = Blockchain()
    block = {
        'index': 1,
        'timestamp': 1234567890,
        'transactions': [],
        'proof': 100,
        'previous_hash': '1'
    }
    
    # The hash should be consistent for the same input
    hash1 = blockchain.hash(block)
    hash2 = blockchain.hash(block)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 produces a 64-character hex string

def test_proof_of_work():
    """Test that the proof of work algorithm works correctly"""
    blockchain = Blockchain()
    last_proof = 100
    proof = blockchain.proof_of_work(last_proof)
    
    # The proof should be valid
    assert blockchain.valid_proof(last_proof, proof)
    
    # An invalid proof should not validate
    assert not blockchain.valid_proof(last_proof, proof + 1)

def test_register_node():
    """Test that a new node can be registered"""
    blockchain = Blockchain()
    
    # Register a new node
    blockchain.register_node("http://192.168.0.1:5000")
    
    assert "192.168.0.1:5000" in blockchain.nodes
    assert len(blockchain.nodes) == 1

def test_valid_chain():
    """Test that a valid chain is correctly identified"""
    blockchain = Blockchain()
    
    # Add some transactions and mine a block
    blockchain.new_transaction("Alice", "Bob", 10.0)
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)
    previous_hash = blockchain.hash(last_block)
    blockchain.new_block(proof, previous_hash)
    
    # The chain should be valid
    assert blockchain.valid_chain(blockchain.chain)
