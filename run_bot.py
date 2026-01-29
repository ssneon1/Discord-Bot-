"""
Simple script to run the Discord bot directly with Python
This avoids the Windows compatibility issues with Gunicorn
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the bot
from main import run

if __name__ == "__main__":
    run()