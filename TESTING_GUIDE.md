# RGrid Testing Guide - Running Your Own Scripts

## Quick Start

### ✅ Prerequisites (Already Running)
- PostgreSQL: `localhost:5433`
- MinIO: `localhost:9000`
- API Server: `localhost:8000`
- CLI configured: `~/.rgrid/credentials`

---

## 📁 Do I Need to Be in a Specific Folder?

**NO!** You can run `rgrid` from anywhere, but you need to use the full path since it's in the venv:

```bash
# Works from ANY directory:
/home/sune/Projects/rgrid/venv/bin/rgrid run /path/to/script.py

# OR activate the venv first:
source /home/sune/Projects/rgrid/venv/bin/activate
rgrid run /path/to/script.py
```

---

## 🧪 Testing Methods

### Method 1: Simple Script (No Arguments)

**1. Create your script anywhere:**
```bash
cat > ~/my_script.py << 'EOF'
print("Hello from RGrid!")
print(f"Result: {42 * 2}")
EOF
```

**2. Submit it:**
```bash
/home/sune/Projects/rgrid/venv/bin/rgrid run ~/my_script.py
```

**3. Check it was stored:**
```bash
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c \
  "SELECT execution_id, status FROM executions ORDER BY created_at DESC LIMIT 1;"
```

---

### Method 2: Script with Arguments

**Create script that uses arguments:**
```bash
cat > ~/process_files.py << 'EOF'
import sys

print(f"Processing {len(sys.argv)-1} files:")
for i, filename in enumerate(sys.argv[1:], 1):
    print(f"  {i}. {filename}")
EOF
```

**Run with arguments:**
```bash
/home/sune/Projects/rgrid/venv/bin/rgrid run ~/process_files.py \
  input.txt data.csv results.json
```

**Arguments are passed to sys.argv[1:]** in the Docker container.

---

### Method 3: Script with Environment Variables

**Create script that uses env vars:**
```bash
cat > ~/config_script.py << 'EOF'
import os

mode = os.getenv('MODE', 'development')
api_key = os.getenv('API_KEY', 'not-set')
debug = os.getenv('DEBUG', 'false')

print(f"Running in {mode} mode")
print(f"API Key: {api_key}")
print(f"Debug: {debug}")
EOF
```

**Run with environment variables:**
```bash
/home/sune/Projects/rgrid/venv/bin/rgrid run ~/config_script.py \
  --env MODE=production \
  --env API_KEY=sk_live_abc123 \
  --env DEBUG=true
```

---

### Method 4: Combined (Arguments + Environment Variables)

```bash
/home/sune/Projects/rgrid/venv/bin/rgrid run ~/my_script.py \
  file1.txt file2.txt output.csv \
  --env MODE=production \
  --env USER_ID=12345 \
  --env REGION=eu-west-1
```

---

## 🔍 Verification Methods

### 1. Check Database
```bash
# See all executions
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c \
  "SELECT execution_id, status, created_at FROM executions ORDER BY created_at DESC LIMIT 5;"

# See execution with arguments and env vars
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c \
  "SELECT execution_id, args, env_vars FROM executions WHERE args::text != '[]'::text LIMIT 1;"
```

### 2. Check via API
```bash
# Get your API key
API_KEY=$(grep api_key ~/.rgrid/credentials | cut -d'=' -f2 | xargs)

# Get latest execution
EXEC_ID=$(docker exec infra-postgres-1 psql -U rgrid -d rgrid -t -c \
  "SELECT execution_id FROM executions ORDER BY created_at DESC LIMIT 1;")

# Query API
curl -s http://localhost:8000/api/v1/executions/$EXEC_ID \
  -H "Authorization: Bearer $API_KEY" | jq .
```

### 3. Test Docker Execution Manually

