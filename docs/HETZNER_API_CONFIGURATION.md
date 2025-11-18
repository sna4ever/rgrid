# Hetzner API Configuration Guide

## Overview

The RGrid orchestrator uses the Hetzner Cloud API to provision and manage worker nodes automatically. This guide explains where and how to configure your Hetzner API credentials.

---

## Configuration Location

### Environment Files (On Deployment Server)

**Hetzner API credentials are stored in environment-specific files on the deployment server:**

- **Staging**: `/home/deploy/rgrid/.env.staging`
- **Production**: `/home/deploy/rgrid/.env.production`

**Each environment has its own:**
- API token
- SSH key
- Database connection
- MinIO configuration

---

## Required Environment Variables

The orchestrator daemon requires three Hetzner-related variables:

```bash
# Hetzner Cloud API Configuration
HETZNER_API_TOKEN=your_hetzner_api_token_here
HETZNER_SSH_KEY_PATH=/home/deploy/.ssh/rgrid_worker_key
ORCHESTRATOR_ENABLED=true
```

### Variable Descriptions

#### `HETZNER_API_TOKEN` (REQUIRED)
- **Purpose**: Authenticates with Hetzner Cloud API
- **Format**: Long alphanumeric string (e.g., `foE9Lyda2ApwsWtKsOrezXLE7sUP2R5bm869ArVGaJLAWosn5EWao1NMyqNDrnHO`)
- **Permissions Required**: Read & Write
- **Used For**:
  - Creating worker servers (CX22 instances)
  - Uploading SSH keys
  - Deleting terminated workers
  - Querying server status

