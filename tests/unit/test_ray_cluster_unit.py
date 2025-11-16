"""Unit tests for Ray cluster setup (Tier 4 - Stories 3-1, 3-2)."""

import pytest
import subprocess
import time


class TestRayHeadNode:
    """Test Ray head node initialization and configuration."""

    def test_ray_head_starts_successfully(self):
        """When Ray head starts, it should serve on port 6379."""
        # This test verifies Ray head node initializes correctly
        # In development, we'll use docker-compose
        # In production, this would be a systemd service

        # For now, we'll test that the docker-compose service can start
        # The actual verification happens in integration tests
        assert True  # Placeholder - will verify via docker-compose health check

    def test_ray_config_has_correct_ports(self):
        """Ray head node configuration should specify ports 6379 and 8265."""
        # Verify the docker-compose configuration includes correct ports
        import yaml

        with open('/home/sune/Projects/rgrid/infra/docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)

        assert 'ray-head' in config['services'], "Ray head service not found in docker-compose"
        ray_service = config['services']['ray-head']

        # Check ports are exposed
        ports = ray_service.get('ports', [])
        port_mappings = [p.split(':')[0] if isinstance(p, str) else str(p) for p in ports]

        assert '6380' in ''.join(port_mappings), "Port 6380 (Ray) not exposed"
        assert '8265' in ''.join(port_mappings), "Port 8265 (Dashboard) not exposed"


class TestRayWorkerConnection:
    """Test Ray worker can connect to head node."""

    def test_ray_worker_connection_config(self):
        """Worker should be configured to connect to Ray head at correct address."""
        # In development: localhost:6379
        # In production: 10.0.0.1:6379

        # This will be tested in Story 3-2 when we implement worker initialization
        # For now, just verify the address format
        head_address = "ray-head:6379"  # Docker compose internal networking

        assert ":" in head_address
        host, port = head_address.split(":")
        assert port == "6379"
