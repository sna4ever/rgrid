# RGrid – Tenancy & Auth (Clerk)

Identity:
- Clerk manages users and organizations (accounts).
- FastAPI validates JWT tokens, maps `sub` → `users.external_user_id`, `org_id` → `accounts.external_org_id`.

Data model:
- `accounts` (tenants)
- `users` (linked to Clerk users)
- `memberships` (user/account roles)
- `projects` (belong to one account)
- `jobs` (belong to one project)

Roles:
- `owner`, `admin`, `developer`, `viewer` at account/project level.

Nodes:
- Authenticate using node tokens; restricted to internal APIs only.

Storage:
- Path-based isolation plus MinIO bucket policies ensures one tenant cannot see another tenant’s artifacts.
