# rgrid - Product Requirements Document

**Author:** BMad
**Date:** 2025-11-14
**Version:** 3.0 - SCRIPT EXECUTION SERVICE MODEL

---

## Executive Summary

**RGrid makes running Python scripts remotely as simple as running them locally.**

Born from a solo developer's frustration with the gap between "this script works on my laptop" and "now I need to run it 100 times in parallel on real hardware," RGrid eliminates the complexity of distributed execution. You have a Python script. It works locally. Run it remotely with the exact same interface—no refactoring, no SDK integration, no infrastructure management.

The paradigm shift: **Your scripts don't change. Just the execution location.**

**Target users:** Solo developers, SaaS builders, data scientists, automation engineers—anyone who writes Python scripts and needs to scale them without becoming a DevOps engineer. You write scripts for local testing, RGrid runs them at scale.

**The "TikTok swipe" moment:**
```bash
# Works locally
python process_data.py input.json

# Run remotely (same interface, same script)
rgrid run process_data.py input.json

# Run 100x in parallel (same script, no changes)
rgrid run process_data.py --batch inputs/*.json --parallel 10
```

No decorators. No SDK imports. No code refactoring. Just: **Run your script. Anywhere. At scale.**

### What Makes This Special

**Zero-friction remote execution + Script-first design + Hetzner-level pricing.**

While AWS Batch requires infrastructure expertise, Modal requires code refactoring, and serverless requires rearchitecting, RGrid takes a fundamentally different approach: **Your scripts are first-class citizens.** Write them once for local execution, run them remotely with a single command. The script doesn't know it's distributed. You don't manage infrastructure. It just works.

The compelling moment: A developer writes a data processing script with local test data. It works. They need to process 1000 files. Instead of refactoring for AWS Lambda or learning Kubernetes, they run: `rgrid run process.py --batch files/*.csv --parallel 50`. Done. Cost: pennies. Time: minutes.

**Core insight:** Most developers don't need distributed computing frameworks. They need **"run this script over there, many times, in parallel."**

---

## Project Classification

**Technical Type:** Developer Tool / Script Execution Platform / CLI-First Service
**Domain:** General Software (Developer Infrastructure)
**Complexity:** Low (domain) / Medium-High (technical execution)

RGrid is a script execution platform that makes remote and parallel execution accessible via CLI. It's an execution layer over battle-tested tools (Ray for distribution, Hetzner for compute) that makes running scripts remotely feel identical to running them locally.

**Primary interface:** CLI (`rgrid run script.py`)
**Secondary interface:** Web console (for monitoring, non-technical users)
**Future interfaces:** GitHub Actions integration, Markdown execution blocks, web UI for script invocation, API for programmatic access

**Architecture philosophy:**
- Scripts are first-class entities (not functions)
- No code changes required (scripts run as-is)
- File-based I/O (conventional input/output paths)
- CLI-first design (web UI is secondary)
- **Execution Model Abstraction Layer (EMA):** Ray powers MVP, but orchestration is pluggable (Temporal, Inngest, Kubernetes, serverless, or custom) without interface changes
- **Cloud Provider Abstraction Layer (CPAL):** Hetzner is default MVP provider, but AWS, GCP, Fly.io, and BYOC integration is possible without CLI changes
- **Runtime Plugin Architecture:** Runtimes follow a pluggable architecture allowing future types (GPU images, custom environments, language-specific runtimes) to be added without breaking changes

**Competitive positioning:**
- **vs AWS Batch:** 100x simpler (CLI vs CloudFormation), comparable cost
- **vs Modal:** No code refactoring required, 50-70% cheaper, script-first vs function-first
- **vs Replicate:** General-purpose scripts (not just ML models), simpler pricing
- **vs DIY (cron + EC2):** Zero infrastructure management, automatic parallelism, instant scalability
- **vs Fly Machines:** Convenience layer over infrastructure primitives (see detailed analysis below)

---

## Design Philosophy: "Dropbox Simplicity for Developers"

RGrid follows a **convention-over-configuration** design philosophy inspired by tools that "just work" — Dropbox, Git, Next.js. The goal is zero-config for 90% of use cases, with invisible intelligence making the right decisions automatically.

### Core Principles

**1. The Best Interface is No Interface**
- No config files for basic usage
- No CLI flags for common operations
- Scripts run remotely with identical syntax to local execution
- Example: `python script.py` → `rgrid run script.py` (literally add "rgrid run")

**2. Convention Over Configuration**
- Smart defaults for everything (runtime, region, parallelism, caching)
- Auto-detection of dependencies (requirements.txt)
- Conventional output locations (current directory or `./outputs/`)
- Only deviate from conventions when explicitly needed

**3. Invisible Intelligence**
- Aggressive caching (scripts, dependencies, inputs) using content hashing
- Automatic optimization (worker scaling, cost reduction)
- Silent error recovery (transient failures auto-retry)
- Users see "it just works" — don't see the complexity beneath

**4. Progressive Disclosure**
- Core command: `rgrid run script.py` (90% of usage)
- Optional flags for power users (`--runtime`, `--parallel`, `--env`)
- Advanced features available but not required (upload, workflows, scheduling)
- Learning curve: 30 seconds for basic usage, weeks to master advanced features

**5. Zero Learning Curve**
- If you know how to run a Python script locally, you know RGrid
- Identical command-line interface (arguments, input files, outputs)
- Familiar concepts (scripts, files, exit codes — not jobs, tasks, executions)

### Design Inspirations

**Dropbox:**
- Install → background process → just works
- No config files, no "sync" commands
- Convention: One folder, files appear automatically

**Git:**
- `git init` → invisible .git/ folder
- `git add` → knows what "changed" means
- Convention: Working directory, staging, commits

**Next.js:**
- `pages/` folder → automatic routing
- No route config required
- Convention: Filename = URL path

**What RGrid Learns:**
- `rgrid init` → invisible credentials at `~/.rgrid/credentials`
- `rgrid run` → knows what to cache, what to upload, what to execute
- Convention: Script in current directory, outputs appear locally

### The 90/10 Rule

**90% of executions use ZERO optional flags:**
```bash
rgrid run script.py input.json
```

**10% use optional power-user features:**
```bash
rgrid run script.py --batch inputs/*.csv --runtime python:3.11-datascience --parallel 50
```

**Design for the 90%, don't force configuration on everyone.**

### Conventions (Defaults that "Just Work")

| Aspect | Convention | Override (if needed) |
|--------|-----------|---------------------|
| **Authentication** | `~/.rgrid/credentials` (global, set once) | N/A (always global) |
| **Runtime** | `python:3.11` (auto-detect from .py extension) | `--runtime python:3.10` |
| **Dependencies** | Auto-detect `requirements.txt` in script dir | `--requirements deps.txt` |
| **Input files** | Command-line arguments (same as local) | N/A (convention only) |
| **Output location** | Current directory (single execution) | `--output-dir results/` |
| **Batch outputs** | `./outputs/<input-name>/` directory structure | `--flat` (all in one dir) |
| **Parallelism** | Auto-scale to batch size (max 10 by default) | `--parallel 50` |
| **Region** | Cheapest available (Hetzner EU initially) | `--region us-east` |
| **Retry policy** | Auto-retry transient failures (2x) | `--no-retry` |
| **Caching** | Aggressive (scripts, deps, inputs hashed) | `--no-cache` |

**Result:** Most users run `rgrid run script.py` and never learn about any flags.

### Three-Level Invisible Caching

**All caching is invisible to the user. Scripts just feel fast after first run.**

**Level 1: Script Cache (content hashing)**
```python
script_hash = sha256(script_content)
if script_hash in cache:
    use_cached_image()  # Instant
else:
    build_image()       # 30s first time
    cache[script_hash] = image
```
- First run: 30s (build)
- Every subsequent identical run: instant
- Change one line: new hash → rebuild
- **User sees:** "It's fast"

**Level 2: Dependency Cache (requirements.txt hashing)**
```python
deps_hash = sha256(requirements_content)
if deps_hash in cache:
    use_cached_layer()  # Instant
else:
    pip_install()       # 60s first time
    cache[deps_hash] = layer
```
- First run with new deps: 60s
- Same deps forever after: instant
- Change pandas version: new hash → rebuild
- **User sees:** "It's fast after first time"

**Level 3: Input File Cache (optional, for identical inputs)**
```python
input_hash = sha256(input_content)
if input_hash in cache and not stale:
    skip_upload()  # Instant
else:
    upload_file()  # 2-5s
```
- Reprocessing same file: skip upload
- **User sees:** "No upload delay"

**Cache Invalidation:**
- Script changed: New hash → rebuild (automatic)
- Dependencies changed: New hash → rebuild (automatic)
- Cache miss: Transparent fallback to build/install
- **User never thinks about cache**

### The One-Sentence Explanation Test

**If you can't explain it in one sentence, it's too complex.**

**RGrid in one sentence:**
> "It's like running Python locally, but on 100 cloud servers in parallel."

**Dropbox in one sentence:**
> "It's a folder that syncs across your devices."

**Git in one sentence:**
> "It saves snapshots of your code over time."

**Simplicity is clarity.**

---

## Competitive Analysis: RGrid vs Infrastructure Primitives

**Question: "Can this compete with Fly Machines? Could users not just create a Fly machine and send their Python script there?"**

**Short Answer: Yes, they could. But that's like saying "Why use Vercel when you can just use EC2?"**

RGrid is a **convenience layer over infrastructure primitives** like Fly Machines, Hetzner nodes, or AWS EC2. The value proposition is not "we have better infrastructure" — it's **"we eliminate the complexity between your script and distributed execution."**

### The Value Stack

**Infrastructure Primitives (Fly Machines, EC2, Hetzner API):**
- Create VM
- Configure networking
- Install dependencies
- Upload code
- Execute
- Handle failures
- Download results
- Tear down
- Pay for all of it

**RGrid:**
```bash
rgrid run script.py --batch data/*.csv --parallel 50
```

### Detailed Comparison: RGrid vs Fly Machines

| Task | Fly Machines (DIY) | RGrid |
|------|-------------------|-------|
| **Create execution environment** | Write Dockerfile, build image, push to registry | Auto-detect runtime from `.py` extension |
| **Provision infrastructure** | `fly machine run --region ord --size shared-cpu-1x` | Automatic based on queue depth |
| **Upload script & dependencies** | Package in Docker image or rsync to machine | Automatic with content-hash caching |
| **Distribute batch workload** | Write custom orchestration logic (queue, workers, etc.) | `--batch data/*.csv --parallel 50` |
| **Monitor progress** | Poll Fly API, parse logs manually | `rgrid status` with real-time progress |
| **Handle failures** | Write retry logic, detect crashed machines | Automatic retry with transient failure detection |
| **Collect outputs** | SCP files back, parse results | Automatic download to `./outputs/` |
| **Clean up infrastructure** | `fly machine destroy` (or pay forever) | Automatic worker termination after 60min |
| **Cost tracking** | Parse Fly bill, calculate per-job costs | `rgrid cost` with per-execution breakdown |
| **Parallelism** | Write custom task queue + worker pool | Built-in via Ray |
| **Batch execution** | Write for-loop + manage worker pool | Single `--batch` flag |

**Time to first execution:**
- **Fly Machines DIY:** 30-60 minutes (write Dockerfile, provision, configure, debug)
- **RGrid:** 30 seconds (`rgrid init` once, then `rgrid run script.py`)

### The "EC2 vs Vercel" Analogy

