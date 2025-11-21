#!/usr/bin/env python3
"""
Setup Hetzner Private Network for RGrid (one-time setup).

This script:
1. Creates a private network for RGrid workers
2. Attaches the staging server to the network
3. Outputs the network ID and private IPs for configuration
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.hetzner_client import HetznerClient


# Configuration
NETWORK_NAME = "rgrid-private"
NETWORK_IP_RANGE = "10.0.0.0/16"
SUBNET_IP_RANGE = "10.0.1.0/24"
STAGING_SERVER_ID = None  # Will be detected automatically


async def main():
    # Get API token from environment
    api_token = os.getenv("HETZNER_API_TOKEN")
    if not api_token:
        print("ERROR: HETZNER_API_TOKEN environment variable not set")
        sys.exit(1)

    client = HetznerClient(api_token)

    print("=== RGrid Private Network Setup ===\n")

    # Step 1: Check if network already exists
    print("Step 1: Checking for existing network...")
    networks = await client.get_networks(name=NETWORK_NAME)

    if networks:
        network = networks[0]
        network_id = network["id"]
        print(f"✓ Network '{NETWORK_NAME}' already exists (ID: {network_id})")
        print(f"  IP Range: {network['ip_range']}")
    else:
        print(f"Creating network '{NETWORK_NAME}'...")

        # Create network
        response = await client.create_network(
            name=NETWORK_NAME,
            ip_range=NETWORK_IP_RANGE,
            subnets=[
                {
                    "type": "cloud",
                    "ip_range": SUBNET_IP_RANGE,
                    "network_zone": "eu-central",
                }
            ],
            labels={"project": "rgrid", "environment": "staging"},
        )

        network = response["network"]
        network_id = network["id"]
        print(f"✓ Network created successfully!")
        print(f"  Network ID: {network_id}")
        print(f"  IP Range: {network['ip_range']}")

    # Step 2: Find staging server
    print("\nStep 2: Finding staging server...")
    servers = await client.list_servers(labels={"project": "rgrid", "environment": "staging"})

    if not servers:
        # Try to find by name pattern
        all_servers = await client.list_servers()
        servers = [s for s in all_servers if "rgrid" in s["name"].lower() or "staging" in s["name"].lower()]

    if not servers:
        print("ERROR: Could not find staging server")
        print("Please manually specify STAGING_SERVER_ID in this script")
        sys.exit(1)

    if len(servers) > 1:
        print("WARNING: Multiple potential staging servers found:")
        for s in servers:
            print(f"  - {s['name']} (ID: {s['id']})")
        print("\nUsing the first one. Edit script if this is incorrect.")

    staging_server = servers[0]
    server_id = staging_server["id"]
    server_name = staging_server["name"]

    print(f"✓ Found staging server: {server_name} (ID: {server_id})")

    # Step 3: Attach staging server to network
    print("\nStep 3: Attaching staging server to private network...")

    # Check if already attached
    if "private_net" in staging_server and staging_server["private_net"]:
        private_nets = staging_server["private_net"]
        already_attached = any(net["network"] == network_id for net in private_nets)

        if already_attached:
            private_ip = next(net["ip"] for net in private_nets if net["network"] == network_id)
            print(f"✓ Server already attached to network")
            print(f"  Private IP: {private_ip}")
        else:
            # Attach to network
            print(f"Attaching server to network...")
            await client.attach_server_to_network(
                network_id=network_id,
                server_id=server_id,
                ip="10.0.1.2"  # Reserve .2 for staging server
            )
            print(f"✓ Server attached to network")
            print(f"  Private IP: 10.0.1.2")
            private_ip = "10.0.1.2"
    else:
        # Attach to network
        print(f"Attaching server to network...")
        await client.attach_server_to_network(
            network_id=network_id,
            server_id=server_id,
            ip="10.0.1.2"  # Reserve .2 for staging server
        )
        print(f"✓ Server attached to network")
        print(f"  Private IP: 10.0.1.2")
        private_ip = "10.0.1.2"

    # Step 4: Output configuration
    print("\n" + "="*50)
    print("SETUP COMPLETE!")
    print("="*50)
    print(f"\nNetwork Configuration:")
    print(f"  Network ID: {network_id}")
    print(f"  Network Name: {NETWORK_NAME}")
    print(f"  IP Range: {NETWORK_IP_RANGE}")
    print(f"  Subnet: {SUBNET_IP_RANGE}")
    print(f"\nStaging Server:")
    print(f"  Server ID: {server_id}")
    print(f"  Server Name: {server_name}")
    print(f"  Private IP: {private_ip}")
    print(f"\nNext Steps:")
    print(f"  1. Update orchestrator environment variable:")
    print(f"     RGRID_NETWORK_ID={network_id}")
    print(f"\n  2. Configure PostgreSQL on staging server to listen on private interface:")
    print(f"     - Edit /etc/postgresql/*/main/postgresql.conf:")
    print(f"       listen_addresses = 'localhost,{private_ip}'")
    print(f"     - Edit /etc/postgresql/*/main/pg_hba.conf:")
    print(f"       host    rgrid_staging    rgrid_staging    10.0.1.0/24    md5")
    print(f"     - Restart PostgreSQL:")
    print(f"       sudo systemctl restart postgresql")
    print(f"\n  3. Workers will auto-connect via private network (10.0.1.0/24)")
    print(f"     Database URL for workers: postgresql://rgrid_staging:***@{private_ip}:5433/rgrid_staging")
    print(f"\nNOTE: Workers will be auto-assigned IPs starting from 10.0.1.3")


if __name__ == "__main__":
    asyncio.run(main())
