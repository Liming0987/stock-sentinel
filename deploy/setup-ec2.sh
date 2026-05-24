#!/bin/bash
# Run this script ON the EC2 instance after SSH-ing in.
# It sets up the production environment.
#
# Usage: bash setup-ec2.sh

set -e

APP_DIR="/home/ec2-user/stock-sentinel"
AWS_REGION="us-east-1"
ACCOUNT_ID="178801185941"

echo "=== Setting up EC2 for Stock Sentinel ==="

# Wait for Docker to be ready
while ! docker info > /dev/null 2>&1; do
  echo "Waiting for Docker..."
  sleep 2
done

# Create app directory
mkdir -p $APP_DIR/nginx
cd $APP_DIR

# Create docker-compose.yml (production)
cat > docker-compose.yml << 'COMPOSE'
version: "3.9"

services:
  db:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: stock_sentinel
      POSTGRES_USER: sentinel
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sentinel"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    image: 178801185941.dkr.ecr.us-east-1.amazonaws.com/stock-sentinel-backend:latest
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://sentinel:${DB_PASSWORD}@db:5432/stock_sentinel
      REDIS_URL: redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  worker:
    image: 178801185941.dkr.ecr.us-east-1.amazonaws.com/stock-sentinel-backend:latest
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://sentinel:${DB_PASSWORD}@db:5432/stock_sentinel
      REDIS_URL: redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
    restart: unless-stopped

  beat:
    image: 178801185941.dkr.ecr.us-east-1.amazonaws.com/stock-sentinel-backend:latest
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://sentinel:${DB_PASSWORD}@db:5432/stock_sentinel
      REDIS_URL: redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: celery -A app.workers.celery_app beat --loglevel=info
    restart: unless-stopped

  frontend:
    image: 178801185941.dkr.ecr.us-east-1.amazonaws.com/stock-sentinel-frontend:latest
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  pgdata:
COMPOSE

# Create nginx config
cat > nginx/nginx.conf << 'NGINX'
events {
    worker_connections 1024;
}

http {
    upstream frontend {
        server frontend:3000;
    }

    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name _;

        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /docs {
            proxy_pass http://backend;
            proxy_set_header Host $host;
        }

        location /openapi.json {
            proxy_pass http://backend;
            proxy_set_header Host $host;
        }

        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
NGINX

# Create .env file (user should edit this)
if [ ! -f .env ]; then
cat > .env << 'ENV'
# Database
DB_PASSWORD=change_this_to_a_strong_password

# Reddit API
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=stock-sentinel/1.0

# Market Data
FINNHUB_API_KEY=

# Auth
JWT_SECRET=change_this_to_a_random_string_at_least_32_chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Frontend
FRONTEND_URL=http://localhost
ENV
echo "Created .env file - EDIT THIS with your secrets!"
fi

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo ""
echo "========================================="
echo "  EC2 SETUP COMPLETE"
echo "========================================="
echo ""
echo "1. Edit .env with your secrets:"
echo "   nano /home/ec2-user/stock-sentinel/.env"
echo ""
echo "2. Start the app:"
echo "   cd /home/ec2-user/stock-sentinel"
echo "   docker compose up -d"
echo ""
echo "3. Future deployments will happen automatically via GitHub Actions!"
echo "========================================="
