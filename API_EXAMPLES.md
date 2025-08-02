# ChainLite API Examples

This document provides cURL commands to interact with the ChainLite API. The server should be running on `http://127.0.0.1:8000`.

## 1. View Available Endpoints

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/' \
  -H 'accept: application/json'
```

## 2. Create a New Transaction

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/transactions' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "sender": "Alice",
  "recipient": "Bob",
  "amount": 10.5
}'
```

## 3. Mine a New Block

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/mine' \
  -H 'accept: application/json'
```

## 4. View the Full Blockchain

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/chain' \
  -H 'accept: application/json'
```

## 5. Register New Nodes

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

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/nodes/resolve' \
  -H 'accept: application/json'
```

## Testing the API

Here's a sequence of commands to test the basic flow:

1. **Create a transaction**:
   ```bash
   curl -X 'POST' 'http://127.0.0.1:8000/transaction' -H 'Content-Type: application/json' -d '{"sender":"Alice","recipient":"Bob","amount":10.5}'
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
