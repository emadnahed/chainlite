# ChainLite API Examples

This document provides cURL commands to interact with the ChainLite API. The server should be running on `http://127.0.0.1:8000`.

## Request/Response Validation

### Transaction Model
```json
{
  "sender": "string (required, regex: ^0x[a-fA-F0-9]{6,}$)",
  "recipient": "string (required, regex: ^0x[a-fA-F0-9]{6,}$)", 
  "amount": "number (required, must be > 0)",
  "signature": "string (required, min length: 1)",
  "timestamp": "integer (required, epoch milliseconds)"
}
```

### Node Registration Model
```json
{
  "nodes": ["string array (required, min items: 1)"]
}
```

### Address Validation
- All wallet addresses must follow the format: `^0x[a-fA-F0-9]{6,}$`
- Example valid address: `0xabc123456789`

### Common Response Format
Most endpoints return data in this structure:
```json
{
  "data": { /* endpoint-specific data */ },
  "message": "string (for some endpoints)"
}
```

## 1. View Available Endpoints

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/' \
  -H 'accept: application/json'
```

## 2. Create a New Transaction

**Request Validation:**
- `sender` and `recipient` must be valid hex addresses (format: `^0x[a-fA-F0-9]{6,}$`)
- `amount` must be positive number
- `signature` and `timestamp` are required fields
- Server auto-generates transaction hash based on all fields

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/transactions' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "sender": "0xabc123456789",
  "recipient": "0xdef987654321",
  "amount": 10.5,
  "signature": "signed_payload_hex_or_base64",
  "timestamp": 1712345678901
}'
```

**Response:**
```json
{
  "data": {
    "transaction": {
      "sender": "0xabc123456789",
      "recipient": "0xdef987654321",
      "amount": 10.5,
      "signature": "signed_payload_hex_or_base64",
      "timestamp": 1712345678901,
      "hash": "0423abce2a573da25474d4048eb95972887c2d5f8acb9f78856068effca5b22c"
    }
  },
  "code": "MSG_0001",
  "httpStatus": "CREATED",
  "description": "Transaction created successfully"
}
```

## 3. Mine a New Block

**Optional Parameters:**
- `miner_address` (query param): Valid hex address to receive mining reward (defaults to node identifier)

**Process:**
1. Performs proof-of-work algorithm
2. Adds reward transaction (1 coin to miner)
3. Creates new block with all pending transactions
4. Validates miner address format if provided

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/mine' \
  -H 'accept: application/json'
```

**With custom miner address:**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/mine?miner_address=0xabc123456789' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "data": {
    "message": "New block forged",
    "index": 18,
    "transactions": [
      {
        "sender": "0",
        "recipient": "0xabc123456789",
        "amount": 1.0,
        "signature": "",
        "timestamp": 1756119729276,
        "hash": "3ffe4e3a972bd2750f9836a2771fef4de534091c13e86de7f2583d49166e0bc9"
      }
    ],
    "nonce": 209765,
    "hash": "8c96edf4f1e407cd3aceeba66778fe7675e4066b63992568a3b1ca6297fa75d6",
    "previous_hash": "f3379a7b21c1a9e59abd0269402d3de214487189672adb6dd6f29b2baa4636a8"
  },
  "code": "MSG_0002",
  "httpStatus": "CREATED",
  "description": "Block mined successfully"
}
```

## 4. View the Full Blockchain

