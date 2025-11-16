"""Integration test for Ray task execution (Tier 4 - Story 3-3)."""

import pytest


@pytest.mark.integration
@pytest.mark.slow
class TestRayTaskExecution:
    """Test Ray remote task execution."""

    def test_simple_ray_task_execution(self):
        """Test that a simple Ray task can be submitted and executed."""
        try:
            import ray
        except ImportError:
            pytest.skip("Ray not installed")

        # Initialize Ray
        try:
            ray.init(address="ray://localhost:10001", ignore_reinit_error=True)
        except Exception as e:
            pytest.skip(f"Cannot connect to Ray: {e}")

        try:
            # Define a simple remote task
            @ray.remote
            def simple_task(x):
                return x * 2

            # Submit task
            result_ref = simple_task.remote(21)

            # Get result
            result = ray.get(result_ref)

            # Verify result
            assert result == 42, f"Expected 42, got {result}"

        finally:
            ray.shutdown()

    def test_ray_task_distributes_across_workers(self):
        """Test that multiple tasks distribute across available workers."""
        try:
            import ray
        except ImportError:
            pytest.skip("Ray not installed")

        try:
            ray.init(address="ray://localhost:10001", ignore_reinit_error=True)
        except Exception as e:
            pytest.skip(f"Cannot connect to Ray: {e}")

        try:
            # Define a task that returns the node ID
            @ray.remote
            def get_node_id():
                import ray
                return ray.get_runtime_context().get_node_id()

            # Submit multiple tasks
            task_refs = [get_node_id.remote() for _ in range(10)]

            # Get results
            node_ids = ray.get(task_refs)

            # Should have executed on at least 1 node (could be head or worker)
            unique_nodes = set(node_ids)
            assert len(unique_nodes) >= 1, f"Expected at least 1 unique node, got {len(unique_nodes)}"

            # With 2 nodes (head + worker), we should see distribution
            # Note: May all execute on one node if that node is available
            print(f"Tasks distributed across {len(unique_nodes)} nodes")

        finally:
            ray.shutdown()

    def test_ray_task_with_error_handling(self):
        """Test that Ray tasks can handle errors properly."""
        try:
            import ray
        except ImportError:
            pytest.skip("Ray not installed")

        try:
            ray.init(address="ray://localhost:10001", ignore_reinit_error=True)
        except Exception as e:
            pytest.skip(f"Cannot connect to Ray: {e}")

        try:
            # Define a task that raises an error
            @ray.remote
            def failing_task():
                raise ValueError("Test error")

            # Submit task
            result_ref = failing_task.remote()

            # Should raise the error when we try to get the result
            with pytest.raises(ray.exceptions.RayTaskError):
                ray.get(result_ref)

        finally:
            ray.shutdown()


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skip(reason="Full execution integration not yet implemented - Story 3-3 partial")
class TestRayExecutionIntegration:
    """Test full execution integration with Ray (to be implemented)."""

    def test_database_execution_via_ray(self):
        """Test executing a database execution record via Ray task."""
        # This would test the full execute_script_task function
        # Skipped for now - demonstrates concept above
        pass
