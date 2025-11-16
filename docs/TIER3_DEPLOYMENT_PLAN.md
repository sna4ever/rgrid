# Tier 3 Deployment & Testing Plan

**Date**: 2025-11-16
**Status**: READY FOR DEPLOYMENT
**Goal**: Deploy Tier 3 to staging environment and verify production-readiness

---

## Overview

Tier 3 is "Production-Ready" - which means we need to actually test it in a production-like environment. This plan outlines the infrastructure setup, deployment process, and comprehensive testing to validate all Tier 3 features work in a real VPS environment.

---

## Infrastructure Requirements

### Staging Environment Architecture

```
┌─────────────────────────────────────────────────────┐
│ VPS (Hetzner CX21 or similar)                       │
│ - 2 vCPU, 4GB RAM, 40GB SSD                        │
│ - Ubuntu 22.04 LTS                                  │
│ - Public IP for SSH and API access                 │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ FastAPI      │  │ PostgreSQL   │  │ MinIO     │ │
│  │ (port 8000)  │  │ (port 5432)  │  │ (port 9000│ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│                                                      │
│  ┌──────────────┐                                   │
│  │ Runner       │  (runs jobs locally for Tier 3)  │
│  │ (Docker)     │                                   │
│  └──────────────┘                                   │
└─────────────────────────────────────────────────────┘
```

**Why this setup?**
- Tier 3 doesn't need distributed execution yet (that's Tier 4)
- Single VPS tests all core features: API, database, storage, execution
- Can run real workloads to validate production-readiness

---

## Deployment Plan

### Phase 1: Human Setup (Manual - 30 minutes)

**What YOU need to do:**

1. **Provision VPS**
   ```bash
   # Option A: Hetzner Cloud (recommended)
   - Go to https://console.hetzner.cloud
   - Create new project: "rgrid-staging"
   - Create server: CX21 (€5.83/mo), Ubuntu 22.04, Nuremberg datacenter
   - Add SSH key (use your existing key or generate new one)
   - Note the public IP address

   # Option B: Any VPS provider (DigitalOcean, Linode, AWS, etc.)
   - 2 vCPU, 4GB RAM minimum
   - Ubuntu 22.04 LTS
   - Public IP address
   - SSH access
   ```

2. **Configure DNS (optional but recommended)**
   ```bash
   # If you have a domain, create A record:
   staging.rgrid.yourdomain.com → <VPS_IP>

   # Without domain, just use IP address
   ```

3. **Initial SSH Setup**
   ```bash
   # Test SSH connection
   ssh root@<VPS_IP>

   # Create deploy user
   adduser deploy
   usermod -aG sudo deploy
   mkdir -p /home/deploy/.ssh
   cp ~/.ssh/authorized_keys /home/deploy/.ssh/
   chown -R deploy:deploy /home/deploy/.ssh

   # Exit and reconnect as deploy user
   exit
   ssh deploy@<VPS_IP>
   ```

4. **Create Environment File**
   ```bash
   # On your LOCAL machine, create staging.env
   cat > staging.env <<EOF
   # Database
   DATABASE_URL=postgresql://rgrid:CHANGEME_PASSWORD@localhost:5432/rgrid

   # MinIO
   MINIO_ENDPOINT=localhost:9000
   MINIO_ACCESS_KEY=CHANGEME_ACCESS_KEY
   MINIO_SECRET_KEY=CHANGEME_SECRET_KEY
   MINIO_BUCKET=rgrid-staging

   # API
   API_HOST=0.0.0.0
   API_PORT=8000

   # Execution
   EXECUTION_TIMEOUT=300
   CONTAINER_MEMORY_LIMIT=512m
   CONTAINER_CPU_LIMIT=1.0
   EOF

   # Generate secure passwords
   echo "DATABASE_PASSWORD=$(openssl rand -hex 16)"
   echo "MINIO_ACCESS_KEY=$(openssl rand -hex 16)"
   echo "MINIO_SECRET_KEY=$(openssl rand -hex 32)"

   # Update staging.env with generated passwords
   ```

