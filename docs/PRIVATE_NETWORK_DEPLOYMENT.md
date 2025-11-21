# Hetzner Private Network Deployment Guide

**Security Architecture**: Worker-to-Database communication via isolated private VLAN

## Overview

This guide walks through deploying RGrid with secure private network connectivity between workers and the database server. Workers communicate with the database over Hetzner's private network (10.0.1.0/24), eliminating the need to expose PostgreSQL to the internet.

## Implementation Summary

### Code Changes (✅ Complete)

1. **HetznerClient** (`orchestrator/hetzner_client.py`):
   - Added `create_network()` - Create private networks
   - Added `get_networks()` - List existing networks
   - Added `attach_server_to_network()` - Attach servers to networks
   - Updated `create_server()` - Support network parameter

2. **WorkerProvisioner** (`orchestrator/provisioner.py`):
   - Added `network_id` and `private_db_ip` parameters
   - Workers automatically added to private network during provisioning
   - DATABASE_URL uses private IP (10.0.1.2) instead of public IP

3. **OrchestratorDaemon** (`orchestrator/daemon.py`):
   - Reads `RGRID_NETWORK_ID` and `RGRID_PRIVATE_DB_IP` from environment
   - Passes network config to provisioner

4. **Setup Script** (`scripts/setup_private_network.py`):
   - One-time network creation
   - Staging server attachment
   - Outputs configuration values

## Deployment Steps

### Step 1: Create Private Network

Run the setup script to create the Hetzner private network and attach the staging server:

```bash
cd /home/sune/Projects/rgrid

# Set Hetzner API token
export HETZNER_API_TOKEN="your_token_here"

# Run setup script
python3 scripts/setup_private_network.py
```

**Expected Output:**
```
=== RGrid Private Network Setup ===

Step 1: Checking for existing network...
Creating network 'rgrid-private'...
✓ Network created successfully!
  Network ID: 12345678
  IP Range: 10.0.0.0/16

Step 2: Finding staging server...
✓ Found staging server: rgrid (ID: 87654321)

Step 3: Attaching staging server to private network...
✓ Server attached to network
  Private IP: 10.0.1.2

==================================================
SETUP COMPLETE!
==================================================

Network Configuration:
  Network ID: 12345678
  Network Name: rgrid-private
  IP Range: 10.0.0.0/16
  Subnet: 10.0.1.0/24

Staging Server:
  Server ID: 87654321
  Server Name: rgrid
  Private IP: 10.0.1.2
```

**Save these values** - you'll need them in Step 3!

### Step 2: Configure PostgreSQL (on Staging Server)

SSH into the staging server and configure PostgreSQL to listen on the private network interface:

```bash
# SSH to staging server
ssh deploy@46.62.246.120

# Edit PostgreSQL config
sudo nano /etc/postgresql/*/main/postgresql.conf
```

**Update listen_addresses:**
```ini
# Change this line:
listen_addresses = 'localhost'

# To this:
listen_addresses = 'localhost,10.0.1.2'
```

**Update pg_hba.conf** to allow private network connections:
```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

**Add this line** (above the "local" entries):
```
# RGrid workers via private network
host    rgrid_staging    rgrid_staging    10.0.1.0/24    md5
```

**Restart PostgreSQL:**
```bash
sudo systemctl restart postgresql

# Verify it's listening on private IP
sudo ss -tlnp | grep 5433
```

**Expected output:**
```
LISTEN  0  200  127.0.0.1:5433  0.0.0.0:*  users:(("postgres",pid=...))
LISTEN  0  200  10.0.1.2:5433   0.0.0.0:*  users:(("postgres",pid=...))
```

### Step 3: Update Orchestrator Environment

SSH to staging server and update the orchestrator environment variables:

```bash
ssh deploy@46.62.246.120

# Edit orchestrator environment file
sudo nano /etc/rgrid/orchestrator.env
```

**Add these lines** (using values from Step 1):
```bash
# Hetzner Private Network Configuration
RGRID_NETWORK_ID=12345678           # From setup script output
RGRID_PRIVATE_DB_IP=10.0.1.2        # From setup script output
```

**Restart orchestrator:**
```bash
sudo systemctl restart orchestrator-staging
sudo journalctl -u orchestrator-staging -f
```

**Verify private network is enabled** in the logs:
```
Private network enabled (Network ID: 12345678, DB IP: 10.0.1.2)
```

### Step 4: Commit and Deploy Code Changes

```bash
# From your local machine
cd /home/sune/Projects/rgrid

# Stage all changes
git add orchestrator/hetzner_client.py
git add orchestrator/provisioner.py
git add orchestrator/daemon.py
git add scripts/setup_private_network.py
git add docs/PRIVATE_NETWORK_DEPLOYMENT.md

# Commit
git commit -m "feat: Add Hetzner private network support for secure worker-database communication

- Add network methods to HetznerClient (create, list, attach)
- Update provisioner to add workers to private network
- Workers use private IP (10.0.1.2) for database access
- Add setup script for one-time network creation
- PostgreSQL no longer needs internet exposure

Security: Workers communicate over isolated private VLAN (10.0.1.0/24)"

