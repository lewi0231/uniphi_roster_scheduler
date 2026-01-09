#!/bin/bash
# Deployment script for Fly.io

set -e

echo "🚀 Deploying to Fly.io..."

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl not found. Install it from: https://fly.io/docs/getting-started/installing-flyctl/"
    exit 1
fi

# Login check
if ! flyctl auth whoami &> /dev/null; then
    echo "🔐 Please login to Fly.io..."
    flyctl auth login
fi

# Create app if it doesn't exist
if ! flyctl apps list | grep -q "roster-scheduler"; then
    echo "📦 Creating new Fly.io app..."
    flyctl apps create roster-scheduler
fi

# Deploy
echo "📤 Deploying application..."
flyctl deploy

echo "✅ Deployment complete!"
echo "🌐 Your app should be available at: https://roster-scheduler.fly.dev"