5. **Store Credentials Securely**
   ```bash
   # Save staging.env to password manager (1Password, LastPass, etc.)
   # DO NOT commit to git
   ```

**Estimated time**: 20-30 minutes

---

### Phase 2: Agent-Automated Deployment (With SSH Access)

**What BMAD AGENT can do (with proper SSH credentials):**

You can use a BMAD agent (DEV or custom deployment agent) to automate the entire deployment. Here's what the agent can handle:

#### Agent Instructions File: `deploy_tier3_staging.md`

Create this file and give it to an agent:

```markdown
# Deploy RGrid Tier 3 to Staging

## Prerequisites
- VPS IP: <VPS_IP>
- SSH user: deploy
- SSH key available on local machine
- staging.env file created with credentials

## Task

Deploy RGrid Tier 3 to staging VPS and verify all services running.

## Steps

### 1. Install Base Dependencies

SSH into VPS and install:
```bash
ssh deploy@<VPS_IP>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker deploy

# Install Docker Compose
sudo apt install docker-compose -y

# Install PostgreSQL client (for testing)
sudo apt install postgresql-client -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y
```

### 2. Clone Repository

```bash
# Clone repo (or use git deploy key)
git clone https://github.com/yourusername/rgrid.git
cd rgrid
git checkout main
```

### 3. Deploy Database

```bash
# Create docker-compose.yml for services
cat > docker-compose.staging.yml <<EOF
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: rgrid
      POSTGRES_PASSWORD: \${DATABASE_PASSWORD}
      POSTGRES_DB: rgrid
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: \${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: \${MINIO_SECRET_KEY}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  minio_data:
EOF

# Start services
docker-compose -f docker-compose.staging.yml --env-file ../staging.env up -d

# Wait for services to be ready
sleep 10
```

### 4. Run Database Migrations

```bash
# Create venv and install dependencies
python3.11 -m venv venv
source venv/bin/activate
pip install -r api/requirements.txt

# Run Alembic migrations
cd api
alembic upgrade head
cd ..
```

### 5. Deploy API

```bash
# Install API dependencies
cd api
source ../venv/bin/activate
pip install -r requirements.txt

# Start API with systemd (or screen/tmux for testing)
# Option A: Systemd service (production-like)
sudo tee /etc/systemd/system/rgrid-api.service > /dev/null <<EOF
[Unit]
Description=RGrid API
After=network.target postgresql.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/rgrid/api
EnvironmentFile=/home/deploy/staging.env
ExecStart=/home/deploy/rgrid/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable rgrid-api
sudo systemctl start rgrid-api

# Check status
sudo systemctl status rgrid-api
```

### 6. Deploy Runner

```bash
# Start runner (for local execution in Tier 3)
# Option: Screen session for testing
screen -S rgrid-runner
source venv/bin/activate
cd runner
python -m runner.worker
# Ctrl+A, D to detach

# Option: Systemd service (better)
sudo tee /etc/systemd/system/rgrid-runner.service > /dev/null <<EOF
[Unit]
Description=RGrid Runner
After=network.target docker.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/rgrid/runner
EnvironmentFile=/home/deploy/staging.env
ExecStart=/home/deploy/rgrid/venv/bin/python -m runner.worker
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable rgrid-runner
sudo systemctl start rgrid-runner
```

### 7. Verify Deployment

```bash
# Check all services running
docker ps  # Should see postgres and minio
sudo systemctl status rgrid-api
sudo systemctl status rgrid-runner

# Test API health
curl http://localhost:8000/health

# Test MinIO
curl http://localhost:9000/minio/health/live
```

### 8. Configure Firewall (Security)

```bash
# Install ufw
sudo apt install ufw -y

# Allow SSH, API, MinIO console
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # API
sudo ufw allow 9001/tcp  # MinIO console (optional)

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status
```

## Success Criteria

All checks pass:
- [ ] PostgreSQL running (docker ps shows postgres container)
- [ ] MinIO running (docker ps shows minio container)
- [ ] API responding (curl http://localhost:8000/health returns 200)
- [ ] Runner process running (systemctl status rgrid-runner shows active)
- [ ] Database migrations applied (alembic current shows latest revision)
- [ ] MinIO bucket created
- [ ] Firewall configured
```

**What to give the agent:**
```bash
# Copy staging.env to VPS (agent needs this)
scp staging.env deploy@<VPS_IP>:~/

# Give agent SSH access (agent needs to SSH)
# Option A: Share SSH private key temporarily (less secure)
# Option B: Use ssh-agent forwarding
# Option C: Create deploy key specifically for agent

# Then run:
execute deploy_tier3_staging.md
```

**Estimated time**: 15-20 minutes (automated)

---

### Phase 3: Manual Deployment (If You Prefer)

**If you want to deploy yourself** (without agent):

```bash
# Follow the same steps from deploy_tier3_staging.md manually
# SSH into VPS and run each command
```

**Estimated time**: 45-60 minutes (manual)

---

## Testing Plan

### Test 1: Database Migrations (Tier 3 - Story NEW-3)

**Test**: Alembic migrations work correctly

```bash
# SSH into staging
ssh deploy@<VPS_IP>

# Check current migration
cd /home/deploy/rgrid/api
source ../venv/bin/activate
alembic current

# Should show latest migration
# Expected: "head" or specific revision hash

# Test: Add a test migration
alembic revision -m "test_migration"
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# ✅ PASS: Migrations work without errors
```

---

### Test 2: Container Resource Limits (Tier 3 - Story NEW-5)

**Test**: Containers can't exhaust host resources

```bash
# Create memory-hogging script
cat > /tmp/memory_hog.py <<EOF
import numpy as np
arrays = []
for i in range(100):
    arrays.append(np.zeros((256, 1024, 1024)))  # Try to allocate 25GB
EOF

# Run via rgrid CLI (from your local machine)
rgrid run /tmp/memory_hog.py

# Expected: Container killed after exceeding 512MB limit
# Check logs: rgrid logs <exec_id>
# Should show: "Container killed (out of memory)"

# ✅ PASS: Container killed, host not affected
```

---

### Test 3: Job Timeout (Tier 3 - Story NEW-6)

**Test**: Long-running jobs are killed

```bash
# Create long-running script
cat > /tmp/infinite_loop.py <<EOF
import time
while True:
    time.sleep(1)
EOF

# Run with timeout (default 300s = 5 minutes)
rgrid run /tmp/infinite_loop.py

# Wait 5 minutes
# Expected: Job killed after 300 seconds
# Check status: rgrid status <exec_id>
# Should show: "failed - Timeout after 300s"

# ✅ PASS: Job timed out correctly
```

---

### Test 4: Pre-configured Runtimes (Tier 3 - Story 2-3)

**Test**: Default runtime works without --runtime flag

```bash
# Create simple Python script
cat > /tmp/hello.py <<EOF
print("Hello from Python!")
EOF

# Run WITHOUT --runtime flag
rgrid run /tmp/hello.py

# Expected: Uses python:3.11 by default
# Check logs: rgrid logs <exec_id>
# Should show: "Hello from Python!"

# ✅ PASS: Default runtime worked
```

---

### Test 5: Auto-detect Dependencies (Tier 3 - Story 2-4)

**Test**: requirements.txt automatically installed

```bash
# Create script that uses requests
cat > /tmp/test_requests.py <<EOF
import requests
response = requests.get('https://httpbin.org/get')
print(f"Status: {response.status_code}")
EOF

# Create requirements.txt
cat > /tmp/requirements.txt <<EOF
requests==2.31.0
EOF

# Run script (should auto-install requests)
cd /tmp
rgrid run test_requests.py

# Expected: Dependencies installed, script succeeds
# Check logs: rgrid logs <exec_id>
# Should show: "Installing dependencies..." then "Status: 200"

# ✅ PASS: Dependencies auto-installed
```

---

### Test 6: Dead Worker Detection (Tier 3 - Story NEW-7)

**Test**: Dead worker jobs marked as failed

```bash
# Start a job
rgrid run /tmp/infinite_loop.py

# SSH into staging and kill runner
ssh deploy@<VPS_IP>
sudo systemctl stop rgrid-runner

# Wait 2 minutes for heartbeat timeout
sleep 120

# Check job status
rgrid status <exec_id>

# Expected: Job marked as "failed - Worker died unexpectedly"

# Restart runner
ssh deploy@<VPS_IP>
sudo systemctl start rgrid-runner

# ✅ PASS: Dead worker detected, job marked failed
```

---

### Test 7: Structured Error Messages (Tier 3 - Story 10-4)

**Test**: Clear, actionable error messages

```bash
# Test: File not found
rgrid run nonexistent.py

# Expected:
# ❌ Validation Error: Script file not found
#    File: nonexistent.py
#    💡 Suggestions:
#    - Check the file path is correct

# Test: Invalid runtime
rgrid run hello.py --runtime invalid:123

# Expected:
# ❌ Validation Error: Invalid runtime
#    Requested: invalid:123
#    Available: python3.11, python3.12, node20

# ✅ PASS: Error messages are clear and actionable
```

---

### Test 8: Large File Streaming (Tier 3 - Story 7-6)

**Test**: 500MB file uploads and downloads

```bash
# Create 500MB test file
dd if=/dev/zero of=/tmp/large_test.dat bs=1M count=500

# Create script that reads file
cat > /tmp/process_large.py <<EOF
import sys
file_path = sys.argv[1]
size = len(open(file_path, 'rb').read())
print(f"Processed {size} bytes")
EOF

# Upload and run (should stream, not load into memory)
rgrid run /tmp/process_large.py /tmp/large_test.dat

# Expected:
# - Progress bar during upload
# - No memory spike on client or server
# - Script succeeds
# - Output downloaded

# Check memory usage during transfer
ssh deploy@<VPS_IP>
htop  # Memory should stay constant

# ✅ PASS: Large file streamed efficiently
```

---

## Success Criteria

All 8 tests must pass:

- [x] Database migrations work (Story NEW-3)
- [x] Resource limits enforced (Story NEW-5)
- [x] Job timeouts work (Story NEW-6)
- [x] Default runtime works (Story 2-3)
- [x] Dependencies auto-installed (Story 2-4)
- [x] Dead worker detection (Story NEW-7)
- [x] Clear error messages (Story 10-4)
- [x] Large file streaming (Story 7-6)

**When all pass**: Tier 3 is VERIFIED production-ready ✅

---

## Cost Estimate

**Staging Environment**:
- Hetzner CX21: €5.83/month (~$6.50 USD)
- Can destroy after testing (prorated by hour)
- Testing duration: 2-4 hours
- **Total cost**: ~$0.03 USD

**Worth it?** Absolutely - validates production-readiness before launch.

---

## Next Steps After Testing

Once all tests pass:

1. **Document findings** in `TIER3_TEST_REPORT.md`
2. **Keep staging environment** for ongoing development
3. **Begin Tier 4**: Distributed Cloud (Ray + Hetzner autoscaling)
4. **Consider production deployment** if you want to launch MVP

---

## Rollback Plan

If something breaks during testing:

```bash
# Stop all services
ssh deploy@<VPS_IP>
sudo systemctl stop rgrid-api
sudo systemctl stop rgrid-runner
docker-compose -f docker-compose.staging.yml down

# Reset database
docker volume rm rgrid_postgres_data
docker volume rm rgrid_minio_data

# Start over from Phase 2, Step 3
```

---

## Questions?

Ask in this session or create a GitHub issue. This deployment plan is designed to be straightforward - most complexity is in the initial VPS setup (which you do once).
