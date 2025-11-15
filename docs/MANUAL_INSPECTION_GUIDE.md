# Manual Inspection Guide - How to Verify Everything Yourself

**For users who want to see the code and verify the system is real (no Docker knowledge required)**

---

## Table of Contents

1. [Inspect The Code](#1-inspect-the-code)
2. [Check Services Running](#2-check-services-running)
3. [Inspect Docker Containers](#3-inspect-docker-containers)
4. [Check Database Tables](#4-check-database-tables)
5. [View Configuration Files](#5-view-configuration-files)
6. [See Real Execution Flow](#6-see-real-execution-flow)
7. [Verify No Stubs](#7-verify-no-stubs)

---

## 1. Inspect The Code

### View Project Structure
```bash
# See all components
tree -L 2 -I 'venv|__pycache__|node_modules'

# Or use ls
ls -la
```

**Expected output:**
```
api/          - FastAPI backend
cli/          - RGrid CLI tool
runner/       - Docker executor
common/       - Shared code
tests/        - Test suite
docs/         - Documentation
```

### Read Key Implementation Files

**Docker Executor (proves real Docker execution):**
```bash
cat runner/runner/executor.py
```
Look for line 49: `container: Container = self.client.containers.run(` - this is REAL Docker

**API Execution Endpoint (proves real database writes):**
```bash
cat api/app/api/v1/executions.py
```
Look for line 49: `db.add(db_execution)` - this is REAL SQLAlchemy

**CLI Client (proves real HTTP calls):**
```bash
cat cli/rgrid/api_client.py
```
Look for: `httpx.Client` - this is REAL HTTP client

---

## 2. Check Services Running

### See What Docker Containers Are Running
```bash
docker ps
```

**You should see:**
```
CONTAINER ID   IMAGE                 STATUS       PORTS
abc123...      postgres:15-alpine    Up X min     0.0.0.0:5433->5432/tcp
def456...      minio/minio:latest    Up X min     0.0.0.0:9000-9001->9000-9001/tcp
```

This proves PostgreSQL and MinIO are REAL running services.

### Check API Server
```bash
# Is the API running?
curl http://localhost:8000/

# Check health
curl http://localhost:8000/api/v1/health
```

**Expected:**
```json
{
  "status": "ok (db: connected)",
  "version": "0.1.0"
}
```

---

## 3. Inspect Docker Containers

### See Container Details
```bash
# List containers with more info
docker ps -a

# See container logs
docker logs infra-postgres-1
docker logs infra-minio-1
```

### Enter a Running Container (like SSH)
```bash
# Go inside the PostgreSQL container
docker exec -it infra-postgres-1 /bin/sh

# Now you're INSIDE the container. Try:
ps aux              # See running processes
ls /var/lib/postgresql/data   # See database files
exit                # Leave the container
```

### See What RGrid Containers Were Created
```bash
# List all containers (including stopped ones)
docker ps -a | grep python

# See container that executed your script
docker ps -a --filter "ancestor=python:3.11-slim"
```

**This proves scripts actually ran in Docker containers**

### Inspect a Container's Details
```bash
# Get full details of postgres container
docker inspect infra-postgres-1 | less

# See just the network settings
docker inspect infra-postgres-1 | grep IPAddress
```

---

## 4. Check Database Tables

### Connect to PostgreSQL Database
```bash
# Method 1: Using docker exec (easiest)
docker exec -it infra-postgres-1 psql -U rgrid -d rgrid
```

Now you're in PostgreSQL. Try these commands:

```sql
-- See all tables
\dt

-- Should show:
--  public | executions
--  public | api_keys

-- View table structure
\d executions

-- Count total executions
SELECT COUNT(*) FROM executions;

-- See latest 5 executions
SELECT
    execution_id,
    status,
    runtime,
    created_at
FROM executions
ORDER BY created_at DESC
LIMIT 5;

-- See full details of one execution
SELECT * FROM executions LIMIT 1;

-- See environment variables stored
SELECT
    execution_id,
    env_vars
FROM executions
WHERE env_vars::text != '{}'::text;

-- Exit PostgreSQL
\q
```

### Quick Database Queries (Without Entering psql)
```bash
# Count executions
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c "SELECT COUNT(*) FROM executions;"

# See latest execution
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c "SELECT execution_id, status FROM executions ORDER BY created_at DESC LIMIT 1;"

# See all table names
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c "\dt"
```

---

## 5. View Configuration Files

### See RGrid CLI Configuration
```bash
# Where is it?
ls -la ~/.rgrid/

# What's in credentials file?
cat ~/.rgrid/credentials
```

**Expected:**
```ini
[default]
api_key = sk_dev_xxxxxxxxxxxxx
api_url = http://localhost:8000
```

### Check File Permissions (Security)
```bash
ls -la ~/.rgrid/credentials
```

**Should show:** `-rw-------` (only you can read/write)

### View Environment Variables
```bash
# See what .env file contains
cat .env

# Check DATABASE_URL
grep DATABASE_URL .env
```

### View Docker Compose Configuration
```bash
# See how services are configured
cat infra/docker-compose.yml
```

---

## 6. See Real Execution Flow

### Create a Test Script
```bash
cat > /tmp/my_test.py << 'EOF'
import sys
import os
print(f"Python version: {sys.version}")
print(f"Process ID: {os.getpid()}")
print(f"Working directory: {os.getcwd()}")
print("Hello from RGrid!")
EOF
```

### Submit It
```bash
# Make sure API is running first
# In one terminal:
cd /home/sune/Projects/rgrid
export PYTHONPATH=/home/sune/Projects/rgrid/api:$PYTHONPATH
venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal:
venv/bin/rgrid run /tmp/my_test.py --env TEST=manual_inspection
```

### Track the Execution

**Step 1: See it was received by API**
```bash
# Check API logs
tail -f /tmp/api2.log
# Look for: POST /api/v1/executions
```

**Step 2: See it in database**
```bash
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c \
  "SELECT execution_id, status, created_at FROM executions ORDER BY created_at DESC LIMIT 1;"
```

**Step 3: Get the execution details**
```bash
# Get the execution_id from previous step
EXEC_ID="exec_xxxxx"  # Replace with actual ID

curl -s http://localhost:8000/api/v1/executions/$EXEC_ID \
  -H "Authorization: Bearer $(grep api_key ~/.rgrid/credentials | cut -d'=' -f2 | xargs)" \
  | jq .
```

---

## 7. Verify No Stubs

### Check Docker Executor Code
```bash
# See the REAL Docker execution code
cat runner/runner/executor.py | grep -A 20 "def execute_script"
```

**Look for these REAL operations:**
- `docker.from_env()` - Real Docker client
- `containers.run()` - Real container creation
- `container.wait()` - Real execution wait
- `container.logs()` - Real log collection

### Check API Database Code
```bash
# See REAL database writes
cat api/app/api/v1/executions.py | grep -A 10 "db.add"
```

**Look for:**
- `db.add(db_execution)` - Real SQLAlchemy add
- `await db.flush()` - Real async database write

### Test Docker Execution Yourself
```bash
cat > /tmp/test_docker.py << 'PYEOF'
from runner.executor import DockerExecutor

script = """
print('Testing real Docker execution')
result = sum(range(100))
print(f'Sum of 0-99: {result}')
"""

executor = DockerExecutor()
exit_code, output, errors = executor.execute_script(
    script_content=script,
    runtime="python:3.11-slim",
    args=[],
    env_vars={"MANUAL_TEST": "yes"}
)

print(f"Exit code: {exit_code}")
print(f"Output:\n{output}")
executor.close()
PYEOF

venv/bin/python /tmp/test_docker.py
```

**Expected output:**
```
Exit code: 0
Output:
Testing real Docker execution
Sum of 0-99: 4950
```

If you get this, Docker execution is REAL!

---

## 8. Advanced Inspection

### Watch Docker Containers Being Created
```bash
# In one terminal, watch for new containers
watch -n 1 'docker ps -a --format "table {{.ID}}\t{{.Image}}\t{{.Status}}" | head -10'

# In another terminal, run an execution
venv/bin/rgrid run /tmp/my_test.py
```

You'll see a Python container appear and disappear!

### See Database Grow in Real-Time
```bash
# Watch execution count
watch -n 2 'docker exec infra-postgres-1 psql -U rgrid -d rgrid -t -c "SELECT COUNT(*) FROM executions;"'

# In another terminal, submit executions
venv/bin/rgrid run /tmp/my_test.py
venv/bin/rgrid run /tmp/my_test.py
```

Watch the count increase!

### See MinIO (S3 Storage)
```bash
# Access MinIO web console
echo "Open browser: http://localhost:9001"
echo "Username: rgrid_dev"
echo "Password: rgrid_dev_secret"

# Or use CLI
docker exec infra-minio-1 mc alias set local http://localhost:9000 rgrid_dev rgrid_dev_secret
docker exec infra-minio-1 mc ls local/
```

---

## Quick Verification Checklist

Run these commands to verify everything:

```bash
# 1. Check services are running
docker ps | grep -E "postgres|minio"

# 2. Check database has data
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c "SELECT COUNT(*) FROM executions;"

# 3. Check API is responding
curl http://localhost:8000/api/v1/health

# 4. Check credentials exist
ls -la ~/.rgrid/credentials

# 5. Test execution
venv/bin/rgrid run /tmp/my_test.py

# 6. Verify it's in database
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c \
  "SELECT execution_id, status FROM executions ORDER BY created_at DESC LIMIT 1;"
```

---

## Understanding What You See

### When You See This in Code:
```python
container = self.client.containers.run(...)
```
**This means:** Real Docker container is created and executed

### When You See This in Database:
```
execution_id | status | created_at
exec_abc123  | queued | 2025-11-15 15:20:45
```
**This means:** Real record stored in PostgreSQL

### When Docker Shows:
```
CONTAINER ID   IMAGE              STATUS
abc123         python:3.11-slim   Up 2 seconds
```
**This means:** Real Python container running your script

---

## Troubleshooting

### "docker: command not found"
```bash
# Install Docker first
sudo apt-get update
sudo apt-get install docker.io
```

### "Cannot connect to Docker daemon"
```bash
# Start Docker service
sudo systemctl start docker

# Or check if it's running
sudo systemctl status docker
```

### "Permission denied" for Docker
```bash
# Add yourself to docker group
sudo usermod -aG docker $USER
# Then logout and login again
```

### "API not responding"
```bash
# Start the API server
cd /home/sune/Projects/rgrid
export PYTHONPATH=/home/sune/Projects/rgrid/api:$PYTHONPATH
venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Summary

**To verify everything is real:**

1. ✅ Read the source code (no mocks, real implementations)
2. ✅ Check Docker containers are running (`docker ps`)
3. ✅ Query the database (`docker exec ... psql`)
4. ✅ View credentials (`cat ~/.rgrid/credentials`)
5. ✅ Test execution and watch it happen
6. ✅ See data persist in real PostgreSQL

**Everything is real - no stubs, no fakes, no mocks!**