# Push to GitHub
git push
```

### Step 5: Test End-to-End

**Submit a test job:**
```bash
# From local machine
curl -X POST "http://46.62.246.120:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @/tmp/test_job.json
```

**Monitor orchestrator logs:**
```bash
ssh deploy@46.62.246.120 "sudo journalctl -u orchestrator-staging -f"
```

**Look for these indicators of success:**
```
✅ Using private network IP for database: 10.0.1.2
✅ Worker worker-XXXXX provisioned successfully
✅ Worker became active (status transition: provisioning → active)
✅ Job claimed by worker
✅ Job completed successfully
```

**Verify worker is on private network:**
```bash
# From staging server
ssh deploy@46.62.246.120

# Check Hetzner servers
curl -H "Authorization: Bearer $HETZNER_API_TOKEN" \
  "https://api.hetzner.cloud/v1/servers" | jq '.servers[] | {name, networks}'
```

**Expected output:**
```json
{
  "name": "rgrid-worker-XXXXX",
  "networks": [12345678]
}
```

## Architecture Diagram

```
┌────────────────────────────────────────────────┐
│         Hetzner Private Network                │
│           10.0.1.0/24 (RFC 1918)              │
│                                                │
│  ┌──────────────┐        ┌─────────────┐     │
│  │ Staging      │        │  Worker 1   │     │
│  │ Server       │◄──────►│  10.0.1.3   │     │
│  │ 10.0.1.2     │        └─────────────┘     │
│  │              │                             │
│  │ PostgreSQL   │        ┌─────────────┐     │
│  │ :5433        │◄──────►│  Worker 2   │     │
│  └──────────────┘        │  10.0.1.4   │     │
│                          └─────────────┘     │
└────────────────────────────────────────────────┘
        ▲
        │ NO INTERNET EXPOSURE
        │ Database traffic stays within Hetzner private VLAN
```

## Security Benefits

✅ **Zero Internet Exposure**: PostgreSQL never listens on public interface
✅ **Network Isolation**: Workers and database on isolated private VLAN
✅ **Automatic Security**: No firewall rules needed - network-level isolation
✅ **No TLS Overhead**: Private network is already encrypted by Hetzner
✅ **Attack Surface Reduced**: Database unreachable from internet

## IP Address Allocation

| IP Address | Purpose |
|-----------|---------|
| 10.0.1.1 | Reserved (network) |
| 10.0.1.2 | Staging server (database) |
| 10.0.1.3+ | Auto-assigned to workers |
| 10.0.1.254 | Reserved (broadcast) |

Workers are automatically assigned IPs starting from 10.0.1.3 by Hetzner.

## Troubleshooting

### Workers still trying public IP

**Symptom**: Logs show `Using public IP for database`

**Fix**: Ensure environment variables are set:
```bash
ssh deploy@46.62.246.120 "sudo cat /etc/rgrid/orchestrator.env | grep RGRID"
```

Should show:
```
RGRID_NETWORK_ID=12345678
RGRID_PRIVATE_DB_IP=10.0.1.2
```

### Workers timeout on database connection

**Symptom**: Workers provision but never become active

**Check PostgreSQL is listening on private IP:**
```bash
ssh deploy@46.62.246.120 "sudo ss -tlnp | grep 10.0.1.2:5433"
```

**Check pg_hba.conf allows private network:**
```bash
ssh deploy@46.62.246.120 "sudo grep '10.0.1.0/24' /etc/postgresql/*/main/pg_hba.conf"
```

### Network not attached to worker

**Symptom**: Worker has no private IP

**Verify network ID is correct:**
```bash
ssh deploy@46.62.246.120 "cat /etc/rgrid/orchestrator.env | grep RGRID_NETWORK_ID"
```

**Check Hetzner network exists:**
```bash
curl -H "Authorization: Bearer $HETZNER_API_TOKEN" \
  "https://api.hetzner.cloud/v1/networks"
```

## Rollback Procedure

If you need to rollback to public IP access:

1. **Unset environment variables:**
   ```bash
   ssh deploy@46.62.246.120
   sudo nano /etc/rgrid/orchestrator.env
   # Comment out RGRID_NETWORK_ID and RGRID_PRIVATE_DB_IP
   ```

2. **Restart orchestrator:**
   ```bash
   sudo systemctl restart orchestrator-staging
   ```

3. **Configure PostgreSQL for public access:**
   ```bash
   sudo nano /etc/postgresql/*/main/postgresql.conf
   # listen_addresses = 'localhost,46.62.246.120'

   sudo nano /etc/postgresql/*/main/pg_hba.conf
   # host    rgrid_staging    rgrid_staging    46.0.0.0/8    md5

   sudo systemctl restart postgresql
   ```

## Cost

Hetzner Private Networks are **FREE** - no additional cost for using this feature!

## Next Steps

After successful deployment:

1. Monitor worker provisioning for 24 hours
2. Verify all jobs execute successfully via private network
3. Remove any public PostgreSQL firewall rules (defense in depth)
4. Document private IP in runbooks
5. Consider expanding private network for other services (MinIO, etc.)

## Support

If you encounter issues:
- Check orchestrator logs: `sudo journalctl -u orchestrator-staging -f`
- Check PostgreSQL logs: `sudo journalctl -u postgresql -f`
- Verify network with Hetzner API
- Review this guide's troubleshooting section