Returns full chain from database with each block including:
- `index`, `timestamp`, `transactions` (without internal `_id`),
- `nonce` (mapped from internal `proof`), `previous_hash`, and computed `hash`.

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/chain' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "data": {
    "chain": [
      {
        "index": 1,
        "timestamp": 1754173382.922078,
        "transactions": [],
        "proof": 100,
        "previous_hash": null
      },
      {
        "index": 2,
        "timestamp": 1754173859.144962,
        "transactions": [
          {
            "sender": "0",
            "recipient": "3c2f8a00250646339c24eb5d4a60675d",
            "amount": 1.0
          }
        ],
        "proof": 35293,
        "previous_hash": "474458693c0aedc7644b150cc7568027798d356cd0eef2afd81c2d56f5c5b606"
      }
      // ... more blocks
    ],
    "chain_length": 18,
    "total_transactions": 24
  },
  "code": "MSG_0064",
  "httpStatus": "OK",
  "description": "Blockchain retrieved successfully"
}
```

## 5. Register New Nodes

- If body `nodes` is empty or omitted, the server auto-registers itself using its IP and the request port for mobile-friendly access.
- Each node can be provided with or without scheme; it will be normalized internally.
- Successful registrations are broadcast to existing peers.

**Response:**
```json
{
  "data": {
    "registered_nodes": [
      "http://127.0.0.1:8002",
      "http://127.0.0.1:8003"
    ],
    "total_nodes": [
      "http://127.0.0.1:8002",
      "http://127.0.0.1:8003",
      "http://127.0.0.1:8001"
    ],
    "total_count": 3
  },
  "code": "MSG_0065",
  "httpStatus": "CREATED",
  "description": "Nodes registered successfully"
}

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/nodes/register' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "nodes": [
    "http://127.0.0.1:8002",
    "http://127.0.0.1:8003"
  ]
}'
```

## 6. Resolve Chain Conflicts (Consensus)

Applies consensus algorithm by checking all registered nodes for the longest valid chain.

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/nodes/resolve' \
  -H 'accept: application/json'
```

**Response (Local Chain Authoritative):**
```json
{
  "data": {
    "chain": [
      // ... full chain data
    ],
    "chain_length": 18,
    "total_transactions": 24,
    "consensus_reached": true,
    "action_taken": "Local chain is authoritative"
  },
  "code": "MSG_0066",
  "httpStatus": "OK",
  "description": "Local chain is authoritative"
}
```

**Response (Chain Replaced):**
```json
{
  "data": {
    "chain": [
      // ... full chain data from the network
    ],
    "chain_length": 20,
    "total_transactions": 30,
    "consensus_reached": true,
    "action_taken": "Chain was replaced"
  },
  "code": "MSG_0067",
  "httpStatus": "OK",
  "description": "Chain was replaced with a longer valid chain"
}
```

## 7. List Nodes

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/nodes' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "data": {
    "nodes": [
      "http://127.0.0.1:8002",
      "http://127.0.0.1:8003",
      "http://127.0.0.1:8001"
    ],
    "total_nodes": 3
  },
  "code": "MSG_0068",
  "httpStatus": "OK",
  "description": "List of registered nodes retrieved successfully"
}
```

## 8. Unregister Single Node

Remove a specific node from the network.

```bash
curl -X 'DELETE' \
  'http://127.0.0.1:8000/nodes/127.0.0.1:8002' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "data": {
    "removed_node": "127.0.0.1:8002",
    "total_nodes": [
      "http://127.0.0.1:8003",
      "http://127.0.0.1:8001"
    ],
    "total_count": 2
  },
  "code": "MSG_0071",
  "httpStatus": "OK",
  "description": "Node unregistered successfully"
}

## 9. Unregister Multiple Nodes

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/nodes/unregister' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "nodes": [
    "http://127.0.0.1:8002",
    "http://127.0.0.1:8003"
  ]
}'
```

## 10. Get Pending Transactions

Returns all transactions in the mempool that haven't been mined yet.

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/pending_tx' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "data": {
    "transactions": [],
    "total_count": 0
  },
  "code": "MSG_0068",
  "httpStatus": "OK",
  "description": "List of pending transactions retrieved successfully"
}
```

## 11. Get Wallet Balance

Calculate the balance for a specific address by summing all sent/received transactions.

