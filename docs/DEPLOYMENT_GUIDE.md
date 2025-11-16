# RGrid Production Deployment Guide

## Overview

This guide covers deploying RGrid to production with Hetzner Cloud for distributed worker execution.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Control Plane (Hetzner CX22 or dedicated server)                │
│                                                                   │
│  ├─ PostgreSQL Database                                          │
│  ├─ MinIO S3 Storage                                             │
│  ├─ Ray Head Node (port 6380)                                    │
│  ├─ FastAPI Backend (port 8000)                                  │
│  └─ Orchestrator Daemon                                          │
│      ├─ Worker Health Monitor                                    │
│      ├─ Worker Provisioner                                       │
│      └─ Lifecycle Manager                                        │
└───────────────────────────────────────────────────────────────────┘
                            │
                            │ Provisions workers via Hetzner API
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│ Worker Nodes (Hetzner CX22, auto-provisioned)                     │
│                                                                    │
│  ├─ Ray Worker (connects to Ray head on control plane)            │
│  ├─ Docker Engine (runs user containers)                          │
│  └─ Heartbeat Sender (30s interval)                               │
│                                                                    │
│  Auto-scaled based on queue depth (5-10 workers max)              │
│  Auto-terminated on billing hour if idle                          │
│  Auto-replaced if health check fails                              │
└────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. Hetzner Cloud Account

- Sign up at https://hetzner.com/cloud
- Create API token (Read & Write permissions)
- Note down token for deployment

### 2. SSH Key

Generate SSH key for worker access:

```bash
ssh-keygen -t ed25519 -f infra/hetzner_worker.key -C "rgrid-workers"
```

### 3. Domain & SSL (Optional but Recommended)

- Point domain to control plane IP
- Use Let's Encrypt for SSL certificate

## Deployment Steps

### Step 1: Provision Control Plane

#### Option A: Hetzner CX22 Server

```bash
# Create server via Hetzner Cloud Console
# - Server type: CX22 (2 vCPU, 4GB RAM)
# - Location: Nuremberg (nbg1)
# - Image: Ubuntu 22.04
# - Add your SSH key
# - Assign floating IP (recommended)

# SSH into server
ssh root@<control-plane-ip>
```

#### Option B: Existing Server

Any server with:
- Ubuntu 22.04 LTS
- 4GB RAM minimum
- 2 CPU cores
- Public IP address

### Step 2: Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    postgresql-15 \
    docker.io \
    docker-compose \
    git \
    nginx

# Start services
systemctl enable docker postgresql
systemctl start docker postgresql
```

### Step 3: Configure PostgreSQL

```bash
# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE rgrid;
CREATE USER rgrid WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE rgrid TO rgrid;
\q
EOF

# Allow local connections
# Edit /etc/postgresql/15/main/pg_hba.conf
# Add: host rgrid rgrid 127.0.0.1/32 md5

# Restart PostgreSQL
systemctl restart postgresql
```

### Step 4: Deploy MinIO

```bash
# Create MinIO directory
mkdir -p /opt/minio/data

# Run MinIO via Docker
docker run -d \
    --name minio \
    --restart always \
    -p 9000:9000 \
    -p 9001:9001 \
    -v /opt/minio/data:/data \
    -e "MINIO_ROOT_USER=rgrid_admin" \
    -e "MINIO_ROOT_PASSWORD=your_secure_minio_password" \
    minio/minio server /data --console-address ":9001"

# Create bucket
docker exec minio \
    mc alias set local http://localhost:9000 rgrid_admin your_secure_minio_password

docker exec minio \
    mc mb local/rgrid
```

### Step 5: Deploy Ray Head Node

```bash
# Create docker-compose.yml for Ray
cat > /opt/ray-compose.yml <<'EOF'
version: '3.8'
services:
  ray-head:
    image: rayproject/ray:2.8.0-py311
    container_name: ray-head
    command: ray start --head --port=6380 --dashboard-host=0.0.0.0 --dashboard-port=8265 --num-cpus=0
    ports:
      - "6380:6380"
      - "8265:8265"
      - "10001:10001"
    restart: always
    tmpfs:
      - /tmp/ray:mode=1777
EOF

# Start Ray head
docker-compose -f /opt/ray-compose.yml up -d
```

### Step 6: Clone RGrid Repository

```bash
cd /opt
git clone https://github.com/yourusername/rgrid.git
cd rgrid
```

### Step 7: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

Example `.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://rgrid:your_secure_password_here@localhost:5432/rgrid

# API
API_SECRET_KEY=$(openssl rand -hex 32)
API_HOST=0.0.0.0
API_PORT=8000

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=rgrid_admin
MINIO_SECRET_KEY=your_secure_minio_password
MINIO_BUCKET_NAME=rgrid
MINIO_USE_SSL=false

# Ray
RAY_HEAD_ADDRESS=ray://localhost:10001
RAY_ENABLED=true

