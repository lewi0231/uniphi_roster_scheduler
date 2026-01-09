# Roster Scheduler

A constraint-based rostering system for car yard scheduling using OR-Tools CP-SAT solver.

## 🐳 Docker Deployment (Recommended for End Users)

The easiest way to run this application is with Docker Compose. This packages both the backend API and frontend interface into containers that run locally on your PC.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed on your PC
- At least 2GB of available RAM (solver can be memory-intensive)

### Quick Start

1. **Clone or download this repository**

2. **Run with Docker Compose:**

   **Mac/Linux:**

   ```bash
   ./start.sh
   # OR
   docker-compose up --build
   ```

   **Windows:**

   ```batch
   run.bat
   # OR
   docker-compose up --build
   ```

3. **Access the application:**

   - Frontend: http://localhost:3333
   - Backend API: http://localhost:8888
   - API Documentation: http://localhost:8888/docs

4. **Stop the containers:**
   ```bash
   docker-compose down
   ```

### Sharing with Others

To share this application with colleagues, see **[DISTRIBUTION.md](DISTRIBUTION.md)** for detailed instructions.

### Docker Configuration

- **Backend**: Runs on port 8888 (internal: `http://backend:8888`)
- **Frontend**: Runs on port 3333 (mapped from container port 3000)
- **Health checks**: Automatically configured
- **Environment variables**: Can be set in `docker-compose.yml` or `.env` file

### Environment Variables (Optional)

Create a `.env` file in the root directory:

```env
LOG_LEVEL=INFO
SOLVER_TIMEOUT_SECONDS=120.0
SOLVER_NUM_WORKERS=4
ENVIRONMENT=docker
```

### Advantages of Docker Deployment

✅ **No network reliability issues** - Everything runs locally  
✅ **No timeouts** - 2+ minute solver runs won't hit network limits  
✅ **Data privacy** - All employee/yard data stays on your PC  
✅ **Easy distribution** - Share a single `docker-compose.yml` file  
✅ **Works anywhere** - Same behavior on Windows/Mac/Linux

---

## 🔧 Development Setup

### Installation

```bash
pip install -r requirements.txt
```

### Testing

```bash
pytest -s tests/
```

### Run Server (Development)

```bash
# Activate virtual environment
source venv/bin/activate

# Run with auto-reload
uvicorn src.scheduler.rostering_api:api --host 0.0.0.0 --port 8888 --reload
```

---

## ☁️ Cloud Deployment

### Fly.io (Recommended for Free Hosting)

Fly.io offers a free tier suitable for CPU-intensive constraint solving workloads.

#### Quick Start

1. **Install Fly CLI:**

   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login:**

   ```bash
   flyctl auth login
   ```

3. **Deploy:**
   ```bash
   flyctl deploy
   ```

#### Configuration

The `fly.toml` file is pre-configured with:

- 2 shared CPUs, 1GB RAM (suitable for CP-SAT solver)
- Environment variables from ConfigMap
- Health check endpoints
- Auto-start/stop disabled for consistent performance

#### Cost

- **Free tier:** 3 shared-cpu VMs (256MB each) OR 1 shared-cpu VM (3GB)
- **Paid:** ~$5-10/month for dedicated CPU (much faster)

### Alternative: Railway

Railway offers $5/month free credit:

1. Connect your GitHub repo
2. Railway auto-detects Dockerfile
3. Set environment variables in Railway dashboard
4. Deploy automatically on git push

### Alternative: Google Cloud Run

Pay-per-use after generous free tier:

- 2M requests/month free
- 360K GB-seconds free
- Perfect for variable traffic

---

## 📚 API Documentation

When running the backend, visit:

- **Swagger UI**: http://localhost:8888/docs
- **ReDoc**: http://localhost:8888/redoc

---

## 🏗️ Project Structure

```
roster-scheduler/
├── src/
│   └── scheduler/
│       ├── rostering_api.py    # FastAPI application
│       └── utils.py             # Utility functions
├── frontend/                    # Frontend code (copy your repo here)
│   ├── Dockerfile
│   └── README.md
├── tests/                       # Unit tests
├── docker-compose.yml           # Multi-container orchestration
├── Dockerfile                   # Backend container
└── requirements.txt             # Python dependencies
```