**Address Validation:** Must match pattern `^0x[a-fA-F0-9]{6,}$`

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/balance/0xabc123456789' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "balance": 0.0
}
```

## 12. Get Latest Blocks

Retrieve the most recent blocks from the blockchain.

**Query Parameters:**
- `limit` (optional): Number of blocks to return (1-100, default: 10)

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/blocks/latest?limit=5' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "data": {
    "blocks": [
      {
        "index": 18,
        "timestamp": 1756119729276,
        "transactions": [
          {
            "sender": "0",
            "recipient": "0xabc123456789",
            "amount": 1.0,
            "signature": "",
            "timestamp": 1756119729276,
            "hash": "3ffe4e3a972bd2750f9836a2771fef4de534091c13e86de7f2583d49166e0bc9"
          }
        ],
        "previous_hash": "f3379a7b21c1a9e59abd0269402d3de214487189672adb6dd6f29b2baa4636a8",
        "nonce": 209765,
        "hash": "8c96edf4f1e407cd3aceeba66778fe7675e4066b63992568a3b1ca6297fa75d6"
      },
      {
        "index": 17,
        "timestamp": 1756119720777,
        "transactions": [
          {
            "sender": "0xabc123456789",
            "recipient": "0xdef987654321",
            "amount": 10.5,
            "signature": "signed_payload_hex_or_base64",
            "timestamp": 1712345678901,
            "hash": "0423abce2a573da25474d4048eb95972887c2d5f8acb9f78856068effca5b22c"
          },
          {
            "sender": "0",
            "recipient": "48a751baa10b472ab913a9a33d734714",
            "amount": 1.0,
            "signature": "",
            "timestamp": 1756119720777,
            "hash": "abdb6f78256a9d087dc191b64a92f9f84a181284237deafa95fa8ff5c9cb46bb"
          }
        ],
        "previous_hash": "fe84ed48f12f076da52822f013219f0c4770c727f46591d00f045aef0a1fc552",
        "nonce": 15889,
        "hash": "f3379a7b21c1a9e59abd0269402d3de214487189672adb6dd6f29b2baa4636a8"
      },
      {
        "index": 16,
        "timestamp": 1756111889822,
        "transactions": [
          {
            "sender": "0",
            "recipient": "0xabc123456789",
            "amount": 1.0,
            "signature": "",
            "timestamp": 1756111889822,
            "hash": "e7ba2ce2353db64735e586dbd96697e3dedf956e2b748df4ecd2cd3cc277c97b"
          }
        ],
        "previous_hash": "7f4bcb44dcf7c97a5851e6b1897ebd8a8944bd38eca3f8f18d3b8205a64c06d2",
        "nonce": 29341,
        "hash": "fe84ed48f12f076da52822f013219f0c4770c727f46591d00f045aef0a1fc552"
      },
      {
        "index": 15,
        "timestamp": 1756111875609,
        "transactions": [
          {
            "sender": "0xabc123456789",
            "recipient": "0xdef987654321",
            "amount": 10.5,
            "signature": "signed_payload_hex_or_base64",
            "timestamp": 1712345678901,
            "hash": "0423abce2a573da25474d4048eb95972887c2d5f8acb9f78856068effca5b22c"
          },
          {
            "sender": "0xabc123456789",
            "recipient": "0xdef987654321",
            "amount": 10.5,
            "signature": "signed_payload_hex_or_base64",
            "timestamp": 1712345678901,
            "hash": "0423abce2a573da25474d4048eb95972887c2d5f8acb9f78856068effca5b22c"
          },
          {
            "sender": "0",
            "recipient": "17ec96a8c6d446038215108a16221e1e",
            "amount": 1.0,
            "signature": "",
            "timestamp": 1756111875609,
            "hash": "99b525d1f30cc88031dc3ac711f6c1bbe1198b99b27dd85e19102315d81a7841"
          }
        ],
        "previous_hash": "804065055cb8ea15a706d851878d64d61717b7f5f9bc7d4e25a679af34111cc1",
        "nonce": 20760,
        "hash": "7f4bcb44dcf7c97a5851e6b1897ebd8a8944bd38eca3f8f18d3b8205a64c06d2"
      },
      {
        "index": 14,
        "timestamp": 1756021635108,
        "transactions": [
          {
            "sender": "0",
            "recipient": "738325c4cc434b22915cbbfc09e5aedc",
            "amount": 1.0,
            "signature": "",
            "timestamp": 1756021635108,
            "hash": "3ad907fb320dc021282ad8ce884008b302dcbac0755a75179b6cd1a7498c5874"
          }
        ],
        "previous_hash": "02020c6889b3d58bbaa9e76a9463e201c03f00bdca2c2e72c1112ba0bab4d7af",
        "nonce": 153122,
        "hash": "804065055cb8ea15a706d851878d64d61717b7f5f9bc7d4e25a679af34111cc1"
      }
    ],
    "total_count": 5
  },
  "code": "MSG_0076",
  "httpStatus": "OK",
  "description": "Latest blocks retrieved successfully"
}
```

## 13. Get Block by Height

Retrieve a specific block by its index/height.

