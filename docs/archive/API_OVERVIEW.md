# RGrid – API Overview (Condensed)

Auth:
- End users: Clerk JWT in `Authorization: Bearer <token>`.
- Automation: project API keys in `X-RGrid-Key`.

Key endpoints:
- `POST /projects` – create project, return initial API key.
- `POST /projects/:slug/files/upload` – upload input file, returns presigned GET URL (30-120 min expiry).
- `POST /projects/:slug/jobs` – submit JobSpec.
- `GET /jobs/:id` – status, timestamps, retries, artifacts.
- `GET /jobs/:id/logs/stream` – WebSocket log stream.
- `GET /jobs/:id/artifacts` – list artifacts.
- `GET /jobs/:id/artifacts/:artifact_id/download` – presigned GET URL for output download.

Runner/internal:
- `POST /runner/register`
- `POST /runner/claim`
- `POST /runner/heartbeat`
- `POST /runner/executions/:id/finish`
