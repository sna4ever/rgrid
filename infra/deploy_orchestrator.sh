#!/bin/bash
#
# Deploy RGrid Orchestrator to control plane
#
set -e

echo "=== RGrid Orchestrator Deployment ==="

# Configuration
DEPLOY_USER="rgrid"
DEPLOY_DIR="/opt/rgrid"
VENV_DIR="$DEPLOY_DIR/venv"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

# Create user if doesn't exist
if ! id "$DEPLOY_USER" &>/dev/null; then
    echo "Creating user $DEPLOY_USER..."
    useradd -r -s /bin/bash -d "$DEPLOY_DIR" "$DEPLOY_USER"
fi

# Create deployment directory
echo "Creating deployment directory..."
mkdir -p "$DEPLOY_DIR"

# Copy application files
echo "Copying application files..."
rsync -av --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    /home/sune/Projects/rgrid/ "$DEPLOY_DIR/"

# Set ownership
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"

# Create virtual environment
echo "Creating Python virtual environment..."
sudo -u "$DEPLOY_USER" python3 -m venv "$VENV_DIR"

# Install dependencies
echo "Installing Python dependencies..."
sudo -u "$DEPLOY_USER" "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u "$DEPLOY_USER" "$VENV_DIR/bin/pip" install -r "$DEPLOY_DIR/requirements.txt" || true
sudo -u "$DEPLOY_USER" "$VENV_DIR/bin/pip" install \
    ray==2.8.0 \
    sqlalchemy \
    asyncpg \
    psycopg2-binary \
    httpx \
    python-dotenv

# Copy .env file
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    echo "Warning: .env file not found, creating template..."
    cat > "$DEPLOY_DIR/.env" <<EOF
# Database
DATABASE_URL=postgresql+asyncpg://rgrid:rgrid_password@localhost:5432/rgrid

# Hetzner Cloud
HETZNER_API_TOKEN=your_hetzner_api_token_here
HETZNER_SSH_KEY_PATH=/opt/rgrid/infra/hetzner_worker.key

# Ray
RAY_HEAD_ADDRESS=ray://10.0.0.1:10001
RAY_ENABLED=true
EOF
    chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/.env"
    echo "Please edit $DEPLOY_DIR/.env with your configuration"
fi

# Install systemd service
echo "Installing systemd service..."
cp "$DEPLOY_DIR/infra/orchestrator.service" /etc/systemd/system/
systemctl daemon-reload

# Enable and start service
echo "Enabling orchestrator service..."
systemctl enable orchestrator.service

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit $DEPLOY_DIR/.env with your configuration"
echo "2. Start the service: systemctl start orchestrator"
echo "3. Check status: systemctl status orchestrator"
echo "4. View logs: journalctl -u orchestrator -f"
echo ""
