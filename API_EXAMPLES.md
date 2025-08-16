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

**Response:** Returns the created transaction object with auto-generated hash.

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

**Response Format:**
```json
{
  "message": "New block forged",
  "index": 2,
  "transactions": [...],
  "nonce": 12345,
  "hash": "000abc123...",
  "previous_hash": "000def456..."
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

**Response Shape:**
```json
{
  "data": {
    "chain": [
      {
        "index": 1,
        "timestamp": 1712345678901,
        "transactions": [...],
        "nonce": 100,
        "previous_hash": null,
        "hash": "0000..."
      }
    ]
  }
}
```

## 5. Register New Nodes

- If body `nodes` is empty or omitted, the server auto-registers itself using its IP and the request port for mobile-friendly access.
- Each node can be provided with or without scheme; it will be normalized internally.
- Successful registrations are broadcast to existing peers.

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

**Response (Chain Replaced):**
```json
{
  "message": "Chain was replaced",
  "chain": [
    {
      "index": 1,
      "timestamp": 1712345678901,
      "transactions": [...],
      "nonce": 100,
      "previous_hash": null,
      "hash": "000..."
    }
  ]
}
```

**Response (Local Chain Authoritative):**
```json
{
  "message": "Local chain is authoritative"
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
    "nodes": ["http://127.0.0.1:8002", "http://127.0.0.1:8003"]
  }
}
```

## 8. Unregister Single Node

Remove a specific node from the network.

```bash
curl -X 'DELETE' \
  'http://127.0.0.1:8000/nodes/127.0.0.1:8002' \
  -H 'accept: application/json'
```

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
  "transactions": [
    {
      "sender": "0xabc123456789",
      "recipient": "0xdef987654321",
      "amount": 10.5,
      "signature": "signed_payload",
      "timestamp": 1712345678901,
      "hash": "abc123..."
    }
  ]
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
  "balance": 25.5
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
        "index": 2,
        "timestamp": 1712345678901,
        "transactions": [...],
        "nonce": 12345,
        "previous_hash": "000def456...",
        "hash": "000abc123..."
      }
    ]
  }
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

**Response:** Same format as latest blocks, returns single block or 404 if not found.

## 14. Get Block by Hash

Retrieve a specific block by its SHA-256 hash.

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/blocks/hash/000abc123456789...' \
  -H 'accept: application/json'
```

**Response:** Returns single block or 404 if hash not found.

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
        "sender": "0xabc123456789",
        "recipient": "0xdef987654321",
        "amount": 10.5,
        "signature": "signed_payload",
        "timestamp": 1712345678901,
        "hash": "abc123...",
        "block_index": 2
      }
    ]
  }
}
```

## 16. Get Transaction by Hash

Search for a transaction by its SHA-256 hash in both pending and confirmed transactions.

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/transactions/abc123456789...' \
  -H 'accept: application/json'
```

**Response:** Returns single transaction object or 404 if not found.

## 17. Get Transactions for Address

Retrieve all transactions where the address is either sender or recipient.

**Path Parameters:**
- `address`: Valid hex address (`^0x[a-fA-F0-9]{6,}$`)

**Query Parameters:**
- `limit` (optional): Number of transactions (1-100, default: 20)
- `before` (optional): Return transactions before this timestamp (epoch ms)

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/address/0xabc123456789/transactions?limit=15&before=1712345678901' \
  -H 'accept: application/json'
```

**Response:** Same format as latest transactions, filtered by address.

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
  "hashRate": 0,
  "difficulty": 4,
  "currentTarget": "0000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
  "nonceAttempts": 0,
  "inProgress": false,
  "lastBlock": {
    "index": 2,
    "hash": "000abc123...",
    "timestamp": 1712345678901
  }
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
