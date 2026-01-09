# Distribution Guide

This guide explains how to share the Roster Scheduler application with others.

## Option 1: Share Git Repository (Recommended)

This is the simplest and most maintainable approach.

### For You (Developer):
1. **Push to a Git repository** (GitHub, GitLab, etc.):
   ```bash
   git add .
   git commit -m "Add Docker setup and frontend integration"
   git push origin main
   ```

2. **Share the repository URL** with your colleague

### For Your Colleague:
1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd roster-scheduler
   ```

2. **Install Docker Desktop** (if not already installed):
   - Download from: https://www.docker.com/products/docker-desktop/
   - Install and start Docker Desktop

3. **Build and run**:
   ```bash
   docker-compose up --build
   ```

4. **Access the application**:
   - Frontend: http://localhost:3333
   - Backend API: http://localhost:8888
   - API Docs: http://localhost:8888/docs

5. **Stop when done**:
   ```bash
   docker-compose down
   ```

---

## Option 2: Export Docker Images (For Offline/Private Sharing)

If you prefer to share pre-built images without code:

### For You (Developer):
1. **Build the images**:
   ```bash
   docker-compose build
   ```

2. **Export both images**:
   ```bash
   docker save roster-scheduler-backend:latest | gzip > roster-scheduler-backend.tar.gz
   docker save roster-scheduler-frontend:latest | gzip > roster-scheduler-frontend.tar.gz
   ```
   
   Or export the images with their tags:
   ```bash
   docker images | grep roster-scheduler
   # Note the image names, then:
   docker save <image-name> | gzip > roster-scheduler-backend.tar.gz
   docker save <image-name> | gzip > roster-scheduler-frontend.tar.gz
   ```

3. **Share the .tar.gz files** (via USB, cloud storage, etc.)

### For Your Colleague:
1. **Install Docker Desktop** (if not already installed)

2. **Load the images**:
   ```bash
   gunzip -c roster-scheduler-backend.tar.gz | docker load
   gunzip -c roster-scheduler-frontend.tar.gz | docker load
   ```

3. **Create docker-compose.yml** (if not provided) and run:
   ```bash
   docker-compose up
   ```

---

## Option 3: Docker Hub / Registry (For Easy Updates)

For professional distribution with easy updates:

### For You (Developer):
1. **Create Docker Hub account** (if you don't have one): https://hub.docker.com

2. **Tag your images**:
   ```bash
   docker tag roster-scheduler-backend:latest yourusername/roster-scheduler-backend:latest
   docker tag roster-scheduler-frontend:latest yourusername/roster-scheduler-frontend:latest
   ```

3. **Push to Docker Hub**:
   ```bash
   docker login
   docker push yourusername/roster-scheduler-backend:latest
   docker push yourusername/roster-scheduler-frontend:latest
   ```

4. **Update docker-compose.yml** to use your registry:
   ```yaml
   services:
     backend:
       image: yourusername/roster-scheduler-backend:latest
       # ... rest of config
     frontend:
       image: yourusername/roster-scheduler-frontend:latest
       # ... rest of config
   ```

### For Your Colleague:
1. **Create docker-compose.yml** with your registry images

2. **Pull and run**:
   ```bash
   docker-compose pull
   docker-compose up
   ```

---

## Quick Start Script

You can also create a simple script for your colleague to run:

### Create `run.sh`:
```bash
#!/bin/bash
echo "🚀 Starting Roster Scheduler..."
docker-compose up --build
```

### Create `run.bat` (for Windows):
```batch
@echo off
echo Starting Roster Scheduler...
docker-compose up --build
```

---

## Requirements for Your Colleague

- **Docker Desktop** installed and running
- **At least 2GB free RAM** (solver can be memory-intensive)
- **Internet connection** (for pulling base images on first run)

---

## Troubleshooting

### "Port already in use" error
- Change ports in `docker-compose.yml` if 3333 or 8888 are in use
- Update `ports` section: `- "3334:3000"` for frontend, `- "8889:8888"` for backend

### "Permission denied" errors (Linux)
- Add user to docker group: `sudo usermod -aG docker $USER`
- Log out and back in

### Slow first build
- This is normal - images need to be downloaded and built
- Subsequent builds will be faster due to caching
