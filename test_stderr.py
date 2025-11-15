#!/usr/bin/env python3
"""Test script with both stdout and stderr."""

import sys

print("This goes to stdout")
print("This goes to stderr", file=sys.stderr)
print("Back to stdout")
