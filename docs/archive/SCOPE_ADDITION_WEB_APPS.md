# Scope Addition: Web Applications

**Date:** 2025-11-15
**Phase:** Architecture (before epic breakdown)
**Status:** Approved and integrated into architecture

---

## Summary

Added two Next.js web applications to the monorepo to complete the user-facing product:

1. **Marketing Website** (`website/`) - Public landing page at `rgrid.dev`
2. **Console Dashboard** (`console/`) - Authenticated web UI at `app.rgrid.dev`

## Rationale

- **Marketing Website**: Required for product launch, user acquisition, and onboarding
- **Console Dashboard**: Provides web access for non-technical users and teams who prefer GUI over CLI
- **Low Traffic**: Both apps can run on existing CX31 control plane (~2GB RAM total)
- **Monorepo Benefits**: Shared Tailwind config, TypeScript types, component library

## Architecture Changes

### Monorepo Structure
Added two new folders:
- `website/` - Next.js 14+ (App Router) marketing site
- `console/` - Next.js 14+ (App Router) dashboard with Clerk auth

### Deployment (Control Plane)
- **Nginx routing** for three domains:
  - `rgrid.dev` → website:3000
  - `app.rgrid.dev` → console:3000
  - `api.rgrid.dev` → api:8000
- **Docker Compose** updated with website and console services
- **SSL** via certbot for all three domains

### Technology Stack
Added:
- **Web Framework:** Next.js 14+ (App Router)
- **Reverse Proxy:** Nginx

## MVP Scope for Each

### Marketing Website (Simple)
- Landing page (hero, features, CTA)
- Features page
- Pricing page
- Docs landing (or link to external docs)
- Sign up → redirects to Clerk → console

### Console Dashboard (Minimal)
- Jobs list (status, duration, cost)
- Job details (logs, artifacts, download)
- Account settings (API keys, profile)
- Billing (credit balance, add credits, usage history)
- Clerk authentication wrapper

## Cost Impact

**No additional infrastructure cost:**
- CX31 (8GB RAM) already provisioned
- Website + Console use ~2GB RAM combined
- Low traffic expected for MVP
- Can scale to separate hosting later if needed

## Implementation Impact

### New Epics/Stories Required
- Epic: Marketing Website
  - Story: Landing page
  - Story: Features page
  - Story: Pricing page
  - Story: Docs integration
- Epic: Console Dashboard
  - Story: Authentication (Clerk setup)
  - Story: Jobs list and details
  - Story: Settings and API keys
  - Story: Billing and credits

### Dependencies
- **Clerk**: Account creation, sign-up flow
- **FastAPI**: Console calls API endpoints for data
- **Shared components**: Both apps can share UI components

## Files Updated

- ✅ `docs/architecture.md` - Added website/ and console/ to monorepo structure
- ✅ `docs/architecture.md` - Added docker-compose services for both apps
- ✅ `docs/architecture.md` - Added Nginx routing configuration
- ✅ `docs/architecture.md` - Updated technology stack
- ✅ `docs/ARCHITECTURE_SUMMARY.md` - Updated Decision 1 and deployment section

---

**Approved by:** User
**Integrated into:** Architecture v1.0
**Next Step:** Proceed to epic breakdown with web apps included in scope
