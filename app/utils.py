import hashlib
import json
from typing import Any, Dict

def hash_string_sha256(string: str) -> str:
    """
    Creates a SHA-256 hash of a string
    
    :param string: The string to hash
    :return: The SHA-256 hash of the string
    """
    return hashlib.sha256(string.encode()).hexdigest()

def valid_proof(last_proof: int, proof: int, difficulty: int = 4) -> bool:
    """
    Validates the Proof
    
    :param last_proof: Previous Proof
    :param proof: Current Proof
    :param difficulty: Number of leading zeros required
    :return: True if correct, False if not
    """
    guess = f"{last_proof}{proof}".encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash[:difficulty] == "0" * difficulty

def sort_dict_by_key(dictionary: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Sort a dictionary by its keys
    
    :param dictionary: Dictionary to sort
    :return: Sorted dictionary
    """
    return dict(sorted(dictionary.items()))

def hash_block(block: Dict[str, Any]) -> str:
    """
    Creates a SHA-256 hash of a Block
    
    :param block: Block
    :return: Hash of the block
    """
    # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()
