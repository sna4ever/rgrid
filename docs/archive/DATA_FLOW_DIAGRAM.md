# RGrid – Data Flow Diagram (Text)

High-level:

Client → API → Postgres ←→ Orchestrator → Hetzner (nodes)
                                 ↑
                                 ↓
                                MinIO
                                 ↑
                                 ↓
                               Runner

Data paths:
- Inputs: Storage → Runner (download) → Container.
- Outputs: Container → Runner (filesystem) → Storage (upload) → API metadata.
- Control: Orchestrator ↔ DB ↔ Runner; Clerk ↔ API.

See SEQUENCE_FLOWS.md for sequence-style diagrams.