**Path Parameters:**
- `height`: Block index (integer >= 1)

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/blocks/2' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "data": {
    "block": {
      "index": 2,
      "timestamp": 1754173859.144962,
      "transactions": [
        {
          "sender": "0",
          "recipient": "3c2f8a00250646339c24eb5d4a60675d",
          "amount": 1.0
        }
      ],
      "previous_hash": "474458693c0aedc7644b150cc7568027798d356cd0eef2afd81c2d56f5c5b606",
      "nonce": 35293,
      "hash": "ba601d5b17f7e6be208f98174c71f89e29907850309d61eeb857f84c268fe6cc"
    }
  },
  "code": "MSG_0077",
  "httpStatus": "OK",
  "description": "Block retrieved successfully"
}

## 14. Get Block by Hash

Retrieve a specific block by its SHA-256 hash.

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/blocks/hash/000abc123456789...' \
  -H 'accept: application/json'
```

**Response (Success):**
```json
{
  "data": {
    "block": {
      "index": 2,
      "timestamp": 1754173859.144962,
      "transactions": [
        {
          "sender": "0",
          "recipient": "3c2f8a00250646339c24eb5d4a60675d",
          "amount": 1.0
        }
      ],
      "previous_hash": "474458693c0aedc7644b150cc7568027798d356cd0eef2afd81c2d56f5c5b606",
      "nonce": 35293,
      "hash": "ba601d5b17f7e6be208f98174c71f89e29907850309d61eeb857f84c268fe6cc"
    }
  },
  "code": "MSG_0077",
  "httpStatus": "OK",
  "description": "Block retrieved successfully"
}
```

**Response (Not Found):**
```json
{
  "data": {},
  "code": "ERR_0079",
  "httpStatus": "NOT_FOUND",
  "description": "Block with hash 000abc123456789... not found"
}

## 15. Get Latest Transactions

Retrieve the most recent confirmed transactions from the database.

**Query Parameters:**
- `limit` (optional): Number of transactions to return (1-100, default: 20)

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/transactions/latest?limit=10' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "data": {
    "transactions": [
      {
        "sender": "0",
        "recipient": "0xabc123456789",
        "amount": "1.0",
        "signature": "",
        "timestamp": "1756119729276",
        "hash": "3ffe4e3a972bd2750f9836a2771fef4de534091c13e86de7f2583d49166e0bc9",
        "block_index": "18"
      },
      {
        "sender": "0",
        "recipient": "48a751baa10b472ab913a9a33d734714",
        "amount": "1.0",
        "signature": "",
        "timestamp": "1756119720777",
        "hash": "abdb6f78256a9d087dc191b64a92f9f84a181284237deafa95fa8ff5c9cb46bb",
        "block_index": "17"
      },
      {
        "sender": "0",
        "recipient": "0xabc123456789",
        "amount": "1.0",
        "signature": "",
        "timestamp": "1756111889822",
        "hash": "e7ba2ce2353db64735e586dbd96697e3dedf956e2b748df4ecd2cd3cc277c97b",
        "block_index": "16"
      },
      {
        "sender": "0",
        "recipient": "17ec96a8c6d446038215108a16221e1e",
        "amount": "1.0",
        "signature": "",
        "timestamp": "1756111875609",
        "hash": "99b525d1f30cc88031dc3ac711f6c1bbe1198b99b27dd85e19102315d81a7841",
        "block_index": "15"
      }
    ],
    "total_count": 4
  },
  "code": "MSG_0080",
  "httpStatus": "OK",
  "description": "Latest transactions retrieved successfully"
}
```

## 16. Get Transaction by Hash

Search for a transaction by its SHA-256 hash in both pending and confirmed transactions.

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/transactions/3ffe4e3a972bd2750f9836a2771fef4de534091c13e86de7f2583d49166e0bc9' \
  -H 'accept: application/json'
```

**Response (Found in Block):**
```json
{
  "data": {
    "transaction": {
      "sender": "0",
      "recipient": "0xabc123456789",
      "amount": "1.0",
      "signature": "",
      "timestamp": "1756119729276",
      "hash": "3ffe4e3a972bd2750f9836a2771fef4de534091c13e86de7f2583d49166e0bc9",
      "block_index": "18",
      "status": "confirmed"
    }
  },
  "code": "MSG_0081",
  "httpStatus": "OK",
  "description": "Transaction found in blockchain"
}
```