If you want to see what the output would be (since we don't have workers yet):

```bash
cat > /tmp/test_execution.py << 'EOF'
import sys
sys.path.insert(0, '/home/sune/Projects/rgrid/runner')
from runner.executor import DockerExecutor

# Read your script
with open('/path/to/your/script.py', 'r') as f:
    script = f.read()

# Execute it
executor = DockerExecutor()
exit_code, output, errors = executor.execute_script(
    script_content=script,
    runtime="python:3.11-slim",
    args=["arg1", "arg2"],
    env_vars={"KEY": "value"}
)

print(f"Exit Code: {exit_code}")
print(f"Output:\n{output}")
executor.close()
EOF

/home/sune/Projects/rgrid/venv/bin/python /tmp/test_execution.py
```

---

## 📋 Example Test Scripts

### Example 1: Data Processing
```python
#!/usr/bin/env python3
import sys
import json

# Get filenames from arguments
input_file = sys.argv[1] if len(sys.argv) > 1 else "data.json"
output_file = sys.argv[2] if len(sys.argv) > 2 else "results.json"

print(f"Processing {input_file} → {output_file}")

# Your processing logic here
result = {"status": "processed", "count": 42}
print(json.dumps(result, indent=2))
```

### Example 2: Environment-based Configuration
```python
#!/usr/bin/env python3
import os

# Read config from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/db')
API_ENDPOINT = os.getenv('API_ENDPOINT', 'https://api.example.com')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))

print(f"Connecting to: {DATABASE_URL}")
print(f"API: {API_ENDPOINT}")
print(f"Processing in batches of {BATCH_SIZE}")
```

### Example 3: Complete Example
```python
#!/usr/bin/env python3
import sys
import os
import json
from datetime import datetime

def main():
    # Configuration from environment
    mode = os.getenv('MODE', 'development')
    max_items = int(os.getenv('MAX_ITEMS', '10'))

    # Input from arguments
    input_files = sys.argv[1:] if len(sys.argv) > 1 else []

    # Processing
    print(f"Running in {mode} mode")
    print(f"Processing {len(input_files)} files (max: {max_items})")

    results = {
        "timestamp": str(datetime.now()),
        "mode": mode,
        "files_processed": len(input_files),
        "files": input_files[:max_items]
    }

    print(json.dumps(results, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

**Run it:**
```bash
/home/sune/Projects/rgrid/venv/bin/rgrid run ~/complete_example.py \
  file1.csv file2.csv file3.csv \
  --env MODE=production \
  --env MAX_ITEMS=5
```

---

## 🎯 What's Working vs Not Working

### ✅ Working Now
- Submit scripts from anywhere on your system
- Pass arguments to scripts
- Set environment variables
- Store executions in PostgreSQL
- Execute scripts in Docker containers (manually)
- Verify via database queries

### ❌ Not Working Yet (Need Tier 2)
- Automatic execution (need worker daemon)
- `rgrid status <exec_id>` command
- `rgrid logs <exec_id>` command
- Real-time log streaming
- Auto-transition from "queued" → "running" → "completed"

---

## 🚀 Quick Reference

```bash
# Simple execution
venv/bin/rgrid run script.py

# With arguments
venv/bin/rgrid run script.py arg1 arg2 arg3

# With environment variables
venv/bin/rgrid run script.py --env KEY=value --env FOO=bar

# Combined
venv/bin/rgrid run script.py file.txt --env MODE=prod

# Check database
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c \
  "SELECT COUNT(*) FROM executions;"

# View latest execution
docker exec infra-postgres-1 psql -U rgrid -d rgrid -c \
  "SELECT * FROM executions ORDER BY created_at DESC LIMIT 1;"
```

---

## 📝 Important Notes

1. **Script location:** Can be ANYWHERE on your system
2. **Working directory:** Can run `rgrid` from ANY directory (using full path)
3. **Python version in container:** Scripts run in Python 3.11 (not your system Python)
4. **Status stays "queued":** Normal for Tier 1 - no worker daemon yet
5. **Output not captured yet:** Need worker to store stdout/stderr

---

## 🐛 Troubleshooting

**"Error: Connection refused"**
```bash
# Check if API is running
curl http://localhost:8000/api/v1/health

# If not, start it:
cd /home/sune/Projects/rgrid
export PYTHONPATH=/home/sune/Projects/rgrid/api:$PYTHONPATH
venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

**"Error: Missing Authorization header"**
```bash
# Reinitialize CLI
venv/bin/rgrid init
```

**Want to see actual execution output?**
```bash
# Use manual Docker executor test (shown in Method 3 above)
```

---

**Happy Testing!** 🎉