**You CAN deploy a Next.js app on EC2:**
1. Provision EC2 instance
2. Install Node.js
3. Configure nginx
4. Set up SSL certificates
5. Configure DNS
6. Write systemd service
7. Set up log rotation
8. Configure auto-scaling
9. Set up monitoring
10. Manage updates

**Or you can use Vercel:**
```bash
vercel deploy
```

**RGrid is to Fly Machines what Vercel is to EC2.**

### What RGrid Actually Does

RGrid is **developer-facing orchestration** over infrastructure-level primitives:

**Layer 1: Infrastructure (Fly, Hetzner, AWS)**
- Provides: VMs, networking, storage
- User sees: None of this

**Layer 2: Orchestration (Ray, Temporal, Kubernetes)**
- Provides: Task distribution, scheduling, execution
- User sees: None of this

**Layer 3: RGrid (Convenience + DX)**
- Provides: `rgrid run script.py --batch *.csv`
- User sees: **THIS**

### Why Not Just Use Fly Machines Directly?

**Answer: For the same reason developers use Vercel instead of EC2, Railway instead of bare Kubernetes, or GitHub Actions instead of Jenkins on a VM.**

**Fly Machines are excellent infrastructure.** RGrid could even use Fly Machines as a cloud provider backend (via CPAL abstraction). The question isn't "Fly vs RGrid" — it's:

> **"Do I want to manage infrastructure, or do I want to run my script 100 times in parallel?"**

### Real-World Workflow Comparison

**User wants to process 1000 images with FFmpeg:**

**With Fly Machines:**
```bash
# 1. Write Dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y ffmpeg python3
COPY process_image.py /app/
WORKDIR /app

# 2. Build and push image
docker build -t my-ffmpeg .
fly deploy --image my-ffmpeg

# 3. Write orchestration script
for file in images/*.png; do
  fly machine run my-ffmpeg python3 /app/process_image.py $file
done

# 4. Wait for all machines to complete (manual polling)
# 5. Download outputs from each machine (manual scripting)
# 6. Destroy machines (manual cleanup)
# 7. Calculate costs (parse Fly bill)
```

**With RGrid:**
```bash
rgrid run process_image.py --batch images/*.png --runtime ffmpeg:latest --parallel 50
```

**Same infrastructure underneath. 100x simpler interface.**

### Strategic Positioning

**RGrid is not competing with Fly Machines.** RGrid could **use** Fly Machines as a compute backend.

**Competitive set:**
- **Direct competitors:** Modal, Replicate, AWS Batch (script/task execution platforms)
- **Infrastructure partners:** Fly.io, Hetzner, AWS, GCP (compute providers)
- **Inspiration:** Vercel, Railway, Render (DX-first infrastructure)

**Business model compatibility:**
- Hetzner MVP: Direct compute provider relationship
- Future multi-cloud: Use Fly.io, AWS, GCP via CPAL abstraction
- Enterprise BYOC: Use customer's Fly.io account for execution

### The Wedge Strategy

**Phase 1 (MVP):** Script execution is stupid simple
- Target: Solo developers frustrated with infrastructure
- Value prop: `python script.py` → `rgrid run script.py`

**Phase 2 (Growth):** Workflow orchestration
- Target: Teams with complex pipelines
- Value prop: Multi-step DAGs, scheduling, dependencies

**Phase 3 (Scale):** Developer platform
- Target: Companies building on RGrid
- Value prop: API, webhooks, integrations, marketplace

**Throughout all phases: Infrastructure (Fly, Hetzner, AWS) is abstracted away.**

### Why This Wins

**Developers don't want to think about:**
- VMs
- Networking
- Load balancers
- Kubernetes
- Docker registries
- IAM roles
- Security groups

**Developers want:**
```bash
rgrid run my_script.py --batch data/*.json --parallel 100
```

**That's the wedge. That's why RGrid exists.**

---

## Success Criteria

Success means RGrid becomes the **default choice** for script execution at scale — the tool developers reach for instinctively when they need to run a script more than once or on bigger hardware.

### Primary Success Indicators (MVP Validation)

1. **Time to First Execution < 3 minutes**
   - From `brew install rgrid` or `pip install rgrid-cli` to running first script remotely
   - Including auth setup
   - Target: 2 minutes for experienced developers

2. **Personal Utility Proof**
   - RGrid actively used for 3+ real workloads within 8 weeks
   - Replaced local batch scripts or manual server SSH
   - Real workloads: data processing, image conversion, LLM batch inference, web scraping

3. **Zero Refactoring Required**
   - Scripts that work locally work remotely without modification
   - 100% success rate for scripts following basic conventions (read files, write files, exit codes)

4. **Cost Efficiency Delivered**
   - Running parallel workloads costs ≤50% of AWS Lambda for equivalent compute
   - Cost transparency: developers understand billing without surprises
   - Target: < $0.10 per 1000 script executions (assuming 30s average runtime)

5. **Interface Simplicity**
   - Local command: `python script.py input.json`
   - Remote command: `rgrid run script.py input.json`
   - Parallelism: `rgrid run script.py --batch inputs/*.json`
   - Developers describe experience as "obvious" or "just like running locally"

### Secondary Indicators (Growth Validation)

6. **Adoption Beyond Creator**
   - If shared: 10+ developers successfully run their own scripts
   - Positive DX feedback (GitHub stars, testimonials, Twitter mentions)

7. **Use Case Diversity**
   - Works for: data transformation, ffmpeg/image processing, LLM batch inference, web scraping, ETL, automation scripts
   - Developers use it for problems beyond initial examples

