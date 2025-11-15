# RGrid - Remote Python Script Execution Platform

**Run Python scripts remotely as simply as running them locally.**

```bash
# Works locally
python process_data.py input.json

# Run remotely (same interface, same script)
rgrid run process_data.py input.json

# Run 100x in parallel (same script, no changes)
rgrid run process_data.py --batch inputs/*.json --parallel 10
```

## What is RGrid?

RGrid makes running Python scripts remotely as simple as running them locally. No code refactoring, no SDK integration, no infrastructure management. Just add `rgrid run` before your script command.

**Target users:** Solo developers, SaaS builders, data scientists, automation engineers—anyone who writes Python scripts and needs to scale them without becoming a DevOps engineer.

## Features

- **Zero-friction execution**: Scripts run remotely with identical syntax to local execution
- **No code changes**: Scripts don't need decorators, SDK imports, or refactoring
- **Automatic parallelism**: Run batches of scripts in parallel with simple flags
- **Cost-optimized**: Hetzner-based infrastructure at developer-friendly pricing
- **File handling**: Automatic input upload and output download
- **Dependency management**: Auto-detect and install Python dependencies

## Project Structure

This is a monorepo containing all RGrid components:

- **api/** - FastAPI backend (control plane)
- **orchestrator/** - Auto-scaling service for worker provisioning
- **runner/** - Worker agent that executes scripts in Docker containers
- **cli/** - Python CLI tool (published to PyPI as `rgrid`)
- **console/** - Next.js dashboard for monitoring
- **website/** - Next.js marketing site
- **common/** - Shared Python package for models and types
- **infra/** - Infrastructure as Code (Terraform, Docker, cloud-init)
- **tests/** - Monorepo-wide tests
- **docs/** - Comprehensive documentation

## Quick Start

### Installation

```bash
pip install rgrid
```

### Initialize

```bash
rgrid init
```

### Run a Script

```bash
# Single execution
rgrid run my_script.py input.json

# Batch execution
rgrid run process.py --batch data/*.csv --parallel 10
```

## Development Setup

```bash
# Install dependencies
make setup

# Run tests
make test

# Format code
make format

# Lint code
make lint
```

## Documentation

See the `docs/` directory for comprehensive documentation:

- **docs/PRD.md** - Product Requirements Document
- **docs/architecture.md** - Technical Architecture
- **docs/epics.md** - Epic Breakdown and Stories

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL
- **Distributed Computing**: Ray
- **Container Runtime**: Docker
- **Cloud Provider**: Hetzner
- **CLI**: Click, Rich
- **Web**: Next.js 14+, React 18
- **Auth**: Clerk (web) + API Keys (CLI)
- **Storage**: MinIO (S3-compatible)

## License

[To be determined]

## Contributing

[To be determined]
