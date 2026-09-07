# Deployment – MCP Server Builder Production Deployment Guide

Complete guide for deploying MCP Server Builder to production environments.

## Pre-Deployment Checklist

- [ ] All tests passing: `pytest --cov=app`
- [ ] Security audit complete
- [ ] Environment variables configured
- [ ] Dependencies pinned to exact versions
- [ ] Code reviewed and merged to main
- [ ] Version updated in `app/__version__.py`
- [ ] CHANGELOG.md updated
- [ ] README updated if needed
- [ ] Monitoring and logging configured
- [ ] Backup strategy in place

## Environment Setup

### Production Environment Variables

```bash
# Core Configuration
export OPENAI_API_KEY=sk-your-production-key
export OPENAI_MODEL=gpt-4-turbo-preview
export DEBUG=false

# Security
export REQUEST_TIMEOUT=30
export MAX_RESPONSE_SIZE=10485760
export MAX_DISCOVERY_PAGES=10

# CORS (restrict to your domain)
export CORS_ORIGINS=https://yourapp.com,https://www.yourapp.com

# Logging
export LOG_LEVEL=INFO
export LOG_FILE=/var/log/mcp-server-builder/app.log

# Server
export HOST=0.0.0.0
export PORT=8000
export WORKERS=4
```

### Never Use `.env` Files in Production

```bash
# WRONG
docker run -it --env-file .env myapp  # .env has secrets!

# CORRECT
# Use cloud provider's secret management:
# - AWS Secrets Manager
# - Google Cloud Secret Manager
# - Azure Key Vault
# - HashiCorp Vault
# - Kubernetes Secrets (if using K8s)
```

## Deployment Options

### Option 1: Standalone Server (Linux/macOS)

**Best for**: Small to medium deployments, single server

#### Install

```bash
# SSH into server
ssh user@your-server.com

# Clone repository
git clone https://github.com/marsaempower/mcp-server-builder.git
cd mcp-server-builder

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Create .env (never commit this)
touch .env
chmod 600 .env
# Edit with secrets
```

#### Run with Gunicorn

```bash
# Test locally first
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000

# In production (with systemd)
sudo vi /etc/systemd/system/mcp-builder.service
```

**Systemd Service File**:

```ini
[Unit]
Description=MCP Server Builder
After=network.target

[Service]
Type=notify
User=mcp
WorkingDirectory=/home/mcp/mcp-server-builder
Environment="PATH=/home/mcp/mcp-server-builder/venv/bin"
EnvironmentFile=/home/mcp/mcp-server-builder/.env
ExecStart=/home/mcp/mcp-server-builder/venv/bin/gunicorn \
    app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --access-logfile /var/log/mcp-builder/access.log \
    --error-logfile /var/log/mcp-builder/error.log

Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**Start Service**:

```bash
# Enable and start
sudo systemctl enable mcp-builder
sudo systemctl start mcp-builder

# Check status
sudo systemctl status mcp-builder

# View logs
sudo journalctl -u mcp-builder -f
```

### Option 2: Docker Deployment

**Best for**: Container-based infrastructure, Kubernetes, cloud platforms

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application
COPY app/ ./app/
COPY index.html static/ ./

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
EXPOSE 8000
CMD ["gunicorn", \
     "app.main:app", \
     "--workers=4", \
     "--worker-class=uvicorn.workers.UvicornWorker", \
     "--bind=0.0.0.0:8000", \
     "--timeout=120", \
     "--access-logfile=-", \
     "--error-logfile=-"]
```

**Build and Run**:

```bash
# Build image
docker build -t mcp-server-builder:latest .

# Run container
docker run -d \
  --name mcp-builder \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e DEBUG=false \
  -e CORS_ORIGINS=https://yourapp.com \
  -v /var/log/mcp-builder:/var/log/mcp-builder \
  mcp-server-builder:latest

# View logs
docker logs -f mcp-builder

# Stop container
docker stop mcp-builder
```

#### Docker Compose

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      DEBUG: "false"
      CORS_ORIGINS: "https://yourapp.com"
      LOG_LEVEL: "INFO"
    volumes:
      - ./app/data:/app/app/data
      - logs:/var/log/mcp-builder
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - web
    restart: unless-stopped

volumes:
  logs:
```

### Option 3: Cloud Platforms

#### Heroku

```bash
# Install Heroku CLI
brew tap heroku/brew && brew install heroku

# Login
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set OPENAI_API_KEY=sk-...
heroku config:set DEBUG=false

# Deploy
git push heroku main

# View logs
heroku logs -t
```

**Procfile** (for Heroku):

```
web: gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --workers 4
```

#### AWS (EC2 + Load Balancer)

```bash
# Create EC2 instance
# - Ubuntu 22.04 LTS
# - t3.medium or larger
# - Security group: allow 80, 443, 22

# SSH and setup (see Option 1)

# Use Application Load Balancer
# - Target: EC2 instance
# - Port: 8000
# - Health check: /health
# - SSL/TLS certificate from ACM
```

#### Google Cloud (Cloud Run)

```bash
# Ensure requirements.txt is up-to-date

