#!/usr/bin/env python3
"""Simple RGrid test script."""

import os
import sys
import time

print("🚀 Hello from RGrid!")
print(f"Running on Python {sys.version.split()[0]}")

# Show arguments if provided
if len(sys.argv) > 1:
    print(f"\n📦 Arguments: {sys.argv[1:]}")

# Show environment variables
user_name = os.environ.get("USER_NAME", "World")
print(f"\n👋 Hello, {user_name}!")

# Do some simple computation
print("\n🔢 Computing factorial of 10...")
result = 1
for i in range(1, 11):
    result *= i
print(f"10! = {result:,}")

# Simulate some work
print("\n⏳ Processing for 3 seconds...")
time.sleep(3)

print("\n✅ All done! RGrid is working perfectly!")
