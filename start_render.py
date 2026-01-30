#!/usr/bin/env python3
"""
Render deployment startup script
Handles PORT environment variable properly
"""
import os
import sys

# Get port from environment or default to 8000
port = os.environ.get('PORT', '8000')

# Build the gunicorn command
cmd = f"gunicorn main:run --bind 0.0.0.0:{port} --workers 1 --timeout 300"

print(f"Starting bot with command: {cmd}")
os.system(cmd)