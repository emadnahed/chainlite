# 🚀 ChainLite — A Minimal Blockchain API in Python

ChainLite is a lightweight, modular blockchain implementation built using **Python + FastAPI**. It demonstrates how blockchain fundamentals like proof-of-work, transactions, mining, and network consensus can be implemented and exposed via a RESTful API.

> 🎯 Ideal for developers seeking to understand blockchain internals, build blockchain-based apps, or showcase backend architecture skills.

---

## 📌 Features

- 🧱 Custom-built blockchain structure (blocks, chain, PoW)
- 🔐 Transaction handling and hashing (SHA-256)
- ⛏️ Mining endpoint with basic Proof-of-Work algorithm
- 🔗 Peer-to-peer node registration & chain consensus
- 🧪 Integrated testing with `pytest`
- 📦 Dockerized and ready to deploy
- 📚 Interactive API docs via Swagger UI (thanks to FastAPI)

---

## 🚀 Live Demo

🔗 [COMING SOON]

---

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI
- **Hashing:** SHA-256 (`hashlib`)
- **Data Persistence:** In-memory (optional JSON/DB can be added)
- **Networking:** REST (HTTP APIs between nodes)
- **Others:** `uvicorn`, `requests`, `pydantic`, `pytest`, `docker`

---

## 📦 API Endpoints

| Method | Endpoint              | Description                             |
|--------|-----------------------|-----------------------------------------|
| `POST` | `/transaction`        | Submit a new transaction to the pool    |
| `POST` | `/mine`               | Mine a new block and add to the chain   |
| `GET`  | `/chain`              | Retrieve the full blockchain            |
| `POST` | `/nodes/register`     | Register new peer nodes                 |
| `GET`  | `/nodes/resolve`      | Trigger consensus algorithm             |

📚 Swagger UI available at: `http://localhost:8000/docs`

---

## 🧱 Blockchain Overview

Each block contains:
- `index`: Block position in chain
- `timestamp`: Time of creation
- `transactions`: List of transactions
- `proof`: Nonce satisfying PoW
- `previous_hash`: SHA-256 hash of the previous block

---

## 🔧 Getting Started


### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
uvicorn app.main:app --reload
```

### 4. Test endpoints

Visit: `http://127.0.0.1:8000/docs`

---

## 🧪 Run Tests

```bash
pytest
```

---

## 🐳 Run with Docker

Build and run the API only:
```bash
docker build -t chainlite .
docker run --env MONGODB_URI='mongodb://host.docker.internal:27017/chainlite' -p 8000:8000 chainlite
```

Or run the full stack (API + MongoDB) with Docker Compose:
```bash
cp .env.example .env  # prepare non-secret defaults for Compose
docker compose up --build
```
- API: http://localhost:8000
- MongoDB: accessible inside the network as mongo:27017

Security note:
- .env is in .gitignore. Never commit secrets.
- For production, inject secrets via your CI/CD, Docker secrets, or platform env vars.

To stop and clean up:
```bash
docker compose down
```

---

## 🌐 Peer-to-Peer Setup

To simulate multiple nodes:

1. Run the app on different ports (e.g., 8000, 8001, 8002)
2. Register nodes using:

```bash
POST /nodes/register
{
  "nodes": ["http://localhost:8001", "http://localhost:8002"]
}
```

3. Call `/nodes/resolve` to trigger conflict resolution (longest valid chain wins).

---

## 📁 Project Structure

```
chainlite/
├── app/
│   ├── main.py          # FastAPI app
│   ├── blockchain.py    # Core Blockchain class
│   ├── models.py        # Pydantic request/response models
│   └── utils.py         # Hashing and helper functions
├── tests/
│   └── test_blockchain.py
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## ✨ Future Enhancements

* Add wallet system using RSA key pairs
* Add persistent DB storage (e.g., SQLite or MongoDB)
* Advanced consensus (e.g., Proof of Stake or PBFT)
* Real-time P2P communication (WebSockets or ZeroMQ)

---

## 📜 License

This project is open-source under the [MIT License](LICENSE).

---

## 🙌 Acknowledgments

Inspired by educational blockchain prototypes and enhanced with modern Python practices.

---

## 👋 Contact
Questions or suggestions? Open an issue or pull request!