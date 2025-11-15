# Quick Command Reference

**Copy-paste these commands to inspect the system**

---

## 🔍 Inspect Code

```bash
# View Docker executor (real implementation)
cat runner/runner/executor.py

# View API endpoint (real database writes)
cat api/app/api/v1/executions.py

# View CLI client (real HTTP calls)
cat cli/rgrid/api_client.py

# View database models
cat api/app/models/execution.py
```

---

## 🐳 Check Docker

```bash
# See what's running
docker ps

# See container logs
docker logs infra-postgres-1
docker logs infra-minio-1

# Go inside PostgreSQL container
docker exec -it infra-postgres-1 /bin/sh
# (type 'exit' to leave)

# See all containers (including stopped)
docker ps -a
```

---

## 🗄️ Check Database

```bash
# Enter PostgreSQL
docker exec -it infra-postgres-1 psql -U rgrid -d rgrid

# Then inside PostgreSQL:
\dt                          # List tables
\d executions               # Show table structure
SELECT COUNT(*) FROM executions;
SELECT * FROM executions ORDER BY created_at DESC LIMIT 5;
\q                          # Exit

# Or quick one-liners:
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c "SELECT COUNT(*) FROM executions;"
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c "SELECT execution_id, status FROM executions ORDER BY created_at DESC LIMIT 3;"
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c "\d executions"
```

---

## 📁 Check Files

```bash
# RGrid credentials
ls -la ~/.rgrid/
cat ~/.rgrid/credentials

# Environment config
cat .env

# Project structure
ls -la
tree -L 2 -I 'venv|__pycache__'

# Test files
ls -la tests/
```

---

## 🧪 Test Execution

```bash
# Create test script
cat > /tmp/test.py << 'EOF'
import sys
print(f"Python: {sys.version[:20]}")
print("Hello from RGrid!")
result = 42 * 2
print(f"Calculation: {result}")
EOF

# Run it
venv/bin/rgrid run /tmp/test.py --env TEST=manual

# Check it's in database
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c "SELECT execution_id, status FROM executions ORDER BY created_at DESC LIMIT 1;"
```

---

## 🚀 Start/Stop Services

```bash
# Start services
docker-compose -f infra/docker-compose.yml up -d

# Stop services
docker-compose -f infra/docker-compose.yml down

# Restart a service
docker-compose -f infra/docker-compose.yml restart postgres

# Check service status
docker-compose -f infra/docker-compose.yml ps
```

---

## 🌐 Check API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Root endpoint
curl http://localhost:8000/

# Get API docs (in browser)
xdg-open http://localhost:8000/docs
# Or manually: http://localhost:8000/docs

# Test execution creation
curl -X POST http://localhost:8000/api/v1/executions \
  -H "Authorization: Bearer sk_dev_test123" \
  -H "Content-Type: application/json" \
  -d '{
    "script_content": "print(\"test\")",
    "runtime": "python:3.11",
    "args": [],
    "env_vars": {}
  }'
```

---

## 📊 Monitor in Real-Time

```bash
# Watch Docker containers
watch -n 1 'docker ps --format "table {{.ID}}\t{{.Image}}\t{{.Status}}"'

# Watch database count
watch -n 2 'docker exec infra-postgres-1 psql -U rgrid -d rgrid -t -c "SELECT COUNT(*) FROM executions;"'

# Watch API logs
tail -f /tmp/api2.log

# Watch PostgreSQL logs
docker logs -f infra-postgres-1
```

---

## 🔬 Verify Real Execution

```bash
# Test Docker executor directly
cat > /tmp/verify.py << 'EOF'
from runner.executor import DockerExecutor

executor = DockerExecutor()
code, out, err = executor.execute_script(
    "print('Real execution test'); print(42+58)",
    "python:3.11-slim", [], {}
)
print(f"Exit: {code}\nOutput:\n{out}")
executor.close()
EOF

venv/bin/python /tmp/verify.py
```

---

## 🧹 Cleanup

```bash
# Remove all executions from database
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c "TRUNCATE TABLE executions;"

# Remove credentials
rm -rf ~/.rgrid/

# Stop all services
docker-compose -f infra/docker-compose.yml down

# Remove all containers
docker-compose -f infra/docker-compose.yml down -v
```

---

## 🐛 Troubleshooting

```bash
# Check if services are healthy
docker ps
curl http://localhost:8000/api/v1/health

# Restart API server
pkill -f uvicorn
export PYTHONPATH=/home/sune/Projects/rgrid/api:$PYTHONPATH
venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Check database is accessible
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c "SELECT 1;"

# Reinitialize CLI
rm -rf ~/.rgrid && venv/bin/rgrid init
```

---

## 📝 Common Queries

```sql
-- Inside psql (docker exec -it infra-postgres-1 psql -U rgrid -d rgrid)

-- Total executions
SELECT COUNT(*) FROM executions;

-- Latest 10 executions
SELECT execution_id, status, runtime, created_at
FROM executions
ORDER BY created_at DESC
LIMIT 10;

-- Failed executions
SELECT execution_id, exit_code
FROM executions
WHERE status = 'failed';

-- Executions with environment variables
SELECT execution_id, env_vars
FROM executions
WHERE env_vars::text != '{}'::text;

-- Script preview
SELECT execution_id, LEFT(script_content, 100) as preview
FROM executions
ORDER BY created_at DESC
LIMIT 5;
```

---

**Save this file for quick reference!**
