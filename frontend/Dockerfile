# Use Node.js alpine as base image instead of plain alpine
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package.json and pnpm-lock.yaml first to leverage Docker caching
COPY package.json pnpm-lock.yaml* ./

# Install dependencies using pnpm
RUN pnpm install --frozen-lockfile

# Approve build scripts for trusted packages
RUN pnpm approve-builds @tailwindcss/oxide sharp unrs-resolver

# Copy the rest of the application code
COPY . .

# Set build-time arguments for environment configuration
ARG NODE_ENV=production
ARG NEXT_PUBLIC_APP_ENV=production
ARG NEXT_PUBLIC_APP_URL
ARG NEXT_PUBLIC_ANALYTICS_ENABLED=false
ARG NEXT_PUBLIC_ENABLE_DEBUG_MODE=false
ARG NEXT_PUBLIC_ENABLE_CONSOLE_LOGS=false

# Set environment variables for build
ENV NODE_ENV=$NODE_ENV
ENV NEXT_PUBLIC_APP_ENV=$NEXT_PUBLIC_APP_ENV
ENV NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL
ENV NEXT_PUBLIC_ANALYTICS_ENABLED=$NEXT_PUBLIC_ANALYTICS_ENABLED
ENV NEXT_PUBLIC_ENABLE_DEBUG_MODE=$NEXT_PUBLIC_ENABLE_DEBUG_MODE
ENV NEXT_PUBLIC_ENABLE_CONSOLE_LOGS=$NEXT_PUBLIC_ENABLE_CONSOLE_LOGS

# Build the Next.js app
RUN pnpm build

# Production image
FROM node:20-alpine AS runner
WORKDIR /app

# Set to production environment
ENV NODE_ENV=production

# Copy built artifacts from builder stage for standalone mode
# The standalone directory contains only the necessary files for production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Run the application
USER node
EXPOSE 3000
CMD ["node", "server.js"]