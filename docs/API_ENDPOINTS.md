# RGrid API Endpoints Documentation

**Generated:** 2025-11-22 (STAB-3)
**Purpose:** Deployment verification and reference

## Router Registration (api/app/main.py)

All routers are registered in `api/app/main.py`:

```python
app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(executions_router, prefix="/api/v1", tags=["executions"])
app.include_router(cost_router, prefix="/api/v1", tags=["cost"])
app.include_router(websocket_logs_router, tags=["websocket"])
```

---

## Health Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/health` | Health check with DB status | No |

**Source:** `api/app/api/v1/health.py`

---

## Execution Endpoints

| Method | Endpoint | Description | Auth Required | Story |
|--------|----------|-------------|---------------|-------|
| POST | `/api/v1/executions` | Create new execution | Yes | Core |
| GET | `/api/v1/executions/{execution_id}` | Get execution status | Yes | Core |
| POST | `/api/v1/executions/{execution_id}/retry` | Retry execution | Yes | 10-6 |
| GET | `/api/v1/executions/{execution_id}/artifacts` | List execution artifacts | Yes | 7-5 |
| POST | `/api/v1/artifacts/download-url` | Get presigned download URL | Yes | 7-5 |

**Source:** `api/app/api/v1/executions.py`

---

## Batch Endpoints

| Method | Endpoint | Description | Auth Required | Story |
|--------|----------|-------------|---------------|-------|
| GET | `/api/v1/batches/{batch_id}/status` | Get batch status | Yes | 8-5 |
| GET | `/api/v1/batches/{batch_id}/executions` | List batch executions | Yes | 5-4 |

**Source:** `api/app/api/v1/executions.py`

---

## Cost Endpoints

| Method | Endpoint | Description | Auth Required | Story |
|--------|----------|-------------|---------------|-------|
| GET | `/api/v1/cost` | Get cost breakdown by date | Yes | 9-3 |
| GET | `/api/v1/estimate` | Estimate batch cost | Yes | 9-4 |

**Source:** `api/app/api/v1/cost.py`

---

## WebSocket Endpoints

| Protocol | Endpoint | Description | Story |
|----------|----------|-------------|-------|
| WebSocket | `/ws/executions/{execution_id}/logs` | Real-time log streaming | 8-3 |

**HTTP API for log streaming (runner use):**

| Method | Endpoint | Description | Story |
|--------|----------|-------------|-------|
| POST | `/api/v1/executions/{execution_id}/logs/stream` | Stream log entry | 8-3 |

**Source:** `api/app/websocket/logs.py`

---

## Authentication

All authenticated endpoints require:
- Header: `Authorization: Bearer <API_KEY>`

API keys are validated via `app.api.v1.auth.verify_api_key`

---

## Endpoint Summary by Story

### Tier 5 - File Management
- **7-5**: `GET /executions/{id}/artifacts`, `POST /artifacts/download-url`

### Tier 5 - Batch Management
- **5-4**: `GET /batches/{id}/executions`

### Tier 6 - Monitoring & UX
- **8-3**: `WS /ws/executions/{id}/logs`, `POST /executions/{id}/logs/stream`
- **8-5**: `GET /batches/{id}/status`

### Tier 7 - Cost Tracking
- **9-3**: `GET /cost`
- **9-4**: `GET /estimate`

### Tier 8 - Error Handling
- **10-6**: `POST /executions/{id}/retry`

---

## Deployment Checklist

- [x] All routers imported in main.py
- [x] All routers registered with app.include_router()
- [x] Health endpoint accessible without auth
- [x] Execution endpoints require auth
- [x] Cost endpoints require auth
- [x] WebSocket endpoint for log streaming
- [x] Batch endpoints for progress monitoring

---

## Testing Endpoints

```bash
# Health check (no auth)
curl https://staging.rgrid.dev/api/v1/health

# Authenticated request example
curl -H "Authorization: Bearer $API_KEY" \
  https://staging.rgrid.dev/api/v1/cost

# Cost estimate
curl -H "Authorization: Bearer $API_KEY" \
  "https://staging.rgrid.dev/api/v1/estimate?runtime=python:3.11&files=100"
```

---

## Notes

1. All endpoints are registered correctly in main.py
2. WebSocket logs endpoint uses `/ws/` prefix (not `/api/v1/`)
3. Log streaming POST endpoint is under the websocket router but uses HTTP
4. No missing routers detected - all new features have working endpoints
