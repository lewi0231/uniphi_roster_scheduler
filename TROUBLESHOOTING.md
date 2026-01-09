# Troubleshooting Guide

## Memory Issues During Docker Build

### Error: "ResourceExhausted: cannot allocate memory"

This error occurs when Docker Desktop doesn't have enough memory allocated.

### Solution: Increase Docker Desktop Memory

**Windows:**

1. **Open Docker Desktop**

   - Right-click the Docker icon in system tray
   - Click "Settings" or "Preferences"

2. **Go to Resources**

   - Click "Resources" in the left sidebar
   - Click "Advanced" tab

3. **Increase Memory**

   - Move the "Memory" slider to at least **4GB** (4096 MB)
   - Recommended: **6-8GB** if your system has enough RAM
   - Click "Apply & Restart"

4. **Wait for Docker to restart** (may take 1-2 minutes)

5. **Try building again:**
   ```bash
   docker-compose up --build
   ```

**Mac:**

1. **Open Docker Desktop**

   - Click Docker icon in menu bar
   - Click "Settings" or "Preferences"

2. **Go to Resources**

   - Click "Resources" in left sidebar

3. **Increase Memory**
   - Set Memory to at least **4GB** (4096 MB)
   - Recommended: **6-8GB**
   - Click "Apply & Restart"

**Linux:**

Docker on Linux uses system memory directly. Ensure you have at least 4GB free RAM.

### Additional Optimizations

If you still have memory issues:

1. **Close other applications** to free up RAM
2. **Build one service at a time:**
   ```bash
   docker-compose build backend
   docker-compose build frontend
   docker-compose up
   ```
3. **Use Docker BuildKit** (usually enabled by default):
   ```bash
   DOCKER_BUILDKIT=1 docker-compose build
   ```

---

## Port Already in Use

### Error: "port is already allocated" or "address already in use"

**Solution:**

1. **Check what's using the port:**

   ```bash
   # Windows PowerShell
   netstat -ano | findstr :3333
   netstat -ano | findstr :8888

   # Mac/Linux
   lsof -i :3333
   lsof -i :8888
   ```

2. **Change ports in docker-compose.yml:**

   ```yaml
   ports:
     - "3334:3000" # Changed from 3333
     - "8889:8888" # Changed from 8888
   ```

3. **Update frontend environment variable:**
   ```yaml
   - NEXT_PUBLIC_API_URL=http://localhost:8889
   ```

---

## Docker Desktop Not Starting

### Error: "Docker Desktop failed to start"

**Solutions:**

1. **Restart Docker Desktop**

   - Quit Docker Desktop completely
   - Wait 30 seconds
   - Start it again

2. **Check WSL2 (Windows):**

   - Docker Desktop requires WSL2 on Windows
   - Install WSL2: `wsl --install`
   - Restart computer after installation

3. **Check virtualization:**
   - Ensure virtualization is enabled in BIOS
   - Check Windows Features: "Virtual Machine Platform" and "Windows Subsystem for Linux"

---

## Build Takes Too Long

**First build is slow** - this is normal:

- Base images need to be downloaded (hundreds of MB)
- Dependencies need to be installed
- Application needs to be compiled

**Subsequent builds are faster** due to Docker layer caching.

**To speed up:**

- Keep Docker Desktop running between builds
- Don't clear Docker cache unnecessarily

---

## Frontend Build Errors

### Error: "Module not found" or "Cannot find module"

**Solution:**

1. **Ensure frontend code is complete:**

   ```bash
   ls frontend/package.json  # Should exist
   ```

2. **Rebuild frontend:**
   ```bash
   docker-compose build frontend --no-cache
   ```

---

## Backend API Connection Errors

### Error: "Failed to generate roster" or connection refused

**Check:**

1. **Backend is running:**

   ```bash
   docker-compose ps
   ```

   Both `backend` and `frontend` should show "Up"

2. **Backend health check:**

   ```bash
   curl http://localhost:8888/health
   ```

   Should return: `{"status":"healthy"}`

3. **Check logs:**
   ```bash
   docker-compose logs backend
   ```

---

## Permission Errors (Linux/Mac)

### Error: "Permission denied" when running docker commands

**Solution:**

1. **Add user to docker group (Linux):**

   ```bash
   sudo usermod -aG docker $USER
   ```

   Log out and back in for changes to take effect.

2. **Check Docker Desktop permissions (Mac):**
   - System Preferences > Security & Privacy
   - Grant Docker Desktop necessary permissions

---

## Still Having Issues?

1. **Check Docker Desktop logs:**

   - Windows: `%LOCALAPPDATA%\Docker\log.txt`
   - Mac: `~/Library/Containers/com.docker.docker/Data/log/`

2. **Verify Docker is working:**

   ```bash
   docker --version
   docker run hello-world
   ```

3. **Get detailed error output:**

   ```bash
   docker-compose up --build --verbose
   ```

4. **Contact support with:**
   - Full error message
   - Docker Desktop version
   - System RAM available
   - Operating system version
