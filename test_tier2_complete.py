#!/usr/bin/env python3
"""
Comprehensive Tier 2 test script.

Tests:
1. Script execution
2. Output capture (stdout)
3. Exit code tracking
4. Arguments
5. Environment variables
"""

import os
import sys
import time

def main():
    print("=== Tier 2 Integration Test ===")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")

    # Test arguments
    print(f"\nArguments received: {sys.argv[1:]}")

    # Test environment variables
    print(f"\nEnvironment variables:")
    print(f"  TEST_ENV: {os.environ.get('TEST_ENV', 'NOT_SET')}")
    print(f"  API_KEY: {os.environ.get('API_KEY', 'NOT_SET')}")

    # Test computation
    print("\nPerforming computation...")
    result = sum(range(1000))
    print(f"Sum of 0-999: {result}")

    # Test timing
    print("\nSleeping for 2 seconds...")
    time.sleep(2)
    print("Sleep complete!")

    # Final status
    print("\n=== Test completed successfully! ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