8. **Performance Perception**
   - Parallel execution perceived as "significantly faster" than local sequential
   - Overhead acceptable (cold start < 30s doesn't block usage)

### What Success Looks Like (Qualitative)

A developer writes a script to process data. It works on 10 test files. Now they have 10,000 files. They:
1. Run: `rgrid run process.py --batch data/*.csv --parallel 100`
2. See progress in terminal
3. Get all results back
4. Pay < $5
5. Never SSH'd into a server or wrote a Dockerfile

That's the paradigm shift working.

### Anti-goals

- **NOT** replacing application deployment (use Vercel, Fly.io for that)
- **NOT** long-running services (this is for batch/parallel scripts)
- **NOT** sub-second latency execution (this is for batch jobs, not real-time API)
- **NOT** competing with Airflow/Dagster for complex DAG orchestration (yet)
- **NOT** requiring users to learn Ray, Docker, or cloud providers

---

## Product Scope

### MVP - Minimum Viable Product

**Core Philosophy:** Ship the paradigm shift. Prove that "run script locally → run script remotely" with zero code changes is viable and valuable.

#### The Developer Experience

**Setup (< 1 minute):**
```bash
brew install rgrid  # or pip install rgrid-cli
rgrid init  # Handles auth, generates API key, creates config
```

**Usage (identical to local execution):**
```bash
# Your script works locally
python process_data.py input.csv

# Run it remotely (same interface)
rgrid run process_data.py input.csv

# Run in parallel across multiple inputs
rgrid run process_data.py --batch inputs/*.csv --parallel 10

# Specify runtime if needed
rgrid run process_data.py input.csv --runtime python:3.11

# Monitor progress
rgrid status <execution-id>

# Get logs
rgrid logs <execution-id>

# Download outputs
rgrid download <execution-id> ./outputs/
```

**What just happened (invisible to user):**
- RGrid uploaded your script
- Detected dependencies (requirements.txt if present)
- Spun up Hetzner workers with Python runtime
- Uploaded input files
- Executed script in isolated container
- Collected outputs
- Returned results
- Cleaned up workers

#### MVP Feature Set

**1. CLI - The Primary Interface**

**Philosophy: Minimal core commands, 90% of usage with one command**

**Essential Commands (4 total - covers 95% of usage):**
- `rgrid init` - First-time setup and authentication (once ever)
- `rgrid run <script> [args]` - Execute script remotely (90% of usage)
- `rgrid logs <execution-id>` - View logs when debugging
- `rgrid cost` - Monthly billing check

**Optional Commands (power users):**
- `rgrid status [execution-id]` - Check detailed execution status
- `rgrid download <execution-id> <dest>` - Download outputs (usually automatic)
- `rgrid list` - List recent executions
- `rgrid retry <execution-id>` - Retry failed execution
- `rgrid cancel <execution-id>` - Cancel running execution

**90% of users only ever use: `rgrid init` (once) and `rgrid run` (always)**

**Run command options:**
```bash
rgrid run script.py [args] [options]

Options:
  --runtime <image>       Docker runtime (default: python:3.11)
  --batch <pattern>       Run script for each file matching pattern
  --parallel <n>          Max parallel executions (default: 10)
  --cpu <n>               CPU cores per execution (default: 1)
  --memory <size>         Memory per execution (default: 2Gi)
  --timeout <seconds>     Max execution time (default: 300)
  --env KEY=VALUE         Environment variables
  --requirements <file>   Python requirements file
  --watch                 Stream logs in real-time
```

**2. Script Execution Model**

**File-based I/O convention:**
```python
# Your script follows a simple convention
import sys
import json

# Read input from argument or stdin
input_file = sys.argv[1]  # e.g., "input.json"
with open(input_file) as f:
    data = json.load(f)

# Process
result = process(data)

# Write output to conventional location
with open('output.json', 'w') as f:
    json.dump(result, f)

# Exit code indicates success/failure
sys.exit(0)  # Success
```

**RGrid conventions:**
- Script receives input files as arguments (same as local)
- Script writes outputs to current directory
- RGrid collects all files created in working directory
- Exit code 0 = success, non-zero = failure
- Stdout/stderr captured as logs

**3. Dependency Management**

**Automatic detection:**
```bash
# RGrid detects requirements.txt in same directory as script
project/
  process.py
  requirements.txt  # Installed automatically

# Run without specifying dependencies
rgrid run process.py input.json
```

**Explicit requirements:**
```bash
# Specify requirements file
rgrid run script.py input.json --requirements deps.txt
```

**Pre-baked runtimes:**
```bash
# Use runtime with common packages pre-installed
rgrid run script.py input.json --runtime python:3.11-datascience
# Includes: numpy, pandas, scikit-learn, matplotlib

rgrid run script.py input.json --runtime python:3.11-llm
# Includes: openai, anthropic, langchain, requests
```

**4. Batch Execution & Parallelism**

**Pattern matching:**
```bash
# Process all CSV files in parallel
rgrid run process.py --batch data/*.csv --parallel 20

# Process numbered files
rgrid run process.py --batch inputs/file_{1..100}.json --parallel 50
```

**How it works:**
- RGrid expands the pattern
- Creates one execution per file
- Distributes across workers (up to --parallel limit)
- Each execution runs script with one input file
- Returns all outputs when complete

**Progress tracking:**
```bash
rgrid run process.py --batch data/*.csv --parallel 10 --watch

Output:
> Starting batch execution: 100 files, 10 parallel
> [====>    ] 45/100 complete (3 failed, 52 running/queued)
> Estimated completion: 2m 15s
```

**5. Runtime Environment**

**Default runtimes (pre-configured):**
- `python:3.11` - Clean Python 3.11 (minimal packages)
- `python:3.10` - Python 3.10
- `python:3.11-datascience` - NumPy, Pandas, SciPy, scikit-learn, Matplotlib
- `python:3.11-llm` - OpenAI, Anthropic, LangChain, requests
- `ffmpeg:latest` - FFmpeg + Python for media processing
- `node:20` - Node.js 20 for JavaScript execution

**Custom runtimes:**
```bash
# Use any public Docker image
rgrid run script.py --runtime docker.io/custom/my-runtime:v1 input.json
```

**6. Authentication & Configuration**

**Convention: Global credentials, optional project settings**

**Authentication (global, set once):**
```bash
# First time ever (anywhere on your machine)
rgrid init

# Interactive prompts:
# - Create account or login with email
# - Generates API key automatically
# - Stores credentials at: ~/.rgrid/credentials

# File structure (~/.rgrid/credentials):
[default]
api_key = sk_live_abc123...
user_id = user_xyz789

# From then on, NEVER think about auth again
# All rgrid commands automatically use credentials
```

**Project Settings (optional, rarely needed):**
```yaml
# .rgrid/config (optional, in project directory)
# For project-specific defaults
runtime: python:3.11-datascience
region: eu-central
parallel: 20

# NO API key here - always in ~/.rgrid/credentials
# This file is safe to commit to git
```

**Security model:**
- API keys NEVER in project files (always in `~/.rgrid/credentials`)
- Credentials file is user-specific (not shared, not in git)
- Following industry standard (AWS, Docker, GitHub CLI pattern)
- API keys never in CLI arguments (not exposed in shell history)
- Optional: `.rgrid/` added to `.gitignore` automatically by `rgrid init`

**Multi-account support (future):**
```bash
# Use named profiles for different accounts
rgrid init --profile work
rgrid init --profile personal

# Use specific profile
rgrid run script.py --profile work
```

**7. Observability**

**Execution tracking:**
```bash
# List recent executions
rgrid list

Output:
ID          SCRIPT          STATUS      STARTED         DURATION    COST
exec_abc123 process.py      completed   2m ago          45s         $0.02
exec_abc124 convert.py      running     30s ago         -           -
exec_abc125 analyze.py      failed      1h ago          12s         $0.01
```

**Logs:**
```bash
# View logs (stdout/stderr)
rgrid logs exec_abc123

# Stream logs in real-time
rgrid logs exec_abc123 --follow
```

**Status:**
```bash
# Check execution status
rgrid status exec_abc123

Output:
Execution: exec_abc123
Script: process_data.py
Status: completed
Started: 2025-11-14 10:30:15
Completed: 2025-11-14 10:31:00
Duration: 45s
Cost: $0.02
Worker: worker-hetzner-eu-01
Exit Code: 0
Outputs: 3 files (12.5 MB)
```

**8. Output Handling**

**Convention: Outputs appear locally, as if script ran locally**

**Single Execution (automatic download to current directory):**
```bash
# Run script
rgrid run process.py input.json

# Outputs automatically downloaded to current directory
# Same as if you ran: python process.py input.json
$ ls
process.py  input.json  output.json  results.csv
```

**Batch Execution (organized output directory structure):**
```bash
# Run batch
rgrid run process.py --batch inputs/*.json

# Convention: Outputs organized by input filename
./outputs/
  input1/
    output.json
    results.csv
  input2/
    output.json
    results.csv
  input3/
    output.json
    results.csv

# Preserves input filename in directory structure
# Easy to map outputs back to inputs
```

**Custom output location (optional override):**
```bash
# Single execution - different output directory
rgrid run process.py input.json --output-dir results/

# Batch execution - custom location
rgrid run process.py --batch inputs/*.json --output-dir my_results/

# Flat structure (all outputs in one directory, no subdirectories)
rgrid run process.py --batch inputs/*.json --flat
./outputs/
  input1_output.json
  input1_results.csv
  input2_output.json
  input2_results.csv
```

**Remote-only mode (skip automatic download):**
```bash
# Keep outputs remote, get URLs only
rgrid run process.py input.json --remote-only

# List outputs with URLs
rgrid outputs exec_abc123
output.json         1.2 MB    https://rgrid.storage/exec_abc123/output.json
results.csv         8.3 MB    https://rgrid.storage/exec_abc123/results.csv

# Download later if needed
rgrid download exec_abc123 ./results/
```

**Storage and retention:**
- All outputs stored in S3-compatible storage (MinIO)
- Automatic download is the default (feels local)
- Retention: 30 days (configurable)
- Large files (>100MB): Automatic compression

**9. Cost Tracking**

**Per-execution costs:**
```bash
# View costs
rgrid costs

Output:
Date        Executions  Compute Hours   Cost
2025-11-14  45          2.3h            $0.18
2025-11-13  120         5.1h            $0.39

Total (last 7 days): $2.47
```

**Cost estimates:**
```bash
# Estimate before running
rgrid estimate --runtime python:3.11 --batch data/*.csv --parallel 20

Output:
Estimated executions: 500
Estimated duration: ~30s per execution (based on similar scripts)
Estimated cost: ~$1.20 (500 executions × 30s × $0.008/hour)
```

**10. Real-Time Feedback & Long-Running Jobs**

**Context:** Scripts vary wildly in execution time (2 seconds to 30 minutes). Users need visibility into progress, especially for long-running jobs, without requiring them to manually poll for updates.

**Challenge: How to stream feedback/logs back to local caller instance?**

**Solution: WebSocket streaming with graceful degradation**

**Architecture:**
```
CLI ←→ WebSocket ←→ Control Plane ←→ Worker (stdout/stderr capture)
```

**Implementation:**

**For Single Executions:**
```bash
# Default: Fire and forget (async)
rgrid run process.py input.json
> Execution started: exec_abc123
> Status: running
> View logs: rgrid logs exec_abc123 --follow

# Watch mode: Stream logs in real-time
rgrid run process.py input.json --watch
> Execution started: exec_abc123
> Connecting to log stream...
> [00:00] Starting script execution
> [00:01] Loading data from input.json
> [00:02] Processing 1000 records...
> [00:15] Progress: 450/1000 (45%)
> [00:28] Progress: 900/1000 (90%)
> [00:32] Writing output.json
> [00:33] ✓ Execution completed (33s)
> [00:33] Downloading outputs...
> [00:34] ✓ Downloaded: output.json (1.2 MB)
> [00:34] ✓ Cost: $0.02
```

**For Batch Executions:**
```bash
# Batch with watch: Aggregate progress + individual logs
rgrid run process.py --batch data/*.csv --parallel 10 --watch

> Batch execution started: 100 files, 10 parallel workers
> Execution IDs: exec_001 to exec_100
>
> [====>        ] 42/100 complete (3 failed, 10 running, 45 queued)
> Estimated completion: 3m 15s
> Cost so far: $0.84
>
> Recent completions:
>   ✓ data_042.csv → outputs/data_042/ (12s, $0.01)
>   ✓ data_043.csv → outputs/data_043/ (15s, $0.01)
>   ✗ data_044.csv → FAILED (timeout after 5m)
>
> Press 'l' to view logs for specific execution
> Press 'q' to detach (execution continues in background)
```

**User presses 'l' to view specific execution logs:**
```bash
> Select execution ID (or number 1-100): 45
> Streaming logs for exec_045 (data_045.csv)...
>
> [00:00] Starting script execution
> [00:02] Loading data from data_045.csv
> [00:03] Processing 5000 records...
> [00:10] Progress: 2500/5000 (50%)
> [still running...]
>
> Press 'b' to return to batch overview
```

**Long-Running Jobs (>5 minutes):**

**Problem:** Network interruptions, user closes terminal, laptop sleeps

**Solution: Detached execution with reconnection**

```bash
# Start long-running job
rgrid run train_model.py dataset.csv --watch

> Execution started: exec_abc123
> Connecting to log stream...
> [00:00] Loading dataset (500 MB)...
> [01:30] Training epoch 1/100...
> [02:00] Epoch 1 complete, loss: 0.452
> [02:05] Training epoch 2/100...
>
> [User closes laptop, network disconnects]
>
# Later: Reconnect to same execution
rgrid logs exec_abc123 --follow

> Reconnecting to execution exec_abc123...
> Status: running (started 15 minutes ago)
> [15:00] Training epoch 8/100...
> [15:30] Epoch 8 complete, loss: 0.124
> [16:00] Training epoch 9/100...
> [still running...]
```

**Technical Implementation:**

**WebSocket Connection (for --watch mode):**
```python
# CLI establishes WebSocket connection to control plane
ws = WebSocket('wss://api.rgrid.dev/v1/executions/exec_abc123/stream')

# Control plane subscribes to worker stdout/stderr
# Worker captures script output and streams to control plane
# Control plane forwards to CLI via WebSocket

# Graceful handling:
# - Connection drop: CLI shows "Disconnected, execution continues"
# - Reconnection: CLI resumes streaming from last received line
# - User Ctrl+C: CLI detaches, execution continues
```

**Polling Fallback (for environments without WebSocket):**
```bash
# Automatic fallback if WebSocket unavailable
rgrid run process.py input.json --watch

> WebSocket unavailable, falling back to polling...
> Execution started: exec_abc123
> Status: running (polling every 2s)
> [00:00] Starting script execution
> [00:02] Loading data...
> [00:04] Processing...
> [polling continues...]
```

**Long-Running Job Best Practices:**

**For jobs >5 minutes:**
```bash
# Best practice: Start without --watch, check later
rgrid run long_job.py data.csv

> Execution started: exec_abc123
> View status: rgrid status exec_abc123
> View logs: rgrid logs exec_abc123 --follow
> Execution will continue in background

# Check status later
rgrid status exec_abc123
> Status: running
> Duration: 12m 34s
> Estimated completion: ~8 minutes remaining

# Stream logs when ready
rgrid logs exec_abc123 --follow
> [12:34] Training epoch 45/100...
> [13:00] Epoch 45 complete...
```

**Timeout Handling:**
```bash
# Default timeout: 5 minutes (Free tier)
rgrid run slow_script.py input.json

> Error: Execution timeout (5m limit on Free tier)
> Upgrade to Verified tier for 30m limit, or use --timeout flag

# Override timeout (Verified tier)
rgrid run slow_script.py input.json --timeout 1800  # 30 minutes

> Execution started: exec_abc123
> Timeout: 30 minutes
> Status: running...
```

**Real-Time Progress for Common Patterns:**

**FFmpeg Video Processing:**
```bash
rgrid run convert_video.py video.mp4 --runtime ffmpeg:latest --watch

> Execution started: exec_abc123
> [00:00] FFmpeg starting...
> [00:02] Duration: 00:45:30, bitrate: 5000 kb/s
> [00:05] frame=  150 fps= 30 q=28.0 time=00:00:05 bitrate=1500kbits/s
> [00:10] frame=  300 fps= 30 q=28.0 time=00:00:10 bitrate=1500kbits/s
> [Progress: 22% | 00:10:00 / 00:45:30 | ETA: 00:35:30]
> [00:15] frame=  450 fps= 30 q=28.0 time=00:00:15 bitrate=1500kbits/s
> [Progress: 33% | 00:15:00 / 00:45:30 | ETA: 00:30:30]
```

**Batch Job Progress (100 files):**
```bash
rgrid run process.py --batch data/*.csv --parallel 20 --watch

> Batch execution: 100 files, 20 parallel workers
> Started: 2025-11-14 10:30:00
>
> Overall Progress:
> [=========>           ] 45/100 complete (3 failed, 20 running, 32 queued)
> Duration: 2m 30s | ETA: 3m 15s | Cost: $0.90
>
> Active Workers (20):
>   worker-01: data_046.csv [=====>    ] 50% (8s elapsed)
>   worker-02: data_047.csv [===       ] 30% (5s elapsed)
>   worker-03: data_048.csv [=========>] 90% (14s elapsed)
>   ... (17 more)
>
> Recent Events:
>   ✓ data_042.csv completed (12s, $0.01)
>   ✓ data_043.csv completed (15s, $0.01)
>   ✗ data_044.csv FAILED: timeout after 5m
>   ✓ data_045.csv completed (18s, $0.02)
>
> Commands: [l]ogs | [r]etry failed | [c]ancel all | [q]uit (detach)
```

**User Experience Goals:**

1. **Short jobs (<1 min):** Fire and forget, automatic download
2. **Medium jobs (1-5 min):** Optional --watch for real-time feedback
3. **Long jobs (>5 min):** Detached execution, reconnectable logs
4. **Batch jobs:** Aggregate progress, individual log drill-down

**Key Design Principles:**

- **Default is async:** Executions don't block CLI by default
- **--watch is opt-in:** Real-time streaming when desired
- **Graceful degradation:** WebSocket → polling → async
- **Reconnectable:** Long jobs survive network interruptions
- **Progress indicators:** For jobs that emit progress (ffmpeg, training loops)
- **Batch visibility:** Clear overview + drill-down to individuals

**Technical Requirements:**

**FR (added to functional requirements):**
- **FR78:** System supports real-time log streaming via WebSocket connections
- **FR79:** CLI can reconnect to running executions and resume log streaming
- **FR80:** Batch executions display aggregate progress with drill-down to individual logs
- **FR81:** Long-running executions continue when CLI disconnects (detached mode)
- **FR82:** System provides progress estimates for batch jobs (completion percentage, ETA)

**NFR (non-functional requirements):**
- **NFR23:** Log streaming latency < 1 second from worker to CLI
- **NFR24:** WebSocket connections survive network interruptions with automatic reconnection
- **NFR25:** Polling fallback when WebSocket unavailable (2-second intervals)

**11. Minimal Web Console**

**View-only web interface:**
- Dashboard: Recent executions, costs, active workers
- Execution detail: Logs, outputs, duration, cost
- Download outputs via browser
- **Future:** Allow non-technical users to invoke uploaded scripts

#### MVP Validation Test Case

**The "100 Image Conversion" Proof:**

Create a local script that converts PNG to JPG using ffmpeg:

```python
# convert_image.py
import sys
import subprocess

input_file = sys.argv[1]  # e.g., "image1.png"
output_file = input_file.replace('.png', '.jpg')

subprocess.run([
    'ffmpeg', '-i', input_file,
    '-q:v', '2', output_file
], check=True)

print(f"Converted {input_file} → {output_file}")
```

**Test locally:**
```bash
python convert_image.py test.png
# Works: test.jpg created
```

**Test remotely (single):**
```bash
rgrid run convert_image.py test.png --runtime ffmpeg:latest
# Works: can download test.jpg
```

**Test at scale (100 images in parallel):**
```bash
rgrid run convert_image.py --batch images/*.png --parallel 20 --runtime ffmpeg:latest --watch
```

**Success criteria:**
- All 100 conversions complete successfully
- Total time < 3 minutes (vs ~15 minutes locally sequential)
- Cost < $0.50
- Zero code changes to script
- DX feedback: "That was stupid simple"

**12. Marketing Website**

**Public landing site (rgrid.dev):**
- **Landing page**: Hero section, value proposition, clear CTA ("Get Started")
- **Features page**: Explain key benefits (simplicity, cost efficiency, scale on demand)
- **Pricing page**: Transparent per-hour worker costs, no surprise bills
- **Docs landing**: Getting started guide, API reference, examples
- **Sign-up flow**: Clerk authentication, redirect to console after account creation

**Design principles:**
- **Fast loading**: < 1 second initial load (static Next.js build)
- **Clear messaging**: "Run Python scripts remotely, no infrastructure" in hero
- **Trust signals**: Show example code, transparent pricing, open source badge
- **Mobile-friendly**: Responsive design for all devices
- **SEO-optimized**: Meta tags, structured data, sitemap

**MVP scope:**
- Landing page with hero + 3-feature showcase
- Pricing page with calculator (estimate cost for X jobs/month)
- Sign-up button → Clerk → Console
- Footer with links (docs, GitHub, status page, contact)

**Future:**
- Blog for case studies and tutorials
- Interactive playground (run example scripts in browser)
- Customer testimonials and use case gallery

---

## Security, Abuse Prevention & Risk Mitigation

**Context:** As a platform that runs arbitrary user code on shared infrastructure, RGrid faces real security and abuse risks. This section outlines comprehensive defense strategies.

### Threat Model

**Primary Threats:**
1. **Cost Attacks** - Free tier abuse to rack up infrastructure bills
2. **Crypto Mining** - Long-running CPU-intensive malicious workloads
3. **DDoS / Spam Bots** - Using platform to attack external targets
4. **Illegal Content Hosting** - Web servers, file storage, prohibited content
5. **Data Exfiltration** - Stealing data from platform or other users
6. **Account Spam** - Bot signups to exploit free tier
7. **Resource Exhaustion** - Overwhelming infrastructure

### Defense-in-Depth Strategy

#### **Layer 1: Account Verification & Trust Tiers**

**Free Tier (Trust Nothing)**
```yaml
Requirements:
  - Email verification required (click verification link)
  - CAPTCHA on signup (Cloudflare Turnstile)

Limits:
  - 100 executions/month total
  - 5 minute maximum execution time
  - No network access (isolated containers)
  - 1 concurrent execution maximum
  - Daily compute cap: 30 minutes total
  - No batch execution (single files only)

Monitoring:
  - Log all executions (script content hash, resource usage)
  - Flag accounts with >80% CPU usage average
  - Automatic suspension on first Terms of Service violation
  - Manual review queue for anomalies
```

**Verified Tier (Card on File)**
```yaml
Requirements:
  - Valid payment method ($1 authorization hold)
  - Phone verification (SMS code)
  - Account age > 24 hours

Limits:
  - 1,000 executions/month
  - 30 minute maximum execution time
  - Network access allowed (with egress monitoring)
  - 10 concurrent executions
  - Daily spending cap: $10 (user-adjustable up to $50)
  - Batch execution: up to 100 files

Monitoring:
  - Anomaly detection (CPU patterns, network usage, script similarity)
  - Automatic warnings before reaching limits
  - Temporary suspension on abuse (not permanent ban)
  - 48-hour review for reinstatement
```

**Trusted Tier (Established Users)**
```yaml
Requirements:
  - Total spending > $100 lifetime
  - Account age > 30 days
  - No prior violations

Limits:
  - Unlimited executions
  - 60 minute maximum execution time
  - Higher concurrency (50+ workers)
  - Daily spending cap: $100 (adjustable up to $500)
  - Batch execution: unlimited

Monitoring:
  - Light monitoring (trust-based)
  - Violations reviewed manually before action
  - Account manager contact for enterprise usage
```

#### **Layer 2: Execution Isolation & Resource Limits**

**Container Isolation:**
```python
# Each execution runs in isolated Docker container
docker run \
  --network=none \          # No network by default
  --read-only \             # Read-only root filesystem
  --tmpfs /tmp:size=100M \  # Limited temp storage
  --cpus=2 \                # Hard CPU limit
  --memory=4G \             # Hard memory limit
  --pids-limit=100 \        # Limit process count
  --security-opt=no-new-privileges \
  --cap-drop=ALL \          # Drop all capabilities
  user-script
```

**Resource Limits (enforced via cgroups):**
- CPU: Max 2 vCPU per execution
- Memory: Max 4GB RAM per execution
- Storage: Max 10GB temp disk
- Processes: Max 100 processes
- File descriptors: Max 1024
- Execution time: Hard timeout (kills process)

**Network Controls (Progressive Permissions Model):**

**Context:** Users need network access for legitimate use cases (API calls, web scraping, browser automation) but unrestricted access enables abuse. Solution: Progressive permissions based on trust tier.

**Free Tier (No Network Access):**
```yaml
Network: DISABLED (--network=none in Docker)
Rationale: Eliminates DDoS, spam, crypto mining risks
Use cases: Local data processing, pure computation, file transformations
Override: None (hard restriction)
```

**Verified Tier (Monitored Network Access):**
```yaml
Network: ENABLED with monitoring
Egress: Allowed (no inbound connections)
Rate limit: 1,000 requests/minute per execution
Bandwidth: 100 Mbps per execution
Blocked ports: 25 (SMTP), 445 (SMB), 1433 (MSSQL), 3306 (MySQL), 3389 (RDP)
DNS monitoring: Flag suspicious domains (crypto pools, C2 servers, known malicious hosts)
User-Agent tracking: Detect browser automation libraries (Playwright, Selenium, Puppeteer)

Browser Automation Detection:
  - Allowed: YES (with monitoring)
  - Libraries detected: playwright, selenium, puppeteer, scrapy, requests
  - Abuse signals:
    - Same target domain >1000 times in 5 minutes
    - Failed connection attempts >100 (port scanning behavior)
    - Excessive rate (>100 req/sec to single domain)
    - Suspicious domains (admin panels, login endpoints, CAPTCHA farms)
  - Actions on abuse:
    - First offense: Warning email + execution killed
    - Second offense: 24-hour account suspension
    - Third offense: Manual review required
```

**Trusted Tier (Relaxed Monitoring):**
```yaml
Network: ENABLED with light monitoring
Rate limit: 10,000 requests/minute (10x Verified)
Bandwidth: 1 Gbps
Monitoring: Anomaly-based (not strict rule-based)
Override: User can request temporary limit increases (verified manually)
```

**Browser Automation Security Model:**

The challenge: Browser automation is **legitimate** (testing, scraping, automation) but also enables **abuse** (DDoS, spam, unauthorized access).

**Solution: Intent-based detection + progressive trust**

**Legitimate Browser Automation (Allowed):**
```python
# Web scraping for data analysis
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://example.com/public-data')
    data = page.query_selector_all('.data-row')
    # Process and save data
    browser.close()
```

**Signals this is legitimate:**
- Reasonable rate (<10 pages/minute)
- Public endpoints (not admin panels, login forms)
- Respectful behavior (honors robots.txt, user-agent disclosure)
- Verified tier account in good standing

**Abusive Browser Automation (Blocked):**
```python
# DDoS or credential stuffing
for i in range(10000):
    page.goto('https://victim.com/login')
    page.fill('#username', username_list[i])
    page.fill('#password', password_list[i])
    page.click('#submit')
```

**Signals this is abuse:**
- Excessive rate (>100 req/min to single endpoint)
- Login/admin endpoints targeted
- Repeated failures (credential stuffing pattern)
- CAPTCHA solving attempts

**Detection Mechanism:**
```python
def detect_browser_abuse(execution):
    # Pattern 1: Excessive requests to single domain
    if execution.requests_per_domain['example.com'] > 1000 in 5_minutes:
        flag_account(execution.user, "excessive_scraping")
        kill_execution(execution.id)

    # Pattern 2: Login endpoint targeting
    if execution.urls_accessed.includes('/login', '/admin', '/wp-admin'):
        if execution.failed_responses > 50:
            flag_account(execution.user, "credential_stuffing")
            suspend_account(execution.user, duration=24_hours)

    # Pattern 3: CAPTCHA solving services
    if execution.dns_queries.includes('2captcha.com', 'anticaptcha.com'):
        flag_account(execution.user, "captcha_bypass")
        manual_review_required()

    # Pattern 4: Distributed attack pattern
    if execution.unique_targets > 100 in 10_minutes:
        flag_account(execution.user, "scanning_behavior")
        kill_execution(execution.id)
```

**User Experience for Legitimate Use:**
```bash
# User runs browser automation script
rgrid run scrape_data.py --runtime playwright:latest --watch

# First time (Verified tier):
> ✓ Execution started
> ⚠️  Network monitoring enabled (Verified tier)
> ✓ Script completed (45s)
> ✓ 12 pages scraped
> ℹ️  Network usage: 234 requests, 12 MB egress (within limits)

# After establishing trust (multiple successful runs):
> ✓ Execution started
> ✓ Script completed (45s)
> (No monitoring warnings)
```

**Abuse Prevention in Practice:**

**Scenario 1: Legitimate web scraping**
- User scrapes 100 product pages from e-commerce site
- Rate: 5 pages/minute
- Result: ✅ Allowed (reasonable rate, public data)

**Scenario 2: Aggressive scraping**
- User scrapes 10,000 pages in 10 minutes
- Rate: 1000 pages/minute
- Result: ⚠️ Warning email, execution continues but flagged for review

**Scenario 3: DDoS attempt**
- User sends 50,000 requests to single domain in 5 minutes
- Pattern: Same endpoint, no data collection
- Result: 🚫 Execution killed immediately, account suspended 24 hours

**Scenario 4: Credential stuffing**
- User targets `/login` endpoint with 1000 username/password combos
- Pattern: Repeated POST to auth endpoint, high failure rate
- Result: 🚫 Execution killed, account suspended pending manual review

**Rollout Strategy:**

**Phase 1 (Closed Beta):**
- Free tier ONLY (no network access)
- Learn baseline resource usage patterns
- Validate container isolation

**Phase 2 (Open Beta):**
- Verified tier available (network enabled with strict monitoring)
- Tight rate limits (1000 req/min)
- Fast response to abuse (immediate suspension)

**Phase 3 (General Availability):**
- All tiers active
- Automated abuse detection with ML (anomaly patterns)
- Established trust system (Trusted tier unlocks)

**Key Design Principle:**
> **Start restrictive, loosen gradually based on behavior.**

This prevents early-stage abuse while enabling legitimate use cases. Verified tier (card on file) unlocks network access. Trust tier (spending history) unlocks higher limits.

#### **Layer 3: Abuse Detection & Anomaly Monitoring**

**Crypto Mining Detection:**
```python
def detect_crypto_mining(execution):
    if (execution.avg_cpu > 95% and
        execution.duration > 300 and
        execution.network_activity < 1MB):
        flag_account(execution.user, reason="suspected_crypto_mining")
        kill_execution(execution.id)
        send_warning_email(execution.user)
```

**DDoS / Spam Detection:**
```python
def detect_abuse_patterns(execution):
    if execution.outbound_requests > 10000:
        flag_account(execution.user, reason="excessive_requests")

    if execution.unique_destinations < 5 and execution.requests > 1000:
        flag_account(execution.user, reason="targeted_spam")

    if execution.failed_connections > 100:
        flag_account(execution.user, reason="port_scanning")
```

**Data Exfiltration Detection:**
```python
def detect_exfiltration(execution):
    if execution.egress_bytes > 10GB:
        flag_account(execution.user, reason="excessive_data_transfer")

    if execution.upload_rate > 100MB/s sustained:
        flag_account(execution.user, reason="suspicious_upload")
```

**Pattern-Based Detection:**
- Script similarity analysis (detect mass abuse campaigns)
- Execution timing patterns (scheduled attacks)
- Geographic anomalies (signups from high-risk regions)
- Payment fraud patterns (stolen cards, chargebacks)

#### **Layer 4: Infrastructure Protection**

**Worker Isolation:**
- Ephemeral workers (destroyed after batch, max 60 min lifetime)
- No persistent storage on workers
- No SSH access to workers
- Workers cannot access control plane
- Workers in separate VPC from control plane

**Data Protection:**
- User scripts never logged (only content hash)
- Execution outputs encrypted at rest (S3 encryption)
- API keys hashed (bcrypt) and never logged
- PII scrubbing in logs (emails, IPs, API keys redacted)

**DDoS Protection:**
- Cloudflare in front of API (rate limiting, bot detection)
- API rate limits: 100 req/min per API key
- Distributed control plane (multiple regions)
- Graceful degradation (queue jobs when overloaded)

#### **Layer 5: Financial Controls**

**Spending Limits:**
- Hard daily caps per tier
- Soft warnings at 50%, 80% of cap
- Execution blocks at 100% of cap
- User-adjustable caps (within tier limits)

**Billing Protection:**
- Prepaid credits for new accounts
- Postpaid billing only for Verified+ tier
- Automatic charge holds if usage spikes >10x
- Fraud detection via Stripe Radar

**Cost Transparency:**
- Per-execution cost shown before running
- Real-time cost tracking in dashboard
- Email alerts at spending thresholds
- Itemized billing (per execution, exportable CSV)

### Compliance & Legal

**Terms of Service (Prohibited Use):**
- ❌ Crypto mining or proof-of-work computations
- ❌ DDoS attacks or network scanning
- ❌ Spam, phishing, or malware distribution
- ❌ Illegal content hosting or distribution
- ❌ Circumventing platform limits
- ❌ Reselling compute without authorization

**Data Privacy (GDPR/CCPA Compliance):**
- User data retention: 90 days max (configurable)
- Right to deletion (API endpoint + manual request)
- Data export (download all execution data)
- Consent-based analytics tracking

**Incident Response:**
1. Detection (automated monitoring + manual reports)
2. Investigation (review logs, usage patterns)
3. Action (warning, temporary suspension, permanent ban)
4. Appeal (manual review within 48 hours)
5. Remediation (refund if false positive)

### Monitoring & Observability

**Operational Metrics:**
- Failed execution rate (target: <5%)
- Average execution time per tier
- Worker utilization (target: 60-80%)
- Cost per execution (optimize over time)

**Security Metrics:**
- Account suspension rate
- Abuse detection false positive rate (target: <1%)
- Average time to detect abuse (target: <5 minutes)
- Chargebacks / fraud rate (target: <0.5%)

**Alerting:**
- Slack alerts for account suspensions
- PagerDuty for infrastructure outages
- Email alerts for users hitting limits
- Dashboard for operator monitoring

### Rollout Strategy (Progressive Trust)

**Phase 1: Closed Beta (50 users)**
- Invite-only signups
- Manual vetting of each user
- Free tier only
- Learn abuse patterns

**Phase 2: Open Beta (500 users)**
- Public signups with email verification
- Free + Verified tiers
- Tight monitoring, fast response

**Phase 3: General Availability (5,000+ users)**
- All tiers active
- Automated abuse detection
- Established trust system

### Competitive Analysis (How Others Handle This)

**Vercel:**
- Free tier: Generous but monitored
- Automatic suspension on abuse
- Enterprise tier for high usage

**Replit:**
- Free tier: Very limited (public repls only)
- Always-on requires paid plan
- Automatic takedown of Terms violations

**Modal:**
- Free tier: $30 credit
- Credit card required for anything beyond free
- Usage monitoring and caps

**Heroku:**
- Removed free tier entirely (too much abuse)
- Credit card required from day 1
- Lesson: Free tier needs tight limits

### Risk Assessment

**Low Risk (Manageable):**
- ✅ Crypto mining: CPU limits + timeout = unprofitable
- ✅ Account spam: Email + card verification = high friction
- ✅ Data exfiltration: Isolated containers = no access

**Medium Risk (Requires Monitoring):**
- ⚠️ DDoS bots: Network monitoring + egress limits mitigate
- ⚠️ Cost attacks: Spending caps + anomaly detection manage
- ⚠️ Reputation damage: Terms enforcement + proactive monitoring

**High Risk (Potential MVP Blockers):**
- 🚨 Runaway costs from abuse: **Mitigated** via hard spending caps, prepaid credits
- 🚨 Platform ban from cloud providers: **Mitigated** via abuse detection, Terms enforcement
- 🚨 Payment fraud / chargebacks: **Mitigated** via Stripe Radar, verification tiers

**Verdict: Risks are manageable with proper controls. Launch conservatively, scale trust gradually.**

---

### Growth Features (Post-MVP)

Features that enhance power and flexibility once paradigm is proven:

**Enhanced Script Management:**
- `rgrid upload <script> --name <alias>` - Upload script, invoke by name later
- `rgrid invoke <name> [args]` - Run previously uploaded script
- `rgrid versions <name>` - List script versions
- Script versioning and rollback
- GitHub integration: `rgrid connect github.com/user/repo`, then `rgrid run repo/script.py`

**Advanced Execution Patterns:**
- `rgrid run --workflow workflow.yaml` - Multi-step DAGs (integrate Temporal)
- Scheduled executions: `rgrid schedule "0 * * * *" script.py input.json`
- Streaming outputs: `rgrid run script.py --stream-output`
- Chained executions: Output of one script → input to next

**Declarative Workflow Support:**
```yaml
# workflow.yaml
name: data-pipeline
steps:
  - name: fetch
    script: fetch_data.py
    runtime: python:3.11

  - name: process
    script: process_data.py
    runtime: python:3.11-datascience
    inputs:
      data: ${steps.fetch.outputs.data.csv}

  - name: visualize
    script: create_charts.py
    runtime: python:3.11-datascience
    inputs:
      processed: ${steps.process.outputs.results.json}
```

Then: `rgrid run --workflow workflow.yaml`

**LLM-Specific Features (Major Growth Area):**
- Pre-configured LLM runtimes with API keys injected
- Token usage tracking across batch executions
- Rate limit handling (automatic backoff/retry)
- Parallel agent execution helpers
- Cost optimization (cheapest model selection)

**Extensibility & Future-Proofing:**
- **Event Hooks (Internal):** Executions expose internal event stream enabling future webhooks, workflow triggers, audit logs
- **Execution Metadata Tagging:** Attach metadata to executions for organization, cost allocation, analytics
- **Alternative Execution Engines:** EMA allows swapping Ray for Temporal, Inngest, Kubernetes Jobs without CLI changes

**Integration Patterns for Existing Applications:**

RGrid is designed to integrate seamlessly with existing Django, Rails, Flask, or other web applications as a background job executor - without requiring code refactoring.

**Pattern 1: Subprocess Integration (Zero Dependencies)**
```python
# Django example - tasks.py
import subprocess

def process_video_background(video_id):
    video = Video.objects.get(id=video_id)

    # Shell out to rgrid CLI (already installed)
    result = subprocess.run([
        'rgrid', 'run', 'scripts/process_video.py',
        video.file.path,
        '--env', f'VIDEO_ID={video_id}',
        '--env', f'DATABASE_URL={os.getenv("DATABASE_URL")}'
    ], capture_output=True)

    if result.returncode == 0:
        video.status = 'processed'
        video.save()
```

**Pattern 2: Thin Python Library (Recommended)**
```python
# Thin wrapper over CLI (no heavy SDK)
import rgrid

def process_video_background(video_id):
    video = Video.objects.get(id=video_id)

    # Clean API, internally calls CLI
    execution = rgrid.run(
        script='scripts/process_video.py',
        args=[video.file.path],
        env={'VIDEO_ID': video_id, 'DATABASE_URL': os.getenv('DATABASE_URL')},
        wait=False  # Don't block, return immediately
    )

    # Store execution ID for polling
    video.rgrid_execution_id = execution.id
    video.status = 'processing'
    video.save()

# Later, check status
def check_video_status(video_id):
    video = Video.objects.get(id=video_id)
    status = rgrid.status(video.rgrid_execution_id)

    if status.completed:
        outputs = rgrid.download(video.rgrid_execution_id)
        video.processed_file = outputs['output.mp4']
        video.status = 'completed'
        video.save()
```

**Python Library API (Simple & Intuitive):**
```python
import rgrid

# Fire and forget (blocks until complete)
rgrid.run('process.py', 'input.json')

# Async (get execution ID back)
execution = rgrid.run('process.py', 'input.json', wait=False)
execution.id  # exec_abc123

# Check status later
status = rgrid.status('exec_abc123')
status.completed  # True/False
status.logs()     # Get logs

# Download outputs
outputs = rgrid.download('exec_abc123', dest='./results/')

# Batch execution
executions = rgrid.run('process.py', batch='data/*.csv', parallel=50)
for ex in executions:
    if not ex.completed:
        print(f"Failed: {ex.id}")
```

**Pattern 3: HTTP API (Language-Agnostic)**
```ruby
# Rails example - app/jobs/process_video_job.rb
class ProcessVideoJob < ApplicationJob
  def perform(video_id)
    video = Video.find(video_id)

    # Direct HTTP API call (no library needed)
    response = HTTParty.post('https://api.rgrid.dev/v1/executions',
      headers: {
        'Authorization' => "Bearer #{ENV['RGRID_API_KEY']}",
        'Content-Type' => 'application/json'
      },
      body: {
        script: 'scripts/process_video.py',
        args: [video.file.path],
        env: {
          VIDEO_ID: video_id,
          DATABASE_URL: ENV['DATABASE_URL']
        }
      }.to_json
    )

    execution_id = response['id']
    video.update(rgrid_execution_id: execution_id, status: 'processing')
  end
end
```

**Pattern 4: Integration with Existing Job Queues**

RGrid works alongside Celery, Sidekiq, Resque - use them for scheduling, RGrid for execution:

```python
# Celery + RGrid (Django/Flask)
from celery import shared_task
import rgrid

@shared_task
def process_video(video_id):
    """Celery schedules, RGrid executes"""
    video = Video.objects.get(id=video_id)

    # Execute heavy work on RGrid
    execution = rgrid.run(
        script='scripts/process_video.py',
        args=[video.file.path]
    )  # Blocks until complete

    video.status = 'completed'
    video.save()

# Usage (normal Celery)
process_video.delay(video_id=123)
```

```ruby
# Sidekiq + RGrid (Rails)
class ProcessVideoWorker
  include Sidekiq::Worker

  def perform(video_id)
    video = Video.find(video_id)

    # Shell out to rgrid CLI
    system("rgrid run scripts/process_video.py #{video.file.path}")

    video.update(status: 'completed')
  end
end

# Usage (normal Sidekiq)
ProcessVideoWorker.perform_async(123)
```

**Design Philosophy:**
- **No refactoring required:** Scripts work as-is
- **Thin integration:** Wrapper over CLI, not heavy SDK
- **Language-agnostic:** Works from Python, Ruby, PHP, Node.js, Go
- **Queue-compatible:** Works alongside Celery, Sidekiq, Resque

**Implementation:**
- Python library: ~200 lines (thin wrapper over subprocess)
- Ruby gem: Similar thin wrapper
- JavaScript library: Wrapper over child_process
- HTTP API: Direct access for any language

**Infrastructure Expansion:**
- GPU-enabled workers (for ML inference, rendering)
- Multi-cloud support (AWS, GCP, Fly.io - user selects region/provider)
- Spot instance support (even cheaper, with retry)
- Bring-your-own-cloud (use user's cloud credits)

**Developer Experience:**
- Local development mode: `rgrid run --local` (test without cloud)
- VS Code extension (right-click script → "Run on RGrid")
- GitHub Actions integration: `uses: rgrid/run-script`
- Performance profiling: `rgrid profile exec_abc123`

**Collaboration & Sharing:**
- Share script templates with team
- Public script gallery (opt-in)
- Team workspaces (shared scripts, billing)
- Execution replay/debugging

**Enterprise Features (Vision):**
- VPC/private networking
- SSO/SAML authentication
- Custom Docker registries
- Audit logging and compliance
- SLA guarantees

### Vision (Future Paradigm Expansion)

**The "Heroku for Scripts" Evolution:**

1. **Invisible Infrastructure Everywhere**
   - Any language (Python today, then JS, Ruby, Go, shell scripts)
   - Any cloud (user never specifies, RGrid optimizes)
   - Any workload (batch, streaming, scheduled)

2. **Script Marketplace & Ecosystem**
   - Public script library (like npm but for executable scripts)
   - Community-contributed utilities
   - One-click deployment of common tasks

3. **The New Mental Model**
   - Developers stop thinking about "local vs remote"
   - Scripts are just scripts; execution location is deployment detail
   - `rgrid run` becomes as common as `git push`

4. **Non-Developer Access**
   - Business users invoke scripts via web UI (no CLI needed)
   - Markdown execution blocks (run scripts from documentation)
   - Notion/Slack integrations (trigger scripts from workspace)

5. **Economic Disruption**
   - Commodity cloud pricing democratized
   - Small teams access enterprise-scale compute
   - Pay per execution, not per infrastructure

**Ultimate vision:** RGrid disappears. Running scripts remotely becomes the default. The abstraction becomes the standard.

---

## Functional Requirements

**Context:** These FRs define the CAPABILITIES that deliver the paradigm shift. They're organized by user-facing capability areas, NOT implementation layers.

### CLI & Developer Interface

**FR1:** Developers can install RGrid via package manager (brew/pip) with zero additional system dependencies

**FR2:** Developers can authenticate and initialize RGrid in < 1 minute via `rgrid init`

**FR3:** Developers can execute local scripts remotely with identical syntax: `rgrid run script.py args`

**FR4:** Developers can execute scripts in parallel across multiple input files via `--batch` flag

**FR5:** Developers can specify runtime requirements via `--runtime` flag (Python versions, pre-baked environments)

**FR6:** Developers can monitor execution status in real-time via `rgrid status` and `--watch` flag

**FR7:** Developers can access execution logs (stdout/stderr) via `rgrid logs`

**FR8:** Developers can download execution outputs via `rgrid download`

**FR9:** Developers can view cost estimates before execution and actual costs after

**FR10:** Developers receive clear, actionable error messages when executions fail (not raw infrastructure errors)

### Script Execution Model

**FR11:** Scripts execute in isolated container environments with specified runtimes

**FR12:** System supports multiple pre-configured runtimes (Python 3.10, 3.11, datascience, LLM, ffmpeg, Node.js) without user setup

**FR13:** Developers can specify custom Docker images from public registries for specialized environments

**FR14:** Scripts receive input files as command-line arguments (identical to local execution)

**FR15:** Scripts write outputs to working directory; RGrid automatically collects all created files

**FR16:** Script exit codes determine execution success (0 = success, non-zero = failure)

**FR17:** Scripts can read from environment variables passed via `--env` flag

**FR18:** System automatically detects and installs dependencies from requirements.txt in same directory as script

**FR19:** Developers can explicitly specify requirements file via `--requirements` flag

**FR20:** Scripts have network access by default (can fetch external data, call APIs)

### Caching & Performance Optimization

**FR21:** System caches script images using content hashing (sha256 of script content)

**FR22:** System caches dependency layers using requirements.txt content hashing

**FR23:** Cached scripts and dependencies provide instant execution after first run (no rebuild/reinstall)

**FR24:** Cache invalidation is automatic when script or dependencies change (new hash → rebuild)

**FR25:** Caching is completely invisible to users (no cache management commands required)

**FR26:** System optionally caches input files to avoid redundant uploads of identical files

### Batch Execution & Parallelism

**FR27:** System expands file patterns (glob patterns) into individual executions

**FR28:** System distributes batch executions across available workers up to parallelism limit

**FR29:** System tracks progress of batch executions (completed, failed, running, queued)

**FR30:** Developers can set max parallelism via `--parallel` flag

**FR31:** System handles batch execution failures gracefully (continue processing remaining items)

**FR32:** Developers can retry failed executions individually or in batch

**FR33:** Batch outputs organized in `./outputs/<input-name>/` directory structure by convention

**FR34:** Developers can override output location via `--output-dir` flag

**FR35:** Developers can request flat output structure (all files in one directory) via `--flat` flag

### Distributed Orchestration (Invisible Infrastructure)

**FR36:** System automatically provisions compute workers on Hetzner cloud infrastructure when workload demand increases

**FR37:** System distributes script executions across available workers using Ray's task scheduling

**FR38:** System scales worker pool based on pending execution queue depth

**FR39:** System automatically terminates idle workers to minimize cost (scale to zero)

**FR40:** System maintains worker health monitoring and automatically replaces failed workers

**FR41:** System caches common Docker images on workers to reduce cold-start latency

**FR42:** System manages Ray cluster lifecycle (initialization, scaling, cleanup) without user intervention

**FR43:** System handles network communication between CLI, control plane, and workers

### File & Artifact Management

**FR44:** System automatically uploads input files referenced in script arguments

**FR45:** System collects all files created in script's working directory as outputs

**FR46:** System stores execution outputs in S3-compatible storage (MinIO) with retention policy

**FR47:** Single execution outputs automatically downloaded to current directory (convention)

**FR48:** Developers can skip automatic download via `--remote-only` flag (outputs stay remote)

**FR49:** Developers can list outputs before downloading via `rgrid outputs <execution-id>`

**FR50:** System handles large files efficiently (streaming uploads/downloads, compression for >100MB)

### Authentication & Configuration

**FR51:** System authenticates all CLI commands using API keys stored in `~/.rgrid/credentials`

**FR52:** API keys NEVER stored in project files or passed as CLI arguments (security best practice)

**FR53:** `rgrid init` creates global credentials file at `~/.rgrid/credentials` (once per machine)

**FR54:** Optional project-level configuration via `.rgrid/config` for defaults (runtime, region, parallelism)

**FR55:** Project config files safe to commit to git (no secrets, only preferences)

**FR56:** Multi-account support via named profiles (future enhancement)

### Observability & Monitoring

**FR57:** Developers can view execution history (recent runs, status, duration) via CLI and web console

**FR58:** Developers can access real-time logs for running executions via `--watch` or `--follow`

**FR59:** Developers can retrieve historical logs for completed executions

**FR60:** System tracks execution metadata (start time, end time, exit code, worker ID, cost, runtime)

**FR61:** Developers can view current worker pool status (count, region, utilization)

**FR62:** System provides progress tracking for batch executions (N/total complete, estimated time remaining)

### Cost & Billing

**FR63:** System calculates per-execution cost based on actual compute time and resources used

**FR64:** Developers can view itemized cost breakdown by execution, day, or month via `rgrid cost`

**FR65:** System displays cost estimates before running batch executions via `rgrid estimate`

**FR66:** Billing is transparent with clear mapping to underlying infrastructure costs (Hetzner pricing + markup)

**FR67:** Developers can set cost alerts or spending limits per account (future: per project)

### Error Handling & Reliability

**FR68:** System detects and reports common user errors (invalid runtime, missing input files, syntax errors)

**FR69:** System handles network failures gracefully with automatic reconnection

**FR70:** Failed executions preserve logs and error context for debugging

**FR71:** System prevents cascading failures (one bad execution doesn't crash workers)

**FR72:** Developers can manually retry failed executions via `rgrid retry <execution-id>`

**FR73:** System automatically retries transient failures (worker crashes, network errors) with configurable limit (default: 2 retries)

### Extensibility & Future-Proofing

**FR74:** Developers can attach custom metadata to executions (tags, labels, key-value attributes) via `--metadata` flag for organization and filtering

**FR75:** System stores execution metadata and makes it queryable for analytics and optimization

**FR76:** Execution lifecycle events (start, complete, fail, retry) are captured internally for future extensibility (webhooks, workflows, audit trails)

**FR77:** System architecture uses pluggable abstractions (EMA for execution engines, CPAL for cloud providers, runtime providers) enabling future extensions without CLI interface changes

---

**Total Functional Requirements: 82** (up from 77 in previous version)

**New FRs focus on:**
- Caching strategy (FR21-FR26)
- Batch output conventions (FR33-FR35)
- Authentication model (FR51-FR56 updated)
- Automatic output handling (FR47-FR48)
- Real-time feedback and streaming (FR78-FR82)

---

## Non-Functional Requirements

**Context:** These define quality attributes and constraints that shape HOW the system delivers functional capabilities.

### Performance

**NFR1: Low-Latency Execution Overhead**
- Cold start (first execution with new runtime): < 30 seconds from CLI command to script start
- Warm execution (runtime cached): < 10 seconds overhead vs local execution
- Batch execution: near-linear speedup (20x speedup with 20 parallel workers)

**NFR2: CLI Responsiveness**
- CLI commands respond within 2 seconds (status, logs, costs, list)
- File uploads: minimum 10 MB/s (acceptable for small scripts)
- Log streaming: < 1 second latency

**NFR3: Scalability Targets**
- Support 100+ concurrent executions per account (MVP)
- Support 1000+ queued executions without degradation
- Scale worker pool to 50+ nodes within 5 minutes of demand spike

### Reliability

**NFR4: Execution Success Rate**
- 95%+ success rate for valid scripts (excluding user code bugs)
- Automatic retry succeeds for 90%+ of transient failures

**NFR5: Infrastructure Resilience**
- Single worker failure doesn't impact other executions
- Control plane uptime: 99%+
- Graceful degradation when cloud provider has issues

**NFR6: Data Durability**
- Execution logs retained for 7 days minimum
- Outputs retained for 30 days or until user deletes
- No data loss during worker lifecycle transitions

### Security

**NFR7: Isolation**
- Each execution runs in isolated container (no shared filesystem)
- Resource limits enforced (CPU, memory) to prevent abuse
- Scripts cannot access other users' data or executions

**NFR8: Authentication**
- All CLI commands require valid API key
- API keys stored securely (hashed in database, encrypted in transit)
- Support key rotation without downtime

**NFR9: Data Privacy**
- User scripts and data never logged or inspected by system
- Execution logs only accessible to account owner
- Outputs stored with account-scoped access control

### Usability & Developer Experience

**NFR10: Time to First Execution**
- New user to first successful remote execution: < 3 minutes
- Experienced user trying new script: < 1 minute

**NFR11: Interface Simplicity**
- Local command: `python script.py input.json`
- Remote command: `rgrid run script.py input.json`
- Identical syntax = zero learning curve

**NFR12: Error Messages Quality**
- Errors are actionable (include resolution steps)
- Common errors detected early (before cloud execution)
- No cryptic infrastructure errors exposed to users

### Maintainability & Operational Simplicity

**NFR13: Infrastructure as Code**
- All infrastructure provisioning automated (Terraform/Pulumi)
- Worker images reproducible from Dockerfile
- Zero manual server configuration

**NFR14: Observability for Operators**
- System metrics exposed (Prometheus/Grafana compatible)
- Structured logging for debugging (JSON logs, trace IDs)
- Health checks for all services (control plane, workers, Ray cluster)

**NFR15: Deployment Simplicity**
- Control plane deployable via single command (Docker Compose or fly deploy)
- Worker image updates don't disrupt running executions
- Database migrations automated and safe

### Cost Efficiency

**NFR16: Compute Cost Optimization**
- Worker cost ≤ 1.2x Hetzner bare compute pricing (max 20% markup)
- Idle workers terminated within 5 minutes (minimize waste)
- Image caching reduces redundant network transfer costs

**NFR17: User Cost Transparency**
- Users can predict costs before execution (estimate available)
- Billing breakdowns show exactly what was charged (per-second granularity)

### Scalability (Growth Considerations)

**NFR18: Multi-Cloud Readiness**
- Cloud provider abstraction allows adding AWS/GCP/Fly without CLI changes
- No Hetzner-specific logic in CLI or API

**NFR19: Multi-Language Extensibility**
- Execution model supports non-Python runtimes (already Docker-based)
- CLI architecture supports language-specific features without refactor

### Architectural Future-Proofing

**NFR20: Modular Pluggability**
- Execution engines pluggable via EMA (switch Ray → Temporal → custom without CLI changes)
- Cloud providers pluggable via CPAL (add new providers without CLI refactor)
- Runtime providers pluggable (GPU, language-specific, custom environments addable without breaking changes)

**NFR21: Event-Driven Extensibility**
- Internal event stream for execution lifecycle (start, complete, fail, retry)
- Extensible for future automation (webhooks, workflow triggers, audit logging)
- Zero performance impact when events not consumed

**NFR22: Metadata-Driven Optimization**
- Execution metadata (tags, labels, attributes) stored and queryable
- Enables future AI-driven routing, cost prediction, and workload optimization
- Metadata schema extensible without schema migrations

---

## CLI Interface Specification

**Context:** As a CLI-first tool, the command interface is the primary user touchpoint.

### Core Commands

**`rgrid init`** - Setup and authentication
```bash
rgrid init

# Interactive prompts:
# - Create account or login
# - Generate API key
# - Configure default settings (region, etc.)
# Stores config in ~/.rgrid/config.yaml
```

**`rgrid run`** - Execute script remotely
```bash
rgrid run <script> [args] [options]

Arguments:
  script              Path to Python script
  args                Arguments passed to script (same as local execution)

Options:
  --runtime IMAGE     Docker runtime (default: python:3.11)
  --batch PATTERN     Run script for each file matching pattern
  --parallel N        Max parallel executions (default: 10)
  --cpu N             CPU cores per execution (default: 1)
  --memory SIZE       Memory per execution (default: 2Gi)
  --timeout SECONDS   Max execution time (default: 300)
  --env KEY=VALUE     Environment variables (repeatable)
  --requirements FILE Python requirements file
  --watch             Stream logs in real-time
  --metadata KEY=VAL  Attach metadata (repeatable)
  --dry-run           Show what would run without executing

Examples:
  rgrid run process.py input.json
  rgrid run process.py --batch data/*.csv --parallel 20
  rgrid run process.py input.json --runtime python:3.11-datascience
  rgrid run process.py input.json --env API_KEY=xxx --watch
```

**`rgrid status`** - Check execution status
```bash
rgrid status [execution-id]

# Without ID: shows recent executions
# With ID: shows detailed status for specific execution
```

**`rgrid logs`** - View execution logs
```bash
rgrid logs <execution-id> [options]

Options:
  --follow, -f        Stream logs in real-time
  --tail N            Show last N lines (default: 100)
```

**`rgrid download`** - Download execution outputs
```bash
rgrid download <execution-id> <destination>

# Downloads all output files to destination directory
```

**`rgrid outputs`** - List execution outputs
```bash
rgrid outputs <execution-id>

# Shows list of output files with sizes
```

**`rgrid list`** - List recent executions
```bash
rgrid list [options]

Options:
  --limit N           Number of executions to show (default: 20)
  --status STATUS     Filter by status (completed, running, failed)
  --script NAME       Filter by script name
```

**`rgrid costs`** - View billing summary
```bash
rgrid costs [options]

Options:
  --range RANGE       Time range (7d, 30d, 2025-11-01:2025-11-14)
  --detailed          Show per-execution breakdown
```

**`rgrid retry`** - Retry failed execution
```bash
rgrid retry <execution-id>

# Re-runs failed execution with same parameters
```

**`rgrid cancel`** - Cancel running execution
```bash
rgrid cancel <execution-id>
```

**`rgrid estimate`** - Estimate execution cost
```bash
rgrid estimate [options]

# Same options as 'rgrid run'
# Shows estimated cost without executing
```

### Future Commands (Growth)

```bash
# Script management
rgrid upload <script> --name <alias>
rgrid invoke <alias> [args]
rgrid versions <alias>

# Workflow execution
rgrid run --workflow workflow.yaml

# Scheduled execution
rgrid schedule "0 * * * *" script.py input.json

# GitHub integration
rgrid connect github.com/user/repo
rgrid run repo/script.py input.json

# Account management
rgrid keys list
rgrid keys create --name "production"
rgrid keys revoke <key-id>
```

---

## Implementation Planning

### Epic Breakdown Required

This PRD must be decomposed into implementable epics and stories optimized for the 200k context limit workflow.

**Suggested Epic Structure:**

1. **Epic 1: CLI Foundation** - Core CLI framework, config management, auth
2. **Epic 2: Script Execution (Single)** - Upload script, execute remotely, return output
3. **Epic 3: Ray Integration** - Ray cluster setup, task distribution, result collection
4. **Epic 4: Hetzner Provisioning** - Auto-scaling workers, lifecycle management
5. **Epic 5: Batch Execution** - Pattern matching, parallel execution, progress tracking
6. **Epic 6: Observability** - Logs, status, execution history
7. **Epic 7: File/Output Handling** - Input upload, output collection, download
8. **Epic 8: Cost Tracking** - Per-execution billing, cost API, estimates
9. **Epic 9: Web Interfaces** - Marketing website (rgrid.dev) + Console dashboard (app.rgrid.dev)
10. **Epic 10: MVP Validation** - 100 image conversion test, DX polish, documentation

**Next Step:** Run `/bmad:bmm:workflows:create-epics-and-stories` to create implementation breakdown.

---

## Technical Stack & Architecture Decisions

**Context:** Technology choices that enable rapid MVP development while maintaining production scalability.

### Recommended Tech Stack

**MVP Approach: Python-First for Speed**

**Component: CLI**
```
Language: Python (Click framework)
Packaging: PyInstaller (→ standalone binary)
Distribution: PyPI (pip install rgrid-cli) + Homebrew

Why: Fastest iteration, easy integration with Ray
Alternative (Production): Rewrite in Go for single binary distribution
```

**Component: Control Plane (API + Orchestration)**
```
Language: Python
Framework: FastAPI (async, high performance)
API Documentation: Auto-generated OpenAPI/Swagger
Deployment: Fly.io (global edge deployment) or Railway

Why: FastAPI = Python's fastest framework, async support, auto-validation
Scales to: 10k+ req/sec (sufficient for MVP → growth)
Alternative (Scale): Rewrite in Go when hitting performance ceiling
```

**Component: Distributed Execution**
```
Framework: Ray (Python-native distributed computing)
Why: Battle-tested, handles task distribution/scheduling/result collection
Integrates naturally with Python control plane
Alternative: Temporal (for workflow-heavy use cases in growth phase)
```

**Component: Worker Nodes**
```
Provider: Hetzner Cloud (CX22 instances)
OS: Ubuntu 22.04 LTS
Runtime: Docker (for script isolation)
Orchestration: Ray cluster on ephemeral nodes

Why: Hetzner = 1/3 cost of AWS for equivalent compute
Alternative: Multi-cloud (AWS, GCP, Fly.io) via CPAL abstraction
```

**Component: Database**
```
Primary: PostgreSQL 15
Managed Service: Supabase (Postgres + realtime + auth)
Schema: Executions, Users, Projects, Workers, Costs, Logs

Why: Postgres = proven, reliable, excellent JSON support, good for queues
Tables: Simple relational model, no complex joins needed
Alternative: CockroachDB (for global distribution at scale)
```

**Component: Object Storage**
```
Service: MinIO (S3-compatible, self-hosted)
Usage: Script storage, input files, output artifacts, logs
Retention: 30 days default (configurable)

Why: S3-compatible API, self-hosted = cost control
Alternative: Cloudflare R2 (zero egress fees) or AWS S3
```

**Component: Authentication**
```
Service: Clerk (managed auth + user management)
Methods: Email/password, magic links
API Keys: Self-generated, bcrypt hashed

Why: Clerk handles email verification, user management, security
Alternative: Auth0 or custom (FastAPI + JWT)
```

**Component: Payments**
```
Service: Stripe
Features: Subscriptions, usage-based billing, Radar (fraud detection)

Why: Industry standard, excellent developer experience
```

**Component: Monitoring & Observability**
```
Metrics: Prometheus + Grafana
Logging: Structured JSON logs → Loki or Datadog
Errors: Sentry (error tracking + performance monitoring)
Uptime: Better Uptime or Checkly

Why: Standard stack, proven, good free tiers
```

**Component: Infrastructure as Code**
```
Tool: Terraform (or Pulumi with Python)
Managed: Hetzner Cloud provisioning, DNS, storage

Why: Reproducible infrastructure, version controlled
```

**Component: CDN & DDoS Protection**
```
Service: Cloudflare (free tier)
Features: Rate limiting, bot detection, caching, global CDN

Why: Essential for API protection, excellent free tier
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                        User                             │
└───────────────────────┬─────────────────────────────────┘
                        │
                   CLI (Python)
                        │
                        ├─ ~/.rgrid/credentials (API key)
                        │
                        ▼
            ┌───────────────────────┐
            │   Cloudflare CDN      │ ◄─── DDoS protection
            └───────────┬───────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Control Plane (FastAPI)  │
            │  - Auth (Clerk)       │
            │  - Billing (Stripe)   │
            │  - Job queue          │
            └───────────┬───────────┘
                        │
        ┌───────────────┼────────────────┐
        │               │                │
        ▼               ▼                ▼
 ┌──────────┐    ┌───────────┐   ┌──────────┐
 │ Postgres │    │   MinIO   │   │   Ray    │
 │(Supabase)│    │ (Storage) │   │ Cluster  │
 └──────────┘    └───────────┘   └─────┬────┘
                                        │
                        ┌───────────────┴──────────────┐
                        │                              │
                        ▼                              ▼
                ┌───────────────┐            ┌───────────────┐
                │ Worker Node 1 │            │ Worker Node N │
                │  (Hetzner)    │            │  (Hetzner)    │
                │               │            │               │
                │  - Docker     │            │  - Docker     │
                │  - Python     │            │  - Python     │
                │  - FFmpeg     │            │  - FFmpeg     │
                └───────────────┘            └───────────────┘
```

### Development Phases

**Phase 1: MVP (Python everywhere)**
- CLI: Python + Click → PyInstaller
- API: Python + FastAPI
- Workers: Ray (Python)
- Database: Postgres (Supabase)
- Storage: MinIO (self-hosted)
- Deploy: Fly.io (control plane) + Hetzner (workers)

**Pros:** Fastest time to market, unified language, easy debugging
**Cons:** Heavier binaries, potential performance ceiling
**Timeline:** 6-8 weeks to functional MVP

**Phase 2: Production Optimization (Selective rewrites)**
- CLI: Rewrite in Go (single <10MB binary)
- API: Keep Python or rewrite in Go (based on perf data)
- Workers: Keep Ray (works well)
- Database: Keep Postgres (proven)
- Storage: Migrate to R2 (zero egress costs)

**Pros:** Optimized where it matters, maintain velocity elsewhere
**Cons:** Multi-language maintenance
**Timeline:** 3-4 months after MVP launch

**Phase 3: Scale (Multi-region, multi-cloud)**
- Control plane: Multi-region deployment
- Workers: Multi-cloud (AWS, GCP, Hetzner)
- Database: Global Postgres (CockroachDB or PlanetScale)
- CDN: Full Cloudflare Enterprise

**Pros:** Global scale, redundancy, performance
**Timeline:** 12+ months, based on growth

### Technology Trade-offs

| Choice | MVP Decision | Production Alternative | When to Switch |
|--------|--------------|------------------------|----------------|
| **CLI Language** | Python (PyInstaller) | Go (native binary) | When binary size >50MB or startup >1s |
| **API Language** | Python (FastAPI) | Go (Gin/Echo) | When API latency >100ms p99 or scaling >10k req/s |
| **Database** | Postgres (Supabase) | CockroachDB | When need multi-region writes |
| **Storage** | MinIO (self-hosted) | Cloudflare R2 | When egress costs >$500/month |
| **Worker Provider** | Hetzner only | Multi-cloud | When Hetzner has outages or need regional diversity |
| **Auth** | Clerk | Custom (FastAPI) | When cost >$1k/month or need custom flows |

### Competitive Stack Analysis

**Modal (Reference):**
- Backend: Python
- Execution: Custom container orchestration
- Storage: S3
- Deployment: AWS
**Lesson:** Python works at scale for this use case

**Vercel (Inspiration):**
- Backend: Go (performance)
- Frontend: TypeScript
- Deployment: Global edge
**Lesson:** Go for performance-critical paths

**Fly.io (Infrastructure):**
- Control plane: Go/Rust
- Deployment: Multi-region
**Lesson:** Go/Rust for distributed systems

**Recommendation: Start Python, optimize selectively**

### Risk Mitigation

**Technical Risks:**
1. **Ray learning curve** - Mitigate: Use Ray's high-level API, not low-level primitives
2. **Python performance** - Mitigate: Async FastAPI, optimize hot paths, rewrite in Go if needed
3. **Hetzner reliability** - Mitigate: CPAL abstraction ready for multi-cloud from day 1

**Operational Risks:**
1. **Infrastructure costs** - Mitigate: Aggressive autoscaling, spot instances, cost monitoring
2. **Abuse/fraud** - Mitigate: Security section controls (tiers, limits, monitoring)
3. **Data loss** - Mitigate: Postgres backups, MinIO replication, execution log retention

---

## Architectural Future-Proofing Strategy

This PRD includes **six strategic architectural doors** that cost nothing in MVP but prevent major rewrites later:

**1. Execution Model Abstraction Layer (EMA)**
- **What:** Ray is the MVP engine, but all orchestration runs through a pluggable abstraction
- **Why:** Enables future support for Temporal, Inngest, Kubernetes, serverless, or custom executors
- **Impact:** Can swap/extend execution engines without CLI changes (FR65, NFR20)

**2. Cloud Provider Abstraction Layer (CPAL)**
- **What:** Hetzner is default, but provider logic is abstracted
- **Why:** Enables AWS, GCP, Fly.io, BYOC without refactoring
- **Impact:** Multi-cloud ready from day one (NFR18, NFR20)

**3. Runtime Plugin Architecture**
- **What:** Runtimes are pluggable providers, not hardcoded Docker images
- **Why:** Enables GPU runtimes, language-specific runtimes, custom environments
- **Impact:** Extensible runtime model without breaking changes (NFR20)

**4. Declarative Workflow Support (Future)**
- **What:** Control plane designed to eventually support DAGs, pipelines, event triggers
- **Why:** Script-first today, but can add workflows without breaking existing CLI
- **Impact:** Architecture supports future workflow orchestration

**5. Event Hooks (Internal)**
- **What:** Execution lifecycle events captured internally (not exposed in MVP)
- **Why:** Enables future webhooks, workflow triggers, audit logs, script chaining
- **Impact:** Event-driven automation possible later (FR64, NFR21)

**6. Execution Metadata Enrichment**
- **What:** Executions support tags, labels, custom attributes
- **Why:** Seed for analytics, AI-driven routing, cost prediction, dynamic optimization
- **Impact:** Metadata-driven intelligence and organization (FR62, FR63, NFR22)

**Design Philosophy:**
These architectural decisions follow the **"build small, but leave doors open"** principle used by AWS, Stripe, and Vercel. They:
- Add **zero complexity** to MVP implementation
- Avoid **1-2 major rewrites** in years 2-3
- Make the architecture **compatible with**:
  - Workflow orchestration and DAGs
  - Multi-cloud autoscaling
  - Multi-language support
  - Event-driven automation
  - AI-driven optimization

**Architect's Note:** When designing the control plane, CLI, and data models, these abstraction layers should be present as interfaces/protocols even if only one implementation exists in MVP. This costs nothing now but saves months of migration work later.

---

## Next Steps

1. **Detail the PRD with Clarifying Questions**
   - Answer questions about script storage, I/O conventions, dependency handling, use cases

2. **Epic Breakdown**
   - Run: `/bmad:bmm:workflows:create-epics-and-stories`
   - Transform requirements into implementable stories

3. **Architecture Design**
   - Run: `/bmad:bmm:workflows:architecture`
   - Design: CLI → API → Ray integration, Hetzner provisioning, file handling

4. **Proof of Concept**
   - Before full implementation, validate core concept:
   - Can you run a local script remotely with zero changes?
   - Does the CLI feel natural?
   - Does batch execution work smoothly?

---

## Document History & Evolution

**Version 1.0** - Decorator SDK Model (deprecated)
- `@remote` decorator for distributed Python functions
- Required code refactoring
- Target: Senior Python developers

**Version 2.0** - Paradigm Shift to Script Execution (deprecated)
- Script-first model
- Zero code changes required
- Target: Anyone who writes Python scripts

**Version 3.0** - Convention Over Configuration (current)
- **"Dropbox simplicity for developers"** design philosophy
- Global credentials (`~/.rgrid/credentials`), zero-config by default
- Three-level invisible caching (scripts, dependencies, inputs)
- Minimal CLI: 4 essential commands, 90% usage with `rgrid run`
- Conventional output handling (automatic download, organized directories)
- 77 functional requirements (up from 65)

**Key Design Decisions:**
- **Authentication:** Global credentials file (never in project), following AWS/Docker pattern
- **Caching:** Aggressive content-hashing at 3 levels (invisible to user)
- **Outputs:** Automatic download by convention, organized by input filename
- **CLI:** Minimal core (init, run, logs, cost), optional power-user commands
- **Philosophy:** Convention over configuration, invisible intelligence, progressive disclosure

---

_This PRD captures the essence of RGrid - **"Dropbox simplicity for developers"** applied to distributed script execution._

_**Core Paradigm:** Your scripts don't change. Just the execution location._

_**Design Philosophy:** The best interface is no interface. The best config is no config. 90% of executions use zero flags._

_**Architectural Strategy:** Build small today (CLI + Ray + Hetzner), but design with abstraction layers (EMA, CPAL, runtime plugins, event hooks, metadata, caching) that enable future growth without rewrites._

_Created through collaborative discovery between BMad and AI Product Manager (2025-11-14)._

**Changelog:**
- 2025-11-14: Initial creation - Decorator SDK model
- 2025-11-14: Pivoted to script execution service model
- 2025-11-14: Added architectural future-proofing strategy
- 2025-11-14: **Integrated "Dropbox simplicity" design philosophy with convention-over-configuration approach**
- 2025-11-15: **Added comprehensive competitive analysis vs Fly Machines, progressive permissions model for browser automation security, and real-time feedback/streaming logs implementation (FR78-FR82, NFR23-NFR25)**
