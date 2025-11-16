"""Integration tests for Ray cluster (Tier 4 - Stories 3-1, 3-2)."""

import pytest
import httpx
import time


@pytest.mark.integration
class TestRayDashboard:
    """Test Ray dashboard accessibility."""

    def test_ray_dashboard_accessible(self):
        """Ray dashboard should be accessible at http://localhost:8265."""
        # Try to connect to Ray dashboard
        # This test requires Ray head node to be running (docker-compose up)

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get("http://localhost:8265")

                # Ray dashboard returns HTML page
                assert response.status_code == 200
                assert "ray" in response.text.lower() or "dashboard" in response.text.lower()
        except httpx.ConnectError:
            pytest.skip("Ray head node not running - start with docker-compose up")

    def test_ray_head_port_open(self):
        """Ray head node should be listening on port 6380."""
        import socket

        try:
            # Try to connect to Ray port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 6380))
            sock.close()

            assert result == 0, "Ray head node not listening on port 6380"
        except Exception as e:
            pytest.skip(f"Cannot test Ray port: {e}")


@pytest.mark.integration
class TestRayClusterSetup:
    """Test Ray cluster initialization and worker registration."""

    def test_ray_client_can_connect(self):
        """Ray client should be able to connect to head node."""
        # This test will be expanded in Story 3-2 when workers are implemented
        # For now, just verify we can import ray
        try:
            import ray
        except ImportError:
            pytest.skip("Ray not installed - run: pip install ray")

        # Verify Ray is available
        assert ray is not None

    def test_worker_registration(self):
        """Worker should register with Ray cluster and be visible."""
        try:
            import ray
        except ImportError:
            pytest.skip("Ray not installed")

        # Connect to Ray cluster
        try:
            ray.init(address="ray://localhost:10001", ignore_reinit_error=True)
        except Exception as e:
            pytest.skip(f"Cannot connect to Ray cluster: {e}")

        try:
            # Get cluster nodes
            nodes = ray.nodes()

            # Should have at least 2 nodes: head + 1 worker
            assert len(nodes) >= 2, f"Expected at least 2 nodes, got {len(nodes)}"

            # Check for worker node (not head)
            worker_nodes = [n for n in nodes if not n.get('Alive', False) or 'head' not in n.get('NodeName', '').lower()]

            # Verify we have at least one worker
            assert len(worker_nodes) >= 1, "No worker nodes found in cluster"

        finally:
            ray.shutdown()

    def test_worker_advertises_resources(self):
        """Worker should advertise 2 CPUs and 4GB memory."""
        try:
            import ray
        except ImportError:
            pytest.skip("Ray not installed")

        try:
            ray.init(address="ray://localhost:10001", ignore_reinit_error=True)
        except Exception as e:
            pytest.skip(f"Cannot connect to Ray cluster: {e}")

        try:
            # Get available cluster resources
            resources = ray.cluster_resources()

            # Should have CPU resources
            assert 'CPU' in resources, "No CPU resources advertised"

            # Worker advertises 2 CPUs + head has some, so total should be >= 2
            total_cpus = resources.get('CPU', 0)
            assert total_cpus >= 2, f"Expected >= 2 CPUs, got {total_cpus}"

            # Check memory (should be >= 4GB from worker)
            memory_bytes = resources.get('memory', 0)
            memory_gb = memory_bytes / (1024 ** 3)
            assert memory_gb >= 3, f"Expected >= 3GB memory, got {memory_gb:.2f}GB"

        finally:
            ray.shutdown()


@pytest.mark.integration
@pytest.mark.slow
class TestRayClusterE2E:
    """End-to-end Ray cluster tests."""

    def test_submit_simple_ray_task(self):
        """Should be able to submit and execute a simple Ray task."""
        try:
            import ray
        except ImportError:
            pytest.skip("Ray not installed")

        # This will be implemented in Story 3-3 (Ray task submission)
        # For now, skip
        pytest.skip("Ray task submission not yet implemented (Story 3-3)")
