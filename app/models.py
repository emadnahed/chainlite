from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Generic, TypeVar, Union
import re
from datetime import datetime
from enum import Enum

# Generic Type for response data
T = TypeVar('T')

class Status(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

class BaseResponse(BaseModel, Generic[T]):
    data: Optional[T] = {}
    code: str
    httpStatus: str
    description: str
    token: Optional[str] = ""
    meta: Optional[Dict[str, Any]] = None

    @classmethod
    def success(
        cls,
        description: str,
        data: Optional[Any] = None,
        meta: Optional[Dict[str, Any]] = None,
        code: str = "MSG_0000",
        http_status: str = "OK"
    ) -> 'BaseResponse[T]':
        return cls(
            data=data or {},
            code=code,
            httpStatus=http_status,
            description=description,
            meta=meta
        )

    @classmethod
    def error(
        cls,
        description: str,
        data: Optional[Any] = None,
        meta: Optional[Dict[str, Any]] = None,
        code: str = "ERR_0000",
        http_status: str = "ERROR"
    ) -> 'BaseResponse[T]':
        return cls(
            data=data or {},
            code=code,
            httpStatus=http_status,
            description=description,
            meta=meta
        )

class Transaction(BaseModel):
    sender: str = Field(..., description="Address of the sender")
    recipient: str = Field(..., description="Address of the recipient")
    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    signature: str = Field(..., min_length=1, description="Transaction signature or id")
    timestamp: int = Field(..., description="Epoch milliseconds when the tx was created")

    @validator('sender', 'recipient')
    def validate_address(cls, v: str) -> str:
        if not isinstance(v, str) or not re.match(r'^0x[a-fA-F0-9]{6,}$', v):
            raise ValueError('Invalid address format')
        return v

class Block(BaseModel):
    index: int = Field(..., description="The block index in the blockchain")
    timestamp: int = Field(..., description="Epoch milliseconds when the block was created")
    transactions: List[Transaction] = Field(..., description="List of transactions in the block")
    nonce: int = Field(..., description="The proof-of-work nonce")
    previous_hash: Optional[str] = Field(None, description="Hash of the previous block in the chain")
    hash: Optional[str] = Field(None, description="Hash of the current block")

class ChainResponse(BaseModel):
    chain: List[Block] = Field(..., description="List of blocks in the blockchain")
    chain_length: int = Field(..., description="Number of blocks in the blockchain")
    total_transactions: Optional[int] = Field(None, description="Total transactions across all blocks")

class NodeRegistration(BaseModel):
    nodes: List[str] = Field(..., min_items=1, description="List of node addresses to register")

class MiningResponse(BaseModel):
    message: str = Field(..., description="Status message")
    index: int = Field(..., description="Index of the newly mined block")
    transactions: List[Transaction] = Field(..., description="List of transactions included in the block")
    nonce: int = Field(..., description="The proof-of-work nonce used to mine this block")
    hash: str = Field(..., description="Hash of the newly mined block")
    previous_hash: str = Field(..., description="Hash of the previous block in the chain")

# Response Models
class TransactionResponse(BaseResponse[Transaction]):
    pass

class BlockResponse(BaseResponse[Block]):
    pass

class ChainListResponse(BaseResponse[ChainResponse]):
    pass

class NodeListResponse(BaseResponse[Dict[str, List[str]]]):
    pass

class ErrorResponse(BaseResponse[None]):
    error_type: Optional[str] = Field(None, description="Type of error that occurred")