# Deploy
gcloud run deploy mcp-builder \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=sk-...
```

## Reverse Proxy Configuration

### Nginx

```nginx
upstream mcp_builder {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourapp.com www.yourapp.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourapp.com www.yourapp.com;
    
    # SSL configuration
    ssl_certificate /etc/ssl/certs/yourapp.com.crt;
    ssl_certificate_key /etc/ssl/private/yourapp.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;
    
    # Proxy configuration
    location / {
        proxy_pass http://mcp_builder;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files
    location /static/ {
        alias /home/mcp/mcp-server-builder/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Apache

```apache
<VirtualHost *:443>
    ServerName yourapp.com
    ServerAlias www.yourapp.com
    
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/yourapp.com.crt
    SSLCertificateKeyFile /etc/ssl/private/yourapp.com.key
    
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
    
    <Directory /var/www/static>
        Options -Indexes
        Require all granted
        ExpiresActive On
        ExpiresDefault "access plus 7 days"
    </Directory>
</VirtualHost>

<VirtualHost *:80>
    ServerName yourapp.com
    ServerAlias www.yourapp.com
    Redirect permanent / https://yourapp.com/
</VirtualHost>
```

## Monitoring & Logging

### Application Logging

**Configure Python logging** in `app/main.py`:

```python
import logging
import logging.handlers

# Create logger
logger = logging.getLogger("mcp_builder")
logger.setLevel(logging.DEBUG)

# File handler
file_handler = logging.handlers.RotatingFileHandler(
    "/var/log/mcp-builder/app.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=10
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))

logger.addHandler(file_handler)
logger.addHandler(console_handler)
```

### Health Check Endpoint

```python
# app/main.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat()
    }
```

**Monitor with curl**:

```bash
curl https://yourapp.com/health
```

### Monitoring Tools

#### Prometheus

```python
# app/main.py
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('request_duration_seconds', 'Request duration')

@app.middleware("http")
async def add_metrics(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    request_count.labels(method=request.method, endpoint=request.url.path).inc()
    request_duration.observe(duration)
    return response

@app.get("/metrics")
async def metrics():
    return generate_latest()
```

#### Datadog

```python
# Monitor with Datadog agent
# Install: https://docs.datadoghq.com/agent/

# In app/main.py
from ddtrace import patch_all
patch_all()

from ddtrace import tracer
with tracer.trace("discover_api"):
    result = await discover_api(url)
```

### Log Aggregation (ELK Stack, Splunk, etc.)

Configure log forwarding:

```bash
# With Filebeat
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/mcp-builder/app.log
  fields:
    application: mcp-builder
    environment: production

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

## Database (Future)

When scaling beyond 10,000 projects, migrate to PostgreSQL:

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    source_url TEXT NOT NULL,
    source_api_name VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    status VARCHAR(50),
    tool_count INTEGER,
    error_message TEXT,
    INDEX idx_created (created_at),
    INDEX idx_status (status)
);

CREATE TABLE project_files (
    id BIGSERIAL PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    path VARCHAR(255),
    content LONGTEXT,
    file_type VARCHAR(50)
);
```

## Backup Strategy

### Project Data Backup

```bash
# Daily backup of generated projects
0 2 * * * tar -czf /backups/mcp-builder-$(date +\%Y\%m\%d).tar.gz /home/mcp/mcp-server-builder/app/data/

# Keep 30 days of backups
find /backups -name "mcp-builder-*.tar.gz" -mtime +30 -delete

# Upload to S3
0 3 * * * aws s3 cp /backups/mcp-builder-$(date +\%Y\%m\%d).tar.gz s3://my-backup-bucket/mcp-builder/
```

### Database Backup (Future)

```bash
# PostgreSQL backup
PGPASSWORD=$DB_PASSWORD pg_dump -h localhost -U mcp_user mcp_db | \
  gzip > /backups/db-$(date +\%Y\%m\%d).sql.gz

# Restore from backup
gunzip /backups/db-2024-01-01.sql.gz -c | \
  PGPASSWORD=$DB_PASSWORD psql -h localhost -U mcp_user mcp_db
```

## Scaling Strategy

### Phase 1: Single Server (Current)
- Uvicorn + Gunicorn
- JSON file storage
- Direct HTTP requests
- Suitable for: < 100 concurrent users

### Phase 2: Multiple Workers
- Load balancer (nginx, HAProxy)
- Multiple Gunicorn workers
- Shared storage (NFS)
- Suitable for: 100-1000 concurrent users

### Phase 3: Database + Caching
- PostgreSQL for projects
- Redis for caching
- Message queue (Celery)
- Suitable for: 1000+ concurrent users

### Phase 4: Distributed
- Kubernetes cluster
- Auto-scaling
- CDN for static files
- Suitable for: 10000+ concurrent users

## Security Checklist

- [ ] HTTPS enforced (with valid certificate)
- [ ] Environment variables (not .env files)
- [ ] API keys never logged
- [ ] CORS properly configured (not `*`)
- [ ] Rate limiting enabled
- [ ] Security headers set (HSTS, X-Frame-Options, etc.)
- [ ] WAF (Web Application Firewall) enabled
- [ ] Regular security updates
- [ ] Monitoring alerts configured
- [ ] Backup strategy in place

## Troubleshooting

### High Memory Usage

```bash
# Check process
ps aux | grep gunicorn

# Reduce workers if needed
--workers 2  # Instead of 4

# Monitor with top
top -p $(pgrep -f gunicorn | head -1)
```

### Slow Requests

```bash
# Check logs
tail -f /var/log/mcp-builder/app.log

# Look for slow OpenAI API calls
# Increase timeout if needed
--timeout 180  # 3 minutes

# Add caching to discovery
```

### Out of Disk Space

```bash
# Check disk usage
du -sh /home/mcp/mcp-server-builder/app/data

# Remove old projects
find /home/mcp/mcp-server-builder/app/data -name "*.json" -mtime +90 -delete
```

## Rollback Procedure

```bash
# If deployment goes wrong:

# 1. Identify last working version
git log --oneline | head -5

# 2. Checkout previous version
git checkout v0.1.0

# 3. Reinstall dependencies (if needed)
pip install -r requirements.txt

# 4. Restart service
sudo systemctl restart mcp-builder

# 5. Verify
curl https://yourapp.com/health
```

---

**Last Updated**: 2024-01-01
