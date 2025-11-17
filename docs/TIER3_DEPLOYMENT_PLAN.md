# Tier 3 Deployment & Testing Plan (Beginner-Friendly)

**Date**: 2025-11-16
**Status**: READY FOR DEPLOYMENT
**Goal**: Deploy both staging AND production environments to a single VPS to save costs

---

## 🎯 Overview for Beginners

**What are we doing?**
We're setting up a real server (VPS = Virtual Private Server) on the internet where RGrid will run. This server will host TWO separate environments:
- **Staging** - For testing new features safely
- **Production** - For real users (when you're ready to launch)

**Why on the same VPS?**
Running both on one server saves money (~$6/month instead of $12/month). We'll isolate them using different ports and databases so they don't interfere with each other.

**What is Docker?**
Docker is like a shipping container for software. It packages your code with everything it needs to run (Python, libraries, etc.) so it works identically everywhere. Each "container" is isolated - if one crashes, it doesn't affect others.

**What is a database migration?**
It's like a version control system for your database schema. When you add a new column or table, you create a "migration" file that records the change. This lets you upgrade (or downgrade) your database structure safely.

---

## 💰 Cost Breakdown

**Single VPS Running Both Environments**:
- Hetzner CX21: €5.83/month (~$6.50 USD)
- 2 vCPU, 4GB RAM, 40GB SSD
- Sufficient for staging + production initially
- Can upgrade later when you have real traffic

**Domain**: rgrid.dev (already registered with NameSilo)
- Staging: `https://staging.rgrid.dev`
- Production: `https://api.rgrid.dev`
- Portainer (optional): `https://portainer.rgrid.dev`

**Total monthly cost**: ~$6.50 USD

---

## 🏗️ Architecture: Single VPS, Dual Environment

```
┌─────────────────────────────────────────────────────────────┐
│ Hetzner VPS (CX21) - Ubuntu 24.04 LTS                      │
│ Public IP: XXX.XXX.XXX.XXX                                 │
│                                                             │
│  STAGING ENVIRONMENT (Port 8001)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Docker Network: rgrid-staging                        │  │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────┐            │  │
│  │  │ API     │  │ Postgres │  │ MinIO   │            │  │
│  │  │ :8001   │  │ :5433    │  │ :9001   │            │  │
│  │  └─────────┘  └──────────┘  └─────────┘            │  │
│  │  ┌─────────┐                                        │  │
│  │  │ Runner  │  (executes test jobs)                  │  │
│  │  └─────────┘                                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  PRODUCTION ENVIRONMENT (Port 8000)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Docker Network: rgrid-production                     │  │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────┐            │  │
│  │  │ API     │  │ Postgres │  │ MinIO   │            │  │
│  │  │ :8000   │  │ :5432    │  │ :9000   │            │  │
│  │  └─────────┘  └──────────┘  └─────────┘            │  │
│  │  ┌─────────┐                                        │  │
│  │  │ Runner  │  (executes real jobs)                  │  │
│  │  └─────────┘                                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Portainer (Docker GUI): Port 9443                         │
│                                                             │
│  Firewall (UFW): SSH(22), HTTP(80), HTTPS(443)            │
│  NGINX Reverse Proxy: staging.rgrid.dev → :8001           │
│                       api.rgrid.dev → :8000                │
│                       portainer.rgrid.dev → :9443          │
└─────────────────────────────────────────────────────────────┘
```

**Why this works:**
- Different ports prevent conflicts (8000 vs 8001)
- Different databases keep data separate (5432 vs 5433)
- Docker networks isolate containers
- NGINX routes traffic based on domain name
- Firewall protects both environments

---

## 📋 Part 1: What YOU Must Do (Manual Setup - 60 minutes)

### Step 1: Provision the VPS (10 minutes)

**[FROM: Your computer's web browser]**

1. **Go to Hetzner Cloud**
   - Visit: https://console.hetzner.cloud
   - Log in (or create account if new)

2. **Create a new project**
   - Click "New Project"
   - Name: `rgrid`
   - Click "Create"

3. **Create a server**
   - Click "Add Server"
   - **Location**: Nuremberg, Germany (or closest to you)
   - **Image**: Ubuntu 24.04 LTS (latest stable release)
   - **Type**: CX21 (2 vCPU, 4GB RAM) - €5.83/month
   - **Networking**: Leave defaults (IPv4 + IPv6)
   - **SSH Keys**: Click "Add SSH Key"

4. **Add your SSH key** (if you don't have one yet):

   **[FROM: Your local machine terminal]**
   ```bash
   # Check if you have an SSH key
   ls ~/.ssh/id_ed25519.pub

   # If not found, create one:
   ssh-keygen -t ed25519 -C "your-email@example.com"
   # Press Enter 3 times (default location, no passphrase for automation)

   # Display your public key
   cat ~/.ssh/id_ed25519.pub
   # Copy this entire output
   ```

   **[BACK TO: Hetzner web console]**
   - Paste your public key
   - Name: "Your Computer"
   - Click "Add SSH Key"

5. **Finalize server creation**
   - **Name**: `rgrid-main`
   - Click "Create & Buy Now"
   - Wait 30-60 seconds for server to start
   - **Write down the IP address** (e.g., 162.55.123.45)

**What just happened?**
You rented a computer in a datacenter. It's now running Ubuntu 24.04 LTS (Long Term Support - maintained until 2029) and waiting for you to connect via SSH (Secure Shell - encrypted remote access).

---

### Step 2: Configure DNS (15 minutes)

**[FROM: NameSilo.com dashboard]**

1. **Log in to NameSilo**
   - Visit: https://www.namesilo.com
   - Log in to your account

2. **Go to DNS settings**
   - Click on your domain: `rgrid.dev`
   - Click "Manage DNS" or "DNS Records"

3. **Add DNS records** (one by one)

   **For Staging:**
   - **Type**: A
   - **Host**: staging
   - **Value**: <YOUR_VPS_IP> (e.g., 162.55.123.45)
   - **TTL**: 3600
   - Click "Submit"

   **For Production:**
   - **Type**: A
   - **Host**: api
   - **Value**: <YOUR_VPS_IP> (same IP as staging)
   - **TTL**: 3600
   - Click "Submit"

   **For Portainer (optional - Docker GUI):**
   - **Type**: A
   - **Host**: portainer
   - **Value**: <YOUR_VPS_IP> (same IP as others)
   - **TTL**: 3600
   - Click "Submit"

   **For Root domain (optional - for website later):**
   - **Type**: A
   - **Host**: @
   - **Value**: <YOUR_VPS_IP>
   - **TTL**: 3600
   - Click "Submit"

4. **Verify DNS propagation** (wait 5-10 minutes)

   **[FROM: Your local machine terminal]**
   ```bash
   # Test if DNS is working (might take 5-10 minutes)
   dig staging.rgrid.dev
   # Should show your VPS IP in the ANSWER section

   dig api.rgrid.dev
   # Should also show your VPS IP

   dig portainer.rgrid.dev
   # Should also show your VPS IP (if you added it)
   ```

**What just happened?**
You told the internet: "When someone types staging.rgrid.dev, send them to this IP address." DNS is like a phone book for the internet.

---

### Step 3: Initial SSH Setup & Security Hardening (20 minutes)

**[FROM: Your local machine terminal]**

1. **First connection to VPS**
   ```bash
   # Connect as root (initial setup only)
   ssh root@<YOUR_VPS_IP>
   # Example: ssh root@162.55.123.45

   # You should see a prompt like: root@rgrid-main:~#
   ```

   **What is SSH?** Secure Shell - it's like remote desktop for Linux, but text-based. You type commands on your computer, they execute on the VPS.

**[FROM: Inside the VPS - the rest of Step 3]**

2. **Update the system**
   ```bash
   # Update package lists (like "checking for updates")
   apt update

   # Install updates (like "install updates")
   apt upgrade -y
   # This might take 2-3 minutes
   ```

3. **Create a non-root user** (security best practice)
   ```bash
   # Create user called 'deploy' (you could use your name instead)
   adduser deploy
   # Enter a password when prompted (SAVE THIS PASSWORD!)
   # Press Enter for all other questions (accept defaults)

   # Give deploy user sudo access (ability to run admin commands)
   usermod -aG sudo deploy
   ```

   **Why not use root?** Root user has unlimited power. If an attacker gets root access, they own your server. Using a regular user with sudo is safer.

4. **Set up SSH key for deploy user**
   ```bash
   # Copy your SSH key to deploy user
   mkdir -p /home/deploy/.ssh
   cp ~/.ssh/authorized_keys /home/deploy/.ssh/
   chown -R deploy:deploy /home/deploy/.ssh
   chmod 700 /home/deploy/.ssh
   chmod 600 /home/deploy/.ssh/authorized_keys
   ```

5. **Harden SSH security**
   ```bash
   # Edit SSH configuration
   nano /etc/ssh/sshd_config

   # Find and change these lines (use Ctrl+W to search):
   # Change: PermitRootLogin yes
   # To:     PermitRootLogin no

   # Change: PasswordAuthentication yes
   # To:     PasswordAuthentication no

   # Save: Ctrl+O, Enter, Ctrl+X

   # Restart SSH service
   systemctl restart sshd
   ```

   **What did we do?** Disabled root login and password login. Now only your SSH key can access the server. Much more secure!

6. **Install and configure firewall**
   ```bash
   # Install UFW (Uncomplicated Firewall - it's actually simple!)
   apt install ufw -y

   # Allow SSH (port 22) - IMPORTANT: Do this first or you'll lock yourself out!
   ufw allow 22/tcp

   # Allow HTTP (port 80) for web traffic
   ufw allow 80/tcp

   # Allow HTTPS (port 443) for secure web traffic
   ufw allow 443/tcp

   # Enable firewall
   ufw --force enable

   # Check status
   ufw status verbose
   # You should see: Status: active
   ```

   **What is a firewall?** Think of it as a security guard. It blocks all incoming traffic except what you explicitly allow (SSH, HTTP, HTTPS).

7. **Install fail2ban** (brute-force protection)
   ```bash
   # Install fail2ban
   apt install fail2ban -y

   # Start it
   systemctl enable fail2ban
   systemctl start fail2ban
   ```

   **What is fail2ban?** It watches for repeated failed login attempts and temporarily bans the attacker's IP. Stops brute-force attacks.

8. **Set up automatic security updates**
   ```bash
   # Install unattended-upgrades
   apt install unattended-upgrades -y

   # Enable it
   dpkg-reconfigure -plow unattended-upgrades
   # Select "Yes" when prompted
   ```

   **Why?** Security patches install automatically. One less thing to worry about.

9. **Exit and reconnect as deploy user**
   ```bash
   # Exit from root
   exit

   # You're back on your local machine now
   ```

**[FROM: Your local machine terminal]**

10. **Test new user connection**
    ```bash
    # Connect as deploy user
    ssh deploy@<YOUR_VPS_IP>
    # Example: ssh deploy@162.55.123.45

    # You should see: deploy@rgrid-main:~$

    # Try root (should fail - this is good!)
    ssh root@<YOUR_VPS_IP>
    # Should say: Permission denied
    ```

**Security checklist** ✅
- [ ] Non-root user created
- [ ] Root login disabled
- [ ] Password authentication disabled (SSH key only)
- [ ] Firewall enabled (SSH, HTTP, HTTPS only)
- [ ] Fail2ban protecting against brute-force
- [ ] Automatic security updates enabled

---

### Step 4: Create Environment Files & Manage Credentials (15 minutes)

**[FROM: Your local machine terminal]**

1. **Create credentials directory** (local, not on VPS yet)
   ```bash
   # Create a secure directory on your local machine
   mkdir -p ~/.rgrid-credentials
   chmod 700 ~/.rgrid-credentials
   cd ~/.rgrid-credentials
   ```

2. **Generate secure passwords**
   ```bash
   # Generate database passwords
   echo "STAGING_DB_PASSWORD=$(openssl rand -hex 16)" >> credentials.txt
   echo "PRODUCTION_DB_PASSWORD=$(openssl rand -hex 16)" >> credentials.txt

   # Generate MinIO credentials
   echo "STAGING_MINIO_ACCESS=$(openssl rand -hex 16)" >> credentials.txt
   echo "STAGING_MINIO_SECRET=$(openssl rand -hex 32)" >> credentials.txt
   echo "PRODUCTION_MINIO_ACCESS=$(openssl rand -hex 16)" >> credentials.txt
   echo "PRODUCTION_MINIO_SECRET=$(openssl rand -hex 32)" >> credentials.txt

   # Display credentials
   cat credentials.txt
   # SAVE THESE! You'll need them in the next step.
   ```

3. **Create staging environment file**
   ```bash
   # Create staging.env
   cat > staging.env <<'EOF'
# RGrid Staging Environment
# DO NOT COMMIT TO GIT!

# Database
DATABASE_URL=postgresql://rgrid_staging:<STAGING_DB_PASSWORD>@localhost:5433/rgrid_staging

# MinIO
MINIO_ENDPOINT=localhost:9001
MINIO_ACCESS_KEY=<STAGING_MINIO_ACCESS>
MINIO_SECRET_KEY=<STAGING_MINIO_SECRET>
MINIO_BUCKET=rgrid-staging
MINIO_SECURE=false

# API
API_HOST=0.0.0.0
API_PORT=8001
API_ENV=staging

# Execution Settings
EXECUTION_TIMEOUT=300
CONTAINER_MEMORY_LIMIT=512m
CONTAINER_CPU_LIMIT=1.0

# Docker Network
DOCKER_NETWORK=rgrid-staging
EOF
   ```

4. **Create production environment file**
   ```bash
   # Create production.env
   cat > production.env <<'EOF'
# RGrid Production Environment
# DO NOT COMMIT TO GIT!

# Database
DATABASE_URL=postgresql://rgrid_production:<PRODUCTION_DB_PASSWORD>@localhost:5432/rgrid_production

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=<PRODUCTION_MINIO_ACCESS>
MINIO_SECRET_KEY=<PRODUCTION_MINIO_SECRET>
MINIO_BUCKET=rgrid-production
MINIO_SECURE=false

# API
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=production

# Execution Settings
EXECUTION_TIMEOUT=300
CONTAINER_MEMORY_LIMIT=512m
CONTAINER_CPU_LIMIT=1.0

# Docker Network
DOCKER_NETWORK=rgrid-production
EOF
   ```

5. **Replace placeholders with actual passwords**
   ```bash
   # Open staging.env and replace:
   # <STAGING_DB_PASSWORD> with value from credentials.txt
   # <STAGING_MINIO_ACCESS> with value from credentials.txt
   # <STAGING_MINIO_SECRET> with value from credentials.txt
   nano staging.env
   # Ctrl+X, Y, Enter to save

   # Same for production.env
   nano production.env
   # Ctrl+X, Y, Enter to save
   ```

6. **Store credentials in password manager** (CRITICAL!)

   **Option A: 1Password, LastPass, Bitwarden (recommended)**
   - Create a new secure note called "RGrid VPS Credentials"
   - Paste contents of `credentials.txt`
   - Attach `staging.env` and `production.env` files
   - Delete local copies after uploading:
     ```bash
     # After uploading to password manager:
     shred -u credentials.txt  # Secure delete
     ```

   **Option B: Encrypted file on your computer**
   ```bash
   # Encrypt with GPG
   gpg -c credentials.txt
   # Enter a strong passphrase
   # Creates credentials.txt.gpg

   # Delete original
   shred -u credentials.txt

   # To decrypt later:
   # gpg credentials.txt.gpg
   ```

   **⚠️ NEVER commit .env files to Git!**

7. **Copy environment files to VPS**
   ```bash
   # Copy staging.env
   scp staging.env deploy@<YOUR_VPS_IP>:~/staging.env

   # Copy production.env
   scp production.env deploy@<YOUR_VPS_IP>:~/production.env

   # Verify
   ssh deploy@<YOUR_VPS_IP> "ls -la ~/*.env"
   # Should show: staging.env and production.env
   ```

**Credential Security Best Practices**:
- ✅ Store in password manager (1Password, LastPass, etc.)
- ✅ Use different passwords for staging vs production
- ✅ Never commit to Git (add `*.env` to `.gitignore`)
- ✅ Use SSH keys instead of passwords
- ✅ Rotate passwords every 90 days (for production)

**Where to store what:**

| Credential Type | Where to Store | Why |
|----------------|----------------|-----|
| SSH Private Key | `~/.ssh/id_ed25519` (local machine) | Encrypted by OS, never share |
| Database Passwords | Password manager + VPS .env files | Encrypted at rest, access controlled |
| MinIO Keys | Password manager + VPS .env files | Encrypted at rest, access controlled |
| VPS Root Password | Password manager only | Emergency access only |
| Deploy User Password | Password manager only | Backup if SSH key lost |

---

## 📋 Part 2: Automated Deployment (Agent or Manual - 45 minutes)

### Option A: Agent-Assisted Deployment (Recommended)

**[FROM: Your local machine - BMAD agent session]**

Create a file called `deploy-rgrid.md` and give it to a BMAD agent:

```markdown
# Deploy RGrid Dual Environment to VPS

## Context
- VPS IP: <YOUR_VPS_IP>
- SSH User: deploy
- SSH Key: ~/.ssh/id_ed25519
- Environment files: staging.env and production.env already on VPS

## Task
Deploy both staging and production environments to the VPS. Follow all steps sequentially.

## Deployment Steps

### 1. Install Base Dependencies

[VPS] Connect and install Docker, Docker Compose, Python 3.11:

```bash
ssh deploy@<YOUR_VPS_IP>

# Update system
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker deploy
rm get-docker.sh

# Install Docker Compose
sudo apt install docker-compose -y

# Install Python 3.11 and venv
sudo apt install python3.11 python3.11-venv python3-pip git -y

# Install PostgreSQL client (for testing)
sudo apt install postgresql-client -y

# Install NGINX (reverse proxy)
sudo apt install nginx -y

# Log out and back in for Docker group to take effect
exit
```

[LOCAL] Reconnect:
```bash
ssh deploy@<YOUR_VPS_IP>
```

### 1.5. Install Portainer (Docker GUI) - Optional but Recommended

[VPS] Install Portainer for visual Docker management:

```bash
# Create volume for Portainer data
docker volume create portainer_data

# Run Portainer container
docker run -d \
  -p 9443:9443 \
  -p 8000:8000 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest

# Verify Portainer is running
docker ps | grep portainer
```

**What is Portainer?**
A web-based GUI for Docker that makes it easy to:
- See all containers at a glance (running, stopped, resource usage)
- View real-time logs without terminal commands
- Monitor CPU/RAM usage per container
- Access container terminals via browser
- Manage networks, volumes, and images visually

**Secure Access Options:**

**Option A: SSH Tunnel (Recommended for testing)**

[LOCAL] Create secure tunnel:
```bash
# Open SSH tunnel (keeps Portainer off public internet)
ssh -L 9443:localhost:9443 deploy@<YOUR_VPS_IP>

# Keep this terminal open, then visit:
# https://localhost:9443
```

**Option B: Subdomain with SSL (For permanent access)**

We'll configure this later with NGINX after setting up domains. This gives you `https://portainer.rgrid.dev`

**First-time Setup:**

1. **[LOCAL]** Open browser to `https://localhost:9443` (via SSH tunnel)
2. **Create admin password** (12+ characters, save to password manager!)
3. Click **"Get Started"**
4. You'll see the Docker environment dashboard

**What you'll see:**
- 📊 Dashboard showing containers, images, volumes, networks
- 📦 Container list with status (green = running)
- 📝 Click any container to view logs
- 📈 Real-time CPU/RAM graphs
- 🖥️ Built-in terminal access to containers

**Beginner Tip:** Portainer is excellent for learning Docker! Run commands in terminal, then check Portainer to see what changed visually.

### 2. Clone Repository

[VPS] Clone the RGrid repository:

```bash
cd ~
git clone https://github.com/sna4ever/rgrid.git
cd rgrid
git checkout main
```

### 3. Set Up Docker Networks

[VPS] Create isolated networks for each environment:

```bash
# Create staging network
docker network create rgrid-staging

# Create production network
docker network create rgrid-production

# Verify
docker network ls | grep rgrid
```

### 4. Deploy Staging Environment

[VPS] Set up staging databases and services:

```bash
# Create staging docker-compose
cat > ~/rgrid/docker-compose.staging.yml <<'EOF'
version: '3.8'

services:
  postgres-staging:
    image: postgres:15
    container_name: postgres-staging
    environment:
      POSTGRES_USER: rgrid_staging
      POSTGRES_PASSWORD: ${STAGING_DB_PASSWORD}
      POSTGRES_DB: rgrid_staging
    ports:
      - "5433:5432"
    volumes:
      - postgres_staging_data:/var/lib/postgresql/data
    networks:
      - rgrid-staging
    restart: unless-stopped

  minio-staging:
    image: minio/minio:latest
    container_name: minio-staging
    command: server /data --console-address ":9091"
    environment:
      MINIO_ROOT_USER: ${STAGING_MINIO_ACCESS}
      MINIO_ROOT_PASSWORD: ${STAGING_MINIO_SECRET}
    ports:
      - "9001:9000"
      - "9091:9091"
    volumes:
      - minio_staging_data:/data
    networks:
      - rgrid-staging
    restart: unless-stopped

networks:
  rgrid-staging:
    external: true

volumes:
  postgres_staging_data:
  minio_staging_data:
EOF

# Start staging services
cd ~/rgrid
docker-compose -f docker-compose.staging.yml --env-file ~/staging.env up -d

# Wait for services to be ready
sleep 15

# Verify staging services
docker ps | grep staging
```

### 5. Deploy Production Environment

[VPS] Set up production databases and services:

```bash
# Create production docker-compose
cat > ~/rgrid/docker-compose.production.yml <<'EOF'
version: '3.8'

services:
  postgres-production:
    image: postgres:15
    container_name: postgres-production
    environment:
      POSTGRES_USER: rgrid_production
      POSTGRES_PASSWORD: ${PRODUCTION_DB_PASSWORD}
      POSTGRES_DB: rgrid_production
    ports:
      - "5432:5432"
    volumes:
      - postgres_production_data:/var/lib/postgresql/data
    networks:
      - rgrid-production
    restart: unless-stopped

  minio-production:
    image: minio/minio:latest
    container_name: minio-production
    command: server /data --console-address ":9090"
    environment:
      MINIO_ROOT_USER: ${PRODUCTION_MINIO_ACCESS}
      MINIO_ROOT_PASSWORD: ${PRODUCTION_MINIO_SECRET}
    ports:
      - "9000:9000"
      - "9090:9090"
    volumes:
      - minio_production_data:/data
    networks:
      - rgrid-production
    restart: unless-stopped

networks:
  rgrid-production:
    external: true

volumes:
  postgres_production_data:
  minio_production_data:
EOF

# Start production services
cd ~/rgrid
docker-compose -f docker-compose.production.yml --env-file ~/production.env up -d

# Wait for services
sleep 15

# Verify production services
docker ps | grep production
```

### 6. Set Up Python Environment

[VPS] Create virtual environment and install dependencies:

```bash
cd ~/rgrid

# Create virtual environment
python3.11 -m venv venv

# Activate it
source venv/bin/activate

# Install API dependencies
pip install --upgrade pip
pip install -r api/requirements.txt

# Install runner dependencies
pip install -r runner/requirements.txt

# Install CLI dependencies
pip install -r cli/requirements.txt
```

### 7. Run Database Migrations

[VPS] Apply Alembic migrations for both environments:

```bash
# Staging migrations
cd ~/rgrid/api
source ~/rgrid/venv/bin/activate
export $(cat ~/staging.env | xargs)
alembic upgrade head

# Production migrations
export $(cat ~/production.env | xargs)
alembic upgrade head

cd ~
```

### 8. Create MinIO Buckets

[VPS] Create S3 buckets for both environments:

```bash
# Install MinIO client
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# Configure staging MinIO
mc alias set staging http://localhost:9001 ${STAGING_MINIO_ACCESS} ${STAGING_MINIO_SECRET}
mc mb staging/rgrid-staging
mc anonymous set download staging/rgrid-staging

# Configure production MinIO
mc alias set production http://localhost:9000 ${PRODUCTION_MINIO_ACCESS} ${PRODUCTION_MINIO_SECRET}
mc mb production/rgrid-production
mc anonymous set download production/rgrid-production

# Verify buckets
mc ls staging
mc ls production
```

### 9. Deploy API Services (Systemd)

[VPS] Create systemd services for both APIs:

```bash
# Staging API service
sudo tee /etc/systemd/system/rgrid-api-staging.service > /dev/null <<'EOF'
[Unit]
Description=RGrid API (Staging)
After=network.target docker.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/rgrid/api
EnvironmentFile=/home/deploy/staging.env
ExecStart=/home/deploy/rgrid/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Production API service
sudo tee /etc/systemd/system/rgrid-api-production.service > /dev/null <<'EOF'
[Unit]
Description=RGrid API (Production)
After=network.target docker.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/rgrid/api
EnvironmentFile=/home/deploy/production.env
ExecStart=/home/deploy/rgrid/venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Start staging API
sudo systemctl enable rgrid-api-staging
sudo systemctl start rgrid-api-staging

# Start production API
sudo systemctl enable rgrid-api-production
sudo systemctl start rgrid-api-production

# Check status
sudo systemctl status rgrid-api-staging
sudo systemctl status rgrid-api-production
```

### 10. Deploy Runner Services (Systemd)

[VPS] Create systemd services for both runners:

```bash
# Staging runner service
sudo tee /etc/systemd/system/rgrid-runner-staging.service > /dev/null <<'EOF'
[Unit]
Description=RGrid Runner (Staging)
After=network.target docker.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/rgrid/runner
EnvironmentFile=/home/deploy/staging.env
ExecStart=/home/deploy/rgrid/venv/bin/python -m runner.worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Production runner service
sudo tee /etc/systemd/system/rgrid-runner-production.service > /dev/null <<'EOF'
[Unit]
Description=RGrid Runner (Production)
After=network.target docker.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/rgrid/runner
EnvironmentFile=/home/deploy/production.env
ExecStart=/home/deploy/rgrid/venv/bin/python -m runner.worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Start staging runner
sudo systemctl enable rgrid-runner-staging
sudo systemctl start rgrid-runner-staging

# Start production runner
sudo systemctl enable rgrid-runner-production
sudo systemctl start rgrid-runner-production

# Check status
sudo systemctl status rgrid-runner-staging
sudo systemctl status rgrid-runner-production
```

### 11. Configure NGINX Reverse Proxy

[VPS] Set up NGINX to route traffic by domain:

```bash
# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Create staging config
sudo tee /etc/nginx/sites-available/rgrid-staging <<'EOF'
server {
    listen 80;
    server_name staging.rgrid.dev;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Create production config
sudo tee /etc/nginx/sites-available/rgrid-production <<'EOF'
server {
    listen 80;
    server_name api.rgrid.dev;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Create Portainer config (optional - for permanent web access)
sudo tee /etc/nginx/sites-available/rgrid-portainer <<'EOF'
server {
    listen 80;
    server_name portainer.rgrid.dev;

    location / {
        proxy_pass https://localhost:9443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for websockets
        proxy_read_timeout 86400;
    }
}
EOF

# Enable sites
sudo ln -s /etc/nginx/sites-available/rgrid-staging /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/rgrid-production /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/rgrid-portainer /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload NGINX
sudo systemctl reload nginx
```

### 12. Install SSL Certificates (Let's Encrypt)

[VPS] Set up HTTPS with free SSL certificates:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate for staging
sudo certbot --nginx -d staging.rgrid.dev --non-interactive --agree-tos -m your-email@example.com

# Get certificate for production
sudo certbot --nginx -d api.rgrid.dev --non-interactive --agree-tos -m your-email@example.com

# Get certificate for Portainer (optional - if you want permanent web access)
sudo certbot --nginx -d portainer.rgrid.dev --non-interactive --agree-tos -m your-email@example.com

# Certbot will automatically configure NGINX for HTTPS
# Certificates auto-renew every 90 days

# Note: You'll need to add portainer.rgrid.dev to NameSilo DNS (same IP as other subdomains)
```

### 13. Verify Deployment

[VPS] Check all services are running:

```bash
# Check Docker containers
docker ps

# Should see 4 containers:
# - postgres-staging
# - minio-staging
# - postgres-production
# - minio-production

# Check systemd services
sudo systemctl status rgrid-api-staging
sudo systemctl status rgrid-api-production
sudo systemctl status rgrid-runner-staging
sudo systemctl status rgrid-runner-production

# All should show: active (running)

# Test APIs locally
curl http://localhost:8001/health
curl http://localhost:8000/health

# Both should return: {"status":"healthy"}
```

[LOCAL] Test from your computer:

```bash
# Test staging
curl https://staging.rgrid.dev/health

# Test production
curl https://api.rgrid.dev/health

# Both should return: {"status":"healthy"}
```

## Success Criteria

All checks must pass:
- [ ] 4 Docker containers running (postgres + minio for both envs)
- [ ] 4 systemd services active (API + runner for both envs)
- [ ] NGINX routing correctly by domain
- [ ] SSL certificates installed and working
- [ ] Database migrations applied for both envs
- [ ] MinIO buckets created for both envs
- [ ] Health endpoints responding on both staging and production
```

**To use this:**
```bash
# [LOCAL] In a BMAD agent session:
execute deploy-rgrid.md
```

The agent will SSH into your VPS and execute all steps automatically.

---

### Option B: Manual Deployment

If you prefer to do it yourself, follow all the steps in the `deploy-rgrid.md` file above, executing each command block sequentially.

**Estimated time**: 45-60 minutes

---

## 🧪 Testing Plan (Both Environments)

### Test Each Tier 3 Feature on Staging First, Then Production

For each test, run on **staging** first. If it passes, run on **production**.

#### Test 1: Database Migrations (Story NEW-3)

**[LOCAL]** Test migrations work:

```bash
# SSH into VPS
ssh deploy@<YOUR_VPS_IP>

# Test staging migrations
cd ~/rgrid/api
source ~/rgrid/venv/bin/activate
export $(cat ~/staging.env | xargs)

# Check current migration
alembic current

# Create test migration
alembic revision -m "test_migration"
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# ✅ PASS if no errors

# Test production migrations
export $(cat ~/production.env | xargs)
alembic current
# ✅ Should show same migration version
```

---

#### Test 2: Resource Limits (Story NEW-5)

**[LOCAL]** Test container memory limits:

```bash
# Create memory-hogging script
cat > /tmp/memory_hog.py <<'EOF'
import numpy as np
arrays = []
for i in range(100):
    arrays.append(np.zeros((256, 1024, 1024)))  # Try to allocate 25GB
    print(f"Allocated {i+1} GB")
EOF

# Configure CLI for staging
export RGRID_API_URL=https://staging.rgrid.dev

# Run script (should be killed at 512MB)
rgrid run /tmp/memory_hog.py

# Check logs
rgrid logs <exec_id>
# Should show: Container killed (out of memory)

# ✅ PASS if container was killed before exhausting server RAM

# Test on production
export RGRID_API_URL=https://api.rgrid.dev
rgrid run /tmp/memory_hog.py
# Should also be killed
```

---

#### Test 3: Job Timeout (Story NEW-6)

**[LOCAL]** Test job timeouts:

```bash
# Create infinite loop script
cat > /tmp/infinite_loop.py <<'EOF'
import time
while True:
    time.sleep(1)
    print("Still running...")
EOF

# Test on staging
export RGRID_API_URL=https://staging.rgrid.dev
rgrid run /tmp/infinite_loop.py

# Wait 5 minutes (timeout is 300s)
# After 5 minutes, check status
rgrid status <exec_id>
# Should show: failed - Timeout after 300s

# ✅ PASS if job timed out correctly

# Test on production
export RGRID_API_URL=https://api.rgrid.dev
rgrid run /tmp/infinite_loop.py
# Wait 5 minutes, verify timeout
```

---

#### Test 4: Pre-configured Runtimes (Story 2-3)

**[LOCAL]** Test default runtime:

```bash
# Create simple script
cat > /tmp/hello.py <<'EOF'
import sys
print(f"Hello from Python {sys.version}")
EOF

# Test on staging (no --runtime flag)
export RGRID_API_URL=https://staging.rgrid.dev
rgrid run /tmp/hello.py

# Check logs
rgrid logs <exec_id>
# Should show: Hello from Python 3.11.x

# ✅ PASS if default runtime worked

# Test on production
export RGRID_API_URL=https://api.rgrid.dev
rgrid run /tmp/hello.py
```

---

#### Test 5: Auto-detect Dependencies (Story 2-4)

**[LOCAL]** Test requirements.txt auto-install:

```bash
# Create directory for test
mkdir -p /tmp/rgrid-test
cd /tmp/rgrid-test

# Create script using requests
cat > test_requests.py <<'EOF'
import requests
response = requests.get('https://httpbin.org/get')
print(f"Status: {response.status_code}")
EOF

# Create requirements.txt
cat > requirements.txt <<'EOF'
requests==2.31.0
EOF

# Test on staging
export RGRID_API_URL=https://staging.rgrid.dev
rgrid run test_requests.py

# Check logs
rgrid logs <exec_id>
# Should show: Installing dependencies... then Status: 200

# ✅ PASS if dependencies auto-installed

# Test on production
export RGRID_API_URL=https://api.rgrid.dev
rgrid run test_requests.py
```

---

#### Test 6: Dead Worker Detection (Story NEW-7)

**[VPS]** Test dead worker handling:

```bash
# Start a long-running job on staging
# [LOCAL]
export RGRID_API_URL=https://staging.rgrid.dev
rgrid run /tmp/infinite_loop.py
# Note the exec_id

# [VPS] Kill the staging runner
ssh deploy@<YOUR_VPS_IP>
sudo systemctl stop rgrid-runner-staging

# Wait 2 minutes for heartbeat timeout
sleep 120

# [LOCAL] Check job status
rgrid status <exec_id>
# Should show: failed - Worker died unexpectedly

# [VPS] Restart runner
sudo systemctl start rgrid-runner-staging

# ✅ PASS if job was marked as failed

# Test on production
# [LOCAL]
export RGRID_API_URL=https://api.rgrid.dev
rgrid run /tmp/infinite_loop.py

# [VPS]
sudo systemctl stop rgrid-runner-production
sleep 120
sudo systemctl start rgrid-runner-production

# [LOCAL]
rgrid status <exec_id>
# Should be failed
```

---

#### Test 7: Structured Error Messages (Story 10-4)

**[LOCAL]** Test error clarity:

```bash
# Test file not found
export RGRID_API_URL=https://staging.rgrid.dev
rgrid run nonexistent.py

# Should show:
# ❌ Validation Error: Script file not found
#    💡 Suggestions: Check the file path...

# ✅ PASS if error message is clear and actionable

# Test on production
export RGRID_API_URL=https://api.rgrid.dev
rgrid run nonexistent.py
```

---

#### Test 8: Large File Streaming (Story 7-6)

**[LOCAL]** Test large file upload:

```bash
# Create 500MB file
dd if=/dev/zero of=/tmp/large_test.dat bs=1M count=500

# Create processing script
cat > /tmp/process_large.py <<'EOF'
import sys
file_path = sys.argv[1]
size = len(open(file_path, 'rb').read())
print(f"Processed {size} bytes")
EOF

# Test on staging
export RGRID_API_URL=https://staging.rgrid.dev
rgrid run /tmp/process_large.py /tmp/large_test.dat

# Watch for progress bar during upload
# Check completion
rgrid logs <exec_id>
# Should show: Processed 524288000 bytes

# ✅ PASS if large file uploaded and processed

# [VPS] Check memory didn't spike
ssh deploy@<YOUR_VPS_IP>
htop  # Memory should stay under 2GB

# Test on production
export RGRID_API_URL=https://api.rgrid.dev
rgrid run /tmp/process_large.py /tmp/large_test.dat
```

---

## ✅ Success Criteria

All 8 tests pass on BOTH staging and production:

**Staging**:
- [ ] Database migrations work
- [ ] Resource limits enforced
- [ ] Job timeouts work
- [ ] Default runtime works
- [ ] Dependencies auto-installed
- [ ] Dead worker detection works
- [ ] Clear error messages
- [ ] Large file streaming works

**Production**:
- [ ] All 8 tests also pass
- [ ] No errors in logs
- [ ] Services stable for 24 hours

**When all pass**: Tier 3 is VERIFIED production-ready on both environments ✅

---

## 📊 Monitoring & Maintenance

### Check Service Health

**[VPS]** Daily health check:

```bash
ssh deploy@<YOUR_VPS_IP>

# Check all services
sudo systemctl status rgrid-api-staging
sudo systemctl status rgrid-api-production
sudo systemctl status rgrid-runner-staging
sudo systemctl status rgrid-runner-production

# Check Docker containers
docker ps

# Check disk space
df -h

# Check memory usage
free -h
```

### View Logs

**[VPS]** Check logs when debugging:

```bash
# API logs
sudo journalctl -u rgrid-api-staging -n 50 --no-pager
sudo journalctl -u rgrid-api-production -n 50 --no-pager

# Runner logs
sudo journalctl -u rgrid-runner-staging -n 50 --no-pager
sudo journalctl -u rgrid-runner-production -n 50 --no-pager

# Follow logs in real-time
sudo journalctl -u rgrid-api-staging -f
```

### Restart Services

**[VPS]** If something breaks:

```bash
# Restart specific service
sudo systemctl restart rgrid-api-staging

# Restart all services
sudo systemctl restart rgrid-api-staging rgrid-api-production rgrid-runner-staging rgrid-runner-production

# Restart Docker containers
docker restart postgres-staging minio-staging postgres-production minio-production
```

---

## 🔄 Updating Code (Deploy New Features)

### Staging Deployment (Test First)

**[VPS]** Deploy to staging first:

```bash
ssh deploy@<YOUR_VPS_IP>

# Pull latest code
cd ~/rgrid
git pull origin main

# Activate venv
source venv/bin/activate

# Install any new dependencies
pip install -r api/requirements.txt
pip install -r runner/requirements.txt

# Run migrations (staging)
cd api
export $(cat ~/staging.env | xargs)
alembic upgrade head

# Restart staging services
sudo systemctl restart rgrid-api-staging
sudo systemctl restart rgrid-runner-staging

# Check health
curl http://localhost:8001/health
```

### Production Deployment (After Staging Works)

**[VPS]** Deploy to production:

```bash
# Run migrations (production)
export $(cat ~/production.env | xargs)
alembic upgrade head

# Restart production services
sudo systemctl restart rgrid-api-production
sudo systemctl restart rgrid-runner-production

# Check health
curl http://localhost:8000/health
```

**Best Practice**: Always test on staging for at least 1 hour before deploying to production.

---

## 🚨 Rollback Plan

### If Staging Breaks

**[VPS]** Reset staging environment:

```bash
# Stop services
sudo systemctl stop rgrid-api-staging rgrid-runner-staging
docker-compose -f docker-compose.staging.yml down

# Delete data (if needed)
docker volume rm rgrid_postgres_staging_data rgrid_minio_staging_data

# Re-deploy from Part 2, Step 4
```

### If Production Breaks

**[VPS]** Emergency rollback:

```bash
# Stop production services
sudo systemctl stop rgrid-api-production rgrid-runner-production

# Revert code
cd ~/rgrid
git log --oneline -5  # Find last working commit
git checkout <commit-hash>

# Downgrade database (if migration broke it)
cd api
export $(cat ~/production.env | xargs)
alembic downgrade -1  # Go back one migration

# Restart services
sudo systemctl start rgrid-api-production rgrid-runner-production

# Verify
curl http://localhost:8000/health
```

**Critical**: Always have a database backup before deploying to production!

### Database Backup (Set Up Now!)

**[VPS]** Create automated backups:

```bash
# Create backup script
cat > ~/backup-databases.sh <<'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)

# Backup staging
docker exec postgres-staging pg_dump -U rgrid_staging rgrid_staging > ~/backups/staging_$DATE.sql

# Backup production
docker exec postgres-production pg_dump -U rgrid_production rgrid_production > ~/backups/production_$DATE.sql

# Keep only last 7 days
find ~/backups/ -name "*.sql" -mtime +7 -delete
EOF

chmod +x ~/backup-databases.sh
mkdir -p ~/backups

# Add to crontab (run daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/deploy/backup-databases.sh") | crontab -
```

---

## 💡 Cost Optimization Tips

1. **Single VPS**: You're already doing this! Saves $6/month.

2. **Scale down when not testing**:
   - Stop staging services when not actively testing
   - Keep production running 24/7

3. **Monitor disk usage**:
   ```bash
   # Clean up old Docker images monthly
   docker system prune -a -f
   ```

4. **Upgrade only when needed**:
   - CX21 is sufficient for 100-1000 jobs/day
   - Upgrade to CX31 (4 vCPU, 8GB) when you hit limits

---

## 🎓 Beginner Glossary

- **VPS**: Virtual Private Server - A computer you rent in a datacenter
- **SSH**: Secure Shell - Encrypted remote access to your server
- **Docker**: Containerization platform - packages apps with dependencies
- **Portainer**: Web-based GUI for Docker - visual management of containers
- **systemd**: Linux service manager - keeps apps running, restarts on crash
- **NGINX**: Reverse proxy - routes web traffic to correct service
- **Firewall (UFW)**: Security layer - blocks unauthorized access
- **SSL/TLS**: Encryption for HTTPS - secures data in transit
- **DNS**: Domain Name System - translates rgrid.dev to IP address
- **PostgreSQL**: Relational database - stores structured data
- **MinIO**: S3-compatible object storage - stores files/artifacts
- **Alembic**: Database migration tool - version control for DB schema
- **SSH Tunnel**: Secure encrypted connection to access remote services locally

---

## 📞 Getting Help

**If something goes wrong:**

1. **Check service status**:
   ```bash
   [VPS] sudo systemctl status rgrid-api-staging
   ```

2. **Check logs**:
   ```bash
   [VPS] sudo journalctl -u rgrid-api-staging -n 100 --no-pager
   ```

3. **Ask in this session**: Share the error message and I'll help debug

4. **GitHub Issues**: Create an issue at https://github.com/sna4ever/rgrid/issues

---

## 🎯 Next Steps After Deployment

Once all tests pass:

1. **Document your setup** - Create `DEPLOYMENT_NOTES.md` with your specific IPs, domains, etc.

2. **Set up monitoring** (optional but recommended):
   - Install Uptime Kuma or similar
   - Get alerts if services go down

3. **Start using staging** - Test all new features here first

4. **Begin Tier 4** - Distributed Cloud (Ray + Hetzner workers)

5. **Consider production launch** - When ready for real users

---

**You now have a production-ready RGrid deployment running both staging and production on a single VPS!** 🎉
