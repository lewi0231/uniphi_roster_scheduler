#!/bin/bash
# Quick start script for Docker deployment

set -e

echo "🚀 Starting Roster Scheduler with Docker Compose..."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop:"
    echo "   https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Check if docker-compose is available
if ! docker compose version &> /dev/null && ! docker-compose version &> /dev/null; then
    echo "❌ docker-compose is not available. Please ensure Docker Desktop includes Compose."
    exit 1
fi

# Check if frontend directory has content
if [ ! -f "frontend/package.json" ] && [ ! -f "frontend/index.html" ]; then
    echo "⚠️  WARNING: Frontend directory appears empty."
    echo "   Please copy your frontend code into the 'frontend/' directory."
    echo "   See frontend/README.md for instructions."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build and start containers
echo "📦 Building and starting containers..."
if docker compose version &> /dev/null; then
    docker compose up --build
else
    docker-compose up --build
fi
