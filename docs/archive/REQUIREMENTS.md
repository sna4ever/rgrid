# RGrid – Requirements

## Functional Requirements

### Core Platform
- FR1: Auth via Clerk (OIDC JWT). All API calls authenticated.
- FR2: Multi-tenant data model (accounts → users → memberships → jobs).
- FR3: Job submission via JSON JobSpec (runtime, command, inputs, outputs, resources, timeout).
- FR4: Persistent queue in Postgres; workers claim jobs with FOR UPDATE SKIP LOCKED.
- FR5: Worker nodes download inputs, run Docker containers, upload outputs to MinIO via presigned URLs.
- FR6: Real-time log streaming and persisted logs.
- FR7: Artifact listing and download via presigned GET URLs.
- FR8: Autoscaling of Hetzner CX22 nodes based on queue depth.
- FR9: Billing/cost tracking in microns (1 EUR = 1,000,000 microns).

### Marketing Website (rgrid.dev)
- FR10: Public landing page with hero, features, and CTA.
- FR11: Features page explaining RGrid benefits and use cases.
- FR12: Pricing page showing transparent per-hour costs.
- FR13: Docs landing page or integration with documentation.
- FR14: Sign-up button redirects to Clerk authentication flow.

### Console Dashboard (app.rgrid.dev)
- FR15: Clerk-authenticated web interface for account members.
- FR16: Jobs list view (status, duration, cost, timestamp).
- FR17: Job detail view (logs, artifacts, execution info).
- FR18: Artifact download via browser (presigned URLs).
- FR19: Account settings (profile, API keys, team members).
- FR20: Billing dashboard (credit balance, usage history, add credits).

## Non-Functional Requirements
- NFR1: Strong isolation (no network by default, read-only root fs, cgroup limits).
- NFR2: Reliability (automatic retry, detection of dead workers, timeouts).
- NFR3: Scalability (hundreds of nodes and thousands of concurrent jobs).
- NFR4: Observability (metrics, logs, node heartbeats).
- NFR5: Maintainability (clear separation of API, orchestrator, runner, website, console).
