# Quick Start Guide for Users

This guide is for colleagues/users who want to run the Roster Scheduler on their PC.

## Prerequisites

1. **Install Docker Desktop**

   - Download from: https://www.docker.com/products/docker-desktop/
   - Install and start Docker Desktop
   - Wait for Docker to fully start (green icon in system tray/menu bar)

2. **Verify Docker is running**
   - Open terminal/command prompt
   - Run: `docker --version`
   - You should see Docker version information

## Installation Steps

### Option A: Using Git (Recommended)

1. **Get the code:**

   ```bash
   git clone <repository-url>
   cd roster-scheduler
   ```

2. **Run the application:**

   **Mac/Linux:**

   ```bash
   ./start.sh
   ```

   **Windows:**

   ```batch
   run.bat
   ```

   Or manually:

   ```bash
   docker-compose up --build
   ```

3. **Wait for build to complete** (first time may take 5-10 minutes)

4. **Access the application:**
   - Open browser: http://localhost:3333
   - The scheduler interface should load

### Option B: Using Pre-built Images

If you received `.tar.gz` files:

1. **Extract and load images:**

   ```bash
   gunzip -c roster-scheduler-backend.tar.gz | docker load
   gunzip -c roster-scheduler-frontend.tar.gz | docker load
   ```

2. **Get the docker-compose.yml file** (should be provided separately)

3. **Run:**
   ```bash
   docker-compose up
   ```

## Using the Application

1. **Open in browser:** http://localhost:3333

2. **Configure settings:**

   - Max Shift Length (hours)
   - Base Start Time
   - Max Position Radius
   - Radius Constraint Mode

3. **Add employees** with their availability

4. **Add car yards** with requirements

5. **Click "Generate Roster"**

6. **Review results** in the roster display

## Stopping the Application

Press `Ctrl+C` in the terminal where Docker is running, or:

```bash
docker-compose down
```

## Troubleshooting

### "Port already in use"

- Another application is using port 3333 or 8888
- Change ports in `docker-compose.yml` if needed

### "Cannot connect to Docker daemon"

- Make sure Docker Desktop is running
- Restart Docker Desktop if needed

### "Out of memory" or "ResourceExhausted: cannot allocate memory" errors

**This is the most common issue on Windows!**

**Fix: Increase Docker Desktop Memory**

1. **Open Docker Desktop**

   - Right-click Docker icon in system tray (bottom-right)
   - Click "Settings"

2. **Go to Resources**

   - Click "Resources" in left sidebar
   - Click "Advanced" tab

3. **Increase Memory**

   - Move "Memory" slider to **at least 4GB** (4096 MB)
   - **Recommended: 6-8GB** if your PC has enough RAM
   - Click "Apply & Restart"

4. **Wait for Docker to restart** (1-2 minutes)

5. **Close other applications** to free up RAM

6. **Try building again:**
   ```bash
   docker-compose up --build
   ```

**If still failing:**

- Build services one at a time:
  ```bash
  docker-compose build backend
  docker-compose build frontend
  docker-compose up
  ```

See **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** for more details.

### Slow performance

- First run includes downloading images (only happens once)
- Subsequent runs are faster
- Ensure Docker Desktop has enough RAM allocated (recommended: 4GB+)

## Getting Help

If you encounter issues:

1. Check Docker Desktop is running
2. Verify you're using the correct ports
3. Check the terminal output for error messages
4. Contact the developer with error logs