**Response (Found in Pending):**
```json
{
  "data": {
    "transaction": {
      "sender": "0xabc123456789",
      "recipient": "0xdef987654321",
      "amount": 10.5,
      "signature": "signed_payload",
      "timestamp": 1712345678901,
      "hash": "abc123...",
      "block_index": null,
      "status": "pending"
    }
  },
  "code": "MSG_0081",
  "httpStatus": "OK",
  "description": "Transaction retrieved successfully (pending)"
}
```

**Response (Not Found):**
```json
{
  "data": {},
  "code": "ERR_0082",
  "httpStatus": "NOT_FOUND",
  "description": "Transaction with hash not found in blockchain or mempool"
}
```

## 17. Get Transactions for Address

Retrieve all transactions where the address is either sender or recipient.

**Path Parameters:**
- `address`: Valid hex address (`^0x[a-fA-F0-9]{6,}$`)

**Query Parameters:**
- `limit` (optional): Number of transactions (1-100, default: 20)
- `before` (optional): Return transactions before this timestamp (epoch ms)

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/address/0xabc123456789/transactions' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "data": {
    "address": "0xabc123456789",
    "sent": [
      {
        "recipient": "0xdef987654321",
        "amount": "10.5",
        "timestamp": "1712345678901",
        "hash": "0423abce2a573da25474d4048eb95972887c2d5f8acb9f78856068effca5b22c",
        "block_index": "17"
      }
    ],
    "received": [
      {
        "sender": "0",
        "amount": "1.0",
        "timestamp": "1756119729276",
        "hash": "3ffe4e3a972bd2750f9836a2771fef4de534091c13e86de7f2583d49166e0bc9",
        "block_index": "18"
      },
      {
        "sender": "0",
        "amount": "1.0",
        "timestamp": "1756111889822",
        "hash": "e7ba2ce2353db64735e586dbd96697e3dedf956e2b748df4ecd2cd3cc277c97b",
        "block_index": "16"
      }
    ],
    "total_sent": 10.5,
    "total_received": 2.0,
    "balance": -8.5
  },
  "code": "MSG_0083",
  "httpStatus": "OK",
  "description": "Address transactions retrieved successfully"
}
```

## 18. Mining Status

Returns current mining metrics and status information.

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/mining/status' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "data": {
    "hashRate": 0,
    "difficulty": 4,
    "currentTarget": "0000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
    "nonceAttempts": 0,
    "inProgress": false,
    "lastBlock": {
      "index": 18,
      "hash": "8c96edf4f1e407cd3aceeba66778fe7675e4066b63992568a3b1ca6297fa75d6",
      "timestamp": 1756119729276,
      "transactions_count": 1
    }
  },
  "code": "MSG_0070",
  "httpStatus": "OK",
  "description": "Mining status retrieved successfully"
}
```

## Testing the API

Here's a sequence of commands to test the basic flow:

1. **Create a transaction**:
   ```bash
   curl -X 'POST' \
     'http://127.0.0.1:8000/transactions' \
     -H 'accept: application/json' \
     -H 'Content-Type: application/json' \
     -d '{
       "sender": "0xabc123456789",
       "recipient": "0xdef987654321",
       "amount": 10.5,
       "signature": "signed_payload_hex_or_base64",
       "timestamp": 1712345678901
     }'
   ```

2. **Mine a block**:
   ```bash
   curl -X 'GET' 'http://127.0.0.1:8000/mine'
   ```

3. **View the blockchain**:
   ```bash
   curl -X 'GET' 'http://127.0.0.1:8000/chain'
   ```

4. **Register a peer node** (if you have another instance running):
   ```bash
   curl -X 'POST' 'http://127.0.0.1:8000/nodes/register' -H 'Content-Type: application/json' -d '{"nodes":["http://127.0.0.1:8002"]}'
   ```

5. **Resolve conflicts** (if you have multiple nodes):
   ```bash
   curl -X 'GET' 'http://127.0.0.1:8000/nodes/resolve'
   ```

## Multiple Node Setup

To test the full functionality with multiple nodes, you'll need to:

1. Start the first node (already running on port 8000)
2. Start additional nodes on different ports (e.g., 8002, 8003)
3. Register the nodes with each other
4. Mine blocks on different nodes
5. Use the consensus algorithm to resolve any conflicts
