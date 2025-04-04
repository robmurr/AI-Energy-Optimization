# CPU TDP Finder API (Client + Backend)

This project lets you detect your CPU's name and retrieve its TDP (Thermal Design Power) using a remote backend server. The backend stores known values in MongoDB and uses OpenAI to query unknown CPUs. It's self-hosted and works even over the internet.

---

## Client Setup

### Requirements

- Python 3.11+
- `py-cpuinfo`
- `requests`

### Install Requirements

```bash
pip install py-cpuinfo requests
```

### Run the Client

```bash
python3 cputdp.py
```

This script will:
1. Detect your CPU name using `py-cpuinfo`
2. Send a request to `http://fennecs.duckdns.org:5000/get-tdp`
3. Receive and print the TDP (in Watts) from the backend

---

## Backend Overview

The backend is a Flask API hosted in Docker. It:
1. Accepts POST requests with a CPU name
2. Checks a local MongoDB instance to see if the TDP is already known
3. If not, queries the OpenAI API for the TDP
4. Saves the result in MongoDB for next time

---

## Backend Deployment (Docker)

### Project Structure

```
cputdp/
├── docker-compose.yml
└── app/
    ├── Dockerfile
    ├── main.py
    ├── requirements.txt
    └── .env
```

### `.env`

```
OPENAI_API_KEY=your_openai_key_here
```

> This is used by the backend to call OpenAI when a CPU TDP is unknown.

---

###  Docker Compose Setup

#### `docker-compose.yml`

```yaml
version: '3.8'

services:
  mongo:
    image: mongo
    container_name: tdp_mongo
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db

  backend:
    build: ./app
    container_name: tdp_backend
    ports:
      - "5000:5000"
    env_file:
      - ./app/.env
    depends_on:
      - mongo
    restart: always

volumes:
  mongo-data:
```

#### `app/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

#### `app/requirements.txt`

```
Flask
pymongo
python-dotenv
openai
```

#### `app/main.py`

```python
from flask import Flask, request, jsonify
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

client = MongoClient("mongodb://mongo:27017/")
db = client["cputdp"]
collection = db["tdps"]

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def fetch_tdp(cpu_name):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Return only the TDP (number in watts) for the CPU given."},
                {"role": "user", "content": cpu_name}
            ]
        )
        tdp = int(response.choices[0].message.content.strip().split()[0])
        return tdp
    except:
        return -1

@app.route("/get-tdp", methods=["POST"])
def get_tdp():
    data = request.get_json()
    cpu_name = data.get("cpu_name", "")

    existing = collection.find_one({"cpu_name": cpu_name})
    if existing:
        return jsonify({"tdp": existing["tdp"]}), 200

    tdp = fetch_tdp(cpu_name)
    if tdp == -1:
        return jsonify({"error": "TDP not found"}), 404

    collection.insert_one({"cpu_name": cpu_name, "tdp": tdp})
    return jsonify({"tdp": tdp}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

---

## Port Forwarding

To allow public access, forward these ports on your router:

| Port | Protocol | Forward To          | Purpose         |
|------|----------|---------------------|-----------------|
| 5000 | TCP      | 192.168.x.x:5000    | Flask API       |
| 27017 | TCP     | 192.168.x.x:27017   | MongoDB (optional for Compass) |

---

## Security Note

The client communicates over HTTP, which is fine for non-sensitive data like TDP lookups. If you plan to send anything sensitive, use HTTPS with a reverse proxy like Nginx + Certbot.

---

## Example Output

```bash
Detected CPU: Apple M1
TDP: 10W
```

---