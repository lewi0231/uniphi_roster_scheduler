# Environment Setup Guide

This document explains how to set up and configure the Work Rate Calculator for different environments.

## Environment Configuration

The application supports three environments:

- **Development**: Local development with debugging enabled
- **Production**: Optimized for production with debugging disabled
- **Test**: For automated testing

## Environment Variables

### Required Variables

- `NODE_ENV`: The Node.js environment (development/production/test)
- `NEXT_PUBLIC_APP_ENV`: The application environment
- `NEXT_PUBLIC_APP_URL`: The application URL

### Optional Variables

- `NEXT_PUBLIC_ANALYTICS_ENABLED`: Enable analytics (default: false)
- `NEXT_PUBLIC_ANALYTICS_ID`: Analytics ID
- `NEXT_PUBLIC_ENABLE_DEBUG_MODE`: Show debug information (default: true in dev)
- `NEXT_PUBLIC_ENABLE_CONSOLE_LOGS`: Enable console logging (default: true in dev)

## Local Development

### Option 1: Direct Development

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev
```

### Option 2: Docker Development

```bash
# Start development container
pnpm docker:dev

# Stop development container
pnpm docker:dev:down
```

### Option 3: Build Development Image

```bash
# Build development image
pnpm docker:build:dev

# Run development container
docker run -p 3000:3000 work-rate-calculator:dev
```

## Production Build

### GitHub Actions (Automated)

The GitHub Actions workflow automatically builds production images with:

- Environment: `production`
- Debug mode: `disabled`
- Console logs: `disabled`
- Analytics: `enabled`

### Manual Production Build

```bash
# Build production image
pnpm docker:build

# Run production container
docker run -p 3000:3000 work-rate-calculator
```

## Environment-Specific Features

### Development Environment

- Hot reloading enabled
- Debug information displayed
- Console logging enabled
- Development optimizations disabled

### Production Environment

- Hot reloading disabled
- Debug information hidden
- Console logging disabled
- Production optimizations enabled
- Analytics enabled (if configured)

## Configuration Files

- `env.example`: Example environment variables
- `lib/config.ts`: Environment configuration utility
- `next.config.mjs`: Next.js configuration with environment support
- `Dockerfile`: Production Docker build
- `Dockerfile.dev`: Development Docker build
- `docker-compose.dev.yml`: Local development setup

## Kubernetes Deployment

The application is deployed to Kubernetes using Flux with:

- **Development**: `clusters/homelab/environments/development/apps/work-rate-calculator/`
- **Production**: `clusters/homelab/environments/production/apps/work-rate-calculator/`

Each environment uses the same image but with different configurations applied at build time.