# Hetzner Cloud
HETZNER_API_TOKEN=your_hetzner_api_token_here
HETZNER_SSH_KEY_PATH=/opt/rgrid/infra/hetzner_worker.key
```

### Step 8: Run Database Migrations

```bash
# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations
cd api
alembic upgrade head
cd ..
```

### Step 9: Deploy API Backend

```bash
# Install API as systemd service
cat > /etc/systemd/system/rgrid-api.service <<'EOF'
[Unit]
Description=RGrid API Backend
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/rgrid/api
EnvironmentFile=/opt/rgrid/.env
ExecStart=/opt/rgrid/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
systemctl daemon-reload
systemctl enable rgrid-api
systemctl start rgrid-api
```

### Step 10: Deploy Orchestrator

```bash
# Run deployment script
cd /opt/rgrid
./infra/deploy_orchestrator.sh

# Start orchestrator
systemctl start orchestrator

# Check status
systemctl status orchestrator

# View logs
journalctl -u orchestrator -f
```

### Step 11: Configure Nginx (Optional)

```bash
# Install SSL certificate (Let's Encrypt)
apt install -y certbot python3-certbot-nginx

# Get certificate
certbot certonly --nginx -d api.yourdomain.com

# Configure Nginx
cat > /etc/nginx/sites-available/rgrid <<'EOF'
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/rgrid /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

## Verification

### 1. Check Services

```bash
# PostgreSQL
systemctl status postgresql

# MinIO
docker ps | grep minio

# Ray Head
docker ps | grep ray-head

# API
systemctl status rgrid-api
curl http://localhost:8000/

# Orchestrator
systemctl status orchestrator
journalctl -u orchestrator --no-pager | tail -20
```

### 2. Submit Test Execution

```bash
# Install CLI
pip install /opt/rgrid/cli

# Initialize
rgrid init

# Submit job
echo 'print("Hello from RGrid!")' > test.py
rgrid run test.py

# Check status
rgrid status <execution-id>
```

### 3. Monitor Worker Provisioning

```bash
# Watch orchestrator logs
journalctl -u orchestrator -f

# Watch Ray dashboard
# Open http://<control-plane-ip>:8265

# Check Hetzner Cloud Console
# Workers should appear as "rgrid-worker-XXXXXX"
```

## Monitoring

### Logs

```bash
# Orchestrator
journalctl -u orchestrator -f

# API
journalctl -u rgrid-api -f

# Ray Head
docker logs -f ray-head
```

### Metrics

- Ray Dashboard: http://<control-plane-ip>:8265
- MinIO Console: http://<control-plane-ip>:9001
- PostgreSQL: Use your favorite DB client

## Cost Optimization

### Hetzner Pricing (as of 2024)

- CX22 (control plane): €6.10/month (~$6.50)
- CX22 (worker): €0.009/hour (~$0.01/hour)

### Auto-Scaling Behavior

- **Provision**: When queue depth ≥ 5 jobs
- **Terminate**: When idle AND approaching billing hour
- **Max workers**: 10 concurrent (configurable)

### Example Costs

- **Light usage** (1-2 workers, 10h/day): ~€2-4/month
- **Medium usage** (3-5 workers, 8h/day): ~€10-20/month
- **Heavy usage** (5-10 workers, 24/7): ~€300-600/month

## Troubleshooting

### Workers Not Provisioning

```bash
# Check orchestrator logs
journalctl -u orchestrator -n 100

# Verify Hetzner API token
curl -H "Authorization: Bearer $HETZNER_API_TOKEN" \
    https://api.hetzner.cloud/v1/servers

# Check SSH key uploaded
cat /opt/rgrid/infra/hetzner_worker.key.pub
```

### Workers Not Connecting to Ray

```bash
# Check Ray head is running
docker ps | grep ray-head

# Check Ray dashboard
curl http://localhost:8265/api/cluster_status

# Check worker logs (SSH into worker)
ssh -i /opt/rgrid/infra/hetzner_worker.key root@<worker-ip>
journalctl -u ray -f
```

### Database Connection Issues

```bash
# Test connection
psql postgresql://rgrid:password@localhost:5432/rgrid -c "SELECT 1"

# Check PostgreSQL is running
systemctl status postgresql

# Review pg_hba.conf
sudo cat /etc/postgresql/15/main/pg_hba.conf
```

## Security Considerations

1. **Firewall**: Only expose necessary ports (80, 443, 22)
2. **SSH Keys**: Use SSH keys, disable password authentication
3. **Database**: Strong password, local connections only
4. **API Keys**: Rotate regularly
5. **SSL**: Use HTTPS for API endpoint
6. **Workers**: Ephemeral, no persistent data

## Backup

```bash
# Database backup
pg_dump postgresql://rgrid:password@localhost:5432/rgrid > rgrid-backup.sql

# MinIO backup
docker exec minio mc mirror local/rgrid /backup/rgrid

# Configuration backup
tar czf rgrid-config-backup.tar.gz /opt/rgrid/.env /opt/rgrid/infra/hetzner_worker.key
```

## Scaling

### Increase Worker Limit

Edit `orchestrator/provisioner.py`:

```python
MAX_WORKERS = 20  # Increase from 10
```

Restart orchestrator:

```bash
systemctl restart orchestrator
```

### Multi-Region

Deploy separate control planes in different Hetzner locations:
- Nuremberg (nbg1)
- Helsinki (hel1)
- Falkenstein (fsn1)

## Support

For issues, check:
- Logs: `journalctl -u orchestrator -f`
- Ray Dashboard: http://<ip>:8265
- Hetzner Console: https://console.hetzner.cloud/

---

**Deployment Guide Complete**
**Date**: 2025-11-16
**Version**: Tier 4 Production
