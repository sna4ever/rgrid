# Worker Operations Guide

This document describes how to operate the RGrid worker and dead worker cleanup daemon (Story NEW-7).

## Overview

RGrid workers send periodic heartbeats to detect when workers crash unexpectedly. A separate cleanup daemon monitors for stale heartbeats and marks jobs from dead workers as failed.

## Components

### 1. Worker Heartbeat

Workers automatically send heartbeats every 30 seconds to the `worker_heartbeats` table in the database.

**Configuration:**
- Heartbeat interval: 30 seconds (hardcoded)
- Worker ID: Auto-generated UUID (8 characters)
- Hostname: Automatically detected

**No additional configuration required** - heartbeats are automatically enabled when the worker starts.

### 2. Dead Worker Cleanup Daemon

The cleanup daemon runs as a separate process and continuously monitors for dead workers.

**How it works:**
1. Every 60 seconds, checks for workers with heartbeats older than 2 minutes
2. Marks all running jobs from dead workers as "failed"
3. Sets error message: "Worker died unexpectedly"

## Running the Cleanup Daemon

### Basic Usage

```bash
# Set environment variables
export DATABASE_URL="postgresql://rgrid:rgrid@localhost/rgrid"

# Run cleanup daemon
python runner/cleanup_daemon.py
```

### Configuration Options

Configure via environment variables:

- **DATABASE_URL** (required): PostgreSQL connection string
- **STALE_THRESHOLD_MINUTES** (default: 2): Minutes without heartbeat to consider worker dead
- **CHECK_INTERVAL** (default: 60): Seconds between cleanup checks

Example with custom configuration:

```bash
export DATABASE_URL="postgresql://rgrid:rgrid@localhost/rgrid"
export STALE_THRESHOLD_MINUTES=3
export CHECK_INTERVAL=30

python runner/cleanup_daemon.py
```

### Running as a Service

For production, run the cleanup daemon as a systemd service:

**Create `/etc/systemd/system/rgrid-cleanup-daemon.service`:**

```ini
[Unit]
Description=RGrid Dead Worker Cleanup Daemon
After=network.target postgresql.service

[Service]
Type=simple
User=rgrid
WorkingDirectory=/opt/rgrid
Environment="DATABASE_URL=postgresql://rgrid:rgrid@localhost/rgrid"
Environment="STALE_THRESHOLD_MINUTES=2"
Environment="CHECK_INTERVAL=60"
ExecStart=/opt/rgrid/venv/bin/python /opt/rgrid/runner/cleanup_daemon.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl enable rgrid-cleanup-daemon
sudo systemctl start rgrid-cleanup-daemon
sudo systemctl status rgrid-cleanup-daemon
```

### Docker Compose

Add to your `docker-compose.yml`:

```yaml
services:
  cleanup-daemon:
    build: ./runner
    command: python cleanup_daemon.py
    environment:
      - DATABASE_URL=postgresql://rgrid:rgrid@postgres/rgrid
      - STALE_THRESHOLD_MINUTES=2
      - CHECK_INTERVAL=60
    depends_on:
      - postgres
    restart: unless-stopped
```

## Monitoring

### Check Daemon Logs

```bash
# If running via systemd
sudo journalctl -u rgrid-cleanup-daemon -f

# If running directly
# Logs go to stdout
```

### Database Queries

**Check worker heartbeats:**

```sql
SELECT worker_id, last_heartbeat_at,
       EXTRACT(EPOCH FROM (NOW() - last_heartbeat_at)) AS seconds_since_heartbeat
FROM worker_heartbeats
ORDER BY last_heartbeat_at DESC;
```

**Find stale workers (>2 minutes):**

```sql
SELECT worker_id, last_heartbeat_at
FROM worker_heartbeats
WHERE last_heartbeat_at < NOW() - INTERVAL '2 minutes';
```

**Check jobs from dead workers:**

```sql
SELECT execution_id, worker_id, status, execution_error
FROM executions
WHERE execution_error = 'Worker died unexpectedly'
ORDER BY created_at DESC
LIMIT 10;
```

## Troubleshooting

### Workers not sending heartbeats

**Symptoms:** No records in `worker_heartbeats` table

**Solution:**
1. Ensure worker is running recent version with heartbeat support
2. Check worker logs for heartbeat errors
3. Verify database connectivity

### Cleanup daemon not detecting dead workers

**Symptoms:** Dead workers not being cleaned up

**Solution:**
1. Check cleanup daemon is running: `ps aux | grep cleanup_daemon`
2. Check daemon logs for errors
3. Verify `STALE_THRESHOLD_MINUTES` configuration
4. Manually query for stale workers (SQL above)

### False positives (healthy workers marked as dead)

**Symptoms:** Running workers marked as dead

**Solution:**
1. Check network latency between worker and database
2. Increase `STALE_THRESHOLD_MINUTES` (e.g., to 3 or 5 minutes)
3. Check for database performance issues

### Jobs not being marked as failed

**Symptoms:** Running jobs stay "running" forever

**Solution:**
1. Ensure cleanup daemon is running
2. Check daemon logs for errors
3. Verify worker heartbeats exist in database
4. Check database permissions for UPDATE on `executions` table

## Testing

### Simulate Worker Death

```bash
# Start worker
python runner/runner/worker.py &
WORKER_PID=$!

# Wait a bit
sleep 10

# Kill worker
kill -9 $WORKER_PID

# Wait for cleanup (2 minutes + check interval)
sleep 180

# Check if jobs marked as failed
psql -U rgrid -d rgrid -c "SELECT execution_id, status, execution_error FROM executions WHERE worker_id LIKE 'worker-%' ORDER BY created_at DESC LIMIT 5;"
```

## Architecture

```
┌─────────────┐                    ┌──────────────┐
│   Worker    │  Heartbeat (30s)   │   Database   │
│             ├───────────────────►│ worker_      │
│  (running   │                    │  heartbeats  │
│   jobs)     │                    └──────┬───────┘
└─────────────┘                           │
                                          │
                                          │ Query stale
                                          │ heartbeats (60s)
                                          │
                                    ┌─────▼────────┐
                                    │   Cleanup    │
                                    │   Daemon     │
                                    │              │
                                    │ Marks jobs   │
                                    │ as failed    │
                                    └──────────────┘
```

## Best Practices

1. **Always run the cleanup daemon in production** - Without it, crashed workers will leave jobs stuck "running" forever

2. **Monitor cleanup daemon uptime** - Use systemd or process monitoring to ensure it's always running

3. **Tune thresholds for your environment:**
   - Fast network: 2 minutes stale threshold is fine
   - Slow/unreliable network: Increase to 3-5 minutes
   - High-frequency checks: Decrease check interval to 30s

4. **Monitor false positives** - If healthy workers are being marked as dead, increase `STALE_THRESHOLD_MINUTES`

5. **Log retention** - Keep cleanup daemon logs for debugging failed job scenarios

## Related Documentation

- [Architecture](./ARCHITECTURE.md) - Overall system architecture
- [Database Schema](./DB_QUEUE.md) - Worker heartbeats table schema
- [Worker Implementation](../runner/runner/worker.py) - Worker daemon code

## Support

For issues or questions, see the RGrid documentation or file a GitHub issue.