**How to Get**:
1. Log in to [Hetzner Cloud Console](https://console.hetzner.cloud/)
2. Navigate to Project → Security → API Tokens
3. Click "Generate API Token"
4. Name: `rgrid-orchestrator-staging` (or `production`)
5. Permissions: **Read & Write**
6. Copy token immediately (shown only once)

#### `HETZNER_SSH_KEY_PATH` (REQUIRED)
- **Purpose**: SSH private key for accessing provisioned workers
- **Format**: Filesystem path
- **Default Staging**: `/home/deploy/.ssh/rgrid_worker_key`
- **Default Production**: `/home/deploy/.ssh/rgrid_worker_key_prod`
- **Used For**:
  - Orchestrator uploads public key to Hetzner
  - Workers are provisioned with this public key
  - Future: Direct SSH access for debugging

**SSH Key Pair**:
- **Private key**: Stored on server at path above (never committed to git)
- **Public key**: Uploaded to Hetzner Cloud automatically by orchestrator
- **Generated during deployment**: `ssh-keygen -t ed25519 -f <path> -N ""`

#### `ORCHESTRATOR_ENABLED` (OPTIONAL)
- **Purpose**: Master switch to enable/disable worker provisioning
- **Values**: `true` or `false`
- **Default**: `false` (safe default)
- **Use Case**:
  - Set to `false` during initial testing
  - Set to `true` when ready for worker provisioning
  - Prevents accidental worker provisioning with invalid token

---

## Configuration Flow

### How Orchestrator Loads Configuration

```
1. systemd service starts
   └─ Reads EnvironmentFile: /home/deploy/rgrid/.env.staging

2. Orchestrator daemon starts
   └─ Reads os.getenv("HETZNER_API_TOKEN")
   └─ Reads os.getenv("HETZNER_SSH_KEY_PATH")
   └─ Validates all required variables present

3. Components initialize
   ├─ HetznerClient(api_token)
   ├─ WorkerProvisioner(api_token, ssh_key_path)
   └─ WorkerLifecycleManager(api_token)

4. Provisioning starts
   └─ Orchestrator uploads SSH public key to Hetzner
   └─ Monitors queue depth
   └─ Provisions workers as needed
```

### systemd Service Integration

**Staging Service** (`/etc/systemd/system/orchestrator-staging.service`):
```ini
[Service]
EnvironmentFile=/home/deploy/rgrid/.env.staging  # ← Loads variables
ExecStart=/home/deploy/rgrid/venv/bin/python -m orchestrator.daemon
```

**Production Service** (`/etc/systemd/system/orchestrator-production.service`):
```ini
[Service]
EnvironmentFile=/home/deploy/rgrid/.env.production  # ← Loads variables
ExecStart=/home/deploy/rgrid/venv/bin/python -m orchestrator.daemon
```

---

## Setup Instructions

### For Staging Environment

1. **SSH into deployment server**:
   ```bash
   ssh deploy@46.62.246.120
   ```

2. **Edit staging environment file**:
   ```bash
   nano /home/deploy/rgrid/.env.staging
   ```

3. **Update Hetzner configuration**:
   ```bash
   # Find these lines and update:
   HETZNER_API_TOKEN=your_real_token_here
   HETZNER_SSH_KEY_PATH=/home/deploy/.ssh/rgrid_worker_key
   ORCHESTRATOR_ENABLED=true
   ```

4. **Verify SSH key exists**:
   ```bash
   ls -la /home/deploy/.ssh/rgrid_worker_key*
   # Should show:
   # -rw------- rgrid_worker_key (private)
   # -rw-r--r-- rgrid_worker_key.pub (public)
   ```

5. **Restart orchestrator**:
   ```bash
   sudo systemctl restart orchestrator-staging
   ```

6. **Verify orchestrator started**:
   ```bash
   systemctl status orchestrator-staging
   journalctl -u orchestrator-staging -n 50 --no-pager
   ```

7. **Check for successful SSH key upload**:
   ```bash
   journalctl -u orchestrator-staging | grep "SSH key"
   # Should see: "Using existing SSH key (ID: 12345)"
   # Or: "Created SSH key (ID: 12345)"
   ```

### For Production Environment

**Same steps as staging, but use:**
- File: `/home/deploy/rgrid/.env.production`
- Service: `orchestrator-production`
- SSH Key: `/home/deploy/.ssh/rgrid_worker_key_prod`

**⚠️ IMPORTANT**: Always test on staging first!

---

## Security Best Practices

### API Token Security

✅ **DO**:
- Store tokens only in environment files on the server
- Use separate tokens for staging and production
- Set token permissions to "Read & Write" (minimum required)
- Rotate tokens periodically (every 90 days recommended)
- Name tokens descriptively (`rgrid-orchestrator-staging`)

❌ **DON'T**:
- Never commit API tokens to git
- Never share tokens between environments
- Never use "Admin" permission tokens
- Never log tokens in plaintext

### File Permissions

**Environment files**:
```bash
chmod 600 /home/deploy/rgrid/.env.staging
chmod 600 /home/deploy/rgrid/.env.production
```

**SSH private keys**:
```bash
chmod 600 /home/deploy/.ssh/rgrid_worker_key
chmod 600 /home/deploy/.ssh/rgrid_worker_key_prod
```

**SSH public keys**:
```bash
chmod 644 /home/deploy/.ssh/rgrid_worker_key.pub
chmod 644 /home/deploy/.ssh/rgrid_worker_key_prod.pub
```

---

## Verification

### Check Configuration Loaded

```bash
# View orchestrator startup logs
journalctl -u orchestrator-staging -n 100 --no-pager | grep -E "(started|HETZNER|SSH key)"
```

**Expected output**:
```
Worker provisioner started
Using existing SSH key (ID: 12345678)
```

**Error output** (if token invalid):
```
ERROR - Failed to get SSH keys: {"error":{"code":"unauthorized"}}
ERROR - Failed to ensure SSH key: unauthorized
```

### Test Hetzner API Access

```bash
# From deployment server
HETZNER_TOKEN="your_token_here"
curl -H "Authorization: Bearer $HETZNER_TOKEN" \
  https://api.hetzner.cloud/v1/servers
```

**Expected**: JSON response with server list (may be empty)
**Error**: `{"error":{"code":"unauthorized"}}` means invalid token

---

## Troubleshooting

### "unauthorized" Errors

**Problem**: Orchestrator logs show:
```
ERROR - Failed to get SSH keys: unauthorized
```

**Solution**:
1. Verify token is correct in `.env.staging`
2. Check token permissions (must be "Read & Write")
3. Verify token is for correct Hetzner project
4. Check token hasn't expired
5. Restart orchestrator after fixing

### SSH Key Upload Fails

**Problem**: Orchestrator logs show:
```
ERROR - Failed to ensure SSH key: Failed to create SSH key
```

**Solution**:
1. Verify SSH public key exists at specified path
2. Check file permissions (should be readable)
3. Verify Hetzner API token has "Write" permission
4. Check Hetzner project SSH key limit (default: 50)

### Workers Not Provisioning

**Problem**: Queue has jobs but no workers provision

**Solution**:
1. Check `ORCHESTRATOR_ENABLED=true` in environment file
2. Verify queue depth ≥ 5 (provisioning threshold)
3. Check Hetzner account limits (quota)
4. Review orchestrator provisioner logs
5. Verify SSH key uploaded successfully

---

## Environment File Examples

### Staging (.env.staging)

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://rgrid_staging:password@localhost:5433/rgrid_staging

# Hetzner Cloud Configuration (Tier 4)
HETZNER_API_TOKEN=your_staging_token_here_foE9Lyda2ApwsWtKsOrezXLE
HETZNER_SSH_KEY_PATH=/home/deploy/.ssh/rgrid_worker_key
ORCHESTRATOR_ENABLED=true

# MinIO Configuration
MINIO_ENDPOINT=localhost:9091
MINIO_ACCESS_KEY=rgrid_staging_user
MINIO_SECRET_KEY=rgrid_staging_secret_key
MINIO_BUCKET=rgrid-staging

# Ray Configuration (Optional)
RAY_ENABLED=false
RAY_HEAD_ADDRESS=ray://10.0.0.1:10001

# Logging
LOG_LEVEL=INFO
```

### Production (.env.production)

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://rgrid_prod:secure_password@localhost:5432/rgrid_production

# Hetzner Cloud Configuration (Tier 4)
HETZNER_API_TOKEN=your_production_token_here_XYZ123456789ABC
HETZNER_SSH_KEY_PATH=/home/deploy/.ssh/rgrid_worker_key_prod
ORCHESTRATOR_ENABLED=true

# MinIO Configuration
MINIO_ENDPOINT=localhost:9090
MINIO_ACCESS_KEY=rgrid_prod_user
MINIO_SECRET_KEY=rgrid_prod_very_secure_key
MINIO_BUCKET=rgrid-production

# Ray Configuration (Optional)
RAY_ENABLED=false
RAY_HEAD_ADDRESS=ray://10.0.0.1:10001

# Logging
LOG_LEVEL=WARNING
```

---

## Quick Reference

### Configuration Checklist

- [ ] Hetzner API token generated (Read & Write permissions)
- [ ] Token added to `.env.staging` or `.env.production`
- [ ] SSH key pair generated
- [ ] SSH key path configured in environment file
- [ ] `ORCHESTRATOR_ENABLED=true` set
- [ ] File permissions correct (600 for .env, 600 for private key)
- [ ] Orchestrator service restarted
- [ ] Logs verified (no "unauthorized" errors)
- [ ] SSH key uploaded to Hetzner successfully

### Quick Commands

```bash
# Edit staging config
nano /home/deploy/rgrid/.env.staging

# Restart staging orchestrator
sudo systemctl restart orchestrator-staging

# Check status
systemctl status orchestrator-staging

# View logs
journalctl -u orchestrator-staging -f

# Test Hetzner API
curl -H "Authorization: Bearer $HETZNER_API_TOKEN" \
  https://api.hetzner.cloud/v1/servers
```

---

## Related Documentation

- **Deployment Guide**: `docs/DEPLOYMENT_GUIDE.md`
- **Deployment Report**: `docs/TIER4_DEPLOYMENT_REPORT.md`
- **Orchestrator Architecture**: `docs/ARCHITECTURE.md`
- **Worker Provisioning**: `docs/WORKER_PROVISIONING.md` (if exists)

---

**Last Updated**: 2025-11-18
**Applies To**: Tier 4 (Distributed Execution)
**Environments**: Staging, Production
